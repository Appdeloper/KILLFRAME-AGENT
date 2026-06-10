def select_clips(footage_folder, style_profile):
    import cv2
    import numpy as np
    import os
    from pathlib import Path

    # Find video file
    video_path = None
    for ext in [".mp4",".avi",".mov",".mkv"]:
        for f in Path(footage_folder).glob(f"*{ext}"):
            if f.stat().st_size > 100000:
                video_path = str(f)
                break
        if video_path:
            break

    if not video_path:
        print("[KILLFRAME] No footage found!")
        return []

    # Quick caching check: If temp/kills/ contains clips, we can return them immediately to avoid scanning!
    if os.path.exists("temp/kills"):
        existing_kills = sorted([os.path.join("temp", "kills", f) for f in os.listdir("temp/kills") if f.endswith(".mp4")])
        if len(existing_kills) >= 8:
            print(f"[KILLFRAME] Cache hit! Found {len(existing_kills)} already extracted clips in temp/kills/. Skipping 24-minute scan.")
            return existing_kills

    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps
    print(f"[KILLFRAME] Footage: {duration/60:.1f}min | {total_frames} frames | {fps:.0f}fps")

    # Use learned style for threshold
    learned_pacing = style_profile.get("pacing", "fast")
    print(f"[KILLFRAME] Using learned pacing: {learned_pacing}")

    all_scores = []
    frame_idx = 0
    prev_frame = None
    prev_gray = None
    prev_brightness = 0
    last_progress = -1

    # First pass — collect all scores
    print("[KILLFRAME] Pass 1/2: Collecting frame scores...")
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_idx % 10 != 0:
            frame_idx += 1
            continue

        progress = int((frame_idx / total_frames) * 100)
        if progress % 10 == 0 and progress != last_progress:
            print(f"[KILLFRAME] Scanning: {progress}%")
            last_progress = progress

        timestamp = frame_idx / fps
        if timestamp < 20:
            frame_idx += 1
            continue

        # Skip bad frames
        center = frame[int(frame.shape[0]*0.2):int(frame.shape[0]*0.8),
                      int(frame.shape[1]*0.2):int(frame.shape[1]*0.8)]
        if center.std() < 12:
            frame_idx += 1
            continue

        score = 0
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        brightness = frame.mean()
        h, w = frame.shape[:2]

        # Signal 1: Kill feed
        kz = frame[0:int(h*0.14), int(w*0.70):w]
        red = ((kz[:,:,2]>140) & (kz[:,:,0]<80)).sum()
        score += (red/(kz.shape[0]*kz.shape[1]+1)) * 300

        # Signal 2: Flash
        score += max(0, brightness-155) * 2.5

        # Signal 3: Motion
        if prev_frame is not None:
            diff = cv2.absdiff(frame, prev_frame).mean()
            score += diff * 2

        # Signal 4: Optical flow
        if prev_gray is not None:
            prev_gray_small = cv2.resize(prev_gray, (480, 270))
            gray_small = cv2.resize(gray, (480, 270))
            flow = cv2.calcOpticalFlowFarneback(
                prev_gray_small, gray_small, None, 0.5, 3, 15, 3, 5, 1.2, 0
            )
            flow_mag = np.sqrt(flow[...,0]**2+flow[...,1]**2).mean()
            score += flow_mag * 3

        # Signal 5: Recoil
        gun_zone = frame[int(h*0.5):h, int(w*0.2):int(w*0.8)]
        if prev_frame is not None:
            prev_gun = prev_frame[int(h*0.5):h, int(w*0.2):int(w*0.8)]
            score += cv2.absdiff(gun_zone, prev_gun).mean()

        # Signal 6: Contours
        edges = cv2.Canny(gray, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        big = [c for c in contours if 1500<cv2.contourArea(c)<50000]
        score += min(50, len(big)*4)

        # Signal 7: Hit effect
        center_r = frame[int(h*0.3):int(h*0.7), int(w*0.3):int(w*0.7)]
        red_hit = ((center_r[:,:,2]>160) & (center_r[:,:,0]<60)).sum()
        score += (red_hit/(center_r.size+1)) * 150

        all_scores.append((timestamp, float(score)))
        prev_frame = frame.copy()
        prev_gray = gray.copy()
        prev_brightness = brightness
        frame_idx += 1

    cap.release()

    if not all_scores:
        print("[KILLFRAME] No frames analyzed — returning empty")
        return []

    scores_only = [s for _, s in all_scores]
    auto_threshold = np.percentile(scores_only, 82)
    print(f"[KILLFRAME] Auto threshold: {auto_threshold:.1f} (top 18% of frames)")

    # Find kill moments
    kill_moments = [(t,s) for t,s in all_scores if s >= auto_threshold]

    # Deduplicate kills within 2 seconds
    merged = []
    for ts, sc in sorted(kill_moments):
        if not merged or ts - merged[-1][0] > 2.0:
            merged.append([ts, sc])
        elif sc > merged[-1][1]:
            merged[-1] = [ts, sc]

    merged.sort(key=lambda x: x[1], reverse=True)
    print(f"[KILLFRAME] Kill moments found: {len(merged)}")

    # If not enough kills lower threshold
    output_duration = style_profile.get("output_duration", 60)
    clip_len = style_profile.get("recommended_clip_length", 2.2)
    clips_needed = max(8, int(output_duration / clip_len))

    if len(merged) < 8:
        print(f"[KILLFRAME] Only {len(merged)} kills — lowering threshold 40% and rescanning...")
        new_thresh = auto_threshold * 0.6
        kill_moments = [(t,s) for t,s in all_scores if s >= new_thresh]
        merged = []
        for ts, sc in sorted(kill_moments):
            if not merged or ts - merged[-1][0] > 1.5:
                merged.append([ts, sc])
            elif sc > merged[-1][1]:
                merged[-1] = [ts, sc]
        merged.sort(key=lambda x: x[1], reverse=True)
        print(f"[KILLFRAME] After rescan: {len(merged)} kills")

    selected = merged[:clips_needed]
    selected_times = sorted([t for t,_ in selected])
    print(f"[KILLFRAME] Selected top {len(selected_times)} clips for {output_duration}s montage")

    # Extract clips
    print("[KILLFRAME] Pass 2/2: Extracting kill clips...")
    os.makedirs("temp/kills", exist_ok=True)
    output_clips = []

    for i, ts in enumerate(selected_times):
        start = max(0, ts - 1.0)
        out = f"temp/kills/kill_{i:03d}.mp4"
        gpu_cmd = f'ffmpeg -hwaccel cuda -ss {start:.2f} -i "{video_path}" -t 3.5 -c:v h264_nvenc -c:a aac "{out}" -y -loglevel quiet'
        cpu_cmd = f'ffmpeg -ss {start:.2f} -i "{video_path}" -t 3.5 -c:v libx264 -preset ultrafast -c:a aac "{out}" -y -loglevel quiet'
        result = os.system(gpu_cmd)
        if result != 0 or not os.path.exists(out):
            os.system(cpu_cmd)
        if os.path.exists(out) and os.path.getsize(out) > 1000:
            output_clips.append(out)
            print(f"[KILLFRAME] 💀 Kill {i+1}/{len(selected_times)} extracted at {ts:.1f}s")
        else:
            print(f"[KILLFRAME] Failed clip at {ts:.1f}s — skipping")

    print(f"[KILLFRAME] ══════════════════════════════════")
    print(f"[KILLFRAME] SCAN COMPLETE")
    print(f"[KILLFRAME] Kills detected : {len(merged)}")
    print(f"[KILLFRAME] Clips extracted: {len(output_clips)}")
    print(f"[KILLFRAME] ══════════════════════════════════")
    return output_clips
