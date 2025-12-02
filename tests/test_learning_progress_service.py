"""
Unit tests for learning progress service.

Tests the automatic learning progress tracking functionality when users
search for new phrases.
"""

import sys
import os
import pytest
from datetime import datetime

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
from services.learning_progress_service import (
    has_learning_progress,
    is_first_search,
    create_initial_progress,
    initialize_learning_progress_on_search,
    get_learning_progress,
    STAGE_BASIC,
    STAGE_INTERMEDIATE,
    STAGE_ADVANCED,
    STAGE_MASTERED
)
from uuid import uuid4


@pytest.fixture(scope='function')
def app_context():
    """Create a fresh app context and database for each test"""
    app = create_app('testing')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'  # In-memory database
    app.config['TESTING'] = True

    with app.app_context():
        db.create_all()

        # Add test languages if they don't exist
        if not Language.query.filter_by(code='en').first():
            lang_en = Language(code='en', original_name='English', en_name='English', display_order=1)
            db.session.add(lang_en)

        if not Language.query.filter_by(code='de').first():
            lang_de = Language(code='de', original_name='Deutsch', en_name='German', display_order=2)
            db.session.add(lang_de)

        db.session.commit()

        yield app

        db.session.remove()
        db.drop_all()


@pytest.fixture
def test_user(app_context):
    """Create a test user"""
    user = User(
        google_id='test_user_123',
        email='test@example.com',
        name='Test User',
        primary_language_code='en',
        translator_languages=["en", "de"]
    )
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def test_phrase(app_context):
    """Create a test phrase"""
    phrase = Phrase(
        text='geben',
        language_code='de',
        type='word',
        is_quizzable=True
    )
    db.session.add(phrase)
    db.session.commit()
    return phrase


@pytest.fixture
def test_session(app_context, test_user):
    """Create a test session"""
    session = Session(
        session_id=str(uuid4()),
        user_id=test_user.id
    )
    db.session.add(session)
    db.session.commit()
    return session


class TestHasLearningProgress:
    """Test has_learning_progress function"""

    def test_returns_false_when_no_progress_exists(self, app_context, test_user, test_phrase):
        """Should return False when no learning progress exists"""
        result = has_learning_progress(test_user.id, test_phrase.id)
        assert result is False

    def test_returns_true_when_progress_exists(self, app_context, test_user, test_phrase):
        """Should return True when learning progress exists"""
        # Create a learning progress entry
        progress = UserLearningProgress(
            user_id=test_user.id,
            phrase_id=test_phrase.id,
            stage=STAGE_BASIC
        )
        db.session.add(progress)
        db.session.commit()

        result = has_learning_progress(test_user.id, test_phrase.id)
        assert result is True


class TestIsFirstSearch:
    """Test is_first_search function"""

    def test_returns_true_when_no_search_exists(self, app_context, test_user, test_phrase):
        """Should return True when user has never searched this phrase"""
        result = is_first_search(test_user.id, test_phrase.id)
        assert result is True

    def test_returns_false_when_search_exists(self, app_context, test_user, test_phrase, test_session):
        """Should return False when user has searched this phrase before"""
        # Create a user search entry
        search = UserSearch(
            user_id=test_user.id,
            phrase_id=test_phrase.id,
            session_id=test_session.session_id,
            llm_translations_json={'en': 'to give'}
        )
        db.session.add(search)
        db.session.commit()

        result = is_first_search(test_user.id, test_phrase.id)
        assert result is False


class TestCreateInitialProgress:
    """Test create_initial_progress function"""

    def test_creates_progress_with_correct_defaults(self, app_context, test_user, test_phrase):
        """Should create learning progress with stage='basic' and all counters at 0"""
        progress = create_initial_progress(test_user.id, test_phrase.id)

        assert progress is not None
        assert progress.user_id == test_user.id
        assert progress.phrase_id == test_phrase.id
        assert progress.stage == STAGE_BASIC
        assert progress.times_reviewed == 0
        assert progress.times_correct == 0
        assert progress.times_incorrect == 0
        assert progress.next_review_date is None
        assert progress.first_seen_at is not None
        assert progress.created_at is not None

    def test_does_not_create_duplicate_progress(self, app_context, test_user, test_phrase):
        """Should not create duplicate progress for same user-phrase pair"""
        # Create first progress
        progress1 = create_initial_progress(test_user.id, test_phrase.id)
        assert progress1 is not None

        # Attempt to create duplicate
        progress2 = create_initial_progress(test_user.id, test_phrase.id)
        assert progress2 is None

        # Verify only one progress exists
        count = UserLearningProgress.query.filter_by(
            user_id=test_user.id,
            phrase_id=test_phrase.id
        ).count()
        assert count == 1

    def test_handles_database_error_gracefully(self, app_context, test_user, test_phrase):
        """Should handle database errors gracefully and return None"""
        # Create initial progress
        progress1 = create_initial_progress(test_user.id, test_phrase.id)
        assert progress1 is not None

        # Try to create duplicate - should catch IntegrityError and return None
        progress2 = create_initial_progress(test_user.id, test_phrase.id)
        assert progress2 is None


class TestInitializeLearningProgressOnSearch:
    """Test initialize_learning_progress_on_search function"""

    def test_creates_progress_on_first_search(self, app_context, test_user, test_phrase, test_session):
        """Should create learning progress when user searches phrase for the first time"""
        # Create a user search (simulating first search)
        search = UserSearch(
            user_id=test_user.id,
            phrase_id=test_phrase.id,
            session_id=test_session.session_id,
            llm_translations_json={'en': 'to give'}
        )
        db.session.add(search)
        db.session.commit()

        # Initialize learning progress
        progress = initialize_learning_progress_on_search(
            user_id=test_user.id,
            phrase_id=test_phrase.id,
            is_quizzable=True
        )

        assert progress is not None
        assert progress.stage == STAGE_BASIC
        assert progress.user_id == test_user.id
        assert progress.phrase_id == test_phrase.id

    def test_does_not_create_progress_on_repeated_search(self, app_context, test_user, test_phrase, test_session):
        """Should NOT create learning progress when user searches phrase again"""
        # Create first search
        search1 = UserSearch(
            user_id=test_user.id,
            phrase_id=test_phrase.id,
            session_id=test_session.session_id,
            llm_translations_json={'en': 'to give'}
        )
        db.session.add(search1)
        db.session.commit()

        # Create second search
        search2 = UserSearch(
            user_id=test_user.id,
            phrase_id=test_phrase.id,
            session_id=test_session.session_id,
            llm_translations_json={'en': 'to give'}
        )
        db.session.add(search2)
        db.session.commit()

        # Try to initialize learning progress after second search
        progress = initialize_learning_progress_on_search(
            user_id=test_user.id,
            phrase_id=test_phrase.id,
            is_quizzable=True
        )

        assert progress is None

        # Verify no progress was created
        count = UserLearningProgress.query.filter_by(
            user_id=test_user.id,
            phrase_id=test_phrase.id
        ).count()
        assert count == 0

    def test_does_not_create_progress_for_non_quizzable_phrases(self, app_context, test_user, test_session):
        """Should NOT create learning progress for non-quizzable phrases"""
        # Create a non-quizzable phrase (too long)
        long_phrase = Phrase(
            text='This is a very long sentence that should not be quizzable because it is too long',
            language_code='en',
            type='sentence',
            is_quizzable=False
        )
        db.session.add(long_phrase)
        db.session.commit()

        # Create a search for the non-quizzable phrase
        search = UserSearch(
            user_id=test_user.id,
            phrase_id=long_phrase.id,
            session_id=test_session.session_id,
            llm_translations_json={'de': 'Das ist ein sehr langer Satz'}
        )
        db.session.add(search)
        db.session.commit()

        # Try to initialize learning progress
        progress = initialize_learning_progress_on_search(
            user_id=test_user.id,
            phrase_id=long_phrase.id,
            is_quizzable=False
        )

        assert progress is None

        # Verify no progress was created
        count = UserLearningProgress.query.filter_by(
            user_id=test_user.id,
            phrase_id=long_phrase.id
        ).count()
        assert count == 0


class TestGetLearningProgress:
    """Test get_learning_progress function"""

    def test_returns_progress_when_exists(self, app_context, test_user, test_phrase):
        """Should return learning progress when it exists"""
        # Create a learning progress entry
        progress = UserLearningProgress(
            user_id=test_user.id,
            phrase_id=test_phrase.id,
            stage=STAGE_INTERMEDIATE,
            times_reviewed=5,
            times_correct=4,
            times_incorrect=1
        )
        db.session.add(progress)
        db.session.commit()

        # Retrieve the progress
        retrieved = get_learning_progress(test_user.id, test_phrase.id)

        assert retrieved is not None
        assert retrieved.id == progress.id
        assert retrieved.stage == STAGE_INTERMEDIATE
        assert retrieved.times_reviewed == 5
        assert retrieved.times_correct == 4
        assert retrieved.times_incorrect == 1

    def test_returns_none_when_no_progress(self, app_context, test_user, test_phrase):
        """Should return None when no learning progress exists"""
        progress = get_learning_progress(test_user.id, test_phrase.id)
        assert progress is None


class TestStageConstants:
    """Test stage constants are correctly defined"""

    def test_stage_constants(self):
        """Should have all 4 stage constants defined"""
        assert STAGE_BASIC == 'basic'
        assert STAGE_INTERMEDIATE == 'intermediate'
        assert STAGE_ADVANCED == 'advanced'
        assert STAGE_MASTERED == 'mastered'


class TestConcurrentRequests:
    """Test edge cases with concurrent requests and duplicate entries"""

    def test_handles_duplicate_key_error(self, app_context, test_user, test_phrase):
        """Should handle duplicate key errors gracefully due to unique constraint"""
        # Create first progress
        progress1 = create_initial_progress(test_user.id, test_phrase.id)
        assert progress1 is not None

        # Simulate concurrent request trying to create the same progress
        progress2 = create_initial_progress(test_user.id, test_phrase.id)
        assert progress2 is None

        # Verify only one progress exists
        count = UserLearningProgress.query.filter_by(
            user_id=test_user.id,
            phrase_id=test_phrase.id
        ).count()
        assert count == 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])