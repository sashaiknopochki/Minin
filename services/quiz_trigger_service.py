"""
Quiz Trigger Service - Determines when to trigger quizzes and selects phrases for review.

This service implements the quiz triggering logic based on user search frequency
and spaced repetition scheduling.
"""

import logging
from datetime import date
from typing import Dict, Any, Optional, List, Tuple
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

    @staticmethod
    def get_filtered_phrases_for_practice(
        user: User,
        stage: str = 'all',
        language_code: str = 'all',
        due_for_review: bool = False,
        exclude_phrase_ids: Optional[List[int]] = None
    ) -> Tuple[Optional[UserLearningProgress], int]:
        """
        Select phrases for practice mode with flexible filtering.

        This method extends get_phrase_for_quiz() with additional filtering options
        for the Practice page. It returns both the next phrase to practice AND the
        total count of matching phrases for progress tracking.

        Args:
            user (User): The user instance to get phrases for
            stage (str): Filter by learning stage ('all', 'basic', 'intermediate',
                        'advanced', 'mastered'). Default: 'all'
            language_code (str): Filter by language ISO code or 'all'. Default: 'all'
            due_for_review (bool): If True, only include phrases where
                                  next_review_date <= today. Default: False
            exclude_phrase_ids (List[int], optional): List of phrase IDs to exclude
                                                     (already seen in current session)

        Returns:
            Tuple[UserLearningProgress or None, int]:
                - First element: The learning progress record for the next phrase,
                                or None if no eligible phrases found
                - Second element: Total count of phrases matching the filters

        Examples:
            >>> # Get all phrases due for review in German, basic stage
            >>> progress, total = QuizTriggerService.get_filtered_phrases_for_practice(
            ...     user, stage='basic', language_code='de', due_for_review=True
            ... )
            >>> print(f"Question 1 of {total}")

            >>> # Get next phrase excluding already seen ones
            >>> progress, total = QuizTriggerService.get_filtered_phrases_for_practice(
            ...     user, exclude_phrase_ids=[1, 5, 12]
            ... )

        Implementation Notes:
            - Always includes is_quizzable=True filter
            - When language_code='all', uses user's translator_languages
            - Orders by next_review_date ASC (most overdue first)
            - Returns (None, 0) if no phrases match filters
        """
        try:
            # Validate user
            if not user or not hasattr(user, 'id'):
                logger.error("get_filtered_phrases_for_practice called with invalid user")
                return (None, 0)

            # Log user details for debugging
            active_languages = getattr(user, 'translator_languages', None)
            logger.info(
                f"🔍 DEBUG Practice Query - User: {user.id}, "
                f"Filters: stage={stage}, language_code={language_code}, due={due_for_review}, "
                f"exclude_count={len(exclude_phrase_ids) if exclude_phrase_ids else 0}"
            )
            logger.info(f"   User translator_languages: {active_languages}")
            logger.info(f"   User primary_language_code: {getattr(user, 'primary_language_code', 'N/A')}")

            # Build base query
            query = UserLearningProgress.query.join(
                Phrase, UserLearningProgress.phrase_id == Phrase.id
            ).filter(
                UserLearningProgress.user_id == user.id,
                Phrase.is_quizzable == True
            )

            # Count after base filters
            count_after_base = query.count()
            logger.info(f"   After base filters (user_id + is_quizzable): {count_after_base} phrases")

            # Apply stage filter
            if stage != 'all':
                query = query.filter(UserLearningProgress.stage == stage)
                count_after_stage = query.count()
                logger.info(f"   After stage filter ({stage}): {count_after_stage} phrases")

            # Apply language filter
            if language_code != 'all':
                query = query.filter(Phrase.language_code == language_code)
                count_after_lang = query.count()
                logger.info(f"   After language filter ({language_code}): {count_after_lang} phrases")
            else:
                # Use user's active translator languages
                if not active_languages or not isinstance(active_languages, list) or len(active_languages) == 0:
                    logger.warning(f"❌ User {user.id} has no active translator languages")
                    return (None, 0)
                query = query.filter(Phrase.language_code.in_(active_languages))
                count_after_lang = query.count()
                logger.info(f"   After language filter (in {active_languages}): {count_after_lang} phrases")

            # Apply due for review filter
            if due_for_review:
                query = query.filter(UserLearningProgress.next_review_date <= date.today())
                count_after_due = query.count()
                logger.info(f"   After due filter (next_review_date <= today): {count_after_due} phrases")

            # Apply exclusion filter (phrases already seen in current session)
            if exclude_phrase_ids and len(exclude_phrase_ids) > 0:
                query = query.filter(UserLearningProgress.phrase_id.notin_(exclude_phrase_ids))
                count_after_exclude = query.count()
                logger.info(f"   After exclusion filter: {count_after_exclude} phrases")

            # Order by most overdue first (spaced repetition priority)
            query = query.order_by(UserLearningProgress.next_review_date.asc())

            # Get total count of matching phrases
            total_count = query.count()

            # Get first phrase
            next_phrase = query.first()

            if next_phrase:
                phrase = next_phrase.phrase
                logger.info(
                    f"✅ Selected phrase for practice: '{phrase.text}' ({phrase.language_code}), "
                    f"stage={next_phrase.stage}, next_review={next_phrase.next_review_date}, "
                    f"total_matching={total_count}"
                )
            else:
                logger.warning(
                    f"❌ No phrases found for practice "
                    f"(user_id={user.id}, filters: stage={stage}, "
                    f"language={language_code}, due={due_for_review})"
                )

            return (next_phrase, total_count)

        except Exception as e:
            logger.error(
                f"Error in get_filtered_phrases_for_practice for user_id={user.id}: {str(e)}",
                exc_info=True
            )
            return (None, 0)