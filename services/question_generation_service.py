"""
Question Generation Service - Generates quiz questions using LLM.

This service creates quiz questions based on the question type and user's learning data.
MVP implementation supports only multiple choice questions.
"""

import os
import json
import logging
import time
import random
from typing import Dict, Any, Optional, List
from decimal import Decimal
from dotenv import load_dotenv
from services.llm_provider_factory import get_llm_client, LLMProviderFactory
from services.llm_models.question_models import (
    MultipleChoiceQuestion,
    TextInputQuestion,
    ContextualQuestion,
    DefinitionQuestion,
    SynonymQuestion
)
from services.cost_service import CostCalculationService
from services.session_cost_aggregator import add_quiz_cost
from services.session_service import get_or_create_session

from models import db
from models.quiz_attempt import QuizAttempt
from models.phrase import Phrase
from models.phrase_translation import PhraseTranslation
from models.user import User
from models.user_searches import UserSearch
from models.language import Language

# Configure logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Get default model based on configured provider
DEFAULT_MODEL = LLMProviderFactory.get_default_model()

# Retry configuration
MAX_RETRIES = 3
INITIAL_RETRY_DELAY = 1.0  # seconds
MAX_RETRY_DELAY = 10.0  # seconds


def _strip_markdown_code_fences(content: str) -> str:
    """
    Strip markdown code fences from LLM response.

    Different LLM providers format their JSON responses differently:
    - OpenAI typically returns raw JSON
    - Mistral often wraps JSON in ```json ... ``` markdown code fences

    This function normalizes the response by removing code fences if present.

    Args:
        content: The raw LLM response content

    Returns:
        Cleaned content with code fences removed

    Examples:
        >>> _strip_markdown_code_fences('```json\\n{"key": "value"}\\n```')
        '{"key": "value"}'
        >>> _strip_markdown_code_fences('{"key": "value"}')
        '{"key": "value"}'
    """
    content = content.strip()

    # Check for markdown code fences (```json or ``` or ```JSON)
    if content.startswith('```'):
        # Remove opening fence
        lines = content.split('\n')
        # First line is the opening fence (```json or ```)
        lines = lines[1:]

        # Remove closing fence if present
        if lines and lines[-1].strip() == '```':
            lines = lines[:-1]

        content = '\n'.join(lines).strip()

    return content


class QuestionGenerationService:
    """Service to generate quiz questions using LLM"""

    @staticmethod
    def generate_question(quiz_attempt: QuizAttempt) -> Dict[str, Any]:
        """
        Generate quiz question via LLM with fallback support.

        This method creates a complete quiz question with options and correct answer
        using an LLM. It retrieves all necessary data (phrase, translations, context)
        and calls the LLM to generate an appropriate question based on the question type.

        If LLM generation fails after retries, falls back to hardcoded question generation.

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
            RuntimeError: If both LLM and fallback generation fail

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
            - Falls back to simple questions if LLM fails
        """
        # Validate quiz_attempt
        if not quiz_attempt:
            logger.error("generate_question called with None quiz_attempt")
            raise ValueError("quiz_attempt cannot be None")

        if not hasattr(quiz_attempt, 'id') or not quiz_attempt.id:
            logger.error("quiz_attempt missing id")
            raise ValueError("quiz_attempt must have a valid id")

        try:
            # Get phrase and user
            phrase = Phrase.query.get(quiz_attempt.phrase_id)
            user = User.query.get(quiz_attempt.user_id)

            if not phrase:
                logger.error(f"Phrase not found: {quiz_attempt.phrase_id}")
                raise ValueError(f"Phrase not found: {quiz_attempt.phrase_id}")
            if not user:
                logger.error(f"User not found: {quiz_attempt.user_id}")
                raise ValueError(f"User not found: {quiz_attempt.user_id}")

            if not phrase.text:
                logger.error(f"Phrase {phrase.id} has no text")
                raise ValueError(f"Phrase {phrase.id} has no text")

            # Get all translations for this phrase
            translations = PhraseTranslation.query.filter_by(
                phrase_id=phrase.id
            ).all()

            if not translations:
                logger.error(f"No translations found for phrase: {phrase.id}")
                raise ValueError(
                    f"No translations found for phrase: {phrase.id}. "
                    f"Cannot generate quiz without translation data."
                )

            # Get context sentence if available (most recent search by this user)
            context = UserSearch.query.filter_by(
                user_id=user.id,
                phrase_id=phrase.id
            ).order_by(UserSearch.searched_at.desc()).first()

            context_sentence = context.context_sentence if context else None

            # Build translation data for LLM
            translations_data = {}
            for trans in translations:
                try:
                    lang = Language.query.get(trans.target_language_code)
                    if lang and trans.translations_json:
                        translations_data[lang.en_name] = trans.translations_json
                except Exception as e:
                    logger.warning(
                        f"Failed to process translation {trans.id}: {str(e)}"
                    )
                    continue

            if not translations_data:
                logger.error(f"No valid translation data for phrase: {phrase.id}")
                raise ValueError(
                    f"No valid translation data for phrase: {phrase.id}"
                )

            # Try to generate question via LLM
            try:
                question_data = QuestionGenerationService._call_llm_for_question(
                    question_type=quiz_attempt.question_type,
                    phrase_text=phrase.text,
                    phrase_language=phrase.language_code,
                    translations=translations_data,
                    native_language=user.primary_language_code,
                    context_sentence=context_sentence
                )
            except (RuntimeError, Exception) as e:
                # LLM failed, use fallback
                logger.warning(
                    f"LLM generation failed for quiz_attempt {quiz_attempt.id}: {str(e)}. "
                    f"Using fallback question generation."
                )
                question_data = QuestionGenerationService._generate_fallback_question(
                    question_type=quiz_attempt.question_type,
                    phrase_text=phrase.text,
                    phrase_language=phrase.language_code,
                    translations=translations_data,
                    native_language=user.primary_language_code
                )

            # Update quiz attempt with question and answer
            quiz_attempt.prompt_json = question_data['prompt']

            # Handle correct_answer: convert list to JSON string if needed
            correct_answer = question_data['correct_answer']
            if isinstance(correct_answer, list):
                quiz_attempt.correct_answer = json.dumps(correct_answer)
            else:
                quiz_attempt.correct_answer = correct_answer

            # Store cost data if available (from Phase 4)
            if 'generation_cost' in question_data:
                gen_cost = question_data['generation_cost']
                quiz_attempt.question_gen_prompt_tokens = gen_cost['tokens']['prompt_tokens']
                quiz_attempt.question_gen_completion_tokens = gen_cost['tokens']['completion_tokens']
                quiz_attempt.question_gen_total_tokens = gen_cost['tokens']['total_tokens']
                quiz_attempt.question_gen_cost_usd = float(gen_cost['cost_usd'])
                quiz_attempt.question_gen_model = gen_cost['model']

                # Aggregate to session
                try:
                    session = get_or_create_session(user.id)
                    add_quiz_cost(session.session_id, gen_cost['cost_usd'])
                    logger.debug(f"Added quiz generation cost ${gen_cost['cost_usd']} to session {session.session_id}")
                except Exception as e:
                    logger.warning(f"Failed to aggregate quiz cost to session: {e}")

            db.session.commit()

            logger.info(
                f"Generated question for quiz_attempt {quiz_attempt.id}: "
                f"phrase='{phrase.text}', type={quiz_attempt.question_type}"
            )

            return question_data['prompt']

        except ValueError:
            # Re-raise ValueError for proper error propagation
            raise
        except Exception as e:
            logger.error(
                f"Failed to generate question for quiz_attempt {quiz_attempt.id}: {str(e)}",
                exc_info=True
            )
            db.session.rollback()
            raise RuntimeError(f"Failed to generate question: {str(e)}")

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
        # Initialize LLM provider
        try:
            provider = get_llm_client()
        except ValueError as e:
            logger.error(f"Failed to initialize LLM provider: {str(e)}")
            raise RuntimeError(f"LLM provider configuration error: {str(e)}")

        # Generate question based on type
        if question_type == 'multiple_choice_target':
            return QuestionGenerationService._generate_multiple_choice_target(
                provider=provider,
                phrase_text=phrase_text,
                phrase_language=phrase_language,
                translations=translations,
                native_language=native_language
            )

        elif question_type == 'multiple_choice_source':
            return QuestionGenerationService._generate_multiple_choice_source(
                provider=provider,
                phrase_text=phrase_text,
                phrase_language=phrase_language,
                translations=translations,
                native_language=native_language
            )

        elif question_type == 'text_input_target':
            return QuestionGenerationService._generate_text_input_target(
                provider=provider,
                phrase_text=phrase_text,
                phrase_language=phrase_language,
                translations=translations,
                native_language=native_language
            )

        elif question_type == 'text_input_source':
            return QuestionGenerationService._generate_text_input_source(
                provider=provider,
                phrase_text=phrase_text,
                phrase_language=phrase_language,
                translations=translations,
                native_language=native_language
            )

        elif question_type == 'contextual':
            return QuestionGenerationService._generate_contextual(
                provider=provider,
                phrase_text=phrase_text,
                phrase_language=phrase_language,
                translations=translations,
                native_language=native_language,
                context_sentence=context_sentence
            )

        elif question_type == 'definition':
            return QuestionGenerationService._generate_definition(
                provider=provider,
                phrase_text=phrase_text,
                phrase_language=phrase_language,
                translations=translations,
                native_language=native_language
            )

        elif question_type == 'synonym':
            return QuestionGenerationService._generate_synonym(
                provider=provider,
                phrase_text=phrase_text,
                phrase_language=phrase_language,
                translations=translations,
                native_language=native_language
            )

        else:
            # Unsupported question type
            raise ValueError(
                f"Question type '{question_type}' not supported. "
                f"Supported types: multiple_choice_target, multiple_choice_source, "
                f"text_input_target, text_input_source, contextual, definition, synonym"
            )

    @staticmethod
    def _shuffle_options(options: List[str], correct_answer: Any) -> List[str]:
        """
        Shuffle multiple choice options to randomize correct answer position.

        Args:
            options: List of answer options
            correct_answer: The correct answer (string or list of strings)

        Returns:
            List of shuffled options
        """
        # Create a copy to avoid modifying the original list
        shuffled = options.copy()
        random.shuffle(shuffled)
        return shuffled

    @staticmethod
    def _generate_multiple_choice_target(
        provider,
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

        user_message = f"""Generate a multiple choice question to test translation recognition.

Source phrase: "{phrase_text}"
Source language: {source_lang_name}
Target language (native): {native_lang_name}

Available translations: {json.dumps(translations, ensure_ascii=False)}

Requirements:
1. Question: "What is the {native_lang_name} translation of \"{phrase_text}\"?"
2. IMPORTANT: Use double quotes around the phrase, not single quotes
3. IMPORTANT: End the question with a question mark (for multiple choice questions)
4. Generate 4 options: 1 correct + 3 distractors
5. If the word has multiple meanings, list ALL valid translations in correct_answer as an array
6. Distractors should be plausible words in {native_lang_name} but clearly wrong for this phrase
7. Distractors should be at similar difficulty level (don't use obvious unrelated words)
8. The order of options in your response doesn't matter - they will be randomized

Return format:
{{
  "question": "What is the {native_lang_name} translation of \"{phrase_text}\"?",
  "options": ["correct_translation", "distractor1", "distractor2", "distractor3"],
  "correct_answer": "correct_translation",
  "question_language": "{native_language}",
  "answer_language": "{native_language}"
}}

If multiple meanings exist, use this format:
{{
  "question": "What is the {native_lang_name} translation of \"{phrase_text}\"?",
  "options": ["cat", "feline", "dog", "house"],
  "correct_answer": ["cat", "feline"],
  "question_language": "{native_language}",
  "answer_language": "{native_language}"
}}
"""

        messages = [
            {"role": "system", "content": "You are a language learning quiz generator. Generate high-quality multiple choice questions."},
            {"role": "user", "content": user_message}
        ]

        try:
            # Use structured outputs with Pydantic
            response = provider.create_structured_completion(
                messages=messages,
                response_model=MultipleChoiceQuestion,
                model=DEFAULT_MODEL,
                temperature=0.7,
                max_tokens=500
            )

            question_obj = response["parsed_object"]

            # Calculate cost
            cost_usd = CostCalculationService.calculate_cost(
                provider=provider.get_provider_name(),
                model=response["model"],
                prompt_tokens=response["usage"]["prompt_tokens"],
                completion_tokens=response["usage"]["completion_tokens"],
                cached_tokens=response["usage"]["cached_tokens"]
            )

            # Shuffle the options to randomize correct answer position
            shuffled_options = QuestionGenerationService._shuffle_options(
                question_obj.options,
                question_obj.correct_answer
            )

            logger.info(f"Generated multiple_choice_target question for '{phrase_text}' (cost: ${cost_usd})")

            return {
                'prompt': {
                    'question': question_obj.question,
                    'options': shuffled_options,
                    'question_language': question_obj.question_language,
                    'answer_language': question_obj.answer_language
                },
                'correct_answer': question_obj.correct_answer,
                'generation_cost': {
                    'tokens': response["usage"],
                    'cost_usd': cost_usd,
                    'model': response["model"]
                }
            }

        except Exception as e:
            logger.error(f"Error generating multiple_choice_target question: {e}")
            raise RuntimeError(f"Failed to generate question: {e}")

    @staticmethod
    def _generate_multiple_choice_source(
        provider,
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
        primary_translation = "the word"
        if native_lang_name in translations:
            trans_data = translations[native_lang_name]
            if isinstance(trans_data, dict) and isinstance(trans_data.get(native_lang_name), list):
                if len(trans_data[native_lang_name]) > 0 and len(trans_data[native_lang_name][0]) > 0:
                    primary_translation = trans_data[native_lang_name][0][0]
            elif isinstance(trans_data, list) and len(trans_data) > 0:
                if isinstance(trans_data[0], list) and len(trans_data[0]) > 0:
                    primary_translation = trans_data[0][0]

        user_message = f"""Generate a multiple choice question to test reverse translation (native language to source language).

Source phrase (correct answer): "{phrase_text}"
Source language: {source_lang_name}
Native language: {native_lang_name}

Available translations: {json.dumps(translations, ensure_ascii=False)}

Requirements:
1. Question: "What is the {source_lang_name} word for \"{primary_translation}\"?"
2. IMPORTANT: Use double quotes around the phrase, not single quotes
3. IMPORTANT: End the question with a question mark (for multiple choice questions)
4. Generate 4 options in {source_lang_name}: 1 correct ('{phrase_text}') + 3 distractors
5. Distractors should be plausible {source_lang_name} words but clearly wrong for this meaning
6. Distractors should be at similar difficulty level
7. The order of options in your response doesn't matter - they will be randomized

Return format:
{{
  "question": "What is the {source_lang_name} word for \"{primary_translation}\"?",
  "options": ["{phrase_text}", "distractor1", "distractor2", "distractor3"],
  "correct_answer": "{phrase_text}",
  "question_language": "{native_language}",
  "answer_language": "{phrase_language}"
}}
"""

        messages = [
            {"role": "system", "content": "You are a language learning quiz generator. Generate high-quality multiple choice questions."},
            {"role": "user", "content": user_message}
        ]

        try:
            # Use structured outputs with Pydantic
            response = provider.create_structured_completion(
                messages=messages,
                response_model=MultipleChoiceQuestion,
                model=DEFAULT_MODEL,
                temperature=0.7,
                max_tokens=500
            )

            question_obj = response["parsed_object"]

            # Calculate cost
            cost_usd = CostCalculationService.calculate_cost(
                provider=provider.get_provider_name(),
                model=response["model"],
                prompt_tokens=response["usage"]["prompt_tokens"],
                completion_tokens=response["usage"]["completion_tokens"],
                cached_tokens=response["usage"]["cached_tokens"]
            )

            # Shuffle the options to randomize correct answer position
            shuffled_options = QuestionGenerationService._shuffle_options(
                question_obj.options,
                question_obj.correct_answer
            )

            logger.info(f"Generated multiple_choice_source question for '{phrase_text}' (cost: ${cost_usd})")

            return {
                'prompt': {
                    'question': question_obj.question,
                    'options': shuffled_options,
                    'question_language': question_obj.question_language,
                    'answer_language': question_obj.answer_language
                },
                'correct_answer': question_obj.correct_answer,
                'generation_cost': {
                    'tokens': response["usage"],
                    'cost_usd': cost_usd,
                    'model': response["model"]
                }
            }

        except Exception as e:
            logger.error(f"Error generating multiple_choice_source question: {e}")
            raise RuntimeError(f"Failed to generate question: {e}")

    @staticmethod
    def _generate_text_input_target(
        provider,
        phrase_text: str,
        phrase_language: str,
        translations: Dict[str, Any],
        native_language: str
    ) -> Dict[str, Any]:
        """
        Generate text input question: "Type the [native language] translation of '[phrase]'"

        User sees phrase in source language and types translation in their native language.

        Args:
            provider client instance
            phrase_text: The word/phrase to quiz on (e.g., "Katze")
            phrase_language: Language code of the phrase (e.g., "de")
            translations: Dict of translations by language name
            native_language: User's native language code (e.g., "en")

        Returns:
            dict: {
                'prompt': {
                    'question': str,
                    'options': None,  # No options for text input
                    'question_language': str,
                    'answer_language': str
                },
                'correct_answer': str or list
            }
        """
        # Get native language name for the prompt
        native_lang = Language.query.get(native_language)
        native_lang_name = native_lang.en_name if native_lang else "English"

        # Get source language name
        source_lang = Language.query.get(phrase_language)
        source_lang_name = source_lang.en_name if source_lang else phrase_language

        user_message = f"""Generate a text input question to test translation recall (production).

Source phrase: "{phrase_text}"
Source language: {source_lang_name}
Target language (native): {native_lang_name}

Available translations: {json.dumps(translations, ensure_ascii=False)}

Requirements:
1. Question: "Type the {native_lang_name} translation of \"{phrase_text}\"."
2. IMPORTANT: Use double quotes around the phrase, not single quotes
3. IMPORTANT: End the question with a period
4. No multiple choice options - user types the answer
5. If the word has multiple valid meanings, list ALL in correct_answer as an array

Return format:
{{
  "question": "Type the {native_lang_name} translation of \"{phrase_text}\".",
  "options": null,
  "correct_answer": "cat",
  "question_language": "{native_language}",
  "answer_language": "{native_language}"
}}

If multiple meanings exist, use this format:
{{
  "question": "Type the {native_lang_name} translation of \"{phrase_text}\".",
  "options": null,
  "correct_answer": ["cat", "feline"],
  "question_language": "{native_language}",
  "answer_language": "{native_language}"
}}
"""

        messages = [
            {"role": "system", "content": "You are a language learning quiz generator. Generate high-quality text input questions."},
            {"role": "user", "content": user_message}
        ]

        try:
            # Use structured outputs with Pydantic
            response = provider.create_structured_completion(
                messages=messages,
                response_model=TextInputQuestion,
                model=DEFAULT_MODEL,
                temperature=0.7,
                max_tokens=500
            )

            question_obj = response["parsed_object"]

            # Calculate cost
            cost_usd = CostCalculationService.calculate_cost(
                provider=provider.get_provider_name(),
                model=response["model"],
                prompt_tokens=response["usage"]["prompt_tokens"],
                completion_tokens=response["usage"]["completion_tokens"],
                cached_tokens=response["usage"]["cached_tokens"]
            )

            logger.info(f"Generated text_input_target question for '{phrase_text}' (cost: ${cost_usd})")

            return {
                'prompt': {
                    'question': question_obj.question,
                    'options': None,
                    'question_language': question_obj.question_language,
                    'answer_language': question_obj.answer_language
                },
                'correct_answer': question_obj.correct_answer,
                'generation_cost': {
                    'tokens': response["usage"],
                    'cost_usd': cost_usd,
                    'model': response["model"]
                }
            }

        except Exception as e:
            logger.error(f"Error generating text_input_target question: {e}")
            raise RuntimeError(f"Failed to generate question: {e}")



    @staticmethod
    def _generate_text_input_source(
        provider,
        phrase_text: str,
        phrase_language: str,
        translations: Dict[str, Any],
        native_language: str
    ) -> Dict[str, Any]:
        """
        Generate text input question: "Type the [source language] translation of '[native phrase]'"

        User sees phrase in native language and types translation in source language.
        This is more challenging as user must produce the foreign language word.

        Args:
            provider client instance
            phrase_text: The word/phrase in source language (e.g., "Katze")
            phrase_language: Language code of the phrase (e.g., "de")
            translations: Dict of translations by language name
            native_language: User's native language code (e.g., "en")

        Returns:
            dict: {
                'prompt': {
                    'question': str,
                    'options': None,
                    'question_language': str,
                    'answer_language': str
                },
                'correct_answer': str
            }
        """
        # Get native language name
        native_lang = Language.query.get(native_language)
        native_lang_name = native_lang.en_name if native_lang else "English"

        # Get source language name
        source_lang = Language.query.get(phrase_language)
        source_lang_name = source_lang.en_name if source_lang else phrase_language

        # Extract a native translation to show in question
        # CRITICAL: Must use NATIVE language translation, not any other learning language
        native_translation = None
        
        # Look specifically for the user's native language translation
        if native_lang_name in translations:
            trans_data = translations[native_lang_name]
            
            # Handle different data structures
            if isinstance(trans_data, dict):
                # translations_json format: {"Russian": [[...], [...]], ...}
                for key in trans_data:
                    if isinstance(trans_data[key], list) and trans_data[key]:
                        if isinstance(trans_data[key][0], list) and trans_data[key][0]:
                            native_translation = trans_data[key][0][0]
                            break
                        elif isinstance(trans_data[key][0], str):
                            native_translation = trans_data[key][0]
                            break
            elif isinstance(trans_data, list) and len(trans_data) > 0:
                # Simple list format
                if isinstance(trans_data[0], list) and len(trans_data[0]) > 0:
                    native_translation = trans_data[0][0]
                elif isinstance(trans_data[0], str):
                    native_translation = trans_data[0]

        if not native_translation:
            logger.warning(f"No {native_lang_name} translation found for {phrase_text}, using phrase itself")
            native_translation = phrase_text

        user_message = f"""Generate a reverse text input question to test production in the target language.

Native word: "{native_translation}"
Native language: {native_lang_name}
Target language (to type): {source_lang_name}
Correct answer in {source_lang_name}: "{phrase_text}"

Available translations: {json.dumps(translations, ensure_ascii=False)}

Requirements:
1. Question: "Type the {source_lang_name} word for \"{native_translation}\"."
2. IMPORTANT: Use double quotes around the phrase, not single quotes
3. IMPORTANT: End the question with a period
4. No multiple choice options - user types the answer
5. The correct answer is the original phrase: "{phrase_text}"

Return format:
{{
  "question": "Type the {source_lang_name} word for \"{native_translation}\".",
  "options": null,
  "correct_answer": "{phrase_text}",
  "question_language": "{native_language}",
  "answer_language": "{phrase_language}"
}}
"""

        messages = [
            {"role": "system", "content": "You are a language learning quiz generator. Generate high-quality text input questions."},
            {"role": "user", "content": user_message}
        ]

        try:
            # Use structured outputs with Pydantic
            response = provider.create_structured_completion(
                messages=messages,
                response_model=TextInputQuestion,
                model=DEFAULT_MODEL,
                temperature=0.7,
                max_tokens=500
            )

            question_obj = response["parsed_object"]

            # Calculate cost
            cost_usd = CostCalculationService.calculate_cost(
                provider=provider.get_provider_name(),
                model=response["model"],
                prompt_tokens=response["usage"]["prompt_tokens"],
                completion_tokens=response["usage"]["completion_tokens"],
                cached_tokens=response["usage"]["cached_tokens"]
            )

            logger.info(f"Generated text_input_source question for '{phrase_text}' (cost: ${cost_usd})")

            return {
                'prompt': {
                    'question': question_obj.question,
                    'options': None,
                    'question_language': question_obj.question_language,
                    'answer_language': question_obj.answer_language
                },
                'correct_answer': question_obj.correct_answer,
                'generation_cost': {
                    'tokens': response["usage"],
                    'cost_usd': cost_usd,
                    'model': response["model"]
                }
            }

        except Exception as e:
            logger.error(f"Error generating text_input_source question: {e}")
            raise RuntimeError(f"Failed to generate question: {e}")



    @staticmethod
    def _generate_contextual(
        provider,
        phrase_text: str,
        phrase_language: str,
        translations: Dict[str, Any],
        native_language: str,
        context_sentence: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate contextual question: "In the sentence '{context}', what does '{phrase}' mean?"

        This tests the user's ability to understand a word in context, which is crucial
        for disambiguating words with multiple meanings.

        Args:
            provider client instance
            phrase_text: The word/phrase to quiz on (e.g., "Bank")
            phrase_language: Language code of the phrase (e.g., "de")
            translations: Dict of translations by language name
            native_language: User's native language code (e.g., "en")
            context_sentence: Sentence where the word was seen (e.g., "Ich sitze auf der Bank")

        Returns:
            dict: {
                'prompt': {
                    'question': str,
                    'options': None,
                    'question_language': str,
                    'answer_language': str,
                    'context_sentence': str
                },
                'correct_answer': str
            }
        """
        # Get native language name
        native_lang = Language.query.get(native_language)
        native_lang_name = native_lang.en_name if native_lang else "English"

        # Get source language name
        source_lang = Language.query.get(phrase_language)
        source_lang_name = source_lang.en_name if source_lang else phrase_language

        # If context sentence is missing, instruction to generate one
        context_instruction = ""
        if context_sentence:
            context_instruction = f'Context sentence: "{context_sentence}"'
        else:
            context_instruction = f"""Context sentence: NONE PROVIDED.
Action: GENERATE a simple, clear sentence in {source_lang_name} using the word "{phrase_text}".
Use this generated sentence as the context for the question."""

        user_message = f"""Generate a contextual translation question.

{context_instruction}
Word to test: "{phrase_text}"
Source language: {source_lang_name}
Target language (native): {native_lang_name}

Available translations: {json.dumps(translations, ensure_ascii=False)}

Requirements:
1. Ask the ENTIRE question in the SOURCE language ({source_lang_name}). Do NOT use English.
2. User answers in their NATIVE language ({native_lang_name})
3. Question format (TRANSLATE to {source_lang_name}): "In the sentence '[context_sentence]', what does '{phrase_text}' mean?"
4. The correct answer must match the context of the sentence
5. If word has multiple meanings, only the contextually appropriate one is correct
6. Include the full context sentence (provided or generated) in the question
7. If you generated a sentence, ensure it clearly demonstrates the word's meaning

Return format:
{{
  "question": "[Question in {source_lang_name} asking for meaning of '{phrase_text}' in context]",
  "correct_answer": "contextually appropriate translation",
  "contextual_meaning": "brief explanation of why this meaning fits the context",
  "question_language": "{phrase_language}",
  "answer_language": "{native_language}"
}}
"""

        messages = [
            {"role": "system", "content": "You are a language learning quiz generator. Generate high-quality contextual questions."},
            {"role": "user", "content": user_message}
        ]

        try:
            # Use structured outputs with Pydantic
            response = provider.create_structured_completion(
                messages=messages,
                response_model=ContextualQuestion,
                model=DEFAULT_MODEL,
                temperature=0.7,
                max_tokens=500
            )

            question_obj = response["parsed_object"]

            # Calculate cost
            cost_usd = CostCalculationService.calculate_cost(
                provider=provider.get_provider_name(),
                model=response["model"],
                prompt_tokens=response["usage"]["prompt_tokens"],
                completion_tokens=response["usage"]["completion_tokens"],
                cached_tokens=response["usage"]["cached_tokens"]
            )

            logger.info(f"Generated contextual question for '{phrase_text}' with context (cost: ${cost_usd})")

            return {
                'prompt': {
                    'question': question_obj.question,
                    'options': None,
                    'question_language': question_obj.question_language,
                    'answer_language': question_obj.answer_language,
                    'context_sentence': context_sentence
                },
                'correct_answer': question_obj.correct_answer,
                'generation_cost': {
                    'tokens': response["usage"],
                    'cost_usd': cost_usd,
                    'model': response["model"]
                }
            }

        except Exception as e:
            logger.error(f"Error generating contextual question: {e}")
            raise RuntimeError(f"Failed to generate question: {e}")

    @staticmethod
    def _generate_definition(
        provider,
        phrase_text: str,
        phrase_language: str,
        translations: Dict[str, Any],
        native_language: str
    ) -> Dict[str, Any]:
        """
        Generate definition question: "Define '{phrase}'" or "What does '{phrase}' mean?"

        CRITICAL: This is different from text_input questions - the user must explain
        the word IN THE SOURCE LANGUAGE, not translate it. This tests deep understanding.

        Args:
            provider client instance
            phrase_text: The word/phrase to quiz on (e.g., "geben")
            phrase_language: Language code of the phrase (e.g., "de")
            translations: Dict of translations by language name
            native_language: User's native language code (for reference)

        Returns:
            dict: {
                'prompt': {
                    'question': str,
                    'options': None,
                    'question_language': str (source language),
                    'answer_language': str (source language)
                },
                'correct_answer': str or list (acceptable definitions in source language)
            }
        """
        # Get source language name
        source_lang = Language.query.get(phrase_language)
        source_lang_name = source_lang.en_name if source_lang else phrase_language

        user_message = f"""Generate a definition question.

Word to test: "{phrase_text}"
Source language: {source_lang_name}

Available translations with definitions: {json.dumps(translations, ensure_ascii=False)}

Requirements:
1. Ask the ENTIRE question in the SOURCE language ({source_lang_name}). Do NOT use English.
2. Question format (TRANSLATE to {source_lang_name}): "Define '{phrase_text}'" or "What does '{phrase_text}' mean?"
3. Extract the definition from translations_json to use as reference answer
4. **CRITICAL**: The correct_answer should be a definition IN THE SOURCE LANGUAGE ({source_lang_name}), NOT a translation
5. This tests deep understanding - user must explain the word in the language they're learning
6. If multiple acceptable definitions exist, provide them as a list
7. No options - text input only

Return format:
{{
  "question": "[Question in {source_lang_name} asking for definition of '{phrase_text}']",
  "correct_answer": "definition in source language" or ["definition 1", "definition 2"],
  "question_language": "{phrase_language}",
  "answer_language": "{phrase_language}"
}}

Example (for German word "geben"):
{{
  "question": "Was bedeutet 'geben'?",
  "correct_answer": ["etwas jemandem übergeben", "jemandem etwas schenken", "zur Verfügung stellen"],
  "question_language": "de",
  "answer_language": "de"
}}
"""

        messages = [
            {"role": "system", "content": "You are a language learning quiz generator. Generate high-quality definition questions."},
            {"role": "user", "content": user_message}
        ]

        try:
            # Use structured outputs with Pydantic
            response = provider.create_structured_completion(
                messages=messages,
                response_model=DefinitionQuestion,
                model=DEFAULT_MODEL,
                temperature=0.7,
                max_tokens=500
            )

            question_obj = response["parsed_object"]

            # Calculate cost
            cost_usd = CostCalculationService.calculate_cost(
                provider=provider.get_provider_name(),
                model=response["model"],
                prompt_tokens=response["usage"]["prompt_tokens"],
                completion_tokens=response["usage"]["completion_tokens"],
                cached_tokens=response["usage"]["cached_tokens"]
            )

            logger.info(f"Generated definition question for '{phrase_text}' (cost: ${cost_usd})")

            return {
                'prompt': {
                    'question': question_obj.question,
                    'options': None,
                    'question_language': question_obj.question_language,
                    'answer_language': question_obj.answer_language
                },
                'correct_answer': question_obj.correct_answer,
                'generation_cost': {
                    'tokens': response["usage"],
                    'cost_usd': cost_usd,
                    'model': response["model"]
                }
            }

        except Exception as e:
            logger.error(f"Error generating definition question: {e}")
            raise RuntimeError(f"Failed to generate question: {e}")

    @staticmethod
    def _generate_synonym(
        provider,
        phrase_text: str,
        phrase_language: str,
        translations: Dict[str, Any],
        native_language: str
    ) -> Dict[str, Any]:
        """
        Generate synonym question: "Provide a synonym for '{phrase}'"

        CRITICAL: User must provide a synonym IN THE SOURCE LANGUAGE, not a translation.
        The use of the word "synonym" makes it clear we want a word in the same language.

        Args:
            provider client instance
            phrase_text: The word/phrase to quiz on (e.g., "schön")
            phrase_language: Language code of the phrase (e.g., "de")
            translations: Dict of translations by language name
            native_language: User's native language code (for reference)

        Returns:
            dict: {
                'prompt': {
                    'question': str,
                    'options': None,
                    'question_language': str (source language),
                    'answer_language': str (source language)
                },
                'correct_answer': list (acceptable synonyms in source language)
            }
        """
        # Get source language name
        source_lang = Language.query.get(phrase_language)
        source_lang_name = source_lang.en_name if source_lang else phrase_language

        user_message = f"""Generate a synonym question.

Word to test: "{phrase_text}"
Source language: {source_lang_name}

Available translations with related words: {json.dumps(translations, ensure_ascii=False)}

Requirements:
1. Ask the ENTIRE question in the SOURCE language ({source_lang_name}). Do NOT use English.
2. Question format (TRANSLATE to {source_lang_name}): "Provide a synonym for '{phrase_text}'"
3. Use the word "synonym" (translated if appropriate) to make it clear we want a word in the SAME language
4. Extract related words/synonyms from translations_json
5. **CRITICAL**: The correct_answer should be synonyms IN THE SOURCE LANGUAGE ({source_lang_name}), NOT translations
6. Accept any valid synonym in the source language, not just the ones from translations_json
7. Provide multiple acceptable synonyms as a list
8. This tests vocabulary breadth within the target language
9. No options - text input only

Return format:
{{
  "question": "[Question in {source_lang_name} asking for synonym of '{phrase_text}']",
  "correct_answer": ["synonym1", "synonym2", "synonym3"],
  "question_language": "{phrase_language}",
  "answer_language": "{phrase_language}"
}}

Example (for German word "schön"):
{{
  "question": "Nenne ein Synonym für 'schön'",
  "correct_answer": ["hübsch", "wunderschön", "herrlich", "attraktiv", "prächtig"],
  "question_language": "de",
  "answer_language": "de"
}}
"""

        messages = [
            {"role": "system", "content": "You are a language learning quiz generator. Generate high-quality synonym questions."},
            {"role": "user", "content": user_message}
        ]

        try:
            # Use structured outputs with Pydantic
            response = provider.create_structured_completion(
                messages=messages,
                response_model=SynonymQuestion,
                model=DEFAULT_MODEL,
                temperature=0.7,
                max_tokens=500
            )

            question_obj = response["parsed_object"]

            # Calculate cost
            cost_usd = CostCalculationService.calculate_cost(
                provider=provider.get_provider_name(),
                model=response["model"],
                prompt_tokens=response["usage"]["prompt_tokens"],
                completion_tokens=response["usage"]["completion_tokens"],
                cached_tokens=response["usage"]["cached_tokens"]
            )

            logger.info(f"Generated synonym question for '{phrase_text}' (cost: ${cost_usd})")

            return {
                'prompt': {
                    'question': question_obj.question,
                    'options': None,
                    'question_language': question_obj.question_language,
                    'answer_language': question_obj.answer_language
                },
                'correct_answer': question_obj.correct_answer,
                'generation_cost': {
                    'tokens': response["usage"],
                    'cost_usd': cost_usd,
                    'model': response["model"]
                }
            }

        except Exception as e:
            logger.error(f"Error generating synonym question: {e}")
            raise RuntimeError(f"Failed to generate question: {e}")


    @staticmethod
    def _generate_fallback_question(
        question_type: str,
        phrase_text: str,
        phrase_language: str,
        translations: Dict[str, Any],
        native_language: str
    ) -> Dict[str, Any]:
        """
        Generate a simple fallback question when LLM fails.

        This provides a basic question without LLM-generated distractors.
        Uses placeholder distractors to ensure quiz functionality continues.

        Args:
            question_type: Type of question
            phrase_text: The word/phrase to quiz on
            phrase_language: Language code of the phrase
            translations: Dict of translations by language name
            native_language: User's native language code

        Returns:
            dict: Question data in same format as LLM-generated questions

        Raises:
            ValueError: If unable to extract translation data
        """
        logger.info(f"Generating fallback question for '{phrase_text}'")

        try:
            # Get language names
            native_lang = Language.query.get(native_language)
            native_lang_name = native_lang.en_name if native_lang else "English"

            source_lang = Language.query.get(phrase_language)
            source_lang_name = source_lang.en_name if source_lang else phrase_language

            # Extract correct answer from translations
            correct_answer = "translation"
            if translations:
                # Try to find native language translation
                if native_lang_name in translations:
                    trans_data = translations[native_lang_name]
                    if isinstance(trans_data, dict):
                        # Try different structures
                        for key in trans_data:
                            if isinstance(trans_data[key], list) and trans_data[key]:
                                if isinstance(trans_data[key][0], list) and trans_data[key][0]:
                                    correct_answer = trans_data[key][0][0]
                                    break
                                elif isinstance(trans_data[key][0], str):
                                    correct_answer = trans_data[key][0]
                                    break

            if question_type == 'multiple_choice_target':
                # Source language phrase → native language translation
                return {
                    'prompt': {
                        'question': f"What is the {native_lang_name} translation of '{phrase_text}'?",
                        'options': [
                            correct_answer,
                            "[option 2]",
                            "[option 3]",
                            "[option 4]"
                        ],
                        'question_language': native_language,
                        'answer_language': native_language
                    },
                    'correct_answer': correct_answer
                }

            elif question_type == 'multiple_choice_source':
                # Native language translation → source language phrase
                return {
                    'prompt': {
                        'question': f"What is the {source_lang_name} word for '{correct_answer}'?",
                        'options': [
                            phrase_text,
                            "[option 2]",
                            "[option 3]",
                            "[option 4]"
                        ],
                        'question_language': native_language,
                        'answer_language': phrase_language
                    },
                    'correct_answer': phrase_text
                }

            elif question_type == 'text_input_target':
                # Simple text input: "Type the English translation of 'Katze'"
                return {
                    'prompt': {
                        'question': f"Type the {native_lang_name} translation of '{phrase_text}'",
                        'options': None,
                        'question_language': native_language,
                        'answer_language': native_language
                    },
                    'correct_answer': correct_answer
                }

            elif question_type == 'text_input_source':
                # Reverse text input: "Type the German word for 'cat'"
                return {
                    'prompt': {
                        'question': f"Type the {source_lang_name} word for '{correct_answer}'",
                        'options': None,
                        'question_language': native_language,
                        'answer_language': phrase_language
                    },
                    'correct_answer': phrase_text
                }

            elif question_type == 'contextual':
                # Fallback for contextual: simple translation question
                # Note: context_sentence not available in fallback scenario
                return {
                    'prompt': {
                        'question': f"What does '{phrase_text}' mean in this context?",
                        'options': None,
                        'question_language': native_language,
                        'answer_language': native_language,
                        'context_sentence': ''  # No context available
                    },
                    'correct_answer': correct_answer
                }

            elif question_type == 'definition':
                # Fallback for definition: ask for definition in source language
                # Extract first available definition from translations if possible
                return {
                    'prompt': {
                        'question': f"Define '{phrase_text}' in {source_lang_name}",
                        'options': None,
                        'question_language': phrase_language,
                        'answer_language': phrase_language
                    },
                    'correct_answer': f"[definition of {phrase_text} in {source_lang_name}]"
                }

            elif question_type == 'synonym':
                # Fallback for synonym: ask for synonym in source language
                return {
                    'prompt': {
                        'question': f"Provide a synonym for '{phrase_text}' in {source_lang_name}",
                        'options': None,
                        'question_language': phrase_language,
                        'answer_language': phrase_language
                    },
                    'correct_answer': [f"[synonym of {phrase_text}]"]
                }

            else:
                raise ValueError(f"Unsupported question type for fallback: {question_type}")

        except Exception as e:
            logger.error(f"Failed to generate fallback question: {str(e)}", exc_info=True)
            raise ValueError(f"Unable to generate fallback question: {str(e)}")

    @staticmethod
    def _call_api_with_retry(
        provider,
        prompt: str,
        model: str = DEFAULT_MODEL,
        system_message: str = "You are a language learning quiz generator. Return only valid JSON."
    ) -> str:
        """
        Call LLM API with exponential backoff retry logic.

        Args:
            provider client instance
            prompt: The user prompt
            model: The model to use (default: DEFAULT_MODEL from factory)
            system_message: The system message

        Returns:
            str: The API response content

        Raises:
            RuntimeError: If all retries fail
        """
        retry_delay = INITIAL_RETRY_DELAY

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                logger.debug(f"API call attempt {attempt}/{MAX_RETRIES}")

                response = provider.create_chat_completion(
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": prompt}
                    ],
                    model=model,
                    temperature=0.7,
                    max_tokens=500,
                    timeout=30.0  # 30 second timeout
                )

                content = response["content"]
                # Clean markdown code fences if present (Mistral tends to add them)
                content = _strip_markdown_code_fences(content)
                logger.debug(f"API call succeeded on attempt {attempt}")
                return content

            except (ConnectionError, TimeoutError) as e:
                # Handle connection/timeout errors with retry
                logger.warning(f"Connection/timeout error on attempt {attempt}: {str(e)}")
                if attempt < MAX_RETRIES:
                    time.sleep(retry_delay)
                    retry_delay = min(retry_delay * 2, MAX_RETRY_DELAY)
                else:
                    raise RuntimeError(f"Connection failed after {MAX_RETRIES} attempts")

            except ValueError as e:
                # Handle API errors (providers may raise ValueError for API issues)
                error_msg = str(e).lower()
                if "rate limit" in error_msg or "quota" in error_msg:
                    logger.warning(f"Rate limit hit on attempt {attempt}: {str(e)}")
                    if attempt < MAX_RETRIES:
                        time.sleep(retry_delay)
                        retry_delay = min(retry_delay * 2, MAX_RETRY_DELAY)
                    else:
                        raise RuntimeError(f"Rate limit exceeded after {MAX_RETRIES} attempts")
                else:
                    # Other ValueError, don't retry
                    raise RuntimeError(f"API error: {str(e)}")

            except Exception as e:
                logger.error(f"Unexpected error on attempt {attempt}: {str(e)}")
                raise RuntimeError(f"Unexpected API error: {str(e)}")

        raise RuntimeError(f"Failed after {MAX_RETRIES} attempts")
