#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Depose Files: A simple file deposition API using Flask.
"""

from flask import Flask, jsonify, send_file, render_template, request, url_for, redirect
from flask_restful import Api, Resource
import os
from docdepotdb import *
import ddclient
from datetime import datetime
import json
from functools import wraps
import hashlib
from helper import *

# Define directories and create them if they don't exist
datadir = 'data'
documentdir = f'{datadir}/documents'
attachmentdir = f'{datadir}/attachments'
_ = [os.makedirs(path) for path in [datadir, documentdir, attachmentdir] if not os.path.exists(path)]

# ENV VARS
env_vars = EnvironmentConfigProvider()
# Set default API key (you can also use environment variables)
apikey = env_vars.apikey
# default redirect target
default_redirect = env_vars.default_redirect
# WEBSITE SETTINGS
html_settings = env_vars._get_html_configs()

# read version as commit hash
commit_hash_file='COMMIT_HASH'
if os.path.exists(commit_hash_file):
    with open(commit_hash_file, 'r') as datei:
        commit_hash = datei.read().replace('\n', '')
    html_settings["github_repo"] += f'/tree/{commit_hash}'
else:
    commit_hash = None


# Initialize the DatabaseManager and cleanup expired files
db = DatabaseManager(data=f'{datadir}/data.db', docdir = documentdir)
if env_vars.cleanup_db_on_start:
    db.delete_expired_items()

# Initialize Flask app and API
app = Flask(__name__)
api = Api(app)

class AttachmentResource(Resource):
    def post(self):
        """
        Endpoint for adding an attachment to a document.

        Parameters:
        - token: Token for accessing the document.
        - name: Filename of the attachment.

        Returns:
        - aid: Attachment ID.
        """
        try:
            data = request.form
            file = request.files.get('file')

            if not file:
                return {"error": "file is required"}, 400

            # check if file is uploaded
            if not file.filename:
                return {"error": "file is required"}, 400
            
            # Check file size (max 15MB = 15 * 1024 * 1024 bytes)
            max_file_size = 15 * 1024 * 1024  # 15MB
            if len(file.read()) > max_file_size:
                return {"error": "Die Datei muss kleiner als 15MB sein!"}, 400
            file.seek(0)

            dbdata = {
                'token': data.get('token'),
                'name': file.filename,
            }

            # Add attachment to the database
            aid = db.add_attachment(**dbdata)

            if aid:
                # Save the attachment file to the ./attachments/ directory
                attachment_path = f'./{attachmentdir}/{aid}'
                file.save(attachment_path)
                response = {
                    "aid": aid,
                    "status": "success"
                }
                return response, 201
            else:
                response = {
                    "error": "Token not found",
                    "status": "error"
                }
                return response, 500
            
        except Exception as e:
            response = {
                "error": str(e),
                "status": "error"
            }
            return response, 500

class DocumentResource(Resource):
    def post(self):
        """
        Endpoint for adding a new document.

        Parameters:
        - title: Title of the document.
        - filename: Name of the file.
        - user_uid: User's unique identifier.
        - file: File to be uploaded.

        Returns:
        - token: Unique token for accessing the document.
        - did: Document ID.
        """
        try:
            auth_key = request.headers.get('Authorization')
            if auth_key != apikey:
                return jsonify({"error": "Unauthorized"}), 401

            data = request.form
            file = request.files.get('file')

            if not file:
                return {"error": "file is required"}, 400

            # check if file is uploaded
            if not file.filename:
                return {"error": "file is required"}, 400

            dbdata = {
                'title': data.get('title'),
                'filename': data.get('filename'),
                'user_uid': data.get('user_uid'),
            }

            # Add document to the database
            did = db.add_document(dbdata)

            # Save the file to the ./documents/ directory
            file_path = f'./{documentdir}/{did}'
            file.save(file_path)
            
            # Verify the checksum of the saved file
            with open(file_path, 'rb') as saved_file:
                saved_file_content = saved_file.read()
                saved_checksum = hashlib.sha256(saved_file_content).hexdigest()

            if data.get('checksum', None) != saved_checksum:
                # Delete the document and return an error if the checksums do not match
                db.delete_document(did)
                return {"error": "Checksum verification failed"}, 400


            # Add token for the document
            token = db.add_token(did)

            return {"token": token, "did": did}, 201
        except Exception as e:
            return {"error": str(e)}, 500

class GenerateTokenResource(Resource):
    def post(self):
        """
        Endpoint for generating a new token for a document.

        Request Body:
        {
            "did": "Document ID"
        }

        Returns:
        {
            "token": "Unique token for accessing the document."
        }
        """
        try:
            auth_key = request.headers.get('Authorization')
            if auth_key != apikey:
                return jsonify({"error": "Unauthorized"}), 401

            data = request.get_json()
            did = data.get('did')

            # Generate a new token for the document
            token = db.add_token(did)

            return {"token": token}, 201
        except Exception as e:
            return {"error": str(e)}, 500

class DeleteTokenResource(Resource):
    def delete(self):
        """
        Endpoint for deleting a token.

        Request Body:
        {
            "token_value": "Value of the token to be deleted."
        }
        """
        try:
            auth_key = request.headers.get('Authorization')
            if auth_key != apikey:
                return jsonify({"error": "Unauthorized"}), 401

            data = request.get_json()
            token_value = data.get('token_value')

            # Delete the token and associated events
            db.delete_token(token_value)

            return {"message": f"Token with value {token_value} deleted successfully."}, 200
        except Exception as e:
            return {"error": str(e)}, 500

class DeleteUserResource(Resource):
    def delete(self):
        """
        Endpoint for deleting a user and associated documents, tokens, and files.

        Request Body:
        {
            "uid": "User's unique identifier."
        }
        """
        try:
            auth_key = request.headers.get('Authorization')
            if auth_key != apikey:
                return jsonify({"error": "Unauthorized"}), 401

            data = request.get_json()
            uid = data.get('uid')

            # Delete the user and associated documents, tokens, and files
            db.delete_user(uid)

            return {"message": f"User with UID {uid} deleted successfully."}, 200
        except Exception as e:
            return {"error": str(e)}, 500

class UpdateTokenValidUntilResource(Resource):
    def put(self):
        """
        Endpoint for updating the 'valid_until' date of a token.

        Request Body:
        {
            "token_value": "Value of the token to be updated.",
            "valid_until": "New 'valid_until' date for the token."
        }
        """
        try:
            auth_key = request.headers.get('Authorization')
            if auth_key != apikey:
                return jsonify({"error": "Unauthorized"}), 401

            data = request.get_json()
            token_value = data.get('token_value')
            valid_until = data.get('valid_until')

            # Update the 'valid_until' date of the token
            db.update_token_valid_until(token_value, valid_until)

            return {"message": f"Token with value {token_value} updated successfully."}, 200
        except Exception as e:
            return {"error": str(e)}, 500

class AverageTimeForAllUsersResource(Resource):
    def get(self):
        """
        Endpoint for retrieving the average time span for each user between document upload time and the first token event.

        Returns:
        - A dictionary where keys are user UIDs and values are the average time spans as timedelta objects.
        """
        try:
            auth_key = request.headers.get('Authorization')
            if auth_key != apikey:
                return jsonify({"error": "Unauthorized"}), 401

            user_average_times_dt = db.calculate_average_time_for_all_users()
            user_average_times_seconds = {user: time.total_seconds() if time is not None else None for user, time in user_average_times_dt.items()}

            return user_average_times_seconds, 200
        except Exception as e:
            return {"error": str(e)}, 500
        
class RenameUsersResource(Resource):
    def post(self):
        """
        Endpoint for renaming users.

        Request Body:
        {
            "user_dict": {
                "old_uid": "New_UID",
                "another_old_uid": "Another_New_UID",
                ...
            }
        }
        """
        try:
            auth_key = request.headers.get('Authorization')
            if auth_key != apikey:
                return jsonify({"error": "Unauthorized"}), 401

            data = request.get_json()
            user_dict = data.get('user_dict')

            # Rename users based on the provided dictionary
            db.rename_users(user_dict)

            return {"message": "Users renamed successfully."}, 200
        except Exception as e:
            return {"error": str(e)}, 500
        
class DDClientVersionResource(Resource):
    def get(self):
        """
        Endpoint for retrieving the version of ddclient.

        Returns:
        - version: Version of ddclient.
        """
        try:
            return {"version": ddclient.__version__}, 200
        except Exception as e:
            return {"error": str(e)}, 500
        
def convert_datetimes_to_strings(data_func):
    """
    Decorator function to convert datetime objects to string representations.

    Parameters:
    - data_func: Function that retrieves data and returns a list of dictionaries.

    Returns:
    - Wrapper function that performs the datetime-to-string conversion.
    """
    @wraps(data_func)
    def wrapper(*args, **kwargs):
        try:
            auth_key = request.headers.get('Authorization')
            if auth_key != apikey:
                return jsonify({"error": "Unauthorized"}), 401

            # Retrieve data using the original function
            data = data_func(*args, **kwargs)

            # Convert datetime objects to strings before returning
            for entry in data:
                for key, value in entry.items():
                    if isinstance(value, datetime):
                        entry[key] = value.strftime('%Y-%m-%d %H:%M:%S.%f') if value else None

            return data if data else {"message": f"No {data_func.__name__} found."}, 200
        except Exception as e:
            return {"error": str(e)}, 500

    return wrapper

class GetEventsResource(Resource):
    @convert_datetimes_to_strings
    def get(self):
        """
        Endpoint for retrieving all events.

        Returns:
        - A list of dictionaries containing event information.
        """
        return db.get_events()

class GetDocumentsResource(Resource):
    @convert_datetimes_to_strings
    def get(self):
        """
        Endpoint for retrieving all documents.

        Returns:
        - A list of dictionaries containing document information.
        """
        return db.get_documents()

class GetUsersResource(Resource):
    @convert_datetimes_to_strings
    def get(self):
        """
        Endpoint for retrieving all users.

        Returns:
        - A list of dictionaries containing user information.
        """
        return db.get_users()
    
class UpdateUserExpiryDateResource(Resource):
    def put(self):
        """
        Endpoint for updating the 'valid_until' date of a user.

        Request Body:
        {
            "user_uid": "User UID to be updated.",
            "valid_until": "New 'valid_until' date for the user."
        }
        """
        try:
            auth_key = request.headers.get('Authorization')
            if auth_key != apikey:
                return jsonify({"error": "Unauthorized"}), 401

            data = request.get_json()
            user_uid = data.get('user_uid')
            valid_until = data.get('valid_until')

            # Update the 'valid_until' date of the user
            db.update_user_valid_until(user_uid, valid_until)

            return {"message": f"User with UID {user_uid} updated successfully."}, 200
        except Exception as e:
            return {"error": str(e)}, 500

class SetAllUsersExpiryDateResource(Resource):
    def put(self):
        """
        Endpoint for setting the 'valid_until' date for all users.

        Request Body:
        {
            "valid_until": "New 'valid_until' date for all users."
        }
        """
        try:
            auth_key = request.headers.get('Authorization')
            if auth_key != apikey:
                return jsonify({"error": "Unauthorized"}), 401

            data = request.get_json()
            valid_until = data.get('valid_until')

            # Set the 'valid_until' date for all users
            db.set_all_users_expiry_date(valid_until)

            return {"message": f"All users' expiry date set to {valid_until} successfully."}, 200
        except Exception as e:
            return {"error": str(e)}, 500
        
class CheckTokenValidityResource(Resource):
    def post(self):
        """
        Endpoint for checking the validity of a list of tokens.

        Request Body:
        {
            "token_list": ["token1", "token2", ...]
        }

        Returns:
        {
            "token_validity_dict": {
                "token1": True/False,
                "token2": True/False,
                ...
            }
        }
        """
        try:
            auth_key = request.headers.get('Authorization')
            if auth_key != apikey:
                return jsonify({"error": "Unauthorized"}), 401

            data = request.get_json()
            token_list = data.get('token_list')

            # Check the validity of the tokens
            token_validity_dict = db.are_tokens_valid(token_list)

            return {"token_validity_dict": token_validity_dict}, 200
        except Exception as e:
            return {"error": str(e)}, 500

class AddRedirectsResource(Resource):
    def post(self):
        """
        Endpoint for adding or updating redirects.

        Request Body:
        {
            "redirect_list": [
                {
                    "uid": "User's unique identifier",
                    "did": "Document ID",
                    "url": "Redirect URL",
                    "valid_until": "Valid until date (optional)",
                    "description": "This is a description",
                },
                ...
            ]
        }

        Returns:
        {
            "message": "Redirects added or updated successfully."
        }
        """
        try:
            auth_key = request.headers.get('Authorization')
            if auth_key != apikey:
                return jsonify({"error": "Unauthorized"}), 401

            data = request.get_json()
            redirect_list = data.get('redirect_list')

            # Add or update redirects
            db.add_redirects(redirect_list)

            return {"message": "Redirects added or updated successfully."}, 200
        except Exception as e:
            return {"error": str(e)}, 500

# Add routes to the API
api.add_resource(AttachmentResource, '/api/add_attachment')
api.add_resource(DocumentResource, '/api/add_document')
api.add_resource(GenerateTokenResource, '/api/generate_token')
api.add_resource(DeleteTokenResource, '/api/delete_token')
api.add_resource(DeleteUserResource, '/api/delete_user')
api.add_resource(UpdateTokenValidUntilResource, '/api/update_token_valid_until')
api.add_resource(AverageTimeForAllUsersResource, '/api/average_time_for_all_users')
api.add_resource(RenameUsersResource, '/api/rename_users')
api.add_resource(DDClientVersionResource, '/api/ddclient_version')
api.add_resource(GetEventsResource, '/api/get_events')
api.add_resource(GetDocumentsResource, '/api/get_documents')
api.add_resource(GetUsersResource, '/api/get_users')
api.add_resource(UpdateUserExpiryDateResource, '/api/update_user_expiry_date')
api.add_resource(SetAllUsersExpiryDateResource, '/api/set_all_users_expiry_date')
api.add_resource(CheckTokenValidityResource, '/api/check_token_validity')
api.add_resource(AddRedirectsResource, '/api/add_redirects')


@app.route('/r/<token>')
def handle_redirect(token):
    """
    Handle redirects based on the provided token.

    Parameters:
    - token: Unique token for performing the redirect.

    Returns:
    - Redirect to the URL associated with the token, if found.
    - Error if redirect not found.
    """
    try:
        if env_vars.enable_redirect == False:
            return redirect(url_for('render_index', token=token))
        
        document = db.get_document_from_token(token)
        if document:
            redirect_url = db.get_redirect(token)
            if redirect_url:
                return redirect(redirect_url['url'])
            elif default_redirect:
                return redirect(default_redirect)
            else:
                return redirect(url_for('render_index', token=token))
        else:
            return redirect(url_for('empty_page'))
    except Exception as e:
        return {"error": str(e)}, 500

@app.route('/document/<token>')
def get_documents(token):
    """
    Retrieve and serve the requested document.

    Parameters:
    - token: Unique token for accessing the document.

    Returns:
    - File response or error if document not found.
    """
    try:
        document = db.get_document_from_token(token)
        if document:
            current_time = datetime.utcnow()
            if document['valid_until'] >= current_time:
                db.add_event(token, event = 'download')
                file_path = f'{documentdir}/{document["did"]}'
                return send_file(file_path, as_attachment=False, download_name=document["filename"])
            else:
                return render_template('index.html', document_found=True, is_valid=False, html_settings=html_settings)
        else:
            return render_template('index.html', document_found=False, html_settings=html_settings)
    except Exception as e:
        return {"error": str(e)}, 500
    
@app.route('/attachment/<aid>')
def get_attachment(aid):
    """
    Retrieve and serve the requested attachment.

    Parameters:
    - aid: Attachment ID for accessing the attachment.

    Returns:
    - File response or error if attachment not found.
    """
    try:
        attachment_info = db.get_attachment_info(aid)
        if attachment_info:
            file_path = f'{attachmentdir}/{aid}'
            return send_file(file_path, as_attachment=False, download_name=attachment_info["name"])
        else:
            return redirect(url_for('render_index', token=token))
    except Exception as e:
        return {"error": str(e)}, 500

@app.route('/<token>')
def render_index(token):
    """
    Render the index page with document information.

    Parameters:
    - token: Unique token for accessing the document.

    Returns:
    - Rendered HTML template or error if document not found.
    """
    try:
        document = db.get_document_from_token(token)
        if document:
            current_time = datetime.utcnow()
            isvalid = document['valid_until'] >= current_time
            count = db.get_download_event_count(token)
            first_viewed = db.get_first_event_datetime(token)
            
            average_time = db.cluster_time_span(db.calculate_average_time_for_token(token))
            
            redirect_url = db.get_redirect(token)
            
            attachment_list = db.get_attachments_for_token(token)
            for attachment in attachment_list:
                attachment['uploaded'] = attachment['uploaded'].strftime('%d.%m.%Y %H:%M Uhr')

            
            if first_viewed!=None:
                first_viewed = first_viewed.strftime('%d.%m.%Y %H:%M:%S')
            return render_template(
                'index.html',
                token=token,
                document=document,
                count=count,
                first_viewed=first_viewed,
                is_valid=isvalid,
                average_time=average_time,
                html_settings = html_settings,
                redirect = redirect_url,
                attachment_list=attachment_list,
            )
        else:
            return render_template('index.html', document_found=False, html_settings=html_settings)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/')
def empty_page():
    """
    Return an empty page.

    Returns:
    - Empty HTML page.
    """
    return ''

@app.errorhandler(Exception)
def handle_error(error):
    """
    Handle errors and return a JSON response.

    Parameters:
    - error: The caught exception.

    Returns:
    - JSON response with error information.
    """
    return jsonify({"error": str(error)}), 500

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)
