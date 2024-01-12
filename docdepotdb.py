#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A simple database management system for storing users, documents, tokens, and events.
"""

from sqlalchemy import create_engine, Column, String, Integer, DateTime, ForeignKey, func, and_
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker, Session, aliased
import uuid
from datetime import datetime, timedelta, timezone
import os

local_timezone = timezone(timedelta(hours=1))

Base = declarative_base()

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
                            time_span = earliest_event_datetime - document.upload_datetime
                            total_time_span += time_span
    
                # Calculate the average time span
                average_time_span = total_time_span / len(documents) if (len(documents) > 0) & (total_time_span.total_seconds()>0) else None
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
