"""
LLM Translation Service
Handles translation using LLM providers (OpenAI, Mistral, etc.) with support for multiple target languages
"""

import os
import json
import logging
from typing import List, Dict, Optional
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from services.llm_provider_factory import get_llm_client, LLMProviderFactory
from services.llm_models.translation_models import TranslationResponse
from services.cost_service import CostCalculationService

# Configure logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Get default model based on configured provider
DEFAULT_MODEL = LLMProviderFactory.get_default_model()

# Model constants for backward compatibility
GPT_4_1_MINI = "gpt-4.1-mini"
O4_MINI = "o4-mini"
MISTRAL_SMALL = "mistral-small-latest"
MISTRAL_MEDIUM = "mistral-medium-latest"
MISTRAL_LARGE = "mistral-large-latest"


def translate_text(
    text: str,
    source_language: str,
    target_languages: List[str],
    model: str = DEFAULT_MODEL,
    native_language: str = "English"
) -> Dict:
    """
    Translate text from source language to multiple target languages using OpenAI API.
    Returns all possible meanings/definitions of the word.

    Args:
        text: The text to translate
        source_language: The source language (e.g., "English", "German", "Spanish")
        target_languages: List of target languages (e.g., ["English", "German", "Spanish"])
        model: The OpenAI model to use (default: GPT_4_1_MINI)
        native_language: Language for definitions/contexts (default: "English")

    Returns:
        Dictionary containing:
        - success: bool
        - original_text: str
        - source_language: str
        - target_languages: list
        - native_language: str
        - translations: dict with language keys and list of meanings
        - model: str
        - usage: token usage stats (if success)
        - error: error message (if failed)
    """
    # Initialize LLM provider
    try:
        provider = get_llm_client()
    except ValueError as e:
        logger.error(f"Failed to initialize LLM provider: {str(e)}")
        return {
            "success": False,
            "error": f"LLM provider configuration error: {str(e)}",
            "original_text": text,
            "source_language": source_language,
            "target_languages": target_languages,
            "native_language": native_language
        }

    # Create system prompt for translation with spell-checking and multiple meanings
    target_langs_str = ", ".join(target_languages)
    system_prompt = f"""You are a professional translator, linguist, and spelling checker.

FIRST: Check if the word/phrase "{text}" exists and is correctly spelled in {source_language}. If it's misspelled or invalid, suggest the correct spelling and return empty translations.

THEN: Translate the {source_language} word/phrase "{text}" to the following target languages: {target_langs_str}

IMPORTANT RULES:
1. Do NOT include {source_language} in your translations (since that's the source language)
2. Provide ALL possible meanings and definitions for each translation
3. Write ALL definitions/contexts in {native_language}, not in the target language
4. CRITICAL RULE - When to create separate vs combined entries:
   - If translations are DIFFERENT WORDS (e.g., "снимать" → "take off", "lose weight", "accept"), create SEPARATE entries for each word
   - If translations are the EXACT SAME WORD with different meanings (e.g., "собака" → "dog" (animal), "dog" (insult)), create ONE entry with combined contexts
   - Example CORRECT: [["take off", "verb", "remove clothing"], ["lose weight", "verb phrase", "reduce body mass"], ["accept", "verb", "agree to take"]]
   - Example WRONG: [["take off, lose weight, accept", "verb", "various meanings"]] ← DO NOT DO THIS
5. Only include translations that are actually valid in the target language - do not include meanings that don't exist in that language
6. ALWAYS include grammatical information:
   - For nouns: part of speech and gender if the language has genders (e.g., "существительное, женский род", "noun, masculine")
   - For verbs: part of speech and relevant tense/form info (e.g., "глагол, прошедшее время", "verb, infinitive")
   - For other parts of speech: include the type (adjective, adverb, etc.)
7. ALSO provide grammatical analysis of the SOURCE word itself in a "source_info" field

Return your response as a JSON object with "translations" and "source_info" fields.
Each translation should be an array with THREE elements: [translation, grammar_info, context/meaning in {native_language}].
The "source_info" field should be an array with THREE elements: [source_word, grammar_info, context/meaning in {native_language}].

Examples:

CORRECT - with source_info included:
If translating "кошка" from Russian to German with contexts in Russian:
{{
  "source_info": ["кошка", "существительное, женский род", "домашнее животное, самка кошачьих"],
  "translations": {{
    "German": [["Katze", "существительное, женский род", "домашнее животное, самка кошачьих"]]
  }}
}}

CORRECT - combining repeated words with grammatical info:
If translating "собака" from Russian to English with contexts in Russian:
{{
  "source_info": ["собакаC", "существительное, мужской род", "домашнее животное из семейства псовых, презрительное обозначение человека, инструмент для захвата"],
  "translations": {{
    "English": [["dog", "существительное", "домашнее животное из семейства псовых, презрительное обозначение человека, инструмент для захвата"]]
  }}
}}

CORRECT - different words for different meanings with grammatical info:
If translating "bank" from English to German with contexts in Russian:
{{
  "source_info": ["bank", "существительное", "финансовое учреждение, берег реки"],
  "translations": {{
    "German": [["Bank", "существительное, женский род", "финансовое учреждение"], ["Ufer", "существительное, средний род", "берег реки"], ["Böschung", "существительное, женский род", "насыпь"]]
  }}
}}

CORRECT - different words must be separate entries:
If translating "снимать" from Russian to English with contexts in Russian:
{{
  "source_info": ["снимать", "глагол, инфинитив", "убирать что-либо, уменьшать вес, брать обязанности"],
  "translations": {{
    "English": [
      ["take off", "verb, infinitive", "снимать что-либо, убирать"],
      ["lose weight", "verb phrase", "уменьшать вес тела"],
      ["accept", "verb", "брать на себя обязанности, принимать"]
    ]
  }}
}}

WRONG - DO NOT combine different words:
{{
  "translations": {{
    "English": [["take off, lose weight, accept", "verb", "various meanings"]]
  }}
}}"""

    # Create user message with spell-check request and JSON format
    user_message = f"""Check spelling and translate:

Word/phrase: "{text}"
Source language: {source_language}
Target languages: {target_langs_str}

Respond with JSON including spell-check fields:
{{
  "word_exists": true/false,
  "sent_word": "{text}",
  "correct_word": "suggested_spelling_or_empty_string",
  "source_info": ["source_word", "grammar_info", "context"],
  "translations": {{
    "TargetLanguage1": [["translation", "grammar_info", "context"], ...],
    "TargetLanguage2": [["translation", "grammar_info", "context"], ...],
    ...
  }}
}}

Examples:

Valid word:
{{
  "word_exists": true,
  "sent_word": "collection",
  "correct_word": "",
  "source_info": ["collection", "noun", "a group of things collected"],
  "translations": {{
    "German": [["Sammlung", "noun, feminine", "a group of things collected"], ["Kollektion", "noun, feminine", "a fashion/design collection"]],
    "Russian": [["коллекция", "noun", "собрание предметов"]]
  }}
}}

Invalid/misspelled word:
{{
  "word_exists": false,
  "sent_word": "colection",
  "correct_word": "collection",
  "source_info": [],
  "translations": {{}}
}}
"""

    # Make API call with structured outputs
    try:
        logger.info(f"Translating '{text}' from {source_language} to {target_languages}")

        # Prepare messages
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]

        # Use structured completion with Pydantic model
        response = provider.create_structured_completion(
            messages=messages,
            response_model=TranslationResponse,
            model=model,
            temperature=0.2,  # Lower temperature for more consistent spell-checking
            max_tokens=1000  # Increased for spell-check fields
        )

        # Extract parsed object
        parsed_response = response["parsed_object"]

        # Calculate cost immediately after LLM call
        cost_usd = CostCalculationService.calculate_cost(
            provider=provider.get_provider_name(),
            model=response["model"],
            prompt_tokens=response["usage"]["prompt_tokens"],
            completion_tokens=response["usage"]["completion_tokens"],
            cached_tokens=response["usage"].get("cached_tokens", 0)
        )

        logger.info(
            f"Translation successful. Tokens: {response['usage']['total_tokens']}, "
            f"Cost: ${float(cost_usd):.6f}"
        )

        # Check if word doesn't exist (spelling issue detected)
        if not parsed_response.word_exists:
            logger.warning(
                f"Spelling issue detected: '{parsed_response.sent_word}' → "
                f"suggested: '{parsed_response.correct_word}'"
            )
            return {
                "success": True,
                "spelling_issue": True,
                "sent_word": parsed_response.sent_word,
                "correct_word": parsed_response.correct_word,
                "source_language": source_language,
                "target_languages": target_languages,
                "original_text": text,
                "model": response["model"],
                "usage": response["usage"],
                "cost_usd": float(cost_usd)
            }

        # Return successful translation with cost data
        return {
            "success": True,
            "spelling_issue": False,
            "original_text": text,
            "source_language": source_language,
            "target_languages": target_languages,
            "native_language": native_language,
            "source_info": parsed_response.source_info,
            "translations": parsed_response.translations,
            "model": response["model"],
            "usage": response["usage"],
            "cost_usd": float(cost_usd)
        }

    except Exception as e:
        logger.error(f"Translation failed: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "original_text": text,
            "source_language": source_language,
            "target_languages": target_languages,
            "native_language": native_language
        }
