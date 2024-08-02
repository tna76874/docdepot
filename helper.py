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

from cryptography.fernet import Fernet
from datetime import datetime, timedelta
import urllib

import PyPDF2
from reportlab.pdfgen import canvas
import io

class CheckHistory:
    def __init__(self):
        self.performed_checks = []

    def add_check(self, short, passed = None, description = None):
        self.performed_checks.append({"passed": passed, "description": description, "short": short})

    def get_checks(self):
        return self.performed_checks
    
    def _get_checks_string(self):
        checks_string = ""
        for check in self.performed_checks:
            checks_string += f"{check['short']}: {'Passed' if check['passed'] else 'Failed'} - {check['description']}\n"
        return checks_string

    def _get_failed_checks_string(self):
        failed_checks_string = ""
        for check in self.performed_checks:
            if check["passed"] == False:
                failed_checks_string += f"{check['short']}: Failed\n"
        return failed_checks_string

    def update_last(self, passed=None, description=None, short=None):
        if self.performed_checks:
            last_check = self.performed_checks[-1]
            if passed is not None:
                last_check["passed"] = passed
            if description is not None:
                last_check["description"] = description
            if short is not None:
                last_check["short"] = short

    def _is_passed(self):
        for check in self.performed_checks:
            if check["passed"] == False:
                return False
        return True

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
            
            buffer = io.BytesIO()
            pdf_converted.write(buffer)
            buffer.seek(0)
            
            return buffer.getvalue()
    
        except:
            return None

    @none_on_exception
    def _convert(self, image_bytes, height = 1000, quality = 80, pdf=False):
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

        return self._convert_from_operations(image_bytes, operations=operations)

    @none_on_exception
    def _convert_from_operations(self, image_bytes, operations=[]):
        url = f'{self.base_url}/pipeline'

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
        
    @none_on_exception
    def autorotate_and_resize(self):
        return self._convert(self.loaded.buffer, height = self.size)
    
    @none_on_exception
    def image_to_jpeg(self):
        operations = [
            {
                "operation": "convert",
                "params": {
                    "type": self.format,
                    "quality": 100,
                    "background": "255,255,255",
                    "stripmeta": "true",
                    "force": "true",
                }
            }
        ]
        return self._convert_from_operations(self.loaded.buffer, operations = operations)

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
    
class CryptCheckSum:
    def __init__(self, **kwargs):
        self.key = kwargs.get('key')
        if self.key is None:
            raise ValueError("Missing key")
        
        self.fernet = Fernet(self.key.encode('utf-8'))
        self.urlsafe = kwargs.get('urlsafe', True)
        

    def encrypt(self, **kwargs):
        """Verschlüsselt die übergebenen Argumente in einem JSON-Format."""
        # Erstelle ein Dictionary mit den Werten

        data = {
            'checksum': kwargs.get('checksum'),
            'aid': kwargs.get('aid'),
            'user_id': kwargs.get('user_id'),
            'uploaded': self._parse_time(kwargs.get('uploaded')).isoformat() if kwargs.get('uploaded') else None,
            'doc_upload_time': self._parse_time(kwargs.get('doc_upload_time')).isoformat() if kwargs.get('doc_upload_time') else None,
            'did': kwargs.get('did'),
            'now' : datetime.now().isoformat(),
        }

        # Konvertiere das Dictionary in einen JSON-String
        json_data = json.dumps(data)

        # Verschlüsseln des JSON-Strings
        encrypted_data = self.fernet.encrypt(json_data.encode()).decode('utf-8')

        if self.urlsafe:
            encrypted_data = urllib.parse.quote_plus(encrypted_data)

        return encrypted_data

    def decrypt(self, encrypted_string):
        try:
            """Entschlüsselt den gegebenen String und gibt ein Dictionary zurück."""
            if self.urlsafe:
                encrypted_string = urllib.parse.unquote(encrypted_string)

            encrypted_data = encrypted_string.encode('utf-8')
    
            decrypted_data = self.fernet.decrypt(encrypted_data)
    
            json_data = decrypted_data.decode('utf-8')
    
            data = json.loads(json_data)
    
            if 'upload_time' in data and data['upload_time'] is not None:
                data['upload_time'] = datetime.fromisoformat(data['upload_time'])
            if 'did_upload_time' in data and data['did_upload_time'] is not None:
                data['did_upload_time'] = datetime.fromisoformat(data['did_upload_time'])
    
            return data
        except:
            return None

    @staticmethod
    def _validate_fernet_key(key):
        """Überprüft, ob der gegebene Fernet-Schlüssel gültig ist."""
        try:
            fernet = Fernet(key)
            test_data = b'test'
            encrypted_data = fernet.encrypt(test_data)
            fernet.decrypt(encrypted_data)
            return True
        except:
            return False

    @staticmethod
    def generate_key():
        """Generiert einen neuen Fernet-Key."""
        return Fernet.generate_key().decode('utf-8')

    @staticmethod
    def _parse_time(upload_time):
        """Parst die upload_time und gibt ein datetime-Objekt zurück."""
        if isinstance(upload_time, datetime):
            return upload_time
        
        if isinstance(upload_time, str):
            formats = [
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d",
                "%d.%m.%Y",
            ]
            for fmt in formats:
                try:
                    return datetime.strptime(upload_time, fmt)
                except ValueError:
                    continue
        
        raise ValueError("upload_time muss ein datetime-Objekt oder ein gültiger Zeitstring sein.")

class TimedeltaFormatter:
    def __init__(self, td):
        if not isinstance(td, timedelta):
            raise ValueError("Das Argument muss ein timedelta-Objekt sein.")
        self.td = td

    def format(self):
        total_seconds = int(self.td.total_seconds())
        days = total_seconds // 86400
        hours = (total_seconds % 86400) // 3600
        minutes = (total_seconds % 3600) // 60

        parts = []
        if days > 0:
            parts.append(f"{days} Tag{'en' if days > 1 else ''}")
        if hours > 0 or days > 0:
            parts.append(f"{hours} Stunde{'n' if hours != 1 else ''}")
        if minutes > 0 or hours > 0 or days > 0:
            parts.append(f"{minutes} Minute{'n' if minutes != 1 else ''}")

        return ', '.join(parts) if parts else '0 Minuten'

class EnvironmentConfigProvider:
    def __init__(self):
        self.apikey = os.environ.get("DOCDEPOT_API_KEY", "test")
        self.default_redirect = os.environ.get("DOCDEPOT_DEFAULT_REDIRECT", None)
        self.grace_minutes = os.environ.get("DOCDEPOT_GRACE_MINUTES", 0)
        self.fernet_key = os.environ.get("DOCDEPOT_FERNET_KEY")
        
        if CryptCheckSum._validate_fernet_key(self.fernet_key)==False:
            raise ValueError("Invalid Fernet key")
        
        
        self.default_attachment_days = os.environ.get("DOCDEPOT_DAYS_TO_ALLOW_ATTACHMENT", 14)
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
        
        self.classify_host = self._read_var('CNN_HOST')
        self.classify_key = self._read_var('CNN_API_KEY')
        self.classify_model_threshold = float(self._read_var('DOCDEPOT_MODEL_THRESHOLD') or 0.55)

        self.blur_threshold = float(self._read_var('DOCDEPOT_BLUR_THRESHOLD') or 40)

    def get_grace_minutes(self):
        try:
            return int(self.grace_minutes)
        except:
            return 0
    
    def get_default_attachment_days(self):
        try:
            return int(self.default_attachment_days)
        except:
            return 14
        
    def _read_var(self, var_name):
        value = os.environ.get(var_name)
        return value if value != "" else None

    def get_api_key(self):
        return self.apikey
    
    def _get_imaginary(self, loaded):
        if self.imaginary_host is not None:
            return ImageAPI(url = self.imaginary_host, loaded=loaded)
        return None
    
    def _get_gotify(self, title = 'DocDepot'):
        if self.gotify_host is not None and self.gotify_token is not None:
            return PushNotify(self.gotify_host, self.gotify_token, title = title, priority = self.gotify_priority)
        return None
    
    def _get_classify(self):
        if (not self.classify_host) or (not self.classify_key):
            return None
        
        try:
            classifier = ImageClassifier(url=self.classify_host, api_key = self.classify_key, threshold = self.classify_model_threshold)
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
