from models import db
from datetime import datetime
from flask_login import UserMixin
from sqlalchemy.orm import validates
import re


class User(UserMixin, db.Model):
    """User model - stores user information and preferences"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)

    # Google OAuth identifier
    google_id = db.Column(db.String, unique=True, nullable=False)

    email = db.Column(db.String, nullable=False, index=True)
    name = db.Column(db.String)

    # Language for quiz responses (supports extended codes like zh-CN)
    primary_language_code = db.Column(db.String(10), db.ForeignKey('languages.code'))

    # Array of language codes e.g. ["en", "de", "ru"]
    translator_languages = db.Column(db.JSON)

    # Ask quiz every N words
    quiz_frequency = db.Column(db.Integer, default=5)

    quiz_mode_enabled = db.Column(db.Boolean, default=True)
    searches_since_last_quiz = db.Column(db.Integer, default=0)

    # Quiz type preferences (advanced stage only)
    enable_contextual_quiz = db.Column(db.Boolean, default=True)
    enable_definition_quiz = db.Column(db.Boolean, default=True)
    enable_synonym_quiz = db.Column(db.Boolean, default=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_active_at = db.Column(db.DateTime)

    # Relationships
    primary_language = db.relationship('Language', foreign_keys=[primary_language_code])
    sessions = db.relationship('Session', back_populates='user', lazy='dynamic')
    user_searches = db.relationship('UserSearch', back_populates='user', lazy='dynamic')
    learning_progress = db.relationship('UserLearningProgress', back_populates='user', lazy='dynamic')
    quiz_attempts = db.relationship('QuizAttempt', back_populates='user', lazy='dynamic')

    @validates('email')
    def validate_email(self, key, email):
        if not email:
            raise ValueError('Email is required')
        # Basic email format validation
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, email):
            raise ValueError(f'Invalid email format: {email}')
        return email

    @validates('quiz_frequency')
    def validate_quiz_frequency(self, key, value):
        if value is not None and value < 1:
            raise ValueError('quiz_frequency must be a positive integer')
        return value

    @validates('translator_languages')
    def validate_translator_languages(self, key, languages):
        if languages is None:
            return languages
        if not isinstance(languages, list):
            raise ValueError('translator_languages must be a list')
        for lang in languages:
            # Allow codes up to 10 characters (supports extended codes like zh-CN, zh-TW)
            if not isinstance(lang, str) or len(lang) < 2 or len(lang) > 10:
                raise ValueError(f'Invalid language code: {lang}. Must be 2-10 characters')
        return languages

    def __repr__(self):
        return f'<User {self.email}>'