import json
import logging
import os
import re
import tempfile
from glob import glob

import requests
from yt_dlp import YoutubeDL

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GROQ_MODEL = "llama3-8b-8192"
GROQ_ENDPOINT = f"https://api.groq.ai/v1/models/{GROQ_MODEL}/completions"

STYLE_SCHEMA = {
    "average_cut_pace_seconds": float,
    "intensity_preference": str,
    "visual_triggers": list,
}


class StyleAnalyzerError(Exception):
    pass


def _load_groq_api_key():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise KeyError("GROQ_API_KEY is required for style analysis")
    return api_key


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
        info = ydl.extract_info(video_url, download=False)
        video_id = info.get("id")
        if not video_id:
            return ""
        try:
            ydl.download([video_url])
        except Exception as exc:
            logger.warning("Transcript download failed for %s: %s", video_url, exc)
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


def _extract_response_text(data):
    if not isinstance(data, dict):
        return None
    if "output_text" in data and isinstance(data["output_text"], str):
        return data["output_text"]
    if "output" in data:
        output = data["output"]
        if isinstance(output, list):
            parts = []
            for item in output:
                if isinstance(item, dict) and "content" in item:
                    parts.append(item["content"])
                elif isinstance(item, str):
                    parts.append(item)
            if parts:
                return "\n".join(parts)
        elif isinstance(output, str):
            return output
    if "choices" in data and isinstance(data["choices"], list) and data["choices"]:
        first = data["choices"][0]
        if isinstance(first, dict):
            if "message" in first and isinstance(first["message"], dict):
                return first["message"].get("content")
            return first.get("text") or first.get("output_text")
    return None


def _safe_json_from_text(text):
    if not text:
        raise StyleAnalyzerError("Empty response text from Groq")
    first = text.find("{")
    last = text.rfind("}")
    if first == -1 or last == -1 or last <= first:
        raise StyleAnalyzerError("No JSON object found in Groq response")
    try:
        return json.loads(text[first:last + 1])
    except json.JSONDecodeError as exc:
        raise StyleAnalyzerError(f"Failed to parse JSON: {exc}") from exc


def _validate_style_payload(payload):
    result = {}
    if not isinstance(payload, dict):
        raise StyleAnalyzerError("Groq returned a non-JSON object")
    for key, expected_type in STYLE_SCHEMA.items():
        value = payload.get(key)
        if value is None:
            raise StyleAnalyzerError(f"Missing required style key: {key}")
        if not isinstance(value, expected_type):
            if expected_type is float and isinstance(value, (int, str)):
                try:
                    value = float(value)
                except (ValueError, TypeError):
                    raise StyleAnalyzerError(f"Invalid value for {key}: {value}")
            elif expected_type is list and isinstance(value, str):
                value = [item.strip() for item in value.split(",") if item.strip()]
            else:
                raise StyleAnalyzerError(f"Invalid type for {key}: {type(value).__name__}")
        result[key] = value
    if not isinstance(result["visual_triggers"], list):
        raise StyleAnalyzerError("visual_triggers must be a list")
    return {
        "average_cut_pace_seconds": float(result["average_cut_pace_seconds"]),
        "intensity_preference": str(result["intensity_preference"]).lower(),
        "visual_triggers": [str(item).lower() for item in result["visual_triggers"]],
    }


def _query_groq(api_key, prompt):
    response = requests.post(
        GROQ_ENDPOINT,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={"input": prompt, "max_output_tokens": 256},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def analyze_style(youtube_url):
    api_key = _load_groq_api_key()
    logger.info("Extracting metadata for %s", youtube_url)

    ydl_opts = {
        "skip_download": True,
        "quiet": True,
        "nocheckcertificate": True,
        "ignoreerrors": True,
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(youtube_url, download=False)

    entries = []
    if isinstance(info, dict) and info.get("entries"):
        for entry in info["entries"]:
            if isinstance(entry, dict) and entry.get("webpage_url"):
                entries.append(entry)
    elif isinstance(info, dict):
        entries.append(info)

    entries = [entry for entry in entries if entry]
    if not entries:
        raise StyleAnalyzerError("No videos found at the provided YouTube URL")

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
        raise StyleAnalyzerError("Unable to build creator profile from metadata")

    prompt = (
        "You are a film editor AI. Analyze the creator profile and return exactly one JSON object with the following keys:\n"
        "- average_cut_pace_seconds (float)\n"
        "- intensity_preference (high, smooth, slow-mo)\n"
        "- visual_triggers (array of strings)\n"
        "Do not include any explanatory text outside the JSON object.\n\n"
        f"Creator profile for the most recent videos:\n{profile_text}\n"
    )

    logger.info("Sending analysis prompt to Groq model %s", GROQ_MODEL)
    response = _query_groq(api_key, prompt)
    output_text = _extract_response_text(response)
    style_payload = _safe_json_from_text(output_text)
    result = _validate_style_payload(style_payload)
    logger.info("Style analysis result: %s", result)
    return result
