import numpy as np
import soundfile as sf
import os

sr = 22050
duration = 30.0
t = np.linspace(0, duration, int(sr*duration), endpoint=False)
# create beat-heavy signal: bass pulse + hi-hat noise
signal = np.zeros_like(t)
# strong pulse every 0.6s
for b in np.arange(0, duration, 0.6):
    idx = int(b*sr)
    pulse = 0.8 * np.sin(2*np.pi*60*(t[:sr//10])) * np.hanning(sr//10)
    signal[idx:idx+len(pulse)] += pulse
# background synth
signal += 0.1 * np.sin(2*np.pi*220*t)
# hi-hat noise
noise = 0.02 * np.random.randn(len(t)) * (1 + 0.5*np.sin(2*np.pi*8*t))
signal += noise
# normalize
signal = signal / np.max(np.abs(signal))

wav_path = 'test_music.wav'
mp3_path = 'test_music.mp3'
try:
    sf.write(wav_path, signal, sr)
    print('WAV written:', wav_path)
    # try converting to mp3 using ffmpeg-python
    try:
        import ffmpeg
        ffmpeg.input(wav_path).output(mp3_path, **{'q:a': 0}).overwrite_output().run(quiet=True)
        print('MP3 written:', mp3_path)
    except Exception as e:
        print('ffmpeg conversion failed, mp3 not created:', e)
        print('Falling back to keeping WAV as test_music.wav')
except Exception as exc:
    print('Failed to generate music with Python:', exc)
    print('Falling back to yt-dlp download')
    os.system('yt-dlp -x --audio-format mp3 -o "test_music.%(ext)s" "https://www.youtube.com/watch?v=5qap5aO4i9A" --postprocessor-args "-t 30"')
    if os.path.exists(mp3_path):
        print('Downloaded test_music.mp3')
