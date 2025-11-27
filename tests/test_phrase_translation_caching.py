"""
Test for phrase translation caching workflow

This test verifies the complete caching workflow:
1. First search: Creates phrase + calls LLM + caches translation
2. Second search (same phrase, same target): Returns cached translation (no LLM call)
3. Third search (same phrase, different target): Reuses phrase + calls LLM for new target
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add parent directory to path so we can import the app
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app
from models import db
from models.phrase import Phrase
from models.phrase_translation import PhraseTranslation
from models.language import Language
from services.phrase_translation_service import (
    get_or_create_phrase,
    get_cached_translation,
    cache_translation,
    get_or_create_translations
)


@pytest.fixture
def app():
    """Create and configure a test app"""
    app = create_app('testing')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['TESTING'] = True

    with app.app_context():
        db.create_all()

        # Create test languages
        languages = [
            Language(code='de', original_name='Deutsch', en_name='German', display_order=1),
            Language(code='en', original_name='English', en_name='English', display_order=2),
            Language(code='fr', original_name='Français', en_name='French', display_order=3),
            Language(code='ru', original_name='Русский', en_name='Russian', display_order=4),
        ]
        for lang in languages:
            db.session.add(lang)
        db.session.commit()

        yield app

        db.session.remove()
        db.drop_all()


@pytest.fixture
def app_context(app):
    """Create an app context for tests"""
    with app.app_context():
        yield


def test_get_or_create_phrase(app_context):
    """Test phrase creation and retrieval"""
    # Create a new phrase
    phrase1 = get_or_create_phrase("geben", "de")
    assert phrase1 is not None
    assert phrase1.text == "geben"
    assert phrase1.language_code == "de"
    assert phrase1.search_count == 0

    # Get the same phrase (should not create duplicate)
    phrase2 = get_or_create_phrase("geben", "de")
    assert phrase2.id == phrase1.id

    # Different language should create a new phrase
    phrase3 = get_or_create_phrase("geben", "en")
    assert phrase3.id != phrase1.id


def test_cache_and_retrieve_translation(app_context):
    """Test caching and retrieving translations"""
    # Create a phrase
    phrase = get_or_create_phrase("geben", "de")

    # Initially no cached translation
    cached = get_cached_translation(phrase.id, "en")
    assert cached is None

    # Cache a translation
    translation_data = [
        ["give", "verb, infinitive", "to give something to someone"],
        ["to give", "verb phrase", "transfer possession"]
    ]

    cached_translation = cache_translation(
        phrase_id=phrase.id,
        target_language_code="en",
        translations_json=translation_data,
        model_name="gpt-4.1-mini",
        model_version="2024-11-01"
    )

    assert cached_translation is not None
    assert cached_translation.phrase_id == phrase.id
    assert cached_translation.target_language_code == "en"
    assert cached_translation.translations_json == translation_data
    assert cached_translation.model_name == "gpt-4.1-mini"

    # Retrieve the cached translation
    retrieved = get_cached_translation(phrase.id, "en")
    assert retrieved is not None
    assert retrieved.id == cached_translation.id
    assert retrieved.translations_json == translation_data

    # Different target language should not be cached
    cached_fr = get_cached_translation(phrase.id, "fr")
    assert cached_fr is None


def test_multiple_translations_same_phrase(app_context):
    """Test that same phrase can have multiple translations for different target languages"""
    # Create a phrase
    phrase = get_or_create_phrase("geben", "de")

    # Cache English translation
    en_data = [["give", "verb", "to give"]]
    cache_translation(phrase.id, "en", en_data, "gpt-4.1-mini")

    # Cache French translation
    fr_data = [["donner", "verbe", "donner quelque chose"]]
    cache_translation(phrase.id, "fr", fr_data, "gpt-4.1-mini")

    # Cache Russian translation
    ru_data = [["давать", "глагол", "передавать что-то"]]
    cache_translation(phrase.id, "ru", ru_data, "gpt-4.1-mini")

    # Verify all translations are cached
    assert get_cached_translation(phrase.id, "en") is not None
    assert get_cached_translation(phrase.id, "fr") is not None
    assert get_cached_translation(phrase.id, "ru") is not None

    # Verify they're different
    en_cached = get_cached_translation(phrase.id, "en")
    fr_cached = get_cached_translation(phrase.id, "fr")

    assert en_cached.translations_json != fr_cached.translations_json


@patch('services.phrase_translation_service.translate_text')
def test_get_or_create_translations_all_fresh(mock_translate, app_context):
    """Test the complete workflow when no translations are cached"""
    # Mock LLM response
    mock_translate.return_value = {
        'success': True,
        'translations': {
            'English': [["give", "verb", "to give"]],
            'French': [["donner", "verbe", "donner"]]
        },
        'model': 'gpt-4.1-mini',
        'usage': {'prompt_tokens': 100, 'completion_tokens': 50, 'total_tokens': 150}
    }

    # First search - everything should be fresh
    result = get_or_create_translations(
        text="geben",
        source_language="German",
        source_language_code="de",
        target_languages=["English", "French"],
        target_language_codes=["en", "fr"],
        model="gpt-4.1-mini"
    )

    # Verify result
    assert result['success'] is True
    assert result['phrase_id'] is not None
    assert 'English' in result['translations']
    assert 'French' in result['translations']
    assert result['cache_status']['English'] == 'fresh'
    assert result['cache_status']['French'] == 'fresh'

    # Verify LLM was called
    mock_translate.assert_called_once()

    # Verify translations were cached
    phrase_id = result['phrase_id']
    assert get_cached_translation(phrase_id, "en") is not None
    assert get_cached_translation(phrase_id, "fr") is not None


@patch('services.phrase_translation_service.translate_text')
def test_get_or_create_translations_all_cached(mock_translate, app_context):
    """Test the complete workflow when all translations are already cached"""
    # Create phrase and cache translations
    phrase = get_or_create_phrase("geben", "de")
    cache_translation(phrase.id, "en", [["give", "verb", "to give"]], "gpt-4.1-mini")
    cache_translation(phrase.id, "fr", [["donner", "verbe", "donner"]], "gpt-4.1-mini")

    # Second search - everything should be cached
    result = get_or_create_translations(
        text="geben",
        source_language="German",
        source_language_code="de",
        target_languages=["English", "French"],
        target_language_codes=["en", "fr"],
        model="gpt-4.1-mini"
    )

    # Verify result
    assert result['success'] is True
    assert result['phrase_id'] == phrase.id
    assert 'English' in result['translations']
    assert 'French' in result['translations']
    assert result['cache_status']['English'] == 'cached'
    assert result['cache_status']['French'] == 'cached'

    # Verify LLM was NOT called (everything was cached)
    mock_translate.assert_not_called()


@patch('services.phrase_translation_service.translate_text')
def test_get_or_create_translations_partial_cached(mock_translate, app_context):
    """Test the complete workflow when some translations are cached and some are fresh"""
    # Create phrase and cache only English translation
    phrase = get_or_create_phrase("geben", "de")
    cache_translation(phrase.id, "en", [["give", "verb", "to give"]], "gpt-4.1-mini")

    # Mock LLM response for French only
    mock_translate.return_value = {
        'success': True,
        'translations': {
            'French': [["donner", "verbe", "donner"]]
        },
        'model': 'gpt-4.1-mini',
        'usage': {'prompt_tokens': 80, 'completion_tokens': 30, 'total_tokens': 110}
    }

    # Search with both English and French
    result = get_or_create_translations(
        text="geben",
        source_language="German",
        source_language_code="de",
        target_languages=["English", "French"],
        target_language_codes=["en", "fr"],
        model="gpt-4.1-mini"
    )

    # Verify result
    assert result['success'] is True
    assert result['phrase_id'] == phrase.id
    assert 'English' in result['translations']
    assert 'French' in result['translations']
    assert result['cache_status']['English'] == 'cached'
    assert result['cache_status']['French'] == 'fresh'

    # Verify LLM was called only for French
    mock_translate.assert_called_once()
    call_args = mock_translate.call_args[1]
    assert 'French' in call_args['target_languages']
    assert 'English' not in call_args['target_languages']

    # Verify both translations are now cached
    assert get_cached_translation(phrase.id, "en") is not None
    assert get_cached_translation(phrase.id, "fr") is not None


def test_workflow_example_from_spec(app_context):
    """
    Test the exact workflow from the specification:

    1. First user searches "geben" (German → English)
    2. Second user searches "geben" (German → English) - should get cache hit
    3. Third user searches "geben" (German → French) - reuses phrase, fresh translation
    """
    with patch('services.phrase_translation_service.translate_text') as mock_translate:
        # Setup: Mock LLM to return translations
        def llm_side_effect(*args, **kwargs):
            target_langs = kwargs.get('target_languages', [])
            translations = {}

            if 'English' in target_langs:
                translations['English'] = [["give", "verb", "to give something"]]
            if 'French' in target_langs:
                translations['French'] = [["donner", "verbe", "donner quelque chose"]]

            return {
                'success': True,
                'translations': translations,
                'model': 'gpt-4.1-mini',
                'usage': {'total_tokens': 100}
            }

        mock_translate.side_effect = llm_side_effect

        # First user searches "geben" (German → English)
        result1 = get_or_create_translations(
            text="geben",
            source_language="German",
            source_language_code="de",
            target_languages=["English"],
            target_language_codes=["en"],
            model="gpt-4.1-mini"
        )

        assert result1['success'] is True
        assert result1['cache_status']['English'] == 'fresh'
        phrase_id = result1['phrase_id']

        # Verify phrase and translation were created
        assert Phrase.query.get(phrase_id) is not None
        assert PhraseTranslation.query.filter_by(phrase_id=phrase_id, target_language_code='en').first() is not None

        # Second user searches "geben" (German → English) - cache hit
        result2 = get_or_create_translations(
            text="geben",
            source_language="German",
            source_language_code="de",
            target_languages=["English"],
            target_language_codes=["en"],
            model="gpt-4.1-mini"
        )

        assert result2['success'] is True
        assert result2['phrase_id'] == phrase_id  # Same phrase
        assert result2['cache_status']['English'] == 'cached'  # Cache hit!

        # Third user searches "geben" (German → French) - reuses phrase, fresh translation
        result3 = get_or_create_translations(
            text="geben",
            source_language="German",
            source_language_code="de",
            target_languages=["French"],
            target_language_codes=["fr"],
            model="gpt-4.1-mini"
        )

        assert result3['success'] is True
        assert result3['phrase_id'] == phrase_id  # Same phrase
        assert result3['cache_status']['French'] == 'fresh'  # New translation

        # Verify we now have both English and French cached for the same phrase
        en_cached = PhraseTranslation.query.filter_by(phrase_id=phrase_id, target_language_code='en').first()
        fr_cached = PhraseTranslation.query.filter_by(phrase_id=phrase_id, target_language_code='fr').first()

        assert en_cached is not None
        assert fr_cached is not None
        assert en_cached.phrase_id == fr_cached.phrase_id  # Same phrase

        # Verify LLM was called exactly twice (once for English, once for French)
        assert mock_translate.call_count == 2


if __name__ == '__main__':
    pytest.main([__file__, '-v'])