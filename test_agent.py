import os
import tempfile
import numpy as np
import soundfile as sf

from modules.beat_detector import detect_beats
from modules.style_analyzer import analyze_style
from modules.clip_selector import select_clips
from modules.video_editor import edit_video


SUCCESS = "PASS"
FAIL = "FAIL"


def test_beat_detector():
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            sample_rate = 22050
            duration_seconds = 2.0
            silent_audio = np.zeros(int(sample_rate * duration_seconds), dtype=np.float32)
            sf.write(tmp.name, silent_audio, sample_rate)
            result = detect_beats(tmp.name)
        os.unlink(tmp.name)
        if not isinstance(result, dict):
            return FAIL, "beat_detector did not return a dict"
        if "timestamps" not in result or "total_beats" not in result:
            return FAIL, "beat_detector response missing expected keys"
        return SUCCESS, result
    except Exception as exc:
        return FAIL, str(exc)


def test_style_analyzer():
    try:
        result = analyze_style("https://www.youtube.com/watch?v=invalid_url_for_test")
        if not isinstance(result, dict):
            return FAIL, "style_analyzer did not return a dict"
        expected_keys = {"cuts_per_minute", "transition_style", "pacing", "vibe", "color_tone", "recommended_clip_length"}
        if not expected_keys.issubset(result.keys()):
            return FAIL, f"style_analyzer result missing keys: {expected_keys - set(result.keys())}"
        return SUCCESS, result
    except Exception as exc:
        return FAIL, str(exc)


def test_clip_selector():
    try:
        result = select_clips(os.getcwd(), {})
        if not isinstance(result, list):
            return FAIL, "clip_selector did not return a list"
        return SUCCESS, result
    except Exception as exc:
        return FAIL, str(exc)


def test_video_editor():
    try:
        try:
            edit_video([], {"total_beats": 0, "timestamps": [], "avg_gap_seconds": 2.5}, "test_output.mp4", {})
        except ValueError:
            return SUCCESS, "empty-clips error handled"
        except Exception as exc:
            return FAIL, f"unexpected exception: {exc}"
        return FAIL, "edit_video did not raise on empty clips"
    except Exception as exc:
        return FAIL, str(exc)


if __name__ == "__main__":
    tests = [
        ("beat_detector", test_beat_detector),
        ("style_analyzer", test_style_analyzer),
        ("clip_selector", test_clip_selector),
        ("video_editor", test_video_editor),
    ]
    passed = 0
    for name, func in tests:
        status, detail = func()
        print(f"{name}: {status}")
        if status == SUCCESS:
            passed += 1
        else:
            print(f"  detail: {detail}")
    print(f"KILLFRAME-AGENT: {passed}/{len(tests)} modules working")
    if passed != len(tests):
        raise SystemExit(1)
