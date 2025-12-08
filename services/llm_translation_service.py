"""
LLM Translation Service
Handles translation using OpenAI API with support for multiple target languages
"""

import os
import json
import logging
from typing import List, Dict, Optional
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field

# Configure logging
logger = logging.getLogger(__name__)

# Model constants
GPT_4_1_MINI = "gpt-4.1-mini"
O4_MINI = "o4-mini"
DEFAULT_MODEL = GPT_4_1_MINI

# Models that support structured outputs
STRUCTURED_OUTPUT_MODELS = {
    "gpt-4o-mini",
    "gpt-4.1-mini",
    "o4-mini",
    "gpt-4o-2024-08-06",
    "gpt-4o-2024-11-20",
    "gpt-4o",
}


# Pydantic models for structured outputs
class TranslationEntry(BaseModel):
    """A single translation entry consisting of [word, grammar_info, context/meaning]."""
    word: str = Field(description="The translated word or phrase")
    grammar_info: str = Field(description="Part of speech and gender/tense information")
    context: str = Field(description="Context or meaning explanation in the native language")


class TranslationResponse(BaseModel):
    """Structured response containing translations for all target languages.

    Each field is a target language name with a list of translation entries.
    The model is dynamically created based on target_languages parameter.
    """
    translations: Dict[str, List[List[str]]] = Field(
        description="Dictionary where keys are target language names and values are arrays of [translation, grammar_info, context] triplets"
    )


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
    # Load environment variables
    load_dotenv()

    # Get API key from environment
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY not found in environment variables")
        return {
            "success": False,
            "error": "OPENAI_API_KEY not configured",
            "original_text": text,
            "source_language": source_language,
            "target_languages": target_languages,
            "native_language": native_language
        }

    # Initialize OpenAI client
    client = OpenAI(api_key=api_key)

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

    # Check if model supports structured outputs
    use_structured_output = model in STRUCTURED_OUTPUT_MODELS

    # Make API call
    try:
        logger.info(f"Translating '{text}' from {source_language} to {target_languages}")

        # Prepare API call parameters with lower temperature for deterministic spell-checking
        api_params = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            "temperature": 0.2,  # Lower temperature for more consistent spell-checking
            "max_tokens": 1000  # Increased for spell-check fields
        }

        # Add structured output for supported models
        if use_structured_output:
            # Build dynamic schema with specific language properties
            language_properties = {}
            for lang in target_languages:
                language_properties[lang] = {
                    "type": "array",
                    "items": {
                        "type": "array",
                        "items": {"type": "string"},
                        "minItems": 3,
                        "maxItems": 3
                    }
                }

            json_schema = {
                "name": "translation_response",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "word_exists": {
                            "type": "boolean",
                            "description": "Whether the word exists and is correctly spelled in the source language"
                        },
                        "sent_word": {
                            "type": "string",
                            "description": "The original word that was sent"
                        },
                        "correct_word": {
                            "type": "string",
                            "description": "Suggested correct spelling (empty string if word is valid)"
                        },
                        "source_info": {
                            "type": "array",
                            "items": {"type": "string"},
                            "minItems": 3,
                            "maxItems": 3
                        },
                        "translations": {
                            "type": "object",
                            "properties": language_properties,
                            "required": target_languages,
                            "additionalProperties": False
                        }
                    },
                    "required": ["word_exists", "sent_word", "correct_word", "source_info", "translations"],
                    "additionalProperties": False
                }
            }
            api_params["response_format"] = {
                "type": "json_schema",
                "json_schema": json_schema
            }
            logger.info(f"Using structured outputs for model {model}")
        else:
            # For models that don't support structured outputs, request JSON mode
            api_params["response_format"] = {"type": "json_object"}
            logger.info(f"Using JSON mode for model {model}")

        response = client.chat.completions.create(**api_params)

        translation_content = response.choices[0].message.content

        # Parse JSON response
        try:
            response_data = json.loads(translation_content)

            # Extract spell-check fields (with safe defaults)
            word_exists = response_data.get("word_exists", True)  # Default to True for safety
            sent_word = response_data.get("sent_word", text)
            correct_word = response_data.get("correct_word", "")

            translations_dict = response_data.get("translations", {})
            source_info = response_data.get("source_info", [text, "", ""])

            # Check if word doesn't exist (spelling issue detected)
            if not word_exists:
                logger.warning(f"Spelling issue detected: '{sent_word}' → suggested: '{correct_word}'")
                return {
                    "success": True,
                    "spelling_issue": True,
                    "sent_word": sent_word,
                    "correct_word": correct_word,
                    "source_language": source_language,
                    "target_languages": target_languages,
                    "original_text": text,
                    "model": model,
                    "usage": {
                        "prompt_tokens": response.usage.prompt_tokens,
                        "completion_tokens": response.usage.completion_tokens,
                        "total_tokens": response.usage.total_tokens
                    }
                }

            # Fallback if translations not in expected format
            if not translations_dict and isinstance(response_data, dict):
                translations_dict = response_data
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM response as JSON: {e}")
            translations_dict = {target_languages[0]: [[translation_content, "", ""]]}
            source_info = [text, "", ""]

        logger.info(f"Translation successful. Tokens used: {response.usage.total_tokens}")

        return {
            "success": True,
            "spelling_issue": False,  # Explicitly set for valid words
            "original_text": text,
            "source_language": source_language,
            "target_languages": target_languages,
            "native_language": native_language,
            "source_info": source_info,
            "translations": translations_dict,
            "model": model,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
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
