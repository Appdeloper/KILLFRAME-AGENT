#!/usr/bin/env python3
"""
KILLFRAME-AGENT — Interactive Mode
Just run: python run.py
"""
import os
import sys
import getpass
import subprocess
from pathlib import Path
from dotenv import load_dotenv, set_key

ENV_FILE = Path(".env")

def clear():
    os.system("cls" if os.name=="nt" else "clear")

def banner():
    print("="*55)
    print("   🎮  KILLFRAME-AGENT — Autonomous Montage Editor")
    print("   🏆  Microsoft Agents League Hackathon 2026")
    print("="*55)
    print()

def ask_api_key():
    load_dotenv(ENV_FILE)
    keys = ["GEMINI_API_KEY","OPENAI_API_KEY","GROQ_API_KEY","ANTHROPIC_API_KEY"]
    for k in keys:
        v = os.getenv(k)
        if v and len(v) > 10:
            provider = k.replace("_API_KEY","").lower()
            print(f"  [✅] API Key found: {provider.upper()}")
            return v
    print("  [🔑] No API key found.")
    print()
    print("  Get a FREE key at:")
    print("  • Gemini  → aistudio.google.com  (starts with AIza)")
    print("  • Groq    → console.groq.com     (starts with gsk_)")
    print()
    while True:
        key = getpass.getpass("  Enter your API key (hidden): ").strip()
        if not key:
            print("  [!] Cannot be empty. Try again.")
            continue
        if len(key) < 10:
            print("  [!] Key too short. Try again.")
            continue
        if key.startswith("AIza"): name = "GEMINI_API_KEY"
        elif key.startswith("gsk_"): name = "GROQ_API_KEY"
        elif key.startswith("sk-ant"): name = "ANTHROPIC_API_KEY"
        elif key.startswith("sk-"): name = "OPENAI_API_KEY"
        else: name = "GEMINI_API_KEY"
        ENV_FILE.touch(exist_ok=True)
        set_key(str(ENV_FILE), name, key)
        print(f"  [✅] Key saved securely to .env")
        return key

def ask_reference():
    print()
    print("─"*55)
    print("  STEP 1 — Reference YouTube Video")
    print("─"*55)
    print("  Paste a YouTube URL of a montage you want to copy.")
    print("  Example: https://www.youtube.com/watch?v=NwV3DjiXmms")
    print("  Press ENTER to skip and use default style.")
    print()
    url = input("  YouTube URL: ").strip()
    if not url:
        url = "https://www.youtube.com/watch?v=NwV3DjiXmms"
        print(f"  [✅] Using default reference")
    else:
        print(f"  [✅] Reference: {url}")
    return url

def ask_footage():
    print()
    print("─"*55)
    print("  STEP 2 — Raw Gameplay Footage")
    print("─"*55)
    print("  Drag and drop your MP4 gameplay file path here.")
    print("  Or type the full path to your video file.")
    print()
    while True:
        path = input("  Footage path: ").strip().strip('"').strip("'")
        if not path:
            print("  [!] Path cannot be empty. Try again.")
            continue
        if not os.path.exists(path):
            print(f"  [!] File not found: {path}")
            print("  Try again with correct path.")
            continue
        if not path.lower().endswith((".mp4",".avi",".mov",".mkv")):
            print("  [!] Must be MP4, AVI, MOV or MKV file.")
            continue
        size_mb = os.path.getsize(path) / (1024*1024)
        print(f"  [✅] Footage loaded: {os.path.basename(path)} ({size_mb:.0f}MB)")
        return path

def ask_music():
    print()
    print("─"*55)
    print("  STEP 3 — Background Music")
    print("─"*55)
    print("  Drag and drop your music file path here.")
    print("  Supported: MP3, WAV, WEBM, M4A")
    print()
    while True:
        path = input("  Music path: ").strip().strip('"').strip("'")
        if not path:
            print("  [!] Path cannot be empty. Try again.")
            continue
        if not os.path.exists(path):
            print(f"  [!] File not found: {path}")
            continue
        if not path.lower().endswith((".mp3",".wav",".webm",".m4a",".ogg")):
            print("  [!] Must be MP3, WAV, WEBM, M4A or OGG file.")
            continue
        size_mb = os.path.getsize(path) / (1024*1024)
        print(f"  [✅] Music loaded: {os.path.basename(path)} ({size_mb:.1f}MB)")
        return path

def ask_duration():
    print()
    print("─"*55)
    print("  STEP 4 — Output Duration")
    print("─"*55)
    print("  How long should the montage be?")
    print()
    print("  [1] 30 seconds  — Instagram Reel")
    print("  [2] 1 minute    — YouTube Short")
    print("  [3] 3 minutes   — Standard Montage")
    print("  [4] 5 minutes   — Long Montage")
    print("  [5] 10 minutes  — Full Highlight Reel")
    print()
    choices = {"1":30,"2":60,"3":180,"4":300,"5":600}
    while True:
        choice = input("  Choose (1-5): ").strip()
        if choice in choices:
            dur = choices[choice]
            mins = dur // 60
            secs = dur % 60
            label = f"{mins}:{secs:02d}" if mins else f"{secs}s"
            print(f"  [✅] Output duration: {label}")
            return dur
        print("  [!] Enter 1, 2, 3, 4 or 5")

def ask_output():
    print()
    print("─"*55)
    print("  STEP 5 — Output Filename")
    print("─"*55)
    print("  Press ENTER for default: killframe_output.mp4")
    print()
    name = input("  Output filename: ").strip()
    if not name:
        name = "killframe_output.mp4"
    if not name.endswith(".mp4"):
        name += ".mp4"
    print(f"  [✅] Output: {name}")
    return name

def confirm(youtube, footage, music, duration, output):
    print()
    print("="*55)
    print("  KILLFRAME-AGENT — Ready To Edit")
    print("="*55)
    print(f"  Reference  : {youtube[:50]}")
    print(f"  Footage    : {os.path.basename(footage)}")
    print(f"  Music      : {os.path.basename(music)}")
    mins = duration // 60
    secs = duration % 60
    print(f"  Duration   : {mins}:{secs:02d}")
    print(f"  Output     : {output}")
    print("="*55)
    print()
    go = input("  Press ENTER to start editing or Q to quit: ").strip().lower()
    return go != "q"

def run_agent(youtube, footage, music, duration, output):
    print()
    print("="*55)
    print("  🎬 KILLFRAME-AGENT PIPELINE STARTING...")
    print("="*55)
    print()
    cmd = [
        sys.executable, "agent.py",
        "--youtube", youtube,
        "--footage", os.path.dirname(footage),
        "--music", music,
        "--output", output,
        "--duration", str(duration)
    ]
    # Copy footage to test_footage folder
    import shutil
    footage_dir = "test_footage"
    os.makedirs(footage_dir, exist_ok=True)
    dest = os.path.join(footage_dir, os.path.basename(footage))
    if not os.path.exists(dest):
        print(f"  [📋] Copying footage to working folder...")
        shutil.copy2(footage, dest)
        print(f"  [✅] Ready")
    # Update cmd to use footage folder
    cmd[cmd.index("--footage")+1] = footage_dir
    # Run agent
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    for line in process.stdout:
        print(line, end="")
    process.wait()
    print()
    if os.path.exists(output) and os.path.getsize(output) > 10000:
        mb = os.path.getsize(output)/(1024*1024)
        print("="*55)
        print(f"  ✅ MONTAGE COMPLETE!")
        print(f"  📁 File: {output} ({mb:.1f}MB)")
        print("="*55)
        print()
        play = input("  Press ENTER to play montage or S to skip: ").strip().lower()
        if play != "s":
            os.startfile(output) if os.name=="nt" else os.system(f"open '{output}'")
    else:
        print("="*55)
        print("  ❌ Something went wrong. Check errors above.")
        print("="*55)

def ask_learning_mode(youtube_url):
    print()
    print("─"*55)
    print("  STEP 0 — Learning Mode")
    print("─"*55)
    print("  [L] Learn from 100 YouTube videos first (recommended for best results)")
    print("  [S] Skip learning and use cached intelligence")
    print()
    while True:
        choice = input("  Choose (L/S): ").strip().upper()
        if choice == 'L':
            from modules.youtube_learner import learn_from_youtube
            # Call learn_from_youtube
            learn_from_youtube(reference_url=youtube_url, max_videos=100)
            print()
            print("[KILLFRAME] Intelligence cached to style_intelligence.json")
            print("[KILLFRAME] Next run will be instant — no relearning needed")
            print("[KILLFRAME] To relearn: delete style_intelligence.json")
            break
        elif choice == 'S':
            print("  [✅] Skipping learning, using cached/default intelligence")
            break
        print("  [!] Enter L or S")

def main():
    clear()
    banner()
    ask_api_key()
    youtube = ask_reference()
    ask_learning_mode(youtube)
    footage = ask_footage()
    music = ask_music()
    duration = ask_duration()
    output = ask_output()
    if confirm(youtube, footage, music, duration, output):
        run_agent(youtube, footage, music, duration, output)
    else:
        print("  Cancelled. Run again anytime.")

if __name__ == "__main__":
    main()

