#!/usr/bin/env python3
import argparse
import time
import shutil
import os
from modules.style_analyzer import analyze_style
from modules.beat_detector import detect_beats
from modules.clip_selector import select_clips
from modules.video_editor import edit_video

BANNER = r"""
 _  __ _ _ _               _                       _     _   _ 
| |/ /(_) | | _____  _ __ | |__   ___  _ __   __ _| |__ | |_(_)_ __   __ _ 
| ' / | | |/ / _ \| '_ \| '_ \ / _ \| '_ \ / _` | '_ \| __| | '_ \ / _` |
| . \ | |   < (_) | | | | | | | (_) | | | | (_| | |_) | |_| | | | | (_| |
|_|\_\|_|_|\_\___/|_| |_|_| |_|\___/|_| |_|\__,_|_.__/ \__|_|_| |_|\__, |
                                                                   |___/ 
"""


def human_size(n):
    for unit in ['B','KB','MB','GB','TB']:
        if n < 1024.0:
            return f"{n:3.1f}{unit}"
        n /= 1024.0
    return f"{n:.1f}PB"


def run_pipeline(youtube, footage, music, output):
    print(BANNER)
    start = time.time()

    print('\n[ 25%] Analyzing creator style...')
    style = analyze_style(youtube)
    print('      ', style)

    print('\n[ 50%] Detecting beats...')
    beats = detect_beats(music)
    print('      ', beats.get('total_beats', 0), 'beats')

    print('\n[ 75%] Selecting clips...')
    clips = select_clips(footage, style)
    print('      Selected', len(clips), 'clips')

    print('\n[100%] Editing montage...')
    try:
        edit_video(clips, beats, output, style, music)
    except Exception as e:
        print('[DEMO] Error during export:', e)
        raise

    elapsed = time.time() - start
    size = os.path.getsize(output) if os.path.exists(output) else 0
    print('\n=== DEMO COMPLETE ===')
    print('Output:', output, '-', human_size(size))
    print(f'Total time: {elapsed:.1f}s')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--youtube', required=True)
    parser.add_argument('--footage', required=True)
    parser.add_argument('--music', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    run_pipeline(args.youtube, args.footage, args.music, args.output)
