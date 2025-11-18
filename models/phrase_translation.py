from models import db
from datetime import datetime


class PhraseTranslation(db.Model):
    """PhraseTranslation model - caches LLM translations for phrases"""
    __tablename__ = 'phrase_translations'

    id = db.Column(db.Integer, primary_key=True)

    phrase_id = db.Column(db.Integer, db.ForeignKey('phrases.id'), nullable=False)

    # Target language for this translation (e.g., 'en' for English translation of German word)
    target_language_code = db.Column(db.String(2), db.ForeignKey('languages.code'), nullable=False)

    # LLM response: definitions, examples, synonyms
    translations_json = db.Column(db.JSON, nullable=False)

    # e.g., gpt-4o, claude-3.5-sonnet, gemini-1.5-pro
    model_name = db.Column(db.String, nullable=False)

    # e.g., 2024-11-01, specific version identifier
    model_version = db.Column(db.String)

    # Optional: hash of the prompt used
    prompt_hash = db.Column(db.String)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    # User feedback for quality tracking
    helpful_count = db.Column(db.Integer, default=0)
    unhelpful_count = db.Column(db.Integer, default=0)

    # Relationships
    phrase = db.relationship('Phrase', back_populates='translations')
    target_language = db.relationship('Language')

    # Unique constraint on (phrase_id, target_language_code) to allow multiple translations per phrase
    __table_args__ = (
        db.UniqueConstraint('phrase_id', 'target_language_code', name='uq_phrase_target_language'),
    )

    def __repr__(self):
        return f'<PhraseTranslation phrase_id={self.phrase_id} target={self.target_language_code} model={self.model_name}>'
