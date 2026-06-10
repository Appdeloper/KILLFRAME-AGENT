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
        env_key = os.environ.pop("GROQ_API_KEY", None)
        try:
            analyze_style("https://www.youtube.com/watch?v=invalid_url_for_test")
            return FAIL, "Expected KeyError when GROQ_API_KEY is missing"
        except KeyError:
            pass
        finally:
            if env_key is not None:
                os.environ["GROQ_API_KEY"] = env_key
        return SUCCESS, "missing-api-key behavior is correct"
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
            edit_video([], {"beat_timestamps": [0.0, 1.0]}, "test_output.mp4", {"average_cut_pace_seconds": 2.5}, "test_music.mp3")
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
