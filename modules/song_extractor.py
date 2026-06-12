"""
KILLFRAME-AGENT Song Extractor
Automatically extracts song from reference video,
identifies it, and downloads the clean version
"""
import os
import subprocess
import json
import numpy as np
from pathlib import Path

def extract_audio_from_reference(video_path, output_path="reference_audio.wav"):
    """Extract audio track from reference YouTube video"""
    print("[KILLFRAME] Extracting audio from reference video...")
    cmd = f'ffmpeg -i "{video_path}" -vn -acodec pcm_s16le -ar 44100 -ac 2 "{output_path}" -y -loglevel quiet'
    result = os.system(cmd)
    if result == 0 and os.path.exists(output_path):
        print(f"[KILLFRAME] Audio extracted: {output_path}")
        return output_path
    return None

def identify_song(audio_path):
    """
    Try multiple methods to identify the song:
    1. Use shazam-cli if available
    2. Use ACRCloud API
    3. Use audd.io API (free tier)
    4. Search YouTube for the audio
    """
    print("[KILLFRAME] Identifying song...")

    # Method 1 — audd.io free API
    try:
        import requests
        with open(audio_path, 'rb') as f:
            audio_data = f.read(500000)  # First 500KB
        response = requests.post(
            'https://api.audd.io/',
            data={'api_token': 'test', 'return': 'spotify,apple_music'},
            files={'file': ('audio.wav', audio_data)}
        )
        result = response.json()
        if result.get('result'):
            song = result['result']
            title = song.get('title','')
            artist = song.get('artist','')
            if title and artist:
                print(f"[KILLFRAME] Song identified: {artist} - {title}")
                return f"{artist} - {title}"
    except Exception as e:
        print(f"[KILLFRAME] audd.io failed: {e}")

    # Method 2 — analyze audio fingerprint manually
    try:
        import librosa
        y, sr = librosa.load(audio_path, duration=30)
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        print(f"[KILLFRAME] Could not identify song name. BPM: {tempo:.1f}")
    except:
        pass

    return None

def download_clean_song(song_name, output_path="clean_music.mp3"):
    """Download clean version of identified song from YouTube"""
    if not song_name:
        return None
    print(f"[KILLFRAME] Downloading clean version: {song_name}")
    try:
        import yt_dlp
        query = f"ytsearch1:{song_name} official audio"
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': output_path.replace('.mp3',''),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320',
            }],
            'quiet': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([query])
        
        # Normalize file extension
        if os.path.exists(output_path + ".mp3"):
            if os.path.exists(output_path):
                os.remove(output_path)
            os.rename(output_path + ".mp3", output_path)

        if os.path.exists(output_path):
            print(f"[KILLFRAME] Clean song downloaded: {output_path}")
            return output_path

        # Find downloaded file with fallback check
        for ext in ['.mp3', '.mp3.mp3']:
            p = output_path.replace('.mp3', ext)
            if os.path.exists(p):
                print(f"[KILLFRAME] Clean song downloaded: {p}")
                return p
    except Exception as e:
        print(f"[KILLFRAME] Download failed: {e}")
    return None

def get_reference_song(reference_video_path):
    """
    Full pipeline:
    1. Extract audio from reference video
    2. Identify the song
    3. Download clean version
    4. Return path to clean music file
    """
    print("[KILLFRAME] ══════════════════════════════")
    print("[KILLFRAME]   AUTO SONG EXTRACTOR")
    print("[KILLFRAME] ══════════════════════════════")

    # Check cache
    if os.path.exists("clean_music.mp3") and os.path.getsize("clean_music.mp3") > 100000:
        print("[KILLFRAME] Using cached clean music")
        return "clean_music.mp3"

    # Extract from reference
    audio = extract_audio_from_reference(reference_video_path)
    if not audio:
        print("[KILLFRAME] Could not extract audio")
        return None

    # Identify song
    song_name = identify_song(audio)

    if song_name:
        # Download clean version
        clean = download_clean_song(song_name)
        if clean:
            print(f"[KILLFRAME] ✅ Clean song ready: {clean}")
            return clean

    # Fallback — use extracted audio directly
    print("[KILLFRAME] Using extracted reference audio as music")
    extracted_mp3 = "reference_music.mp3"
    cmd = f'ffmpeg -i "{audio}" -codec:a libmp3lame -qscale:a 2 "{extracted_mp3}" -y -loglevel quiet'
    os.system(cmd)
    if os.path.exists(extracted_mp3):
        return extracted_mp3
    return audio
