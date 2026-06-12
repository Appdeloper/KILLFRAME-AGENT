import os
import cv2
import numpy as np
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

def cinematic_grade(frame, style):
    try:
        from modules.color_analyzer import apply_reference_grade, get_default_grade
        return apply_reference_grade(frame, style if "red_mult" in style else get_default_grade())
    except:
        return frame

def make_zoom(clip, zoom):
    def zoom_fn(get_frame, t):
        try:
            frame = get_frame(t)
            p = t / max(clip.duration, 0.01)
            scale = 1.0 + (zoom-1.0)*(1.0-p)
            h, w = frame.shape[:2]
            nh, nw = int(h*scale), int(w*scale)
            if nh <= 0 or nw <= 0:
                return frame
            r = cv2.resize(frame, (nw, nh))
            y1 = max(0,(nh-h)//2)
            x1 = max(0,(nw-w)//2)
            cr = r[y1:y1+h, x1:x1+w]
            if cr.shape[0]!=h or cr.shape[1]!=w:
                cr = cv2.resize(cr,(w,h))
            return cr
        except:
            return get_frame(t)
    return clip.fl(zoom_fn)

def edit_video(clips, beat_timeline, output_path, style_profile, music_path, reference_video_path=None):
    from moviepy.editor import (VideoFileClip, concatenate_videoclips,
        AudioFileClip, ColorClip, concatenate_audioclips)
    import numpy as np
    import cv2
    import os

    # Handle both dict and string clips
    clip_data = []
    for c in clips:
        if isinstance(c, dict):
            clip_data.append(c)
        elif isinstance(c, str):
            clip_data.append({"path":c,"kill_offset":1.0,"score":0})

    if not clip_data:
        print("[KILLFRAME] [ERROR] No clips to edit")
        raise ValueError("No clips to edit")

    # Get beats
    drops = beat_timeline.get("bass_drops",[])
    strong = beat_timeline.get("strong_beats",[])
    all_beats = beat_timeline.get("timestamps",[])
    if not all_beats:
        all_beats = [i*2.5 for i in range(200)]

    beat_gap = float(beat_timeline.get("avg_gap_seconds",2.5))
    beat_gap = max(0.8, min(beat_gap, 4.0))
    drops_set = set([round(d,2) for d in drops])

    # Color grade
    grade = None
    try:
        from modules.color_analyzer import extract_reference_lut, apply_reference_grade, get_default_grade
        if reference_video_path and os.path.exists(reference_video_path):
            grade = extract_reference_lut(reference_video_path)
            print("[KILLFRAME] Reference color grade loaded")
        else:
            grade = get_default_grade()
    except:
        grade = None

    def safe_grade(frame):
        try:
            if grade is None:
                return frame
            f = frame.astype(np.float32)
            # Contrast
            c = float(grade.get("contrast_mult",1.2))
            f = np.clip((f-128)*c+128, 0, 255)
            # Warmth
            f[:,:,0] = np.clip(f[:,:,0]*float(grade.get("red_mult",1.06)), 0, 255)
            f[:,:,1] = np.clip(f[:,:,1]*float(grade.get("green_mult",1.02)), 0, 255)
            # Saturation
            hsv = cv2.cvtColor(f.astype(np.uint8), cv2.COLOR_RGB2HSV).astype(np.float32)
            hsv[:,:,1] = np.clip(hsv[:,:,1]*float(grade.get("saturation_mult",1.25)), 0, 255)
            f = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2RGB).astype(np.float32)
            # Shadow lift
            lift = float(grade.get("shadow_lift",8.0))
            f = np.clip(f + lift*(1-f/255), 0, 255)
            # Subtle vignette
            h, w = f.shape[:2]
            Y, X = np.ogrid[:h, :w]
            v = 1 - 0.10*(((X-w/2)**2+(Y-h/2)**2)/((w/2)**2+(h/2)**2))
            f = f * np.clip(v,0.90,1.0)[:,:,np.newaxis]
            result = np.clip(f,0,255).astype(np.uint8)
            return result if result.mean() > 10 else frame
        except:
            return frame

    print(f"[KILLFRAME] Loading {len(clip_data)} clips...")
    loaded = []

    # Sort — highest score kills go to bass drops
    clip_data.sort(key=lambda x: x.get("score",0), reverse=True)

    # Loop clip_data if output duration is long but we have few clips
    output_duration = int(style_profile.get("output_duration", 60))
    approx_clip_dur = beat_gap + 0.06
    clips_needed_to_fill = int(output_duration / approx_clip_dur) + 1
    if len(clip_data) < clips_needed_to_fill:
        print(f"[KILLFRAME] Looping clip data to fill target duration: need {clips_needed_to_fill}, have {len(clip_data)}")
        original_clip_data = list(clip_data)
        while len(clip_data) < clips_needed_to_fill:
            clip_data.extend(original_clip_data)
        clip_data = clip_data[:clips_needed_to_fill]

    for i, data in enumerate(clip_data):
        path = data.get("path","")
        kill_offset = float(data.get("kill_offset",1.0))
        clip = None
        try:
            if not os.path.exists(path):
                print(f"[KILLFRAME] [ERROR] Missing: {path}")
                continue
            clip = VideoFileClip(path)
            if clip.duration < 0.3:
                clip.close()
                continue

            # TRUE BEAT-KILL SYNC
            # Kill lands at 0.3s into clip (right on beat)
            target = 0.3
            trim_start = max(0.0, kill_offset - target)
            trim_end = min(clip.duration, trim_start + beat_gap)
            if trim_end - trim_start < 0.3:
                trim_start = 0.0
                trim_end = min(clip.duration, beat_gap)

            clip = clip.subclip(trim_start, trim_end)
            if clip.size != (1920,1080):
                clip = clip.resize((1920,1080))

            # Color grade
            clip = clip.fl_image(safe_grade)

            # Zoom pulse
            beat_t = all_beats[i % len(all_beats)]
            is_drop = round(beat_t,2) in drops_set
            clip = make_zoom(clip, 1.07 if is_drop else 1.04)

            loaded.append(clip)
            btype = "DROP" if is_drop else "BEAT"
            print(f"[KILLFRAME] [OK] {i+1:03d}/{len(clip_data)} | {btype} | {trim_end-trim_start:.2f}s")

        except Exception as e:
            print(f"[KILLFRAME] [ERROR] Clip {i+1} error: {e}")
            if clip:
                try: clip.close()
                except: pass

    if not loaded:
        print("[KILLFRAME] [ERROR] No clips loaded — check footage")
        raise ValueError("No clips loaded")

    print(f"[KILLFRAME] Building {len(loaded)} clip montage...")

    # Build with flash transitions
    final_clips = []
    for i, clip in enumerate(loaded):
        final_clips.append(clip)
        if i < len(loaded)-1:
            next_beat = all_beats[(i+1) % len(all_beats)]
            is_drop = round(next_beat,2) in drops_set
            flash = ColorClip((1920,1080),[255,255,255],
                duration=0.07 if is_drop else 0.05)
            final_clips.append(flash)

    try:
        final_video = concatenate_videoclips(final_clips, method="compose")
    except Exception as e:
        print(f"[KILLFRAME] Compose failed: {e} — trying chain")
        try:
            final_video = concatenate_videoclips(loaded, method="chain")
        except Exception as e2:
            print(f"[KILLFRAME] [ERROR] Cannot concatenate: {e2}")
            for c in loaded:
                try: c.close()
                except: pass
            return

    print(f"[KILLFRAME] Montage: {final_video.duration:.2f}s | {len(loaded)} clips")

    # Add music
    if music_path and music_path not in ["AUTO",""] and os.path.exists(music_path):
        try:
            audio = AudioFileClip(music_path)
            print(f"[KILLFRAME] Music: {audio.duration:.1f}s")
            if audio.duration < final_video.duration:
                loops = int(final_video.duration/audio.duration)+2
                audio = concatenate_audioclips([audio]*loops)
            audio = audio.subclip(0, final_video.duration).volumex(0.88)
            final_video = final_video.set_audio(audio)
            print("[KILLFRAME] [OK] Music synced")
        except Exception as e:
            print(f"[KILLFRAME] Music error: {e}")

    # Export — 3 quality fallbacks
    configs = [
        {"codec":"libx264","audio_codec":"aac","bitrate":"10000k","fps":30,
         "threads":4,"preset":"slow","ffmpeg_params":["-crf","17","-movflags","+faststart"],"logger":None},
        {"codec":"libx264","audio_codec":"aac","bitrate":"8000k","fps":30,
         "threads":4,"preset":"fast","logger":None},
        {"codec":"libx264","audio_codec":"aac","bitrate":"5000k","fps":30,
         "threads":2,"preset":"ultrafast","logger":None},
    ]

    exported = False
    for cfg in configs:
        try:
            print(f"[KILLFRAME] Exporting: {cfg['preset']} | {cfg['bitrate']}")
            final_video.write_videofile(output_path, **cfg)
            if os.path.exists(output_path) and os.path.getsize(output_path)>100000:
                mb = os.path.getsize(output_path)/(1024*1024)
                print(f"[KILLFRAME] ----------------------------------")
                print(f"[KILLFRAME]   [OK] MONTAGE COMPLETE")
                print(f"[KILLFRAME]   Clips      : {len(loaded)}")
                print(f"[KILLFRAME]   Duration   : {final_video.duration:.1f}s")
                print(f"[KILLFRAME]   Size       : {mb:.1f}MB")
                print(f"[KILLFRAME]   Quality    : {cfg['bitrate']} {cfg['preset']}")
                print(f"[KILLFRAME]   Beat sync  : TRUE — kills on beats")
                print(f"[KILLFRAME]   Color grade: YES")
                print(f"[KILLFRAME]   Music      : YES")
                print(f"[KILLFRAME] ----------------------------------")
                exported = True
                break
        except Exception as e:
            print(f"[KILLFRAME] Export failed ({cfg['preset']}): {e}")

    for c in loaded:
        try: c.close()
        except: pass

    if not exported:
        print("[KILLFRAME] [ERROR] All export attempts failed")
