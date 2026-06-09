import os
from moviepy.editor import VideoFileClip, concatenate_videoclips


def edit_video(clips, beat_timeline, output_path, style_profile):
    if not clips:
        raise ValueError("No clips were provided for editing.")

    recommended_length = float(style_profile.get("recommended_clip_length", 2.5))
    trimmed_clips = []

    for clip_path in clips:
        if not os.path.exists(clip_path):
            continue

        clip = VideoFileClip(clip_path)
        duration = min(clip.duration, recommended_length)
        if duration <= 0:
            clip.close()
            continue

        trimmed_clips.append(clip.subclip(0, duration))

    if not trimmed_clips:
        raise ValueError("No valid video clips could be trimmed.")

    final_clip = concatenate_videoclips(trimmed_clips, method="compose")
    try:
        final_clip.write_videofile(
            output_path,
            codec="libx264",
            audio_codec="aac",
            threads=4,
            verbose=False,
            logger=None,
        )
    except Exception as exc:
        print(f"[KILLFRAME] Video export failed: {exc}")
        raise
    finally:
        final_clip.close()
        for clip in trimmed_clips:
            clip.close()
