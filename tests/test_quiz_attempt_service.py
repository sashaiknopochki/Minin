"""
Unit tests for QuizAttemptService.

Tests the quiz attempt creation and question type selection logic including:
- Quiz attempt creation with valid learning progress
- Question type selection based on learning stages
- Error handling for invalid stages and missing progress
- Randomness and coverage of question types
"""

import sys
import os
import pytest
from datetime import date

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models import db
from models.user import User
from models.language import Language
from models.phrase import Phrase
from models.user_learning_progress import UserLearningProgress
from models.quiz_attempt import QuizAttempt
from services.quiz_attempt_service import QuizAttemptService


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
    """Create a test user"""
    user = User(
        google_id='test_quiz_attempt_user',
        email='quiz_attempt@example.com',
        name='Quiz Attempt Test User',
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
        type='word'
    )
    db.session.add(phrase)
    db.session.commit()
    return phrase


@pytest.fixture
def test_progress_basic(app_context, test_user, test_phrase):
    """Create learning progress at basic stage"""
    progress = UserLearningProgress(
        user_id=test_user.id,
        phrase_id=test_phrase.id,
        stage='basic',
        next_review_date=date.today()
    )
    db.session.add(progress)
    db.session.commit()
    return progress


class TestCreateQuizAttempt:
    """Test create_quiz_attempt method"""

    def test_creates_quiz_attempt_successfully(self, app_context, test_user, test_phrase, test_progress_basic):
        """Should create a quiz attempt with all required fields"""
        quiz_attempt = QuizAttemptService.create_quiz_attempt(
            user_id=test_user.id,
            phrase_id=test_phrase.id
        )

        assert quiz_attempt is not None
        assert quiz_attempt.id is not None  # flush() should assign ID
        assert quiz_attempt.user_id == test_user.id
        assert quiz_attempt.phrase_id == test_phrase.id
        assert quiz_attempt.question_type in ['multiple_choice_target', 'multiple_choice_source']
        assert quiz_attempt.was_correct is False  # Initial placeholder value
        assert quiz_attempt.prompt_json is None  # To be filled by QuestionGenerationService
        assert quiz_attempt.correct_answer is None
        assert quiz_attempt.user_answer is None

    def test_selects_correct_question_type_for_stage(self, app_context, test_user, test_phrase, test_progress_basic):
        """Should select question type appropriate for learning stage"""
        # Basic stage should get multiple choice
        quiz_attempt = QuizAttemptService.create_quiz_attempt(
            user_id=test_user.id,
            phrase_id=test_phrase.id
        )

        assert quiz_attempt.question_type in ['multiple_choice_target', 'multiple_choice_source']

    def test_raises_error_when_no_learning_progress(self, app_context, test_user, test_phrase):
        """Should raise ValueError when no learning progress exists"""
        with pytest.raises(ValueError) as exc_info:
            QuizAttemptService.create_quiz_attempt(
                user_id=test_user.id,
                phrase_id=test_phrase.id
            )

        assert "No learning progress found" in str(exc_info.value)
        assert str(test_user.id) in str(exc_info.value)
        assert str(test_phrase.id) in str(exc_info.value)

    def test_creates_different_attempts_for_same_phrase(self, app_context, test_user, test_phrase, test_progress_basic):
        """Should allow multiple quiz attempts for the same phrase"""
        # Create first attempt
        attempt1 = QuizAttemptService.create_quiz_attempt(
            user_id=test_user.id,
            phrase_id=test_phrase.id
        )
        db.session.commit()

        # Create second attempt
        attempt2 = QuizAttemptService.create_quiz_attempt(
            user_id=test_user.id,
            phrase_id=test_phrase.id
        )
        db.session.commit()

        assert attempt1.id != attempt2.id
        assert attempt1.phrase_id == attempt2.phrase_id

    def test_uses_flush_not_commit(self, app_context, test_user, test_phrase, test_progress_basic):
        """Should use flush() to get ID without committing transaction"""
        quiz_attempt = QuizAttemptService.create_quiz_attempt(
            user_id=test_user.id,
            phrase_id=test_phrase.id
        )

        # ID should be assigned by flush()
        assert quiz_attempt.id is not None

        # But we can still rollback if needed
        db.session.rollback()

        # After rollback, the attempt shouldn't exist
        count = QuizAttempt.query.filter_by(id=quiz_attempt.id).count()
        assert count == 0


class TestSelectQuestionType:
    """Test select_question_type method"""

    def test_basic_stage_returns_multiple_choice(self, app_context):
        """Should return multiple choice question types for basic stage"""
        valid_types = ['multiple_choice_target', 'multiple_choice_source']

        # Test multiple times to ensure it always returns valid type
        for _ in range(10):
            question_type = QuizAttemptService.select_question_type('basic')
            assert question_type in valid_types

    def test_intermediate_stage_returns_text_input(self, app_context):
        """Should return text input question types for intermediate stage"""
        valid_types = ['text_input_target', 'text_input_source']

        for _ in range(10):
            question_type = QuizAttemptService.select_question_type('intermediate')
            assert question_type in valid_types

    def test_advanced_stage_returns_contextual_types(self, app_context):
        """Should return advanced question types for advanced stage"""
        valid_types = ['contextual', 'definition', 'synonym']

        for _ in range(10):
            question_type = QuizAttemptService.select_question_type('advanced')
            assert question_type in valid_types

    def test_mastered_stage_raises_error(self, app_context):
        """Should raise ValueError for mastered stage"""
        with pytest.raises(ValueError) as exc_info:
            QuizAttemptService.select_question_type('mastered')

        assert "Invalid stage: mastered" in str(exc_info.value)

    def test_invalid_stage_raises_error(self, app_context):
        """Should raise ValueError for unknown stage"""
        with pytest.raises(ValueError) as exc_info:
            QuizAttemptService.select_question_type('unknown_stage')

        assert "Invalid stage: unknown_stage" in str(exc_info.value)

    def test_empty_string_stage_raises_error(self, app_context):
        """Should raise ValueError for empty string stage"""
        with pytest.raises(ValueError) as exc_info:
            QuizAttemptService.select_question_type('')

        assert "Invalid stage" in str(exc_info.value)

    def test_none_stage_raises_error(self, app_context):
        """Should raise ValueError for None stage"""
        with pytest.raises(ValueError) as exc_info:
            QuizAttemptService.select_question_type(None)

        assert "Invalid stage" in str(exc_info.value)


class TestQuestionTypeRandomness:
    """Test that question type selection is properly randomized"""

    def test_basic_stage_selects_both_types(self, app_context):
        """Should eventually select both multiple choice types for variety"""
        selected_types = set()

        # Run enough times to be confident both types will appear
        for _ in range(50):
            question_type = QuizAttemptService.select_question_type('basic')
            selected_types.add(question_type)

        # Should have selected both types
        assert 'multiple_choice_target' in selected_types
        assert 'multiple_choice_source' in selected_types

    def test_intermediate_stage_selects_both_types(self, app_context):
        """Should eventually select both text input types for variety"""
        selected_types = set()

        for _ in range(50):
            question_type = QuizAttemptService.select_question_type('intermediate')
            selected_types.add(question_type)

        assert 'text_input_target' in selected_types
        assert 'text_input_source' in selected_types

    def test_advanced_stage_selects_all_types(self, app_context):
        """Should eventually select all three advanced question types"""
        selected_types = set()

        # Need more iterations since there are 3 types
        for _ in range(100):
            question_type = QuizAttemptService.select_question_type('advanced')
            selected_types.add(question_type)

        assert 'contextual' in selected_types
        assert 'definition' in selected_types
        assert 'synonym' in selected_types


class TestIntegrationScenarios:
    """Test realistic end-to-end scenarios"""

    def test_create_attempts_for_different_stages(self, app_context, test_user, test_phrase):
        """Should create appropriate quiz attempts for each learning stage"""
        stages = ['basic', 'intermediate', 'advanced']

        for stage in stages:
            # Create progress at this stage
            progress = UserLearningProgress(
                user_id=test_user.id,
                phrase_id=test_phrase.id,
                stage=stage,
                next_review_date=date.today()
            )
            db.session.add(progress)
            db.session.commit()

            # Create quiz attempt
            quiz_attempt = QuizAttemptService.create_quiz_attempt(
                user_id=test_user.id,
                phrase_id=test_phrase.id
            )
            db.session.commit()

            # Verify question type is appropriate for stage
            if stage == 'basic':
                assert quiz_attempt.question_type in ['multiple_choice_target', 'multiple_choice_source']
            elif stage == 'intermediate':
                assert quiz_attempt.question_type in ['text_input_target', 'text_input_source']
            elif stage == 'advanced':
                assert quiz_attempt.question_type in ['contextual', 'definition', 'synonym']

            # Clean up for next iteration
            db.session.delete(progress)
            db.session.delete(quiz_attempt)
            db.session.commit()

    def test_multiple_users_independent_quiz_attempts(self, app_context, test_phrase):
        """Should create independent quiz attempts for different users"""
        # Create two users
        user1 = User(
            google_id='user1_quiz',
            email='user1@example.com',
            name='User 1',
            primary_language_code='en',
            translator_languages=["en", "de"]
        )
        user2 = User(
            google_id='user2_quiz',
            email='user2@example.com',
            name='User 2',
            primary_language_code='en',
            translator_languages=["en", "de"]
        )
        db.session.add_all([user1, user2])
        db.session.flush()

        # Create progress for both users
        progress1 = UserLearningProgress(
            user_id=user1.id,
            phrase_id=test_phrase.id,
            stage='basic',
            next_review_date=date.today()
        )
        progress2 = UserLearningProgress(
            user_id=user2.id,
            phrase_id=test_phrase.id,
            stage='intermediate',
            next_review_date=date.today()
        )
        db.session.add_all([progress1, progress2])
        db.session.commit()

        # Create quiz attempts
        attempt1 = QuizAttemptService.create_quiz_attempt(user1.id, test_phrase.id)
        attempt2 = QuizAttemptService.create_quiz_attempt(user2.id, test_phrase.id)
        db.session.commit()

        # Verify they're independent
        assert attempt1.user_id != attempt2.user_id
        assert attempt1.id != attempt2.id
        # Different stages should get different question type categories
        assert attempt1.question_type in ['multiple_choice_target', 'multiple_choice_source']
        assert attempt2.question_type in ['text_input_target', 'text_input_source']

    def test_quiz_attempt_persists_after_commit(self, app_context, test_user, test_phrase, test_progress_basic):
        """Should persist quiz attempt to database after commit"""
        quiz_attempt = QuizAttemptService.create_quiz_attempt(
            user_id=test_user.id,
            phrase_id=test_phrase.id
        )
        attempt_id = quiz_attempt.id

        db.session.commit()

        # Retrieve from database
        retrieved = QuizAttempt.query.get(attempt_id)

        assert retrieved is not None
        assert retrieved.id == attempt_id
        assert retrieved.user_id == test_user.id
        assert retrieved.phrase_id == test_phrase.id
        assert retrieved.question_type == quiz_attempt.question_type


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_case_sensitive_stage_names(self, app_context):
        """Should be case-sensitive for stage names"""
        # Lowercase 'basic' should work
        question_type = QuizAttemptService.select_question_type('basic')
        assert question_type in ['multiple_choice_target', 'multiple_choice_source']

        # Uppercase 'BASIC' should fail
        with pytest.raises(ValueError):
            QuizAttemptService.select_question_type('BASIC')

    def test_whitespace_in_stage_names(self, app_context):
        """Should not accept stages with whitespace"""
        with pytest.raises(ValueError):
            QuizAttemptService.select_question_type(' basic ')

        with pytest.raises(ValueError):
            QuizAttemptService.select_question_type('basic ')

    def test_wrong_user_id_raises_error(self, app_context, test_phrase, test_progress_basic):
        """Should raise error when user_id doesn't match progress"""
        # Progress exists for test_user, try with different user_id
        with pytest.raises(ValueError):
            QuizAttemptService.create_quiz_attempt(
                user_id=99999,  # Non-existent user
                phrase_id=test_phrase.id
            )


if __name__ == '__main__':
    pytest.main([__file__, '-v'])