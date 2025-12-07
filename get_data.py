# This Python script is used to communicate with an ESP32 network and receive CSI data

# SET THESE VARIABLES
name = "test_v2"   # between ESPs (m)
category = "p"  # presence or no presence or activity {"p", "n", "a"}

path = f"{name}/{category}/"

import os

# Create base and label subfolders

os.makedirs(path, exist_ok=True)

import serial, re
import numpy as np
import matplotlib.pyplot as plt
import collections
import datetime

amplitude = collections.deque(maxlen=50)
phase = collections.deque(maxlen=50)

# Check operating system
if os.name == "nt":
    esp_serial = serial.Serial(port='COM9', baudrate=921600)   
else:
    esp_serial = serial.Serial(port='/dev/ttyUSB0', baudrate=921600)

data = ""

monitor_dpi = 192

plt.ion()
fig = plt.figure()
ax = plt.Axes(fig, [0., 0., 1., 1.])
ax.set_axis_off()
fig.add_axes(ax)
fig.canvas.draw()
plt.show(block=False)

i = 0
img_i = 0

while 1:
    data = esp_serial.readline().decode(errors='ignore')

    if 'CSI DATA' in data:
        data = re.findall(r"\(.*?\)", data)

        csi_size = len(data)

        # print(csi_size)

        if csi_size == 192:
            amplitudes = []
            phases = []

            iteration = 0
            for tup in data:
                tup = re.sub(r'[()\ ]', '', tup)
                ints = tup.split(",")
                a = 0
                b = 0

                if ints[0].isdigit() or (ints[0].startswith('-') and ints[0][1:].isdigit()):
                    a = int(ints[0])
                if ints[1].isdigit() or (ints[1].startswith('-') and ints[1][1:].isdigit()):
                    b = int(ints[1])

                # (iteration > 5 and iteration < 32) or (iteration > 32 and iteration < 59)
                # or (iteration > 65 and iteration < 123) or (iteration > 133 and iteration < 191):
                if (iteration > 65 and iteration < 123):
                    # Non-logarithmic
                    amplitudes.append(np.sqrt(a ** 2 + b ** 2))
                    phases.append(np.atan2(b, a))

                iteration += 1

            amplitude.append(amplitudes)
            phase.append(phases)

            plt.clf()
            
            # df has shape (50, 58) -> (samples, freqs)
            df = np.clip(np.asarray(amplitude, dtype=np.float32) * (255/35), 0, 255) # Get max 255, min 0
            plt.pcolormesh(np.transpose(df), cmap='gray')
            plt.axis('off')

            fig.canvas.flush_events()
            plt.show()

            date = datetime.datetime.now().strftime("%Y-%m-%d %H%M%S")
            i += 1
                            
            if i == 50:
                if img_i > 0:
                    df = np.clip(np.asarray(amplitude, dtype=np.float32) * (255/35), 0, 255) # Get max 255, min 0
                    # Save a 58X50 pixel image (freq x samples), matching the live plot data
                    img = np.transpose(df)      # shape (58, 50) -> 58 px high, 50 px wide
                    # img_norm = np.clip(img / 35.0, 0, 1)  # normalize like vmin=0, vmax=35

                    plt.imsave(f"{path}{date}.png", img, cmap='gray')

                print(f"Image: {img_i}")
                if img_i == 55:
                    exit()
                i = 0
                img_i += 1

