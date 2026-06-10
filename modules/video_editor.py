import logging
import os
import cv2
import numpy as np
from moviepy.editor import VideoFileClip, AudioFileClip, ColorClip, concatenate_videoclips

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def color_grade_frame(frame):
    # frame is a numpy RGB array
    # 1. Apply Contrast (1.3x)
    f_cont = 128.0 + 1.3 * (frame.astype(float) - 128.0)
    f_cont = np.clip(f_cont, 0, 255).astype(np.uint8)
    
    # 2. Apply Saturation (1.4x)
    hsv = cv2.cvtColor(f_cont, cv2.COLOR_RGB2HSV)
    hsv[:, :, 1] = np.clip(hsv[:, :, 1].astype(float) * 1.4, 0, 255).astype(np.uint8)
    rgb = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)
    return rgb

def edit_video(segments, beat_timeline, output_path, style_profile, music_path):
    if not isinstance(segments, list) or not segments:
        raise ValueError("segments must be a non-empty list")
    if not isinstance(beat_timeline, dict) or "beat_timestamps" not in beat_timeline:
        raise ValueError("beat_timeline must contain beat_timestamps")
    if not os.path.exists(music_path):
        raise FileNotFoundError(f"Music file not found: {music_path}")

    beat_timestamps = [float(ts) for ts in beat_timeline["beat_timestamps"]]
    if not beat_timestamps:
        raise ValueError("beat_timestamps cannot be empty")

    logger.info("Starting video editing and beat synchronization")
    
    current_time = 0.0
    final_clips = []
    
    for idx, seg in enumerate(segments):
        logger.info("Processing segment %d/%d: %s", idx + 1, len(segments), seg["path"])
        clip = VideoFileClip(seg["path"])
        
        # Resize to 1080p (1920x1080) for uniform rendering
        clip = clip.resize((1920, 1080))
        
        # Apply color grading
        clip = clip.fl_image(color_grade_frame)
        
        # Speed up clip to 1.1x
        clip = clip.speedx(1.1)
        
        # Sync each clip's end to the nearest beat timestamp
        nominal_end = current_time + clip.duration
        
        # Find the nearest beat timestamp that is strictly greater than current_time + 0.5s
        candidate_beats = [b for b in beat_timestamps if b > current_time + 0.5]
        if not candidate_beats:
            nearest_beat = nominal_end
        else:
            nearest_beat = min(candidate_beats, key=lambda b: abs(b - nominal_end))
            
        adjusted_duration = nearest_beat - current_time
        logger.info("Syncing clip duration from %.2fs to %.2fs (nearest beat: %.2fs)", 
                    clip.duration, adjusted_duration, nearest_beat)
        
        if adjusted_duration < clip.duration:
            clip = clip.subclip(0, adjusted_duration)
        elif adjusted_duration > clip.duration:
            try:
                clip = clip.loop(duration=adjusted_duration)
            except Exception:
                # If loop method fails, subclip as fallback
                pass
                
        final_clips.append(clip)
        current_time = nearest_beat
        
        # Add 0.05s white flash between clips
        if idx < len(segments) - 1:
            flash = ColorClip(size=(1920, 1080), color=(255, 255, 255), duration=0.05)
            final_clips.append(flash)
            current_time += 0.05

    total_video_duration = current_time
    logger.info("Loading background music: %s", music_path)
    music = AudioFileClip(music_path)
    music = music.volumex(0.85)
    
    # Loop music if needed
    if music.duration < total_video_duration:
        logger.info("Looping background music (music duration: %.2fs, video duration: %.2fs)", 
                    music.duration, total_video_duration)
        try:
            music = music.loop(duration=total_video_duration)
        except Exception:
            from moviepy.audio.AudioClip import concatenate_audioclips
            n_loops = int(np.ceil(total_video_duration / music.duration))
            music = concatenate_audioclips([music] * n_loops).subclip(0, total_video_duration)
    else:
        music = music.subclip(0, total_video_duration)
        
    logger.info("Concatenating clips and setting audio")
    final_video = concatenate_videoclips(final_clips, method="compose")
    final_video = final_video.set_audio(music)
    
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    logger.info("Writing final montage to %s", output_path)
    final_video.write_videofile(
        output_path,
        fps=24,
        codec="libx264",
        bitrate="8000k",
        audio_codec="aac",
        threads=4,
        preset="fast"
    )
    
    # Close resources
    final_video.close()
    music.close()
    for c in final_clips:
        c.close()
        
    logger.info("Montage generated successfully: %s", output_path)
