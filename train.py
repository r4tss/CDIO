import sys

if len(sys.argv) < 3:
    print("Run script as: train.py [DATASET PATH] [MODEL SAVE NAME]")
    exit()

import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
import matplotlib.pyplot as plt
import pathlib

# --- Ange din dataset-mapp här ---
data_dir = pathlib.Path(f"{sys.argv[1]}/").with_suffix('')

# --- Bildparametrar ---
img_height = 192
img_width = 50
batch_size = 32

# --- Ladda dataset från mappar ---
train_ds = tf.keras.preprocessing.image_dataset_from_directory(
    data_dir,
    validation_split=0.2,
    subset="training",
    seed=123,
    color_mode="grayscale",
    image_size=(img_height, img_width),
    batch_size=batch_size,
    labels="inferred",
    label_mode="int",
    verbose=True
)

val_ds = tf.keras.preprocessing.image_dataset_from_directory(
    data_dir,
    validation_split=0.2,
    subset="validation",
    seed=123,
    color_mode="grayscale",
    image_size=(img_height, img_width),
    batch_size=batch_size,
    labels="inferred",
    label_mode="int",
    verbose=True
)

image_count = len(list(data_dir.glob('*/*.png'))) + len(list(data_dir.glob('p/*/*.png')))
print(f"Number of images: {image_count}")

class_names = train_ds.class_names
num_classes = len(class_names)
print(f"Class names: {class_names}")

plt.figure(figsize=(20, 10))
for images, labels in train_ds.take(1):
    for i in range(9):
        ax = plt.subplot(3, 3, i + 1)
        plt.imshow(images[i].numpy().astype("uint8"), interpolation='nearest', aspect='auto', cmap='gray')
        plt.title(class_names[labels[i]])
        plt.axis("off")
plt.suptitle("Training images", fontsize=30)
plt.show()

for image_batch, labels_batch in train_ds:
    print(image_batch.shape)
    print(labels_batch.shape)
    break


# --- Pipeline-optimering ---
# AUTOTUNE = tf.data.AUTOTUNE
# train_ds = train_ds.cache().shuffle(1000).prefetch(AUTOTUNE)
# val_ds   = val_ds.cache().prefetch(AUTOTUNE)

# --- Data augmentation ---
data_augmentation = tf.keras.Sequential([
    layers.RandomFlip("horizontal"),
    #layers.RandomZoom(0.2),
    layers.RandomContrast(0.4)
])

plt.figure(figsize=(10, 10))
for images, labels in train_ds.take(1):
    for i in range(9):
        # Add the image to a batch.
        image = tf.cast(tf.expand_dims(images[i], 0), tf.float32)
        
        augmented_image = data_augmentation(image)
        ax = plt.subplot(3, 3, i + 1)
        plt.imshow(augmented_image[0], interpolation='nearest', aspect='auto', cmap='gray')
        plt.title(class_names[labels[i]])
        plt.axis("off")
plt.suptitle("Augmented training images", fontsize=30)
plt.show()

train_ds = train_ds.repeat(5).shuffle(1000)
train_ds = train_ds.map(lambda x, y: (data_augmentation(x, training=True), y))

# --- Modell ---
model = keras.Sequential([    
    layers.Rescaling(1./255, input_shape=(img_height, img_width, 1), name="Input_image"),
    # layers.Input(shape=(img_height, img_width, 1), name="Input_image"),

    layers.Conv2D(32, (3, 3), activation="relu"),
    layers.MaxPooling2D(),

    layers.Conv2D(64, (3, 3), activation="relu"),
    layers.MaxPooling2D(),

    layers.Conv2D(128, (3, 3), activation="relu"),
    layers.MaxPooling2D(),

    layers.Flatten(),
    layers.Dense(64, activation="relu"),
    layers.Dense(num_classes, activation="softmax", name="Prediction")
])

earlystop = tf.keras.callbacks.EarlyStopping(monitor="val_loss", min_delta=0.1, patience=10, mode="min")

model.compile(
    optimizer=tf.keras.optimizers.Adam(learning_rate=0.0001),
    loss=tf.keras.losses.SparseCategoricalCrossentropy(reduction="sum"),
    metrics=[tf.keras.metrics.SparseCategoricalAccuracy()],
)

model.summary()

keras.utils.plot_model(model, "model.png", show_shapes=True)

# --- Train presence/no presence model ---
history = model.fit(
    train_ds,
    validation_data=val_ds,
    epochs=500,
    callbacks=[earlystop]
)

# --- Plotta träning/validering ---
plt.figure()
plt.style.use('default')
plt.plot(history.history["sparse_categorical_accuracy"], label="Training")
plt.plot(history.history["val_sparse_categorical_accuracy"], label="Validation")
plt.xlabel("Epochs")
plt.ylabel("Accuracy")
plt.legend()
plt.show()

model.save(f"{sys.argv[2]}.keras")

# --- Activities ---

activities_dir = pathlib.Path(f"{sys.argv[1]}/p/").with_suffix('')

train_activities_ds = tf.keras.preprocessing.image_dataset_from_directory(
    activities_dir,
    validation_split=0.2,
    subset="training",
    seed=123,
    color_mode="grayscale",
    image_size=(img_height, img_width),
    batch_size=batch_size,
    labels="inferred",
    label_mode="int",
    verbose=True
)

val_activities_ds = tf.keras.preprocessing.image_dataset_from_directory(
    activities_dir,
    validation_split=0.2,
    subset="validation",
    seed=123,
    color_mode="grayscale",
    image_size=(img_height, img_width),
    batch_size=batch_size,
    labels="inferred",
    label_mode="int",
    verbose=True
)

image_count = len(list(data_dir.glob('p/*/*.png')))
print(f"Number of images: {image_count}")

class_names = train_activities_ds.class_names
num_classes = len(class_names)
print(f"Class names: {class_names}")

plt.figure(figsize=(10, 10))
for images, labels in train_activities_ds.take(1):
    for i in range(9):
        ax = plt.subplot(3, 3, i + 1)
        plt.imshow(images[i].numpy().astype("uint8"), interpolation='nearest', aspect='auto', cmap='gray')
        plt.title(class_names[labels[i]])
        plt.axis("off")
plt.suptitle("Training images", fontsize=30)
plt.show()

for image_batch, labels_batch in train_activities_ds:
    print(image_batch.shape)
    print(labels_batch.shape)
    break

# --- Pipeline-optimering ---
# AUTOTUNE = tf.data.AUTOTUNE
# train_ds = train_ds.cache().shuffle(1000).prefetch(AUTOTUNE)
# val_ds   = val_ds.cache().prefetch(AUTOTUNE)

plt.figure(figsize=(10, 10))
for images, labels in train_activities_ds.take(1):
    for i in range(9):
        # Add the image to a batch.
        image = tf.cast(tf.expand_dims(images[i], 0), tf.float32)
        
        augmented_image = data_augmentation(image)
        ax = plt.subplot(3, 3, i + 1)
        plt.imshow(augmented_image[0], interpolation='nearest', aspect='auto', cmap='gray')
        plt.title(class_names[labels[i]])
        plt.axis("off")
plt.suptitle("Augmented training images", fontsize=30)
plt.show()

train_activities_ds = train_activities_ds.repeat(20).shuffle(1000)
train_activities_ds = train_activities_ds.map(lambda x, y: (data_augmentation(x, training=True), y))

# --- Modell ---
activity_model = keras.Sequential([    
    layers.Rescaling(1./255, input_shape=(img_height, img_width, 1), name="Input_image"),
    # layers.Input(shape=(img_height, img_width, 1), name="Input_image"),

    layers.Conv2D(32, (3, 3), activation="relu"),
    layers.MaxPooling2D(),

    layers.Conv2D(64, (3, 3), activation="relu"),
    layers.MaxPooling2D(),

    layers.Conv2D(128, (3, 3), activation="relu"),
    layers.MaxPooling2D(),

    layers.Flatten(),
    layers.Dense(64, activation="relu"),
    layers.Dense(num_classes, activation="softmax", name="Prediction")
])

earlystop = tf.keras.callbacks.EarlyStopping(monitor="val_loss", min_delta=0.1, patience=10, mode="min")

activity_model.compile(
    optimizer=tf.keras.optimizers.Adam(learning_rate=0.0001),
    loss=tf.keras.losses.SparseCategoricalCrossentropy(reduction="sum"),
    metrics=[tf.keras.metrics.SparseCategoricalAccuracy()],
)

# --- Train activities model ---
history = activity_model.fit(
    train_activities_ds,
    validation_data=val_activities_ds,
    epochs=500,
    callbacks=[earlystop]
)

# --- Plotta träning/validering ---
plt.figure()
plt.style.use('default')
plt.plot(history.history["sparse_categorical_accuracy"], label="Training")
plt.plot(history.history["val_sparse_categorical_accuracy"], label="Validation")
plt.xlabel("Epochs")
plt.ylabel("Accuracy")
plt.legend()
plt.show()

activity_model.save(f"{sys.argv[2]}_activities.keras")
