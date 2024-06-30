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

# init gotify, if set
gotify = env_vars._get_gotify()

# init classifier
classify = env_vars._get_classify()

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
    db.delete_orphans()
    db._calculate_missing_checksums()
    db._delete_duplicates_from_attachments()
    db._db_migration()

# Initialize Flask app and API
app = Flask(__name__)
api = Api(app)

class AttachmentDownloadResource(Resource):
    """
    Resource to download the requested attachment.

    Parameters:
    - aid: Attachment ID for accessing the attachment.

    Returns:
    - File response or redirects to index if attachment not found.
    """
    def get(self, aid):
        try:
            auth_key = request.headers.get('Authorization')
            authorized = auth_key == apikey         
            
            attachment_info = db.get_attachment_info(aid)
            if attachment_info:
                file_path = f'{attachmentdir}/{aid}'
                if not attachment_info.get('allow_attachment', True) and not authorized:
                    return {"error": "File not found"}, 500
                return send_file(file_path, as_attachment=False, download_name=attachment_info["name"])
            else:
                return {"error": "File not found"}, 500
        except Exception as e:
            return {"error": str(e)}, 500

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
            
            performed_checks = CheckHistory()
            
            document = db.get_document_from_token(data.get('token'))
            if not document:
                performed_checks.add_check("Dokument")
                performed_checks.update_last(passed = False, description="Dokument nicht gefunden")
                return performed_checks.get_checks(), 400
            
            if not document.get('allow_attachment', False):
                performed_checks.add_check("Verbesserung", passed = False, description="Für dieses Dokument ist keine Verbesserung freigeschaltet.")
                return performed_checks.get_checks(), 400
            
            
            performed_checks.add_check("Abgabefrist")
            if not db._allow_attachment_for_token(data.get('token')):
                performed_checks.update_last(passed = False, description="Abgabefrist abgelaufen")
                return performed_checks.get_checks(), 400
            else:
                performed_checks.update_last(passed = True, description="Abgabefrist gültig")

            if not file:
                performed_checks.add_check("Datei-Upload")
                erformed_checks.update_last(passed = False, description="Keine Datei hochgeladen")
                return performed_checks.get_checks(), 400

            # check if file is uploaded
            if not file.filename:
                performed_checks.add_check("Dateiname")
                erformed_checks.update_last(passed = False, description="Kein Dateiname enthalten")
                return performed_checks.get_checks(), 400

            # load file
            loaded_file = FileLoader(file, filename=file.filename).load()
            print(loaded_file.attributes)
            
            # Check file size
            performed_checks.add_check("Dateigröße")
            if loaded_file.attributes.get('size')==False:
                performed_checks.update_last(passed = False, description=f"Die Datei muss kleiner als {loaded_file.max_size_mb()}MB sein!")
                return performed_checks.get_checks(), 400
            else:
                performed_checks.update_last(passed = True, description=f"Die Datei ist kleiner als {loaded_file.max_size_mb()}MB")
            
            # Check if mimetype is accepted
            performed_checks.add_check("Dateityp")
            if not loaded_file.attributes.get('accept_mimetype', False)==True:
                performed_checks.update_last(passed = False, description=f"Falscher Dateityp ({loaded_file.attributes.get('mimetype', '--')}). Erlaubte Dateien sind PDFs und Bilder.")
                return performed_checks.get_checks(), 400
            else:
                performed_checks.update_last(passed = True, description=f"Erlaubter Dateityp (PDFs und Bilder).")

            # do not allow duplicates on upload    
            performed_checks.add_check("Duplikat")
            if db.check_if_checksum_exists(loaded_file.attributes.get('sha256_hash')):
                performed_checks.update_last(passed = False, description="Die Datei ist bereits schon auf dem Server vorhanden.")
                return performed_checks.get_checks(), 400
            else:
                performed_checks.update_last(passed = True, description="Die Datei wurde vorher noch nicht hochgeladen.")

            # AI/QUALITY checks
            if classify:
                classify_result = classify.classify_image(loaded_file.buffer)
                if classify_result!=None:
                    if classify_result.get('blur', False)==False:
                        performed_checks.add_check("Bildschärfe")
                        performed_checks.update_last(passed = False, description="Das Bild ist unscharf.")
                        return performed_checks.get_checks(), 400
                    elif classify_result.get('cnn', False)==False:
                        performed_checks.add_check("AI-Check")
                        performed_checks.update_last(passed = False, description="Ungenügende Bildqualität. Bitte auf einen deutlichen und gut ausgeleuchteten Scan/Foto achten.")
                        return performed_checks.get_checks(), 400
                    elif classify_result.get('pass', False)==False:
                        performed_checks.add_check("Bild-Checks", passed=False, description="Ungültige Datei")
                        return performed_checks.get_checks(), 400
                    
                performed_checks.add_check("Bildschärfe", passed=True, description="Das Bild ist scharf.")
                performed_checks.add_check("AI-Check", passed=True, description="Die KI nimmt das Bild an.")

            # FILE COMPRESSION
            imaginary = env_vars._get_imaginary(loaded_file)
            if imaginary:
                if loaded_file.attributes.get('is_image', False):
                    compressed_buffer = imaginary.autorotate_and_resize()
                    if not compressed_buffer:
                        performed_checks.add_check("Bild-Kompression", passed=False, description="Fehler beim Komprimieren des Bildes. Bitte ein PDF hochladen.")
                        return performed_checks.get_checks(), 400
                    
                    loaded_file.buffer = compressed_buffer
                    loaded_file.attributes.update({'filename' : imaginary.fullfilename})
                    
                elif loaded_file.attributes.get('is_pdf', False):
                    compressed_buffer = imaginary.compress_pdf()
                    if not compressed_buffer:
                        performed_checks.add_check("PDF-Kompression", passed=False, description="Fehler beim Komprimieren des PDFs.")
                        return performed_checks.get_checks(), 400

                    loaded_file.buffer = compressed_buffer            
            
            ## ADDING TO DB

            
            dbdata = {
                'token': data.get('token'),
                'name': loaded_file.attributes.get('filename'),
                'checksum': loaded_file.attributes.get('sha256_hash'),
            }

            # Add attachment to the database
            aid = db.add_attachment(**dbdata)

            if aid:
                # Save the attachment file to the ./attachments/ directory
                attachment_path = f'./{attachmentdir}/{aid}'
                with open(attachment_path, 'wb') as new_file:
                    new_file.write(loaded_file.buffer)
    
                response = {
                    "aid": aid,
                    "status": "success"
                }
                if gotify:
                    hash_sid = ShortHash(document["user_uid"]).get()
                    gotify.send(f'{document["title"]}\n{hash_sid}\n{request.scheme}://{request.host}/{dbdata["token"]}')
                    
                return performed_checks.get_checks(), 201
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
                'checksum' : data.get('checksum', None),
                'allow_attachment' : data.get('allow_attachment') == 'True',
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

class CreateSummaryTokenResource(Resource):
    def post(self):
        """
        Endpoint for getting the summary token based on 'sid'.

        Request Body:
        {
            "sid": "Value of the sid to get the summary token for."
        }
        """
        try:
            auth_key = request.headers.get('Authorization')
            if auth_key != apikey:
                return jsonify({"error": "Unauthorized"}), 401

            data = request.get_json()
            sid = data.get('sid')

            if sid:
                sumtoken = db._create_summary_token_for_sid(sid)
                if sumtoken is not None:
                    return {"token": sumtoken}, 200
                else:
                    return {"message": "Summary token not found for the provided sid."}, 404
            else:
                return {"error": "sid is required in the request body."}, 400

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
        
class UpdateDocumentAttachmentStatusResource(Resource):
    def put(self):
        """
        Endpoint for updating the 'allow_attachment' status of documents.

        Request Body:
        {
            "doc_status_list": [
                {"did": "Document ID 1", "allow_attachment": true},
                {"did": "Document ID 2", "allow_attachment": false},
                ...
            ]
        }
        """
        try:
            auth_key = request.headers.get('Authorization')
            if auth_key != apikey:
                return jsonify({"error": "Unauthorized"}), 401

            data = request.get_json()
            doc_status_list = data.get('doc_status_list')

            # Update the 'allow_attachment' status of documents
            db.update_document_attachment_status(doc_status_list)

            return {"message": "Document attachment status updated successfully."}, 200
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

class GetAttachmentListResource(Resource):
    @convert_datetimes_to_strings
    def get(self):
        """
        Endpoint for retrieving all attachments.

        Returns:
        - A list of dictionaries containing attachment information.
        """
        return db.get_all_attachments()

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
        
class SetAllAttachmentsExpiryDateResource(Resource):
    def put(self):
        """
        Endpoint for setting the 'allow_until' date for all tokens.

        Request Body:
        {
            "expires": "isoformat"
        }
        """
        try:
            auth_key = request.headers.get('Authorization')
            if auth_key != apikey:
                return jsonify({"error": "Unauthorized"}), 401

            data = request.get_json()
            valid_until = data.get('expires')
            if not valid_until:
                return {"error": "missing expiry date"}, 500

            db.set_all_attachment_deadlines(valid_until)

            return {"message": f"successfully set deadlines."}, 200
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
api.add_resource(AttachmentDownloadResource, '/attachment/<aid>')
api.add_resource(AttachmentResource, '/api/add_attachment')
api.add_resource(DocumentResource, '/api/add_document')
api.add_resource(GenerateTokenResource, '/api/generate_token')
api.add_resource(DeleteTokenResource, '/api/delete_token')
api.add_resource(DeleteUserResource, '/api/delete_user')
api.add_resource(UpdateTokenValidUntilResource, '/api/update_token_valid_until')
api.add_resource(UpdateDocumentAttachmentStatusResource, '/api/update_document_attachment_status')
api.add_resource(AverageTimeForAllUsersResource, '/api/average_time_for_all_users')
api.add_resource(RenameUsersResource, '/api/rename_users')
api.add_resource(DDClientVersionResource, '/api/ddclient_version')
api.add_resource(GetEventsResource, '/api/get_events')
api.add_resource(GetDocumentsResource, '/api/get_documents')
api.add_resource(GetUsersResource, '/api/get_users')
api.add_resource(GetAttachmentListResource, '/api/get_attachments')
api.add_resource(CreateSummaryTokenResource, '/api/create_summary_token')
api.add_resource(UpdateUserExpiryDateResource, '/api/update_user_expiry_date')
api.add_resource(SetAllUsersExpiryDateResource, '/api/set_all_users_expiry_date')
api.add_resource(SetAllAttachmentsExpiryDateResource, '/api/set_all_attachments_expiry_dates')
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
                password = request.args.get('p')
                loaded_file = FileLoader(file_path, filename=document["filename"], password = password).load()

                return send_file(loaded_file.get_bytestream(), as_attachment=False, download_name=loaded_file.attributes.get('filename'))
            else:
                return render_template('main.html', page_name='document', document_found=True, is_valid=False, html_settings=html_settings)
        else:
            return render_template('main.html', page_name='document', document_found=False, html_settings=html_settings)
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
                
            attachment_info = {
                'is_allowed': db._allow_attachment_for_token(token),
                'allow_until': db._get_deadline_for_attachment(token).strftime('%d.%m.%Y %H:%M Uhr') if db._get_deadline_for_attachment(token) else None,
            }
            
            return render_template(
                'main.html',
                page_name='document',
                token=token,
                password = request.args.get('p'),
                document=document,
                count=count,
                first_viewed=first_viewed,
                is_valid=isvalid,
                average_time=average_time,
                html_settings = html_settings,
                redirect = redirect_url,
                attachment_list=attachment_list,
                attachment_info=attachment_info,
            )
        else:
            return render_template('main.html', page_name='document', document_found=False, html_settings=html_settings)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/s/<summarytoken>')
def render_summary(summarytoken):
    """
    Render the summary page with summary token information.

    Parameters:
    - summarytoken: Unique summary token for accessing the summary.

    Returns:
    - Rendered HTML template or redirect to empty_page if summary token not found.
    """
    try:
        summary_info = db._get_tokens_for_sid_from_summary(summarytoken)
        
        if summary_info:
            db._add_summary_click_event(summarytoken)
            return render_template(
                'main.html',
                page_name='summary',
                password = request.args.get('p'),
                summary_token=summarytoken,
                summary_info=summary_info,
                html_settings=html_settings
            )
        else:
            return redirect(url_for('empty_page'))
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
