from models import db
from datetime import datetime, timezone


class UserSearch(db.Model):
    """UserSearch model - tracks user search history"""
    __tablename__ = 'user_searches'

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    phrase_id = db.Column(db.Integer, db.ForeignKey('phrases.id'), nullable=False, index=True)

    searched_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # UUID for grouping searches in same session
    session_id = db.Column(db.String(36), db.ForeignKey('sessions.session_id'), index=True)

    # Optional: where user saw the word
    context_sentence = db.Column(db.Text)

    # Cache of all translations e.g. {"en": "cat", "de": "Katze", "ru": "кошка"}
    llm_translations_json = db.Column(db.JSON)

    # Relationships
    user = db.relationship('User', back_populates='user_searches')
    phrase = db.relationship('Phrase', back_populates='user_searches')
    session = db.relationship('Session')

    def __repr__(self):
        return f'<UserSearch user_id={self.user_id} phrase_id={self.phrase_id}>'