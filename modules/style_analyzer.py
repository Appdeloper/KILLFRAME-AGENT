import json
import logging
import os
import re
import tempfile
from glob import glob

import requests
from yt_dlp import YoutubeDL
import google.generativeai as genai

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StyleAnalyzerError(Exception):
    pass

def _clean_text(text):
    if not text:
        return ""
    return re.sub(r"\s+", " ", text.strip())

def _transcript_from_vtt(path):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as stream:
            lines = []
            for line in stream:
                stripped = line.strip()
                if not stripped or stripped.startswith("WEBVTT"):
                    continue
                if re.match(r"^\d{2}:\d{2}:\d{2}\.\d{3}", stripped) or re.match(r"^\d{2}:\d{2}\.\d{3}", stripped):
                    continue
                lines.append(stripped)
        return " ".join(lines)
    except Exception:
        return ""

def _fetch_transcript(video_url, tmp_dir):
    options = {
        "skip_download": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitlesformat": "vtt",
        "subtitleslangs": ["en"],
        "outtmpl": os.path.join(tmp_dir, "%(id)s.%(ext)s"),
        "quiet": True,
        "nocheckcertificate": True,
    }
    with YoutubeDL(options) as ydl:
        try:
            info = ydl.extract_info(video_url, download=False)
            video_id = info.get("id")
            if not video_id:
                return ""
            ydl.download([video_url])
        except Exception as exc:
            logger.warning("Transcript download failed for %s: %s", video_url, exc)
            return ""
        patterns = [
            os.path.join(tmp_dir, f"{video_id}.en.vtt"),
            os.path.join(tmp_dir, f"{video_id}.vtt"),
            os.path.join(tmp_dir, f"{video_id}.en.json3"),
            os.path.join(tmp_dir, f"{video_id}.json3"),
        ]
        for path in patterns:
            if os.path.exists(path):
                return _transcript_from_vtt(path)
    return ""

def _collect_video_metadata(entry):
    return {
        "title": _clean_text(entry.get("title", "")),
        "description": _clean_text(entry.get("description", "")),
        "tags": entry.get("tags", []) or [],
        "chapters": [
            {"title": _clean_text(chapter.get("title", "")), "start_time": chapter.get("start_time")}
            for chapter in entry.get("chapters", []) or []
        ],
        "upload_date": entry.get("upload_date"),
        "view_count": entry.get("view_count"),
    }

def _build_creator_profile(entries, transcripts):
    blocks = []
    for index, entry in enumerate(entries, start=1):
        metadata = _collect_video_metadata(entry)
        transcript = transcripts.get(entry.get("webpage_url")) or ""
        blocks.append(
            json.dumps(
                {
                    "video_rank": index,
                    "metadata": metadata,
                    "transcript": transcript,
                },
                indent=2,
            )
        )
    return "\n\n".join(blocks)

def analyze_style(youtube_url):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise KeyError("GEMINI_API_KEY is required for style analysis")

    logger.info("Configuring Gemini API key and model")
    genai.configure(api_key=api_key)

    logger.info("Extracting metadata for %s", youtube_url)
    ydl_opts = {
        "skip_download": True,
        "quiet": True,
        "nocheckcertificate": True,
        "ignoreerrors": True,
    }
    with YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(youtube_url, download=False)
        except Exception as exc:
            logger.warning("Failed to extract YouTube info: %s. Using default profile.", exc)
            info = {}

    entries = []
    if isinstance(info, dict) and info.get("entries"):
        for entry in info["entries"]:
            if isinstance(entry, dict) and entry.get("webpage_url"):
                entries.append(entry)
    elif isinstance(info, dict):
        entries.append(info)

    entries = [entry for entry in entries if entry]
    
    profile_text = ""
    if entries:
        entries = entries[:5]
        transcripts = {}
        with tempfile.TemporaryDirectory() as tmp_dir:
            for entry in entries:
                video_url = entry.get("webpage_url")
                if not video_url:
                    continue
                transcripts[video_url] = _fetch_transcript(video_url, tmp_dir)
        profile_text = _build_creator_profile(entries, transcripts)

    if not profile_text:
        # Fallback profile text if yt-dlp fails
        profile_text = "Free Fire montage creator, fast pacing, intense cuts, high motion, red and dark colors."

    prompt = (
        "You are an expert film editor AI. Analyze the gaming creator profile and return exactly one JSON object with these keys:\n"
        "- cuts_per_minute (float)\n"
        "- transition_style (string)\n"
        "- pacing (string: fast, smooth, slow-mo)\n"
        "- vibe (string)\n"
        "- color_tone (string)\n"
        "- recommended_clip_length (float)\n"
        "Do not include any explanatory text outside the JSON object.\n\n"
        f"Creator profile for the most recent videos:\n{profile_text}\n"
    )

    logger.info("Generating style analysis using gemini-1.5-flash")
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(
        prompt,
        generation_config={"response_mime_type": "application/json"}
    )
    
    res_text = response.text.strip()
    logger.info("Received raw response: %s", res_text)
    
    try:
        data = json.loads(res_text)
    except Exception as e:
        raise StyleAnalyzerError(f"Failed to parse JSON response from Gemini: {e}")

    # Map old keys for compatibility
    cuts = float(data.get("cuts_per_minute", 15.0))
    if cuts <= 0:
        cuts = 15.0
    data["average_cut_pace_seconds"] = float(round(60.0 / cuts, 2))
    data["intensity_preference"] = data.get("pacing", "high").lower()
    data["visual_triggers"] = [data.get("vibe", "intense").lower()]
    
    logger.info("Style analysis complete: %s", data)
    return data
