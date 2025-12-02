"""
Unit tests for QuizTriggerService.

Tests the quiz triggering logic including:
- Quiz mode enabled/disabled checks
- Search counter threshold checks
- Phrase selection based on spaced repetition
- Language filtering
- Mastered phrase exclusion
"""

import sys
import os
import pytest
from datetime import date, timedelta

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models import db
from models.user import User
from models.language import Language
from models.phrase import Phrase
from models.user_learning_progress import UserLearningProgress
from services.quiz_trigger_service import QuizTriggerService


@pytest.fixture(scope='function')
def app_context():
    """Create a fresh app context and database for each test"""
    app = create_app('testing')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'  # In-memory database
    app.config['TESTING'] = True

    with app.app_context():
        db.create_all()

        # Add test languages if they don't exist
        languages_data = [
            ('en', 'English', 'English', 1),
            ('de', 'Deutsch', 'German', 2),
            ('ru', 'Русский', 'Russian', 3),
            ('fr', 'Français', 'French', 4),
        ]

        for code, original, en_name, order in languages_data:
            if not Language.query.filter_by(code=code).first():
                lang = Language(code=code, original_name=original, en_name=en_name, display_order=order)
                db.session.add(lang)

        db.session.commit()

        yield app

        db.session.remove()
        db.drop_all()


@pytest.fixture
def test_user(app_context):
    """Create a test user with default quiz settings"""
    user = User(
        google_id='test_user_quiz_123',
        email='quiz_test@example.com',
        name='Quiz Test User',
        primary_language_code='en',
        translator_languages=["en", "de"],
        quiz_mode_enabled=True,
        quiz_frequency=5,
        searches_since_last_quiz=0
    )
    db.session.add(user)
    db.session.commit()
    return user


class TestShouldTriggerQuiz:
    """Test should_trigger_quiz method"""

    def test_quiz_mode_disabled(self, app_context, test_user):
        """Should not trigger quiz when quiz mode is disabled"""
        test_user.quiz_mode_enabled = False
        db.session.commit()

        result = QuizTriggerService.should_trigger_quiz(test_user)

        assert result['should_trigger'] is False
        assert result['reason'] == 'quiz_mode_disabled'
        assert result['eligible_phrase'] is None

    def test_threshold_not_reached(self, app_context, test_user):
        """Should not trigger quiz when search counter hasn't reached threshold"""
        test_user.searches_since_last_quiz = 3
        test_user.quiz_frequency = 5
        db.session.commit()

        result = QuizTriggerService.should_trigger_quiz(test_user)

        assert result['should_trigger'] is False
        assert result['reason'] == 'threshold_not_reached'
        assert result['searches_remaining'] == 2
        assert result['eligible_phrase'] is None

    def test_no_phrases_due_for_review(self, app_context, test_user):
        """Should not trigger quiz when no phrases are due for review"""
        test_user.searches_since_last_quiz = 5
        db.session.commit()

        result = QuizTriggerService.should_trigger_quiz(test_user)

        assert result['should_trigger'] is False
        assert result['reason'] == 'no_phrases_due_for_review'
        assert result['eligible_phrase'] is None

    def test_successfully_triggers_quiz(self, app_context, test_user):
        """Should trigger quiz when all conditions are met"""
        # Create a phrase
        phrase = Phrase(text='geben', language_code='de', type='word')
        db.session.add(phrase)
        db.session.flush()

        # Create learning progress that's due for review
        progress = UserLearningProgress(
            user_id=test_user.id,
            phrase_id=phrase.id,
            stage='basic',
            next_review_date=date.today()
        )
        db.session.add(progress)

        # Set user to threshold
        test_user.searches_since_last_quiz = 5
        db.session.commit()

        result = QuizTriggerService.should_trigger_quiz(test_user)

        assert result['should_trigger'] is True
        assert result['reason'] == 'quiz_triggered'
        assert result['eligible_phrase'] is not None
        assert result['eligible_phrase'].phrase_id == phrase.id

    def test_triggers_with_overdue_phrase(self, app_context, test_user):
        """Should trigger quiz when phrase is overdue"""
        # Create a phrase
        phrase = Phrase(text='katze', language_code='de', type='word')
        db.session.add(phrase)
        db.session.flush()

        # Create learning progress that's overdue
        progress = UserLearningProgress(
            user_id=test_user.id,
            phrase_id=phrase.id,
            stage='intermediate',
            next_review_date=date.today() - timedelta(days=3)  # 3 days overdue
        )
        db.session.add(progress)

        test_user.searches_since_last_quiz = 5
        db.session.commit()

        result = QuizTriggerService.should_trigger_quiz(test_user)

        assert result['should_trigger'] is True
        assert result['eligible_phrase'].phrase_id == phrase.id


class TestGetPhraseForQuiz:
    """Test get_phrase_for_quiz method"""

    def test_returns_none_when_no_languages(self, app_context, test_user):
        """Should return None when user has no active languages"""
        test_user.translator_languages = []
        db.session.commit()

        result = QuizTriggerService.get_phrase_for_quiz(test_user)

        assert result is None

    def test_returns_none_when_no_eligible_phrases(self, app_context, test_user):
        """Should return None when no phrases are due for review"""
        # Create a phrase with future review date
        phrase = Phrase(text='buch', language_code='de', type='word')
        db.session.add(phrase)
        db.session.flush()

        progress = UserLearningProgress(
            user_id=test_user.id,
            phrase_id=phrase.id,
            stage='basic',
            next_review_date=date.today() + timedelta(days=5)  # Future date
        )
        db.session.add(progress)
        db.session.commit()

        result = QuizTriggerService.get_phrase_for_quiz(test_user)

        assert result is None

    def test_excludes_mastered_phrases(self, app_context, test_user):
        """Should exclude mastered phrases from quiz selection"""
        # Create mastered phrase
        phrase1 = Phrase(text='hund', language_code='de', type='word')
        db.session.add(phrase1)
        db.session.flush()

        progress1 = UserLearningProgress(
            user_id=test_user.id,
            phrase_id=phrase1.id,
            stage='mastered',  # Mastered - should be excluded
            next_review_date=date.today()
        )
        db.session.add(progress1)

        # Create non-mastered phrase
        phrase2 = Phrase(text='katze', language_code='de', type='word')
        db.session.add(phrase2)
        db.session.flush()

        progress2 = UserLearningProgress(
            user_id=test_user.id,
            phrase_id=phrase2.id,
            stage='basic',
            next_review_date=date.today()
        )
        db.session.add(progress2)
        db.session.commit()

        result = QuizTriggerService.get_phrase_for_quiz(test_user)

        assert result is not None
        assert result.phrase_id == phrase2.id  # Should select non-mastered phrase

    def test_filters_by_active_languages(self, app_context, test_user):
        """Should only return phrases in user's active languages"""
        # User has ["en", "de"] as active languages
        # Create phrase in Russian (not active)
        phrase_ru = Phrase(text='кот', language_code='ru', type='word')
        db.session.add(phrase_ru)
        db.session.flush()

        progress_ru = UserLearningProgress(
            user_id=test_user.id,
            phrase_id=phrase_ru.id,
            stage='basic',
            next_review_date=date.today()
        )
        db.session.add(progress_ru)

        # Create phrase in German (active)
        phrase_de = Phrase(text='katze', language_code='de', type='word')
        db.session.add(phrase_de)
        db.session.flush()

        progress_de = UserLearningProgress(
            user_id=test_user.id,
            phrase_id=phrase_de.id,
            stage='basic',
            next_review_date=date.today()
        )
        db.session.add(progress_de)
        db.session.commit()

        result = QuizTriggerService.get_phrase_for_quiz(test_user)

        assert result is not None
        assert result.phrase_id == phrase_de.id  # Should select German phrase only

    def test_excludes_non_quizzable_phrases(self, app_context, test_user):
        """Should exclude phrases marked as is_quizzable=False"""
        # Create non-quizzable phrase (e.g., very long sentence)
        phrase_non_quizzable = Phrase(
            text='this is a very long sentence that should not be quizzable',
            language_code='de',
            type='sentence',
            is_quizzable=False  # Marked as non-quizzable
        )
        db.session.add(phrase_non_quizzable)
        db.session.flush()

        progress_non_quizzable = UserLearningProgress(
            user_id=test_user.id,
            phrase_id=phrase_non_quizzable.id,
            stage='basic',
            next_review_date=date.today()
        )
        db.session.add(progress_non_quizzable)

        # Create quizzable phrase
        phrase_quizzable = Phrase(
            text='katze',
            language_code='de',
            type='word',
            is_quizzable=True  # Explicitly quizzable
        )
        db.session.add(phrase_quizzable)
        db.session.flush()

        progress_quizzable = UserLearningProgress(
            user_id=test_user.id,
            phrase_id=phrase_quizzable.id,
            stage='basic',
            next_review_date=date.today()
        )
        db.session.add(progress_quizzable)
        db.session.commit()

        result = QuizTriggerService.get_phrase_for_quiz(test_user)

        assert result is not None
        assert result.phrase_id == phrase_quizzable.id  # Should select quizzable phrase only
        assert result.phrase.is_quizzable is True

    def test_orders_by_oldest_review_date(self, app_context, test_user):
        """Should return the most overdue phrase first"""
        # Create three phrases with different review dates
        phrases_data = [
            ('hund', date.today() - timedelta(days=5)),  # Most overdue
            ('katze', date.today() - timedelta(days=2)),
            ('buch', date.today()),  # Due today
        ]

        for text, review_date in phrases_data:
            phrase = Phrase(text=text, language_code='de', type='word')
            db.session.add(phrase)
            db.session.flush()

            progress = UserLearningProgress(
                user_id=test_user.id,
                phrase_id=phrase.id,
                stage='basic',
                next_review_date=review_date
            )
            db.session.add(progress)

        db.session.commit()

        result = QuizTriggerService.get_phrase_for_quiz(test_user)

        assert result is not None
        # Should select the most overdue phrase (hund)
        assert result.phrase.text == 'hund'
        assert result.next_review_date == date.today() - timedelta(days=5)

    def test_includes_phrases_due_today(self, app_context, test_user):
        """Should include phrases with review date equal to today"""
        phrase = Phrase(text='heute', language_code='de', type='word')
        db.session.add(phrase)
        db.session.flush()

        progress = UserLearningProgress(
            user_id=test_user.id,
            phrase_id=phrase.id,
            stage='basic',
            next_review_date=date.today()  # Exactly today
        )
        db.session.add(progress)
        db.session.commit()

        result = QuizTriggerService.get_phrase_for_quiz(test_user)

        assert result is not None
        assert result.phrase_id == phrase.id

    def test_multiple_users_independent_progress(self, app_context, test_user):
        """Should only return phrases for the specific user"""
        # Create another user
        user2 = User(
            google_id='test_user_2',
            email='user2@example.com',
            name='User 2',
            primary_language_code='en',
            translator_languages=["en", "de"]
        )
        db.session.add(user2)
        db.session.flush()

        # Create phrase
        phrase = Phrase(text='wasser', language_code='de', type='word')
        db.session.add(phrase)
        db.session.flush()

        # Create progress for user2 only
        progress = UserLearningProgress(
            user_id=user2.id,
            phrase_id=phrase.id,
            stage='basic',
            next_review_date=date.today()
        )
        db.session.add(progress)
        db.session.commit()

        # Query for test_user (should return None)
        result = QuizTriggerService.get_phrase_for_quiz(test_user)

        assert result is None  # test_user has no phrases due

    def test_handles_all_stages_except_mastered(self, app_context, test_user):
        """Should include basic, intermediate, and advanced stages"""
        stages = ['basic', 'intermediate', 'advanced']
        phrases = []

        for i, stage in enumerate(stages):
            phrase = Phrase(text=f'word_{i}', language_code='de', type='word')
            db.session.add(phrase)
            db.session.flush()

            progress = UserLearningProgress(
                user_id=test_user.id,
                phrase_id=phrase.id,
                stage=stage,
                next_review_date=date.today()
            )
            db.session.add(progress)
            phrases.append(phrase)

        db.session.commit()

        # Should return one of the non-mastered phrases
        result = QuizTriggerService.get_phrase_for_quiz(test_user)

        assert result is not None
        assert result.stage in stages
        assert result.stage != 'mastered'


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_exact_threshold_triggers_quiz(self, app_context, test_user):
        """Should trigger when searches_since_last_quiz equals quiz_frequency"""
        # Create eligible phrase
        phrase = Phrase(text='genau', language_code='de', type='word')
        db.session.add(phrase)
        db.session.flush()

        progress = UserLearningProgress(
            user_id=test_user.id,
            phrase_id=phrase.id,
            stage='basic',
            next_review_date=date.today()
        )
        db.session.add(progress)

        # Set exactly at threshold
        test_user.searches_since_last_quiz = test_user.quiz_frequency  # 5 == 5
        db.session.commit()

        result = QuizTriggerService.should_trigger_quiz(test_user)

        assert result['should_trigger'] is True

    def test_one_below_threshold_does_not_trigger(self, app_context, test_user):
        """Should not trigger when one search below threshold"""
        test_user.searches_since_last_quiz = test_user.quiz_frequency - 1  # 4
        db.session.commit()

        result = QuizTriggerService.should_trigger_quiz(test_user)

        assert result['should_trigger'] is False
        assert result['searches_remaining'] == 1

    def test_handles_null_translator_languages(self, app_context, test_user):
        """Should handle None translator_languages gracefully"""
        test_user.translator_languages = None
        db.session.commit()

        result = QuizTriggerService.get_phrase_for_quiz(test_user)

        assert result is None

    def test_handles_empty_translator_languages(self, app_context, test_user):
        """Should handle empty translator_languages list"""
        test_user.translator_languages = []
        db.session.commit()

        result = QuizTriggerService.get_phrase_for_quiz(test_user)

        assert result is None


class TestIntegrationScenarios:
    """Test realistic end-to-end scenarios"""

    def test_user_changes_active_languages(self, app_context, test_user):
        """Should only quiz phrases in currently active languages"""
        # User starts with ["en", "de"]
        # Create phrases in multiple languages
        phrase_de = Phrase(text='deutsch', language_code='de', type='word')
        phrase_ru = Phrase(text='русский', language_code='ru', type='word')
        db.session.add_all([phrase_de, phrase_ru])
        db.session.flush()

        progress_de = UserLearningProgress(
            user_id=test_user.id,
            phrase_id=phrase_de.id,
            stage='basic',
            next_review_date=date.today()
        )
        progress_ru = UserLearningProgress(
            user_id=test_user.id,
            phrase_id=phrase_ru.id,
            stage='basic',
            next_review_date=date.today()
        )
        db.session.add_all([progress_de, progress_ru])
        db.session.commit()

        # User has German active - should get German phrase
        result = QuizTriggerService.get_phrase_for_quiz(test_user)
        assert result.phrase_id == phrase_de.id

        # User switches to Russian only
        test_user.translator_languages = ["en", "ru"]
        db.session.commit()

        # Should now get Russian phrase
        result = QuizTriggerService.get_phrase_for_quiz(test_user)
        assert result.phrase_id == phrase_ru.id

    def test_multiple_overdue_phrases_returns_oldest(self, app_context, test_user):
        """Should prioritize the most overdue phrase"""
        overdue_dates = [
            ('sehr_alt', date.today() - timedelta(days=30)),
            ('alt', date.today() - timedelta(days=10)),
            ('bisschen_alt', date.today() - timedelta(days=1)),
        ]

        for text, review_date in overdue_dates:
            phrase = Phrase(text=text, language_code='de', type='word')
            db.session.add(phrase)
            db.session.flush()

            progress = UserLearningProgress(
                user_id=test_user.id,
                phrase_id=phrase.id,
                stage='intermediate',
                next_review_date=review_date
            )
            db.session.add(progress)

        db.session.commit()

        result = QuizTriggerService.get_phrase_for_quiz(test_user)

        assert result is not None
        assert result.phrase.text == 'sehr_alt'  # 30 days overdue


if __name__ == '__main__':
    pytest.main([__file__, '-v'])