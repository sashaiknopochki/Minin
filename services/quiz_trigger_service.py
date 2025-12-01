"""
Quiz Trigger Service - Determines when to trigger quizzes and selects phrases for review.

This service implements the quiz triggering logic based on user search frequency
and spaced repetition scheduling.
"""

from datetime import date
from models import db
from models.user import User
from models.user_learning_progress import UserLearningProgress
from models.phrase import Phrase


class QuizTriggerService:
    """Service to check if quiz should be triggered and select phrases for review"""

    @staticmethod
    def should_trigger_quiz(user):
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
                    'searches_remaining': int (only if threshold not reached)
                }

        Examples:
            >>> result = QuizTriggerService.should_trigger_quiz(current_user)
            >>> if result['should_trigger']:
            ...     quiz_phrase_id = result['eligible_phrase'].phrase_id
            ...     # Show quiz for this phrase
        """
        # Check if quiz mode is enabled
        if not user.quiz_mode_enabled:
            return {
                'should_trigger': False,
                'reason': 'quiz_mode_disabled',
                'eligible_phrase': None
            }

        # Check if search counter reached threshold
        if user.searches_since_last_quiz < user.quiz_frequency:
            return {
                'should_trigger': False,
                'reason': 'threshold_not_reached',
                'searches_remaining': user.quiz_frequency - user.searches_since_last_quiz,
                'eligible_phrase': None
            }

        # Find phrase that needs review
        eligible_phrase = QuizTriggerService.get_phrase_for_quiz(user)

        if not eligible_phrase:
            return {
                'should_trigger': False,
                'reason': 'no_phrases_due_for_review',
                'eligible_phrase': None
            }

        return {
            'should_trigger': True,
            'reason': 'quiz_triggered',
            'eligible_phrase': eligible_phrase
        }

    @staticmethod
    def get_phrase_for_quiz(user):
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
        # Get user's active language codes
        # e.g., ["en", "de", "ru"]
        active_languages = user.translator_languages

        # If user has no active languages, return None
        if not active_languages:
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

        return eligible_phrase