import os
import cv2
import numpy as np

os.makedirs('test_footage', exist_ok=True)

width, height = 640, 360
fps = 24
seconds = 3
frames = fps * seconds

for i in range(5):
    filename = os.path.join('test_footage', f'clip_{i+1}.mp4')
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(filename, fourcc, fps, (width, height))
    for f in range(frames):
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        # moving colored rectangle to create motion
        x = (f * 10 + i * 30) % (width - 100)
        y = (f * 5 + i * 15) % (height - 50)
        color = (int((i+1)*40)%256, int((f*3)%256), int((f*7)%256))
        cv2.rectangle(frame, (x, y), (x+100, y+50), color, -1)
        out.write(frame)
    out.release()
print('Created 5 test clips in test_footage')
