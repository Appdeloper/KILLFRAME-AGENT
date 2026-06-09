import logging

import librosa

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def detect_beats(music_path):
    if not music_path or not isinstance(music_path, str):
        raise ValueError("music_path must be a valid string")

    logger.info("Loading audio file %s", music_path)
    y, sr = librosa.load(music_path, sr=None, mono=True)
    if y.size == 0 or sr == 0:
        raise ValueError("Invalid or empty audio file")

    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    if onset_env.size == 0:
        raise ValueError("No onset strength detected in audio")

    tempo, beat_frames = librosa.beat.beat_track(onset_envelope=onset_env, sr=sr)
    logger.info("Detected tempo: %.2f BPM", tempo)

    onset_times = librosa.onset.onset_detect(
        y=y,
        sr=sr,
        units="time",
        backtrack=False,
        pre_max=3,
        post_max=3,
        pre_avg=3,
        post_avg=3,
        delta=0.35,
        wait=6,
    )

    if len(onset_times) == 0:
        logger.warning("No onset peaks found, falling back to beat frames")
        onset_times = librosa.frames_to_time(beat_frames, sr=sr)

    if len(onset_times) == 0:
        logger.warning("Beat frames are empty, using a fixed fallback timeline")
        duration = float(len(y)) / sr
        onset_times = [round((duration * (i + 1)) / 11, 4) for i in range(10)]

    onset_times = [float(round(float(time), 4)) for time in onset_times]
    frame_timestamps = [int(librosa.time_to_frames(time, sr=sr)) for time in onset_times]
    logger.info("Detected %d onset peak timestamps", len(onset_times))

    return {
        "bpm": float(round(tempo, 2)),
        "beat_timestamps": onset_times,
        "frame_timestamps": frame_timestamps,
        "timestamps": onset_times,
        "total_beats": len(onset_times),
    }
