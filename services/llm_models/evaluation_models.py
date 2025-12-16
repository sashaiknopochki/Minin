"""
Evaluation Pydantic Models

Structured output models for LLM answer evaluation operations.
These models define the expected JSON structure for answer evaluation responses.
"""

from pydantic import BaseModel, Field
from typing import Optional


class AnswerEvaluation(BaseModel):
    """
    Answer evaluation result from LLM.
    Used to determine if a user's answer is correct with flexible evaluation criteria.

    Evaluation criteria:
    - Accept with or without articles (cat = the cat = a cat)
    - Accept any capitalization (cat = Cat = CAT)
    - Accept minor typos (1-2 character mistakes)
    - Accept synonyms from translation data
    - Reject clearly different words or concepts

    Example:
    {
        "is_correct": true,
        "explanation": "Answer is correct - 'cat' matches the expected translation",
        "matched_answer": "cat",
        "confidence": 0.95
    }
    """
    is_correct: bool = Field(
        description="Whether the user's answer is correct"
    )
    explanation: str = Field(
        description="Brief explanation of why the answer is correct or incorrect"
    )
    matched_answer: Optional[str] = Field(
        default=None,
        description="Which valid answer the user's response matched (null if incorrect)"
    )
    confidence: Optional[float] = Field(
        default=None,
        description="Confidence score (0.0-1.0) - optional, for future use"
    )