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
    """Structured response containing translations for all target languages.

    Each field is a target language name with a list of translation entries.
    The model is dynamically created based on target_languages parameter.

    Example structure:
    {
        "translations": {
            "English": [
                ["to give", "verb", "to hand over or transfer something"],
                ["to provide", "verb", "to supply or make available"]
            ],
            "French": [
                ["donner", "verbe", "transférer quelque chose à quelqu'un"]
            ]
        }
    }
    """
    translations: Dict[str, List[List[str]]] = Field(
        description="Dictionary where keys are target language names and values are arrays of [translation, grammar_info, context] triplets"
    )