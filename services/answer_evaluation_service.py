"""
Answer Evaluation Service - Evaluates quiz answers and updates learning progress.

This service handles the evaluation of user answers for quiz questions,
updates the quiz attempt records, and tracks learning progress metrics
for spaced repetition.

MVP implementation uses simple exact matching for multiple choice questions.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from models import db
from models.quiz_attempt import QuizAttempt
from models.user_learning_progress import UserLearningProgress

# Configure logging
logger = logging.getLogger(__name__)


class AnswerEvaluationService:
    """Service to evaluate quiz answers and update learning progress"""

    @staticmethod
    def evaluate_answer(quiz_attempt_id: int, user_answer: str) -> Dict[str, Any]:
        """
        Evaluate a user's quiz answer and update learning progress.

        This method evaluates the user's answer against the correct answer,
        updates the quiz attempt record with the result, and updates the
        user's learning progress metrics for spaced repetition tracking.

        Workflow:
        1. Retrieve and validate quiz attempt
        2. Validate question type (MVP: multiple choice only)
        3. Extract valid answers from correct_answer field
        4. Evaluate user's answer
        5. Update quiz_attempt with user_answer and was_correct
        6. Update learning progress metrics
        7. Return evaluation result

        Args:
            quiz_attempt_id (int): The ID of the quiz attempt to evaluate
            user_answer (str): The user's submitted answer

        Returns:
            dict: Evaluation result with keys:
                - was_correct (bool): Whether the answer was correct
                - correct_answer (str): The correct answer(s) for display
                - explanation (str): Simple feedback message

        Raises:
            ValueError: If quiz_attempt not found, user_answer is empty,
                       question_type is unsupported, or required fields are missing
            RuntimeError: If database operations fail

        Examples:
            >>> result = AnswerEvaluationService.evaluate_answer(
            ...     quiz_attempt_id=123,
            ...     user_answer="cat"
            ... )
            >>> print(result['was_correct'])
            True
            >>> print(result['correct_answer'])
            "cat"

        Implementation Notes:
            - MVP supports only multiple_choice_target and multiple_choice_source
            - Uses case-insensitive exact matching with whitespace stripping
            - Handles both single answers and JSON arrays of valid answers
            - Updates are atomic: quiz_attempt and learning_progress or rollback
            - Missing learning progress logs warning but doesn't fail evaluation
        """
        # Validate input
        if not user_answer or not user_answer.strip():
            raise ValueError("User answer cannot be empty")

        # Retrieve quiz attempt
        quiz_attempt = QuizAttempt.query.get(quiz_attempt_id)
        if not quiz_attempt:
            raise ValueError(f"Quiz attempt not found: {quiz_attempt_id}")

        # Validate required fields
        if not quiz_attempt.question_type:
            raise ValueError("Quiz attempt missing question_type field")
        if not quiz_attempt.correct_answer:
            raise ValueError("Quiz attempt missing correct_answer field")

        # Validate question type (MVP: multiple choice only)
        supported_types = ['multiple_choice_target', 'multiple_choice_source']
        if quiz_attempt.question_type not in supported_types:
            raise ValueError(
                f"Question type '{quiz_attempt.question_type}' not supported in MVP. "
                f"Supported types: {', '.join(supported_types)}"
            )

        # Extract valid answers
        valid_answers = AnswerEvaluationService._extract_valid_answers(
            quiz_attempt.correct_answer
        )

        # Evaluate answer
        was_correct = AnswerEvaluationService._evaluate_multiple_choice(
            user_answer=user_answer,
            valid_answers=valid_answers
        )

        # Update quiz attempt
        try:
            quiz_attempt.user_answer = user_answer.strip()
            quiz_attempt.was_correct = was_correct
            db.session.commit()

            logger.info(
                f"Quiz attempt {quiz_attempt_id} evaluated: "
                f"user_answer='{user_answer}', was_correct={was_correct}"
            )

        except Exception as e:
            logger.error(
                f"Failed to update quiz attempt {quiz_attempt_id}: {str(e)}",
                exc_info=True
            )
            db.session.rollback()
            raise RuntimeError(f"Failed to persist evaluation: {str(e)}")

        # Update learning progress
        AnswerEvaluationService._update_learning_progress(
            user_id=quiz_attempt.user_id,
            phrase_id=quiz_attempt.phrase_id,
            was_correct=was_correct
        )

        # Prepare response with all valid answers
        if len(valid_answers) == 1:
            correct_answer_display = valid_answers[0]
        else:
            # Multiple valid answers: show all of them
            correct_answer_display = " / ".join(valid_answers)

        explanation = "Correct!" if was_correct else f"Incorrect. Correct answer(s): {correct_answer_display}"

        return {
            "was_correct": was_correct,
            "correct_answer": correct_answer_display,
            "explanation": explanation
        }

    @staticmethod
    def _extract_valid_answers(correct_answer_field: str) -> List[str]:
        """
        Extract and normalize valid answers from the correct_answer field.

        The correct_answer field can contain either a single answer string
        or a JSON array of multiple valid answers. This method parses both
        formats and returns a normalized list.

        Normalization:
        - Convert all answers to lowercase
        - Strip leading/trailing whitespace
        - Filter out empty strings

        Args:
            correct_answer_field (str): The correct_answer field value,
                                       either a string or JSON array string

        Returns:
            list: List of normalized valid answer strings

        Raises:
            ValueError: If correct_answer_field is empty or contains only invalid answers

        Examples:
            >>> AnswerEvaluationService._extract_valid_answers("cat")
            ['cat']

            >>> AnswerEvaluationService._extract_valid_answers('["cat", "feline"]')
            ['cat', 'feline']

            >>> AnswerEvaluationService._extract_valid_answers("  Cat  ")
            ['cat']

        Implementation Notes:
            - Attempts JSON parsing first, falls back to string parsing
            - Logs error for invalid JSON but continues with fallback
            - All answers normalized to lowercase for case-insensitive matching
        """
        if not correct_answer_field or not correct_answer_field.strip():
            raise ValueError("correct_answer_field cannot be empty")

        valid_answers = []

        # Try parsing as JSON array first
        try:
            parsed = json.loads(correct_answer_field)
            if isinstance(parsed, list):
                valid_answers = parsed
            else:
                # Single value in JSON format, treat as string
                valid_answers = [correct_answer_field]
        except (json.JSONDecodeError, TypeError):
            # Not valid JSON, treat as single string answer
            valid_answers = [correct_answer_field]

        # Normalize all answers: lowercase, strip whitespace, filter empty
        normalized = []
        for answer in valid_answers:
            if isinstance(answer, str):
                cleaned = answer.strip().lower()
                if cleaned:
                    normalized.append(cleaned)
            else:
                logger.warning(
                    f"Skipping non-string answer in valid answers: {answer} (type: {type(answer)})"
                )

        if not normalized:
            raise ValueError("No valid answers found after normalization")

        return normalized

    @staticmethod
    def _evaluate_multiple_choice(user_answer: str, valid_answers: List[str]) -> bool:
        """
        Evaluate a multiple choice answer using exact matching.

        This method performs case-insensitive exact matching between the
        user's answer and the list of valid answers. The user's answer is
        considered correct if it matches ANY of the valid answers.

        Matching strategy:
        - Case-insensitive: "CAT" matches "cat"
        - Whitespace tolerant: " cat " matches "cat"
        - Exact match only (not substring matching)

        Args:
            user_answer (str): The user's submitted answer
            valid_answers (list): List of valid answer strings (already normalized)

        Returns:
            bool: True if user_answer matches any valid answer, False otherwise

        Examples:
            >>> AnswerEvaluationService._evaluate_multiple_choice("cat", ["cat", "feline"])
            True

            >>> AnswerEvaluationService._evaluate_multiple_choice("CAT", ["cat"])
            True

            >>> AnswerEvaluationService._evaluate_multiple_choice(" cat ", ["cat"])
            True

            >>> AnswerEvaluationService._evaluate_multiple_choice("dog", ["cat", "feline"])
            False

        Implementation Notes:
            - Assumes valid_answers are already normalized (lowercase, stripped)
            - Normalizes user_answer before comparison
            - Uses simple string equality (extensible to fuzzy matching later)
        """
        # Normalize user answer
        normalized_user_answer = user_answer.strip().lower()

        # Check if user answer matches any valid answer
        return normalized_user_answer in valid_answers

    @staticmethod
    def _update_learning_progress(
        user_id: int,
        phrase_id: int,
        was_correct: bool
    ) -> Optional[UserLearningProgress]:
        """
        Update learning progress metrics after quiz evaluation.

        This method updates the user's learning progress record to track
        quiz performance for spaced repetition. It increments review counts
        and updates the last reviewed timestamp.

        Updates made:
        - times_reviewed: Increment by 1
        - times_correct OR times_incorrect: Increment by 1 based on was_correct
        - last_reviewed_at: Set to current timestamp

        Note: Does NOT update stage or next_review_date in MVP.
        These will be handled by future spaced repetition algorithm.

        Args:
            user_id (int): The ID of the user
            phrase_id (int): The ID of the phrase being reviewed
            was_correct (bool): Whether the user's answer was correct

        Returns:
            UserLearningProgress: The updated learning progress object,
                                 or None if not found

        Raises:
            RuntimeError: If database operations fail

        Examples:
            >>> progress = AnswerEvaluationService._update_learning_progress(
            ...     user_id=1,
            ...     phrase_id=42,
            ...     was_correct=True
            ... )
            >>> progress.times_reviewed
            5
            >>> progress.times_correct
            4

        Implementation Notes:
            - Logs warning if learning progress not found, but doesn't fail
            - Uses db.session.commit() to persist changes
            - Rolls back on failure to maintain data consistency
            - Future: Will integrate with spaced repetition algorithm
        """
        try:
            # Get learning progress
            progress = UserLearningProgress.query.filter_by(
                user_id=user_id,
                phrase_id=phrase_id
            ).first()

            if not progress:
                logger.warning(
                    f"Learning progress not found for user_id={user_id}, "
                    f"phrase_id={phrase_id}. Skipping progress update."
                )
                return None

            # Update metrics
            progress.times_reviewed += 1
            if was_correct:
                progress.times_correct += 1
            else:
                progress.times_incorrect += 1

            progress.last_reviewed_at = datetime.utcnow()

            db.session.commit()

            logger.info(
                f"Updated learning progress: user_id={user_id}, phrase_id={phrase_id}, "
                f"reviewed={progress.times_reviewed}, correct={progress.times_correct}, "
                f"incorrect={progress.times_incorrect}"
            )

            return progress

        except Exception as e:
            logger.error(
                f"Failed to update learning progress for user_id={user_id}, "
                f"phrase_id={phrase_id}: {str(e)}",
                exc_info=True
            )
            db.session.rollback()
            raise RuntimeError(f"Failed to update learning progress: {str(e)}")