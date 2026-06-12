import cv2
import numpy as np
import os
import subprocess
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

def is_gameplay(frame):
    """Returns True if frame is actual Free Fire gameplay"""
    try:
        h, w = frame.shape[:2]
        # Skip if mostly white (menu/start screen)
        if frame.mean() > 215:
            return False
        # Skip if completely black
        if frame.mean() < 8:
            return False
        # Skip Windows taskbar (very dark bottom strip)
        bottom = frame[int(h*0.93):h, :]
        if 15 < bottom.mean() < 58 and bottom.std() < 18:
            return False
        # Skip white menus (Windows start menu)
        center = frame[int(h*0.2):int(h*0.8), int(w*0.2):int(w*0.8)]
        white_ratio = (center > 205).all(axis=2).mean()
        if white_ratio > 0.25:
            return False
        # Skip solid color screens
        if center.std() < 8:
            return False
        return True
    except:
        return True

def select_clips(footage_folder, style_profile):
    # Find video file
    video_path = None
    for ext in ["*.mp4","*.avi","*.mov","*.mkv"]:
        files = list(Path(footage_folder).glob(ext))
        files = [f for f in files if f.stat().st_size > 50000]
        if files:
            video_path = str(max(files, key=lambda f: f.stat().st_size))
            break

    if not video_path:
        print("[KILLFRAME] [ERROR] No footage found in folder")
        return []

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"[KILLFRAME] [ERROR] Cannot open: {video_path}")
        return []

    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps
    duration_min = duration / 60

    print(f"[KILLFRAME] ----------------------------------")
    print(f"[KILLFRAME]   KILL SCANNER")
    print(f"[KILLFRAME]   File     : {Path(video_path).name}")
    print(f"[KILLFRAME]   Duration : {duration_min:.1f} minutes")
    print(f"[KILLFRAME]   Frames   : {total_frames}")
    print(f"[KILLFRAME]   FPS      : {fps:.0f}")
    print(f"[KILLFRAME] ----------------------------------")

    # Adaptive frame skip based on duration
    if duration < 120:
        skip = 6
    elif duration < 300:
        skip = 8
    else:
        skip = 10

    all_scores = []
    frame_idx = 0
    prev_frame = None
    prev_gray = None
    last_progress = -1

    print("[KILLFRAME] Scanning footage...")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % skip != 0:
            frame_idx += 1
            continue

        timestamp = frame_idx / fps

        # Show real progress
        progress = int((frame_idx / max(total_frames,1)) * 100)
        if progress % 5 == 0 and progress != last_progress:
            kills_found = len([s for _,s in all_scores if s > 25])
            print(f"[KILLFRAME] {progress:3d}% | {timestamp/60:.1f}min | Kills: {kills_found}")
            last_progress = progress

        # Skip first 15 seconds and non-gameplay
        if timestamp < 15:
            frame_idx += 1
            continue
        if not is_gameplay(frame):
            frame_idx += 1
            continue

        h, w = frame.shape[:2]
        score = 0.0
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # SIGNAL 1: Kill feed red pixels top-right
        try:
            kz = frame[0:int(h*0.14), int(w*0.70):w]
            red = ((kz[:,:,2].astype(int)-kz[:,:,0].astype(int)>80) & (kz[:,:,2]>130)).sum()
            kf_score = (red / max(kz.shape[0]*kz.shape[1],1)) * 400
            score += kf_score
            if kf_score > 8:
                score *= 1.8
        except:
            pass

        # SIGNAL 2: Screen flash
        brightness = float(frame.mean())
        score += max(0, brightness - 148) * 3.5

        # SIGNAL 3: Frame motion
        if prev_frame is not None:
            try:
                diff = cv2.absdiff(frame, prev_frame).mean()
                score += diff * 2.5
            except:
                pass

        # SIGNAL 4: Optical flow
        if prev_gray is not None:
            try:
                flow = cv2.calcOpticalFlowFarneback(
                    prev_gray, gray, None, 0.5, 3, 15, 3, 5, 1.2, 0
                )
                score += np.sqrt(flow[...,0]**2+flow[...,1]**2).mean() * 3.5
            except:
                pass

        # SIGNAL 5: Gun recoil
        if prev_frame is not None:
            try:
                gz = frame[int(h*0.5):h, int(w*0.2):int(w*0.8)]
                pgz = prev_frame[int(h*0.5):h, int(w*0.2):int(w*0.8)]
                score += cv2.absdiff(gz, pgz).mean() * 2.0
            except:
                pass

        # SIGNAL 6: Enemy contours
        try:
            edges = cv2.Canny(gray, 45, 140)
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            big = [c for c in contours if 1200 < cv2.contourArea(c) < 60000]
            score += min(60.0, len(big)*5.0)
        except:
            pass

        # SIGNAL 7: Red hit effect center
        try:
            cz = frame[int(h*0.25):int(h*0.75), int(w*0.25):int(w*0.75)]
            rh = ((cz[:,:,2].astype(int)-cz[:,:,0].astype(int)>100) & (cz[:,:,2]>150)).sum()
            score += (rh / max(cz.shape[0]*cz.shape[1],1)) * 200
        except:
            pass

        all_scores.append((timestamp, float(score)))
        prev_frame = frame.copy()
        prev_gray = gray.copy()
        frame_idx += 1

    cap.release()

    if not all_scores:
        print("[KILLFRAME] [ERROR] No frames analyzed")
        return []

    scores_only = [s for _,s in all_scores]
    print(f"\n[KILLFRAME] Scan complete: {len(all_scores)} frames")
    print(f"[KILLFRAME] Score range: {min(scores_only):.1f} — {max(scores_only):.1f}")

    # Calculate clips needed based on output duration
    output_duration = int(style_profile.get("output_duration", 60))
    clip_len = float(style_profile.get("recommended_clip_length", 2.5))
    clips_needed = max(15, int(output_duration / clip_len))
    print(f"[KILLFRAME] Need {clips_needed} clips for {output_duration}s output")

    # Adaptive threshold — keep lowering until enough clips found
    percentile = 82
    merged = []
    for attempt in range(6):
        threshold = np.percentile(scores_only, percentile)
        kills = [(t,s) for t,s in all_scores if s >= threshold]
        merged = []
        for ts, sc in sorted(kills, key=lambda x: x[0]):
            if not merged or ts - merged[-1][0] > 1.8:
                merged.append([ts, sc])
            elif sc > merged[-1][1]:
                merged[-1] = [ts, sc]
        print(f"[KILLFRAME] Threshold {threshold:.1f} (p{percentile}) -> {len(merged)} kills")
        if len(merged) >= clips_needed:
            break
        percentile -= 8

    if not merged:
        print("[KILLFRAME] Using evenly spaced segments as fallback")
        merged = [(i*(duration/20), 1.0) for i in range(1, 21) if i*(duration/20) < duration]

    # Sort by score — best kills first
    merged.sort(key=lambda x: x[1], reverse=True)
    selected = merged[:clips_needed]
    selected_times = sorted([t for t,_ in selected])

    print(f"[KILLFRAME] Selected {len(selected_times)} kill moments")

    # Extract clips
    os.makedirs("temp/kills", exist_ok=True)
    for old in Path("temp/kills").glob("*.mp4"):
        old.unlink()

    output_clips = []
    print(f"[KILLFRAME] Extracting {len(selected_times)} clips...")

    for i, ts in enumerate(selected_times):
        kill_offset = 1.0
        clip_start = max(0.0, ts - kill_offset)
        clip_duration = kill_offset + 2.5
        out = f"temp/kills/kill_{i:03d}.mp4"

        success = False
        cmds = [
            f'ffmpeg -hwaccel cuda -ss {clip_start:.3f} -i "{video_path}" -t {clip_duration:.3f} -c:v h264_nvenc -b:v 8000k -c:a aac "{out}" -y -loglevel quiet',
            f'ffmpeg -ss {clip_start:.3f} -i "{video_path}" -t {clip_duration:.3f} -c:v libx264 -preset ultrafast -b:v 6000k -c:a aac "{out}" -y -loglevel quiet',
            f'ffmpeg -ss {clip_start:.3f} -i "{video_path}" -t {clip_duration:.3f} -c copy "{out}" -y -loglevel quiet',
        ]
        for cmd in cmds:
            result = os.system(cmd)
            if result == 0 and os.path.exists(out) and os.path.getsize(out) > 5000:
                cap_check = cv2.VideoCapture(out)
                ret, f = cap_check.read()
                cap_check.release()
                if ret and f is not None and f.mean() > 5:
                    output_clips.append({
                        "path": out,
                        "kill_offset": kill_offset,
                        "timestamp": ts,
                        "score": next((s for t,s in selected if abs(t-ts)<0.5), 0)
                    })
                    print(f"[KILLFRAME] [OK] Kill {i+1:03d}/{len(selected_times)} | {ts:.1f}s")
                    success = True
                    break
        if not success:
            print(f"[KILLFRAME] [ERROR] Failed: {ts:.1f}s")

    if output_clips:
        try:
            from modules.validator import validate_clips
            output_clips = validate_clips(output_clips)
        except Exception as e:
            print(f"[KILLFRAME] Clip validation warning: {e}")

    print(f"[KILLFRAME] ----------------------------------")
    print(f"[KILLFRAME]   Kills detected  : {len(merged)}")
    print(f"[KILLFRAME]   Clips extracted : {len(output_clips)}")
    print(f"[KILLFRAME] ----------------------------------")
    return output_clips
