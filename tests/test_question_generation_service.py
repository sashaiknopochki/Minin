"""
Unit tests for QuestionGenerationService.

Tests the question generation logic including:
- Multiple choice target question generation
- Multiple choice source question generation
- Error handling for missing data
- LLM response parsing
- Database updates

Note: These tests mock the OpenAI API to avoid actual API calls and costs.
"""

import sys
import os
import pytest
import json
from datetime import date
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models import db
from models.user import User
from models.language import Language
from models.phrase import Phrase
from models.phrase_translation import PhraseTranslation
from models.user_learning_progress import UserLearningProgress
from models.quiz_attempt import QuizAttempt
from models.user_searches import UserSearch
from models.session import Session
from services.question_generation_service import QuestionGenerationService
from uuid import uuid4


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
        google_id='test_qgen_user',
        email='qgen@example.com',
        name='Question Gen Test User',
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
        text='katze',
        language_code='de',
        type='word'
    )
    db.session.add(phrase)
    db.session.commit()
    return phrase


@pytest.fixture
def test_translation(app_context, test_phrase):
    """Create a test translation"""
    translation = PhraseTranslation(
        phrase_id=test_phrase.id,
        target_language_code='en',
        translations_json={
            "English": [
                ["cat", "noun, feminine", "a small domesticated carnivorous mammal"],
                ["feline", "noun", "relating to cats"]
            ]
        },
        model_name='gpt-4.1-mini',
        model_version='2024-11-01'
    )
    db.session.add(translation)
    db.session.commit()
    return translation


@pytest.fixture
def test_quiz_attempt(app_context, test_user, test_phrase):
    """Create a test quiz attempt"""
    # Create learning progress first
    progress = UserLearningProgress(
        user_id=test_user.id,
        phrase_id=test_phrase.id,
        stage='basic',
        next_review_date=date.today()
    )
    db.session.add(progress)
    db.session.flush()

    # Create quiz attempt
    quiz_attempt = QuizAttempt(
        user_id=test_user.id,
        phrase_id=test_phrase.id,
        question_type='multiple_choice_target',
        was_correct=False
    )
    db.session.add(quiz_attempt)
    db.session.commit()
    return quiz_attempt


@pytest.fixture
def mock_openai_response_target():
    """Mock OpenAI API response for multiple_choice_target"""
    return {
        "question": "What is the English translation of 'katze'?",
        "options": ["cat", "dog", "house", "tree"],
        "correct_answer": "cat",
        "question_language": "en",
        "answer_language": "en"
    }


@pytest.fixture
def mock_openai_response_source():
    """Mock OpenAI API response for multiple_choice_source"""
    return {
        "question": "What is the German word for 'cat'?",
        "options": ["katze", "hund", "haus", "baum"],
        "correct_answer": "katze",
        "question_language": "en",
        "answer_language": "de"
    }


class TestGenerateQuestion:
    """Test generate_question method"""

    @patch('services.question_generation_service.OpenAI')
    @patch.dict(os.environ, {'OPENAI_API_KEY': 'test_key'})
    def test_generates_question_successfully(
        self,
        mock_openai_class,
        app_context,
        test_user,
        test_phrase,
        test_translation,
        test_quiz_attempt,
        mock_openai_response_target
    ):
        """Should generate question and update quiz_attempt"""
        # Setup mock
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps(mock_openai_response_target)
        mock_client.chat.completions.create.return_value = mock_response

        # Generate question
        result = QuestionGenerationService.generate_question(test_quiz_attempt)

        # Verify result
        assert result is not None
        assert result['question'] == "What is the English translation of 'katze'?"
        assert result['options'] == ["cat", "dog", "house", "tree"]
        assert result['question_language'] == "en"
        assert result['answer_language'] == "en"

        # Verify quiz_attempt was updated
        db.session.refresh(test_quiz_attempt)
        assert test_quiz_attempt.prompt_json is not None
        assert test_quiz_attempt.prompt_json['question'] == result['question']
        assert test_quiz_attempt.correct_answer == "cat"

    @patch('services.question_generation_service.OpenAI')
    @patch.dict(os.environ, {'OPENAI_API_KEY': 'test_key'})
    def test_generates_source_question(
        self,
        mock_openai_class,
        app_context,
        test_user,
        test_phrase,
        test_translation,
        mock_openai_response_source
    ):
        """Should generate multiple_choice_source question"""
        # Create quiz attempt with source question type
        quiz_attempt = QuizAttempt(
            user_id=test_user.id,
            phrase_id=test_phrase.id,
            question_type='multiple_choice_source',
            was_correct=False
        )
        db.session.add(quiz_attempt)
        db.session.commit()

        # Setup mock
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps(mock_openai_response_source)
        mock_client.chat.completions.create.return_value = mock_response

        # Generate question
        result = QuestionGenerationService.generate_question(quiz_attempt)

        # Verify result
        assert result['question'] == "What is the German word for 'cat'?"
        assert "katze" in result['options']
        assert quiz_attempt.correct_answer == "katze"

    def test_raises_error_for_none_quiz_attempt(self, app_context):
        """Should raise ValueError for None quiz_attempt"""
        with pytest.raises(ValueError) as exc_info:
            QuestionGenerationService.generate_question(None)

        assert "quiz_attempt cannot be None" in str(exc_info.value)

    def test_raises_error_for_missing_phrase(self, app_context, test_user):
        """Should raise ValueError when phrase not found"""
        quiz_attempt = QuizAttempt(
            user_id=test_user.id,
            phrase_id=99999,  # Non-existent
            question_type='multiple_choice_target',
            was_correct=False
        )
        db.session.add(quiz_attempt)
        db.session.commit()

        with pytest.raises(ValueError) as exc_info:
            QuestionGenerationService.generate_question(quiz_attempt)

        assert "Phrase not found" in str(exc_info.value)

    def test_raises_error_for_missing_translations(self, app_context, test_user, test_phrase):
        """Should raise ValueError when no translations exist"""
        quiz_attempt = QuizAttempt(
            user_id=test_user.id,
            phrase_id=test_phrase.id,
            question_type='multiple_choice_target',
            was_correct=False
        )
        db.session.add(quiz_attempt)
        db.session.commit()

        with pytest.raises(ValueError) as exc_info:
            QuestionGenerationService.generate_question(quiz_attempt)

        assert "No translations found" in str(exc_info.value)

    @patch('services.question_generation_service.OpenAI')
    @patch.dict(os.environ, {'OPENAI_API_KEY': 'test_key'})
    def test_includes_context_sentence_when_available(
        self,
        mock_openai_class,
        app_context,
        test_user,
        test_phrase,
        test_translation,
        test_quiz_attempt,
        mock_openai_response_target
    ):
        """Should include context sentence in question generation when available"""
        # Create session
        session = Session(session_id=str(uuid4()), user_id=test_user.id)
        db.session.add(session)
        db.session.flush()

        # Create user search with context
        user_search = UserSearch(
            user_id=test_user.id,
            phrase_id=test_phrase.id,
            session_id=session.session_id,
            context_sentence="Die Katze schläft auf dem Sofa",
            llm_translations_json={"English": "cat"}
        )
        db.session.add(user_search)
        db.session.commit()

        # Setup mock
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps(mock_openai_response_target)
        mock_client.chat.completions.create.return_value = mock_response

        # Generate question
        QuestionGenerationService.generate_question(test_quiz_attempt)

        # Verify OpenAI was called (context sentence would be in the call)
        assert mock_client.chat.completions.create.called


class TestCallLLMForQuestion:
    """Test _call_llm_for_question method"""

    @patch('services.question_generation_service.OpenAI')
    @patch.dict(os.environ, {'OPENAI_API_KEY': 'test_key'})
    def test_multiple_choice_target_generation(
        self,
        mock_openai_class,
        app_context,
        mock_openai_response_target
    ):
        """Should generate multiple_choice_target question"""
        # Setup mock
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps(mock_openai_response_target)
        mock_client.chat.completions.create.return_value = mock_response

        # Call method
        result = QuestionGenerationService._call_llm_for_question(
            question_type='multiple_choice_target',
            phrase_text='katze',
            phrase_language='de',
            translations={"English": [["cat", "noun", "a feline animal"]]},
            native_language='en'
        )

        # Verify structure
        assert 'prompt' in result
        assert 'correct_answer' in result
        assert result['prompt']['question'] is not None
        assert result['prompt']['options'] is not None
        assert len(result['prompt']['options']) == 4

    @patch('services.question_generation_service.OpenAI')
    @patch.dict(os.environ, {'OPENAI_API_KEY': 'test_key'})
    def test_multiple_choice_source_generation(
        self,
        mock_openai_class,
        app_context,
        mock_openai_response_source
    ):
        """Should generate multiple_choice_source question"""
        # Setup mock
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps(mock_openai_response_source)
        mock_client.chat.completions.create.return_value = mock_response

        # Call method
        result = QuestionGenerationService._call_llm_for_question(
            question_type='multiple_choice_source',
            phrase_text='katze',
            phrase_language='de',
            translations={"English": [["cat", "noun", "a feline animal"]]},
            native_language='en'
        )

        # Verify structure
        assert result['prompt']['question'] is not None
        assert result['prompt']['options'] is not None
        assert result['correct_answer'] == 'katze'

    @patch.dict(os.environ, {'OPENAI_API_KEY': 'test_key'})
    def test_raises_error_for_unsupported_question_type(self, app_context):
        """Should raise ValueError for unsupported question types"""
        with pytest.raises(ValueError) as exc_info:
            QuestionGenerationService._call_llm_for_question(
                question_type='text_input_target',  # Not supported in MVP
                phrase_text='katze',
                phrase_language='de',
                translations={"English": [["cat", "noun", "a feline animal"]]},
                native_language='en'
            )

        assert "not supported in MVP" in str(exc_info.value)

    @patch('services.question_generation_service.load_dotenv')
    @patch.dict(os.environ, {'OPENAI_API_KEY': ''})
    def test_raises_error_when_api_key_missing(self, mock_load_dotenv, app_context):
        """Should raise RuntimeError when OPENAI_API_KEY is not set"""
        # Ensure load_dotenv doesn't actually load anything
        mock_load_dotenv.return_value = None

        with pytest.raises(RuntimeError) as exc_info:
            QuestionGenerationService._call_llm_for_question(
                question_type='multiple_choice_target',
                phrase_text='katze',
                phrase_language='de',
                translations={"English": [["cat", "noun", "a feline animal"]]},
                native_language='en'
            )

        assert "OPENAI_API_KEY not configured" in str(exc_info.value)

    @patch('services.question_generation_service.OpenAI')
    @patch.dict(os.environ, {'OPENAI_API_KEY': 'test_key'})
    def test_handles_invalid_json_response(self, mock_openai_class, app_context):
        """Should raise RuntimeError when LLM returns invalid JSON"""
        # Setup mock to return invalid JSON
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "This is not valid JSON"
        mock_client.chat.completions.create.return_value = mock_response

        with pytest.raises(RuntimeError) as exc_info:
            QuestionGenerationService._call_llm_for_question(
                question_type='multiple_choice_target',
                phrase_text='katze',
                phrase_language='de',
                translations={"English": [["cat", "noun", "a feline animal"]]},
                native_language='en'
            )

        assert "LLM returned invalid JSON" in str(exc_info.value)

    @patch('services.question_generation_service.OpenAI')
    @patch.dict(os.environ, {'OPENAI_API_KEY': 'test_key'})
    def test_handles_api_error(self, mock_openai_class, app_context):
        """Should raise RuntimeError when API call fails"""
        # Setup mock to raise exception
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception("API Error")

        with pytest.raises(RuntimeError) as exc_info:
            QuestionGenerationService._call_llm_for_question(
                question_type='multiple_choice_target',
                phrase_text='katze',
                phrase_language='de',
                translations={"English": [["cat", "noun", "a feline animal"]]},
                native_language='en'
            )

        assert "Failed to generate question" in str(exc_info.value)


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    @patch('services.question_generation_service.OpenAI')
    @patch.dict(os.environ, {'OPENAI_API_KEY': 'test_key'})
    def test_handles_multiple_valid_answers(
        self,
        mock_openai_class,
        app_context,
        test_user,
        test_phrase,
        test_translation
    ):
        """Should handle phrases with multiple valid translations"""
        # Create quiz attempt
        quiz_attempt = QuizAttempt(
            user_id=test_user.id,
            phrase_id=test_phrase.id,
            question_type='multiple_choice_target',
            was_correct=False
        )
        db.session.add(quiz_attempt)
        db.session.commit()

        # Mock response with multiple correct answers
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        mock_response_data = {
            "question": "What is the English translation of 'katze'?",
            "options": ["cat", "feline", "dog", "house"],
            "correct_answer": ["cat", "feline"],  # Multiple correct answers
            "question_language": "en",
            "answer_language": "en"
        }

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps(mock_response_data)
        mock_client.chat.completions.create.return_value = mock_response

        # Generate question
        result = QuestionGenerationService.generate_question(quiz_attempt)

        # Verify multiple answers are stored as JSON string
        db.session.refresh(quiz_attempt)
        assert isinstance(quiz_attempt.correct_answer, str)
        # Parse the JSON string to verify contents
        correct_answers = json.loads(quiz_attempt.correct_answer)
        assert isinstance(correct_answers, list)
        assert "cat" in correct_answers
        assert "feline" in correct_answers


if __name__ == '__main__':
    pytest.main([__file__, '-v'])