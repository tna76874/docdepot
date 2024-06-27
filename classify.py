#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Tools
"""
import os
import requests
import numpy as np
from PIL import Image
from io import BytesIO
import cv2

import magic
import mimetypes
from functools import wraps
import hashlib

def none_on_exception(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # print(f'Error: {e}')
            return None
    return wrapper

class FileLoader:
    def __init__(self, file_input, max_file_size = 15 * 1024 * 1024, filename = None):
        self.attributes =   {
                            'filename' : filename,
                            }
        self.max_file_size = max_file_size
        self.load_buffer(file_input)

    def __del__(self):
        self._close_file()
        
    def load(self):
        self.get_mimetype()
        self.calc_checksum()
        self.check_filesize()
        
        self._close_file()
        
        return self

    def max_size_mb(self):
        return self.max_file_size / (1024 * 1024)
    
    @none_on_exception
    def _check_if_is_image(self):
        image_mimetypes = [mimetype for mimetype in mimetypes.types_map.values() if mimetype.startswith('image')] + ['image/heic']
        self.attributes.update({'is_image': self.attributes.get('mimetype') in image_mimetypes})
                                
    @none_on_exception
    def _check_if_is_pdf(self):
        pdf_mimetypes = [mime_type for mime_type in mimetypes.types_map.values() if 'pdf' in mime_type]
        self.attributes.update({'is_pdf': self.attributes.get('mimetype') in pdf_mimetypes})
        
    @none_on_exception
    def _check_if_filetype_is_accepted(self):
        accept_file_mimetype = self.attributes.get('is_pdf', False) or self.attributes.get('is_image', False)
        self.attributes.update({'accept_mimetype': accept_file_mimetype})

    @none_on_exception
    def check_filesize(self):
        self.attributes.update({'size': len(self.buffer) <= self.max_file_size})

    @none_on_exception
    def calc_checksum(self):
        sha256_hash = hashlib.sha256()
        sha256_hash.update(self.buffer)
        self.sha256_hash = sha256_hash.hexdigest()
        self.attributes.update({'sha256_hash':self.sha256_hash})
    
    @none_on_exception
    def get_mimetype(self):
        mime = magic.Magic(mime=True)
        self.mime_type = mime.from_buffer(self.buffer)  
        self.attributes.update({'mimetype':self.mime_type})
        
        self._check_if_is_image()
        self._check_if_is_pdf()
        self._check_if_filetype_is_accepted()
        
    @none_on_exception
    def _open_file(self, file_input):
        self.file = open(file_input, 'rb')
        
    @none_on_exception
    def _read_file(self):
        file_read = self.file.read()
        self.file.seek(0)
        return file_read

    @none_on_exception
    def _close_file(self):
        self.file.close()
    
    @none_on_exception
    def load_buffer(self, file_input):
        if isinstance(file_input, str):
            if not os.path.isfile(file_input):
                raise FileNotFoundError(f'Die Datei {file_input} wurde nicht gefunden.')
            self._open_file(file_input)
        else:
            self.file = file_input
        
        self.buffer = self._read_file()

class DetectBlur:
    def __init__(self, threshold=40):
        self.threshold = threshold

    def detect_blur(self, file_buffer):
        try:           
            # Konvertiere die Binärdaten in ein numpy-Array
            img_array = np.frombuffer(file_buffer, dtype=np.uint8)
            
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
        except:
            return {'status' : False, 'variance': None}

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
    def __init__(self, url = None, api_key = None, threshold=0.55):
        self.url = url
        self.api_key = api_key
        self.threshold = threshold

    def classify_image(self, file_buffer):
        try:
            headers = {'Authorization': self.api_key, 'Accept': 'multipart/form-data'}
            files = {'image': file_buffer}

            # Sende die POST-Anfrage an den Endpoint mit dem Bild als Datei
            response = requests.post(self.url + '/rate', headers=headers, files=files)

            if response.status_code == 200:
                prediction = response.json().get('result')
                if not prediction:
                    return None
                prediction = float(prediction)
                status = True if prediction < self.threshold else False
                return {'status': status, 'prediction': prediction}
            else:
                print(f'Fehler beim Senden der Anfrage. Statuscode: {response.status_code}')
                return None

        except Exception as e:
            print(f'Fehler beim Klassifizieren des Bildes: {e}')
            return None

if __name__ == '__main__':
    pass

