# This Python script is used to communicate with an ESP32 network and receive CSI data

# SET THESE VARIABLES

model_name = "alone"

import os

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

model = load_model(f"{model_name}.keras")

model.summary()

activity_model = load_model(f"{model_name}_activities.keras")

class_names = ["No presence", "Presence"]

#class_names_activity = ["Run", "Sit", "Stand", "Walk"]
class_names_activity = ["Sit", "Stand", "Walk"]

confidence = 0

while 1:
    data = esp_serial.readline().decode(errors='ignore')
    # print(data)

    if 'CSI_DATA' in data:
        data = re.findall(r"\[(.*?)\]", data)

        print(len(data))
        print(type(data))

        if len(data) > 0:
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
            
                # df has shape (50, 58) -> (samples, frequencies)
                df = np.clip(np.asarray(amplitude, dtype=np.float32) * (255/35), 0, 255) # Get max 255, min 0
                plt.pcolormesh(np.transpose(df), cmap='gray', vmin=0, vmax=255)
                plt.axis('off')

                i += 1

            
                if img_i > 1:
                    df = tf.expand_dims(np.transpose(df), 0)
                    prediction = model.predict(np.array(df), verbose=0)
                    prediction = prediction.argmax(axis=-1)[0]
                    # print(f"{prediction}")

                    if class_names[prediction] == "Presence":
                        if confidence < 10:
                            confidence += 1
                    else:
                        if confidence > -10:
                            confidence -= 1

                    # print(f"Confidence: {confidence}")
                    if confidence <= 0:
                        prediction = 0
                        esp_serial.write(b"green")
                        plt.title(f"{class_names[prediction]}", fontsize=50)
                    else:
                        prediction = 1
                        activity_prediction = activity_model.predict(np.array(df), verbose=0)
                        activity_prediction = activity_prediction.argmax(axis=-1)[0]
                        esp_serial.write(b"red")
                    
                        plt.title(f"{class_names[prediction]}: {class_names_activity[activity_prediction]}", fontsize=50)

                
                
                if i == 50:
                    i = 0
                    img_i += 1

                fig.canvas.flush_events()
                plt.show()
