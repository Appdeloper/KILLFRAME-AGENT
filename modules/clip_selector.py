import logging
import os
import cv2
import numpy as np
import subprocess
import time
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def _list_video_files(footage_folder):
    if not footage_folder:
        raise ValueError("footage_folder must be a valid directory or file path")

    if os.path.isfile(footage_folder):
        return [footage_folder]

    if not os.path.isdir(footage_folder):
        raise ValueError("footage_folder must be a valid directory")

    video_files = []
    for root, _, files in os.walk(footage_folder):
        for name in files:
            if name.lower().endswith((".mp4", ".mov", ".avi", ".mkv")):
                video_files.append(os.path.join(root, name))
    return sorted(video_files)

def select_clips(footage_folder, style_profile):
    if not isinstance(style_profile, dict):
        raise ValueError("style_profile must be a dictionary")

    video_files = _list_video_files(footage_folder)
    if not video_files:
        logger.warning("No video files found in %s", footage_folder)
        return []

    video_path = video_files[0]
    os.makedirs(os.path.join("temp", "kills"), exist_ok=True)

    # Quick caching check: If temp/kills/ contains clips, we can return them immediately to avoid scanning!
    existing_kills = sorted([os.path.join("temp", "kills", f) for f in os.listdir("temp/kills") if f.endswith(".mp4")])
    if len(existing_kills) >= 8:
        print(f"[KILLFRAME] Cache hit! Found {len(existing_kills)} already extracted clips in temp/kills/. Skipping 24-minute scan.")
        return [{"path": p, "score": 100.0} for p in existing_kills]

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Could not open video: {video_path}")

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_duration = total_frames / fps
    footage_minutes = total_duration / 60.0

    print(f"[KILLFRAME] Video: {footage_minutes:.1f} min | {total_frames} frames | {int(fps)}fps")
    print(f"[KILLFRAME] Starting kill detection scan...")

    frame_scores = []
    frame_idx = 0
    prev_gray = None
    prev_gray_small = None
    prev_gun_zone = None

    t_scan_start = time.time()
    last_printed_progress = -5
    kills_found = 0
    best_score = 0.0
    running_cooldown = 0.0
    all_scores_for_estimate = []

    LOWER_RED_1 = np.array([0,   140, 140])
    UPPER_RED_1 = np.array([12,  255, 255])
    LOWER_RED_2 = np.array([165, 140, 140])
    UPPER_RED_2 = np.array([180, 255, 255])

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Process every 8th frame for speed
        if frame_idx % 8 != 0:
            frame_idx += 1
            continue

        h, w = frame.shape[:2]
        t = frame_idx / fps

        # Progress tracking every 5%
        progress_pct = int((frame_idx / total_frames) * 100)
        if progress_pct >= last_printed_progress + 5:
            progress_pct = min(100, progress_pct)
            elapsed = int(time.time() - t_scan_start)
            print(f"[KILLFRAME] Scanning: {progress_pct}% ({elapsed}s) | Kills: {kills_found} | Best score: {best_score:.1f}")
            last_printed_progress = progress_pct

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gun_zone = frame[int(h*0.5):h, int(w*0.2):int(w*0.8)]

        # Initialize references on the first processed frame
        if prev_gray is None:
            prev_gray = gray.copy()
            prev_gray_small = cv2.resize(gray, (480, 270))
            prev_gun_zone = gun_zone.copy()

        # Bad segment checks:
        # 1. Skip first 10 seconds
        if t < 10.0:
            frame_idx += 1
            continue

        # 2. Skip if center color std dev below 12 (solid screen)
        center_zone = frame[int(h*0.2):int(h*0.8), int(w*0.2):int(w*0.8)]
        if center_zone.std() < 12.0:
            frame_idx += 1
            continue

        # 3. Skip if mean color is grey (desktop/OBS)
        mean_color = center_zone.mean(axis=(0, 1))
        if max(mean_color) - min(mean_color) < 10.0 and 50.0 <= mean_color.mean() <= 170.0:
            frame_idx += 1
            continue

        # 4. Skip if top area is yellow/orange (victory/defeat banners)
        top_area = frame[0:int(h*0.20), :]
        top_hsv = cv2.cvtColor(top_area, cv2.COLOR_BGR2HSV)
        mask_yo = cv2.inRange(top_hsv, np.array([10, 100, 100]), np.array([35, 255, 255]))
        yo_ratio = mask_yo.sum() / (mask_yo.size * 255)
        if yo_ratio > 0.25:
            frame_idx += 1
            continue

        # 5. Skip if frame is mostly black (loading screen)
        if frame.mean() < 15.0:
            frame_idx += 1
            continue

        # Convert entire frame to HSV for precise checks
        hsv_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # UI Exclusion Mask creation:
        # - Minimap (top-left 15%: x < 15% and y < 15%)
        # - HP bar (bottom 20%, x < 50%)
        ui_exclusion_mask = np.zeros((h, w), dtype=np.uint8)
        ui_exclusion_mask[0:int(h*0.15), 0:int(w*0.15)] = 255
        ui_exclusion_mask[int(h*0.80):h, 0:int(w*0.50)] = 255

        # Precise Red Damage Numbers Detection (Center Zone: x: 20%-80%, y: 15%-75%)
        center_hsv = hsv_frame[int(h*0.15):int(h*0.75), int(w*0.20):int(w*0.80)]
        mask_r1 = cv2.inRange(center_hsv, LOWER_RED_1, UPPER_RED_1)
        mask_r2 = cv2.inRange(center_hsv, LOWER_RED_2, UPPER_RED_2)
        red_mask_center = mask_r1 | mask_r2

        # Exclude UI areas from the red mask if they intersect center zone
        center_ui_excl = ui_exclusion_mask[int(h*0.15):int(h*0.75), int(w*0.20):int(w*0.80)]
        red_mask_center = cv2.bitwise_and(red_mask_center, cv2.bitwise_not(center_ui_excl))

        # Find contours of red blobs in Center zone
        contours, _ = cv2.findContours(red_mask_center, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        digit_blobs = []
        headshot_blobs = []
        for c in contours:
            area = cv2.contourArea(c)
            if 15 <= area <= 900:
                digit_blobs.append(c)
            if area > 400:
                headshot_blobs.append(c)

        # Hit Score Calculation (Module 1 detection parameters)
        hit_score = 0.0
        is_hit = len(digit_blobs) >= 2
        
        if is_hit:
            hit_score += 1.0  # STANDARD_HIT
            
            # HEADSHOT_BONUS (+3.0) for large red blob > 400px area in center zone
            if len(headshot_blobs) > 0:
                hit_score += 3.0
                
            # MULTI_HIT_BONUS (+1.5) for 4+ red blobs at once
            if len(digit_blobs) >= 4:
                hit_score += 1.5

        # Kill Feed Activity Detection (top-right 25% zone: y < 0.14 * h, x > 0.70 * w)
        kill_feed_hsv = hsv_frame[0:int(h*0.14), int(w*0.70):w]
        kf_mask_r1 = cv2.inRange(kill_feed_hsv, LOWER_RED_1, UPPER_RED_1)
        kf_mask_r2 = cv2.inRange(kill_feed_hsv, LOWER_RED_2, UPPER_RED_2)
        kf_red_mask = kf_mask_r1 | kf_mask_r2
        
        kf_ui_excl = ui_exclusion_mask[0:int(h*0.14), int(w*0.70):w]
        kf_red_mask = cv2.bitwise_and(kf_red_mask, cv2.bitwise_not(kf_ui_excl))
        
        kf_ratio = kf_red_mask.sum() / (kf_red_mask.size * 255)
        kill_feed_score = 0.0
        if kf_ratio > 0.005:
            kill_feed_score += 2.5  # KILL_FEED_BONUS

        # Motion & Recoil signals
        small_gray = cv2.resize(gray, (480, 270))
        flow = cv2.calcOpticalFlowFarneback(prev_gray_small, small_gray, None, 0.5, 3, 15, 3, 5, 1.2, 0)
        motion_score = np.sqrt(flow[...,0]**2 + flow[...,1]**2).mean() * 4
        prev_gray_small = small_gray.copy()

        recoil_score = cv2.absdiff(gun_zone, prev_gun_zone).mean() * 2

        # Combine all frame level signals
        total_score = hit_score + kill_feed_score + (motion_score * 0.15) + (recoil_score * 0.1)
        frame_scores.append((t, total_score, is_hit, len(headshot_blobs) > 0, kf_ratio > 0.005, motion_score))

        # Check for immediate feedback on console for detections
        if total_score > 3.0 and t >= running_cooldown:
            kills_found += 1
            running_cooldown = t + 2.0
            if total_score > best_score:
                best_score = total_score
            kill_min = int(t // 60)
            kill_sec = int(t % 60)
            time_str = f"{kill_min}:{kill_sec:02d}"
            kill_type = "headshot" if len(headshot_blobs) > 0 else "kill_feed" if kf_ratio > 0.005 else "standard"
            print(f"[KILLFRAME] 💀 ACTION DETECTED at {time_str} | Score: {total_score:.1f} | Type: {kill_type}")

        # Update references
        prev_gray = gray.copy()
        prev_gun_zone = gun_zone.copy()
        frame_idx += 1

    cap.release()
    elapsed_total = int(time.time() - t_scan_start)
    print(f"[KILLFRAME] Scanning: 100% ({elapsed_total}s) | Kills: {kills_found} | Best score: {best_score:.1f}")

    if not frame_scores:
        frame_scores = [(t, 1.0, False, False, False, 10.0) for t in np.linspace(20.0, max(30.0, total_duration - 5.0), 10)]

    # Group frame scores into events (gap < 2.5s)
    events = []
    current_event = []
    
    # Auto adaptive threshold for active frames
    all_scores_array = np.array([fs[1] for fs in frame_scores])
    threshold = float(np.percentile(all_scores_array, 85))
    print(f"[KILLFRAME] Auto threshold: {threshold:.1f} (top 15% of frames)")

    for fs in frame_scores:
        t, score, is_hit, is_hs, is_kf, motion = fs
        if score >= threshold or is_hit or is_kf:
            if not current_event:
                current_event.append(fs)
            else:
                last_t = current_event[-1][0]
                if t - last_t <= 2.5:
                    current_event.append(fs)
                else:
                    events.append(current_event)
                    current_event = [fs]
        elif current_event:
            last_t = current_event[-1][0]
            if t - last_t > 2.5:
                events.append(current_event)
                current_event = []
                
    if current_event:
        events.append(current_event)

    # Score each event
    scored_events = []
    for idx, ev in enumerate(events):
        ev_t = [fs[0] for fs in ev]
        ev_scores = [fs[1] for fs in ev]
        ev_hits = [fs[2] for fs in ev]
        ev_hs = [fs[3] for fs in ev]
        ev_kf = [fs[4] for fs in ev]
        ev_motions = [fs[5] for fs in ev]
        
        sum_scores = sum(ev_scores)
        headshot_count = sum(1 for hs in ev_hs if hs)
        kill_count = sum(1 for kf in ev_kf if kf)
        
        # Combo multiplier: consecutive hit frames
        combo_multiplier = 0.0
        consec = 0
        for hit in ev_hits:
            if hit:
                consec += 1
                combo_multiplier += consec * 0.5
            else:
                consec = 0
                
        max_motion = max(ev_motions) if ev_motions else 0.0
        lobby_penalty = 0.0
        slow_penalty = 5.0 if max_motion < 5.0 else 0.0
        
        # EVENT_SCORE Formula from hackathon guidelines
        event_score = sum_scores + headshot_count * 3.0 + kill_count * 5.0 + combo_multiplier + max_motion - lobby_penalty - slow_penalty
        
        # Clip boundaries: 1.2s pre-roll, 1.8s post-roll
        start_t = max(0.0, min(ev_t) - 1.2)
        end_t = min(total_duration, max(ev_t) + 1.8)
        dur = end_t - start_t
        
        # Cap/floor duration constraints
        if dur > 4.0:
            end_t = start_t + 4.0
            dur = 4.0
        if dur < 0.8:
            end_t = start_t + 0.8
            dur = 0.8
            
        scored_events.append({
            "event_index": idx,
            "start": start_t,
            "end": end_t,
            "duration": dur,
            "score": event_score,
            "headshots": headshot_count,
            "kills": kill_count,
            "max_motion": max_motion
        })

    # Sort events by score descending
    scored_events.sort(key=lambda x: x["score"], reverse=True)

    # Deduplicate overlapping events
    deduplicated = []
    for ev in scored_events:
        overlap = False
        for d in deduplicated:
            # Check overlap in time interval
            if not (ev["end"] <= d["start"] or ev["start"] >= d["end"]):
                overlap = True
                break
        if not overlap:
            deduplicated.append(ev)

    # Smart clip count based on style profile duration
    duration_to_clips = {30: 8, 60: 15, 120: 25, 180: 35, 300: 55, 600: 100}
    output_duration = max(60, style_profile.get("output_duration", 60))
    clips_needed = next((v for k, v in sorted(duration_to_clips.items()) if output_duration <= k), 100)
    if clips_needed < 15:
        clips_needed = 15
    print(f"[KILLFRAME] Need {clips_needed} clips for {output_duration}s montage")

    # Fallback to evenly spaced segments if less than clips_needed clips
    if len(deduplicated) < clips_needed:
        print(f"[KILLFRAME] Fallback: Generating {clips_needed} evenly spaced segments...")
        deduplicated = []
        step = (total_duration - 15.0) / clips_needed
        for i in range(clips_needed):
            start_t = 10.0 + i * step
            deduplicated.append({
                "start": start_t,
                "end": start_t + 2.5,
                "duration": 2.5,
                "score": 5.0,
                "headshots": 0,
                "kills": 0,
                "max_motion": 10.0
            })

    # Keep only the top clips needed, sorted chronologically
    selected_events = deduplicated[:clips_needed]
    selected_events.sort(key=lambda x: x["start"])

    # Extract clips using FFmpeg (attempt GPU acceleration first)
    extracted_clips = []
    print(f"[KILLFRAME] Extracting {len(selected_events)} clips using FFmpeg...")
    for i, ev in enumerate(selected_events):
        output = f"temp/kills/kill_{i:03d}.mp4"
        
        gpu_cmd = f'ffmpeg -hwaccel cuda -ss {ev["start"]} -i "{video_path}" -t {ev["duration"]} -c:v h264_nvenc "{output}" -y -loglevel quiet'
        cpu_cmd = f'ffmpeg -ss {ev["start"]} -i "{video_path}" -t {ev["duration"]} -c:v libx264 -preset ultrafast "{output}" -y -loglevel quiet'
        
        # Try GPU first
        result = subprocess.run(gpu_cmd, shell=True).returncode
        if result != 0:
            # Fallback to CPU
            subprocess.run(cpu_cmd, shell=True)
            
        print(f"[KILLFRAME] Extracted clip {i+1}/{len(selected_events)}: {output} (duration: {ev['duration']:.2f}s)")

        extracted_clips.append({
            "path": output,
            "start": ev["start"],
            "end": ev["end"],
            "duration": ev["duration"],
            "score": float(ev["score"]),
            "headshots": ev["headshots"],
            "kills": ev["kills"],
            "max_motion": ev["max_motion"]
        })

    # Calculations for report
    top_score = float(max([c["score"] for c in extracted_clips]))
    avg_score = float(np.mean([c["score"] for c in extracted_clips]))

    print("[KILLFRAME] ════════════════════════════════════════")
    print("[KILLFRAME] KILL SCAN COMPLETE")
    print(f"[KILLFRAME] Footage scanned: {footage_minutes:.1f} minutes")
    print(f"[KILLFRAME] Kill moments found: {len(deduplicated)}")
    print(f"[KILLFRAME] Top kill score: {top_score:.1f}")
    print(f"[KILLFRAME] Average kill score: {avg_score:.1f}")
    print(f"[KILLFRAME] Clips selected: {len(extracted_clips)}")
    print("[KILLFRAME] ════════════════════════════════════════")

    return extracted_clips
