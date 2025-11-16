from flask import Flask, jsonify
from config import config
import os


def create_app(config_name=None):
    """Application factory pattern"""
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Initialize SQLAlchemy
    from models import db
    db.init_app(app)

    # Import all models to ensure they are registered with SQLAlchemy
    from models.language import Language
    from models.user import User
    from models.phrase import Phrase
    from models.session import Session
    from models.user_searches import UserSearch
    from models.phrase_translation import PhraseTranslation
    from models.user_learning_progress import UserLearningProgress
    from models.quiz_attempt import QuizAttempt

    # Register blueprints
    from routes.auth import bp as auth_bp
    from routes.translation import bp as translation_bp
    from routes.quiz import bp as quiz_bp
    from routes.progress import bp as progress_bp
    from routes.settings import bp as settings_bp

    app.register_blueprint(auth_bp)
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
    app.run(debug=True)
