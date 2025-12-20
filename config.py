import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base configuration class"""

    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    FLASK_ENV = os.getenv("FLASK_ENV", "development")
    DEBUG = os.getenv("DEBUG", "True") == "True"

    # SQLAlchemy configuration
    # SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URI', 'sqlite:///database.db')
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URI")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Session security
    SESSION_COOKIE_HTTPONLY = True  # Prevent JavaScript access to session cookie
    SESSION_COOKIE_SAMESITE = "Lax"  # Protect against CSRF (development default)

    # For production cross-domain setup, override with environment variable
    # This allows setting SameSite=None for cross-domain cookies
    if os.getenv("SESSION_COOKIE_SAMESITE"):
        SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE")


class DevelopmentConfig(Config):
    """Development environment configuration"""

    DEBUG = True
    SESSION_COOKIE_SECURE = False  # Allow HTTP in development


class ProductionConfig(Config):
    """Production environment configuration"""

    DEBUG = False
    SESSION_COOKIE_SECURE = True  # Require HTTPS in production

    # For cross-domain authentication (Vercel frontend -> GCP backend):
    # - Must use SameSite=None to allow cookies across different domains
    # - Requires Secure=True (HTTPS only) when using SameSite=None
    SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "None")

    # Don't set SESSION_COOKIE_DOMAIN for cross-domain setup
    # The cookie will be tied to the backend domain (GCP) only
    # Frontend must use credentials: 'include' in all fetch requests

    # Flask-Login specific cookie settings
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SECURE = True
    REMEMBER_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "None")
    REMEMBER_COOKIE_DURATION = 2592000  # 30 days in seconds
    REMEMBER_COOKIE_PATH = "/"  # Make cookie available for all paths

    # Also ensure session cookie has correct path
    SESSION_COOKIE_PATH = "/"

    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_size": 20,
        "max_overflow": 10,  # Can temporarily create 5 extra connections
        "pool_recycle": 3600,
        "pool_pre_ping": True,
    }


class TestingConfig(Config):
    """Testing environment configuration"""

    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SESSION_COOKIE_SECURE = False


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
