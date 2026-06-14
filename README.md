# ⚡ VOLTCUT-AGENT

> **VOLTCUT-AGENT is an autonomous AI agent that strikes like lightning — analyzing any gaming creator's YouTube style and instantly producing electric beat-synced kill montages from raw gameplay footage. Any game. Any creator. Zero editing.**

![Python](https://img.shields.io/badge/Python-3.10+-blue?style=for-the-badge&logo=python)
![GitHub Copilot](https://img.shields.io/badge/Built%20With-GitHub%20Copilot-black?style=for-the-badge&logo=github)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)
![Hackathon](https://img.shields.io/badge/Microsoft-Agents%20League%202026-orange?style=for-the-badge&logo=microsoft)
![Games](https://img.shields.io/badge/Games-Any%20Game-red?style=for-the-badge)

---

## ⚡ What Is VOLTCUT-AGENT?

VOLTCUT-AGENT is an **autonomous AI agent** that watches any gaming YouTube creator, learns their exact editing style, and automatically produces a professional beat-synced montage from your raw gameplay footage — with zero manual editing required.

Point it at any YouTube channel. Give it your gameplay and a track. It strikes like lightning and delivers a professional montage.

**Works with ANY game:**
- 🎮 Free Fire
- 🎮 BGMI / PUBG Mobile
- 🎮 Valorant
- 🎮 COD Mobile
- 🎮 Fortnite
- 🎮 Apex Legends
- 🎮 Any FPS / Battle Royale

---

## 🤖 How The Agent Works
📺 INPUT: YouTube Channel URL + Raw Footage + Music

│

▼

⚡ STEP 1 — STYLE ANALYZER

Agent downloads reference video

AI analyzes editing style, pacing, color grade

Output: style_profile.json

│

▼

🎵 STEP 2 — BEAT DETECTOR

Detects every beat drop and bass drop

Snaps to exact 30fps video frames

Output: beat_timeline.json

│

▼

💀 STEP 3 — KILL DETECTOR

Scans footage using 7-signal computer vision

Finds every kill moment automatically

Output: kill_clips/

│

▼

🎬 STEP 4 — VIDEO EDITOR

Syncs kills EXACTLY on beat drops

Applies color grading from reference

Adds music, flash transitions, zoom pulses

Output: voltcut_output.mp4

│

▼

🏆 OUTPUT: Professional Beat-Synced Montage

---

## 🎯 The Problem

Gaming content creators spend **3-4 hours** manually editing every montage:
- ❌ Finding kill moments by hand
- ❌ Manually syncing cuts to beats
- ❌ Color grading every clip
- ❌ Adding transitions one by one
- ❌ Expensive software required

**3 billion+ gamers worldwide. Millions of creators. Zero AI tools built for them.**

**VOLTCUT-AGENT solves this — for free.**

---

## ✅ The Solution
You        : paste YouTube URL + footage + music

VOLTCUT    : does everything else automatically

Result     : professional montage in minutes

Cost       : completely free

---

## 🛠️ Tech Stack

| Tool | Purpose |
|---|---|
| **GitHub Copilot** | AI-assisted development |
| **Python 3.10+** | Core agent language |
| **yt-dlp** | YouTube style analysis |
| **librosa + scipy** | Beat and bass drop detection |
| **OpenCV** | 7-signal kill detection |
| **MoviePy** | Professional video editing |
| **FFmpeg** | Video processing |
| **Gemini/Groq API** | Optional AI style analysis |

---

## 🚀 Getting Started

### Install
```bash
git clone https://github.com/Appdeloper/VOLTCUT-AGENT.git
cd VOLTCUT-AGENT
pip install -r requirements.txt
```

### Run
```bash
python run.py
```

That's it. Follow the prompts:
```
⚡ VOLTCUT-AGENT

  API Key     : (optional — runs free without it)
  YouTube URL : paste any gaming creator URL
  Footage     : drag and drop your gameplay file
  Music       : drag and drop your music file
  Duration    : choose 30s / 1min / 3min / 5min / 8min
  Output name : your filename

  Press ENTER → montage generated automatically
```

---

## 🎮 How To Use VOLTCUT-AGENT

### Requirements
- Python 3.10 or higher
- FFmpeg installed (or use the one bundled with CapCut)

### Installation
```bash
git clone https://github.com/Appdeloper/VOLTCUT-AGENT.git
cd VOLTCUT-AGENT
pip install -r requirements.txt
```

### Run It
```bash
python run.py
```

### What You'll Need
| Input | What To Provide |
|---|---|
| **API Key** | Optional — skip with Enter, runs free |
| **YouTube URL** | Any Free Fire montage to copy the editing style |
| **Footage** | Your own raw Free Fire gameplay (MP4) |
| **Music** | Any song (MP3/WAV) for beat sync |
| **Duration** | Choose output length: 30s to 8min |

### Output
A professional montage video — kills synced to beats, color graded, with flash transitions — saved to your project folder and played automatically.

No editing software required. No API key required. Completely free.

### 💀 Kill Detection — 7 Signal System
VOLTCUT uses 7 simultaneous signals to find kills:
- **Kill Feed**: Red pixels in top-right corner
- **Screen Flash**: White brightness spike
- **Optical Flow**: Rapid camera movement
- **Motion Score**: Frame difference intensity
- **Gun Recoil**: Bottom center movement
- **Enemy Contours**: Large moving objects
- **Hit Effects**: Red center screen flash

Auto-adaptive threshold — learns from YOUR footage automatically.

### 🎵 Beat Sync System
- **Bass Drops**: 1st — highest kills (Longer flash + stronger zoom)
- **Strong Beats**: 2nd — good kills (Normal flash + zoom)
- **Regular Beats**: 3rd — fill clips (Short flash)

Every kill lands exactly on a beat. Not approximately — exactly.

### 🎨 Color Grading
VOLTCUT automatically clones the color grade from your reference video:
- Extracts brightness, contrast, saturation values
- Matches red/green/blue channel ratios
- Applies shadow lift and highlight protection
- Adds subtle vignette

Your output looks like the creator you referenced.

### 📁 Project Structure
```
VOLTCUT-AGENT/
├── agent.py                    # Master pipeline
├── run.py                      # Interactive launcher
├── demo.py                     # Demo mode
├── check.py                    # Health check
├── requirements.txt
├── .env.example
└── modules/
    ├── style_analyzer.py       # YouTube style AI
    ├── beat_detector.py        # Music beat analysis
    ├── clip_selector.py        # Kill detection
    ├── video_editor.py         # Montage editor
    ├── color_analyzer.py       # Color grading
    ├── song_extractor.py       # Auto song finder
    ├── youtube_learner.py      # 100 video learning
    ├── key_manager.py          # API security
    └── validator.py            # Pipeline validator
```

### 🔐 Security
- API key entered via hidden prompt (like password)
- Stored only in local `.env` file
- Never pushed to GitHub
- API key completely optional — runs free without it

### 🔮 Future Vision
- Web UI for non-technical creators
- Direct upload to YouTube and Instagram
- Real-time kill detection during live gameplay
- Style presets from top 100 gaming creators
- Support for console gameplay footage
- Mobile app version

### 🏆 Built For
Microsoft Agents League Hackathon 2026

Track: Creative Apps

Tool: GitHub Copilot

VOLTCUT-AGENT demonstrates true agentic AI — four autonomous steps that take a creative brief and produce a finished professional output with zero human intervention.

### 📊 Market Size
- 3 billion+ active gamers worldwide
- 50 million+ gaming content creators
- $250 billion gaming industry
- Zero dedicated AI montage editors exist

VOLTCUT-AGENT is first to market.

### 👤 Author
Built with ⚡ by Appdeloper for Microsoft Agents League Hackathon 2026.

### 📄 License
MIT License — free to use, modify, and distribute.