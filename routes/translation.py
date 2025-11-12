"""Translation API routes"""

from flask import Blueprint, request, jsonify
from app import db
from models import UserSearch, Phrase, Language
from services.llm_service import LLMService

translation_bp = Blueprint('translation', __name__, url_prefix='/api')


@translation_bp.route('/translate', methods=['POST'])
def translate():
    """Translate word/phrase to multiple languages"""
    # TODO: Implement translation endpoint
    return jsonify({'message': 'Translation endpoint'}), 200


@translation_bp.route('/search-history', methods=['GET'])
def search_history():
    """Retrieve user's search history"""
    # TODO: Implement search history retrieval
    return jsonify({'message': 'Search history endpoint'}), 200


@translation_bp.route('/phrases/<int:phrase_id>', methods=['DELETE'])
def delete_phrase(phrase_id):
    """Delete a phrase from history"""
    # TODO: Implement phrase deletion
    return jsonify({'message': f'Delete phrase {phrase_id} endpoint'}), 200
