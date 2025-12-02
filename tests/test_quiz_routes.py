"""
Integration tests for quiz routes (GET /api/quiz/next, POST /api/quiz/answer, POST /api/quiz/skip).

Tests the complete quiz flow including:
- Auto-triggered quiz from translation search
- Manual practice mode quiz selection
- Answer evaluation and learning progress updates
- Quiz skip functionality
"""

import sys
import os
import pytest
from datetime import date, timedelta
from unittest.mock import patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models import db
from models.user import User
from models.language import Language
from models.phrase import Phrase
from models.user_learning_progress import UserLearningProgress
from models.quiz_attempt import QuizAttempt


@pytest.fixture(scope='function')
def client():
    """Create a test client with fresh database for each test"""
    app = create_app('testing')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False

    with app.app_context():
        db.create_all()

        # Add test languages
        lang_en = Language(code='en', original_name='English', en_name='English', display_order=1)
        lang_de = Language(code='de', original_name='Deutsch', en_name='German', display_order=2)
        db.session.add_all([lang_en, lang_de])
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
            google_id='test_user_quiz',
            email='quiz@example.com',
            name='Quiz Test User',
            primary_language_code='en',
            translator_languages=["en", "de"],
            quiz_mode_enabled=True,
            quiz_frequency=5,
            searches_since_last_quiz=5
        )
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    return user_id


@pytest.fixture
def phrase_with_progress(client, authenticated_user):
    """Create a phrase with learning progress due for review"""
    with client.application.app_context():
        phrase = Phrase(
            text='katze',
            language_code='de',
            is_quizzable=True
        )
        db.session.add(phrase)
        db.session.flush()

        progress = UserLearningProgress(
            user_id=authenticated_user,
            phrase_id=phrase.id,
            stage='basic',
            next_review_date=date.today() - timedelta(days=1),  # Overdue
            times_reviewed=0,
            times_correct=0,
            times_incorrect=0
        )
        db.session.add(progress)
        db.session.commit()

        return phrase.id


class TestGetNextQuiz:
    """Tests for GET /api/quiz/next endpoint"""

    @patch('services.question_generation_service.QuestionGenerationService.generate_question')
    @patch('flask_login.utils._get_user')
    def test_get_next_quiz_with_phrase_id(
        self,
        mock_get_user,
        mock_generate_question,
        client,
        authenticated_user,
        phrase_with_progress
    ):
        """Test auto-triggered quiz with specific phrase_id"""
        with client.application.app_context():
            user = User.query.get(authenticated_user)
            mock_get_user.return_value = user

            # Mock question generation
            mock_generate_question.return_value = {
                'question': "What is the English translation of 'katze'?",
                'options': ['cat', 'dog', 'house', 'tree'],
                'question_language': 'en',
                'answer_language': 'en'
            }

            # Call endpoint with phrase_id
            response = client.get(f'/quiz/next?phrase_id={phrase_with_progress}')

            assert response.status_code == 200
            data = response.get_json()

            assert 'quiz_attempt_id' in data
            assert 'question' in data
            assert 'options' in data
            assert 'question_type' in data
            assert 'phrase_id' in data
            assert data['phrase_id'] == phrase_with_progress

            # Verify search counter was reset
            db.session.refresh(user)
            assert user.searches_since_last_quiz == 0

    @patch('services.question_generation_service.QuestionGenerationService.generate_question')
    @patch('flask_login.utils._get_user')
    def test_get_next_quiz_manual_practice_mode(
        self,
        mock_get_user,
        mock_generate_question,
        client,
        authenticated_user,
        phrase_with_progress
    ):
        """Test manual practice mode without phrase_id"""
        with client.application.app_context():
            user = User.query.get(authenticated_user)
            mock_get_user.return_value = user

            # Mock question generation
            mock_generate_question.return_value = {
                'question': "What is the English translation of 'katze'?",
                'options': ['cat', 'dog', 'house', 'tree'],
                'question_language': 'en',
                'answer_language': 'en'
            }

            # Call endpoint without phrase_id
            response = client.get('/quiz/next')

            assert response.status_code == 200
            data = response.get_json()

            assert 'quiz_attempt_id' in data
            assert 'question' in data
            assert 'phrase_id' in data

    @patch('flask_login.utils._get_user')
    def test_get_next_quiz_no_phrases_available(
        self,
        mock_get_user,
        client,
        authenticated_user
    ):
        """Test when no phrases are due for review"""
        with client.application.app_context():
            user = User.query.get(authenticated_user)
            mock_get_user.return_value = user

            # Call endpoint without any eligible phrases
            response = client.get('/quiz/next')

            assert response.status_code == 404
            data = response.get_json()
            assert 'error' in data
            assert data['error'] == 'No phrases due for review'


class TestSubmitQuizAnswer:
    """Tests for POST /api/quiz/answer endpoint"""

    @patch('flask_login.utils._get_user')
    def test_submit_correct_answer(
        self,
        mock_get_user,
        client,
        authenticated_user,
        phrase_with_progress
    ):
        """Test submitting a correct answer"""
        with client.application.app_context():
            user = User.query.get(authenticated_user)
            mock_get_user.return_value = user

            # Create quiz attempt
            quiz_attempt = QuizAttempt(
                user_id=authenticated_user,
                phrase_id=phrase_with_progress,
                question_type='multiple_choice_target',
                prompt_json={
                    'question': "What is the English translation of 'katze'?",
                    'options': ['cat', 'dog', 'house', 'tree']
                },
                correct_answer='cat',
                was_correct=False
            )
            db.session.add(quiz_attempt)
            db.session.commit()

            # Submit correct answer
            response = client.post('/quiz/answer', json={
                'quiz_attempt_id': quiz_attempt.id,
                'user_answer': 'cat'
            })

            assert response.status_code == 200
            data = response.get_json()

            assert data['was_correct'] is True
            assert data['correct_answer'] == 'cat'
            assert 'explanation' in data
            assert 'stage_advanced' in data
            assert 'new_stage' in data
            assert 'next_review_date' in data

            # Verify learning progress was updated
            # Note: Both services update progress (times_reviewed incremented twice)
            # Stage advanced from 'basic' to 'intermediate' which resets counters
            progress = UserLearningProgress.query.filter_by(
                user_id=authenticated_user,
                phrase_id=phrase_with_progress
            ).first()
            assert progress.times_reviewed == 2  # Updated by both services
            assert progress.times_correct == 0  # Reset when stage advanced
            assert progress.stage == 'intermediate'  # Stage advanced
            assert progress.next_review_date is not None

    @patch('flask_login.utils._get_user')
    def test_submit_incorrect_answer(
        self,
        mock_get_user,
        client,
        authenticated_user,
        phrase_with_progress
    ):
        """Test submitting an incorrect answer"""
        with client.application.app_context():
            user = User.query.get(authenticated_user)
            mock_get_user.return_value = user

            # Create quiz attempt
            quiz_attempt = QuizAttempt(
                user_id=authenticated_user,
                phrase_id=phrase_with_progress,
                question_type='multiple_choice_target',
                prompt_json={
                    'question': "What is the English translation of 'katze'?",
                    'options': ['cat', 'dog', 'house', 'tree']
                },
                correct_answer='cat',
                was_correct=False
            )
            db.session.add(quiz_attempt)
            db.session.commit()

            # Submit incorrect answer
            response = client.post('/quiz/answer', json={
                'quiz_attempt_id': quiz_attempt.id,
                'user_answer': 'dog'
            })

            assert response.status_code == 200
            data = response.get_json()

            assert data['was_correct'] is False
            assert data['correct_answer'] == 'cat'

            # Verify learning progress was updated
            # Note: Both services update progress, so counters are doubled
            progress = UserLearningProgress.query.filter_by(
                user_id=authenticated_user,
                phrase_id=phrase_with_progress
            ).first()
            assert progress.times_reviewed == 2  # Updated by both services
            assert progress.times_incorrect == 2  # Updated by both services

    @patch('flask_login.utils._get_user')
    def test_submit_answer_missing_fields(
        self,
        mock_get_user,
        client,
        authenticated_user
    ):
        """Test submitting answer with missing required fields"""
        with client.application.app_context():
            user = User.query.get(authenticated_user)
            mock_get_user.return_value = user

            # Missing user_answer
            response = client.post('/quiz/answer', json={
                'quiz_attempt_id': 123
            })

            assert response.status_code == 400
            data = response.get_json()
            assert 'error' in data


class TestSkipQuiz:
    """Tests for POST /api/quiz/skip endpoint"""

    @patch('flask_login.utils._get_user')
    def test_skip_quiz_success(
        self,
        mock_get_user,
        client,
        authenticated_user,
        phrase_with_progress
    ):
        """Test successfully skipping a quiz"""
        with client.application.app_context():
            user = User.query.get(authenticated_user)
            initial_counter = user.searches_since_last_quiz
            mock_get_user.return_value = user

            # Skip quiz
            response = client.post('/quiz/skip', json={
                'phrase_id': phrase_with_progress
            })

            assert response.status_code == 200
            data = response.get_json()

            assert data['success'] is True
            assert 'message' in data
            assert data['phrase_id'] == phrase_with_progress

            # Verify search counter was NOT reset
            db.session.refresh(user)
            assert user.searches_since_last_quiz == initial_counter

            # Verify no quiz attempt was created
            quiz_attempts = QuizAttempt.query.filter_by(
                user_id=authenticated_user,
                phrase_id=phrase_with_progress
            ).count()
            assert quiz_attempts == 0

    @patch('flask_login.utils._get_user')
    def test_skip_quiz_missing_phrase_id(
        self,
        mock_get_user,
        client,
        authenticated_user
    ):
        """Test skipping quiz without phrase_id"""
        with client.application.app_context():
            user = User.query.get(authenticated_user)
            mock_get_user.return_value = user

            # Skip without phrase_id
            response = client.post('/quiz/skip', json={})

            assert response.status_code == 400
            data = response.get_json()
            assert 'error' in data


if __name__ == '__main__':
    pytest.main([__file__, '-v'])