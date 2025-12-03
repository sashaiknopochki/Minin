from flask import Flask, jsonify
from flask_login import LoginManager
from flask_cors import CORS
from flask_migrate import Migrate
from config import config
import os
import logging
from logging.handlers import RotatingFileHandler


def configure_logging(app):
    """
    Configure application logging with file rotation and console output.

    Sets up two handlers:
    1. File handler: Writes to logs/minin.log with 10MB rotation
    2. Console handler: Always writes to stdout (visible in terminal)

    Log levels:
    - Development: DEBUG (all messages)
    - Production: INFO (info, warning, error)

    Features:
    - Automatic log file rotation (keeps last 10 files)
    - Timestamps and source location in logs
    - Color-coded console output in development
    """
    # Create logs directory if it doesn't exist
    if not os.path.exists('logs'):
        os.makedirs('logs')

    # Configure log format with timestamp, level, and location
    file_formatter = logging.Formatter(
        '%(asctime)s %(levelname)-8s [%(name)s:%(lineno)d] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    console_formatter = logging.Formatter(
        '%(levelname)-8s [%(name)s] %(message)s'
    )

    # File handler with rotation (10MB max, keep 10 backup files)
    file_handler = RotatingFileHandler(
        'logs/minin.log',
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=10,
        encoding='utf-8'
    )
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(logging.DEBUG)  # Log everything to file

    # Console handler (always enabled, even in production)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)

    # Set log level based on environment
    if app.debug:
        # Development: show DEBUG and above in console and file
        console_handler.setLevel(logging.DEBUG)
        app.logger.setLevel(logging.DEBUG)
        app.logger.info("Logging configured for DEVELOPMENT mode (DEBUG level)")
    else:
        # Production: show INFO and above in console, DEBUG in file
        console_handler.setLevel(logging.INFO)
        app.logger.setLevel(logging.INFO)
        app.logger.info("Logging configured for PRODUCTION mode (INFO level)")

    # Remove default handlers to avoid duplicate logs
    app.logger.handlers.clear()

    # Add our handlers
    app.logger.addHandler(file_handler)
    app.logger.addHandler(console_handler)

    # Also configure root logger for service modules
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if app.debug else logging.INFO)
    root_logger.handlers.clear()
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    # Log startup message
    app.logger.info("=" * 60)
    app.logger.info(f"Minin Application Starting")
    app.logger.info(f"Environment: {os.getenv('FLASK_ENV', 'development')}")
    app.logger.info(f"Log file: {os.path.abspath('logs/minin.log')}")
    app.logger.info("=" * 60)


def create_app(config_name=None):
    """Application factory pattern"""
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Configure logging (must be done early)
    configure_logging(app)

    # Initialize CORS for React frontend
    CORS(app, resources={
        r"/api/*": {"origins": ["http://localhost:5173"]},
        r"/auth/*": {"origins": ["http://localhost:5173"]},
        r"/translation/*": {"origins": ["http://localhost:5173"]},
        r"/quiz/*": {"origins": ["http://localhost:5173"]},
        r"/progress/*": {"origins": ["http://localhost:5173"]},
        r"/settings/*": {"origins": ["http://localhost:5173"]}
    }, supports_credentials=True)

    # Initialize SQLAlchemy
    from models import db
    db.init_app(app)

    # Initialize Flask-Migrate
    migrate = Migrate(app, db)

    # Initialize Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.google_login'

    # Import all models to ensure they are registered with SQLAlchemy
    from models.language import Language
    from models.user import User
    from models.phrase import Phrase
    from models.session import Session
    from models.user_searches import UserSearch
    from models.phrase_translation import PhraseTranslation
    from models.user_learning_progress import UserLearningProgress
    from models.quiz_attempt import QuizAttempt

    # User loader callback for Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register OAuth blueprints
    from auth.oauth import bp as oauth_bp, google_bp
    app.register_blueprint(oauth_bp)
    app.register_blueprint(google_bp, url_prefix='/login')

    # Register API blueprints
    from routes.api import bp as api_bp
    from routes.translation import bp as translation_bp
    from routes.quiz import bp as quiz_bp
    from routes.progress import bp as progress_bp
    from routes.settings import bp as settings_bp

    app.register_blueprint(api_bp)
    app.register_blueprint(translation_bp)
    app.register_blueprint(quiz_bp)
    app.register_blueprint(progress_bp)
    app.register_blueprint(settings_bp)

    # Home route
    @app.route('/')
    def home():
        return jsonify({
            'message': 'Welcome to Minin App!',
            'version': '1.0.0'
        })

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5001)
