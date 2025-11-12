"""
SQLAlchemy database models for Minin application
"""

from datetime import datetime
from app import db
import json


class User(db.Model):
    """User account model with Google OAuth data"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    google_id = db.Column(db.String(255), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    username = db.Column(db.String(255))
    profile_picture = db.Column(db.String(500))
    primary_language_id = db.Column(db.Integer, db.ForeignKey('languages.id'))
    quiz_frequency = db.Column(db.Integer, default=5)  # Quiz after N words
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    primary_language = db.relationship('Language', backref='users')
    searches = db.relationship('UserSearch', backref='user', cascade='all, delete-orphan')
    learning_progress = db.relationship('UserLearningProgress', backref='user', cascade='all, delete-orphan')
    quiz_attempts = db.relationship('QuizAttempt', backref='user', cascade='all, delete-orphan')
    sessions = db.relationship('UserSession', backref='user', cascade='all, delete-orphan')


class Language(db.Model):
    """Language definitions"""
    __tablename__ = 'languages'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(10), unique=True, nullable=False)  # e.g., 'en', 'de', 'ru'
    name = db.Column(db.String(100), nullable=False)  # e.g., 'English', 'German'
    flag_emoji = db.Column(db.String(10))  # e.g., '🇬🇧'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    phrases = db.relationship('Phrase', backref='language', cascade='all, delete-orphan')


class Phrase(db.Model):
    """Storage for words, phrases, and phrasal verbs"""
    __tablename__ = 'phrases'

    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(500), nullable=False)
    language_id = db.Column(db.Integer, db.ForeignKey('languages.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Unique constraint on (text, language_id)
    __table_args__ = (db.UniqueConstraint('text', 'language_id', name='unique_phrase_per_language'),)

    # Relationships
    searches = db.relationship('UserSearch', backref='phrase', cascade='all, delete-orphan')
    learning_progress = db.relationship('UserLearningProgress', backref='phrase', cascade='all, delete-orphan')


class UserSearch(db.Model):
    """History of user translation searches with cached translations"""
    __tablename__ = 'user_searches'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    phrase_id = db.Column(db.Integer, db.ForeignKey('phrases.id'), nullable=False)
    session_id = db.Column(db.Integer, db.ForeignKey('user_sessions.id'))
    llm_translations_json = db.Column(db.JSON)  # Cached LLM translations
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    quiz_attempts = db.relationship('QuizAttempt', backref='search', cascade='all, delete-orphan')


class UserLearningProgress(db.Model):
    """Tracks learning stage for each phrase with spaced repetition"""
    __tablename__ = 'user_learning_progress'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    phrase_id = db.Column(db.Integer, db.ForeignKey('phrases.id'), nullable=False)
    learning_stage = db.Column(
        db.String(50),
        default='new'
    )  # new, recognition, production, mastered
    next_review_date = db.Column(db.DateTime)
    repetition_interval = db.Column(db.Integer, default=1)  # Days
    ease_factor = db.Column(db.Float, default=2.5)  # SM-2 algorithm
    correct_count = db.Column(db.Integer, default=0)
    incorrect_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Unique constraint on (user_id, phrase_id)
    __table_args__ = (db.UniqueConstraint('user_id', 'phrase_id', name='unique_user_phrase_progress'),)


class QuizAttempt(db.Model):
    """Complete history of all quiz attempts"""
    __tablename__ = 'quiz_attempts'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    search_id = db.Column(db.Integer, db.ForeignKey('user_searches.id'))
    phrase_id = db.Column(db.Integer, db.ForeignKey('phrases.id'), nullable=False)
    quiz_mode = db.Column(db.String(50))  # recognition, production
    question = db.Column(db.Text)  # The question asked
    user_answer = db.Column(db.Text)  # User's answer
    correct_answer = db.Column(db.Text)  # Correct answer
    is_correct = db.Column(db.Boolean)  # Whether answer was correct
    llm_evaluation = db.Column(db.JSON)  # LLM evaluation details for debugging
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class UserSession(db.Model):
    """Groups searches by session"""
    __tablename__ = 'user_sessions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    languages_used = db.Column(db.JSON)  # List of language IDs used in session
    word_count = db.Column(db.Integer, default=0)
    quiz_triggered = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    ended_at = db.Column(db.DateTime)

    # Relationships
    searches = db.relationship('UserSearch', backref='session', cascade='all, delete-orphan')
