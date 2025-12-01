"""
Quiz Attempt Service - Creates and manages quiz attempt records.

This service is responsible for creating quiz attempts and selecting
appropriate question types based on the user's learning stage.
"""

import random
from models import db
from models.quiz_attempt import QuizAttempt
from models.user_learning_progress import UserLearningProgress


class QuizAttemptService:
    """Service to create quiz attempt records with appropriate question types"""

    @staticmethod
    def create_quiz_attempt(user_id, phrase_id):
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
            ValueError: If no learning progress exists for the user-phrase pair

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
        # Get learning progress
        progress = UserLearningProgress.query.filter_by(
            user_id=user_id,
            phrase_id=phrase_id
        ).first()

        if not progress:
            raise ValueError(f"No learning progress found for user {user_id}, phrase {phrase_id}")

        # Determine question type based on stage
        question_type = QuizAttemptService.select_question_type(progress.stage)

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

        return quiz_attempt

    @staticmethod
    def select_question_type(stage):
        """
        Select appropriate question type based on learning stage.

        The question type is randomly selected from a pool of types appropriate
        for the user's current learning stage. This provides variety while
        maintaining appropriate difficulty.

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
            stage (str): Learning stage - 'basic', 'intermediate', 'advanced', or 'mastered'

        Returns:
            str: Randomly selected question type from the stage's pool

        Raises:
            ValueError: If stage is invalid or 'mastered' (mastered phrases shouldn't be quizzed)

        Examples:
            >>> type1 = QuizAttemptService.select_question_type('basic')
            >>> type1 in ['multiple_choice_target', 'multiple_choice_source']
            True

            >>> type2 = QuizAttemptService.select_question_type('intermediate')
            >>> type2 in ['text_input_target', 'text_input_source']
            True

            >>> QuizAttemptService.select_question_type('mastered')
            Traceback (most recent call last):
                ...
            ValueError: Invalid stage: mastered

        Notes:
            - Uses random.choice() for selection to provide variety
            - Mastered phrases should never reach this function (filtered earlier)
            - Question types align with cognitive progression: recognition → recall → application
        """
        question_types = {
            'basic': ['multiple_choice_target', 'multiple_choice_source'],
            'intermediate': ['text_input_target', 'text_input_source'],
            'advanced': ['contextual', 'definition', 'synonym'],
            'mastered': []  # Should never reach here
        }

        types = question_types.get(stage, [])
        if not types:
            raise ValueError(f"Invalid stage: {stage}")

        return random.choice(types)