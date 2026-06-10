import os
import cv2
import numpy as np
import logging
from moviepy.editor import VideoFileClip, AudioFileClip, ColorClip, concatenate_videoclips, CompositeVideoClip, TextClip, ImageClip
from moviepy.audio.AudioClip import concatenate_audioclips
import moviepy.video.fx.all as vfx
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def cinematic_grade(frame, style):
    f = frame.astype(np.float32)
    # Contrast S-curve
    f = np.clip((f/255.0)**0.9 * 255, 0, 255)
    # Contrast boost
    f = np.clip((f - 128) * style.get("contrast_level", 1.35) + 128, 0, 255)
    
    # Saturation / Color Pop
    hsv = cv2.cvtColor(f.astype(np.uint8), cv2.COLOR_RGB2HSV).astype(np.float32)
    if style.get("color_grade") == "desaturated_pop":
        # Desaturate but keep red pop (HSV red ranges)
        mask_r1 = cv2.inRange(hsv, np.array([0, 100, 100]), np.array([12, 255, 255]))
        mask_r2 = cv2.inRange(hsv, np.array([165, 100, 100]), np.array([180, 255, 255]))
        mask_red = mask_r1 | mask_r2
        hsv[:,:,1] = np.where(mask_red > 0, hsv[:,:,1] * 1.5, hsv[:,:,1] * 0.25)
    else:
        hsv[:,:,1] = hsv[:,:,1] * style.get("saturation_level", 1.45)
    
    hsv[:,:,1] = np.clip(hsv[:,:,1], 0, 255)
    f = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2RGB).astype(np.float32)
    
    # Shadow lift
    f = np.clip(f * 0.94 + 10, 0, 255)
    
    # Vignette
    if style.get("uses_vignette", True):
        h, w = f.shape[:2]
        Y, X = np.ogrid[:h, :w]
        v = 1 - 0.5*(((X-w/2)**2+(Y-h/2)**2)/((w/2)**2+(h/2)**2))
        f = (f * np.clip(v, 0.5, 1)[:,:,np.newaxis])
        
    # Letterbox black bars
    if style.get("letterbox", False):
        h, w = f.shape[:2]
        bar_h = int(h * 0.1)
        f[0:bar_h, :] = 0
        f[h-bar_h:h, :] = 0
        
    return f.astype(np.uint8)

def chromatic_aberration(frame, intensity=2):
    r, g, b = cv2.split(frame)
    rows, cols = frame.shape[:2]
    M_r = np.float32([[1, 0, intensity], [0, 1, 0]])
    M_b = np.float32([[1, 0, -intensity], [0, 1, 0]])
    r = cv2.warpAffine(r, M_r, (cols, rows))
    b = cv2.warpAffine(b, M_b, (cols, rows))
    return cv2.merge([r, g, b])

def glitch_frame(frame):
    result = frame.copy()
    for _ in range(3):
        y = np.random.randint(0, frame.shape[0]-20)
        h = np.random.randint(2, 15)
        offset = np.random.randint(-20, 20)
        result[y:y+h] = np.roll(result[y:y+h], offset, axis=1)
    return result

def camera_shake(clip, intensity=4):
    def shake(get_frame, t):
        frame = get_frame(t)
        dx = int(np.random.uniform(-intensity, intensity))
        dy = int(np.random.uniform(-intensity, intensity))
        M = np.float32([[1, 0, dx], [0, 1, dy]])
        return cv2.warpAffine(frame, M, (frame.shape[1], frame.shape[0]))
    return clip.fl(shake)

def zoom_pulse(clip, zoom=1.06):
    def zoom_frame(get_frame, t):
        frame = get_frame(t)
        progress = t / clip.duration
        scale = 1.0 + (zoom - 1.0) * (1.0 - progress)
        h, w = frame.shape[:2]
        new_h, new_w = int(h*scale), int(w*scale)
        resized = cv2.resize(frame, (new_w, new_h))
        y1 = (new_h - h) // 2
        x1 = (new_w - w) // 2
        return resized[y1:y1+h, x1:x1+w]
    return clip.fl(zoom_frame)

def speed_ramp(clip):
    slow = clip.subclip(0, min(0.4, clip.duration*0.3)).fx(vfx.speedx, 0.4)
    fast = clip.subclip(min(0.4, clip.duration*0.3)).fx(vfx.speedx, 1.4)
    return concatenate_videoclips([slow, fast])

def draw_text_safe(frame, text, org, font, font_scale, color, thickness, line_type=cv2.LINE_AA):
    is_float = frame.dtype == np.float32 or frame.dtype == np.float64 or (frame.max() <= 1.01 and frame.dtype != np.uint8)
    if is_float:
        frame_uint8 = np.ascontiguousarray((frame * 255.0).clip(0, 255).astype(np.uint8))
    else:
        frame_uint8 = np.ascontiguousarray(frame.copy().astype(np.uint8))
    cv2.putText(frame_uint8, text, org, font, font_scale, color, thickness, line_type)
    if is_float:
        return frame_uint8.astype(np.float32) / 255.0
    else:
        return frame_uint8

def add_kill_text_opencv(clip, kill_num):
    text = f"KILL {kill_num}"
    
    def draw_text(get_frame, t):
        frame = get_frame(t)
        if t <= 0.9:
            h, w = frame.shape[:2]
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 1.9
            thickness_outline = 7
            thickness_text = 3
            text_size = cv2.getTextSize(text, font, font_scale, thickness_outline)[0]
            
            margin_x = 40
            margin_y = 60
            x = w - text_size[0] - margin_x
            y = text_size[1] + margin_y
            
            # Red outline
            frame = draw_text_safe(frame, text, (x, y), font, font_scale, (0, 0, 255), thickness_outline)
            # White text
            frame = draw_text_safe(frame, text, (x, y), font, font_scale, (255, 255, 255), thickness_text)
        return frame
        
    return clip.fl(draw_text)

def get_intro_clip_opencv():
    black_clip = ColorClip((1920, 1080), [0, 0, 0], duration=0.5)
    
    def draw_intro(get_frame, t):
        frame = get_frame(t)
        text = "KILLFRAME-AGENT"
        h, w = frame.shape[:2]
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 2.8
        thickness = 6
        text_size = cv2.getTextSize(text, font, font_scale, thickness)[0]
        x = (w - text_size[0]) // 2
        y = (h + text_size[1]) // 2
        # #ff4444 red is BGR (68, 68, 255)
        return draw_text_safe(frame, text, (x, y), font, font_scale, (68, 68, 255), thickness)
        
    return black_clip.fl(draw_intro)

def get_outro_clip_opencv(last_clip):
    last_frame = last_clip.get_frame(last_clip.duration - 0.1)
    freeze = ImageClip(last_frame).set_duration(1.5)
    
    def draw_outro(get_frame, t):
        frame = get_frame(t)
        text = "MADE WITH KILLFRAME-AGENT"
        h, w = frame.shape[:2]
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 1.5
        thickness = 3
        text_size = cv2.getTextSize(text, font, font_scale, thickness)[0]
        x = (w - text_size[0]) // 2
        y = h - 60
        return draw_text_safe(frame, text, (x, y), font, font_scale, (255, 255, 255), thickness)
        
    return freeze.fl(draw_outro)


def edit_video(clips, beat_timeline, output_path, style_profile, music_path):
    print(f"[KILLFRAME] Loading {len(clips)} kill clips...")
    loaded_clips = []
    for i, clip_info in enumerate(clips):
        path = clip_info["path"] if isinstance(clip_info, dict) else clip_info
        print(f"[KILLFRAME] Loading clip {i+1}/{len(clips)}: {path}")
        try:
            clip = VideoFileClip(path)
            clip = clip.resize((1920, 1080))
            loaded_clips.append(clip)
        except Exception as e:
            print(f"[KILLFRAME] Skipping corrupt clip: {path} | Error: {e}")

    if not loaded_clips:
        raise ValueError("No valid clips loaded for video editing.")

    # Apply video effects per clip
    processed_clips = []
    uses_slowmo = style_profile.get("uses_slowmo", False)
    uses_zoom = style_profile.get("uses_zoom", False)
    uses_shake = style_profile.get("uses_shake", False)
    uses_glitch = style_profile.get("uses_glitch", False)
    uses_chromatic = style_profile.get("uses_chromatic", False)

    for clip in loaded_clips:
        # EFFECT 1 — Advanced color grading
        c = clip.fl_image(lambda f: cinematic_grade(f, style_profile))

        # EFFECT 2 — Chromatic aberration
        if uses_chromatic:
            c = c.fl_image(lambda f: chromatic_aberration(f, intensity=2))

        # EFFECT 3 — Glitch
        if uses_glitch:
            c = c.fl_image(glitch_frame)

        # EFFECT 6 — Speed ramp
        if uses_slowmo:
            c = speed_ramp(c)

        # EFFECT 5 — Zoom pulse
        if uses_zoom:
            c = zoom_pulse(c, zoom=1.0 + style_profile.get("zoom_intensity", 0.06))

        # EFFECT 4 — Camera shake
        if uses_shake:
            c = camera_shake(c, intensity=int(style_profile.get("shake_intensity", 0.04) * 100))

        processed_clips.append(c)

    # Step: Beat drop sync logic
    drops = beat_timeline.get("bass_drops", [])
    strong = beat_timeline.get("strong_beats", [])
    regular = beat_timeline.get("timestamps", [])
    
    # Sort and remove duplicates
    priority_beats = sorted(list(set(drops + strong + regular)))

    synced_clips = []
    for i, clip in enumerate(processed_clips):
        if i < len(priority_beats):
            beat = priority_beats[i]
            if i + 1 < len(priority_beats):
                dur = priority_beats[i+1] - beat
            else:
                dur = 3.0
            type_label = "DROP" if beat in drops else "BEAT"
        else:
            beat = i * style_profile.get("recommended_clip_length", 2.5)
            dur = 3.0
            type_label = "BEAT"

        dur = max(1.0, min(dur, 4.0))
        clip = clip.subclip(0, min(dur, clip.duration)).set_duration(dur)
        # Shift start by 0.5s for intro sequence
        clip = clip.set_start(beat + 0.5)
        synced_clips.append(clip)
        print(f"[KILLFRAME] Clip {i+1} → beat {beat:.2f}s ({type_label})")

    # EFFECT 8 — Kill counter with animation overlays
    overlay_clips = []
    for i, clip in enumerate(synced_clips):
        try:
            kill_text = TextClip(
                f"💀 KILL {i+1}",
                fontsize=52,
                color="white",
                font="Impact",
                stroke_color="#ff0000",
                stroke_width=3
            ).set_position(("right", "top")).set_start(clip.start).set_duration(0.9).set_opacity(0.95)
            overlay_clips.append(CompositeVideoClip([clip, kill_text]))
        except Exception:
            # Fallback to OpenCV
            overlay_clips.append(add_kill_text_opencv(clip, i+1))

    # EFFECT 7 — Multiple transitions
    transition_style = style_profile.get("transition_style", "hard_cut")
    overlay_transitions = []
    for i in range(1, len(overlay_clips)):
        # Transition starts at the clip's start time
        beat_start = overlay_clips[i].start
        
        if transition_style == "flash":
            flash = ColorClip((1920, 1080), [255, 255, 255], duration=0.05).set_start(beat_start)
            overlay_transitions.append(flash)
        elif transition_style == "glitch":
            glitch_trans = ColorClip((1920, 1080), [255, 0, 0], duration=0.04).set_start(beat_start)
            overlay_transitions.append(glitch_trans)
        elif transition_style == "black":
            black_trans = ColorClip((1920, 1080), [0, 0, 0], duration=0.06).set_start(beat_start)
            overlay_transitions.append(black_trans)

    # EFFECT 9 — Intro sequence
    try:
        intro = ColorClip((1920, 1080), [0, 0, 0], duration=0.5)
        intro_text = TextClip(
            "KILLFRAME-AGENT",
            fontsize=80,
            color="#ff4444",
            font="Impact"
        ).set_position("center").set_duration(0.5)
        intro_clip = CompositeVideoClip([intro, intro_text])
    except Exception:
        # Fallback to OpenCV
        intro_clip = get_intro_clip_opencv()

    # EFFECT 10 — Outro with freeze frame
    # Outro starts at the end of the last synced clip
    outro_start = overlay_clips[-1].start + overlay_clips[-1].duration
    try:
        last_clip_processed = processed_clips[-1]
        freeze = last_clip_processed.to_ImageClip(t=last_clip_processed.duration-0.1).set_duration(1.5)
        outro_text = TextClip(
            "MADE WITH KILLFRAME-AGENT",
            fontsize=36,
            color="white",
            font="Impact"
        ).set_position(("center", "bottom")).set_duration(1.5).set_opacity(0.7)
        outro_clip = CompositeVideoClip([freeze, outro_text]).set_start(outro_start)
    except Exception:
        outro_clip = get_outro_clip_opencv(processed_clips[-1]).set_start(outro_start)

    # Total duration of the composition
    total_duration = outro_start + 1.5

    # Compile the final composition using CompositeVideoClip
    final_video = CompositeVideoClip(
        [intro_clip] + overlay_clips + overlay_transitions + [outro_clip],
        size=(1920, 1080)
    ).set_duration(total_duration)

    # Add background music
    audio = None
    if music_path and os.path.exists(music_path):
        audio = AudioFileClip(music_path)
        if audio.duration < final_video.duration:
            loops = int(final_video.duration / audio.duration) + 1
            audio = concatenate_audioclips([audio] * loops)
        audio = audio.subclip(0, final_video.duration).volumex(0.85)
        final_video = final_video.set_audio(audio)

    # Export at 60fps and 10000k bitrate
    final_video.write_videofile(
        output_path,
        codec="libx264",
        audio_codec="aac",
        bitrate="10000k",
        fps=60,
        threads=8,
        preset="fast",
        ffmpeg_params=["-crf", "18", "-movflags", "+faststart"],
        logger=None
    )

    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    drops_synced = sum(1 for i in range(len(overlay_clips)) if i < len(priority_beats) and priority_beats[i] in drops)

    # Print summary
    print("[KILLFRAME] ════════════════════════════════════════")
    print("[KILLFRAME]   WORLD BEST MONTAGE — RENDER COMPLETE")
    print("[KILLFRAME] ════════════════════════════════════════")
    print(f"[KILLFRAME] Clips used        : {len(loaded_clips)}")
    print(f"[KILLFRAME] Total duration    : {final_video.duration:.1f} seconds")
    print(f"[KILLFRAME] File size         : {size_mb:.1f} MB")
    print("[KILLFRAME] Resolution        : 1920x1080 @ 60fps")
    print("[KILLFRAME] Bitrate           : 10000k")
    print("[KILLFRAME] Color graded      : YES — Cinematic")
    print(f"[KILLFRAME] Chromatic         : {'YES' if uses_chromatic else 'NO'}")
    print(f"[KILLFRAME] Glitch effects    : {'YES' if uses_glitch else 'NO'}")
    print(f"[KILLFRAME] Camera shake      : {'YES' if uses_shake else 'NO'}")
    print(f"[KILLFRAME] Speed ramps       : {'YES' if uses_slowmo else 'NO'}")
    print(f"[KILLFRAME] Beat drops synced : {drops_synced} drops")
    print("[KILLFRAME] Kill overlays     : YES")
    print("[KILLFRAME] Intro             : YES")
    print("[KILLFRAME] Outro             : YES")
    print(f"[KILLFRAME] Music             : {'YES' if audio else 'NO'}")
    print("[KILLFRAME] ════════════════════════════════════════")

    # Cleanup
    try:
        final_video.close()
        if audio:
            audio.close()
        for c in loaded_clips:
            c.close()
    except Exception:
        pass
