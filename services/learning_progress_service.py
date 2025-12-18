"""Learning Progress Service - Manages user learning progress tracking for spaced repetition"""
import logging
from typing import Optional
from datetime import datetime, date, timedelta, timezone
from models import db
from models.user_learning_progress import UserLearningProgress
from models.user_searches import UserSearch
from models.quiz_attempt import QuizAttempt

logger = logging.getLogger(__name__)

# Learning stage constants
STAGE_BASIC = 'basic'
STAGE_INTERMEDIATE = 'intermediate'
STAGE_ADVANCED = 'advanced'
STAGE_MASTERED = 'mastered'

VALID_STAGES = [STAGE_BASIC, STAGE_INTERMEDIATE, STAGE_ADVANCED, STAGE_MASTERED]


def has_learning_progress(user_id: int, phrase_id: int) -> bool:
    """
    Check if a user already has a learning progress entry for a phrase.

    Args:
        user_id: The ID of the user
        phrase_id: The ID of the phrase

    Returns:
        True if learning progress exists, False otherwise

    Example:
        >>> has_learning_progress(user_id=1, phrase_id=42)
        True
    """
    progress = UserLearningProgress.query.filter_by(
        user_id=user_id,
        phrase_id=phrase_id
    ).first()

    return progress is not None


def is_first_search(user_id: int, phrase_id: int) -> bool:
    """
    Check if this is the user's first time searching for this phrase.

    This checks the user_searches table for any existing searches
    with this user_id + phrase_id combination.

    Args:
        user_id: The ID of the user
        phrase_id: The ID of the phrase

    Returns:
        True if this is the first search, False otherwise

    Example:
        >>> is_first_search(user_id=1, phrase_id=42)
        True  # User has never searched this phrase before
    """
    existing_search = UserSearch.query.filter_by(
        user_id=user_id,
        phrase_id=phrase_id
    ).first()

    return existing_search is None


def create_initial_progress(user_id: int, phrase_id: int) -> Optional[UserLearningProgress]:
    """
    Create an initial learning progress entry for a user-phrase pair.

    This creates a new entry with:
    - stage: 'basic'
    - times_reviewed: 0
    - times_correct: 0
    - times_incorrect: 0
    - next_review_date: NULL
    - first_seen_at: current timestamp
    - created_at: current timestamp

    Args:
        user_id: The ID of the user
        phrase_id: The ID of the phrase

    Returns:
        The created UserLearningProgress object, or None if creation failed

    Example:
        >>> progress = create_initial_progress(user_id=1, phrase_id=42)
        >>> progress.stage
        'basic'
    """
    try:
        # Check if progress already exists to prevent duplicates
        if has_learning_progress(user_id, phrase_id):
            logger.warning(
                f"Learning progress already exists for user_id={user_id}, phrase_id={phrase_id}"
            )
            return None

        # Create new learning progress entry
        # Set next_review_date to today so phrase is immediately eligible for quiz
        progress = UserLearningProgress(
            user_id=user_id,
            phrase_id=phrase_id,
            stage=STAGE_BASIC,
            times_reviewed=0,
            times_correct=0,
            times_incorrect=0,
            next_review_date=date.today(),  # Eligible for quiz immediately
            first_seen_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc)
        )

        db.session.add(progress)
        db.session.commit()

        logger.info(
            f"Created initial learning progress: user_id={user_id}, phrase_id={phrase_id}, "
            f"stage={STAGE_BASIC}"
        )

        return progress

    except Exception as e:
        logger.error(
            f"Failed to create learning progress for user_id={user_id}, phrase_id={phrase_id}: {str(e)}",
            exc_info=True
        )
        db.session.rollback()
        return None


def initialize_learning_progress_on_search(
    user_id: int,
    phrase_id: int,
    is_quizzable: bool = True
) -> Optional[UserLearningProgress]:
    """
    Initialize learning progress when a user searches for a phrase for the first time.

    This function should be called after logging a user search. It will:
    1. Check if this is the user's first search for this phrase
    2. Check if the phrase is quizzable
    3. Create an initial learning progress entry if both conditions are met

    Args:
        user_id: The ID of the user
        phrase_id: The ID of the phrase
        is_quizzable: Whether the phrase is suitable for quizzes (default: True)

    Returns:
        The created UserLearningProgress object if created, None otherwise

    Example:
        >>> # After logging a search
        >>> progress = initialize_learning_progress_on_search(
        ...     user_id=1,
        ...     phrase_id=42,
        ...     is_quizzable=True
        ... )
        >>> progress.stage
        'basic'
    """
    try:
        # Only create progress for quizzable phrases
        if not is_quizzable:
            logger.debug(
                f"Skipping learning progress for non-quizzable phrase: "
                f"user_id={user_id}, phrase_id={phrase_id}"
            )
            return None

        # Check if this is the first search (before the current one was logged)
        # Since we're called AFTER log_user_search, we need to check if there's
        # exactly 1 search (the one just logged)
        search_count = UserSearch.query.filter_by(
            user_id=user_id,
            phrase_id=phrase_id
        ).count()

        if search_count > 1:
            logger.debug(
                f"Not first search (count={search_count}), skipping learning progress creation: "
                f"user_id={user_id}, phrase_id={phrase_id}"
            )
            return None

        # This is the first search, create learning progress
        return create_initial_progress(user_id, phrase_id)

    except Exception as e:
        logger.error(
            f"Failed to initialize learning progress on search: "
            f"user_id={user_id}, phrase_id={phrase_id}: {str(e)}",
            exc_info=True
        )
        return None


def get_learning_progress(user_id: int, phrase_id: int) -> Optional[UserLearningProgress]:
    """
    Get the learning progress for a user-phrase pair.

    Args:
        user_id: The ID of the user
        phrase_id: The ID of the phrase

    Returns:
        The UserLearningProgress object if it exists, None otherwise

    Example:
        >>> progress = get_learning_progress(user_id=1, phrase_id=42)
        >>> progress.stage
        'intermediate'
    """
    return UserLearningProgress.query.filter_by(
        user_id=user_id,
        phrase_id=phrase_id
    ).first()


# Quiz-related functions

def update_after_quiz(quiz_attempt_id: int) -> dict:
    """
    Update learning progress after quiz attempt.

    This is the main function called after a user answers a quiz question.
    It updates:
    - times_reviewed (increment by 1)
    - times_correct / times_incorrect (based on answer correctness)
    - stage (if advancement criteria met)
    - next_review_date (spaced repetition)
    - last_reviewed_at (current timestamp)

    When advancing stages, times_correct and times_incorrect are reset to 0.

    Args:
        quiz_attempt_id: The ID of the quiz attempt

    Returns:
        dict: {
            'old_stage': str,
            'new_stage': str,
            'stage_advanced': bool,
            'next_review_date': date or None
        }

    Raises:
        ValueError: If quiz_attempt_id is invalid, quiz attempt not found,
                   progress not found, or invalid stage transitions
        RuntimeError: If database operations fail

    Example:
        >>> result = update_after_quiz(quiz_attempt_id=123)
        >>> result['stage_advanced']
        True
        >>> result['new_stage']
        'intermediate'
    """
    # Validate quiz_attempt_id
    if not isinstance(quiz_attempt_id, int) or quiz_attempt_id <= 0:
        logger.error(f"Invalid quiz_attempt_id: {quiz_attempt_id}")
        raise ValueError(f"quiz_attempt_id must be a positive integer, got: {quiz_attempt_id}")

    # Retrieve quiz attempt with error handling
    try:
        quiz_attempt = QuizAttempt.query.get(quiz_attempt_id)
    except Exception as e:
        logger.error(f"Database error retrieving quiz attempt {quiz_attempt_id}: {str(e)}", exc_info=True)
        raise RuntimeError(f"Failed to retrieve quiz attempt: {str(e)}")

    if not quiz_attempt:
        logger.error(f"Quiz attempt not found: {quiz_attempt_id}")
        raise ValueError(f"Quiz attempt {quiz_attempt_id} not found")

    # Validate quiz attempt has required fields
    if not hasattr(quiz_attempt, 'user_id') or not quiz_attempt.user_id:
        logger.error(f"Quiz attempt {quiz_attempt_id} missing user_id")
        raise ValueError(f"Quiz attempt {quiz_attempt_id} missing user_id")

    if not hasattr(quiz_attempt, 'phrase_id') or not quiz_attempt.phrase_id:
        logger.error(f"Quiz attempt {quiz_attempt_id} missing phrase_id")
        raise ValueError(f"Quiz attempt {quiz_attempt_id} missing phrase_id")

    if not hasattr(quiz_attempt, 'was_correct') or quiz_attempt.was_correct is None:
        logger.error(f"Quiz attempt {quiz_attempt_id} missing was_correct field")
        raise ValueError(f"Quiz attempt {quiz_attempt_id} missing was_correct field")

    # Retrieve learning progress with error handling
    try:
        progress = UserLearningProgress.query.filter_by(
            user_id=quiz_attempt.user_id,
            phrase_id=quiz_attempt.phrase_id
        ).first()
    except Exception as e:
        logger.error(
            f"Database error retrieving progress for user_id={quiz_attempt.user_id}, "
            f"phrase_id={quiz_attempt.phrase_id}: {str(e)}",
            exc_info=True
        )
        raise RuntimeError(f"Failed to retrieve learning progress: {str(e)}")

    if not progress:
        logger.error(
            f"No learning progress found for quiz attempt {quiz_attempt_id}: "
            f"user_id={quiz_attempt.user_id}, phrase_id={quiz_attempt.phrase_id}"
        )
        raise ValueError(
            f"No learning progress found for quiz attempt {quiz_attempt_id}. "
            f"User must search for this phrase before being quizzed."
        )

    # Validate current stage
    if not progress.stage or progress.stage not in VALID_STAGES:
        logger.error(
            f"Invalid current stage for progress: user_id={quiz_attempt.user_id}, "
            f"phrase_id={quiz_attempt.phrase_id}, stage='{progress.stage}'"
        )
        raise ValueError(f"Invalid learning stage: '{progress.stage}'. Must be one of: {VALID_STAGES}")

    # Update metrics
    try:
        progress.times_reviewed += 1
        if quiz_attempt.was_correct:
            progress.times_correct += 1
        else:
            progress.times_incorrect += 1

        progress.last_reviewed_at = datetime.now(timezone.utc)

        # Check for stage advancement
        old_stage = progress.stage
        if _should_advance_stage(progress):
            new_stage = _get_next_stage(progress.stage)

            # Validate stage transition
            if not _is_valid_stage_transition(old_stage, new_stage):
                logger.error(
                    f"Invalid stage transition: {old_stage} -> {new_stage} for "
                    f"user_id={quiz_attempt.user_id}, phrase_id={quiz_attempt.phrase_id}"
                )
                raise ValueError(f"Invalid stage transition: {old_stage} -> {new_stage}")

            progress.stage = new_stage
            logger.debug(f"Stage advanced: {old_stage} -> {new_stage}")

            # Reset counters when advancing to new stage
            progress.times_correct = 0
            progress.times_incorrect = 0

        # Calculate next review date
        progress.next_review_date = _calculate_next_review(
            progress=progress,
            was_correct=quiz_attempt.was_correct
        )

        # Commit changes with error handling
        db.session.commit()

        logger.info(
            f"Updated learning progress after quiz: user_id={quiz_attempt.user_id}, "
            f"phrase_id={quiz_attempt.phrase_id}, old_stage={old_stage}, "
            f"new_stage={progress.stage}, was_correct={quiz_attempt.was_correct}"
        )

        return {
            'old_stage': old_stage,
            'new_stage': progress.stage,
            'stage_advanced': old_stage != progress.stage,
            'next_review_date': progress.next_review_date
        }

    except ValueError:
        # Re-raise validation errors without rollback
        raise
    except Exception as e:
        logger.error(
            f"Failed to update learning progress for quiz attempt {quiz_attempt_id}: {str(e)}",
            exc_info=True
        )
        db.session.rollback()
        raise RuntimeError(f"Failed to update learning progress: {str(e)}")


def _should_advance_stage(progress: UserLearningProgress) -> bool:
    """
    Check if user should advance to next stage based on performance.

    Advancement criteria:
    - basic: 2 correct answers → advance to intermediate
    - intermediate: 2 correct answers → advance to advanced
    - advanced: 3 correct answers → advance to mastered
    - mastered: never advance (final state)

    Args:
        progress: UserLearningProgress object

    Returns:
        bool: True if should advance, False otherwise

    Example:
        >>> progress.stage = 'basic'
        >>> progress.times_correct = 2
        >>> _should_advance_stage(progress)
        True
    """
    if progress.stage == STAGE_BASIC:
        return progress.times_correct >= 2
    elif progress.stage == STAGE_INTERMEDIATE:
        return progress.times_correct >= 2
    elif progress.stage == STAGE_ADVANCED:
        return progress.times_correct >= 3
    elif progress.stage == STAGE_MASTERED:
        return False
    return False


def _get_next_stage(current_stage: str) -> str:
    """
    Get next stage in progression.

    Stage progression:
    basic → intermediate → advanced → mastered

    Args:
        current_stage: Current learning stage

    Returns:
        str: Next stage

    Example:
        >>> _get_next_stage('basic')
        'intermediate'
    """
    stages = {
        STAGE_BASIC: STAGE_INTERMEDIATE,
        STAGE_INTERMEDIATE: STAGE_ADVANCED,
        STAGE_ADVANCED: STAGE_MASTERED,
        STAGE_MASTERED: STAGE_MASTERED
    }
    return stages.get(current_stage, STAGE_BASIC)


def _is_valid_stage_transition(from_stage: str, to_stage: str) -> bool:
    """
    Validate that a stage transition is allowed.

    The learning progression is ONE-WAY FORWARD only. Users never move backwards,
    even with incorrect answers. Instead, spaced repetition increases review frequency.

    Valid transitions:
    - basic → intermediate
    - intermediate → advanced
    - advanced → mastered
    - Any stage → same stage (no advancement)

    Invalid transitions:
    - Skipping stages (basic → advanced)
    - Moving backwards (advanced → intermediate, etc.)

    Args:
        from_stage: Current learning stage
        to_stage: Target learning stage

    Returns:
        bool: True if transition is valid, False otherwise

    Example:
        >>> _is_valid_stage_transition('basic', 'intermediate')
        True
        >>> _is_valid_stage_transition('basic', 'basic')
        True
        >>> _is_valid_stage_transition('basic', 'advanced')
        False
        >>> _is_valid_stage_transition('advanced', 'intermediate')
        False
    """
    # Same stage is always valid (no advancement)
    if from_stage == to_stage:
        return True

    # Define valid one-way forward transitions
    valid_transitions = {
        STAGE_BASIC: [STAGE_INTERMEDIATE],
        STAGE_INTERMEDIATE: [STAGE_ADVANCED],
        STAGE_ADVANCED: [STAGE_MASTERED],
        STAGE_MASTERED: []  # No progression from mastered (final state)
    }

    return to_stage in valid_transitions.get(from_stage, [])


def _calculate_next_review(progress: UserLearningProgress, was_correct: bool) -> Optional[date]:
    """
    Calculate next review date using spaced repetition.

    Intervals based on stage and correctness:

    BASIC:
    - Correct: 1 day
    - Incorrect: 0 days (same day)

    INTERMEDIATE:
    - Correct: 3 days
    - Incorrect: 1 day

    ADVANCED:
    - Correct: 7 days (if times_correct < 2), 14 days (if times_correct >= 2)
    - Incorrect: 3 days

    MASTERED:
    - None (never review)

    Args:
        progress: UserLearningProgress object
        was_correct: Whether the user answered correctly

    Returns:
        date: Next review date, or None for mastered phrases

    Example:
        >>> progress.stage = 'basic'
        >>> _calculate_next_review(progress, was_correct=True)
        datetime.date(2025, 12, 3)  # Tomorrow
    """
    if progress.stage == STAGE_MASTERED:
        return None  # Never review mastered words

    if was_correct:
        # Correct answer - increase interval
        intervals = {
            STAGE_BASIC: 1,
            STAGE_INTERMEDIATE: 3,
            STAGE_ADVANCED: 7 if progress.times_correct < 2 else 14
        }
        days = intervals.get(progress.stage, 1)
    else:
        # Incorrect answer - review soon
        intervals = {
            STAGE_BASIC: 0,  # Same day
            STAGE_INTERMEDIATE: 1,
            STAGE_ADVANCED: 3
        }
        days = intervals.get(progress.stage, 1)

    return date.today() + timedelta(days=days)