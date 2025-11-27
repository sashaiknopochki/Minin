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
DEFAULT_MODEL = O4_MINI

# Models that support structured outputs
STRUCTURED_OUTPUT_MODELS = {
    "gpt-4o-mini",
    "gpt-4o-2024-08-06",
    "gpt-4o-2024-11-20",
    "gpt-4o",
}


# Pydantic models for structured outputs
class TranslationEntry(BaseModel):
    """A single translation entry consisting of [word, context/meaning]."""
    word: str = Field(description="The translated word or phrase")
    context: str = Field(description="Context or meaning explanation in the native language")


class TranslationResponse(BaseModel):
    """Structured response containing translations for all target languages.

    Each field is a target language name with a list of translation entries.
    The model is dynamically created based on target_languages parameter.
    """
    translations: Dict[str, List[List[str]]] = Field(
        description="Dictionary where keys are target language names and values are arrays of [translation, context] pairs"
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

    # Create system prompt for translation with multiple meanings
    target_langs_str = ", ".join(target_languages)
    system_prompt = f"""You are a professional translator and linguist.
Translate the {source_language} word/phrase "{text}" to the following target languages: {target_langs_str}

IMPORTANT RULES:
1. Do NOT include {source_language} in your translations (since that's the source language)
2. Provide ALL possible meanings and definitions for each translation
3. Write ALL definitions/contexts in {native_language}, not in the target language
4. CRITICAL: If multiple meanings translate to the EXACT SAME word in the target language, you MUST combine them into ONE entry with all meanings separated by commas. DO NOT repeat the same word multiple times.
5. Only include translations that are actually valid in the target language - do not include meanings that don't exist in that language

Return your response as a JSON object with a "translations" field.
Each translation should be an array with two elements: [translation, context/meaning in {native_language}].

Examples:

CORRECT - combining repeated words:
If translating "собака" from Russian to English with contexts in Russian:
{{
  "translations": {{
    "English": [["dog", "домашнее животное из семейства псовых, презрительное обозначение человека, инструмент для захвата"]]
  }}
}}

INCORRECT - DO NOT do this:
{{
  "translations": {{
    "English": [["dog", "домашнее животное"], ["dog", "презрительное обозначение"], ["dog", "инструмент"]]
  }}
}}

CORRECT - different words for different meanings:
If translating "bank" from English to German with contexts in Russian:
{{
  "translations": {{
    "German": [["Bank", "финансовое учреждение"], ["Ufer", "берег реки"], ["Böschung", "насыпь"]]
  }}
}}"""

    # Check if model supports structured outputs
    use_structured_output = model in STRUCTURED_OUTPUT_MODELS

    # Make API call
    try:
        logger.info(f"Translating '{text}' from {source_language} to {target_languages}")

        # Prepare API call parameters
        api_params = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            "temperature": 0.3,
            "max_tokens": 800
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
                        "minItems": 2,
                        "maxItems": 2
                    }
                }

            json_schema = {
                "name": "translation_response",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "translations": {
                            "type": "object",
                            "properties": language_properties,
                            "required": target_languages,
                            "additionalProperties": False
                        }
                    },
                    "required": ["translations"],
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
            translations_dict = response_data.get("translations", {})

            # Fallback if translations not in expected format
            if not translations_dict and isinstance(response_data, dict):
                translations_dict = response_data
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM response as JSON: {e}")
            translations_dict = {target_languages[0]: [[translation_content, ""]]}

        logger.info(f"Translation successful. Tokens used: {response.usage.total_tokens}")

        return {
            "success": True,
            "original_text": text,
            "source_language": source_language,
            "target_languages": target_languages,
            "native_language": native_language,
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
