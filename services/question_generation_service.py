"""
Question Generation Service - Generates quiz questions using LLM.

This service creates quiz questions based on the question type and user's learning data.
MVP implementation supports only multiple choice questions.
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from openai import OpenAI

from models import db
from models.quiz_attempt import QuizAttempt
from models.phrase import Phrase
from models.phrase_translation import PhraseTranslation
from models.user import User
from models.user_searches import UserSearch
from models.language import Language

# Configure logging
logger = logging.getLogger(__name__)

# Model constants
GPT_4_1_MINI = "gpt-4.1-mini"
DEFAULT_MODEL = GPT_4_1_MINI


class QuestionGenerationService:
    """Service to generate quiz questions using LLM"""

    @staticmethod
    def generate_question(quiz_attempt: QuizAttempt) -> Dict[str, Any]:
        """
        Generate quiz question via LLM.

        This method creates a complete quiz question with options and correct answer
        using an LLM. It retrieves all necessary data (phrase, translations, context)
        and calls the LLM to generate an appropriate question based on the question type.

        Updates quiz_attempt with:
        - prompt_json: Complete question data (question, options, languages)
        - correct_answer: What the system considers correct

        Args:
            quiz_attempt (QuizAttempt): The quiz attempt to generate a question for

        Returns:
            dict: Question data to show to user with keys:
                - question: str - The question text
                - options: list - List of answer options (for multiple choice)
                - question_language: str - Language code for the question
                - answer_language: str - Language code for the answer

        Raises:
            ValueError: If quiz_attempt is invalid or required data is missing
            RuntimeError: If LLM API call fails

        Examples:
            >>> quiz_attempt = QuizAttemptService.create_quiz_attempt(user_id=1, phrase_id=42)
            >>> question_data = QuestionGenerationService.generate_question(quiz_attempt)
            >>> print(question_data['question'])
            "What is the English translation of 'Katze'?"
            >>> print(question_data['options'])
            ["cat", "dog", "house", "tree"]

        Implementation Notes:
            - Currently supports only multiple_choice_target and multiple_choice_source
            - Uses db.session.commit() to persist changes
            - Extracts translations from phrase_translations table
            - Retrieves context sentences from user_searches if available
        """
        if not quiz_attempt:
            raise ValueError("quiz_attempt cannot be None")

        # Get phrase and user
        phrase = Phrase.query.get(quiz_attempt.phrase_id)
        user = User.query.get(quiz_attempt.user_id)

        if not phrase:
            raise ValueError(f"Phrase not found: {quiz_attempt.phrase_id}")
        if not user:
            raise ValueError(f"User not found: {quiz_attempt.user_id}")

        # Get all translations for this phrase
        translations = PhraseTranslation.query.filter_by(
            phrase_id=phrase.id
        ).all()

        if not translations:
            raise ValueError(f"No translations found for phrase: {phrase.id}")

        # Get context sentence if available (most recent search by this user)
        context = UserSearch.query.filter_by(
            user_id=user.id,
            phrase_id=phrase.id
        ).order_by(UserSearch.searched_at.desc()).first()

        context_sentence = context.context_sentence if context else None

        # Build translation data for LLM
        translations_data = {}
        for trans in translations:
            lang = Language.query.get(trans.target_language_code)
            if lang:
                translations_data[lang.en_name] = trans.translations_json

        # Generate question based on type
        question_data = QuestionGenerationService._call_llm_for_question(
            question_type=quiz_attempt.question_type,
            phrase_text=phrase.text,
            phrase_language=phrase.language_code,
            translations=translations_data,
            native_language=user.primary_language_code,
            context_sentence=context_sentence
        )

        # Update quiz attempt
        quiz_attempt.prompt_json = question_data['prompt']
        quiz_attempt.correct_answer = question_data['correct_answer']

        db.session.commit()

        return question_data['prompt']

    @staticmethod
    def _call_llm_for_question(
        question_type: str,
        phrase_text: str,
        phrase_language: str,
        translations: Dict[str, Any],
        native_language: str,
        context_sentence: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Call LLM to generate question.

        This method constructs an appropriate prompt based on the question type
        and calls the OpenAI API to generate the quiz question.

        Args:
            question_type: Type of question (multiple_choice_target, multiple_choice_source, etc.)
            phrase_text: The word/phrase to quiz on
            phrase_language: Language code of the phrase
            translations: Dict of translations by language name
            native_language: User's native language code
            context_sentence: Optional context sentence where phrase was seen

        Returns:
            dict: {
                'prompt': {
                    'question': str,
                    'options': list (for multiple choice) or None,
                    'question_language': str,
                    'answer_language': str
                },
                'correct_answer': str or list (if multiple valid answers)
            }

        Raises:
            ValueError: If question_type is not supported
            RuntimeError: If API call fails
        """
        # Load environment variables
        load_dotenv()

        # Get API key
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("OPENAI_API_KEY not found in environment variables")
            raise RuntimeError("OPENAI_API_KEY not configured")

        # Initialize OpenAI client
        client = OpenAI(api_key=api_key)

        # Generate question based on type
        if question_type == 'multiple_choice_target':
            return QuestionGenerationService._generate_multiple_choice_target(
                client=client,
                phrase_text=phrase_text,
                phrase_language=phrase_language,
                translations=translations,
                native_language=native_language
            )

        elif question_type == 'multiple_choice_source':
            return QuestionGenerationService._generate_multiple_choice_source(
                client=client,
                phrase_text=phrase_text,
                phrase_language=phrase_language,
                translations=translations,
                native_language=native_language
            )

        else:
            # For MVP, only multiple choice is supported
            raise ValueError(
                f"Question type '{question_type}' not supported in MVP. "
                f"Supported types: multiple_choice_target, multiple_choice_source"
            )

    @staticmethod
    def _generate_multiple_choice_target(
        client: OpenAI,
        phrase_text: str,
        phrase_language: str,
        translations: Dict[str, Any],
        native_language: str
    ) -> Dict[str, Any]:
        """
        Generate multiple choice question: "What is the [native language] translation of '[phrase]'?"

        User sees phrase in source language and selects translation in their native language.
        """
        # Get native language name for the prompt
        native_lang = Language.query.get(native_language)
        native_lang_name = native_lang.en_name if native_lang else "English"

        # Get source language name
        source_lang = Language.query.get(phrase_language)
        source_lang_name = source_lang.en_name if source_lang else phrase_language

        prompt = f"""Generate a multiple choice question to test translation recognition.

Source phrase: "{phrase_text}"
Source language: {source_lang_name}
Target language (native): {native_lang_name}

Available translations: {json.dumps(translations, ensure_ascii=False)}

Requirements:
1. Question: "What is the {native_lang_name} translation of '{phrase_text}'?"
2. Generate 4 options: 1 correct + 3 distractors
3. If the word has multiple meanings, list ALL valid translations in correct_answer as an array
4. Distractors should be plausible words in {native_lang_name} but clearly wrong for this phrase
5. Distractors should be at similar difficulty level (don't use obvious unrelated words)
6. Return ONLY valid JSON, no other text

Return format:
{{
  "question": "What is the {native_lang_name} translation of '{phrase_text}'?",
  "options": ["correct_translation", "distractor1", "distractor2", "distractor3"],
  "correct_answer": "correct_translation",
  "question_language": "{native_language}",
  "answer_language": "{native_language}"
}}

If multiple meanings exist, use this format:
{{
  "question": "What is the {native_lang_name} translation of '{phrase_text}'?",
  "options": ["cat", "feline", "dog", "house"],
  "correct_answer": ["cat", "feline"],
  "question_language": "{native_language}",
  "answer_language": "{native_language}"
}}
"""

        try:
            # Call OpenAI API
            response = client.chat.completions.create(
                model=DEFAULT_MODEL,
                messages=[
                    {"role": "system", "content": "You are a language learning quiz generator. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )

            # Parse JSON response
            result = json.loads(response.choices[0].message.content)

            logger.info(f"Generated multiple_choice_target question for '{phrase_text}'")

            return {
                'prompt': {
                    'question': result['question'],
                    'options': result['options'],
                    'question_language': result['question_language'],
                    'answer_language': result['answer_language']
                },
                'correct_answer': result['correct_answer']
            }

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.error(f"Response content: {response.choices[0].message.content}")
            raise RuntimeError(f"LLM returned invalid JSON: {e}")

        except Exception as e:
            logger.error(f"Error calling OpenAI API: {e}")
            raise RuntimeError(f"Failed to generate question: {e}")

    @staticmethod
    def _generate_multiple_choice_source(
        client: OpenAI,
        phrase_text: str,
        phrase_language: str,
        translations: Dict[str, Any],
        native_language: str
    ) -> Dict[str, Any]:
        """
        Generate multiple choice question: "What is the [source language] word for '[translation]'?"

        User sees translation in native language and selects phrase in source language.
        This is the reverse of multiple_choice_target (harder).
        """
        # Get native language name
        native_lang = Language.query.get(native_language)
        native_lang_name = native_lang.en_name if native_lang else "English"

        # Get source language name
        source_lang = Language.query.get(phrase_language)
        source_lang_name = source_lang.en_name if source_lang else phrase_language

        # Extract a primary translation to use in the question
        # (We'll use the first translation from the native language)
        primary_translation = "the word"
        if native_lang_name in translations:
            trans_data = translations[native_lang_name]
            if isinstance(trans_data, dict) and isinstance(trans_data.get(native_lang_name), list):
                if len(trans_data[native_lang_name]) > 0 and len(trans_data[native_lang_name][0]) > 0:
                    primary_translation = trans_data[native_lang_name][0][0]
            elif isinstance(trans_data, list) and len(trans_data) > 0:
                if isinstance(trans_data[0], list) and len(trans_data[0]) > 0:
                    primary_translation = trans_data[0][0]

        prompt = f"""Generate a multiple choice question to test reverse translation (native language to source language).

Source phrase (correct answer): "{phrase_text}"
Source language: {source_lang_name}
Native language: {native_lang_name}

Available translations: {json.dumps(translations, ensure_ascii=False)}

Requirements:
1. Question: "What is the {source_lang_name} word for '{primary_translation}'?"
2. Generate 4 options in {source_lang_name}: 1 correct ('{phrase_text}') + 3 distractors
3. Distractors should be plausible {source_lang_name} words but clearly wrong for this meaning
4. Distractors should be at similar difficulty level
5. Return ONLY valid JSON, no other text

Return format:
{{
  "question": "What is the {source_lang_name} word for '{primary_translation}'?",
  "options": ["{phrase_text}", "distractor1", "distractor2", "distractor3"],
  "correct_answer": "{phrase_text}",
  "question_language": "{native_language}",
  "answer_language": "{phrase_language}"
}}
"""

        try:
            # Call OpenAI API
            response = client.chat.completions.create(
                model=DEFAULT_MODEL,
                messages=[
                    {"role": "system", "content": "You are a language learning quiz generator. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )

            # Parse JSON response
            result = json.loads(response.choices[0].message.content)

            logger.info(f"Generated multiple_choice_source question for '{phrase_text}'")

            return {
                'prompt': {
                    'question': result['question'],
                    'options': result['options'],
                    'question_language': result['question_language'],
                    'answer_language': result['answer_language']
                },
                'correct_answer': result['correct_answer']
            }

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.error(f"Response content: {response.choices[0].message.content}")
            raise RuntimeError(f"LLM returned invalid JSON: {e}")

        except Exception as e:
            logger.error(f"Error calling OpenAI API: {e}")
            raise RuntimeError(f"Failed to generate question: {e}")