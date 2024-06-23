#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Tools
"""
import os
import numpy as np
import tensorflow as tf
from tensorflow.keras.preprocessing import image
from tensorflow.keras.models import load_model
from PIL import Image
from io import BytesIO
import cv2

tf.config.set_visible_devices([], 'GPU')

class DetectBlur:
    def __init__(self, threshold=40):
        self.threshold = threshold

    def detect_blur(self, image_input):
        # Read the image
        img_loaded = ImageLoader().load_image(image_input)
        if not img_loaded:
            return None
        
        # Konvertiere die Binärdaten in ein numpy-Array
        img_array = np.frombuffer(img_loaded, dtype=np.uint8)
        
        # Lade das Bild mit OpenCV aus dem numpy-Array
        image = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        
        # Convert image to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Apply binary thresholding for bright spot detection
        _, binary_image = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)

        # Apply Laplacian filter for edge detection
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)

        # Calculate maximum intensity and variance
        _, max_val, _, _ = cv2.minMaxLoc(gray)
        laplacian_variance = laplacian.var()

        # Initialize result variables
        blur_text = f"Not Blurry ({laplacian_variance})"

        # Check blur condition based on variance of Laplacian image
        is_blurred = laplacian_variance < self.threshold
        if is_blurred:
            blur_text = f"Blurry ({laplacian_variance})"

        return {'status' : is_blurred, 'variance': laplacian_variance}

class ImageLoader:
    def __init__(self):
        pass
    
    def load_image(self, image_input):
        try:
            if isinstance(image_input, str):
                if not os.path.isfile(image_input):
                    raise FileNotFoundError(f'Die Datei {image_input} wurde nicht gefunden.')

                try:
                    Image.open(image_input)
                    with open(image_input, 'rb') as image_file:
                        img = image_file.read()
                        
                except IOError:
                    raise IOError(f'Die Datei {image_input} konnte nicht als Bild geöffnet werden.')

            else:
                img = image_input.read()
                image_input.seek(0)

            return img
        
        except Exception as e:
            print(f'Error loading image: {e}')
            return None

class ImageClassifier:
    def __init__(self, model_path = './data/model.keras', threshold = 0.55):
        self.model = load_model(model_path)
        self.threshold = threshold

    def classify_image(self, image_input):     
        try:
            img_loaded = ImageLoader().load_image(image_input)
            if not img_loaded:
                return None
            
            img = image.load_img(BytesIO(img_loaded), target_size=(150, 150))

            img_array = image.img_to_array(img)
            img_array = np.expand_dims(img_array, axis=0)
            img_array /= 255.0  # Normalisierung

            # Vorhersage
            prediction = self.model.predict(img_array)
            status = True if prediction[0] < self.threshold else False
            
            return {'status' : status, 'prediction' : prediction}
        
        except Exception as e:
            print(f'AI CLASSIFY: {e}')
            return None

if __name__ == '__main__':
    pass

