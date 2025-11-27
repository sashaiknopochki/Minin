"""Language utility functions for mapping between language names and codes"""
from typing import Optional, Dict
from models.language import Language


def get_language_code(language_name: str) -> Optional[str]:
    """
    Convert a language name to its ISO 639-1 code by querying the database.

    Args:
        language_name: Full language name (e.g., "English", "German")

    Returns:
        ISO 639-1 code (e.g., "en", "de"), or None if not found
    """
    language = Language.query.filter_by(en_name=language_name).first()
    return language.code if language else None


def get_language_name(language_code: str) -> Optional[str]:
    """
    Convert an ISO 639-1 code to its English name by querying the database.

    Args:
        language_code: ISO 639-1 code (e.g., "en", "de", "zh-CN")

    Returns:
        Full language name (e.g., "English", "German"), or None if not found
    """
    language = Language.query.get(language_code)
    return language.en_name if language else None


def get_all_language_mappings() -> Dict[str, str]:
    """
    Get a dictionary mapping all language names to their codes.

    Returns:
        Dictionary with en_name as keys and code as values
        e.g., {"English": "en", "German": "de", "Chinese (Simplified)": "zh-CN"}
    """
    languages = Language.query.all()
    return {lang.en_name: lang.code for lang in languages}


def get_all_code_mappings() -> Dict[str, str]:
    """
    Get a dictionary mapping all language codes to their names.

    Returns:
        Dictionary with code as keys and en_name as values
        e.g., {"en": "English", "de": "German", "zh-CN": "Chinese (Simplified)"}
    """
    languages = Language.query.all()
    return {lang.code: lang.en_name for lang in languages}


def is_supported_language(language_name: str) -> bool:
    """Check if a language name exists in the database."""
    return Language.query.filter_by(en_name=language_name).first() is not None


def is_supported_code(language_code: str) -> bool:
    """Check if a language code exists in the database."""
    return Language.query.get(language_code) is not None