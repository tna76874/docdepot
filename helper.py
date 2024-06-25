#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
helper modules
"""
import os
import requests
import hashlib
from PIL import Image
from classify import *
import json

import PyPDF2
from reportlab.pdfgen import canvas
import io


class ImageAPI:
    def __init__(self, url='http://localhost:9000', loaded = None):
        if not loaded:
            raise ValueError("Must be initialized with FileLoader object")
            
        self.base_url = url
        self.loaded = loaded
        self.format = 'jpeg'
        self.size = 1500
        self.filename = os.path.splitext(os.path.basename(self.loaded.attributes.get('filename')))[0] or 'filename'
        
        self.fullfilename = f'{self.filename}.{self.format}'

    def _get_scaled_height(self, width, height):
        size = self.size
        # Bestimme das Verhältnis der aktuellen Dimensionen
        aspect_ratio = width / height
        
        if width > height:
            # Skaliere die Breite auf self.config['size']
            new_width = size
            new_height = size / aspect_ratio
        else:
            # Skaliere die Höhe auf self.config['size']
            new_height = size
            new_width = size * aspect_ratio
        
        # Gib die skalierten Dimensionen zurück
        return int(new_height)
    
    def _generate_pdf_from_list(self, pages):
        pdf_writer = PyPDF2.PdfWriter()

        for image_data in pages:
            if image_data==None:
                continue

            # Öffne das JPEG-Bild mit PIL
            image = Image.open(io.BytesIO(image_data))
            
            # Erstelle ein BytesIO-Objekt für das PDF
            buffer = io.BytesIO()

            # Erstelle ein PDF-Canvas
            pdf_canvas = canvas.Canvas(buffer)

            # Berechne die Größe der PDF-Seite basierend auf der Bildgröße
            pdf_canvas.setPageSize((image.width, image.height))

            # Füge das Bild in das PDF ein
            pdf_canvas.drawInlineImage(image, 0, 0)

            # Speichere das PDF-Canvas
            pdf_canvas.save()

            # Setze das Buffer-Objekt auf den Anfang zurück
            buffer.seek(0)

            # Füge die aktuelle Seite dem PDF-Schreiber hinzu
            pdf_writer.add_page(PyPDF2.PdfReader(buffer).pages[0])
        return pdf_writer

    def compress_pdf(self):
        try:
            # Erstelle ein PDF-Reader-Objekt
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(self.loaded.buffer))
    
            # Liste für die Speicherung der einzelnen io-Stream-Objekte
            output_streams = []
    
            # Durchlaufe jede Seite der PDF-Datei
            for page_num in range(len(pdf_reader.pages)):
                # Erstelle ein io-Stream-Objekt für jede Seite
                output_stream = io.BytesIO()
    
                # Erstelle ein PDF-Writer-Objekt
                pdf_writer = PyPDF2.PdfWriter()
    
                # Extrahiere die Seite
                page = pdf_reader.pages[page_num]
                
                # Bestimme die skalierte Höhe
                size = self._get_scaled_height(page.mediabox.width, page.mediabox.height)

                # Füge die Seite zum PDF-Writer hinzu
                pdf_writer.add_page(page)
    
                # Schreibe den Inhalt des PDF-Writer-Objekts in den io-Stream
                pdf_writer.write(output_stream)
    
                # Setze die Position des Streams auf den Anfang
                output_stream.seek(0)
    
                # Füge den io-Stream zur Liste hinzu
                output_streams.append((output_stream.getvalue(),size))
 
            converted_bytes = list()
            for image_data in output_streams:
                converted_bytes.append(self._convert(image_data[0], height = image_data[1], pdf=True))
            
            pdf_converted = self._generate_pdf_from_list(converted_bytes)

            with open('test.jpg', 'wb') as new_file:
                new_file.write(converted_bytes[0])
            
            buffer = io.BytesIO()
            pdf_converted.write(buffer)
            buffer.seek(0)
            
            return buffer.getvalue()
    
        except:
            return None
        
    def _convert(self, image_bytes, height = 1000, quality = 80, pdf=False):
        try:
            url = f'{self.base_url}/pipeline'
            operations = [
                {
                    "operation": "resize",
                    "params": {
                        "type": self.format,
                        "quality": quality,
                        "background": "255,255,255",
                        "stripmeta": "true",
                        "height": height,
                        "force": "true",
                    }
                }
            ]
            if pdf==False:
                operations = [
                                {
                                    "operation": "autorotate",
                                    "params": {
                                        "type": self.format,
                                    }
                                }
                             ] + operations
    
            files = {'file': (self.fullfilename, image_bytes)}
            params = {
                'operations': json.dumps(operations)
            }
    
            response = requests.post(url, params=params, files=files)
            if response.status_code == 200:
                return response.content
            else:
                print(response.text)
                return None
        except:
            return None
        
        
    def autorotate_and_resize(self):
        return self._convert(self.loaded.buffer)

class ShortHash:
    def __init__(self, input_string):
        self.input_string = input_string
        self.short_hash = self.get()

    def get(self):
        hash_object = hashlib.md5(self.input_string.encode())
        return hash_object.hexdigest()[:4]

class ChecksumCalculator:
    def __init__(self):
        self.sha256_hash = hashlib.sha256()

    def update_checksum(self, data):
        self.sha256_hash.update(data)

    def calc_from_object(self, obj):
        self.sha256_hash = hashlib.sha256()
        self.update_checksum(obj.read())

        checksum = self.sha256_hash.hexdigest()
        self.reset_file_position(obj)
        
        return checksum

    def calc_from_file(self, file_path):
        with open(file_path, 'rb') as file:
            data = file.read()
            self.update_checksum(data)

        checksum = self.sha256_hash.hexdigest()
        return checksum

    def reset_file_position(self, file_obj):
        file_obj.seek(0)

class PushNotify:
    def __init__(self, host=None, token=None, **kwargs):
        if host is None or token is None:
            raise ValueError("Host and token must be provided.")
        self.host = host
        self.token = token
        self.payload = {
                            "priority": 8,
                            "title": 'DocDepot',
                        }
        self.payload.update(kwargs)
        
    def send(self, message):
        url = f"{self.host}/message?token={self.token}"
        payload = self.payload.copy()
        payload['message'] = message
        response = requests.post(url, json=payload)
        return response.status_code == 200

class EnvironmentConfigProvider:
    def __init__(self):
        self.apikey = os.environ.get("DOCDEPOT_API_KEY", "test")
        self.default_redirect = os.environ.get("DOCDEPOT_DEFAULT_REDIRECT", None)
        self.enable_redirect = os.environ.get("DOCDEPOT_ENABLE_REDIRECT", "False").lower() == "true"
        self.show_info = os.environ.get("DOCDEPOT_SHOW_INFO", "False").lower() == "true"
        self.show_response_time = os.environ.get("DOCDEPOT_SHOW_RESPONSE_TIME", "False").lower() == "true"
        self.show_timestamp = os.environ.get("DOCDEPOT_SHOW_TIMESTAMP", "False").lower() == "true"
        self.github_repo = os.environ.get("DOCDEPOT_GITHUB_REPO", "https://github.com/tna76874/docdepot")
        self.cleanup_db_on_start = os.environ.get("DOCDEPOT_CLEANUP_ON_START", "True").lower() == "true"
        
        self.gotify_host = self._read_var('GOTIFY_HOST')
        self.gotify_token = self._read_var('GOTIFY_TOKEN')
        self.gotify_priority = int(self._read_var('GOTIFY_PRIORITY') or 8)
        
        self.imaginary_host = self._read_var('IMAGINARY_HOST')
        
        self.classify_model = self._read_var('DOCDEPOT_MODEL')
        self.classify_model_threshold = float(self._read_var('DOCDEPOT_MODEL_THRESHOLD') or 0.55)

        self.blur_threshold = float(self._read_var('DOCDEPOT_BLUR_THRESHOLD') or 40)
        
    def _read_var(self, var_name):
        value = os.environ.get(var_name)
        return value if value != "" else None

    def get_api_key(self):
        return self.apikey
    
    def _get_imaginary(self, loaded):
        if self.imaginary_host is not None:
            return ImageAPI(url = self.imaginary_host, loaded=loaded)
        return None
    
    def _get_gotify(self):
        if self.gotify_host is not None and self.gotify_token is not None:
            return PushNotify(self.gotify_host, self.gotify_token, title = 'DocDepot', priority = self.gotify_priority)
        return None
    
    def _get_classify(self):
        if not self.classify_model:
            return None
        
        if os.path.exists(self.classify_model):
            try:
                classifier = ImageClassifier(model_path=self.classify_model, threshold = self.classify_model_threshold)
                return classifier
            except:
                return None
        else:
            return None

    def _get_html_configs(self):
        html_configs = {
            "default_redirect": self.default_redirect,
            "show_info": self.show_info,
            "show_response_time": self.show_response_time,
            "show_timestamp": self.show_timestamp,
            "github_repo": self.github_repo,
            "enable_redirect" : self.enable_redirect,
        }
        return html_configs



if __name__ == '__main__':
    pass