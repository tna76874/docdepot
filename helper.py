#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
helper modules
"""
import os
import requests
import hashlib
from classify import *

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
        
        self.classify_model = self._read_var('DOCDEPOT_MODEL')
        self.classify_model_threshold = float(self._read_var('DOCDEPOT_MODEL_THRESHOLD') or 0.55)

        self.blur_threshold = float(self._read_var('DOCDEPOT_BLUR_THRESHOLD') or 40)
        
    def _read_var(self, var_name):
        value = os.environ.get(var_name)
        return value if value != "" else None

    def get_api_key(self):
        return self.apikey
    
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