#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Depose Files: A simple file deposition API using Flask.
"""

from flask import Flask, jsonify, send_file, render_template, request
from flask_restful import Api, Resource
import os
from deposerdb import *
from datetime import datetime

# Define directories and create them if they don't exist
datadir = 'data'
documentdir = f'{datadir}/documents'
_ = [os.makedirs(path) for path in [datadir, documentdir] if not os.path.exists(path)]

# Set default API key (you can also use environment variables)
apikey = os.environ.get("DEPOSER_API_KEY")
if isinstance(apikey, type(None)):
    apikey = 'test'

# Initialize the DatabaseManager
db = DatabaseManager(data=f'{datadir}/data.db', docdir = documentdir)

# Initialize Flask app and API
app = Flask(__name__)
api = Api(app)

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

            dbdata = {
                'title': data.get('title'),
                'filename': data.get('filename'),
                'user_uid': data.get('user_uid'),
            }

            # Add document to the database
            did = db.add_document(dbdata)

            if not file:
                return {"error": "file is required"}, 400

            # Save the file to the ./documents/ directory
            file_path = f'./{documentdir}/{did}'
            file.save(file_path)

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

# Add routes to the API
api.add_resource(DocumentResource, '/api/add_document')
api.add_resource(GenerateTokenResource, '/api/generate_token')
api.add_resource(DeleteTokenResource, '/api/delete_token')
api.add_resource(DeleteUserResource, '/api/delete_user')
api.add_resource(UpdateTokenValidUntilResource, '/api/update_token_valid_until')


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
                db.add_event(token)
                file_path = f'{documentdir}/{document["did"]}'
                return send_file(file_path, as_attachment=False, download_name=document["filename"])
            else:
                return render_template('token_expired.html', expired=document['valid_until'].strftime('%Y-%m-%d %H:%M:%S'))
        else:
            return {"error": "Document not found"}, 404
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
            if document['valid_until'] >= current_time:
                count = db.get_download_event_count(token)
                first_viewed = db.get_first_event_datetime(token)
                if first_viewed!=None:
                    first_viewed = first_viewed.strftime('%d.%m.%Y %H:%M:%S')
                return render_template('index.html', token=token, document=document, count=count, first_viewed=first_viewed)
            else:
                return render_template('token_expired.html', expired=document['valid_until'].strftime('%Y-%m-%d %H:%M:%S'))
        else:
            return jsonify({"error": "Document not found"}), 404
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
    app.run(debug=True)
