import json
import os
import re
import requests
from yt_dlp import YoutubeDL

DEFAULT_STYLE = {
    "cuts_per_minute": 18,
    "transition_style": "hard cut",
    "pacing": "aggressive",
    "vibe": "hype",
    "color_tone": "dark",
    "recommended_clip_length": 2.5,
}


def _safe_json_from_text(text):
    if not text:
        raise ValueError("Empty response text")
    first = text.find("{")
    last = text.rfind("}")
    if first == -1 or last == -1 or last <= first:
        raise ValueError("No JSON object found")
    json_text = text[first:last + 1]
    return json.loads(json_text)


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


def analyze_style(youtube_url):
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return DEFAULT_STYLE.copy()

    try:
        with YoutubeDL({"skip_download": True, "quiet": True, "nocheckcertificate": True}) as ydl:
            info = ydl.extract_info(youtube_url, download=False)

        metadata = {
            "title": info.get("title"),
            "uploader": info.get("uploader"),
            "channel_id": info.get("uploader_id"),
            "description": info.get("description"),
            "duration": info.get("duration"),
            "view_count": info.get("view_count"),
            "like_count": info.get("like_count"),
            "average_rating": info.get("average_rating"),
            "categories": info.get("categories") or [],
            "tags": info.get("tags") or [],
        }

        prompt = (
            "Please analyze the YouTube creator metadata and return only a JSON object with the keys: "
            "cuts_per_minute, transition_style, pacing, vibe, color_tone, recommended_clip_length. "
            "Use the metadata below to infer a montage editing style for gaming content. "
            "Do not add any additional text outside the JSON object.\n\n"
            f"Metadata:\n{json.dumps(metadata, indent=2)}\n"
        )

        response = requests.post(
            "https://api.groq.ai/v1/models/llama3-70b-8192/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={"input": prompt, "max_output_tokens": 256},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        text = _extract_response_text(data)
        if text is None:
            return DEFAULT_STYLE.copy()

        style_data = _safe_json_from_text(text)
        parsed = {
            "cuts_per_minute": style_data.get("cuts_per_minute", DEFAULT_STYLE["cuts_per_minute"]),
            "transition_style": style_data.get("transition_style", DEFAULT_STYLE["transition_style"]),
            "pacing": style_data.get("pacing", DEFAULT_STYLE["pacing"]),
            "vibe": style_data.get("vibe", DEFAULT_STYLE["vibe"]),
            "color_tone": style_data.get("color_tone", DEFAULT_STYLE["color_tone"]),
            "recommended_clip_length": float(style_data.get("recommended_clip_length", DEFAULT_STYLE["recommended_clip_length"])),
        }
        return parsed
    except Exception:
        return DEFAULT_STYLE.copy()
