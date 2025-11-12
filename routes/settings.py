"""Settings and user preference routes"""

from flask import Blueprint, request, jsonify
from app import db
from models import User, Language

settings_bp = Blueprint('settings', __name__, url_prefix='/api')


@settings_bp.route('/languages', methods=['GET'])
def get_languages():
    """Get available languages"""
    # TODO: Implement get languages endpoint
    return jsonify({'message': 'Get languages endpoint'}), 200


@settings_bp.route('/user/settings', methods=['PUT'])
def update_user_settings():
    """Update user preferences"""
    # TODO: Implement update user settings endpoint
    return jsonify({'message': 'Update user settings endpoint'}), 200


@settings_bp.route('/user/primary-language', methods=['PUT'])
def update_primary_language():
    """Change primary language"""
    # TODO: Implement update primary language endpoint
    return jsonify({'message': 'Update primary language endpoint'}), 200
