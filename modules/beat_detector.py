import os
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

def detect_beats(music_path):
    import librosa
    import numpy as np
    from scipy import signal as scipy_signal

    print(f"[KILLFRAME] Analyzing music: {os.path.basename(music_path)}")

    try:
        # Load audio max 10 minutes
        y, sr = librosa.load(music_path, duration=600)
        print(f"[KILLFRAME] Music duration: {len(y)/sr:.1f}s")

        # Separate percussion from harmony
        y_harmonic, y_percussive = librosa.effects.hpss(y)

        # Get tempo and beats
        tempo, beat_frames = librosa.beat.beat_track(y=y_percussive, sr=sr)
        tempo_val = float(tempo[0]) if hasattr(tempo, "__len__") and len(tempo) > 0 else float(tempo)
        beat_times = librosa.frames_to_time(beat_frames, sr=sr).tolist()

        # Onset detection
        onset_env = librosa.onset.onset_strength(y=y_percussive, sr=sr)
        onset_frames = librosa.onset.onset_detect(onset_envelope=onset_env, sr=sr)
        onset_times = librosa.frames_to_time(onset_frames, sr=sr).tolist()

        # Bass drop detection
        try:
            y_bass = librosa.effects.harmonic(y, margin=8)
            bass_env = librosa.onset.onset_strength(y=y_bass, sr=sr, n_mels=20)
            bass_peaks, _ = scipy_signal.find_peaks(
                bass_env,
                height=np.mean(bass_env)*2.5,
                distance=sr//4
            )
            bass_times = librosa.frames_to_time(bass_peaks, sr=sr).tolist()
        except:
            bass_times = []

        # Energy map for buildup detection
        rms = librosa.feature.rms(y=y)[0]
        energy_times = librosa.frames_to_time(
            np.where(rms > np.percentile(rms, 80))[0], sr=sr
        ).tolist()

        # Classify beats
        strong_beats = []
        for t in beat_times:
            frame = librosa.time_to_frames(t, sr=sr)
            if frame < len(onset_env):
                if onset_env[frame] > np.percentile(onset_env, 80):
                    strong_beats.append(t)

        avg_gap = float(np.mean(np.diff(beat_times))) if len(beat_times) > 1 else 2.5

        print(f"[KILLFRAME] BPM: {tempo_val:.1f}")
        print(f"[KILLFRAME] Total beats: {len(beat_times)}")
        print(f"[KILLFRAME] Bass drops: {len(bass_times)}")
        print(f"[KILLFRAME] Strong beats: {len(strong_beats)}")
        print(f"[KILLFRAME] Avg gap: {avg_gap:.2f}s")
        print(f"[KILLFRAME] Recommended clip length: {avg_gap:.2f}s")

        return {
            "total_beats": len(beat_times),
            "bpm": tempo_val,
            "timestamps": beat_times,
            "bass_drops": bass_times,
            "strong_beats": strong_beats,
            "onset_times": onset_times,
            "energy_times": energy_times,
            "avg_gap_seconds": avg_gap,
            "recommended_clip_length": avg_gap,
            "song_duration": float(len(y)/sr),
        }

    except Exception as e:
        print(f"[KILLFRAME] Beat detection error: {e}")
        print("[KILLFRAME] Using fallback beat map")
        fallback_times = [i*2.5 for i in range(40)]
        return {
            "total_beats": 40,
            "bpm": 120.0,
            "timestamps": fallback_times,
            "bass_drops": fallback_times[::4],
            "strong_beats": fallback_times[::2],
            "onset_times": fallback_times,
            "energy_times": fallback_times,
            "avg_gap_seconds": 2.5,
            "recommended_clip_length": 2.5,
            "song_duration": 100.0,
        }
