"""
Quiz Attempt Service - Creates and manages quiz attempt records.

This service is responsible for creating quiz attempts and selecting
appropriate question types based on the user's learning stage.
"""

import logging
import random
from typing import Optional
from models import db
from models.quiz_attempt import QuizAttempt
from models.user import User
from models.user_learning_progress import UserLearningProgress

# Configure logging
logger = logging.getLogger(__name__)


class QuizAttemptService:
    """Service to create quiz attempt records with appropriate question types"""

    @staticmethod
    def create_quiz_attempt(user_id: int, phrase_id: int) -> QuizAttempt:
        """
        Create a new quiz attempt record.

        This method creates a quiz attempt with a question type selected based
        on the user's current learning stage for the phrase. The quiz attempt
        is created in a preliminary state - the actual question content, correct
        answer, and user answer will be filled in by subsequent services.

        Workflow:
        1. Retrieve user's learning progress for the phrase
        2. Select appropriate question type based on learning stage
        3. Create QuizAttempt record with question_type
        4. Flush to database to get the quiz_attempt.id
        5. Return the quiz attempt for further processing

        Args:
            user_id (int): The ID of the user taking the quiz
            phrase_id (int): The ID of the phrase to quiz

        Returns:
            QuizAttempt: The created quiz attempt object with:
                - question_type: Selected based on learning stage
                - was_correct: Initially set to False (updated after evaluation)
                - prompt_json: None (to be filled by QuestionGenerationService)
                - correct_answer: None (to be filled by QuestionGenerationService)
                - user_answer: None (to be filled when user submits)

        Raises:
            ValueError: If no learning progress exists, invalid IDs, or invalid stage
            RuntimeError: If database operation fails

        Examples:
            >>> quiz_attempt = QuizAttemptService.create_quiz_attempt(
            ...     user_id=1,
            ...     phrase_id=42
            ... )
            >>> print(quiz_attempt.question_type)  # e.g., 'multiple_choice_target'
            >>> print(quiz_attempt.id)  # e.g., 123

        Notes:
            - This method only creates the quiz attempt record structure
            - QuestionGenerationService should be called next to populate prompt_json
            - AnswerEvaluationService will update was_correct after user answers
            - The method uses flush() instead of commit() to allow transaction control
        """
        # Validate inputs
        if not user_id or not isinstance(user_id, int) or user_id <= 0:
            logger.error(f"Invalid user_id: {user_id}")
            raise ValueError(f"Invalid user_id: {user_id}")

        if not phrase_id or not isinstance(phrase_id, int) or phrase_id <= 0:
            logger.error(f"Invalid phrase_id: {phrase_id}")
            raise ValueError(f"Invalid phrase_id: {phrase_id}")

        try:
            # Get learning progress
            progress = UserLearningProgress.query.filter_by(
                user_id=user_id,
                phrase_id=phrase_id
            ).first()

            if not progress:
                logger.error(
                    f"No learning progress found for user_id={user_id}, phrase_id={phrase_id}"
                )
                raise ValueError(
                    f"No learning progress found for user {user_id}, phrase {phrase_id}. "
                    f"User must search for this phrase before being quizzed on it."
                )

            # Validate stage
            if not progress.stage:
                logger.error(
                    f"Learning progress missing stage: user_id={user_id}, phrase_id={phrase_id}"
                )
                raise ValueError(
                    f"Learning progress for user {user_id}, phrase {phrase_id} has no stage"
                )

            # Determine question type based on stage
            # First fetch user to check preferences
            user = User.query.get(user_id)
            if not user:
                # Should not happen if validation passed earlier, but safe guard
                logger.warning(f"User {user_id} not found when creating quiz attempt")
            
            try:
                question_type = QuizAttemptService.select_question_type(progress.stage, user)
            except ValueError as e:
                logger.error(
                    f"Failed to select question type for stage={progress.stage}: {str(e)}"
                )
                raise ValueError(
                    f"Cannot create quiz for stage '{progress.stage}': {str(e)}"
                )

            # Create quiz attempt (without prompt_json yet - that's for question generation)
            quiz_attempt = QuizAttempt(
                user_id=user_id,
                phrase_id=phrase_id,
                question_type=question_type,
                was_correct=False  # Placeholder - will be updated by AnswerEvaluationService
                # prompt_json will be filled by QuestionGenerationService
                # correct_answer will be filled by QuestionGenerationService
                # user_answer will be filled when user submits answer
                # was_correct will be updated by AnswerEvaluationService
            )

            db.session.add(quiz_attempt)
            db.session.flush()  # Get quiz_attempt.id without committing transaction

            logger.info(
                f"Created quiz attempt: id={quiz_attempt.id}, user_id={user_id}, "
                f"phrase_id={phrase_id}, question_type={question_type}, stage={progress.stage}"
            )

            return quiz_attempt

        except ValueError:
            # Re-raise ValueError for proper error propagation
            raise
        except Exception as e:
            logger.error(
                f"Failed to create quiz attempt for user_id={user_id}, "
                f"phrase_id={phrase_id}: {str(e)}",
                exc_info=True
            )
            db.session.rollback()
            raise RuntimeError(f"Failed to create quiz attempt: {str(e)}")

    @staticmethod
    def select_question_type(stage: str, user: Optional[User] = None) -> str:
        """
        Select appropriate question type based on learning stage and user preferences.

        The question type is randomly selected from a pool of types appropriate
        for the user's current learning stage. This provides variety while
        maintaining appropriate difficulty.

        For Advanced stage, it respects the user's enabled question types.

        Question Type Progression:
        - basic: Multiple choice questions (recognition)
            - 'multiple_choice_target': Translate to native language (easier)
            - 'multiple_choice_source': Translate from native language

        - intermediate: Text input questions (recall)
            - 'text_input_target': Type translation in native language
            - 'text_input_source': Type translation in source language

        - advanced: Contextual understanding (application)
            - 'contextual': Translate in context of a sentence
            - 'definition': Provide or identify definition
            - 'synonym': Identify or provide synonyms

        Args:
            stage (str): Learning stage
            user (User, optional): User object to check preferences

        Returns:
            str: Randomly selected question type from the stage's pool
        """
        # Validate stage input
        if not stage or not isinstance(stage, str):
            logger.error(f"Invalid stage type: {type(stage)}, value: {stage}")
            raise ValueError(f"Stage must be a non-empty string, got: {stage}")

        stage = stage.strip().lower()

        if not stage:
            logger.error("Empty stage after stripping")
            raise ValueError("Stage cannot be empty")

        question_types = {
            'basic': ['multiple_choice_target', 'multiple_choice_source'],
            'intermediate': ['text_input_target', 'text_input_source'],
            'advanced': ['contextual', 'definition', 'synonym'],
            'mastered': [] 
        }

        types = question_types.get(stage, [])
        if not types:
            valid_stages = [s for s, t in question_types.items() if t]
            logger.error(
                f"Invalid or mastered stage: '{stage}'. "
                f"Valid stages: {', '.join(valid_stages)}"
            )
            raise ValueError(
                f"Invalid stage: '{stage}'. Mastered phrases should not be quizzed. "
                f"Valid stages: {', '.join(valid_stages)}"
            )

        # Apply user preferences for Advanced stage
        if stage == 'advanced' and user:
            preferred_types = []
            if getattr(user, 'enable_contextual_quiz', True):
                preferred_types.append('contextual')
            if getattr(user, 'enable_definition_quiz', True):
                preferred_types.append('definition')
            if getattr(user, 'enable_synonym_quiz', True):
                preferred_types.append('synonym')
            
            # If user has disabled ALL advanced types, fallback to all types
            # or ideally fallback to Intermediate, but sticking to stage for now
            if preferred_types:
                types = preferred_types
                logger.debug(f"Filtered advanced types for user {user.id}: {types}")
            else:
                logger.warning(f"User {user.id} disabled all advanced types, falling back to all advanced types")

        try:
            selected_type = random.choice(types)
            logger.debug(f"Selected question type '{selected_type}' for stage '{stage}'")
            return selected_type
        except IndexError:
            logger.error(f"Unexpected empty types list for stage '{stage}'")
            raise ValueError(f"No question types available for stage: {stage}")