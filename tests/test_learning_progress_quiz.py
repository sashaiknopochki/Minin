"""
Unit tests for LearningProgressService quiz-related functions.

Tests the quiz update logic including:
- update_after_quiz() main orchestration
- Stage advancement criteria (basic→intermediate→advanced→mastered)
- Counter resets when advancing stages
- Spaced repetition interval calculation
- Edge cases and error handling

### CRITICAL: Uses create_app('testing') to avoid destroying real database
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
from models.quiz_attempt import QuizAttempt
from services.learning_progress_service import (
    update_after_quiz,
    _should_advance_stage,
    _get_next_stage,
    _calculate_next_review,
    STAGE_BASIC,
    STAGE_INTERMEDIATE,
    STAGE_ADVANCED,
    STAGE_MASTERED
)


@pytest.fixture(scope='function')
def app_context():
    """
    Create a fresh app context with IN-MEMORY database for each test.

    CRITICAL: Uses create_app('testing') to ensure we NEVER touch the real database.
    The 'testing' config starts with sqlite:///:memory: from the beginning.
    """
    # ✅ CORRECT: Use 'testing' config which starts with :memory:
    app = create_app('testing')

    with app.app_context():
        db.create_all()

        # Add test languages
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
        google_id='test_quiz_user',
        email='quiz@example.com',
        name='Quiz Test User',
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


# ============================================================================
# update_after_quiz() TESTS - Main orchestration function
# ============================================================================

def test_update_after_quiz_correct_answer_increments_times_correct(app_context, test_user, test_phrase):
    """Test that times_correct is incremented when answer is correct"""
    # Create progress
    progress = UserLearningProgress(
        user_id=test_user.id,
        phrase_id=test_phrase.id,
        stage=STAGE_BASIC,
        times_reviewed=0,
        times_correct=0,
        times_incorrect=0
    )
    db.session.add(progress)
    db.session.commit()

    # Create quiz attempt with correct answer
    quiz_attempt = QuizAttempt(
        user_id=test_user.id,
        phrase_id=test_phrase.id,
        question_type='multiple_choice_target',
        correct_answer='to give',
        was_correct=True
    )
    db.session.add(quiz_attempt)
    db.session.commit()

    # Update progress
    result = update_after_quiz(quiz_attempt.id)

    # Refresh from database
    updated_progress = UserLearningProgress.query.get(progress.id)

    assert updated_progress.times_reviewed == 1
    assert updated_progress.times_correct == 1
    assert updated_progress.times_incorrect == 0
    assert updated_progress.last_reviewed_at is not None


def test_update_after_quiz_incorrect_answer_increments_times_incorrect(app_context, test_user, test_phrase):
    """Test that times_incorrect is incremented when answer is incorrect"""
    # Create progress
    progress = UserLearningProgress(
        user_id=test_user.id,
        phrase_id=test_phrase.id,
        stage=STAGE_BASIC,
        times_reviewed=0,
        times_correct=0,
        times_incorrect=0
    )
    db.session.add(progress)
    db.session.commit()

    # Create quiz attempt with incorrect answer
    quiz_attempt = QuizAttempt(
        user_id=test_user.id,
        phrase_id=test_phrase.id,
        question_type='multiple_choice_target',
        correct_answer='to give',
        was_correct=False
    )
    db.session.add(quiz_attempt)
    db.session.commit()

    # Update progress
    result = update_after_quiz(quiz_attempt.id)

    # Refresh from database
    updated_progress = UserLearningProgress.query.get(progress.id)

    assert updated_progress.times_reviewed == 1
    assert updated_progress.times_correct == 0
    assert updated_progress.times_incorrect == 1


def test_update_after_quiz_advances_stage_and_resets_counters(app_context, test_user, test_phrase):
    """Test that advancing stage resets times_correct and times_incorrect"""
    # Create progress at basic stage with 2 correct (ready to advance)
    progress = UserLearningProgress(
        user_id=test_user.id,
        phrase_id=test_phrase.id,
        stage=STAGE_BASIC,
        times_reviewed=2,
        times_correct=1,  # Will become 2 after this quiz, triggering advancement
        times_incorrect=0
    )
    db.session.add(progress)
    db.session.commit()

    # Create quiz attempt with correct answer (this will make it 2 correct)
    quiz_attempt = QuizAttempt(
        user_id=test_user.id,
        phrase_id=test_phrase.id,
        question_type='multiple_choice_target',
        correct_answer='to give',
        was_correct=True
    )
    db.session.add(quiz_attempt)
    db.session.commit()

    # Update progress
    result = update_after_quiz(quiz_attempt.id)

    # Check result
    assert result['old_stage'] == STAGE_BASIC
    assert result['new_stage'] == STAGE_INTERMEDIATE
    assert result['stage_advanced'] is True

    # Refresh from database and verify counters were reset
    updated_progress = UserLearningProgress.query.get(progress.id)

    assert updated_progress.stage == STAGE_INTERMEDIATE
    assert updated_progress.times_correct == 0  # Reset!
    assert updated_progress.times_incorrect == 0  # Reset!
    assert updated_progress.times_reviewed == 3  # Still incremented


def test_update_after_quiz_calculates_next_review_date(app_context, test_user, test_phrase):
    """Test that next_review_date is calculated correctly"""
    # Create progress
    progress = UserLearningProgress(
        user_id=test_user.id,
        phrase_id=test_phrase.id,
        stage=STAGE_BASIC,
        times_reviewed=0,
        times_correct=0,
        times_incorrect=0,
        next_review_date=None
    )
    db.session.add(progress)
    db.session.commit()

    # Create quiz attempt with correct answer
    quiz_attempt = QuizAttempt(
        user_id=test_user.id,
        phrase_id=test_phrase.id,
        question_type='multiple_choice_target',
        correct_answer='to give',
        was_correct=True
    )
    db.session.add(quiz_attempt)
    db.session.commit()

    # Update progress
    result = update_after_quiz(quiz_attempt.id)

    # Refresh from database
    updated_progress = UserLearningProgress.query.get(progress.id)

    # Basic + correct = 1 day from today
    expected_date = date.today() + timedelta(days=1)
    assert updated_progress.next_review_date == expected_date
    assert result['next_review_date'] == expected_date


def test_update_after_quiz_raises_error_for_missing_quiz_attempt(app_context):
    """Test that update_after_quiz raises ValueError for non-existent quiz attempt"""
    with pytest.raises(ValueError, match="Quiz attempt .* not found"):
        update_after_quiz(quiz_attempt_id=99999)


def test_update_after_quiz_raises_error_for_missing_progress(app_context, test_user, test_phrase):
    """Test that update_after_quiz raises ValueError when progress doesn't exist"""
    # Create quiz attempt WITHOUT creating progress
    quiz_attempt = QuizAttempt(
        user_id=test_user.id,
        phrase_id=test_phrase.id,
        question_type='multiple_choice_target',
        correct_answer='to give',
        was_correct=True
    )
    db.session.add(quiz_attempt)
    db.session.commit()

    with pytest.raises(ValueError, match="No progress found"):
        update_after_quiz(quiz_attempt.id)


# ============================================================================
# _should_advance_stage() TESTS - Stage advancement criteria
# ============================================================================

def test_should_advance_basic_with_2_correct(app_context, test_user, test_phrase):
    """Test basic stage advances with 2 correct answers"""
    progress = UserLearningProgress(
        user_id=test_user.id,
        phrase_id=test_phrase.id,
        stage=STAGE_BASIC,
        times_correct=2,
        times_incorrect=0
    )

    assert _should_advance_stage(progress) is True


def test_should_not_advance_basic_with_1_correct(app_context, test_user, test_phrase):
    """Test basic stage does NOT advance with only 1 correct answer"""
    progress = UserLearningProgress(
        user_id=test_user.id,
        phrase_id=test_phrase.id,
        stage=STAGE_BASIC,
        times_correct=1,
        times_incorrect=0
    )

    assert _should_advance_stage(progress) is False


def test_should_advance_intermediate_with_2_correct(app_context, test_user, test_phrase):
    """Test intermediate stage advances with 2 correct answers"""
    progress = UserLearningProgress(
        user_id=test_user.id,
        phrase_id=test_phrase.id,
        stage=STAGE_INTERMEDIATE,
        times_correct=2,
        times_incorrect=0
    )

    assert _should_advance_stage(progress) is True


def test_should_not_advance_intermediate_with_1_correct(app_context, test_user, test_phrase):
    """Test intermediate stage does NOT advance with only 1 correct answer"""
    progress = UserLearningProgress(
        user_id=test_user.id,
        phrase_id=test_phrase.id,
        stage=STAGE_INTERMEDIATE,
        times_correct=1,
        times_incorrect=0
    )

    assert _should_advance_stage(progress) is False


def test_should_advance_advanced_with_3_correct(app_context, test_user, test_phrase):
    """Test advanced stage advances with 3 correct answers"""
    progress = UserLearningProgress(
        user_id=test_user.id,
        phrase_id=test_phrase.id,
        stage=STAGE_ADVANCED,
        times_correct=3,
        times_incorrect=0
    )

    assert _should_advance_stage(progress) is True


def test_should_not_advance_advanced_with_2_correct(app_context, test_user, test_phrase):
    """Test advanced stage does NOT advance with only 2 correct answers"""
    progress = UserLearningProgress(
        user_id=test_user.id,
        phrase_id=test_phrase.id,
        stage=STAGE_ADVANCED,
        times_correct=2,
        times_incorrect=0
    )

    assert _should_advance_stage(progress) is False


def test_should_not_advance_mastered(app_context, test_user, test_phrase):
    """Test mastered stage NEVER advances (terminal state)"""
    progress = UserLearningProgress(
        user_id=test_user.id,
        phrase_id=test_phrase.id,
        stage=STAGE_MASTERED,
        times_correct=100,  # Even with many correct answers
        times_incorrect=0
    )

    assert _should_advance_stage(progress) is False


# ============================================================================
# _get_next_stage() TESTS - Stage progression
# ============================================================================

def test_get_next_stage_from_basic(app_context):
    """Test that basic progresses to intermediate"""
    assert _get_next_stage(STAGE_BASIC) == STAGE_INTERMEDIATE


def test_get_next_stage_from_intermediate(app_context):
    """Test that intermediate progresses to advanced"""
    assert _get_next_stage(STAGE_INTERMEDIATE) == STAGE_ADVANCED


def test_get_next_stage_from_advanced(app_context):
    """Test that advanced progresses to mastered"""
    assert _get_next_stage(STAGE_ADVANCED) == STAGE_MASTERED


def test_get_next_stage_from_mastered(app_context):
    """Test that mastered stays mastered (terminal state)"""
    assert _get_next_stage(STAGE_MASTERED) == STAGE_MASTERED


def test_get_next_stage_invalid_stage_defaults_to_basic(app_context):
    """Test that invalid stage defaults to basic"""
    assert _get_next_stage('invalid_stage') == STAGE_BASIC


# ============================================================================
# _calculate_next_review() TESTS - Spaced repetition intervals
# ============================================================================

def test_calculate_next_review_basic_correct(app_context, test_user, test_phrase):
    """Test basic stage + correct answer = 1 day"""
    progress = UserLearningProgress(
        user_id=test_user.id,
        phrase_id=test_phrase.id,
        stage=STAGE_BASIC,
        times_correct=0
    )

    next_date = _calculate_next_review(progress, was_correct=True)
    expected_date = date.today() + timedelta(days=1)

    assert next_date == expected_date


def test_calculate_next_review_basic_incorrect(app_context, test_user, test_phrase):
    """Test basic stage + incorrect answer = 0 days (same day)"""
    progress = UserLearningProgress(
        user_id=test_user.id,
        phrase_id=test_phrase.id,
        stage=STAGE_BASIC,
        times_correct=0
    )

    next_date = _calculate_next_review(progress, was_correct=False)
    expected_date = date.today()  # Same day

    assert next_date == expected_date


def test_calculate_next_review_intermediate_correct(app_context, test_user, test_phrase):
    """Test intermediate stage + correct answer = 3 days"""
    progress = UserLearningProgress(
        user_id=test_user.id,
        phrase_id=test_phrase.id,
        stage=STAGE_INTERMEDIATE,
        times_correct=0
    )

    next_date = _calculate_next_review(progress, was_correct=True)
    expected_date = date.today() + timedelta(days=3)

    assert next_date == expected_date


def test_calculate_next_review_intermediate_incorrect(app_context, test_user, test_phrase):
    """Test intermediate stage + incorrect answer = 1 day"""
    progress = UserLearningProgress(
        user_id=test_user.id,
        phrase_id=test_phrase.id,
        stage=STAGE_INTERMEDIATE,
        times_correct=0
    )

    next_date = _calculate_next_review(progress, was_correct=False)
    expected_date = date.today() + timedelta(days=1)

    assert next_date == expected_date


def test_calculate_next_review_advanced_correct_first_time(app_context, test_user, test_phrase):
    """Test advanced stage + correct (times_correct < 2) = 7 days"""
    progress = UserLearningProgress(
        user_id=test_user.id,
        phrase_id=test_phrase.id,
        stage=STAGE_ADVANCED,
        times_correct=0  # First correct
    )

    next_date = _calculate_next_review(progress, was_correct=True)
    expected_date = date.today() + timedelta(days=7)

    assert next_date == expected_date


def test_calculate_next_review_advanced_correct_after_2(app_context, test_user, test_phrase):
    """Test advanced stage + correct (times_correct >= 2) = 14 days"""
    progress = UserLearningProgress(
        user_id=test_user.id,
        phrase_id=test_phrase.id,
        stage=STAGE_ADVANCED,
        times_correct=2  # Already has 2 correct
    )

    next_date = _calculate_next_review(progress, was_correct=True)
    expected_date = date.today() + timedelta(days=14)

    assert next_date == expected_date


def test_calculate_next_review_advanced_incorrect(app_context, test_user, test_phrase):
    """Test advanced stage + incorrect answer = 3 days"""
    progress = UserLearningProgress(
        user_id=test_user.id,
        phrase_id=test_phrase.id,
        stage=STAGE_ADVANCED,
        times_correct=0
    )

    next_date = _calculate_next_review(progress, was_correct=False)
    expected_date = date.today() + timedelta(days=3)

    assert next_date == expected_date


def test_calculate_next_review_mastered_returns_none(app_context, test_user, test_phrase):
    """Test mastered stage returns None (never review)"""
    progress = UserLearningProgress(
        user_id=test_user.id,
        phrase_id=test_phrase.id,
        stage=STAGE_MASTERED,
        times_correct=0
    )

    # Should return None regardless of correctness
    assert _calculate_next_review(progress, was_correct=True) is None
    assert _calculate_next_review(progress, was_correct=False) is None


# ============================================================================
# INTEGRATION TESTS - Complete flow
# ============================================================================

def test_complete_progression_basic_to_intermediate(app_context, test_user, test_phrase):
    """Test complete flow: 2 correct answers advances basic to intermediate"""
    # Create progress at basic
    progress = UserLearningProgress(
        user_id=test_user.id,
        phrase_id=test_phrase.id,
        stage=STAGE_BASIC,
        times_reviewed=0,
        times_correct=0,
        times_incorrect=0
    )
    db.session.add(progress)
    db.session.commit()

    # First quiz - correct
    quiz1 = QuizAttempt(
        user_id=test_user.id,
        phrase_id=test_phrase.id,
        question_type='multiple_choice_target',
        correct_answer='to give',
        was_correct=True
    )
    db.session.add(quiz1)
    db.session.commit()

    result1 = update_after_quiz(quiz1.id)
    assert result1['stage_advanced'] is False  # Not yet advanced
    assert result1['new_stage'] == STAGE_BASIC

    # Refresh
    progress = UserLearningProgress.query.get(progress.id)
    assert progress.times_correct == 1

    # Second quiz - correct (should advance)
    quiz2 = QuizAttempt(
        user_id=test_user.id,
        phrase_id=test_phrase.id,
        question_type='multiple_choice_target',
        correct_answer='to give',
        was_correct=True
    )
    db.session.add(quiz2)
    db.session.commit()

    result2 = update_after_quiz(quiz2.id)
    assert result2['stage_advanced'] is True  # Advanced!
    assert result2['old_stage'] == STAGE_BASIC
    assert result2['new_stage'] == STAGE_INTERMEDIATE

    # Refresh and verify counters were reset
    progress = UserLearningProgress.query.get(progress.id)
    assert progress.stage == STAGE_INTERMEDIATE
    assert progress.times_correct == 0  # Reset
    assert progress.times_incorrect == 0  # Reset
    assert progress.times_reviewed == 2  # Not reset


def test_complete_progression_to_mastered(app_context, test_user, test_phrase):
    """Test complete flow: basic → intermediate → advanced → mastered"""
    # Start at advanced with 2 correct (need 1 more to master)
    progress = UserLearningProgress(
        user_id=test_user.id,
        phrase_id=test_phrase.id,
        stage=STAGE_ADVANCED,
        times_reviewed=10,
        times_correct=2,
        times_incorrect=0
    )
    db.session.add(progress)
    db.session.commit()

    # Third correct answer - should advance to mastered
    quiz = QuizAttempt(
        user_id=test_user.id,
        phrase_id=test_phrase.id,
        question_type='contextual',
        correct_answer='geben',
        was_correct=True
    )
    db.session.add(quiz)
    db.session.commit()

    result = update_after_quiz(quiz.id)

    assert result['stage_advanced'] is True
    assert result['old_stage'] == STAGE_ADVANCED
    assert result['new_stage'] == STAGE_MASTERED
    assert result['next_review_date'] is None  # Mastered = never review

    # Refresh and verify
    progress = UserLearningProgress.query.get(progress.id)
    assert progress.stage == STAGE_MASTERED
    assert progress.next_review_date is None