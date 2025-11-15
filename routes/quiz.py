"""Quiz and learning routes"""

from flask import Blueprint, request, jsonify
from app import db
from models import UserLearningProgress, QuizAttempt, Phrase
from services.quiz_service import QuizService

quiz_bp = Blueprint('quiz', __name__, url_prefix='/api')


@quiz_bp.route('/quiz/next', methods=['GET'])
def get_next_quiz():
    """Get next quiz question"""
    # TODO: Implement next quiz endpoint
    return jsonify({'message': 'Get next quiz endpoint'}), 200


@quiz_bp.route('/quiz/answer', methods=['POST'])
def submit_quiz_answer():
    """Submit quiz answer for validation"""
    # TODO: Implement answer submission and validation
    return jsonify({'message': 'Submit quiz answer endpoint'}), 200


@quiz_bp.route('/progress', methods=['GET'])
def get_progress():
    """Get user's learning statistics"""
    # TODO: Implement progress endpoint
    return jsonify({'message': 'Get progress endpoint'}), 200


@quiz_bp.route('/learned-phrases', methods=['GET'])
def get_learned_phrases():
    """List all learned phrases"""
    # TODO: Implement learned phrases endpoint
    return jsonify({'message': 'Get learned phrases endpoint'}), 200
