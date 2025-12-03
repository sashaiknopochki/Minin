"""
Quiz Trigger Service - Determines when to trigger quizzes and selects phrases for review.

This service implements the quiz triggering logic based on user search frequency
and spaced repetition scheduling.
"""

import logging
from datetime import date
from typing import Dict, Any, Optional
from models import db
from models.user import User
from models.user_learning_progress import UserLearningProgress
from models.phrase import Phrase

# Configure logging
logger = logging.getLogger(__name__)


class QuizTriggerService:
    """Service to check if quiz should be triggered and select phrases for review"""

    @staticmethod
    def should_trigger_quiz(user: Optional[User]) -> Dict[str, Any]:
        """
        Check if quiz should be triggered for this user.

        This method evaluates multiple conditions to determine if it's time to show
        a quiz to the user:
        1. Quiz mode must be enabled
        2. Search counter must have reached the frequency threshold
        3. There must be at least one eligible phrase due for review

        Args:
            user (User): The user instance to check

        Returns:
            dict: Dictionary containing trigger decision and context
                {
                    'should_trigger': bool,
                    'reason': str,  # Why quiz should/shouldn't trigger
                    'eligible_phrase': UserLearningProgress or None,
                    'searches_remaining': int (only if threshold not reached),
                    'error': str (only if error occurred)
                }

        Examples:
            >>> result = QuizTriggerService.should_trigger_quiz(current_user)
            >>> if result['should_trigger']:
            ...     quiz_phrase_id = result['eligible_phrase'].phrase_id
            ...     # Show quiz for this phrase

        Raises:
            ValueError: If user is None or invalid
        """
        # Validate user input
        if not user:
            logger.error("should_trigger_quiz called with None user")
            raise ValueError("User cannot be None")

        if not hasattr(user, 'id') or user.id is None:
            logger.error(f"Invalid user object: missing or None id attribute")
            raise ValueError("Invalid user: user must have a valid id")

        try:
            # Check if quiz mode is enabled
            if not user.quiz_mode_enabled:
                logger.debug(f"Quiz mode disabled for user_id={user.id}")
                return {
                    'should_trigger': False,
                    'reason': 'quiz_mode_disabled',
                    'eligible_phrase': None
                }

            # Validate quiz frequency setting
            if not hasattr(user, 'quiz_frequency') or user.quiz_frequency is None:
                logger.warning(f"User {user.id} missing quiz_frequency, defaulting to disabled")
                return {
                    'should_trigger': False,
                    'reason': 'invalid_quiz_settings',
                    'eligible_phrase': None,
                    'error': 'Quiz frequency not configured'
                }

            # Check if search counter reached threshold
            searches_since_last = getattr(user, 'searches_since_last_quiz', 0) or 0
            if searches_since_last < user.quiz_frequency:
                logger.debug(
                    f"Quiz threshold not reached for user_id={user.id}: "
                    f"{searches_since_last}/{user.quiz_frequency}"
                )
                return {
                    'should_trigger': False,
                    'reason': 'threshold_not_reached',
                    'searches_remaining': user.quiz_frequency - searches_since_last,
                    'eligible_phrase': None
                }

            # Find phrase that needs review
            eligible_phrase = QuizTriggerService.get_phrase_for_quiz(user)

            if not eligible_phrase:
                logger.info(f"No phrases due for review for user_id={user.id}")
                return {
                    'should_trigger': False,
                    'reason': 'no_phrases_due_for_review',
                    'eligible_phrase': None
                }

            logger.info(
                f"Quiz triggered for user_id={user.id}, phrase_id={eligible_phrase.phrase_id}"
            )
            return {
                'should_trigger': True,
                'reason': 'quiz_triggered',
                'eligible_phrase': eligible_phrase
            }

        except ValueError:
            # Re-raise ValueError for proper error propagation
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error in should_trigger_quiz for user_id={user.id}: {str(e)}",
                exc_info=True
            )
            return {
                'should_trigger': False,
                'reason': 'error',
                'eligible_phrase': None,
                'error': f"Failed to determine quiz trigger status: {str(e)}"
            }

    @staticmethod
    def get_phrase_for_quiz(user: User) -> Optional[UserLearningProgress]:
        """
        Select a phrase that's due for review based on spaced repetition logic.

        This method implements the phrase selection algorithm with the following priority:
        1. Exclude mastered phrases (user has already mastered them)
        2. Only include quizzable phrases (is_quizzable = True)
        3. Only include phrases in user's currently active languages
        4. Only include phrases where next_review_date <= today (due or overdue)
        5. Order by next_review_date ASC (oldest/most overdue first)

        The language filtering ensures that if a user changes their active languages,
        they only get quizzed on phrases in their current language set. The is_quizzable
        filter excludes very long sentences or other phrases marked as unsuitable for quizzing.

        Args:
            user (User): The user instance to get phrase for

        Returns:
            UserLearningProgress or None: The learning progress record for the
                phrase to quiz, or None if no eligible phrases found

        Examples:
            >>> progress = QuizTriggerService.get_phrase_for_quiz(current_user)
            >>> if progress:
            ...     phrase = progress.phrase
            ...     # Quiz user on this phrase

        Implementation Notes:
            - Uses a JOIN to efficiently filter by phrase language
            - The query is optimized with indexes on user_id and next_review_date
            - Returns the most overdue phrase first for optimal spaced repetition
            - Mastered phrases are permanently excluded from review
        """
        try:
            # Validate user
            if not user or not hasattr(user, 'id'):
                logger.error("get_phrase_for_quiz called with invalid user")
                return None

            # Get user's active language codes
            # e.g., ["en", "de", "ru"]
            active_languages = getattr(user, 'translator_languages', None)

            # If user has no active languages, return None
            if not active_languages or not isinstance(active_languages, list):
                logger.debug(
                    f"User {user.id} has no active translator languages, "
                    f"cannot select phrases for quiz"
                )
                return None

            if len(active_languages) == 0:
                logger.debug(f"User {user.id} has empty translator_languages list")
                return None

            # Query for eligible phrase using spaced repetition logic
            eligible_phrase = UserLearningProgress.query.join(
                Phrase, UserLearningProgress.phrase_id == Phrase.id
            ).filter(
                UserLearningProgress.user_id == user.id,
                UserLearningProgress.stage != 'mastered',  # CRITICAL: exclude mastered
                UserLearningProgress.next_review_date <= date.today(),  # Due or overdue
                Phrase.language_code.in_(active_languages),  # Only active languages
                Phrase.is_quizzable == True  # Only quizzable phrases
            ).order_by(
                UserLearningProgress.next_review_date.asc()  # Oldest first
            ).first()

            if eligible_phrase:
                logger.debug(
                    f"Selected phrase_id={eligible_phrase.phrase_id} for quiz "
                    f"(user_id={user.id}, stage={eligible_phrase.stage})"
                )
            else:
                logger.debug(f"No eligible phrases found for user_id={user.id}")

            return eligible_phrase

        except Exception as e:
            logger.error(
                f"Error querying for eligible phrase for user_id={user.id}: {str(e)}",
                exc_info=True
            )
            return None