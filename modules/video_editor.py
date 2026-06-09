import logging
import os
from moviepy.editor import VideoFileClip, concatenate_videoclips

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def edit_video(segments, beat_timeline, output_path, style_profile):
    if not segments:
        raise ValueError("No highlight segments provided for editing.")
    if not isinstance(beat_timeline, dict) or "beat_timestamps" not in beat_timeline:
        raise ValueError("beat_timeline must include beat_timestamps")
    if not isinstance(style_profile, dict) or "average_cut_pace_seconds" not in style_profile:
        raise ValueError("style_profile must include average_cut_pace_seconds")

    beat_timestamps = beat_timeline["beat_timestamps"]
    if len(beat_timestamps) < 2:
        raise ValueError("Need at least two beat timestamps to edit a montage")

    durations = []
    for index in range(min(len(segments), len(beat_timestamps))):
        if index < len(beat_timestamps) - 1:
            durations.append(max(0.5, beat_timestamps[index + 1] - beat_timestamps[index]))
        else:
            durations.append(float(style_profile["average_cut_pace_seconds"]))

    selected_segments = sorted(segments, key=lambda item: item.get("score", 0), reverse=True)
    selected_segments = selected_segments[: len(durations)]

    video_clips = []
    for segment, duration in zip(selected_segments, durations):
        path = segment.get("path")
        start = float(segment.get("start", 0.0))
        end = float(segment.get("end", start + duration))

        if not os.path.exists(path):
            logger.warning("Missing segment source file: %s", path)
            continue

        clip = VideoFileClip(path)
        actual_end = min(end, clip.duration)
        if actual_end <= start:
            clip.close()
            continue

        trimmed = clip.subclip(start, actual_end)
        if trimmed.duration > duration:
            trimmed = trimmed.subclip(0, duration)
        if trimmed.duration <= 0:
            clip.close()
            continue

        video_clips.append(trimmed)

    if not video_clips:
        raise ValueError("No valid clip segments were available for editing.")

    output_clips = []
    for idx, clip in enumerate(video_clips):
        if idx > 0:
            clip = clip.crossfadein(0.12)
        output_clips.append(clip)

    final_clip = concatenate_videoclips(output_clips, method="compose")
    logger.info("Rendering final montage to %s", output_path)

    try:
        final_clip.write_videofile(
            output_path,
            codec="libx264",
            audio_codec="aac",
            threads=4,
            verbose=False,
            logger=None,
        )
    finally:
        final_clip.close()
        for clip in video_clips:
            try:
                clip.close()
            except Exception:
                pass
