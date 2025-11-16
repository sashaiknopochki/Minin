from models import db
from datetime import datetime


class QuizAttempt(db.Model):
    """QuizAttempt model - tracks quiz attempts and results"""
    __tablename__ = 'quiz_attempts'

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    phrase_id = db.Column(db.Integer, db.ForeignKey('phrases.id'), nullable=False)

    # multiple_choice_target, multiple_choice_source, text_input_target, text_input_source, contextual, definition, synonym
    question_type = db.Column(db.String)

    # What was shown to user e.g. {"question": "Translate: Katze", "options": [...]}
    prompt_json = db.Column(db.JSON)

    # What the system considered correct
    correct_answer = db.Column(db.String)

    user_answer = db.Column(db.String)

    was_correct = db.Column(db.Boolean, nullable=False)

    # Optional: store LLM evaluation for debugging
    llm_evaluation_json = db.Column(db.JSON)

    attempted_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    user = db.relationship('User', back_populates='quiz_attempts')
    phrase = db.relationship('Phrase', back_populates='quiz_attempts')

    def __repr__(self):
        return f'<QuizAttempt user_id={self.user_id} phrase_id={self.phrase_id} correct={self.was_correct}>'