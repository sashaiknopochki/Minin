"""
Unit tests for AnswerEvaluationService.

Tests the answer evaluation logic including:
- Multiple choice answer evaluation (exact, case-insensitive, whitespace)
- Multiple valid answers support
- Learning progress updates (times_reviewed, times_correct, times_incorrect)
- Edge case handling (missing data, invalid JSON, unsupported question types)
- Database operations (persistence, rollback)
"""

import sys
import os
import pytest
import json
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models import db
from models.user import User
from models.language import Language
from models.phrase import Phrase
from models.user_learning_progress import UserLearningProgress
from models.quiz_attempt import QuizAttempt
from services.answer_evaluation_service import AnswerEvaluationService


@pytest.fixture(scope='function')
def app_context():
    """Create a fresh app context and database for each test"""
    app = create_app('development')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'  # In-memory database
    app.config['TESTING'] = True

    with app.app_context():
        db.create_all()

        # Add test languages if they don't exist
        languages_data = [
            ('en', 'English', 'English', 1),
            ('de', 'Deutsch', 'German', 2),
            ('ru', 'Русский', 'Russian', 3),
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
        google_id='test_eval_user',
        email='eval@example.com',
        name='Evaluation Test User',
        primary_language_code='en',
        translator_languages=["en", "de", "ru"]
    )
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def test_phrase(app_context):
    """Create a test phrase"""
    phrase = Phrase(
        text='katze',
        language_code='de',
        type='word'
    )
    db.session.add(phrase)
    db.session.commit()
    return phrase


@pytest.fixture
def test_learning_progress(app_context, test_user, test_phrase):
    """Create a test learning progress record"""
    progress = UserLearningProgress(
        user_id=test_user.id,
        phrase_id=test_phrase.id,
        stage='basic',
        times_reviewed=0,
        times_correct=0,
        times_incorrect=0
    )
    db.session.add(progress)
    db.session.commit()
    return progress


@pytest.fixture
def quiz_attempt_single_answer(app_context, test_user, test_phrase):
    """Create a quiz attempt with single correct answer"""
    quiz_attempt = QuizAttempt(
        user_id=test_user.id,
        phrase_id=test_phrase.id,
        question_type='multiple_choice_target',
        prompt_json={
            "question": "What is the English translation of 'katze'?",
            "options": ["cat", "dog", "house", "tree"],
            "question_language": "en",
            "answer_language": "en"
        },
        correct_answer="cat",  # Single answer
        was_correct=False  # Placeholder
    )
    db.session.add(quiz_attempt)
    db.session.commit()
    return quiz_attempt


@pytest.fixture
def quiz_attempt_multiple_answers(app_context, test_user, test_phrase):
    """Create a quiz attempt with multiple valid answers (JSON array)"""
    quiz_attempt = QuizAttempt(
        user_id=test_user.id,
        phrase_id=test_phrase.id,
        question_type='multiple_choice_target',
        prompt_json={
            "question": "What is the English translation of 'katze'?",
            "options": ["cat", "feline", "dog", "house"],
            "question_language": "en",
            "answer_language": "en"
        },
        correct_answer=json.dumps(["cat", "feline"]),  # Multiple valid answers
        was_correct=False  # Placeholder
    )
    db.session.add(quiz_attempt)
    db.session.commit()
    return quiz_attempt


# ============================================================================
# HAPPY PATH TESTS
# ============================================================================

def test_evaluate_correct_answer_exact_match(app_context, quiz_attempt_single_answer, test_learning_progress):
    """Test evaluation with correct answer (exact match)"""
    result = AnswerEvaluationService.evaluate_answer(
        quiz_attempt_id=quiz_attempt_single_answer.id,
        user_answer="cat"
    )

    assert result['was_correct'] is True
    assert result['correct_answer'] == "cat"
    assert "Correct!" in result['explanation']

    # Verify quiz_attempt was updated
    updated_attempt = QuizAttempt.query.get(quiz_attempt_single_answer.id)
    assert updated_attempt.user_answer == "cat"
    assert updated_attempt.was_correct is True


def test_evaluate_correct_answer_case_insensitive(app_context, quiz_attempt_single_answer, test_learning_progress):
    """Test evaluation with correct answer (case insensitive)"""
    result = AnswerEvaluationService.evaluate_answer(
        quiz_attempt_id=quiz_attempt_single_answer.id,
        user_answer="CAT"  # Uppercase
    )

    assert result['was_correct'] is True
    assert result['correct_answer'] == "cat"

    # Verify quiz_attempt was updated
    updated_attempt = QuizAttempt.query.get(quiz_attempt_single_answer.id)
    assert updated_attempt.user_answer == "CAT"
    assert updated_attempt.was_correct is True


def test_evaluate_correct_answer_whitespace_stripped(app_context, quiz_attempt_single_answer, test_learning_progress):
    """Test evaluation with correct answer (whitespace stripped)"""
    result = AnswerEvaluationService.evaluate_answer(
        quiz_attempt_id=quiz_attempt_single_answer.id,
        user_answer="  cat  "  # Extra whitespace
    )

    assert result['was_correct'] is True
    assert result['correct_answer'] == "cat"

    # Verify quiz_attempt was updated with stripped answer
    updated_attempt = QuizAttempt.query.get(quiz_attempt_single_answer.id)
    assert updated_attempt.user_answer == "cat"  # Should be stripped
    assert updated_attempt.was_correct is True


def test_evaluate_correct_answer_multiple_valid(app_context, quiz_attempt_multiple_answers, test_learning_progress):
    """Test evaluation with multiple valid answers (user provides one of them)"""
    # Test with first valid answer
    result = AnswerEvaluationService.evaluate_answer(
        quiz_attempt_id=quiz_attempt_multiple_answers.id,
        user_answer="cat"
    )

    assert result['was_correct'] is True
    assert "cat" in result['correct_answer']
    assert "feline" in result['correct_answer']
    assert " / " in result['correct_answer']  # Should show both answers


def test_evaluate_correct_answer_second_valid_answer(app_context, quiz_attempt_multiple_answers, test_learning_progress):
    """Test evaluation with multiple valid answers (user provides second valid answer)"""
    # Test with second valid answer
    result = AnswerEvaluationService.evaluate_answer(
        quiz_attempt_id=quiz_attempt_multiple_answers.id,
        user_answer="feline"
    )

    assert result['was_correct'] is True
    assert "cat" in result['correct_answer']
    assert "feline" in result['correct_answer']


def test_evaluate_incorrect_answer(app_context, quiz_attempt_single_answer, test_learning_progress):
    """Test evaluation with incorrect answer"""
    result = AnswerEvaluationService.evaluate_answer(
        quiz_attempt_id=quiz_attempt_single_answer.id,
        user_answer="dog"  # Wrong answer
    )

    assert result['was_correct'] is False
    assert result['correct_answer'] == "cat"
    assert "Incorrect" in result['explanation']
    assert "cat" in result['explanation']

    # Verify quiz_attempt was updated
    updated_attempt = QuizAttempt.query.get(quiz_attempt_single_answer.id)
    assert updated_attempt.user_answer == "dog"
    assert updated_attempt.was_correct is False


# ============================================================================
# LEARNING PROGRESS UPDATE TESTS
# ============================================================================

def test_learning_progress_times_reviewed_incremented(app_context, quiz_attempt_single_answer, test_learning_progress):
    """Test that times_reviewed is incremented after evaluation"""
    initial_reviewed = test_learning_progress.times_reviewed

    AnswerEvaluationService.evaluate_answer(
        quiz_attempt_id=quiz_attempt_single_answer.id,
        user_answer="cat"
    )

    # Refresh from database
    updated_progress = UserLearningProgress.query.get(test_learning_progress.id)
    assert updated_progress.times_reviewed == initial_reviewed + 1


def test_learning_progress_times_correct_incremented(app_context, quiz_attempt_single_answer, test_learning_progress):
    """Test that times_correct is incremented when answer is correct"""
    initial_correct = test_learning_progress.times_correct

    AnswerEvaluationService.evaluate_answer(
        quiz_attempt_id=quiz_attempt_single_answer.id,
        user_answer="cat"  # Correct
    )

    # Refresh from database
    updated_progress = UserLearningProgress.query.get(test_learning_progress.id)
    assert updated_progress.times_correct == initial_correct + 1
    assert updated_progress.times_incorrect == 0  # Should not change


def test_learning_progress_times_incorrect_incremented(app_context, quiz_attempt_single_answer, test_learning_progress):
    """Test that times_incorrect is incremented when answer is incorrect"""
    initial_incorrect = test_learning_progress.times_incorrect

    AnswerEvaluationService.evaluate_answer(
        quiz_attempt_id=quiz_attempt_single_answer.id,
        user_answer="dog"  # Incorrect
    )

    # Refresh from database
    updated_progress = UserLearningProgress.query.get(test_learning_progress.id)
    assert updated_progress.times_incorrect == initial_incorrect + 1
    assert updated_progress.times_correct == 0  # Should not change


def test_learning_progress_last_reviewed_updated(app_context, quiz_attempt_single_answer, test_learning_progress):
    """Test that last_reviewed_at is updated"""
    assert test_learning_progress.last_reviewed_at is None

    AnswerEvaluationService.evaluate_answer(
        quiz_attempt_id=quiz_attempt_single_answer.id,
        user_answer="cat"
    )

    # Refresh from database
    updated_progress = UserLearningProgress.query.get(test_learning_progress.id)
    assert updated_progress.last_reviewed_at is not None
    assert isinstance(updated_progress.last_reviewed_at, datetime)


# ============================================================================
# EDGE CASE TESTS
# ============================================================================

def test_evaluate_missing_quiz_attempt(app_context):
    """Test evaluation with non-existent quiz_attempt_id"""
    with pytest.raises(ValueError, match="Quiz attempt not found"):
        AnswerEvaluationService.evaluate_answer(
            quiz_attempt_id=99999,  # Doesn't exist
            user_answer="cat"
        )


def test_evaluate_empty_user_answer(app_context, quiz_attempt_single_answer):
    """Test evaluation with empty user_answer"""
    with pytest.raises(ValueError, match="User answer cannot be empty"):
        AnswerEvaluationService.evaluate_answer(
            quiz_attempt_id=quiz_attempt_single_answer.id,
            user_answer=""
        )


def test_evaluate_whitespace_only_user_answer(app_context, quiz_attempt_single_answer):
    """Test evaluation with whitespace-only user_answer"""
    with pytest.raises(ValueError, match="User answer cannot be empty"):
        AnswerEvaluationService.evaluate_answer(
            quiz_attempt_id=quiz_attempt_single_answer.id,
            user_answer="   "
        )


def test_evaluate_unsupported_question_type(app_context, test_user, test_phrase, test_learning_progress):
    """Test evaluation with unsupported question type"""
    # Create quiz attempt with unsupported type
    quiz_attempt = QuizAttempt(
        user_id=test_user.id,
        phrase_id=test_phrase.id,
        question_type='text_input_target',  # Not supported in MVP
        prompt_json={"question": "Translate: katze"},
        correct_answer="cat",
        was_correct=False
    )
    db.session.add(quiz_attempt)
    db.session.commit()

    with pytest.raises(ValueError, match="not supported in MVP"):
        AnswerEvaluationService.evaluate_answer(
            quiz_attempt_id=quiz_attempt.id,
            user_answer="cat"
        )


def test_evaluate_missing_correct_answer_field(app_context, test_user, test_phrase, test_learning_progress):
    """Test evaluation when correct_answer field is missing"""
    # Create quiz attempt without correct_answer
    quiz_attempt = QuizAttempt(
        user_id=test_user.id,
        phrase_id=test_phrase.id,
        question_type='multiple_choice_target',
        prompt_json={"question": "Translate: katze"},
        correct_answer=None,  # Missing
        was_correct=False
    )
    db.session.add(quiz_attempt)
    db.session.commit()

    with pytest.raises(ValueError, match="missing correct_answer field"):
        AnswerEvaluationService.evaluate_answer(
            quiz_attempt_id=quiz_attempt.id,
            user_answer="cat"
        )


def test_evaluate_without_learning_progress(app_context, quiz_attempt_single_answer):
    """Test evaluation continues even without learning progress record"""
    # Don't create learning_progress fixture - test without it
    result = AnswerEvaluationService.evaluate_answer(
        quiz_attempt_id=quiz_attempt_single_answer.id,
        user_answer="cat"
    )

    # Should still evaluate successfully
    assert result['was_correct'] is True

    # Verify quiz_attempt was still updated
    updated_attempt = QuizAttempt.query.get(quiz_attempt_single_answer.id)
    assert updated_attempt.was_correct is True


# ============================================================================
# HELPER METHOD TESTS
# ============================================================================

def test_extract_valid_answers_single_string(app_context):
    """Test _extract_valid_answers with single string answer"""
    answers = AnswerEvaluationService._extract_valid_answers("cat")
    assert answers == ["cat"]


def test_extract_valid_answers_json_array(app_context):
    """Test _extract_valid_answers with JSON array"""
    answers = AnswerEvaluationService._extract_valid_answers('["cat", "feline"]')
    assert answers == ["cat", "feline"]


def test_extract_valid_answers_case_normalization(app_context):
    """Test _extract_valid_answers normalizes to lowercase"""
    answers = AnswerEvaluationService._extract_valid_answers("CAT")
    assert answers == ["cat"]

    answers = AnswerEvaluationService._extract_valid_answers('["CAT", "FELINE"]')
    assert answers == ["cat", "feline"]


def test_extract_valid_answers_whitespace_stripped(app_context):
    """Test _extract_valid_answers strips whitespace"""
    answers = AnswerEvaluationService._extract_valid_answers("  cat  ")
    assert answers == ["cat"]

    answers = AnswerEvaluationService._extract_valid_answers('["  cat  ", "  feline  "]')
    assert answers == ["cat", "feline"]


def test_extract_valid_answers_invalid_json_fallback(app_context):
    """Test _extract_valid_answers falls back to string when JSON is invalid"""
    # Invalid JSON should be treated as single string
    answers = AnswerEvaluationService._extract_valid_answers('["cat", "feline"')  # Missing closing bracket
    assert len(answers) == 1
    # Will treat the whole string as answer


def test_extract_valid_answers_empty_raises_error(app_context):
    """Test _extract_valid_answers raises error for empty input"""
    with pytest.raises(ValueError, match="cannot be empty"):
        AnswerEvaluationService._extract_valid_answers("")

    with pytest.raises(ValueError, match="cannot be empty"):
        AnswerEvaluationService._extract_valid_answers("   ")


def test_evaluate_multiple_choice_exact_match(app_context):
    """Test _evaluate_multiple_choice with exact match"""
    result = AnswerEvaluationService._evaluate_multiple_choice("cat", ["cat", "feline"])
    assert result is True


def test_evaluate_multiple_choice_case_insensitive(app_context):
    """Test _evaluate_multiple_choice is case insensitive"""
    result = AnswerEvaluationService._evaluate_multiple_choice("CAT", ["cat", "feline"])
    assert result is True


def test_evaluate_multiple_choice_whitespace_tolerant(app_context):
    """Test _evaluate_multiple_choice strips whitespace"""
    result = AnswerEvaluationService._evaluate_multiple_choice("  cat  ", ["cat", "feline"])
    assert result is True


def test_evaluate_multiple_choice_no_match(app_context):
    """Test _evaluate_multiple_choice returns False when no match"""
    result = AnswerEvaluationService._evaluate_multiple_choice("dog", ["cat", "feline"])
    assert result is False


def test_evaluate_multiple_choice_partial_match_not_accepted(app_context):
    """Test _evaluate_multiple_choice doesn't accept partial matches"""
    result = AnswerEvaluationService._evaluate_multiple_choice("ca", ["cat", "feline"])
    assert result is False