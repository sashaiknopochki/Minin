"""
CLI script for LLM-powered translation using OpenAI API.
Translates words/phrases and returns all meanings.
"""

import os
import json
from dotenv import load_dotenv
from openai import OpenAI

# Model constants
GPT_4_1_MINI = "gpt-4.1-mini"
O4_MINI = "o4-mini"


def translate_text(text: str, source_language: str, target_languages: list, model: str, native_language: str = "English") -> dict:
    """
    Translate text from source language to multiple target languages using OpenAI API.
    Returns all possible meanings/definitions of the word.

    Args:
        text: The text to translate
        source_language: The source language (e.g., "English", "German", "Spanish")
        target_languages: List of target languages (e.g., ["English", "German", "Spanish"])
        model: The OpenAI model to use (e.g., "gpt-4o-mini", "o4-mini-2025-04-16")
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
        - usage: token usage stats
    """
    # Load environment variables from .env file
    load_dotenv()

    # Get API key from environment
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in environment variables")

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

Return your response as a JSON object where each key is a target language and the value is an array of translations.
Each translation should be an array with two elements: [translation, context/meaning in {native_language}].

Examples:

CORRECT - combining repeated words:
If translating "собака" from Russian to English (with contexts in Russian):
{{
  "English": [["dog", "(домашнее животное из семейства псовых, презрительное обозначение человека, инструмент для захвата)"]]
}}

INCORRECT - DO NOT do this:
{{
  "English": [["dog", "(домашнее животное)"], ["dog", "(презрительное обозначение)"], ["dog", "(инструмент)"]]
}}

CORRECT - different words for different meanings:
If translating "bank" from English to German (with contexts in Russian):
{{
  "German": [["Bank", "(финансовое учреждение)"], ["Ufer", "(берег реки)"], ["Böschung", "(насыпь)"]]
}}

Only return the JSON object, nothing else."""

    # Make API call
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            temperature=0.3,
            max_tokens=800
        )

        translation_content = response.choices[0].message.content.strip()

        # Parse JSON response
        try:
            translations_dict = json.loads(translation_content)
            if not isinstance(translations_dict, dict):
                # Fallback: create dict with single language
                translations_dict = {target_languages[0]: [translation_content]}
        except json.JSONDecodeError:
            # If not valid JSON, create fallback structure
            translations_dict = {target_languages[0]: [translation_content]}

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
        return {
            "success": False,
            "error": str(e),
            "original_text": text,
            "source_language": source_language,
            "target_languages": target_languages,
            "native_language": native_language
        }


# CLI testing
if __name__ == "__main__":
    result = translate_text("собака", "Russian", ["English", "German"], GPT_4_1_MINI, native_language="Russian")

    if result["success"]:
        print(result)
        print(f"\nOriginal ({result['source_language']}): {result['original_text']}")
        print(f"Native Language (for contexts): {result['native_language']}")
        print(f"Model: {result['model']}")
        print(f"\nTranslations:")
        for lang, meanings in result['translations'].items():
            print(f"\n  {lang}:")
            for i, (translation, context) in enumerate(meanings, 1):
                print(f"    {i}. {translation} {context}")
        print(f"\nTokens used: {result['usage']['total_tokens']}")
    else:
        print(f"Error: {result['error']}")