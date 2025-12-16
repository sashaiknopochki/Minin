from models import db
from datetime import datetime
from sqlalchemy.orm import validates
import uuid


class Session(db.Model):
    """Session model - groups user searches in the same session"""
    __tablename__ = 'sessions'

    # UUID for grouping searches
    session_id = db.Column(db.String(36), primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)

    started_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    ended_at = db.Column(db.DateTime)

    # Cost aggregation fields (Phase 2)
    total_translation_cost_usd = db.Column(db.Numeric(precision=10, scale=4), default=0.0)
    total_quiz_cost_usd = db.Column(db.Numeric(precision=10, scale=4), default=0.0)
    total_cost_usd = db.Column(db.Numeric(precision=10, scale=4), default=0.0)
    operations_count = db.Column(db.Integer, default=0)

    # Relationships
    user = db.relationship('User', back_populates='sessions')

    @validates('session_id')
    def validate_session_id(self, key, session_id):
        if not session_id:
            raise ValueError('session_id is required')
        try:
            # Validate UUID format
            uuid.UUID(session_id)
        except ValueError:
            raise ValueError(f'Invalid UUID format: {session_id}')
        return session_id

    def __repr__(self):
        return f'<Session {self.session_id}>'