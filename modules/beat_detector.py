import logging
import os
import librosa
import numpy as np
import scipy.signal
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def detect_beats(music_path):
    if not music_path or not os.path.exists(music_path):
        raise ValueError(f"Music file not found: {music_path}")

    logger.info("Loading music file: %s", music_path)
    # Load and separate audio (duration capped at 10 minutes)
    y, sr = librosa.load(music_path, sr=None, mono=True, duration=600)
    if y.size == 0 or sr == 0:
        raise ValueError("Invalid or empty music file")

    song_duration = float(len(y) / sr)

    # Step A — Separate harmonic and percussive
    y_harmonic, y_percussive = librosa.effects.hpss(y)
    
    # Get bass frequencies by computing harmonic separation with a margin
    y_bass = librosa.effects.harmonic(y, margin=8)

    # Step B — Multi-layer beat detection
    # Percussive beats
    tempo, beat_frames = librosa.beat.beat_track(y=y_percussive, sr=sr)
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)
    bpm_val = float(tempo[0]) if hasattr(tempo, "__len__") else float(tempo)

    # Onset strength
    onset_env = librosa.onset.onset_strength(y=y_percussive, sr=sr)
    onset_frames = librosa.onset.onset_detect(onset_envelope=onset_env, sr=sr)
    onset_times = librosa.frames_to_time(onset_frames, sr=sr)

    # Bass drop detection using frame-level peaks (with frame distance logic)
    bass_env = librosa.onset.onset_strength(y=y_bass, sr=sr, n_mels=20)
    distance_frames = max(1, int((sr // 4) // 512))
    
    bass_peaks = scipy.signal.find_peaks(bass_env, height=np.mean(bass_env)*2.5, distance=distance_frames)[0]
    bass_times = librosa.frames_to_time(bass_peaks, sr=sr)

    # Fallback if no bass drops are found: take the top 8 highest energy peaks
    if len(bass_times) < 8:
        lower_height = np.mean(bass_env) * 1.5
        bass_peaks_lower = scipy.signal.find_peaks(bass_env, height=lower_height, distance=distance_frames)[0]
        if len(bass_peaks_lower) >= 8:
            bass_times = librosa.frames_to_time(bass_peaks_lower, sr=sr)
        else:
            # Absolute fallback: choose top 8 frames
            sorted_indices = np.argsort(bass_env)[::-1]
            top_indices = sorted_indices[:min(8, len(sorted_indices))]
            bass_times = librosa.frames_to_time(sorted(top_indices), sr=sr)

    # Buildup detection
    rms = librosa.feature.rms(y=y)[0]
    buildup_threshold = np.percentile(rms, 85)
    buildup_indices = np.where(rms > buildup_threshold)[0]
    buildup_times = librosa.frames_to_time(buildup_indices, sr=sr)

    # Classification
    beat_types = []
    for t in beat_times:
        if any(abs(t - bt) < 0.1 for bt in bass_times):
            beat_types.append("bass_drop")
        else:
            frame_idx = min(len(onset_env) - 1, librosa.time_to_frames(t, sr=sr))
            if onset_env[frame_idx] > np.percentile(onset_env, 90):
                beat_types.append("strong")
            else:
                beat_types.append("regular")

    # Safety: Ensure we have at least 10 beat timestamps
    if len(beat_times) < 10:
        beat_times = np.linspace(1.0, max(10.0, song_duration - 1.0), 10)
        beat_types = ["regular"] * 10
        bpm_val = 120.0

    # Strong beats selection
    strong_beats = [t for t, bt in zip(beat_times, beat_types) if bt in ["strong", "bass_drop"]]
    if len(strong_beats) < 10:
        # Fallback to top onset strength beats
        sorted_indices = np.argsort(onset_env)[::-1]
        top_indices = sorted_indices[:min(15, len(sorted_indices))]
        strong_beats = sorted(librosa.frames_to_time(top_indices, sr=sr).tolist())

    # Format timestamps lists
    timestamps_list = beat_times.tolist()
    bass_drops_list = bass_times.tolist()
    strong_beats_list = [float(t) for t in strong_beats]

    # Metrics
    avg_gap = float(np.mean(np.diff(timestamps_list))) if len(timestamps_list) > 1 else 1.87
    rec_len = max(2.5, avg_gap)
    
    # Calculate duration string e.g. 3:24
    dur_min = int(song_duration // 60)
    dur_sec = int(song_duration % 60)
    duration_str = f"{dur_min}:{dur_sec:02d}"

    # Print output in exact format requested
    print(f"[KILLFRAME] BPM: {bpm_val:.1f}")
    print(f"[KILLFRAME] Total beats: {len(timestamps_list)}")
    print(f"[KILLFRAME] Bass drops: {len(bass_drops_list)} (these are your best cut points)")
    print(f"[KILLFRAME] Strong beats: {len(strong_beats_list)}")
    print(f"[KILLFRAME] Song duration: {duration_str}")
    print(f"[KILLFRAME] Recommended clip length: {rec_len:.2f} seconds")

    return {
        "total_beats": int(len(timestamps_list)),
        "bpm": float(round(bpm_val, 2)),
        "timestamps": timestamps_list,
        "bass_drops": bass_drops_list,
        "strong_beats": strong_beats_list,
        "beat_types": beat_types,
        "avg_gap": float(round(avg_gap, 4)),
        "recommended_clip_length": float(round(rec_len, 2)),
        "song_duration": float(round(song_duration, 2)),
        "energy_map": rms.tolist()
    }
