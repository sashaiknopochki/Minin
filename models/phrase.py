from models import db
from datetime import datetime, timezone
from sqlalchemy.orm import validates


class Phrase(db.Model):
    """Phrase model - stores words, phrases, phrasal verbs, and example sentences"""
    __tablename__ = 'phrases'

    id = db.Column(db.Integer, primary_key=True)

    text = db.Column(db.String, nullable=False)
    language_code = db.Column(db.String(2), db.ForeignKey('languages.code'), nullable=False, index=True)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # word, phrase, phrasal_verb, example_sentence
    type = db.Column(db.String, default='word')

    is_quizzable = db.Column(db.Boolean, default=True)

    # Analytics: track how many times this phrase has been searched
    search_count = db.Column(db.Integer, default=0)

    # Source phrase information from LLM (grammar, part of speech, context)
    # Format: [word, grammar_info, context] e.g., ["geben", "verb, infinitive", "to give something"]
    source_info_json = db.Column(db.JSON)

    # Relationships
    language = db.relationship('Language')
    user_searches = db.relationship('UserSearch', back_populates='phrase', lazy='dynamic')
    learning_progress = db.relationship('UserLearningProgress', back_populates='phrase', lazy='dynamic')
    quiz_attempts = db.relationship('QuizAttempt', back_populates='phrase', lazy='dynamic')
    translations = db.relationship('PhraseTranslation', back_populates='phrase', lazy='dynamic')

    # Unique constraint on (text, language_code)
    __table_args__ = (
        db.UniqueConstraint('text', 'language_code', name='uq_phrase_text_language'),
    )

    @validates('text')
    def validate_text(self, key, text):
        if not text or not text.strip():
            raise ValueError('Phrase text cannot be empty or whitespace')
        # Normalize: strip whitespace and convert to lowercase to prevent duplicates
        return text.strip().lower()

    def __repr__(self):
        return f'<Phrase {self.text} ({self.language_code})>'