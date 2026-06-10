import json
import logging
import os
import re
import tempfile
from yt_dlp import YoutubeDL

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ensure all libraries are installed
def ensure_libraries():
    libs = ["moviepy", "opencv-python", "numpy", "google-generativeai", "openai", "groq", "anthropic"]
    for lib in libs:
        try:
            __import__(lib.replace("-", "_"))
        except ImportError:
            os.system(f"pip install {lib}")
            print(f"[KILLFRAME] Installed: {lib}")

ensure_libraries()

def detect_api_provider(api_key):
    if api_key.startswith("sk-ant-"):
        return "anthropic"
    elif api_key.startswith("sk-"):
        return "openai"
    elif api_key.startswith("gsk_"):
        return "groq"
    elif api_key.startswith("AIza"):
        return "gemini"
    else:
        return "gemini"  # default fallback

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
    # Load API key in order of preference
    api_key = (
        os.getenv("GEMINI_API_KEY") or
        os.getenv("OPENAI_API_KEY") or
        os.getenv("GROQ_API_KEY") or
        os.getenv("ANTHROPIC_API_KEY") or
        None
    )

    default_profile = {
        "cuts_per_minute": 20,
        "transition_style": "hard cut",
        "pacing": "aggressive",
        "vibe": "hype",
        "color_tone": "dark saturated",
        "recommended_clip_length": 2.5,
        "uses_slowmo": False,
        "output_duration": 60
    }

    # Helper to map compatibility keys
    def finalize_profile(data):
        cuts = float(data.get("cuts_per_minute", 20.0))
        if cuts <= 0:
            cuts = 20.0
        data["average_cut_pace_seconds"] = float(round(60.0 / cuts, 2))
        data["intensity_preference"] = data.get("pacing", "aggressive").lower()
        data["visual_triggers"] = [data.get("vibe", "hype").lower()]
        return data

    if not api_key:
        print("[KILLFRAME] Warning: No API keys found in environment. Using default style profile.")
        return finalize_profile(default_profile)

    provider = detect_api_provider(api_key)
    print(f"[KILLFRAME] AI Provider detected: {provider.capitalize()}")
    print("[KILLFRAME] Analyzing reference style...")

    # Build creator profile
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
        profile_text = "Free Fire gaming montage, high pacing, intense color grade, white flashes."

    prompt = (
        "You are an expert film editor AI. Analyze the gaming creator profile and return exactly one JSON object with these keys:\n"
        "- cuts_per_minute (float)\n"
        "- transition_style (string)\n"
        "- pacing (string)\n"
        "- vibe (string)\n"
        "- color_tone (string)\n"
        "- recommended_clip_length (float)\n"
        "- uses_slowmo (boolean)\n"
        "- output_duration (integer)\n"
        "Do not include any explanatory text outside the JSON object.\n\n"
        f"Creator profile for the most recent videos:\n{profile_text}\n"
    )

    result_text = ""
    try:
        if provider == "openai":
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}]
            )
            result_text = response.choices[0].message.content
        elif provider == "anthropic":
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            response = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}]
            )
            result_text = response.content[0].text
        elif provider == "groq":
            from groq import Groq
            client = Groq(api_key=api_key)
            response = client.chat.completions.create(
                model="llama3-70b-8192",
                messages=[{"role": "user", "content": prompt}]
            )
            result_text = response.choices[0].message.content
        else: # gemini
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(prompt)
            result_text = response.text

        # Parse JSON
        start = result_text.find('{')
        end = result_text.rfind('}')
        if start != -1 and end != -1:
            parsed = json.loads(result_text[start:end+1])
            logger.info("Successfully parsed AI response: %s", parsed)
            return finalize_profile(parsed)
        else:
            raise ValueError("No JSON block found in response")

    except Exception as e:
        print(f"[KILLFRAME] AI API Call failed: {e}. Falling back to default style profile.")
        return finalize_profile(default_profile)
