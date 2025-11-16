from models import db
from datetime import datetime


class User(db.Model):
    """User model - stores user information and preferences"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)

    # Google OAuth identifier
    google_id = db.Column(db.String, unique=True, nullable=False)

    email = db.Column(db.String, nullable=False)
    name = db.Column(db.String)

    # Language for quiz responses
    primary_language_code = db.Column(db.String(2), db.ForeignKey('languages.code'))

    # Array of language codes e.g. ["en", "de", "ru"]
    translator_languages = db.Column(db.JSON)

    # Ask quiz every N words
    quiz_frequency = db.Column(db.Integer, default=5)

    quiz_mode_enabled = db.Column(db.Boolean, default=True)
    searches_since_last_quiz = db.Column(db.Integer, default=0)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_active_at = db.Column(db.DateTime)

    # Relationships
    primary_language = db.relationship('Language', foreign_keys=[primary_language_code])
    sessions = db.relationship('Session', back_populates='user', lazy='dynamic')
    user_searches = db.relationship('UserSearch', back_populates='user', lazy='dynamic')
    learning_progress = db.relationship('UserLearningProgress', back_populates='user', lazy='dynamic')
    quiz_attempts = db.relationship('QuizAttempt', back_populates='user', lazy='dynamic')

    def __repr__(self):
        return f'<User {self.email}>'