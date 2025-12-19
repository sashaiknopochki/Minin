"""
Test script to verify session cookie configuration for cross-domain authentication.
This helps debug the issue where language settings aren't persisting for new users.
"""
import os
import sys
from app import create_app

def test_session_configuration():
    """Test that session cookies are configured correctly for production"""
    
    # Test production configuration
    os.environ['FLASK_ENV'] = 'production'
    app = create_app('production')
    
    print("=" * 60)
    print("PRODUCTION SESSION CONFIGURATION TEST")
    print("=" * 60)
    
    checks = []
    
    # Check SESSION_COOKIE_SECURE
    if app.config.get('SESSION_COOKIE_SECURE'):
        print("✓ SESSION_COOKIE_SECURE: True (cookies only sent over HTTPS)")
        checks.append(True)
    else:
        print("✗ SESSION_COOKIE_SECURE: False (SHOULD BE TRUE IN PRODUCTION)")
        checks.append(False)
    
    # Check SESSION_COOKIE_HTTPONLY
    if app.config.get('SESSION_COOKIE_HTTPONLY'):
        print("✓ SESSION_COOKIE_HTTPONLY: True (prevents JavaScript access)")
        checks.append(True)
    else:
        print("✗ SESSION_COOKIE_HTTPONLY: False (SHOULD BE TRUE)")
        checks.append(False)
    
    # Check SESSION_COOKIE_SAMESITE
    samesite = app.config.get('SESSION_COOKIE_SAMESITE')
    if samesite == 'None':
        print("✓ SESSION_COOKIE_SAMESITE: None (allows cross-domain cookies)")
        checks.append(True)
    else:
        print(f"✗ SESSION_COOKIE_SAMESITE: {samesite} (SHOULD BE 'None' FOR CROSS-DOMAIN)")
        checks.append(False)
    
    # Check REMEMBER_COOKIE settings
    if app.config.get('REMEMBER_COOKIE_SECURE'):
        print("✓ REMEMBER_COOKIE_SECURE: True")
        checks.append(True)
    else:
        print("✗ REMEMBER_COOKIE_SECURE: False (SHOULD BE TRUE IN PRODUCTION)")
        checks.append(False)
    
    remember_samesite = app.config.get('REMEMBER_COOKIE_SAMESITE')
    if remember_samesite == 'None':
        print("✓ REMEMBER_COOKIE_SAMESITE: None (allows cross-domain cookies)")
        checks.append(True)
    else:
        print(f"✗ REMEMBER_COOKIE_SAMESITE: {remember_samesite} (SHOULD BE 'None')")
        checks.append(False)
    
    # Check SECRET_KEY is set
    secret_key = app.config.get('SECRET_KEY')
    if secret_key and secret_key != 'dev-secret-key-change-in-production':
        print("✓ SECRET_KEY: Set to production value")
        checks.append(True)
    else:
        print("✗ SECRET_KEY: Using default or not set (MUST BE SET IN PRODUCTION)")
        checks.append(False)
    
    print("=" * 60)
    
    if all(checks):
        print("✓ ALL CHECKS PASSED - Configuration looks good!")
        return 0
    else:
        print(f"✗ {sum(not c for c in checks)} CHECKS FAILED - Review configuration")
        return 1

if __name__ == '__main__':
    sys.exit(test_session_configuration())
