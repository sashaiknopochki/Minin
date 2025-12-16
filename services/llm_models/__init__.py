"""
LLM Pydantic Models

Structured output models for LLM operations:
- Translation models (TranslationEntry, TranslationResponse)
- Question models (MultipleChoiceQuestion, TextInputQuestion, etc.)
- Evaluation models (AnswerEvaluation)
"""

from .translation_models import TranslationEntry, TranslationResponse
from .question_models import (
    MultipleChoiceQuestion,
    TextInputQuestion,
    ContextualQuestion,
    DefinitionQuestion,
    SynonymQuestion
)
from .evaluation_models import AnswerEvaluation

__all__ = [
    'TranslationEntry',
    'TranslationResponse',
    'MultipleChoiceQuestion',
    'TextInputQuestion',
    'ContextualQuestion',
    'DefinitionQuestion',
    'SynonymQuestion',
    'AnswerEvaluation'
]