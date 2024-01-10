#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A simple database management system for storing users, documents, tokens, and events.
"""

from sqlalchemy import create_engine, Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker, Session
import uuid
from datetime import datetime, timedelta
import os

Base = declarative_base()

class User(Base):
    """
    Class representing a user in the database.
    """
    __tablename__ = 'users'
    uid = Column(String, primary_key=True)
    valid_until = Column(DateTime, default=lambda: datetime.utcnow() + timedelta(days=365))
    documents = relationship('Document', back_populates='user', cascade='all, delete-orphan')

class Document(Base):
    """
    Class representing a document in the database.
    """
    __tablename__ = 'documents'
    did = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), unique=True)
    valid_until = Column(DateTime, default=lambda: datetime.utcnow() + timedelta(days=365))
    title = Column(String)
    filename = Column(String)
    upload_datetime = Column(DateTime, default=lambda: datetime.utcnow())
    user_uid = Column(String, ForeignKey('users.uid'))
    user = relationship('User', back_populates='documents')
    tokens = relationship('Token', back_populates='document', cascade='all, delete-orphan')

class Token(Base):
    """
    Class representing a token in the database.
    """
    __tablename__ = 'tokens'
    tid = Column(Integer, primary_key=True, autoincrement=True)
    did = Column(String, ForeignKey('documents.did'))
    token = Column(String, unique=True, default=lambda: str(uuid.uuid4()))
    valid_until = Column(DateTime, default=lambda: datetime.utcnow() + timedelta(days=365))
    create = Column(DateTime, default=lambda: datetime.utcnow())
    document = relationship('Document', back_populates='tokens')
    events = relationship('Event', back_populates='token', cascade='all, delete-orphan', foreign_keys='[Event.tid]')

class Event(Base):
    """
    Class representing an event in the database.
    """
    __tablename__ = 'events'
    eid = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(DateTime, default=datetime.utcnow)
    tid = Column(Integer, ForeignKey('tokens.tid'))
    token = relationship('Token', back_populates='events', foreign_keys=[tid])

class DatabaseManager:
    """
    Class for managing the database operations.
    """
    def __init__(self, data='data/data.db', docdir = 'data/documents'):
        """
        Initialize the DatabaseManager with a given data file.

        :param data: The name of the database file.
        """
        db_url = f'sqlite:///{data}'
        self.engine = create_engine(db_url, echo=False)
        self.session = Session(bind=self.engine)
        self.create_tables()
        self.docdir = docdir 

    def __del__(self):
        """
        Destructor to close the database session when the object is destroyed.
        """
        self.close_session()
        
    def close_session(self):
        """
        Close the current database session.
        """
        self.session.close()

    def create_tables(self):
        """
        Create the database tables if they do not exist.
        """
        Base.metadata.create_all(bind=self.engine)

    def add_user(self, uid):
        """
        Add a new user to the database.

        :param uid: The unique identifier for the user.
        """
        session = self.session
        try:
            user = session.query(User).filter_by(uid=uid).first()
            if user is None:
                new_user = User(uid=uid)
                session.add(new_user)
                session.commit()
                print(f"User with UID {uid} added successfully.")
        except Exception as e:
            print(f"Error adding user: {e}")
        finally:
            session.close()
            
    def add_document(self, data):
        """
        Add a new document to the database.

        :param data: A dictionary containing document data (title, filename, user_uid).
        :return: The unique identifier (did) of the newly added document.
        """
        session = self.session
        try:
            data.pop('did', None)
            uid = data.get('user_uid')
            
            # Check if the user exists, if not, create a new user
            user = session.query(User).filter_by(uid=uid).first()
            if not user:
                new_user = User(uid=uid)
                session.add(new_user)
                session.commit()
            
            new_document = Document(**data)
            session.add(new_document)
            
            if not user:
                new_document.user = new_user
                
            session.commit()

            return new_document.did    
        except Exception as e:
            print(f"Error adding document: {e}")
        finally:
            session.close()
            
    def add_token(self, did):
        """
        Add a new token to the database.

        :param did: The unique identifier (did) of the associated document.
        :return: The generated token value for the newly added token.
        """
        session = self.session
        try:
            new_token = Token(did=did)
            session.add(new_token)
            session.commit()
            
            return new_token.token
        except Exception as e:
            print(f"Error adding token: {e}")
        finally:
            session.close()

    def get_document_from_token(self, token_value):
        """
        Retrieve document information associated with a given token.

        :param token_value: The value of the token to retrieve document information.
        :return: A dictionary containing document information, or None if not found.
        """
        session = self.session
        try:
            token = session.query(Token).filter_by(token=token_value).first()
            if token:
                document = token.document
                if document:
                    return {
                        'did': document.did,
                        'title': document.title,
                        'filename': document.filename,
                        'upload_datetime': document.upload_datetime,
                        'user_uid': document.user_uid,
                        'valid_until': token.valid_until,
                    }
                else:
                    print(f"Document not found for Token: {token_value}")
                    return None
            else:
                print(f"Token not found: {token_value}")
                return None
        except Exception as e:
            print(f"Error getting document from Token: {token_value} - {e}")
            return None
        finally:
            session.close()

    def add_event(self, token_value):
        """
        Add a new event to the database associated with a given token.

        :param token_value: The value of the token for which to add an event.
        :return: None if the token is not found, otherwise, the added event's ID.
        """
        session = self.session
        try:
            token = session.query(Token).filter_by(token=token_value).first()
            if token:
                new_event = Event(tid=token.tid)
                session.add(new_event)
                session.commit()
        except Exception as e:
            pass
        finally:
            session.close()

    def get_download_event_count(self, token_value):
        """
        Retrieve the count of download events associated with a given token.

        :param token_value: The value of the token to count download events.
        :return: The count of download events, or None if the token is not found.
        """
        session = self.session
        try:
            token = session.query(Token).filter_by(token=token_value).first()
            if token:
                download_event_count = session.query(Event).filter_by(tid=token.tid).count()
                return download_event_count
            else:
                return None
        except Exception as e:
            return None
        finally:
            session.close()
            
    def get_first_event_datetime(self, token_value):
        """
        Retrieve the datetime of the first event associated with a given token.
    
        :param token_value: The value of the token to retrieve the first event datetime.
        :return: The datetime of the first event, or None if the token is not found.
        """
        session = self.session
        try:
            token = session.query(Token).filter_by(token=token_value).first()
            if token:
                first_event = session.query(Event).filter_by(tid=token.tid).order_by(Event.date).first()
                if first_event:
                    return first_event.date
                else:
                    return None
            else:
                print(f"Token not found: {token_value}")
                return None
        except Exception as e:
            print(f"Error getting first event datetime for Token: {token_value} - {e}")
            return None
        finally:
            session.close()
            
    def delete_token(self, token_value):
        """
        Delete a token and associated events from the database.

        :param token_value: The value of the token to be deleted.
        """
        session = self.session
        try:
            token = session.query(Token).filter_by(token=token_value).first()
            if token:
                # Delete associated events first
                session.query(Event).filter_by(tid=token.tid).delete()
                
                # Delete the token itself
                session.delete(token)
                session.commit()
        except Exception as e:
            print(f"Error deleting token: {e}")
        finally:
            session.close()

    def delete_document(self, did):
        """
        Delete a document and associated tokens and files from the database.

        :param did: The unique identifier (did) of the document to be deleted.
        """
        session = self.session
        try:
            document = session.query(Document).filter_by(did=did).first()
            if document:
                # Delete associated tokens and events first
                tokens = session.query(Token).filter_by(did=did).all()
                for token in tokens:
                    session.query(Event).filter_by(tid=token.tid).delete()
                    session.delete(token)

                # Delete the document itself
                session.delete(document)
                session.commit()

                # Delete the associated file
                doc_path = os.path.join(self.docdir, did)
                if os.path.exists(doc_path):
                    os.remove(doc_path)
        except Exception as e:
            print(f"Error deleting document: {e}")
        finally:
            session.close()
            
    def delete_user(self, uid):
        """
        Delete a user and associated documents, tokens, and files from the database.

        :param uid: The unique identifier (uid) of the user to be deleted.
        """
        session = self.session
        try:
            user = session.query(User).filter_by(uid=uid).first()
            if user:
                # Delete associated documents, tokens, and events first
                documents = session.query(Document).filter_by(user_uid=uid).all()
                for document in documents:
                    tokens = session.query(Token).filter_by(did=document.did).all()
                    for token in tokens:
                        session.query(Event).filter_by(tid=token.tid).delete()
                        session.delete(token)
                    # Delete the associated file
                    doc_path = os.path.join(self.docdir, document.did)
                    if os.path.exists(doc_path):
                        os.remove(doc_path)
                    # Delete the document itself
                    session.delete(document)

                # Delete the user itself
                session.delete(user)
                session.commit()
        except Exception as e:
            print(f"Error deleting user: {e}")
        finally:
            session.close()

if __name__ == '__main__':
    db_manager = DatabaseManager()
    
    # Uncomment and use the following lines to test the methods individually:
    # db_manager.add_user("example_uid")
    # document_data = {
    #     'title': 'Example Document',
    #     'filename': 'test.pdf',
    #     'user_uid': 'example_uid',
    # }
    # did = db_manager.add_document(document_data)
    #
    # token_data = {
    #     'did': 'example_did',
    #     'token': 'example_token'
    # }
    # token = db_manager.add_token(did)
    #
    # db_manager.add_event(token)
    #
    # db_manager.get_download_event_count(token)
    
    db_manager.close_session()
