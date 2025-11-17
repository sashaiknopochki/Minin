from flask import Blueprint, redirect, url_for, flash, session
from flask_dance.contrib.google import make_google_blueprint, google
from flask_login import login_user, logout_user, current_user
import os
import logging

# Set up logging
logger = logging.getLogger(__name__)

# Create OAuth blueprint
bp = Blueprint('auth', __name__, url_prefix='/auth')

# Create Google OAuth blueprint
google_bp = make_google_blueprint(
    client_id=os.getenv('GOOGLE_CLIENT_ID'),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
    scope=['openid', 'https://www.googleapis.com/auth/userinfo.email', 'https://www.googleapis.com/auth/userinfo.profile'],
    redirect_url='/auth/google/callback'
)


@bp.route('/google')
def google_login():
    """Redirect to Google OAuth login"""
    if not google.authorized:
        # 307 Temporary Redirect - maintains POST method if used
        return redirect(url_for('google.login'), code=307)
    # Already authorized, go to callback
    return redirect(url_for('auth.google_callback'), code=302)


@bp.route('/google/callback')
def google_callback():
    """Handle Google OAuth callback"""
    if not google.authorized:
        logger.warning('OAuth callback received but user not authorized')
        flash('Failed to log in with Google. Please try again.', 'error')
        # 401 Unauthorized
        return redirect(url_for('home'), code=302)

    # Get user info from Google
    try:
        resp = google.get('/oauth2/v2/userinfo')

        if not resp.ok:
            logger.error(f'Failed to fetch user info from Google. Status: {resp.status_code}')
            flash('Failed to fetch user info from Google. Please try again.', 'error')
            # 401 Unauthorized - couldn't get user info
            return redirect(url_for('home'), code=302)

        google_info = resp.json()
        google_id = google_info.get('id')
        email = google_info.get('email')
        name = google_info.get('name', '')

        if not google_id or not email:
            logger.error('Incomplete user info received from Google')
            flash('Failed to retrieve complete user information from Google.', 'error')
            # 400 Bad Request - incomplete data
            return redirect(url_for('home'), code=302)

        # Import here to avoid circular imports
        from auth.utils import get_or_create_user

        # Get or create user
        user = get_or_create_user(google_id, email, name)

        if not user:
            logger.error(f'Failed to create/retrieve user for google_id: {google_id}')
            flash('Failed to create user account. Please contact support.', 'error')
            # 500 Internal Server Error - database issue
            return redirect(url_for('home'), code=302)

        # Log in the user
        login_user(user)
        logger.info(f'User {email} logged in successfully')
        flash('Successfully logged in!', 'success')

        # 302 Found - standard redirect after successful login
        return redirect(url_for('home'), code=302)

    except Exception as e:
        logger.exception(f'Exception during Google OAuth callback: {str(e)}')
        flash('An unexpected error occurred during login. Please try again.', 'error')
        # 500 Internal Server Error
        return redirect(url_for('home'), code=302)


@bp.route('/logout')
def logout():
    """Log out the current user"""
    user_email = current_user.email if current_user.is_authenticated else 'anonymous'

    logout_user()

    # Clear the Google OAuth token
    if 'google_oauth_token' in session:
        del session['google_oauth_token']

    logger.info(f'User {user_email} logged out successfully')
    flash('Successfully logged out.', 'success')

    # 302 Found - standard redirect after logout
    return redirect(url_for('home'), code=302)