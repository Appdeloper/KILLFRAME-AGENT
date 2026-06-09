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


def select_clips(footage_folder, style_profile):
    clips = []
    for root, _, files in os.walk(footage_folder):
        for name in files:
            if name.lower().endswith((".mp4", ".avi")):
                clips.append(os.path.join(root, name))

    if not clips:
        return []

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
    return [clip_path for _, clip_path in scored_clips]
