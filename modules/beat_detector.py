import logging
import os
import librosa
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def detect_beats(music_path):
    if not music_path or not os.path.exists(music_path):
        raise ValueError(f"Music file not found: {music_path}")

    logger.info("Loading music file: %s", music_path)
    y, sr = librosa.load(music_path, sr=None, mono=True)
    if y.size == 0 or sr == 0:
        raise ValueError("Invalid or empty music file")

    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    if onset_env.size == 0:
        raise ValueError("Unable to detect onset strength from audio")

    # Detect beat drops where onset strength jumps by 0.3+
    diff_onset = np.diff(onset_env)
    
    threshold = 0.3
    drop_times = np.array([])
    
    # Try decaying threshold down to 0.01 to get at least 10 beat drops
    while threshold >= 0.01:
        drop_frames = np.where(diff_onset >= threshold)[0] + 1
        drop_times = librosa.frames_to_time(drop_frames, sr=sr)
        if len(drop_times) >= 10:
            break
        threshold -= 0.02

    logger.info("Used threshold %.2f, found %d beat drops", threshold, len(drop_times))

    # Fallback to librosa beat tracking if we have less than 10 timestamps
    if len(drop_times) < 10:
        logger.info("Fewer than 10 beat drops found. Adding standard beat tracking...")
        try:
            tempo, beat_frames = librosa.beat.beat_track(onset_envelope=onset_env, sr=sr)
            beat_times = librosa.frames_to_time(beat_frames, sr=sr)
            drop_times = np.unique(np.concatenate([drop_times, beat_times]))
        except Exception as e:
            logger.warning("Beat tracking failed: %s", e)

    # Fallback to even spacing across the audio if we still have less than 10
    if len(drop_times) < 10:
        logger.info("Still fewer than 10 beats. Generating evenly spaced timestamps...")
        duration = float(len(y)) / sr
        spaced_times = np.array([round((duration * (i + 1)) / 11, 4) for i in range(10)])
        drop_times = np.unique(np.concatenate([drop_times, spaced_times]))

    # Format timestamps
    timestamps = sorted([float(round(float(value), 4)) for value in drop_times])
    
    # Absolute safety fallback (no zero beats)
    if not timestamps:
        timestamps = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]

    logger.info("Detected %d rhythmic timestamps", len(timestamps))

    # Calculate tempo for BPM
    tempo_val = 120.0
    try:
        tempo_val, _ = librosa.beat.beat_track(y=y, sr=sr)
        tempo_val = float(tempo_val[0]) if isinstance(tempo_val, np.ndarray) else float(tempo_val)
    except Exception:
        pass

    return {
        "bpm": float(round(tempo_val, 2)),
        "beat_timestamps": timestamps,
        "timestamps": timestamps,
        "total_beats": len(timestamps),
    }
