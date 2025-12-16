"""
Question Pydantic Models

Structured output models for LLM question generation operations.
These models define the expected JSON structure for different quiz question types.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Union


class MultipleChoiceQuestion(BaseModel):
    """
    Multiple choice question with 4 options.
    Used for both target and source language multiple choice questions.

    Example:
    {
        "question": "What is the English translation of 'geben'?",
        "options": ["to give", "to take", "to run", "to eat"],
        "correct_answer": "to give",  # or ["to give", "to provide"] for multiple valid answers
        "question_language": "en",
        "answer_language": "en"
    }
    """
    question: str = Field(description="The question text (ending with '?')")
    options: List[str] = Field(
        description="List of 4 options: 1 correct answer + 3 distractors",
        min_items=4,
        max_items=4
    )
    correct_answer: Union[str, List[str]] = Field(
        description="The correct answer(s) - single string or list if multiple valid answers"
    )
    question_language: str = Field(description="ISO 639-1 language code for question (e.g., 'en', 'de')")
    answer_language: str = Field(description="ISO 639-1 language code for answers (e.g., 'en', 'de')")


class TextInputQuestion(BaseModel):
    """
    Text input question where user types the answer.
    Used for both target and source language text input questions.
    No multiple choice options - user must recall and type the answer.

    Example:
    {
        "question": "Type the English translation of 'geben'.",
        "options": null,
        "correct_answer": "to give",  # or ["to give", "to provide"] for multiple valid answers
        "question_language": "en",
        "answer_language": "en"
    }
    """
    question: str = Field(description="The question text (ending with '.')")
    options: Optional[List[str]] = Field(
        default=None,
        description="Always null for text input questions"
    )
    correct_answer: Union[str, List[str]] = Field(
        description="The correct answer(s) - single string or list if multiple valid answers"
    )
    question_language: str = Field(description="ISO 639-1 language code for question (e.g., 'en', 'de')")
    answer_language: str = Field(description="ISO 639-1 language code for answer (e.g., 'en', 'de')")


class ContextualQuestion(BaseModel):
    """
    Contextual question that tests understanding of a word within a sentence.
    Question is in source language, answer is in native language.

    Example:
    {
        "question": "In the sentence 'Ich gebe dir ein Buch', what does 'gebe' mean?",
        "correct_answer": "give",
        "contextual_meaning": "In this context, 'gebe' means to transfer or hand over something to someone",
        "question_language": "de",
        "answer_language": "en"
    }
    """
    question: str = Field(description="The question with context sentence (ending with '?')")
    correct_answer: str = Field(description="The contextually appropriate translation")
    contextual_meaning: str = Field(
        description="Brief explanation of why this meaning fits the context"
    )
    question_language: str = Field(description="ISO 639-1 language code for question (e.g., 'de')")
    answer_language: str = Field(description="ISO 639-1 language code for answer (e.g., 'en')")


class DefinitionQuestion(BaseModel):
    """
    Definition question where user must define the word in the source language.
    Both question and answer are in the source language.
    Tests deep understanding.

    Example:
    {
        "question": "Was bedeutet 'geben'?",
        "correct_answer": ["etwas jemandem übergeben", "jemandem etwas schenken"],
        "question_language": "de",
        "answer_language": "de"
    }
    """
    question: str = Field(description="The question asking for definition (ending with '?')")
    correct_answer: Union[str, List[str]] = Field(
        description="The definition(s) in source language - single string or list if multiple valid definitions"
    )
    question_language: str = Field(description="ISO 639-1 language code (same as source language)")
    answer_language: str = Field(description="ISO 639-1 language code (same as source language)")


class SynonymQuestion(BaseModel):
    """
    Synonym question where user must provide a synonym in the source language.
    Both question and answer are in the source language.
    Tests vocabulary breadth.

    Example:
    {
        "question": "Nenne ein Synonym für 'schön'",
        "correct_answer": ["hübsch", "wunderschön", "herrlich", "attraktiv"],
        "question_language": "de",
        "answer_language": "de"
    }
    """
    question: str = Field(description="The question asking for synonym (ending with '?' or '.')")
    correct_answer: List[str] = Field(
        description="List of acceptable synonyms in source language",
        min_items=1
    )
    question_language: str = Field(description="ISO 639-1 language code (same as source language)")
    answer_language: str = Field(description="ISO 639-1 language code (same as source language)")