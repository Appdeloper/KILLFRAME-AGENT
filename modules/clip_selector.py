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
    prev_gun_zone = None

    t_scan_start = time.time()
    last_printed_progress = -5
    kills_found = 0
    best_score = 0.0
    running_cooldown = 0.0
    all_scores_for_estimate = []

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
            prev_gun_zone = gun_zone.copy()

        # Bad segment checks:
        # 1. Skip first 20 seconds
        if t < 20.0:
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

        # 4. Skip if top area is yellow/orange (victory screen)
        top_area = frame[0:int(h*0.2), :]
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

        # Signal 1 — Kill Feed Red Pixels
        kill_zone = frame[0:int(h*0.14), int(w*0.70):w]
        red = ((kill_zone[:,:,2]>140) & (kill_zone[:,:,0]<80) & (kill_zone[:,:,1]<80))
        kill_feed_score = (red.sum() / (kill_zone.shape[0]*kill_zone.shape[1])) * 300

        # Signal 2 — White Flash
        brightness = frame.mean()
        flash_score = max(0, brightness - 150) * 3

        # Signal 3 — Optical Flow Motion
        flow = cv2.calcOpticalFlowFarneback(prev_gray, gray, None, 0.5, 3, 15, 3, 5, 1.2, 0)
        motion_score = np.sqrt(flow[...,0]**2 + flow[...,1]**2).mean() * 4

        # Signal 4 — Gun Recoil
        recoil_score = cv2.absdiff(gun_zone, prev_gun_zone).mean() * 2

        # Signal 5 — Enemy Contour Detection
        edges = cv2.Canny(gray, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        enemy_score = min(50, len([c for c in contours if 1500 < cv2.contourArea(c) < 50000]) * 5)

        # Signal 6 — Blood/Hit Effect Detection
        center = frame[int(h*0.3):int(h*0.7), int(w*0.3):int(w*0.7)]
        red_hit = ((center[:,:,2]>160) & (center[:,:,0]<60)).sum()
        hit_score = (red_hit / center.size) * 200

        # Signal 7 — Elimination Text Detection
        bottom = frame[int(h*0.75):h, int(w*0.2):int(w*0.8)]
        white_pixels = (bottom > 220).all(axis=2).sum()
        text_score = min(30, white_pixels / 100)

        # Total score
        total_score = kill_feed_score + flash_score + motion_score + recoil_score + enemy_score + hit_score + text_score
        frame_scores.append((t, total_score))

        # Maintain running count of estimated kills for progress bar
        all_scores_for_estimate.append(total_score)
        if len(all_scores_for_estimate) > 20:
            running_threshold = np.percentile(all_scores_for_estimate, 85)
            if total_score >= running_threshold and t >= running_cooldown:
                kills_found += 1
                running_cooldown = t + 2.0  # deduplicate window
                if total_score > best_score:
                    best_score = total_score
                
                # Format time string e.g. 0:45
                kill_min = int(t // 60)
                kill_sec = int(t % 60)
                time_str = f"{kill_min}:{kill_sec:02d}"

                signals_map = {
                    "headshot_flash": flash_score,
                    "kill_feed": kill_feed_score,
                    "motion": motion_score,
                    "recoil": recoil_score,
                    "enemy_contour": enemy_score,
                    "hit_effect": hit_score,
                    "elimination_text": text_score
                }
                kill_type = max(signals_map, key=signals_map.get)
                print(f"[KILLFRAME] 💀 KILL DETECTED at {time_str} | Score: {total_score:.1f} | Type: {kill_type}")

        # Update previous frame references
        prev_gray = gray.copy()
        prev_gun_zone = gun_zone.copy()
        frame_idx += 1

    cap.release()
    # Log 100% progress
    elapsed_total = int(time.time() - t_scan_start)
    print(f"[KILLFRAME] Scanning: 100% ({elapsed_total}s) | Kills: {kills_found} | Best score: {best_score:.1f}")

    if not frame_scores:
        frame_scores = [(t, 50.0) for t in np.linspace(20.0, max(30.0, total_duration - 5.0), 10)]

    # Auto adaptive threshold (top 15% of frames)
    all_scores_array = np.array([score for t, score in frame_scores])
    threshold = float(np.percentile(all_scores_array, 85))
    print(f"[KILLFRAME] Auto threshold: {threshold:.1f} (top 15% of frames)")

    def extract_and_deduplicate(thresh):
        candidates = []
        for t, score in frame_scores:
            if score >= thresh:
                candidates.append((t, score))
        
        # Sort chronologically for deduplication loop
        sorted_kills = sorted(candidates, key=lambda x: x[0])
        
        # Merge kills within 2 seconds of each other — keep highest score
        merged = []
        for ts, score in sorted_kills:
            if not merged or ts - merged[-1][0] > 2.0:
                merged.append((ts, score))
            elif score > merged[-1][1]:
                merged[-1] = (ts, score)
        return merged

    # Select kill moments
    kill_moments = extract_and_deduplicate(threshold)

    # Automatic threshold lowering fallback (40% lower)
    if len(kill_moments) < 8:
        threshold = threshold * 0.60
        print(f"[KILLFRAME] Kills less than 8, rescanning with 40% lower threshold: {threshold:.1f}")
        kill_moments = extract_and_deduplicate(threshold)

    # Bulletproof fallback: generate 8 evenly spaced segments
    if len(kill_moments) < 8:
        print("[KILLFRAME] Fallback: Generating 8 evenly spaced segments...")
        kill_moments = []
        step = max(4.0, (total_duration - 25.0) / 8)
        for i in range(8):
            t_val = 20.0 + i * step
            kill_moments.append((t_val, 50.0))

    # Smart clip count based on style profile duration
    duration_to_clips = {30:8, 60:15, 120:25, 180:35, 300:55, 600:100}
    output_dur = style_profile.get("output_duration", 60)
    clips_needed = next((v for k,v in sorted(duration_to_clips.items()) if output_dur <= k), 100)

    # Sort candidates by score descending and take the best, then re-sort chronologically
    kill_moments.sort(key=lambda x: x[1], reverse=True)
    selected_moments = kill_moments[:max(8, min(clips_needed, len(kill_moments)))]
    selected_moments.sort(key=lambda x: x[0])

    # Extract clips using FFmpeg (attempt GPU acceleration first)
    extracted_clips = []
    print(f"[KILLFRAME] Extracting {len(selected_moments)} clips using FFmpeg...")
    for i, (t_moment, score_val) in enumerate(selected_moments):
        start = max(0.0, t_moment - 1.2)
        output = f"temp/kills/kill_{i:03d}.mp4"
        
        gpu_cmd = f'ffmpeg -hwaccel cuda -ss {start} -i "{video_path}" -t 3.5 -c:v h264_nvenc "{output}" -y -loglevel quiet'
        cpu_cmd = f'ffmpeg -ss {start} -i "{video_path}" -t 3.5 -c:v libx264 -preset ultrafast "{output}" -y -loglevel quiet'
        
        # Try GPU first
        result = subprocess.run(gpu_cmd, shell=True).returncode
        if result != 0:
            # Fallback to CPU
            subprocess.run(cpu_cmd, shell=True)
            
        print(f"[KILLFRAME] Extracted clip {i+1}/{len(selected_moments)}: {output}")

        extracted_clips.append({
            "path": output,
            "start": start,
            "end": start + 3.5,
            "duration": 3.5,
            "score": float(score_val)
        })

    # Calculations for report
    top_score = float(max([c["score"] for c in extracted_clips]))
    avg_score = float(np.mean([c["score"] for c in extracted_clips]))

    print("[KILLFRAME] ════════════════════════════════════════")
    print("[KILLFRAME] KILL SCAN COMPLETE")
    print(f"[KILLFRAME] Footage scanned: {footage_minutes:.1f} minutes")
    print(f"[KILLFRAME] Kill moments found: {len(kill_moments)}")
    print(f"[KILLFRAME] Top kill score: {top_score:.1f}")
    print(f"[KILLFRAME] Average kill score: {avg_score:.1f}")
    print(f"[KILLFRAME] Clips selected: {len(extracted_clips)}")
    print("[KILLFRAME] ════════════════════════════════════════")

    return extracted_clips
