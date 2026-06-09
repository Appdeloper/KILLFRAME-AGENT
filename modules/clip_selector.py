import os
import cv2


def _motion_score_for_clip(path, max_frames=120):
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        raise ValueError(f"Unable to open clip: {path}")

    prev_gray = None
    motion_total = 0.0
    frames_processed = 0

    while frames_processed < max_frames:
        success, frame = cap.read()
        if not success:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if prev_gray is not None:
            diff = cv2.absdiff(gray, prev_gray)
            motion_total += float(diff.mean())
        prev_gray = gray
        frames_processed += 1

    cap.release()
    if frames_processed <= 1:
        return 0.0
    return motion_total / max(1, frames_processed - 1)


def _split_single_video_into_segments(video_path, footage_folder):
    try:
        segments_folder = os.path.join(footage_folder, ".segment_clips")
        if os.path.exists(segments_folder):
            for existing in os.listdir(segments_folder):
                try:
                    os.remove(os.path.join(segments_folder, existing))
                except Exception:
                    pass
        os.makedirs(segments_folder, exist_ok=True)

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Unable to open video: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 640)
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 360)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)

        max_duration_seconds = 120.0
        max_segments = 16
        segment_duration = 3.0
        frames_per_segment = max(1, int(round(fps * segment_duration)))
        max_frames = min(frame_count if frame_count > 0 else float('inf'), int(round(fps * max_duration_seconds)))
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")

        segments = []
        segment_index = 0
        writer = None
        segment_score = 0.0
        segment_frame_count = 0
        last_gray = None
        segment_path = None
        frames_read = 0

        while frames_read < max_frames:
            success, frame = cap.read()
            if not success:
                break

            if writer is None:
                segment_path = os.path.join(segments_folder, f"segment_{segment_index:03d}.mp4")
                writer = cv2.VideoWriter(segment_path, fourcc, fps, (width, height))
                if not writer.isOpened():
                    raise ValueError(f"Unable to write segment: {segment_path}")
                segment_score = 0.0
                segment_frame_count = 0
                last_gray = None

            writer.write(frame)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            if last_gray is not None:
                diff = cv2.absdiff(gray, last_gray)
                segment_score += float(diff.mean())
            last_gray = gray
            segment_frame_count += 1
            frames_read += 1

            if segment_frame_count >= frames_per_segment:
                writer.release()
                writer = None
                segments.append((segment_score, segment_path))
                segment_index += 1
                if segment_index >= max_segments:
                    break

        if writer is not None:
            writer.release()
            if segment_frame_count > 0:
                segments.append((segment_score, segment_path))

        cap.release()

        return segments
    except Exception:
        return []


def _select_top_segments(segments):
    if not segments:
        return []
    segments.sort(key=lambda item: item[0], reverse=True)
    paths = [path for _, path in segments]
    return paths[:8] if len(paths) >= 8 else paths


def select_clips(footage_folder, style_profile):
    try:
        clips = []
        for root, dirs, files in os.walk(footage_folder):
            dirs[:] = [d for d in dirs if d != ".segment_clips"]
            for name in files:
                if name.lower().endswith((".mp4", ".avi")):
                    clips.append(os.path.join(root, name))

        if not clips:
            return []

        if len(clips) == 1:
            single_path = clips[0]
            segments = _split_single_video_into_segments(single_path, footage_folder)
            selected = _select_top_segments(segments)
            return selected if selected else clips

        scored_clips = []
        for clip_path in clips:
            try:
                score = _motion_score_for_clip(clip_path)
                scored_clips.append((score, clip_path))
            except Exception:
                continue

        if not scored_clips:
            return clips

        scored_clips.sort(key=lambda item: item[0], reverse=True)
        selected = [clip_path for _, clip_path in scored_clips[:8]]
        return selected if selected else clips
    except Exception:
        return clips
