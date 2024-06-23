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

class ImageClassifier:
    def __init__(self, model_path = './data/model.keras', threshold = 0.55):
        self.model = load_model(model_path)
        self.threshold = threshold

    def classify_image(self, image_input):
        try:
            if isinstance(image_input, str):
                if not os.path.isfile(image_input):
                    raise FileNotFoundError(f'Die Datei {image_input} wurde nicht gefunden.')

                try:
                    Image.open(image_input)
                except IOError:
                    raise IOError(f'Die Datei {image_input} konnte nicht als Bild geöffnet werden.')

                img = image.load_img(image_input, target_size=(150, 150))
            else:  
                try:
                    image_data = image_input.read()
                    image_input.seek(0)
                    img = image.load_img(BytesIO(image_data), target_size=(150, 150))
                except Exception as e:
                    print(f'IMPORT ERROR {e}')
                    return None

            img_array = image.img_to_array(img)
            img_array = np.expand_dims(img_array, axis=0)
            img_array /= 255.0  # Normalisierung

            # Vorhersage
            prediction = self.model.predict(img_array)
            status = True if prediction[0] < self.threshold else False
            
            return {'status' : status, 'prediction' : prediction}
        except Exception as e:
            print(f'{e}')
            return None

# Beispiel zur Verwendung der Klasse:
if __name__ == '__main__':
    classifier = ImageClassifier()

    # Beispiel für einen Dateipfad
    img_path = os.path.abspath('/home/lukas/Dokumente/image_metrik/train (Kopieren)/schlecht/17044626190426350044157406149944.jpg')
    result = classifier.classify_image(img_path)
    print(f'Ergebnis der Klassifizierung: {result}')
    
    
    with open(img_path, 'rb') as image_file:
        image_data = image_file.read()
        result = classifier.classify_image(image_data)
        print(f'Ergebnis der Klassifizierung: {result}')

