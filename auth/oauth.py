from flask import Blueprint, redirect, url_for, flash, session, request, jsonify
from flask_dance.contrib.google import make_google_blueprint, google
from flask_login import login_user, logout_user, current_user
from google.oauth2 import id_token
from google.auth.transport import requests
import os
import logging
from services.session_service import create_session, get_active_session, end_session

# Set up logging
logger = logging.getLogger(__name__)

# Create OAuth blueprint
bp = Blueprint('auth', __name__, url_prefix='/auth')

# Validate OAuth credentials exist
_google_client_id = os.getenv('GOOGLE_CLIENT_ID')
_google_client_secret = os.getenv('GOOGLE_CLIENT_SECRET')

if not _google_client_id or not _google_client_secret:
    logger.warning(
        'Google OAuth credentials not configured. '
        'Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET environment variables.'
    )

# Create Google OAuth blueprint
google_bp = make_google_blueprint(
    client_id=_google_client_id,
    client_secret=_google_client_secret,
    scope=['openid', 'https://www.googleapis.com/auth/userinfo.email', 'https://www.googleapis.com/auth/userinfo.profile'],
    redirect_url='/auth/google/callback'
)


@bp.route('/google', methods=['POST'])
def google_signin():
    """
    Handle Google Identity Services (GIS) sign-in.
    Receives a credential token from the frontend and verifies it.
    """
    try:
        data = request.get_json()
        credential = data.get('credential')

        if not credential:
            return jsonify({
                'success': False,
                'error': 'No credential provided'
            }), 400

        # Verify the credential token with Google
        try:
            idinfo = id_token.verify_oauth2_token(
                credential,
                requests.Request(),
                _google_client_id
            )

            # Extract user information
            google_id = idinfo.get('sub')
            email = idinfo.get('email')
            name = idinfo.get('name', '')
            picture = idinfo.get('picture', '')

            if not google_id or not email:
                logger.error('Incomplete user info from Google token')
                return jsonify({
                    'success': False,
                    'error': 'Incomplete user information'
                }), 400

            # Import here to avoid circular imports
            from auth.utils import get_or_create_user

            # Get or create user
            user = get_or_create_user(google_id, email, name)

            if not user:
                logger.error(f'Failed to create/retrieve user for google_id: {google_id}')
                return jsonify({
                    'success': False,
                    'error': 'Failed to create user account'
                }), 500

            # Log in the user with Flask-Login
            login_user(user, remember=True)
            logger.info(f'User {email} logged in successfully via GIS')

            # Create a new session for the user
            try:
                new_session = create_session(user.id)
                logger.info(f'Created new session {new_session.session_id} for user {email}')
            except Exception as session_error:
                logger.warning(f'Failed to create session for user {email}: {str(session_error)}')
                # Don't fail login if session creation fails

            return jsonify({
                'success': True,
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'name': user.name,
                    'picture': picture,
                    'primary_language_code': user.primary_language_code,
                    'translator_languages': user.translator_languages,
                    'quiz_frequency': user.quiz_frequency
                }
            }), 200

        except ValueError as e:
            # Invalid token
            logger.error(f'Invalid Google token: {str(e)}')
            return jsonify({
                'success': False,
                'error': 'Invalid credential token'
            }), 401

    except Exception as e:
        logger.exception(f'Exception during Google sign-in: {str(e)}')
        return jsonify({
            'success': False,
            'error': 'An unexpected error occurred'
        }), 500


@bp.route('/google/redirect')
def google_login():
    """Redirect to Google OAuth login (legacy redirect-based flow)"""
    if not google.authorized:
        # 307 Temporary Redirect - maintains POST method if used
        return redirect(url_for('google.login'), code=307)
    # Already authorized, go to callback
    return redirect(url_for('auth.google_callback'), code=302)


@bp.route('/google/callback')
def google_callback():
    """Handle Google OAuth callback"""
    if not google.authorized:
        logger.warning(
            'OAuth callback received but user not authorized. '
            'Possible causes: user denied access, session expired, or state mismatch.'
        )
        flash('Failed to log in with Google. Please try again.', 'error')
        return redirect(url_for('home'))

    # Get user info from Google
    try:
        resp = google.get('/oauth2/v2/userinfo')

        if not resp.ok:
            logger.error(
                f'Failed to fetch user info from Google. '
                f'Status: {resp.status_code}, Response: {resp.text[:200] if resp.text else "empty"}'
            )
            flash('Failed to fetch user info from Google. Please try again.', 'error')
            return redirect(url_for('home'))

        google_info = resp.json()
        google_id = google_info.get('id')
        email = google_info.get('email')
        name = google_info.get('name', '')

        if not google_id or not email:
            logger.error(
                f'Incomplete user info received from Google. '
                f'google_id: {google_id is not None}, email: {email is not None}'
            )
            flash('Failed to retrieve complete user information from Google.', 'error')
            return redirect(url_for('home'))

        # Import here to avoid circular imports
        from auth.utils import get_or_create_user

        # Get or create user
        user = get_or_create_user(google_id, email, name)

        if not user:
            logger.error(f'Failed to create/retrieve user for google_id: {google_id}, email: {email}')
            flash('Failed to create user account. Please contact support.', 'error')
            return redirect(url_for('home'))

        # Log in the user
        login_user(user)
        logger.info(f'User {email} logged in successfully')

        # Create a new session for the user
        try:
            new_session = create_session(user.id)
            logger.info(f'Created new session {new_session.session_id} for user {email}')
        except Exception as session_error:
            logger.warning(f'Failed to create session for user {email}: {str(session_error)}')
            # Don't fail login if session creation fails

        flash('Successfully logged in!', 'success')

        return redirect(url_for('home'))

    except Exception as e:
        logger.exception(f'Exception during Google OAuth callback: {str(e)}')
        flash('An unexpected error occurred during login. Please try again.', 'error')
        return redirect(url_for('home'))


@bp.route('/me', methods=['GET'])
def get_current_user():
    """
    Get current authenticated user information.
    Used by frontend to check auth status and get user data.
    """
    if current_user.is_authenticated:
        return jsonify({
            'success': True,
            'authenticated': True,
            'user': {
                'id': current_user.id,
                'email': current_user.email,
                'name': current_user.name,
                'primary_language_code': current_user.primary_language_code,
                'translator_languages': current_user.translator_languages,
                'quiz_frequency': current_user.quiz_frequency
            }
        }), 200
    else:
        return jsonify({
            'success': True,
            'authenticated': False,
            'user': None
        }), 200


@bp.route('/update-languages', methods=['POST'])
def update_languages():
    """
    Update user's language preferences.
    Used during onboarding and settings.
    """
    if not current_user.is_authenticated:
        return jsonify({
            'success': False,
            'error': 'Not authenticated'
        }), 401

    try:
        data = request.get_json()
        primary_language_code = data.get('primary_language_code')
        translator_languages = data.get('translator_languages')

        if not primary_language_code:
            return jsonify({
                'success': False,
                'error': 'primary_language_code is required'
            }), 400

        if not translator_languages or not isinstance(translator_languages, list):
            return jsonify({
                'success': False,
                'error': 'translator_languages must be a non-empty array'
            }), 400

        # Import here to avoid circular imports
        from models import db

        # Update user languages
        current_user.primary_language_code = primary_language_code
        current_user.translator_languages = translator_languages

        db.session.commit()

        logger.info(f'Updated languages for user {current_user.email}')

        return jsonify({
            'success': True,
            'user': {
                'id': current_user.id,
                'email': current_user.email,
                'name': current_user.name,
                'primary_language_code': current_user.primary_language_code,
                'translator_languages': current_user.translator_languages,
                'quiz_frequency': current_user.quiz_frequency
            }
        }), 200

    except Exception as e:
        logger.exception(f'Exception updating languages for user {current_user.email}: {str(e)}')
        return jsonify({
            'success': False,
            'error': 'An unexpected error occurred'
        }), 500


@bp.route('/logout', methods=['POST'])
def logout():
    """Log out the current user (API endpoint for frontend)"""
    user_email = current_user.email if current_user.is_authenticated else 'anonymous'
    user_id = current_user.id if current_user.is_authenticated else None

    # End the active session before logging out
    if user_id:
        try:
            active_session = get_active_session(user_id)
            if active_session:
                end_session(active_session.session_id)
                logger.info(f'Ended session {active_session.session_id} for user {user_email}')
        except Exception as session_error:
            logger.warning(f'Failed to end session for user {user_email}: {str(session_error)}')
            # Don't fail logout if session ending fails

    logout_user()

    # Clear the Google OAuth token
    if 'google_oauth_token' in session:
        del session['google_oauth_token']

    logger.info(f'User {user_email} logged out successfully')

    return jsonify({
        'success': True,
        'message': 'Successfully logged out'
    }), 200