# 🎮 KILLFRAME-AGENT

> **KILLFRAME-AGENT is an autonomous AI agent built for the Microsoft Agents League Hackathon that watches, learns, and edits like a pro gaming content creator — automatically.**

![Python](https://img.shields.io/badge/Python-3.10+-blue?style=for-the-badge&logo=python)
![GitHub Copilot](https://img.shields.io/badge/Built%20With-GitHub%20Copilot-black?style=for-the-badge&logo=github)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)
![Hackathon](https://img.shields.io/badge/Microsoft-Agents%20League%202026-orange?style=for-the-badge&logo=microsoft)

---

## 🔥 What Is KILLFRAME-AGENT?

KILLFRAME-AGENT is the **ultimate autonomous AI gaming montage editor** that watches, learns, and edits like a pro gaming content creator — automatically. Built for Free Fire creators, it studies a reference YouTube video, learns the editing style across a 100-video intelligence database, runs a 7-signal computer vision pipeline to extract raw gameplay highlights, syncs cuts to music beats using advanced DSP, and exports a professionally color-graded montage in seconds.

---

## ✨ Features & Master Modules

### 📺 100-Video AI Learning Engine (`modules/youtube_learner.py`)
- **Deep Style Analysis**: Automatically downloads, scans, and analyzes up to 100 YouTube montage videos to learn optimal cuts per minute, clip pacing, transition flashes, and color saturation.
- **Intelligence Caching**: Compiles and caches unified style intelligence to `style_intelligence.json` for instant subsequent runs, supporting full relearning cycles.

### 🔍 7-Signal Military-Grade Kill Detection (`modules/clip_selector.py`)
- **Computer Vision Pipeline**: Evaluates frames using 7 distinct signals to isolate raw gameplay highlights:
  1. *Kill Feed Activity*: Red-ratio analysis in the top-right kill-feed zone.
  2. *Screen Flash*: Sudden brightness boosts denoting shots fired.
  3. *Frame Difference Motion*: Structural change indicators.
  4. *Optimized Dense Optical Flow*: Farneback flow on resized `480x270` frames for high performance (15x faster scan).
  5. *Gun Recoil*: Frame deviation analysis in the weapon viewport area.
  6. *Edge Contours*: Canny edge contour distribution changes.
  7. *Hit Marker Highlights*: Target-center red flash detection.
- **Smart Cooldown & Deduplication**: Merges overlapping events and avoids duplicate clips within 2 seconds.

### 🎵 Librosa HPSS Beat & Bass Drop Sync (`modules/beat_detector.py`)
- **Audio Stem Separation**: Performs Harmonic-Percussive Source Separation (HPSS) to extract rhythmic frames from melody.
- **Advanced Rhythm Analysis**: Tracks tempo (BPM), onset envelopes, buildup energy maps, strong beats, and bass drops using signal peak analysis (`scipy.signal`).
- **Modern Compatibility**: Fully supports Librosa 0.10+ numpy-scalar conversions.

### 🎬 Hollywood Cinematic Grading (`modules/video_editor.py`)
- **Color Correction**: Applies custom brightness scaling, contrast scaling, saturation boosters, and cinematic vignettes.
- **Beat-Synced Rendering**: Concatenates clips with custom white flash transitions synced precisely to music beats and bass drops.
- **Process Cleanup**: Calls explicit moviepy garbage collection to free file locks.

### 💬 Interactive Configuration Wizard (`run.py` & `start.bat`)
- **One-Click Startup**: Launch `start.bat` to boot the interactive wizard.
- **Interactive Prompts**: Guides the user through API key setup, reference YouTube video selection, drag-and-drop raw footage path, background music path, output duration presets (30s to 10m), and custom filenames.
- **Step 0 Learning Menu**: Allows toggling between full 100-video learning (`L`) or using pre-trained cache intelligence (`S`) for instant generation.

---

## 🛠 Tech Stack

| Tool | Purpose |
|---|---|
| Python | Core language |
| OpenCV | Computer vision & frame-level signal extraction |
| Librosa & SciPy | HPSS separation, tempo tracking & peak frequency detection |
| MoviePy & FFmpeg | Frame compositing, rendering, and encoding |
| Multi-LLM | Gemini, OpenAI, Groq, or Anthropic style profiling support |
| GitHub Copilot | Development assistant |

---

## 🚀 Getting Started

### Prerequisites
```bash
python 3.10+
ffmpeg installed on system and added to PATH
```

### Installation
```bash
# Clone the repo
git clone https://github.com/Appdeloper/KILLFRAME-AGENT.git
cd KILLFRAME-AGENT

# Install dependencies
pip install -r requirements.txt
```

### Run The Wizard (Interactive Mode)
Simply double-click `start.bat` or run:
```bash
python run.py
```

### Run The Agent (CLI Mode)
```bash
python agent.py \
  --youtube "https://www.youtube.com/watch?v=NwV3DjiXmms" \
  --footage "./test_footage" \
  --music "./real_music.mp3" \
  --output "./pro_montage.mp4" \
  --duration 60
```

---

## 🔐 Security

KILLFRAME-AGENT never stores or exposes your API key:
- Key is entered securely via hidden prompt (like a password)
- Stored only in local `.env` file
- `.env` is in `.gitignore` — NEVER pushed to GitHub
- Key is never printed or logged anywhere
- Works with Gemini, OpenAI, Groq, or Anthropic keys

---

## 📁 Project Structure

```
KILLFRAME-AGENT/
│
├── agent.py                  # Main agent pipeline entry point
├── requirements.txt          # Python dependencies
├── .env.example              # Environment variable template
├── README.md                 # You are here
│
└── modules/
    ├── style_analyzer.py     # YouTube creator style analysis
    ├── beat_detector.py      # Music beat detection & timestamps
    ├── clip_selector.py      # Gameplay highlight selection
    ├── video_editor.py       # Final montage assembly & export
    └── key_manager.py        # Secure API key manager
```

---

## 🎮 Why Free Fire?

Free Fire is the **most downloaded mobile game** in history across emerging markets — India, Brazil, Southeast Asia. The creator economy around it is massive yet completely underserved by AI tools.

KILLFRAME-AGENT targets this gap directly: a powerful, **free** tool built for the millions of creators who can't afford expensive editing software but want pro-quality results.

---

## 🏆 Built For

**Microsoft Agents League Hackathon 2026**
Track: **Creative Apps**
Tool: **GitHub Copilot**

This project demonstrates agentic AI by chaining four autonomous reasoning steps — analyze, detect, select, edit — into a single pipeline that takes a creative brief and produces a finished output with no human intervention.

---

## 🔮 Future Vision

- [ ] Support for multiple games (Valorant, BGMI, COD Mobile)
- [ ] Style presets from top 100 gaming creators
- [ ] Real-time clip suggestion during live gameplay
- [ ] Direct upload to YouTube & Instagram Reels
- [ ] Web UI for non-technical creators

---

## 👤 Author

Built with 🔥 for the Microsoft Agents League Hackathon 2026.

---

## 📄 License

MIT License — free to use, modify, and distribute.