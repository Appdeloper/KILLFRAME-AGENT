import logging
import os
from typing import Dict, List

import cv2
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MAX_SEGMENTS_PER_FILE = 8
DEFAULT_SEGMENT_SECONDS = 3.0


def _list_video_files(footage_folder):
    if not footage_folder or not os.path.isdir(footage_folder):
        raise ValueError("footage_folder must be a valid directory")

    video_files = []
    for root, dirs, files in os.walk(footage_folder):
        dirs[:] = [d for d in dirs if d != ".segment_clips"]
        for name in files:
            if name.lower().endswith((".mp4", ".mov", ".avi", ".mkv")):
                video_files.append(os.path.join(root, name))
    return sorted(video_files)


def _score_segment(frames, intensity_preference, trigger_bonus):
    if len(frames) < 2:
        return 0.0

    flow_score = 0.0
    flash_score = 0.0
    for prev, curr in zip(frames[:-1], frames[1:]):
        prev_gray = cv2.cvtColor(prev, cv2.COLOR_BGR2GRAY)
        curr_gray = cv2.cvtColor(curr, cv2.COLOR_BGR2GRAY)
        flow = cv2.calcOpticalFlowFarneback(prev_gray, curr_gray, None, 0.5, 3, 15, 3, 5, 1.2, 0)
        mag, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])
        flow_score += float(np.mean(mag))

        color_diff = cv2.absdiff(curr, prev)
        flash_score += float(np.mean(color_diff))

    flow_score /= max(1, len(frames) - 1)
    flash_score /= max(1, len(frames) - 1)

    if intensity_preference == "high":
        return flow_score * 1.5 + flash_score * 0.8 + trigger_bonus
    if intensity_preference == "smooth":
        return flow_score * 1.0 + flash_score * 0.5 + trigger_bonus * 0.5
    if intensity_preference == "slow-mo":
        return max(0.0, 1.0 / (1.0 + flow_score)) + flash_score * 0.3 + trigger_bonus * 0.2
    return flow_score + flash_score + trigger_bonus


def _extract_segments_from_clip(clip_path, average_length, intensity_preference, visual_triggers):
    cap = cv2.VideoCapture(clip_path)
    if not cap.isOpened():
        raise ValueError(f"Unable to open clip: {clip_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    segment_frame_count = int(max(1, round(fps * average_length)))
    stride = segment_frame_count

    candidates = []
    frames = []
    frame_index = 0

    while True:
        success, frame = cap.read()
        if not success:
            break
        frames.append(frame)
        frame_index += 1

        if len(frames) >= segment_frame_count:
            start_time = max(0.0, (frame_index - len(frames)) / fps)
            end_time = min(total_frames / fps, frame_index / fps)
            trigger_bonus = 0.0
            lower_path = clip_path.lower()
            for trigger in visual_triggers:
                if trigger in lower_path:
                    trigger_bonus += 15.0
            score = _score_segment(frames, intensity_preference, trigger_bonus)
            candidates.append({
                "path": clip_path,
                "start": round(start_time, 3),
                "end": round(end_time, 3),
                "score": score,
            })
            frames = []
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)

        if len(candidates) >= MAX_SEGMENTS_PER_FILE:
            break

    cap.release()
    return candidates


def select_clips(footage_folder, style_profile):
    if not isinstance(style_profile, dict):
        raise ValueError("style_profile must be a dictionary")

    video_files = _list_video_files(footage_folder)
    if not video_files:
        return []

    average_length = float(style_profile.get("average_cut_pace_seconds", DEFAULT_SEGMENT_SECONDS))
    intensity_preference = str(style_profile.get("intensity_preference", "high")).lower()
    visual_triggers = [str(item).lower() for item in style_profile.get("visual_triggers", []) if item]

    all_candidates = []
    for clip_path in video_files:
        try:
            candidates = _extract_segments_from_clip(
                clip_path,
                average_length,
                intensity_preference,
                visual_triggers,
            )
            all_candidates.extend(candidates)
        except Exception as exc:
            logger.warning("Skipping clip %s due to error: %s", clip_path, exc)
            continue

    if not all_candidates:
        return []

    all_candidates.sort(key=lambda candidate: candidate["score"], reverse=True)
    selected = all_candidates[:min(len(all_candidates), 12)]
    logger.info("Selected %d highlight segments from %d files", len(selected), len(video_files))
    return selected
