"""
KILLFRAME-AGENT Color Analyzer
Extracts exact color grading from reference video
and applies it to output montage
"""
import cv2
import numpy as np
from pathlib import Path

def extract_reference_lut(reference_video_path, sample_count=50):
    """
    Extract color grading profile from reference video.
    Returns exact color transformation to apply.
    """
    print("[KILLFRAME] Analyzing reference video color grade...")
    cap = cv2.VideoCapture(reference_video_path)
    if not cap.isOpened():
        return get_default_grade()

    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    step = max(1, total // sample_count)

    brightness_vals = []
    saturation_vals = []
    red_vals = []
    green_vals = []
    blue_vals = []
    contrast_vals = []
    shadow_vals = []
    highlight_vals = []

    frame_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_idx % step != 0:
            frame_idx += 1
            continue

        # Skip dark/bad frames
        if frame.mean() < 40 or frame.mean() > 220:
            frame_idx += 1
            continue

        # BGR means
        blue_vals.append(frame[:,:,0].mean())
        green_vals.append(frame[:,:,1].mean())
        red_vals.append(frame[:,:,2].mean())

        # Overall brightness
        brightness_vals.append(frame.mean())

        # Saturation in HSV
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        saturation_vals.append(hsv[:,:,1].mean())

        # Contrast = std deviation
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        contrast_vals.append(gray.std())

        # Shadows = mean of darkest 10%
        dark_pixels = gray[gray < np.percentile(gray, 10)]
        if len(dark_pixels) > 0:
            shadow_vals.append(dark_pixels.mean())

        # Highlights = mean of brightest 10%
        bright_pixels = gray[gray > np.percentile(gray, 90)]
        if len(bright_pixels) > 0:
            highlight_vals.append(bright_pixels.mean())

        frame_idx += 1

    cap.release()

    if not brightness_vals:
        return get_default_grade()

    # Build grade profile from reference
    avg_brightness = np.mean(brightness_vals)
    avg_saturation = np.mean(saturation_vals)
    avg_red = np.mean(red_vals)
    avg_green = np.mean(green_vals)
    avg_blue = np.mean(blue_vals)
    avg_contrast = np.mean(contrast_vals)

    # Calculate channel ratios
    total_channel = avg_red + avg_green + avg_blue
    red_ratio = avg_red / (total_channel / 3)
    green_ratio = avg_green / (total_channel / 3)
    blue_ratio = avg_blue / (total_channel / 3)

    # Contrast multiplier
    contrast_mult = np.clip(avg_contrast / 45.0, 0.9, 1.5)

    # Saturation multiplier
    sat_mult = np.clip(avg_saturation / 80.0, 0.8, 1.8)

    # Brightness target
    brightness_mult = np.clip(avg_brightness / 110.0, 0.85, 1.3)

    grade = {
        "brightness_mult": float(brightness_mult),
        "contrast_mult": float(contrast_mult),
        "saturation_mult": float(sat_mult),
        "red_mult": float(np.clip(red_ratio, 0.85, 1.2)),
        "green_mult": float(np.clip(green_ratio, 0.85, 1.15)),
        "blue_mult": float(np.clip(blue_ratio, 0.85, 1.15)),
        "shadow_lift": float(np.mean(shadow_vals)) if shadow_vals else 8.0,
        "highlight_protection": float(np.mean(highlight_vals)) if highlight_vals else 220.0,
        "vignette_strength": 0.10,
    }

    print(f"[KILLFRAME] Color grade extracted:")
    print(f"[KILLFRAME]   Brightness  : {brightness_mult:.3f}x")
    print(f"[KILLFRAME]   Contrast    : {contrast_mult:.3f}x")
    print(f"[KILLFRAME]   Saturation  : {sat_mult:.3f}x")
    print(f"[KILLFRAME]   Red channel : {red_ratio:.3f}x")
    print(f"[KILLFRAME]   Green ch.   : {green_ratio:.3f}x")
    print(f"[KILLFRAME]   Blue ch.    : {blue_ratio:.3f}x")

    return grade

def apply_reference_grade(frame, grade):
    """Apply extracted reference color grade to a frame"""
    try:
        f = frame.astype(np.float32)

        # Apply channel ratios (color tone matching)
        f[:,:,0] = np.clip(f[:,:,0] * grade["red_mult"], 0, 255)
        f[:,:,1] = np.clip(f[:,:,1] * grade["green_mult"], 0, 255)
        f[:,:,2] = np.clip(f[:,:,2] * grade["blue_mult"], 0, 255)

        # Apply contrast
        c = grade["contrast_mult"]
        f = np.clip((f - 128) * c + 128, 0, 255)

        # Shadow lift — raise blacks slightly
        shadow = grade["shadow_lift"]
        f = np.clip(f + shadow * (1 - f/255), 0, 255)

        # Apply saturation
        hsv = cv2.cvtColor(f.astype(np.uint8), cv2.COLOR_RGB2HSV).astype(np.float32)
        hsv[:,:,1] = np.clip(hsv[:,:,1] * grade["saturation_mult"], 0, 255)
        f = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2RGB).astype(np.float32)

        # Apply brightness
        f = np.clip(f * grade["brightness_mult"], 0, 255)

        # Vignette
        h, w = f.shape[:2]
        Y, X = np.ogrid[:h, :w]
        v = grade["vignette_strength"]
        mask = 1 - v*(((X-w/2)**2+(Y-h/2)**2)/((w/2)**2+(h/2)**2))
        mask = np.clip(mask, 1-v, 1.0)
        f = f * mask[:,:,np.newaxis]

        result = np.clip(f, 0, 255).astype(np.uint8)

        # Safety: never return frame that's too dark
        if result.mean() < 30:
            return frame
        return result
    except:
        return frame

def get_default_grade():
    return {
        "brightness_mult": 1.05,
        "contrast_mult": 1.20,
        "saturation_mult": 1.25,
        "red_mult": 1.06,
        "green_mult": 1.02,
        "blue_mult": 0.98,
        "shadow_lift": 8.0,
        "highlight_protection": 220.0,
        "vignette_strength": 0.08,
    }
