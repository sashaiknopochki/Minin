"""
Integration tests for Google OAuth authentication flow.

Tests the complete authentication flow including:
- OAuth callback handling
- User creation with correct default settings
- Login/logout functionality
- Session management
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from unittest.mock import Mock, patch, MagicMock
from flask import session
from app import create_app
from models import db
from models.user import User
from models.language import Language
from datetime import datetime


class TestGoogleOAuth(unittest.TestCase):
    """Test Google OAuth authentication flow"""

    def setUp(self):
        """Set up test client and database"""
        # Create app with test configuration
        self.app = create_app('development')
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test_auth.db'
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.app.config['SECRET_KEY'] = 'test-secret-key'

        # Set mock OAuth credentials (tests don't actually use them)
        os.environ['GOOGLE_CLIENT_ID'] = 'test-client-id'
        os.environ['GOOGLE_CLIENT_SECRET'] = 'test-client-secret'

        self.client = self.app.test_client()

        with self.app.app_context():
            db.create_all()

            # Create test languages
            lang_en = Language(code='en', original_name='English', en_name='English', display_order=1)
            lang_de = Language(code='de', original_name='Deutsch', en_name='German', display_order=2)
            lang_ru = Language(code='ru', original_name='Русский', en_name='Russian', display_order=3)
            db.session.add_all([lang_en, lang_de, lang_ru])
            db.session.commit()

    def tearDown(self):
        """Clean up test database"""
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

        # Remove test database file
        if os.path.exists('instance/test_auth.db'):
            os.remove('instance/test_auth.db')

    def test_google_login_redirect(self):
        """Test that /auth/google redirects to Google OAuth"""
        mock_google = MagicMock()
        mock_google.authorized = False

        with patch('auth.oauth.google', new=mock_google):
            response = self.client.get('/auth/google', follow_redirects=False)

            # Should redirect to Google login
            self.assertEqual(response.status_code, 307)

    def test_google_callback_creates_new_user(self):
        """Test OAuth callback creates new user with correct default settings"""
        # Mock Google OAuth authorization
        mock_google = MagicMock()
        mock_google.authorized = True

        # Mock Google userinfo response
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {
            'id': 'google123',
            'email': 'test@example.com',
            'name': 'Test User'
        }
        mock_google.get.return_value = mock_response

        with patch('auth.oauth.google', new=mock_google):
            with self.app.app_context():
                # Call the callback endpoint
                response = self.client.get('/auth/google/callback', follow_redirects=True)

                # Should redirect to home with success message
                self.assertEqual(response.status_code, 200)

                # Verify user was created
                user = User.query.filter_by(email='test@example.com').first()
                self.assertIsNotNone(user)
                self.assertEqual(user.google_id, 'google123')
                self.assertEqual(user.name, 'Test User')

                # ✅ Test default Russian primary language
                self.assertEqual(user.primary_language_code, 'ru')

                # ✅ Test default languages order: de, en, ru
                self.assertEqual(user.translator_languages, ['de', 'en', 'ru'])

                # Test other defaults
                self.assertEqual(user.quiz_frequency, 5)
                self.assertTrue(user.quiz_mode_enabled)
                self.assertEqual(user.searches_since_last_quiz, 0)
                self.assertIsNotNone(user.last_active_at)

    def test_google_callback_updates_existing_user(self):
        """Test OAuth callback updates last_active_at for existing users"""
        # Create existing user
        with self.app.app_context():
            old_time = datetime(2024, 1, 1)
            user = User(
                google_id='google456',
                email='existing@example.com',
                name='Existing User',
                primary_language_code='en',
                translator_languages=['en'],
                last_active_at=old_time
            )
            db.session.add(user)
            db.session.commit()
            user_id = user.id

        # Mock Google OAuth
        mock_google = MagicMock()
        mock_google.authorized = True
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {
            'id': 'google456',
            'email': 'existing@example.com',
            'name': 'Existing User'
        }
        mock_google.get.return_value = mock_response

        with patch('auth.oauth.google', new=mock_google):
            with self.app.app_context():
                response = self.client.get('/auth/google/callback', follow_redirects=True)

                self.assertEqual(response.status_code, 200)

                # Verify user was updated
                user = User.query.get(user_id)
                self.assertIsNotNone(user)

                # Last active should be updated (not the old time)
                self.assertNotEqual(user.last_active_at, old_time)

                # Original settings should be preserved
                self.assertEqual(user.primary_language_code, 'en')
                self.assertEqual(user.translator_languages, ['en'])

    def test_google_callback_handles_unauthorized(self):
        """Test OAuth callback handles unauthorized state"""
        mock_google = MagicMock()
        mock_google.authorized = False

        with patch('auth.oauth.google', new=mock_google):
            response = self.client.get('/auth/google/callback', follow_redirects=True)

            # Should redirect to home
            self.assertEqual(response.status_code, 200)

            # No user should be created
            with self.app.app_context():
                user_count = User.query.count()
                self.assertEqual(user_count, 0)

    def test_google_callback_handles_missing_user_info(self):
        """Test OAuth callback handles incomplete user info from Google"""
        mock_google = MagicMock()
        mock_google.authorized = True

        # Mock incomplete response (missing email)
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {
            'id': 'google789',
            'name': 'Test User'
            # Missing email
        }
        mock_google.get.return_value = mock_response

        with patch('auth.oauth.google', new=mock_google):
            response = self.client.get('/auth/google/callback', follow_redirects=True)

            # Should redirect to home with error
            self.assertEqual(response.status_code, 200)

            # No user should be created
            with self.app.app_context():
                user_count = User.query.count()
                self.assertEqual(user_count, 0)

    def test_google_callback_handles_api_error(self):
        """Test OAuth callback handles Google API errors"""
        mock_google = MagicMock()
        mock_google.authorized = True

        # Mock failed API response
        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 500
        mock_google.get.return_value = mock_response

        with patch('auth.oauth.google', new=mock_google):
            response = self.client.get('/auth/google/callback', follow_redirects=True)

            # Should redirect to home with error
            self.assertEqual(response.status_code, 200)

            # No user should be created
            with self.app.app_context():
                user_count = User.query.count()
                self.assertEqual(user_count, 0)

    def test_logout_clears_session(self):
        """Test logout clears user session and OAuth token"""
        # First login a user
        mock_google = MagicMock()
        mock_google.authorized = True
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {
            'id': 'google999',
            'email': 'logout@example.com',
            'name': 'Logout Test'
        }
        mock_google.get.return_value = mock_response

        with patch('auth.oauth.google', new=mock_google):
            with self.client:
                # Login
                self.client.get('/auth/google/callback')

                # Verify user is logged in
                with self.app.app_context():
                    from flask_login import current_user
                    self.assertTrue(current_user.is_authenticated)

                # Logout
                response = self.client.get('/auth/logout', follow_redirects=True)

                self.assertEqual(response.status_code, 200)

                # Verify user is logged out
                with self.app.app_context():
                    from flask_login import current_user
                    self.assertFalse(current_user.is_authenticated)

    def test_user_model_has_flask_login_methods(self):
        """Test User model has required Flask-Login methods"""
        with self.app.app_context():
            user = User(
                google_id='test',
                email='test@example.com',
                primary_language_code='ru',
                translator_languages=['de', 'en', 'ru']
            )

            # Test UserMixin methods exist
            self.assertTrue(hasattr(user, 'is_authenticated'))
            self.assertTrue(hasattr(user, 'is_active'))
            self.assertTrue(hasattr(user, 'is_anonymous'))
            self.assertTrue(hasattr(user, 'get_id'))


if __name__ == '__main__':
    print("=" * 70)
    print("Running Google OAuth Integration Tests")
    print("=" * 70)
    print("\nNote: These tests mock Google OAuth responses.")
    print("No real Google credentials are needed for testing.\n")
    print("=" * 70)

    # Run tests with verbose output
    unittest.main(verbosity=2)