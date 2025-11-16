from flask import Flask, jsonify
from config import config
import os


def create_app(config_name=None):
    """Application factory pattern"""
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')

    app = Flask(__name__)
    app.config.from_object(config[config_name])

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
