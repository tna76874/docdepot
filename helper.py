#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
helper modules
"""
import os

class EnvironmentConfigProvider:
    def __init__(self):
        self.apikey = os.environ.get("DOCDEPOT_API_KEY", "test")
        self.default_redirect = os.environ.get("DOCDEPOT_DEFAULT_REDIRECT", None)
        self.show_info = os.environ.get("DOCDEPOT_SHOW_INFO", "False").lower() == "true"
        self.show_response_time = os.environ.get("DOCDEPOT_SHOW_RESPONSE_TIME", "False").lower() == "true"
        self.show_timestamp = os.environ.get("DOCDEPOT_SHOW_TIMESTAMP", "False").lower() == "true"
        self.github_repo = os.environ.get("DOCDEPOT_GITHUB_REPO", "https://github.com/tna76874/docdepot")
        self.cleanup_db_on_start = os.environ.get("DOCDEPOT_CLEANUP_ON_START", "True").lower() == "true"
        
    def _read_var(self, var_name):
        value = os.environ.get(var_name)
        return value if value != "" else None

    def get_api_key(self):
        return self.apikey


    def _get_html_configs(self):
        html_configs = {
            "default_redirect": self.default_redirect,
            "show_info": self.show_info,
            "show_response_time": self.show_response_time,
            "show_timestamp": self.show_timestamp,
            "github_repo": self.github_repo
        }
        return html_configs

if __name__ == '__main__':
    pass