from models import db
from datetime import datetime


class Session(db.Model):
    """Session model - groups user searches in the same session"""
    __tablename__ = 'sessions'

    # UUID for grouping searches
    session_id = db.Column(db.String(36), primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)

    started_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    ended_at = db.Column(db.DateTime)

    # Relationships
    user = db.relationship('User', back_populates='sessions')

    def __repr__(self):
        return f'<Session {self.session_id}>'