# This Python script is used to communicate with an ESP32 network and receive CSI data

# SET THESE VARIABLES
# name = "test"   # between ESPs (m)
# category = "a"  # presence or no presence {"p", "n"}
# 
# path = f"{name}/{category}/"
# 
import os

# Create base and label subfolders
# true_path = os.path.join(base_path, "True")
# false_path = os.path.join(base_path, "False")

# os.makedirs(path, exist_ok=True)

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

# Load ML model
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing import image
import tensorflow as tf

model = load_model('model.h5')

model.summary()

#class_names = ["Activity", "No presence", "Presence"]

class_names = ["n", "p"]

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
            
            if img_i > 1:
                # img = image.load_img(
                #         "pred.png",
                #         target_size=(57, 50),
                #         color_mode="grayscale"
                #         )
                # img_array = image.img_to_array(img)
                # img_array = tf.expand_dims(img_array, 0)
                df = tf.expand_dims(np.transpose(df), 0)
                prediction = model.predict(np.array(df))
                prediction = prediction.argmax(axis=-1)[0]
                print(f"{class_names[prediction - 1]}")

                if class_names[prediction - 1] == "n":
                    esp_serial.write(b"red")
                else:
                    esp_serial.write(b"green")
                
            if i == 50:
                if img_i > 0:
                    df = np.clip(np.asarray(amplitude, dtype=np.float32) * (255/35), 0, 255) # Get max 255, min 0
                    # Save a 58X50 pixel image (freq x samples), matching the live plot data
                    img = np.transpose(df)      # shape (58, 50) -> 58 px high, 50 px wide
                    # img_norm = np.clip(img / 35.0, 0, 1)  # normalize like vmin=0, vmax=35

                    plt.imsave("pred.png", img, cmap='gray')

                print(f"Image: {img_i}")
                if img_i == 55:
                    exit()
                i = 0
                img_i += 1

