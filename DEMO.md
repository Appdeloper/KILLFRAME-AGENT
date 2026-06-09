KILLFRAME-AGENT — Demo Guide

Run this demo to show the full pipeline in one go. Designed for judges and screen recording.

Steps:

1. Open PowerShell in the project folder (or double-click `demo.bat`).

2. Ensure dependencies and `ffmpeg` are installed:

```powershell
pip install -r requirements.txt
# Install ffmpeg if missing (admin):
# winget install ffmpeg
```

3. Run the demo script (single command):

```powershell
python demo.py --youtube "https://www.youtube.com/@RuokFF" --footage "./test_footage" --music "./test_music.mp3" --output "./demo_montage.mp4"
```

What the demo shows:
- ASCII banner and progress updates
- Style analysis from a YouTube profile (uses defaults if API key is missing)
- Beat detection on the provided music file
- Automatic clip selection from `test_footage`
- Final montage export `demo_montage.mp4`

That's it — judges can now record the screen while running the script.
