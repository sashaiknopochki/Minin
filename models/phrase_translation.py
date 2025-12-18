from models import db
from datetime import datetime


class PhraseTranslation(db.Model):
    """PhraseTranslation model - caches LLM translations for phrases"""
    __tablename__ = 'phrase_translations'

    id = db.Column(db.Integer, primary_key=True)

    phrase_id = db.Column(db.Integer, db.ForeignKey('phrases.id'), nullable=False)

    # Target language for this translation (e.g., 'en', 'zh-CN' for locale-specific translations)
    target_language_code = db.Column(db.String(10), db.ForeignKey('languages.code'), nullable=False)

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

    # Cost tracking fields (Phase 2)
    prompt_tokens = db.Column(db.Integer, default=0)
    completion_tokens = db.Column(db.Integer, default=0)
    total_tokens = db.Column(db.Integer, default=0)
    cached_tokens = db.Column(db.Integer, default=0)
    estimated_cost_usd = db.Column(db.Numeric(precision=10, scale=6), default=0.0)
    cost_calculated_at = db.Column(db.DateTime)

    # Relationships
    phrase = db.relationship('Phrase', back_populates='translations')
    target_language = db.relationship('Language')

    # Unique constraint on (phrase_id, target_language_code) to allow multiple translations per phrase
    __table_args__ = (
        db.UniqueConstraint('phrase_id', 'target_language_code', name='uq_phrase_target_language'),
    )

    def __repr__(self):
        return f'<PhraseTranslation phrase_id={self.phrase_id} target={self.target_language_code} model={self.model_name}>'
