import os
import cv2
import numpy as np
from moviepy.editor import VideoFileClip, AudioFileClip, ColorClip, concatenate_videoclips
from moviepy.audio.AudioClip import concatenate_audioclips
import moviepy.video.fx.all as vfx

def edit_video(clips, beat_timeline, output_path, style_profile, music_path):
    # STEP 1 — Load and validate clips
    print(f"[KILLFRAME] Loading {len(clips)} kill clips...")
    loaded_clips = []
    for i, clip_path in enumerate(clips):
        try:
            clip = VideoFileClip(clip_path)
            # Resize clip to 1080p for uniform sizing
            clip = clip.resize((1920, 1080))
            print(f"[KILLFRAME] Loaded clip {i+1}/{len(clips)}: {clip.duration:.1f}s")
            loaded_clips.append(clip)
        except Exception as e:
            print(f"[KILLFRAME] Skipping corrupt clip: {clip_path}")

    if not loaded_clips:
        raise ValueError("No valid clips loaded for video editing.")

    # STEP 2 — Professional color grading using numpy
    def apply_color_grade(clip, style_profile):
        def grade_frame(frame):
            # Increase contrast
            frame = np.clip((frame.astype(float) - 128) * 1.3 + 128, 0, 255).astype(np.uint8)
            # Increase saturation using HSV
            hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV).astype(np.float32)
            hsv[:,:,1] = np.clip(hsv[:,:,1] * 1.4, 0, 255)
            frame = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2RGB)
            # Dark vignette
            h, w = frame.shape[:2]
            Y, X = np.ogrid[:h, :w]
            cx, cy = w/2, h/2
            mask = 1 - 0.4 * ((X-cx)**2 + (Y-cy)**2) / (cx**2 + cy**2)
            mask = np.clip(mask, 0.6, 1.0)
            frame = (frame * mask[:,:,np.newaxis]).astype(np.uint8)
            return frame
        return clip.fl_image(grade_frame)

    # STEP 3 — Sync clips to beat timestamps
    print("[KILLFRAME] Syncing clips to beat drops...")
    beats = beat_timeline.get("timestamps", [])
    synced_clips = []
    
    current_time = 0.0
    for i, clip in enumerate(loaded_clips):
        clip_length = style_profile.get("recommended_clip_length", 2.5)
        
        # We want to align the end of this clip with the nearest beat timestamp.
        # Speed up factor is 1.1x, so duration is raw_duration / 1.1.
        nominal_duration = min(clip_length, clip.duration) / 1.1
        nominal_end = current_time + nominal_duration
        
        candidate_beats = [b for b in beats if b > current_time + 0.5]
        if candidate_beats:
            nearest_beat = min(candidate_beats, key=lambda b: abs(b - nominal_end))
            target_duration = nearest_beat - current_time
            # Determine the raw subclip duration needed (which is target_duration * 1.1)
            raw_duration = target_duration * 1.1
            clip = clip.subclip(0, min(raw_duration, clip.duration))
            current_time = nearest_beat
        else:
            clip = clip.subclip(0, min(clip_length, clip.duration))
            current_time += clip.duration / 1.1

        # Speed up slightly
        clip = clip.fx(vfx.speedx, 1.1)
        # Apply color grade
        clip = apply_color_grade(clip, style_profile)
        synced_clips.append(clip)
        print(f"[KILLFRAME] Processed clip {i+1}/{len(loaded_clips)}")

    # STEP 4 — Add white flash transitions
    def create_flash(duration=0.06):
        return ColorClip(size=(1920,1080), color=[255,255,255], duration=duration)

    final_clips = []
    for i, clip in enumerate(synced_clips):
        final_clips.append(clip)
        if i < len(synced_clips) - 1:
            final_clips.append(create_flash())

    # STEP 5 — Add music properly
    print("[KILLFRAME] Adding music...")
    final_video = concatenate_videoclips(final_clips, method="compose")
    audio = None
    if music_path and os.path.exists(music_path):
        audio = AudioFileClip(music_path)
        if audio.duration < final_video.duration:
            loops = int(final_video.duration / audio.duration) + 1
            audio = concatenate_audioclips([audio] * loops)
        audio = audio.subclip(0, final_video.duration)
        audio = audio.volumex(0.85)
        final_video = final_video.set_audio(audio)
        print(f"[KILLFRAME] Music added: {music_path}")
    else:
        print("[KILLFRAME] Warning: No music file found")

    # STEP 6 — Export with progress
    print(f"[KILLFRAME] Exporting montage to {output_path}...")
    print(f"[KILLFRAME] Duration: {final_video.duration:.1f}s | Clips: {len(loaded_clips)}")
    
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    final_video.write_videofile(
        output_path,
        codec="libx264",
        audio_codec="aac",
        bitrate="8000k",
        fps=30,
        logger=None,
        threads=4
    )
    file_size = os.path.getsize(output_path) / (1024*1024)
    print(f"[KILLFRAME] Export complete!")
    print(f"[KILLFRAME] Output: {output_path} ({file_size:.1f} MB)")

    # Clean up resources
    final_video.close()
    if audio:
        audio.close()
    for c in loaded_clips:
        try:
            c.close()
        except Exception:
            pass
