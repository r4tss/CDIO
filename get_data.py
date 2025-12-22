# This Python script is used to communicate with an ESP32 network and receive CSI data

# SET THESE VARIABLES
name = "alone"   # between ESPs (m)
category = "n"  # presence or no presence or activity {"p", "n", "a"}

path = f"../datasets/{name}/{category}/"

import os

# Create base and label subfolders

os.makedirs(path, exist_ok=True)

import serial, re
import numpy as np
import matplotlib.pyplot as plt
import collections
import datetime
import sys, select, tty, termios

# Is there data on stdin?
def isData():
    return select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], [])

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

img_i = 0
i = 0

while 1:
    data = esp_serial.readline().decode(errors='ignore')

    if 'CSI_DATA' in data:
        data = re.findall(r"\[(.*?)\]", data)

        data = data[0].split()

        csi_size = len(data)

        # print(csi_size)

        if csi_size == 384:
            amplitudes = []
            phases = []

            real = []
            imag = []

            buf_i = i
            for i in range(int(csi_size/2)):
                real.append(int(data[i * 2]))
                imag.append(int(data[(i * 2) + 1]))

                #if (i > 65 and i < 123):
                    # Non-logarithmic
                amplitudes.append(np.sqrt(real[i] ** 2 + imag[i] ** 2))
                phases.append(np.atan2(imag[i], real[i]))

            i = buf_i
            
            amplitude.append(amplitudes)
            phase.append(phases)

            plt.clf()
            
            # df has shape (50, 58) -> (samples, freqs)
            df = np.clip(np.asarray(amplitude, dtype=np.float32) * (255/35), 0, 255) # Get max 255, min 0
            plt.pcolormesh(np.transpose(df), cmap='gray', vmin=0, vmax=255)
            plt.title(f"Gathering data ({category})\nImage #{img_i}", fontsize=30)
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
                # if img_i == 55:
                #     exit()
                i = 0
                img_i += 1

