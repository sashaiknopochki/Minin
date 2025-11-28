"""
Integration tests for translation search flow with automatic learning progress tracking.

Tests the complete flow from translation request through to learning progress creation.
"""

import sys
import os
import pytest
from unittest.mock import patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models import db
from models.user import User
from models.language import Language
from models.phrase import Phrase
from models.user_searches import UserSearch
from models.user_learning_progress import UserLearningProgress
from models.session import Session
from services.learning_progress_service import STAGE_BASIC


@pytest.fixture(scope='function')
def client():
    """Create a test client with fresh database for each test"""
    app = create_app('development')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False

    with app.app_context():
        db.create_all()

        # Add test languages
        lang_en = Language(code='en', original_name='English', en_name='English', display_order=1)
        lang_de = Language(code='de', original_name='Deutsch', en_name='German', display_order=2)
        lang_ru = Language(code='ru', original_name='Русский', en_name='Russian', display_order=3)
        db.session.add_all([lang_en, lang_de, lang_ru])
        db.session.commit()

        with app.test_client() as client:
            yield client

        db.session.remove()
        db.drop_all()


@pytest.fixture
def authenticated_user(client):
    """Create and authenticate a test user"""
    with client.application.app_context():
        user = User(
            google_id='test_user_integration',
            email='integration@example.com',
            name='Integration Test User',
            primary_language_code='en',
            translator_languages=["en", "de", "ru"]
        )
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    # Mock the current_user to simulate authentication
    return user_id


class TestTranslationWithLearningProgressIntegration:
    """Integration tests for the complete translation + learning progress flow"""

    @patch('routes.translation.get_or_create_translations')
    @patch('flask_login.utils._get_user')
    def test_first_search_creates_learning_progress(
        self,
        mock_get_user,
        mock_translate,
        client,
        authenticated_user
    ):
        """
        Integration test: First search for a phrase should create learning progress entry

        Flow:
        1. User searches for a phrase for the first time
        2. Translation is successful
        3. Search is logged in user_searches
        4. Learning progress is automatically created with stage='basic'
        """
        # Setup mock user authentication
        with client.application.app_context():
            user = User.query.get(authenticated_user)
            mock_get_user.return_value = user

            # Mock successful translation response
            mock_translate.return_value = {
                'success': True,
                'original_text': 'geben',
                'source_language': 'German',
                'target_languages': ['English'],
                'native_language': 'English',
                'translations': {
                    'English': [['to give', 'verb', 'hand over, present']]
                },
                'source_info': ['geben', 'verb', 'regular verb'],
                'model': 'gpt-4.1-mini',
                'usage': {
                    'prompt_tokens': 100,
                    'completion_tokens': 50,
                    'total_tokens': 150
                }
            }

            # Make translation request
            response = client.post('/translation/translate', json={
                'text': 'geben',
                'source_language': 'German',
                'target_languages': ['English'],
                'native_language': 'English'
            })

            # Verify response
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True

            # Verify phrase was created
            phrase = Phrase.query.filter_by(text='geben', language_code='de').first()
            assert phrase is not None
            assert phrase.is_quizzable is True

            # Verify user search was logged
            user_search = UserSearch.query.filter_by(
                user_id=authenticated_user,
                phrase_id=phrase.id
            ).first()
            assert user_search is not None
            assert user_search.llm_translations_json == {'English': [['to give', 'verb', 'hand over, present']]}

            # Verify learning progress was created
            progress = UserLearningProgress.query.filter_by(
                user_id=authenticated_user,
                phrase_id=phrase.id
            ).first()
            assert progress is not None
            assert progress.stage == STAGE_BASIC
            assert progress.times_reviewed == 0
            assert progress.times_correct == 0
            assert progress.times_incorrect == 0
            assert progress.next_review_date is None

    @patch('routes.translation.get_or_create_translations')
    @patch('flask_login.utils._get_user')
    def test_repeated_search_does_not_create_duplicate_progress(
        self,
        mock_get_user,
        mock_translate,
        client,
        authenticated_user
    ):
        """
        Integration test: Searching same phrase again should NOT create duplicate progress

        Flow:
        1. User searches phrase first time → creates progress
        2. User searches same phrase again → does NOT create duplicate progress
        3. Only one learning progress entry exists
        """
        # Setup mock user authentication
        with client.application.app_context():
            user = User.query.get(authenticated_user)
            mock_get_user.return_value = user

            # Mock successful translation response
            mock_translate.return_value = {
                'success': True,
                'original_text': 'katze',
                'source_language': 'German',
                'target_languages': ['English'],
                'native_language': 'English',
                'translations': {
                    'English': [['cat', 'noun', 'domestic animal']]
                },
                'source_info': ['katze', 'noun', 'feminine noun'],
                'model': 'gpt-4.1-mini',
                'usage': {'prompt_tokens': 100, 'completion_tokens': 50, 'total_tokens': 150}
            }

            # First search
            response1 = client.post('/translation/translate', json={
                'text': 'katze',
                'source_language': 'German',
                'target_languages': ['English']
            })
            assert response1.status_code == 200

            # Get phrase ID
            phrase = Phrase.query.filter_by(text='katze', language_code='de').first()
            assert phrase is not None

            # Verify learning progress was created
            progress_count_1 = UserLearningProgress.query.filter_by(
                user_id=authenticated_user,
                phrase_id=phrase.id
            ).count()
            assert progress_count_1 == 1

            # Second search (same phrase)
            response2 = client.post('/translation/translate', json={
                'text': 'katze',
                'source_language': 'German',
                'target_languages': ['English']
            })
            assert response2.status_code == 200

            # Verify no duplicate progress was created
            progress_count_2 = UserLearningProgress.query.filter_by(
                user_id=authenticated_user,
                phrase_id=phrase.id
            ).count()
            assert progress_count_2 == 1  # Still only one

            # Verify two searches were logged
            search_count = UserSearch.query.filter_by(
                user_id=authenticated_user,
                phrase_id=phrase.id
            ).count()
            assert search_count == 2

    @patch('routes.translation.get_or_create_translations')
    @patch('flask_login.utils._get_user')
    def test_non_quizzable_phrase_does_not_create_progress(
        self,
        mock_get_user,
        mock_translate,
        client,
        authenticated_user
    ):
        """
        Integration test: Non-quizzable phrases should not create learning progress

        Flow:
        1. User searches for a long phrase (non-quizzable)
        2. Translation is successful
        3. Search is logged
        4. Learning progress is NOT created
        """
        # Setup mock user authentication
        with client.application.app_context():
            user = User.query.get(authenticated_user)
            mock_get_user.return_value = user

            long_text = 'This is a very long sentence that exceeds the maximum quizzable length'

            # Mock successful translation response
            mock_translate.return_value = {
                'success': True,
                'original_text': long_text,
                'source_language': 'English',
                'target_languages': ['German'],
                'native_language': 'English',
                'translations': {
                    'German': [['Das ist ein sehr langer Satz', 'sentence', '']]
                },
                'source_info': [long_text, 'sentence', ''],
                'model': 'gpt-4.1-mini',
                'usage': {'prompt_tokens': 100, 'completion_tokens': 50, 'total_tokens': 150}
            }

            # Make translation request
            response = client.post('/translation/translate', json={
                'text': long_text,
                'source_language': 'English',
                'target_languages': ['German']
            })

            # Verify response
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True

            # Verify phrase was created as non-quizzable
            phrase = Phrase.query.filter_by(
                text=long_text.strip().lower(),
                language_code='en'
            ).first()
            assert phrase is not None
            assert phrase.is_quizzable is False  # Should be non-quizzable

            # Verify user search was logged
            search_count = UserSearch.query.filter_by(
                user_id=authenticated_user,
                phrase_id=phrase.id
            ).count()
            assert search_count == 1

            # Verify NO learning progress was created
            progress_count = UserLearningProgress.query.filter_by(
                user_id=authenticated_user,
                phrase_id=phrase.id
            ).count()
            assert progress_count == 0  # No progress for non-quizzable phrases

    @patch('routes.translation.get_or_create_translations')
    @patch('flask_login.utils._get_user')
    def test_unauthenticated_user_does_not_create_progress(
        self,
        mock_get_user,
        mock_translate,
        client
    ):
        """
        Integration test: Unauthenticated users should not create learning progress

        Flow:
        1. Unauthenticated user searches for a phrase
        2. Translation is successful
        3. NO search is logged
        4. NO learning progress is created
        """
        # Mock unauthenticated user
        mock_get_user.return_value = MagicMock(is_authenticated=False)

        with client.application.app_context():
            # Mock successful translation response
            mock_translate.return_value = {
                'success': True,
                'original_text': 'hund',
                'source_language': 'German',
                'target_languages': ['English'],
                'native_language': 'English',
                'translations': {
                    'English': [['dog', 'noun', 'domestic animal']]
                },
                'source_info': ['hund', 'noun', 'masculine noun'],
                'model': 'gpt-4.1-mini',
                'usage': {'prompt_tokens': 100, 'completion_tokens': 50, 'total_tokens': 150}
            }

            # Make translation request
            response = client.post('/translation/translate', json={
                'text': 'hund',
                'source_language': 'German',
                'target_languages': ['English']
            })

            # Verify response
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True

            # Verify NO user searches were logged
            search_count = UserSearch.query.count()
            assert search_count == 0

            # Verify NO learning progress was created
            progress_count = UserLearningProgress.query.count()
            assert progress_count == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])