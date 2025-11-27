"""User Search Service - Logs user translation searches to the database"""
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from models import db
from models.phrase import Phrase
from models.user_searches import UserSearch

logger = logging.getLogger(__name__)

# Maximum character length for a phrase to be quizzable
MAX_QUIZZABLE_LENGTH = 48


def log_user_search(
    user_id: int,
    phrase_text: str,
    source_language_code: str,
    llm_response: Dict[str, Any],
    session_id: Optional[str] = None,
    context_sentence: Optional[str] = None
) -> Optional[UserSearch]:
    """
    Log a user's translation search to the database.

    This function:
    1. Gets or creates the phrase being searched
    2. Creates a UserSearch entry with the LLM translations
    3. Increments the phrase search count

    Args:
        user_id: The ID of the user performing the search
        phrase_text: The text being translated (e.g., "geben")
        source_language_code: The language code of the phrase (e.g., "de" for German)
        llm_response: The complete response dict from translate_text() containing:
            - success: bool
            - translations: dict with language keys (e.g., {"English": [["give", "verb", "..."]]})
            - source_info: list with [word, grammar, context]
            - model: str
            - usage: dict with token stats
        session_id: Optional UUID for grouping searches in the same session
        context_sentence: Optional sentence where the user saw the word

    Returns:
        The created UserSearch object, or None if the operation failed

    Example:
        >>> llm_response = translate_text("geben", "German", ["English"], model="gpt-4.1-mini")
        >>> search = log_user_search(
        ...     user_id=1,
        ...     phrase_text="geben",
        ...     source_language_code="de",
        ...     llm_response=llm_response,
        ...     session_id="123e4567-e89b-12d3-a456-426614174000"
        ... )
    """
    try:
        # Validate that the LLM response was successful
        if not llm_response.get('success'):
            logger.error(f"Cannot log search - LLM translation failed: {llm_response.get('error')}")
            return None

        # Extract translations from LLM response
        translations = llm_response.get('translations', {})
        if not translations:
            logger.warning(f"No translations found in LLM response for '{phrase_text}'")

        # Get or create the phrase
        # The Phrase model has a validator that normalizes text (strip + lowercase)
        phrase = Phrase.query.filter_by(
            text=phrase_text.strip().lower(),
            language_code=source_language_code
        ).first()

        if not phrase:
            # Determine if the phrase is quizzable based on length
            # Phrases longer than MAX_QUIZZABLE_LENGTH are likely full sentences/paragraphs
            is_quizzable = len(phrase_text.strip()) <= MAX_QUIZZABLE_LENGTH

            logger.info(
                f"Creating new phrase: '{phrase_text}' ({source_language_code}), "
                f"quizzable={is_quizzable} (length={len(phrase_text.strip())})"
            )

            phrase = Phrase(
                text=phrase_text,
                language_code=source_language_code,
                type='word',  # Default to 'word', can be updated later if needed
                is_quizzable=is_quizzable,
                search_count=0
            )
            db.session.add(phrase)
            db.session.flush()  # Get the phrase ID before creating the search

        # Increment search count
        phrase.search_count = (phrase.search_count or 0) + 1

        # Create the UserSearch entry
        user_search = UserSearch(
            user_id=user_id,
            phrase_id=phrase.id,
            searched_at=datetime.utcnow(),
            session_id=session_id,
            context_sentence=context_sentence,
            llm_translations_json=translations  # Store the translations dict as JSON
        )

        db.session.add(user_search)
        db.session.commit()

        logger.info(
            f"Logged search: user_id={user_id}, phrase='{phrase_text}' ({source_language_code}), "
            f"targets={list(translations.keys())}, search_id={user_search.id}"
        )

        return user_search

    except Exception as e:
        logger.error(f"Failed to log user search: {str(e)}", exc_info=True)
        db.session.rollback()
        return None


def get_user_search_history(
    user_id: int,
    limit: int = 50,
    session_id: Optional[str] = None
) -> list[UserSearch]:
    """
    Get a user's search history.

    Args:
        user_id: The ID of the user
        limit: Maximum number of searches to return (default: 50)
        session_id: Optional session ID to filter by

    Returns:
        List of UserSearch objects ordered by most recent first
    """
    query = UserSearch.query.filter_by(user_id=user_id)

    if session_id:
        query = query.filter_by(session_id=session_id)

    return query.order_by(UserSearch.searched_at.desc()).limit(limit).all()


def get_recent_searches_with_phrases(
    user_id: int,
    limit: int = 20
) -> list[tuple[UserSearch, Phrase]]:
    """
    Get a user's recent searches with their associated phrases.

    Args:
        user_id: The ID of the user
        limit: Maximum number of searches to return (default: 20)

    Returns:
        List of (UserSearch, Phrase) tuples ordered by most recent first
    """
    results = db.session.query(UserSearch, Phrase).join(
        Phrase, UserSearch.phrase_id == Phrase.id
    ).filter(
        UserSearch.user_id == user_id
    ).order_by(
        UserSearch.searched_at.desc()
    ).limit(limit).all()

    return results


def get_session_searches(session_id: str) -> list[UserSearch]:
    """
    Get all searches for a specific session.

    Args:
        session_id: The UUID of the session

    Returns:
        List of UserSearch objects ordered chronologically
    """
    return UserSearch.query.filter_by(
        session_id=session_id
    ).order_by(UserSearch.searched_at.asc()).all()