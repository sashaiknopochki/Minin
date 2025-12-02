from flask import Flask, jsonify
from flask_login import LoginManager
from flask_cors import CORS
from flask_migrate import Migrate
from config import config
import os


def create_app(config_name=None):
    """Application factory pattern"""
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')

    app = Flask(__name__)
    app.config.from_object(config[config_name])

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
