from models import db


class Language(db.Model):
    """Language model - stores supported languages with ISO 639-1 codes"""
    __tablename__ = 'languages'

    # ISO 639-1 codes: en, de, ru, etc.
    code = db.Column(db.String(2), primary_key=True)

    # Русский, Deutsch, English
    original_name = db.Column(db.String, nullable=False)

    # Russian, German, English
    en_name = db.Column(db.String, nullable=False)

    # NULL for most, 1,2,3 for popular languages
    display_order = db.Column(db.Integer)

    def __repr__(self):
        return f'<Language {self.code} - {self.en_name}>'