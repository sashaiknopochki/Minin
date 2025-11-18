from models import db
from datetime import datetime, date


class UserLearningProgress(db.Model):
    """UserLearningProgress model - tracks spaced repetition learning progress"""
    __tablename__ = 'user_learning_progress'

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    phrase_id = db.Column(db.Integer, db.ForeignKey('phrases.id'), nullable=False)

    # new, recognition, production, mastered
    stage = db.Column(db.String, nullable=False, default='new')

    times_reviewed = db.Column(db.Integer, default=0)
    times_correct = db.Column(db.Integer, default=0)
    times_incorrect = db.Column(db.Integer, default=0)

    next_review_date = db.Column(db.Date, default=date.today)
    last_reviewed_at = db.Column(db.DateTime)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    user = db.relationship('User', back_populates='learning_progress')
    phrase = db.relationship('Phrase', back_populates='learning_progress')

    # Unique constraint on (user_id, phrase_id) and index on (user_id, next_review_date)
    __table_args__ = (
        db.UniqueConstraint('user_id', 'phrase_id', name='uq_user_phrase'),
        db.Index('idx_user_next_review', 'user_id', 'next_review_date'),
    )

    def __repr__(self):
        return f'<UserLearningProgress user_id={self.user_id} phrase_id={self.phrase_id} stage={self.stage}>'