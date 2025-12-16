"""
Translation Pydantic Models

Structured output models for LLM translation operations.
These models define the expected JSON structure for translation responses.
"""

from pydantic import BaseModel, Field
from typing import List, Dict


class TranslationEntry(BaseModel):
    """A single translation entry consisting of [word, grammar_info, context/meaning]."""
    word: str = Field(description="The translated word or phrase")
    grammar_info: str = Field(description="Part of speech and gender/tense information")
    context: str = Field(description="Context or meaning explanation in the native language")


class TranslationResponse(BaseModel):
    """Structured response containing translations for all target languages with spell-checking.

    Example structure:
    {
        "word_exists": true,
        "sent_word": "collection",
        "correct_word": "",
        "source_info": ["collection", "noun", "a group of things collected"],
        "translations": {
            "German": [
                ["Sammlung", "noun, feminine", "a group of things collected"],
                ["Kollektion", "noun, feminine", "a fashion/design collection"]
            ],
            "Russian": [
                ["коллекция", "noun", "собрание предметов"]
            ]
        }
    }
    """
    word_exists: bool = Field(description="Whether the word exists and is correctly spelled in the source language")
    sent_word: str = Field(description="The original word that was sent")
    correct_word: str = Field(description="Suggested correct spelling (empty string if word is valid)")
    source_info: List[str] = Field(
        description="Array with 3 elements: [source_word, grammar_info, context/meaning]",
        min_length=3,
        max_length=3
    )
    translations: Dict[str, List[List[str]]] = Field(
        description="Dictionary where keys are target language names and values are arrays of [translation, grammar_info, context] triplets"
    )