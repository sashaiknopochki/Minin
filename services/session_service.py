"""Session management service for tracking user translation sessions"""
import uuid
from datetime import datetime, timezone
from typing import Optional
from models import db
from models.session import Session
from models.user import User


def create_session(user_id: int) -> Session:
    """
    Create a new session for a user.

    Args:
        user_id: The ID of the user

    Returns:
        The newly created Session object

    Raises:
        ValueError: If user_id is invalid
    """
    if not user_id:
        raise ValueError("user_id is required")

    # Generate UUID for session
    session_id = str(uuid.uuid4())

    # Create new session
    new_session = Session(
        session_id=session_id,
        user_id=user_id,
        started_at=datetime.now(timezone.utc)
    )

    db.session.add(new_session)
    db.session.commit()

    return new_session


def get_active_session(user_id: int) -> Optional[Session]:
    """
    Get the user's most recent active session (where ended_at is NULL).

    Args:
        user_id: The ID of the user

    Returns:
        The active Session object, or None if no active session exists
    """
    return Session.query.filter_by(
        user_id=user_id,
        ended_at=None
    ).order_by(Session.started_at.desc()).first()


def get_or_create_session(user_id: int) -> Session:
    """
    Get the user's active session, or create a new one if none exists.

    Args:
        user_id: The ID of the user

    Returns:
        The active or newly created Session object
    """
    active_session = get_active_session(user_id)

    if active_session:
        return active_session

    return create_session(user_id)


def end_session(session_id: str) -> Optional[Session]:
    """
    End a session by setting its ended_at timestamp.

    Args:
        session_id: The UUID of the session to end

    Returns:
        The updated Session object, or None if session not found
    """
    session = Session.query.get(session_id)

    if not session:
        return None

    session.ended_at = datetime.now(timezone.utc)
    db.session.commit()

    return session


def get_user_sessions(user_id: int, limit: int = 10) -> list[Session]:
    """
    Get a user's recent sessions.

    Args:
        user_id: The ID of the user
        limit: Maximum number of sessions to return (default: 10)

    Returns:
        List of Session objects ordered by most recent first
    """
    return Session.query.filter_by(
        user_id=user_id
    ).order_by(Session.started_at.desc()).limit(limit).all()