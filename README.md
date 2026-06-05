
# 🎮 KILLFRAME-AGENT

> **KILLFRAME-AGENT is an autonomous AI agent built for the Microsoft Agents League Hackathon that watches, learns, and edits like a pro gaming content creator — automatically.**



![Python](https://img.shields.io/badge/Python-3.10+-blue?style=for-the-badge&logo=python)




![GitHub Copilot](https://img.shields.io/badge/Built%20With-GitHub%20Copilot-black?style=for-the-badge&logo=github)




![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)




![Hackathon](https://img.shields.io/badge/Microsoft-Agents%20League%202026-orange?style=for-the-badge&logo=microsoft)



---

## 🔥 What Is KILLFRAME-AGENT?

KILLFRAME-AGENT is an **autonomous AI agent** that studies a Free Fire gaming creator's YouTube channel, learns their unique editing style, and automatically produces a professional beat-synced montage from raw gameplay footage — with zero manual editing required.

Point it at a YouTube channel. Give it your gameplay clips and a track. It does the rest.

---

## 🤖 How The Agent Works

```

📺  INPUT: YouTube Channel URL + Raw Gameplay Footage + Music File
          │
          ▼
🔍  STEP 1 — STYLE ANALYZER
    Agent downloads and studies the creator's videos
    Learns: cuts per minute, transition types, pacing, vibe
    Output: style_profile.json
          │
          ▼
🎵  STEP 2 — BEAT DETECTOR
    Agent scans the music file for beat timestamps
    Identifies drop points and rhythm peaks
    Output: beat_timeline.json
          │
          ▼
✂️  STEP 3 — CLIP SELECTOR
    Agent scans raw gameplay for highlight moments
    Detects kill moments via motion spike analysis
    Output: selected_clips[]
          │
          ▼
🎬  STEP 4 — VIDEO EDITOR
    Agent snaps selected clips to beat timestamps
    Applies transitions matching creator's style
    Output: killframe_montage.mp4
          │
          ▼
🏆  OUTPUT: 30-second Beat-Synced Free Fire Montage

```

---

## 🎯 The Problem

Free Fire has **500 million downloads** worldwide and thousands of active content creators producing montage videos daily. Yet:

- ❌ No AI tools exist specifically for Free Fire montage editing
- ❌ Creators spend hours manually syncing cuts to beats
- ❌ Beginners can't replicate pro editing styles
- ❌ Expensive software locks out most creators in emerging markets

**KILLFRAME-AGENT solves all of this — for free.**

---

## ✅ The Solution

An agentic pipeline that:

- 📺 **Watches** — analyzes any Free Fire YouTube creator's style
- 🧠 **Learns** — builds a style profile from their editing patterns
- ✂️ **Edits** — auto-cuts your footage to the beat matching that style
- 🎬 **Exports** — outputs a ready-to-upload montage MP4

---

## 🛠️ Tech Stack

| Tool | Purpose |
|---|---|
| **GitHub Copilot** | AI-assisted development throughout |
| **Python 3.10+** | Core agent language |
| **yt-dlp** | YouTube video downloading & analysis |
| **librosa** | Beat detection & audio analysis |
| **moviepy** | Video editing & montage assembly |
| **FFmpeg** | Video processing & encoding |
| **Groq API (free)** | LLM-powered style analysis brain |
| **requests** | API communication |

---

## 🚀 Getting Started

### Prerequisites
```bash
python 3.10+
ffmpeg installed on system
```

### Installation
```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/KILLFRAME-AGENT.git
cd KILLFRAME-AGENT

# Install dependencies
pip install -r requirements.txt
```

### Set Up Your Free Groq API Key
1. Go to [console.groq.com](https://console.groq.com)
2. Create a free account
3. Generate an API key
4. Create a `.env` file:
```
GROQ_API_KEY=your_key_here
```

### Run The Agent
```bash
python agent.py \
  --youtube "https://youtube.com/@CreatorChannelURL" \
  --footage "./my_gameplay_clips/" \
  --music "./track.mp3" \
  --output "./killframe_montage.mp4"
```

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
    └── video_editor.py       # Final montage assembly & export
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
```