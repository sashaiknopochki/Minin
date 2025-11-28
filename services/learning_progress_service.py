"""Learning Progress Service - Manages user learning progress tracking for spaced repetition"""
import logging
from typing import Optional
from datetime import datetime
from models import db
from models.user_learning_progress import UserLearningProgress
from models.user_searches import UserSearch

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
        progress = UserLearningProgress(
            user_id=user_id,
            phrase_id=phrase_id,
            stage=STAGE_BASIC,
            times_reviewed=0,
            times_correct=0,
            times_incorrect=0,
            next_review_date=None,  # NULL until first quiz attempt
            first_seen_at=datetime.utcnow(),
            created_at=datetime.utcnow()
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