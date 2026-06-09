import librosa


def detect_beats(music_path):
    try:
        y, sr = librosa.load(music_path, sr=None, mono=True)
        if y.size == 0 or sr == 0:
            raise ValueError("Invalid audio file")

        onset_env = librosa.onset.onset_strength(y=y, sr=sr)
        if onset_env.size == 0:
            raise ValueError("No onset energy found")

        tempo, beat_frames = librosa.beat.beat_track(onset_envelope=onset_env, sr=sr)
        peak_frames = librosa.util.peak_pick(onset_env, pre_max=3, post_max=3, pre_avg=3, post_avg=3, delta=0.5, wait=10)

        if peak_frames.size > 0:
            peak_scores = onset_env[peak_frames]
            top_peaks = sorted(
                zip(peak_scores.tolist(), peak_frames.tolist()),
                key=lambda item: item[0],
                reverse=True,
            )[:10]
            timestamps = sorted([float(librosa.frames_to_time(frame, sr=sr)) for _, frame in top_peaks])
        else:
            timestamps = sorted([float(t) for t in librosa.frames_to_time(beat_frames, sr=sr).tolist()])[:10]

        if not timestamps:
            raise ValueError("No beats detected")

        avg_gap = 2.5
        if len(timestamps) > 1:
            gaps = [timestamps[i + 1] - timestamps[i] for i in range(len(timestamps) - 1)]
            avg_gap = float(sum(gaps) / len(gaps))

        recommended_clip_length = float(min(2.5, avg_gap)) if len(timestamps) > 1 else 2.5
        return {
            "total_beats": len(timestamps),
            "timestamps": timestamps,
            "avg_gap_seconds": round(avg_gap, 3),
            "recommended_clip_length": round(recommended_clip_length, 3),
        }
    except Exception:
        return {
            "total_beats": 0,
            "timestamps": [],
            "avg_gap_seconds": 2.5,
            "recommended_clip_length": 2.5,
        }
