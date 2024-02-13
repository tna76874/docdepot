#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A simple database management system for storing users, documents, tokens, and events.
"""

from sqlalchemy import create_engine, Column, String, Integer, DateTime, ForeignKey, func, and_
from sqlalchemy.orm import relationship, sessionmaker, Session, aliased, declarative_base
from sqlalchemy.exc import IntegrityError
import uuid
from datetime import datetime, timedelta, timezone
import os

local_timezone = timezone(timedelta(hours=1))

Base = declarative_base()

class Redirect(Base):
    """
    Class representing a redirect in the database.
    """
    __tablename__ = 'redirects'
    rid = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    uid = Column(String, unique=True, nullable=True)
    did = Column(String, unique=True, nullable=True)
    url = Column(String)
    valid_until = Column(DateTime, default=lambda: datetime.now(local_timezone) + timedelta(days=365))

class User(Base):
    """
    Class representing a user in the database.
    """
    __tablename__ = 'users'
    uid = Column(String, primary_key=True)
    valid_until = Column(DateTime, default=lambda: datetime.now(local_timezone) + timedelta(days=365))
    documents = relationship('Document', back_populates='user', cascade='all, delete-orphan')

class Document(Base):
    """
    Class representing a document in the database.
    """
    __tablename__ = 'documents'
    did = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), unique=True)
    valid_until = Column(DateTime, default=lambda: datetime.now(local_timezone) + timedelta(days=365))
    title = Column(String)
    filename = Column(String)
    upload_datetime = Column(DateTime, default=lambda: datetime.now(local_timezone))
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
    valid_until = Column(DateTime, default=lambda: datetime.now(local_timezone) + timedelta(days=365))
    create = Column(DateTime, default=lambda: datetime.now(local_timezone))
    document = relationship('Document', back_populates='tokens')
    events = relationship('Event', back_populates='token', cascade='all, delete-orphan', foreign_keys='[Event.tid]')

class Event(Base):
    """
    Class representing an event in the database.
    """
    __tablename__ = 'events'
    eid = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(DateTime, default=lambda: datetime.now(local_timezone))
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
        
    def _check_if_redirect_is_valid(self, redirect):
        try:
            if redirect:
                if redirect.valid_until >= datetime.now(local_timezone).replace(tzinfo=None):
                    return True
                else:
                    return False
            else:
                return False
        except:
            return False
        
    def get_redirect(self, token):
        """
        Retrieve a redirect corresponding to a given token, preferring 'did' (Document ID) if existent,
        then 'uid' (User ID) if existent, otherwise None.

        :param token: The token for which to retrieve the redirect.
        :return: The URL of the redirect if found, otherwise None.
        """
        user_info = self.get_document_from_token(token)
        if not user_info:
            return None
        session = self.session
        try:
            redirect = session.query(Redirect).filter(Redirect.did == user_info.get('did')).first()
                           
            if self._check_if_redirect_is_valid(redirect):
                return redirect.url
            else:
                redirect = session.query(Redirect).filter(Redirect.uid == user_info.get('user_uid')).first()
                if self._check_if_redirect_is_valid(redirect):
                    return redirect.url
                else:
                    return None

        except Exception as e:
            print(f"Error retrieving redirect: {e}")
        finally:
            session.close()
            
    def _ensure_datetime(self, time_object):
        if not isinstance(time_object, datetime):
            try:
                time_object = datetime.fromisoformat(time_object)
            except (ValueError, TypeError):
                raise ValueError("new_expiry_date should be a datetime object or a string in ISO format.")  
        return time_object


    def add_redirects(self, redirect_list):
        """
        Add or update redirects from a list of dictionaries to the database.

        :param redirect_list: List of dictionaries representing redirects.
        """
        session = self.session
        try:
            for redirect_data in redirect_list:
                uid = redirect_data.get('uid')
                did = redirect_data.get('did')
                url = redirect_data.get('url')
                valid_until = redirect_data.get('valid_until')
                if valid_until:
                    valid_until = self._ensure_datetime(valid_until)                    

                if (uid is None and did is None) or (uid is not None and did is not None):
                    raise ValueError("Exactly one of 'uid' and 'did' must be defined.")

                if uid is None and did is None:
                    continue

                if uid is None:
                    redirect = session.query(Redirect).filter(Redirect.uid == did).first()
                elif did is None:
                    redirect = session.query(Redirect).filter(Redirect.uid == uid).first()
                else:
                    continue

                if redirect:
                    redirect.url = url
                    if valid_until:
                        redirect.valid_until = valid_until
                else:
                    new_redirect = Redirect(uid=uid, did=did, url=url, valid_until=valid_until)
                    session.add(new_redirect)

            session.commit()
                
        except IntegrityError as e:
            session.rollback()
            print(f"Integrity error occurred: {e}")
        except Exception as e:
            session.rollback()
            print(f"Error adding or updating redirects: {e}")
        finally:
            session.close()
        
    def are_tokens_valid(self, token_list):
        """
        Check if a list of tokens is valid or not.

        :param token_list: List of token strings to be checked.
        :return: A dictionary where keys are tokens, and values are boolean indicating validity.
        """
        session = self.session
        try:
            token_validity_dict = {}

            for token_str in token_list:
                token = session.query(Token).filter(Token.token == token_str).first()

                if token:
                    document = self.get_document_from_token(token_str)
                    if document:
                        current_time = datetime.utcnow()
                        isvalid = document['valid_until'] >= current_time
                        token_validity_dict[token_str] = isvalid
                    else:
                        token_validity_dict[token_str] = False
                else:
                    # Token not found in the database
                    token_validity_dict[token_str] = False

            return token_validity_dict

        except Exception as e:
            print(f"Error checking token validity: {e}")
        finally:
            session.close()
        
    def rename_users(self, rename_dict):
        """
        Rename users in the database based on the provided dictionary.

        :param rename_dict: A dictionary where keys are the old user names (A) and values are the new user names (B).
        """
        for old_name, new_name in rename_dict.items():
            # Query for users with the old name
            users_to_rename = self.session.query(User).filter(User.uid == old_name).all()

            for user in users_to_rename:
                # Update the user's UID to the new name
                user.uid = new_name
    
                # Query for documents associated with the user
                documents_to_rename = self.session.query(Document).filter(Document.user_uid == old_name).all()
    
                for document in documents_to_rename:
                    # Update the document's user UID to the new name
                    document.user_uid = new_name

        # Commit the changes to the database
        self.session.commit()

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
            
    def delete_did_if_no_document_present(self):
        """
        Check the existence of files associated with each document in the database.
        If a file does not exist, delete the document from the database.
        """
        session = self.session
        try:
            all_documents = session.query(Document).all()

            for document in all_documents:
                file_path = os.path.join(self.docdir, document.did)

                if not os.path.exists(file_path):
                    # File doesn't exist, delete the document from the database
                    self.delete_document(document.did)

        except Exception as e:
            print(f"Error checking document file existence: {e}")
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
                    user = document.user
    
                    # Find the nearest valid_until among token, document, and user
                    nearest_valid_until = min(
                        token.valid_until,
                        document.valid_until if document.valid_until else datetime.max.replace(tzinfo=local_timezone),
                        user.valid_until if user.valid_until else datetime.max.replace(tzinfo=local_timezone),
                    )
    
                    return {
                        'did': document.did,
                        'title': document.title,
                        'filename': document.filename,
                        'upload_datetime': document.upload_datetime,
                        'user_uid': document.user_uid,
                        'valid_until': nearest_valid_until,
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
        session = sessionmaker(bind=self.engine)()
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
            
    def update_token_valid_until(self, token_value, new_valid_until):
        """
        Update the 'valid_until' date of a token.

        :param token_value: The value of the token to be updated.
        :param new_valid_until: The new 'valid_until' date for the token.
        """
        if not isinstance(new_valid_until, datetime):
            try:
                new_valid_until = datetime.fromisoformat(new_valid_until)
            except (ValueError, TypeError):
                raise ValueError("new_valid_until should be a datetime object or a string in ISO format.")

        session = self.session
        try:
            token = session.query(Token).filter_by(token=token_value).first()
            if token:
                token.valid_until = new_valid_until
                session.commit()
            else:
                print(f"Token not found: {token_value}")
        except Exception as e:
            print(f"Error updating token: {e}")
        finally:
            session.close()
            
    def update_user_valid_until(self, user_uid, new_valid_until):
        """
        Update the 'valid_until' date of a user.
    
        :param user_uid: The unique identifier (uid) of the user to be updated.
        :param new_valid_until: The new 'valid_until' date for the user.
        """
        if not isinstance(new_valid_until, datetime):
            try:
                new_valid_until = datetime.fromisoformat(new_valid_until)
            except (ValueError, TypeError):
                raise ValueError("new_valid_until should be a datetime object or a string in ISO format.")
    
        session = self.session
        try:
            user = session.query(User).filter_by(uid=user_uid).first()
            if user:
                user.valid_until = new_valid_until
                session.commit()
            else:
                print(f"User not found: {user_uid}")
        except Exception as e:
            print(f"Error updating user: {e}")
        finally:
            session.close()
            
    def set_all_users_expiry_date(self, new_expiry_date):
        """
        Set the 'valid_until' date for all users to a specific date.
    
        :param new_expiry_date: The new 'valid_until' date for all users.
        """
        if not isinstance(new_expiry_date, datetime):
            try:
                new_expiry_date = datetime.fromisoformat(new_expiry_date)
            except (ValueError, TypeError):
                raise ValueError("new_expiry_date should be a datetime object or a string in ISO format.")
    
        session = self.session
        try:
            users = session.query(User).all()
            for user in users:
                user.valid_until = new_expiry_date
            session.commit()
        except Exception as e:
            print(f"Error updating expiry date for all users: {e}")
        finally:
            session.close()
            
    def delete_expired_tokens_and_documents(self):
        """
        Delete all expired tokens and associated documents with no remaining tokens.
        """
        session = self.session
        try:
            current_datetime = datetime.now(local_timezone)

            # Delete expired tokens
            expired_tokens = session.query(Token).filter(Token.valid_until < current_datetime).all()
            for token in expired_tokens:
                # Delete associated events first
                session.query(Event).filter_by(tid=token.tid).delete()
                session.delete(token)

                # Check if the associated document has no remaining tokens
                remaining_tokens = session.query(Token).filter_by(did=token.did).count()
                if remaining_tokens == 0:
                    # Delete the associated file
                    doc_path = os.path.join(self.docdir, token.did)
                    if os.path.exists(doc_path):
                        os.remove(doc_path)

                    # Delete the document itself
                    document = session.query(Document).filter_by(did=token.did).first()
                    if document:
                        session.delete(document)

            session.commit()
        except Exception as e:
            print(f"Error deleting expired tokens and documents: {e}")
        finally:
            session.close()
            
    def delete_expired_items(self):
        """
        Delete all expired tokens, documents, and users with no remaining documents.
        """
        session = self.session
        try:
            current_datetime = datetime.now(local_timezone)
    
            # Delete expired tokens
            expired_tokens = session.query(Token).filter(Token.valid_until < current_datetime).all()
            for token in expired_tokens:
                # Delete associated events first
                session.query(Event).filter_by(tid=token.tid).delete()
                session.delete(token)
    
                # Check if the associated document has no remaining tokens
                remaining_tokens = session.query(Token).filter_by(did=token.did).count()
                if remaining_tokens == 0:
                    # Delete the associated file
                    doc_path = os.path.join(self.docdir, token.did)
                    if os.path.exists(doc_path):
                        os.remove(doc_path)
    
                    # Delete the document itself
                    document = session.query(Document).filter_by(did=token.did).first()
                    if document:
                        session.delete(document)
    
            # Delete expired users
            expired_users = session.query(User).filter(User.valid_until < current_datetime).all()
            for user in expired_users:
                self.delete_user(user.uid)
    
            session.commit()
        except Exception as e:
            print(f"Error deleting expired tokens, documents, and users: {e}")
        finally:
            session.close()
            
    def delete_documents_without_events_after_n_days(self, n=30):
        """
        Delete documents that have no events N days after upload_datetime.

        :param n: The number of days after upload_datetime.
        """
        session = self.session
        try:
            current_datetime = datetime.now(local_timezone)
            threshold_datetime = current_datetime - timedelta(days=n)

            # Find documents with no events N days after upload_datetime
            documents_to_delete = (
                session.query(Document)
                .outerjoin(Token, Document.did == Token.did)
                .outerjoin(Event, Token.tid == Event.tid)
                .group_by(Document.did)
                .having(and_(
                    func.max(Event.date) == None,  # No events after create
                    Document.upload_datetime < threshold_datetime
                ))
                .all()
            )

            # Delete each document using the existing delete_document method
            for document in documents_to_delete:
                self.delete_document(document.did)

        except Exception as e:
            print(f"Error deleting documents without events after {n} days: {e}")
        finally:
            session.close()

    def get_user_of_token(self, token_value):
        """
        Retrieve the user associated with a given token.
    
        :param token_value: The value of the token to retrieve the associated user.
        :return: A dictionary containing user information, or None if not found.
        """
        session = self.session
        try:
            token = session.query(Token).filter_by(token=token_value).first()
            if token:
                user = token.document.user
                if user:
                    return {
                        'uid': user.uid,
                        'valid_until': user.valid_until,
                    }
                else:
                    print(f"User not found for Token: {token_value}")
                    return None
            else:
                print(f"Token not found: {token_value}")
                return None
        except Exception as e:
            print(f"Error getting user from Token: {token_value} - {e}")
            return None
        finally:
            session.close()

    def calculate_average_time_for_user(self, user_uid):
        """
        Calculate the average time span for all tokens of a given user
        between document upload time and the first token event.
    
        :param user_uid: The unique identifier (uid) of the user.
        :return: The average time span as a timedelta object, or None if no relevant data found.
        """
        session = self.session
        try:
            user = session.query(User).filter_by(uid=user_uid).first()
            if user:
                documents = user.documents
                total_time_span = timedelta()
                
                total_time_spans = list()
    
                for document in documents:
                    # Check if the document has tokens
                    if document.tokens:
                        # Find the earliest event datetime for the document's tokens
                        earliest_event_datetime = (
                            session.query(func.min(Event.date))
                            .join(Token, Event.tid == Token.tid)
                            .filter(Token.did == document.did)
                            .scalar()
                        )
    
                        # Calculate the time span between document upload time and the earliest event
                        if earliest_event_datetime:
                            if earliest_event_datetime > document.upload_datetime:
                                time_span = earliest_event_datetime - document.upload_datetime
                                total_time_spans.append(time_span)
    
                # Calculate the average time span
                time_sum = timedelta()
                for zeit in total_time_spans:
                    time_sum+=zeit
                    
                average_time_span = time_sum / len(total_time_spans) if total_time_spans else None

                return average_time_span
    
            else:
                print(f"User not found: {user_uid}")
                return None
    
        except Exception as e:
            print(f"Error calculating average time span for user {user_uid}: {e}")
            return None
    
        finally:
            session.close()

    def cluster_time_span(self, average_time_span):
        """
        Cluster the average time span to the largest time unit.
    
        :param average_time_span: The average time span as a timedelta object.
        :return: A tuple containing the clustered time value and unit.
        """
        if average_time_span is None:
            return None
    
        total_seconds = int(average_time_span.total_seconds())
        days, remainder = divmod(total_seconds, 86400)  # 86400 seconds in a day
        hours, remainder = divmod(remainder, 3600)      # 3600 seconds in an hour
        minutes, seconds = divmod(remainder, 60)        # 60 seconds in a minute
    
        if days > 0:
            if days == 1:
                return days, 'Tag'
            else:
                return days, 'Tage'
        elif hours > 0:
            if hours == 1:
                return hours, 'Stunde'
            else:
                return hours, 'Stunden'
        elif minutes > 0:
            if minutes == 1:
                return minutes, 'Minute'
            else:
                return minutes, 'Minuten'
        else:
            return seconds, 'Sekunden'
            
    def calculate_average_time_for_token(self, token_value):
        """
        Calculate the average time span for a given token
        between document upload time and the first token event.
    
        :param token_value: The value of the token for which to calculate the average time span.
        :return: The average time span as a timedelta object, or None if no relevant data found.
        """
        user_info = self.get_user_of_token(token_value)
        if user_info:
            user_uid = user_info['uid']
            return self.calculate_average_time_for_user(user_uid)
        else:
            print(f"User information not found for Token: {token_value}")
            return None
        
    def calculate_average_time_for_all_users(self):
        """
        Calculate the average time span for each user between document upload time and the first token event.
    
        :return: A dictionary where keys are user UIDs and values are the average time spans as timedelta objects.
        """
        session = self.session
        try:
            user_average_times = {}
    
            # Get all users
            users = session.query(User).all()
    
            for user in users:
                user_uid = user.uid
                average_time_span = self.calculate_average_time_for_user(user_uid)
                user_average_times[user_uid] = average_time_span
    
            return user_average_times
    
        except Exception as e:
            print(f"Error calculating average time span for all users: {e}")
            return None
    
        finally:
            session.close()
            
    def get_events(self):
        """
        Retrieve all events with information including date, token, user_uid, and document title.
    
        :return: A list of dictionaries containing event information.
        """
        session = self.session
        try:
            events_info = []
    
            # Query all events with related information
            events = (
                session.query(Event, Token, Document, User)
                .join(Token, Event.tid == Token.tid)
                .join(Document, Token.did == Document.did)
                .join(User, Document.user_uid == User.uid)
                .all()
            )
    
            for event, token, document, user in events:
                event_info = {
                    'date': event.date,
                    'token': token.token,
                    'user_uid': user.uid,
                    'did': document.did,
                    'title': document.title,
                }
                events_info.append(event_info)
    
            return events_info
    
        except Exception as e:
            print(f"Error retrieving events: {e}")
            return None
    
        finally:
            session.close()
            
    def get_documents(self):
        """
        Retrieve all documents with information including document ID (did), title, filename, user UID, and upload datetime.
    
        :return: A list of dictionaries containing document information.
        """
        session = self.session
        try:
            documents_info = []
    
            # Query all documents with related information
            documents = (
                session.query(Document, User)
                .join(User, Document.user_uid == User.uid)
                .all()
            )
    
            for document, user in documents:
                document_info = {
                    'did': document.did,
                    'title': document.title,
                    'filename': document.filename,
                    'user_uid': user.uid,
                    'upload_datetime': document.upload_datetime,
                }
                documents_info.append(document_info)
    
            return documents_info
    
        except Exception as e:
            print(f"Error retrieving documents: {e}")
            return None
    
        finally:
            session.close()
            
    def get_users(self):
        """
        Retrieve all users with information including user UID and valid until date.
    
        :return: A list of dictionaries containing user information.
        """
        session = self.session
        try:
            users_info = []
    
            # Query all users with related information
            users = session.query(User).all()
    
            for user in users:
                user_info = {
                    'uid': user.uid,
                    'valid_until': user.valid_until,
                }
                users_info.append(user_info)
    
            return users_info
    
        except Exception as e:
            print(f"Error retrieving users: {e}")
            return None
    
        finally:
            session.close()



if __name__ == '__main__':
    self = DatabaseManager()
    
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
    
    self.close_session()
