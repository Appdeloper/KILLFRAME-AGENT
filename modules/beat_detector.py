def detect_beats(music_path):
    import librosa
    import numpy as np
    import os

    if not music_path or not os.path.exists(music_path):
        print("[KILLFRAME] ⚠️ No music — using fallback beats")
        times = [i*2.5 for i in range(200)]
        return {
            "total_beats":len(times),"bpm":120.0,
            "timestamps":times,"bass_drops":times[::4],
            "strong_beats":times[::2],"avg_gap_seconds":2.5,
            "recommended_clip_length":2.5,"song_duration":500.0
        }

    try:
        print(f"[KILLFRAME] Loading music: {os.path.basename(music_path)}")
        y, sr = librosa.load(music_path, duration=600, mono=True)
        song_duration = len(y)/sr
        print(f"[KILLFRAME] Music duration: {song_duration:.1f}s")

        y_harmonic, y_percussive = librosa.effects.hpss(y)
        tempo, beat_frames = librosa.beat.beat_track(y=y_percussive, sr=sr, trim=False)
        tempo_val = float(tempo[0]) if hasattr(tempo, "__len__") and len(tempo) > 0 else float(tempo)
        beat_times = librosa.frames_to_time(beat_frames, sr=sr).tolist()

        # Onset strength
        onset_env = librosa.onset.onset_strength(y=y_percussive, sr=sr)

        # Bass drops
        try:
            from scipy import signal as scipy_signal
            y_bass = librosa.effects.harmonic(y, margin=8)
            bass_env = librosa.onset.onset_strength(y=y_bass, sr=sr, n_mels=20)
            bass_peaks, _ = scipy_signal.find_peaks(
                bass_env,
                height=np.mean(bass_env)*2.0,
                distance=int(sr/4/512)
            )
            bass_times = librosa.frames_to_time(bass_peaks, sr=sr).tolist()
        except:
            bass_times = beat_times[::4]

        avg_str = float(np.mean([onset_env[min(f,len(onset_env)-1)] for f in beat_frames])) if len(beat_frames) > 0 else 1.0
        strong = [t for t,f in zip(beat_times,beat_frames)
                  if onset_env[min(f,len(onset_env)-1)] > avg_str*1.2]

        avg_gap = float(np.mean(np.diff(beat_times))) if len(beat_times)>1 else 2.5

        print(f"[KILLFRAME] BPM          : {tempo_val:.1f}")
        print(f"[KILLFRAME] Total beats  : {len(beat_times)}")
        print(f"[KILLFRAME] Bass drops   : {len(bass_times)}")
        print(f"[KILLFRAME] Strong beats : {len(strong)}")
        print(f"[KILLFRAME] Clip length  : {avg_gap:.3f}s")

        return {
            "total_beats":len(beat_times),
            "bpm":tempo_val,
            "timestamps":beat_times,
            "bass_drops":bass_times,
            "strong_beats":strong,
            "avg_gap_seconds":avg_gap,
            "recommended_clip_length":avg_gap,
            "song_duration":song_duration,
        }
    except Exception as e:
        print(f"[KILLFRAME] Beat detection error: {e}")
        times = [i*2.5 for i in range(200)]
        return {
            "total_beats":len(times),"bpm":120.0,
            "timestamps":times,"bass_drops":times[::4],
            "strong_beats":times[::2],"avg_gap_seconds":2.5,
            "recommended_clip_length":2.5,"song_duration":500.0
        }

def get_precise_beat_map(music_path):
    return detect_beats(music_path)
