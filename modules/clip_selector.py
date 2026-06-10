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

def _crop_region(frame, region):
    height, width = frame.shape[:2]
    x0 = int(width * region[0])
    y0 = int(height * region[1])
    x1 = int(width * (region[0] + region[2]))
    y1 = int(height * (region[1] + region[3]))
    return frame[y0:y1, x0:x1]

def _extract_and_grade_segment(video_path, start_time, end_time, out_path):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return None
        
    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    start_frame = int(start_time * fps)
    end_frame = int(end_time * fps)
    
    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(out_path, fourcc, fps, (width, height))
    
    max_diff = 0.0
    max_brightness = 0.0
    max_red = 0
    
    prev_g = None
    for f in range(start_frame, end_frame):
        ret, frame = cap.read()
        if not ret:
            break
        out.write(frame)
        
        g = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        brightness = float(np.mean(g))
        if brightness > max_brightness:
            max_brightness = brightness
            
        if prev_g is not None:
            diff = float(np.mean(cv2.absdiff(g, prev_g)))
            if diff > max_diff:
                max_diff = diff
        prev_g = g
        
        # Crop top-right corner to check for red pixel spikes
        crop = _crop_region(frame, (0.7, 0.0, 0.3, 0.3))
        if crop.size > 0:
            hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
            mask1 = cv2.inRange(hsv, np.array([0, 120, 120]), np.array([10, 255, 255]))
            mask2 = cv2.inRange(hsv, np.array([170, 120, 120]), np.array([180, 255, 255]))
            mask = cv2.bitwise_or(mask1, mask2)
            red_count = int(cv2.countNonZero(mask))
            if red_count > max_red:
                max_red = red_count
                
    cap.release()
    out.release()
    
    # Calculate intensity
    # Include motion (diff), flash (brightness > 180), and red pixels (kills)
    motion_intensity = max_diff
    flash_intensity = 30.0 if max_brightness > 180.0 else 0.0
    red_intensity = float(max_red) / 5.0
    
    intensity = motion_intensity + flash_intensity + red_intensity
    return intensity

def select_clips(footage_folder, style_profile):
    if not isinstance(style_profile, dict):
        raise ValueError("style_profile must be a dictionary")

    video_files = _list_video_files(footage_folder)
    if not video_files:
        logger.warning("No video files found in %s", footage_folder)
        return []

    # Ensure output folder exists
    os.makedirs(os.path.join("temp", "kills"), exist_ok=True)

    clips = []
    clip_counter = 1

    for video_path in video_files:
        logger.info("Scanning video: %s", video_path)
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            logger.warning("Could not open video: %s", video_path)
            continue
            
        fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        total_duration = total_frames / fps if fps > 0 else 0.0
        
        frame_idx = 0
        prev_gray = None
        cooldown_until = 0.0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
                
            t = frame_idx / fps
            frame_idx += 1
            
            # Skip first 15 seconds
            if t < 15.0:
                continue
                
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            mean_brightness = float(np.mean(gray))
            
            # Skip OBS/menu black or blank transition screens
            if mean_brightness < 12.0 or mean_brightness > 240.0:
                prev_gray = gray
                continue
                
            # Skip static screens (OBS/menu/loading)
            if prev_gray is not None:
                diff_score = float(np.mean(cv2.absdiff(gray, prev_gray)))
                if diff_score < 1.0:
                    prev_gray = gray
                    continue
            prev_gray = gray
            
            # Scan top-right region for RED pixel spikes
            crop = _crop_region(frame, (0.7, 0.0, 0.3, 0.3))
            if crop.size > 0:
                hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
                mask1 = cv2.inRange(hsv, np.array([0, 120, 120]), np.array([10, 255, 255]))
                mask2 = cv2.inRange(hsv, np.array([170, 120, 120]), np.array([180, 255, 255]))
                mask = cv2.bitwise_or(mask1, mask2)
                red_pixels = int(cv2.countNonZero(mask))
                
                # Scan for RED spike
                if red_pixels > 200 and t >= cooldown_until:
                    # Found a kill moment!
                    logger.info("Detected kill moment at %.2f seconds (red pixels: %d)", t, red_pixels)
                    
                    # Extract 2.5 seconds around kill moment (1.5s before, 1.0s after)
                    start_t = max(0.0, t - 1.5)
                    end_t = min(total_duration, t + 1.0)
                    
                    out_name = f"kill_{clip_counter:03d}.mp4"
                    out_path = os.path.join("temp", "kills", out_name)
                    
                    intensity = _extract_and_grade_segment(video_path, start_t, end_t, out_path)
                    if intensity is not None:
                        clips.append({
                            "path": out_path,
                            "start": 0.0,
                            "end": 2.5,
                            "duration": 2.5,
                            "score": intensity
                        })
                        clip_counter += 1
                        
                    cooldown_until = t + 3.0
                    
        cap.release()

    # Fallback to evenly spaced clips if we have fewer than 8 clips
    if len(clips) < 8 and video_files:
        logger.info("Found only %d clips. Generating fallbacks to reach at least 8 clips.", len(clips))
        # Use the first video file to generate fallbacks
        video_path = video_files[0]
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        total_duration = total_frames / fps
        cap.release()
        
        needed = 8 - len(clips)
        # Distribute fallback timestamps across the video duration, starting after 15 seconds
        step = max(3.0, (total_duration - 20.0) / (needed + 1))
        for i in range(needed):
            fallback_t = 15.0 + (i + 1) * step
            if fallback_t + 1.0 >= total_duration:
                break
                
            start_t = max(0.0, fallback_t - 1.5)
            end_t = min(total_duration, fallback_t + 1.0)
            
            out_name = f"kill_fallback_{clip_counter:03d}.mp4"
            out_path = os.path.join("temp", "kills", out_name)
            
            intensity = _extract_and_grade_segment(video_path, start_t, end_t, out_path)
            if intensity is not None:
                clips.append({
                    "path": out_path,
                    "start": 0.0,
                    "end": 2.5,
                    "duration": 2.5,
                    "score": intensity
                })
                clip_counter += 1

    # Sort by intensity (score) descending
    clips.sort(key=lambda x: x["score"], reverse=True)
    
    # Return top 8 to 15 clips
    selected_clips = clips[:max(8, min(15, len(clips)))]
    logger.info("Selected %d top highlights sorted by intensity", len(selected_clips))
    return selected_clips
