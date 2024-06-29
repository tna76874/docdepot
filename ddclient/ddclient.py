#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DocDepot Client
"""
import requests
from urllib.parse import urljoin
from datetime import datetime, timedelta
import json
import argparse
import os
import hashlib



try:
    from ddclient import __version__
except:
    from __init__ import __version__


class DocDepotManager:
    def __init__(self, api_key, host='http://localhost:5000'):
        self.host = host
        self.api_key = api_key
        self.api_url = urljoin(self.host+'/','/api')
        self.success = False
        self.headers = {'Authorization': api_key}
        self.data={}

        # Check ddclient version compatibility
        server_ddclient_version = self.get_server_ddclient_version()
        local_ddclient_version = __version__

        if server_ddclient_version != local_ddclient_version:
            raise ValueError(f"DDClient version ({local_ddclient_version}) does not match server version ({server_ddclient_version}).")

    def check_token_validity(self, token_list):
        """
        Check the validity of a list of tokens.

        Parameters:
        - token_list: List of tokens to be checked.

        Returns:
        - token_validity_dict: Dictionary indicating the validity of each token in the list.
        """
        url = urljoin(self.api_url + '/', 'check_token_validity')
        response = requests.post(url, headers=self.headers, json={'token_list': token_list})

        if response.status_code == 200:
            self.success = True
            self.token_validity_dict = response.json().get('token_validity_dict', {})
            return self.token_validity_dict
        else:
            self.success = False
            try:
                error_message = response.json()
                return f"Error: {response.status_code}, {error_message}"
            except ValueError:
                return f"Error: {response.status_code}, Response content: {response.text}"

    def upload_pdf(self, **kwargs):
        """
        Uploads a PDF document to the server.

        Parameters:
        - title: Title of the document.
        - filename: Name of the file.
        - user_uid: User's unique identifier.
        - file_path: Path to the PDF file to be uploaded.

        Returns:
        - If successful, sets self.success to True and self.token to the server response.
        - If unsuccessful, sets self.success to False and returns an error message.

        Raises:
        - ValueError if required parameters are missing.
        - ValueError if the specified file_path does not exist.
        """

        # Ensure all required parameters are provided
        required_params = ['title', 'filename', 'user_uid', 'file_path']
        if not all(param in kwargs for param in required_params):
            raise ValueError("Missing required parameters. Make sure to provide title, filename, user_uid, and file_path.")

        # Check if the specified file exists
        file_path = kwargs['file_path']
        if not os.path.exists(file_path):
            raise ValueError(f"The file '{file_path}' does not exist.")
            
        # Calculate the checksum of the file
        with open(file_path, 'rb') as file:
            file_content = file.read()
            checksum = hashlib.sha256(file_content).hexdigest()

        # Prepare data for the request
        self.data = {
            'title': kwargs['title'],
            'filename': kwargs['filename'],
            'user_uid': kwargs['user_uid'],
            'allow_attachment' : kwargs.get('allow_attachment', True),
            'checksum': checksum,
        }

        # Prepare the files dictionary for the request
        files = {'file': (self.data['filename'], open(file_path, 'rb'))}

        # Construct the URL for the API endpoint
        url = urljoin(self.api_url + '/', 'add_document')

        # Make the POST request to upload the document
        response = requests.post(url, headers=self.headers, data=self.data, files=files)

        # Process the response
        if response.status_code == 201:
            self.success = True
            self.token = response.json()
        else:
            self.success = False
            try:
                error_message = response.json()
                return f"Error: {response.status_code}, {error_message}"
            except ValueError:
                return f"Error: {response.status_code}, Response content: {response.text}"

    def generate_summary_token_for_sid(self, sid):
        """
        Generate a new token for a document ID.
    
        Parameters:
        - sid: Session ID.
    
        Returns:
        - token: Unique token for doument summary.
        """
        url = urljoin(self.api_url+'/', 'create_summary_token')
        response = requests.post(url, headers=self.headers, json={'sid': sid})
    
        if response.status_code == 200:
            self.success = True
            return response.json().get('token')
        else:
            self.success = False
            try:
                error_message = response.json()
                return f"Error: {response.status_code}, {error_message}"
            except ValueError:
                return f"Error: {response.status_code}, Response content: {response.text}"

    def generate_token_for_document(self, did):
        """
        Generate a new token for a document ID.

        Parameters:
        - did: Document ID.

        Returns:
        - token: Unique token for accessing the document.
        """
        url = urljoin(self.api_url+'/', 'generate_token')
        response = requests.post(url, headers=self.headers, json={'did': did})

        if response.status_code == 201:
            self.success = True
            self.token = response.json()
        else:
            self.success = False
            try:
                error_message = response.json()
                return f"Error: {response.status_code}, {error_message}"
            except ValueError:
                return f"Error: {response.status_code}, Response content: {response.text}"

    def delete_token(self, token_value):
        """
        Delete a token.

        Parameters:
        - token_value: Value of the token to be deleted.

        Returns:
        - message: A success or error message.
        """
        url = urljoin(self.api_url+'/', 'delete_token')
        response = requests.delete(url, headers=self.headers, json={'token_value': token_value})

        if response.status_code == 200:
            self.success = True
            return {"message": f"Token with value {token_value} deleted successfully."}
        else:
            try:
                error_message = response.json()
                return f"Error: {response.status_code}, {error_message}"
            except ValueError:
                return f"Error: {response.status_code}, Response content: {response.text}"

    def delete_user(self, uid):
        """
        Delete a user and associated documents, tokens, and files.

        Parameters:
        - uid: User's unique identifier.

        Returns:
        - message: A success or error message.
        """
        url = urljoin(self.api_url+'/', 'delete_user')
        response = requests.delete(url, headers=self.headers, json={'uid': uid})

        if response.status_code == 200:
            self.success = True
            return {"message": f"User with UID {uid} deleted successfully."}
        else:
            try:
                error_message = response.json()
                return f"Error: {response.status_code}, {error_message}"
            except ValueError:
                return f"Error: {response.status_code}, Response content: {response.text}"

    def update_token_valid_until(self, token_value, valid_until):
        """
        Update the 'valid_until' date of a token.

        Parameters:
        - token_value: Value of the token to be updated.
        - new_valid_until: New 'valid_until' date for the token.

        Returns:
        - message: A success or error message.
        """
        url = urljoin(self.api_url+'/', 'update_token_valid_until')
        response = requests.put(url, headers=self.headers, json={'token_value': token_value, 'valid_until': valid_until})

        if response.status_code == 200:
            return {"message": f"Token with value {token_value} updated successfully."}
        else:
            try:
                error_message = response.json()
                return f"Error: {response.status_code}, {error_message}"
            except ValueError:
                return f"Error: {response.status_code}, Response content: {response.text}"
            
    def convert_str_to_datetime(self, data):
        """
        Convert string representations of datetime to datetime objects.

        Parameters:
        - data: Dictionary containing potential datetime strings.

        Returns:
        - Dictionary with datetime strings converted to datetime objects.
        """
        for key, value in data.items():
            if value is not None and isinstance(value, str):
                try:
                    data[key] = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    print('error')
                    pass  # Ignore if the conversion fails

        return data
            
    def get_average_times_for_all_users(self):
        """
        Retrieve the average time span for each user between document upload time and the first token event.

        Returns:
        - A dictionary where keys are user UIDs and values are the average time spans as timedelta objects.
        """
        url = urljoin(self.api_url + '/', 'average_time_for_all_users')
        response = requests.get(url, headers=self.headers)

        if response.status_code == 200:
            self.success = True
            user_average_times_dt = {user: timedelta(seconds=time) if time is not None else None for user, time in response.json().items()}
            self.data.update({'average_time':user_average_times_dt})
            return self.data['average_time']
        else:
            self.success = False
            try:
                error_message = response.json()
                return f"Error: {response.status_code}, {error_message}"
            except ValueError:
                return f"Error: {response.status_code}, Response content: {response.text}"
            
    def rename_users(self, user_dict):
        """
        Rename users.
    
        Parameters:
        - user_dict: Dictionary where keys are old UIDs and values are new UIDs.
    
        Returns:
        - message: A success or error message.
        """
        url = urljoin(self.api_url + '/', 'rename_users')
        response = requests.post(url, headers=self.headers, json={'user_dict': user_dict})
    
        if response.status_code == 200:
            self.success = True
            return {"message": "Users renamed successfully."}
        else:
            try:
                error_message = response.json()
                return f"Error: {response.status_code}, {error_message}"
            except ValueError:
                return f"Error: {response.status_code}, Response content: {response.text}"
            
    def get_server_ddclient_version(self):
        """
        Retrieve the supported ddclient version from the server.

        Returns:
        - version: Supported version of ddclient on the server.
        """
        try:
            url = urljoin(self.api_url + '/', 'ddclient_version')
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                return response.json().get('version')
            else:
                raise ValueError(f"Unable to retrieve ddclient version from the server. Status Code: {response.status_code}")
        except Exception as e:
            raise ValueError(f"Error retrieving ddclient version: {str(e)}")
            
    def get_events(self):
        """
        Retrieve all events.
    
        Returns:
        - A list of dictionaries containing event information.
        """
        url = urljoin(self.api_url + '/', 'get_events')
        response = requests.get(url, headers=self.headers)
    
        if response.status_code == 200:
            self.success = True
            events_info = response.json()
            return events_info if events_info else {"message": "No events found."}
        else:
            self.success = False
            try:
                error_message = response.json()
                return f"Error: {response.status_code}, {error_message}"
            except ValueError:
                return f"Error: {response.status_code}, Response content: {response.text}"
            
    def get_attachments(self):
        """
        Retrieve all attachments.
    
        Returns:
        - A list of dictionaries containing attachment information.
        """
        url = urljoin(self.api_url + '/', 'get_attachments')
        response = requests.get(url, headers=self.headers)
    
        if response.status_code == 200:
            self.success = True
            attachments_info = response.json()
            return attachments_info if attachments_info else {"message": "No attachments found."}
        else:
            self.success = False
            try:
                error_message = response.json()
                return f"Error: {response.status_code}, {error_message}"
            except ValueError:
                return f"Error: {response.status_code}, Response content: {response.text}"
            
    def get_documents(self):
        """
        Retrieve documents for all users.
    
        Returns:
        - A list of dictionaries containing document information.
        """
        url = urljoin(self.api_url + '/', 'get_documents')
        response = requests.get(url, headers=self.headers)
    
        if response.status_code == 200:
            self.success = True
            documents_info = response.json()
            return documents_info if documents_info else {"message": "No documents found."}
        else:
            self.success = False
            try:
                error_message = response.json()
                return f"Error: {response.status_code}, {error_message}"
            except ValueError:
                return f"Error: {response.status_code}, Response content: {response.text}"

    def get_users(self):
        """
        Retrieve information about all users.
    
        Returns:
        - A list of dictionaries containing user information.
        """
        url = urljoin(self.api_url + '/', 'get_users')
        response = requests.get(url, headers=self.headers)
    
        if response.status_code == 200:
            self.success = True
            users_info = response.json()
            return users_info if users_info else {"message": "No users found."}
        else:
            self.success = False
            try:
                error_message = response.json()
                return f"Error: {response.status_code}, {error_message}"
            except ValueError:
                return f"Error: {response.status_code}, Response content: {response.text}"
            
    def update_user_expiry_date(self, user_uid, valid_until):
        """
        Update the 'valid_until' date of a user.

        Parameters:
        - user_uid: User's unique identifier.
        - valid_until: New 'valid_until' date for the user.

        Returns:
        - message: A success or error message.
        """
        url = urljoin(self.api_url+'/', 'update_user_expiry_date')
        data = {'user_uid': user_uid, 'valid_until': valid_until}
        response = requests.put(url, headers=self.headers, json=data)

        if response.status_code == 200:
            self.success = True
            return {"message": f"User with UID {user_uid} updated successfully."}
        else:
            try:
                error_message = response.json()
                return f"Error: {response.status_code}, {error_message}"
            except ValueError:
                return f"Error: {response.status_code}, Response content: {response.text}"

    def set_all_users_expiry_date(self, valid_until):
        """
        Set the 'valid_until' date for all users.

        Parameters:
        - valid_until: New 'valid_until' date for all users.

        Returns:
        - message: A success or error message.
        """
        url = urljoin(self.api_url+'/', 'set_all_users_expiry_date')
        data = {'valid_until': valid_until}
        response = requests.put(url, headers=self.headers, json=data)

        if response.status_code == 200:
            self.success = True
            return {"message": f"All users' expiry date set to {valid_until} successfully."}
        else:
            try:
                error_message = response.json()
                return f"Error: {response.status_code}, {error_message}"
            except ValueError:
                return f"Error: {response.status_code}, Response content: {response.text}"
            

    def set_all_attachments_expiry_date(self, valid_until):
        """
        Set the 'valid_until' date for all attachments.

        Parameters:
        - valid_until: New 'valid_until' date for all attachments.

        Returns:
        - message: A success or error message.
        """
        if isinstance(valid_until, str):
            valid_until =  datetime.strptime(valid_until, '%Y-%m-%d').isoformat()
        elif isinstance(valid_until, datetime):
            valid_until = valid_until.isoformat()
            
        url = urljoin(self.api_url+'/', 'set_all_attachments_expiry_dates')
        data = {'expires': valid_until}
        response = requests.put(url, headers=self.headers, json=data)

        if response.status_code == 200:
            self.success = True
            return {"message": f"All attachments' expiry date set to {valid_until} successfully."}
        else:
            try:
                error_message = response.json()
                return f"Error: {response.status_code}, {error_message}"
            except ValueError:
                return f"Error: {response.status_code}, Response content: {response.text}"

    def add_redirects(self, redirect_list):
        """
        Füge Weiterleitungen aus einer Liste von Dictionaries zur Datenbank hinzu oder aktualisiere sie.

        :param redirect_list: Liste von Dictionaries, die Weiterleitungen repräsentieren.
        """
        url = urljoin(self.api_url + '/', 'add_redirects')
        response = requests.post(url, headers=self.headers, json={'redirect_list': redirect_list})

        if response.status_code == 200:
            self.success = True
            return {"message": "Redirects added or updated successfully."}
        else:
            self.success = False
            try:
                error_message = response.json()
                return f"Error: {response.status_code}, {error_message}"
            except ValueError:
                return f"Error: {response.status_code}, Response content: {response.text}"

    def get_data(self):
        if self.success==True:
            data = self.data
            if hasattr(self, 'token'):
                data.update(self.token)
            return data
        else:
            return None
        
def get_api_key():
    # Try to get API key from environment variable
    api_key = os.getenv('DOCDEPOT_API_KEY')
    if api_key:
        return api_key

    # If not found in environment variable, check if a file is specified
    key_file_path = os.getenv('DOCDEPOT_API_KEY_FILE')
    if key_file_path and os.path.isfile(key_file_path):
        with open(key_file_path, 'r') as file:
            return file.read().strip()

    # If not found in environment or file, raise an error
    raise ValueError("API key not found. Set DOCDEPOT_API_KEY environment variable or specify a key file with DOCDEPOT_API_KEY_FILE.")

def get_host():
    # Try to get host from environment variable
    host = os.getenv('DOCDEPOT_HOST')
    if host:
        return host

    # If not found in environment or file, use default host
    return 'http://localhost:5000'

def main():
    parser = argparse.ArgumentParser(description='DocDepot Client CLI')
    parser.add_argument('--host', type=str, default=get_host(), help='DocDepot server host URL')
    parser.add_argument('--action', type=str, choices=['upload', 'generate_token', 'delete_token', 'delete_user', 'update_token_valid_until', 'get_average_times'], help='Action to perform')
    parser.add_argument('--document_id', type=int, help='Document ID for token-related actions')
    parser.add_argument('--token_value', type=str, help='Token value for token-related actions')
    parser.add_argument('--valid_until', type=str, help='New valid_until value for update_token_valid_until action')
    parser.add_argument('--user_uid', type=str, help='User UID for user-related actions')
    parser.add_argument('--file_path', type=str, help='Path to the PDF file for upload action')

    args = parser.parse_args()

    # Get API key from environment or file
    api_key = get_api_key()

    doc_manager = DocDepotManager(api_key=api_key, host=args.host)

    if args.action == 'upload':
        if not args.title or not args.filename or not args.user_uid or not args.file_path:
            parser.error("For upload action, title, filename, user_uid, and file_path are required.")
        result = doc_manager.upload_pdf(title=args.title, filename=args.filename, user_uid=args.user_uid, file_path=args.file_path)
    elif args.action == 'generate_token':
        if not args.document_id:
            parser.error("For generate_token action, document_id is required.")
        result = doc_manager.generate_token_for_document(did=args.document_id)
    elif args.action == 'delete_token':
        if not args.token_value:
            parser.error("For delete_token action, token_value is required.")
        result = doc_manager.delete_token(token_value=args.token_value)
    elif args.action == 'delete_user':
        if not args.user_uid:
            parser.error("For delete_user action, user_uid is required.")
        result = doc_manager.delete_user(uid=args.user_uid)
    elif args.action == 'update_token_valid_until':
        if not args.token_value or not args.valid_until:
            parser.error("For update_token_valid_until action, token_value and valid_until are required.")
        result = doc_manager.update_token_valid_until(token_value=args.token_value, valid_until=args.valid_until)
    elif args.action == 'get_average_times':
        result = doc_manager.get_average_times_for_all_users()
    else:
        parser.error("Invalid action specified. Choose one of: upload, generate_token, delete_token, delete_user, update_token_valid_until, get_average_times")

    print(result)
    
if __name__ == '__main__':
    pass
    # Beispiel-Nutzung
    self = DocDepotManager('test', host='http://localhost:5000')

