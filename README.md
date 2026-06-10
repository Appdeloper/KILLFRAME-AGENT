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
    1. Analyze: style_analyzer inspects a creator's YouTube metadata to infer editing style.
    2. Detect: beat_detector finds beat timestamps from the music track.
    3. Select: clip_selector ranks gameplay clips by motion intensity and selects highlights.
    4. Edit: video_editor trims and concatenates clips to produce a beat-synced montage.
```

---

## 🛠 Tech Stack

| Tool | Purpose |
|---|---|
| Python | Core language |
| yt-dlp | YouTube metadata/downloads |
| librosa | Audio beat detection |
| moviepy | Video editing |
| ffmpeg | Encoding and processing |
| Multi-LLM | OpenAI, Anthropic, Groq, or Gemini style analysis |
| GitHub Copilot | Development assistant |

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
git clone https://github.com/Appdeloper/KILLFRAME-AGENT.git
cd KILLFRAME-AGENT

# Install dependencies
pip install -r requirements.txt
```

### Run The Agent
```bash
python agent.py \
  --youtube "https://youtube.com/@CreatorChannelURL" \
  --footage "./test_footage" \
  --music "./real_music.mp3" \
  --output "./pro_montage.mp4"
```

---

## 🔐 Security

KILLFRAME-AGENT never stores or exposes your API key:
- Key is entered securely via hidden prompt (like a password)
- Stored only in local .env file
- .env is in .gitignore — NEVER pushed to GitHub
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