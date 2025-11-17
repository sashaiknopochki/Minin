from models import db
from models.user import User
from flask_login import current_user
from datetime import datetime


def get_or_create_user(google_id, email, name):
    """
    Get or create a user from Google OAuth response.

    Args:
        google_id: Google OAuth identifier
        email: User's email from Google
        name: User's name from Google

    Returns:
        User object
    """
    # Check if user already exists
    user = User.query.filter_by(google_id=google_id).first()

    if user:
        # Update last active timestamp
        user.last_active_at = datetime.utcnow()
        db.session.commit()
        return user

    # Create new user with default settings
    user = User(
        google_id=google_id,
        email=email,
        name=name,
        primary_language_code='ru',  # Default to Russian
        translator_languages=['de', 'en', 'ru'],  # Default languages
        quiz_frequency=5,  # Default quiz frequency
        quiz_mode_enabled=True,
        searches_since_last_quiz=0,
        last_active_at=datetime.utcnow()
    )

    db.session.add(user)
    db.session.commit()

    return user


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
