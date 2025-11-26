from models import db
from models.user import User
from flask_login import current_user
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def get_or_create_user(google_id, email, name):
    """
    Get or create a user from Google OAuth response.

    Args:
        google_id: Google OAuth identifier
        email: User's email from Google
        name: User's name from Google

    Returns:
        User object or None if database operation fails
    """
    try:
        # Check if user already exists
        user = User.query.filter_by(google_id=google_id).first()

        if user:
            # Update last active timestamp
            user.last_active_at = datetime.utcnow()
            db.session.commit()
            return user

        # Create new user without default languages (will trigger onboarding)
        user = User(
            google_id=google_id,
            email=email,
            name=name,
            primary_language_code=None,  # User will set during onboarding
            translator_languages=None,  # User will set during onboarding
            quiz_frequency=5,  # Default quiz frequency
            quiz_mode_enabled=True,
            searches_since_last_quiz=0,
            last_active_at=datetime.utcnow()
        )

        db.session.add(user)
        db.session.commit()

        logger.info(f'Created new user: {email}')
        return user

    except Exception as e:
        db.session.rollback()
        logger.error(f'Failed to create/update user {email}: {str(e)}')
        return None


def is_authenticated():
    """
    Check if the current user is authenticated.

    Returns:
        bool: True if user is authenticated, False otherwise
    """
    return current_user.is_authenticated


def get_current_user():
    """
    Get the current authenticated user.

    Returns:
        User object or None if not authenticated
    """
    if current_user.is_authenticated:
        return current_user
    return None
