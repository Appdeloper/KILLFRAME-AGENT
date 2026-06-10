import logging
import os
import cv2
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def _list_video_files(footage_folder):
    if not footage_folder or not os.path.isdir(footage_folder):
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

    # Ensure output folder exists
    os.makedirs(os.path.join("temp", "kills"), exist_ok=True)

    # STEP 1 — Open video and get real stats
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Could not open video: {video_path}")

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    total_duration = total_frames / fps
    total_minutes = total_duration / 60
    print(f"[KILLFRAME] Video loaded: {total_minutes:.1f} minutes, {total_frames} frames")
    print(f"[KILLFRAME] Starting kill detection scan...")

    # First pass: collect all motion scores for automatic threshold
    all_motion_scores = []
    frame_idx = 0
    prev_frame = None

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Read every 10th frame
        if frame_idx % 10 != 0:
            frame_idx += 1
            continue

        h, w = frame.shape[:2]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Signal 3 — Motion Detection
        motion_score = 0.0
        if prev_frame is not None:
            diff = cv2.absdiff(frame, prev_frame)
            motion_score = float(diff.mean())
        
        all_motion_scores.append(motion_score)
        prev_frame = frame.copy()
        frame_idx += 1

    cap.release()

    # STEP 4 — Calculate automatic threshold
    if not all_motion_scores:
        all_motion_scores = [0.0]
    motion_mean = float(np.mean(all_motion_scores))
    motion_std = float(np.std(all_motion_scores))
    kill_threshold = motion_mean + 1.5 * motion_std
    print(f"[KILLFRAME] Auto threshold calculated: {kill_threshold:.2f} based on your footage")

    # STEP 7 — Smart clip count based on output duration
    duration_setting = style_profile.get("output_duration", 60)
    clips_needed = max(8, int(duration_setting / 3.5))
    print(f"[KILLFRAME] Output duration: {duration_setting}s needs {clips_needed} clips")

    # Perform scan (potentially with threshold lowering fallback)
    def scan_video_for_kills(threshold_val):
        cap = cv2.VideoCapture(video_path)
        frame_idx = 0
        prev_frame = None
        prev_gun_area = None
        cooldown_until = 0.0
        last_printed_progress = -5
        kills_found = 0
        detected_candidates = []

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_idx % 10 != 0:
                frame_idx += 1
                continue

            t = frame_idx / fps
            progress = (frame_idx / total_frames) * 100

            # STEP 2 — Real progress tracking while scanning
            progress_pct = int(progress)
            if progress_pct >= last_printed_progress + 5:
                print(f"[KILLFRAME] Scanning: {progress_pct}% | Kills found so far: {kills_found}")
                last_printed_progress = progress_pct

            # Skip first 15 seconds
            if t < 15.0:
                frame_idx += 1
                continue

            h, w = frame.shape[:2]

            # STEP 5 — Filter bad segments automatically
            # Calculate average color of center 60% of frame
            center_area = frame[int(h*0.2):int(h*0.8), int(w*0.2):int(w*0.8)]
            mean_color = center_area.mean(axis=(0,1)) # B, G, R
            
            # If standard deviation of colors is below 15 — solid color screen — skip it
            std_dev = center_area.std()
            if std_dev < 15.0:
                timestamp_str = f"{int(t)//60}:{int(t)%60:02d}"
                print(f"[KILLFRAME] Skipping non-gameplay segment at {timestamp_str}")
                prev_frame = frame.copy()
                gun_area = frame[int(h*0.6):h, int(w*0.3):int(w*0.7)]
                prev_gun_area = gun_area.copy()
                frame_idx += 1
                continue

            # If frame is mostly dark grey (all channels 50-100) — OBS or desktop — skip
            if 50 <= mean_color[0] <= 100 and 50 <= mean_color[1] <= 100 and 50 <= mean_color[2] <= 100:
                timestamp_str = f"{int(t)//60}:{int(t)%60:02d}"
                print(f"[KILLFRAME] Skipping non-gameplay segment at {timestamp_str}")
                prev_frame = frame.copy()
                gun_area = frame[int(h*0.6):h, int(w*0.3):int(w*0.7)]
                prev_gun_area = gun_area.copy()
                frame_idx += 1
                continue

            # If top 20% of frame is mostly yellow/orange — victory screen — skip
            top_area = frame[0:int(h*0.2), :]
            top_hsv = cv2.cvtColor(top_area, cv2.COLOR_BGR2HSV)
            mask_yo = cv2.inRange(top_hsv, np.array([10, 100, 100]), np.array([35, 255, 255]))
            yo_ratio = mask_yo.sum() / (mask_yo.size * 255)
            if yo_ratio > 0.35:
                timestamp_str = f"{int(t)//60}:{int(t)%60:02d}"
                print(f"[KILLFRAME] Skipping non-gameplay segment at {timestamp_str}")
                prev_frame = frame.copy()
                gun_area = frame[int(h*0.6):h, int(w*0.3):int(w*0.7)]
                prev_gun_area = gun_area.copy()
                frame_idx += 1
                continue

            # STEP 3 — Automatic kill detection using 4 signals
            # Signal 1 — Kill Feed Detection: Crop top-right 25% of frame
            kill_feed_area = frame[0:int(h*0.15), int(w*0.75):w]
            red_mask = (kill_feed_area[:,:,2] > 150) & (kill_feed_area[:,:,0] < 80)
            red_ratio = red_mask.sum() / kill_feed_area.size
            kill_feed_score = red_ratio * 100

            # Signal 2 — Screen Flash Detection
            brightness = float(frame.mean())
            flash_score = max(0, brightness - 160)

            # Signal 3 — Motion Detection
            motion_score = 0.0
            if prev_frame is not None:
                diff = cv2.absdiff(frame, prev_frame)
                motion_score = float(diff.mean())

            # Signal 4 — Gun Recoil Detection: Check center bottom area
            gun_area = frame[int(h*0.6):h, int(w*0.3):int(w*0.7)]
            recoil_score = 0.0
            if prev_gun_area is not None:
                gun_diff = float(cv2.absdiff(gun_area, prev_gun_area).mean())
                recoil_score = gun_diff

            # Compute combined score (for intensity)
            kill_score = motion_score + kill_feed_score + flash_score + recoil_score

            # Automatic kill threshold check
            if motion_score > threshold_val and t >= cooldown_until:
                timestamp_str = f"{int(t)//60}:{int(t)%60:02d}"
                print(f"[KILLFRAME] Found kill at {timestamp_str} - motion score: {motion_score:.1f}")
                detected_candidates.append({
                    "timestamp": t,
                    "score": kill_score
                })
                kills_found += 1
                cooldown_until = t + 3.0

            # Update previous frames
            prev_frame = frame.copy()
            prev_gun_area = gun_area.copy()
            frame_idx += 1

        cap.release()
        return detected_candidates

    # Scan and detect candidates
    candidates = scan_video_for_kills(kill_threshold)

    # STEP 9 — Bulletproof fallback (kills found less than 8 -> lower threshold by 30% and rescan)
    if len(candidates) < 8:
        print("[KILLFRAME] Not enough kills found, lowering threshold and rescanning...")
        kill_threshold *= 0.7
        candidates = scan_video_for_kills(kill_threshold)

    # Extract clips and build final result
    selected_kills = []
    avg_kill_score = 0.0
    clips_list = []

    if len(candidates) >= 8:
        # Sort by score descending and take the best
        candidates.sort(key=lambda x: x["score"], reverse=True)
        top_candidates = candidates[:max(8, min(clips_needed, len(candidates)))]
        selected_kills = [x["timestamp"] for x in top_candidates]
        avg_kill_score = float(np.mean([x["score"] for x in top_candidates]))

        # STEP 6 — Extract clips with real ffmpeg
        print(f"[KILLFRAME] Scan complete! Found {len(candidates)} kill moments")
        print(f"[KILLFRAME] Extracting {len(selected_kills)} best clips...")
        for i, timestamp in enumerate(selected_kills):
            start = max(0.0, timestamp - 1.0)
            duration = 3.5
            output = f"temp/kills/kill_{i:03d}.mp4"
            cmd = f'ffmpeg -ss {start} -i "{video_path}" -t {duration} -c copy "{output}" -y'
            os.system(cmd)
            print(f"[KILLFRAME] Extracted clip {i+1}/{len(selected_kills)}: {output}")
            
            clips_list.append({
                "path": output,
                "start": 0.0,
                "end": 3.5,
                "duration": 3.5,
                "score": float(np.mean([c["score"] for c in top_candidates if c["timestamp"] == timestamp]))
            })
    else:
        # Fallback to splitting video into equal segments
        print("[KILLFRAME] Fallback: Splitting video into equal segments...")
        step = max(3.5, (total_duration - 20.0) / clips_needed)
        for i in range(clips_needed):
            timestamp = 15.0 + i * step
            start = max(0.0, timestamp - 1.0)
            duration = 3.5
            output = f"temp/kills/kill_{i:03d}.mp4"
            cmd = f'ffmpeg -ss {start} -i "{video_path}" -t {duration} -c copy "{output}" -y'
            os.system(cmd)
            print(f"[KILLFRAME] Extracted clip {i+1}/{clips_needed}: {output}")
            
            clips_list.append({
                "path": output,
                "start": 0.0,
                "end": 3.5,
                "duration": 3.5,
                "score": 50.0 # fallback default score
            })
        selected_kills = [15.0 + i * step for i in range(clips_needed)]
        avg_kill_score = 50.0

    # STEP 8 - Final summary
    print("[KILLFRAME] -------------------------------")
    print("[KILLFRAME] KILL DETECTION COMPLETE")
    print(f"[KILLFRAME] Total footage scanned: {total_minutes:.1f} minutes")
    print(f"[KILLFRAME] Kill moments detected: {len(candidates)}")
    print(f"[KILLFRAME] Clips selected: {len(selected_kills)}")
    print(f"[KILLFRAME] Average kill score: {avg_kill_score:.1f}")
    print("[KILLFRAME] -------------------------------")

    # Sort final clips by score descending
    clips_list.sort(key=lambda x: x["score"], reverse=True)
    return clips_list
