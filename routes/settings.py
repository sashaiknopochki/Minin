from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user, logout_user
from models import db
from models.user import User
from models.session import Session
from models.user_searches import UserSearch
from models.user_learning_progress import UserLearningProgress
from models.quiz_attempt import QuizAttempt
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('settings', __name__, url_prefix='/settings')


@bp.route('/test')
def test():
    return jsonify({'message': 'Settings blueprint working'})


@bp.route('/quiz-frequency', methods=['PATCH'])
@login_required
def update_quiz_frequency():
    """
    Update the user's quiz frequency setting.

    This controls how often quizzes appear during word searches.

    Request Body:
        {
            "quiz_frequency": int (1, 3, 5, or 10)
        }

    Returns:
        JSON response with success status and updated value
    """
    try:
        data = request.get_json()

        if not data or 'quiz_frequency' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing quiz_frequency in request body'
            }), 400

        quiz_frequency = data['quiz_frequency']

        # Validate the value
        valid_values = [1, 3, 5, 10]
        if quiz_frequency not in valid_values:
            return jsonify({
                'success': False,
                'error': f'Invalid quiz_frequency. Must be one of: {valid_values}'
            }), 400

        # Update the user's quiz_frequency
        current_user.quiz_frequency = quiz_frequency
        db.session.commit()

        logger.info(f'Updated quiz_frequency to {quiz_frequency} for user {current_user.email}')

        return jsonify({
            'success': True,
            'quiz_frequency': quiz_frequency
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.exception(f'Error updating quiz_frequency for user {current_user.email}: {str(e)}')
        return jsonify({
            'success': False,
            'error': 'Failed to update quiz frequency. Please try again.'
        }), 500


@bp.route('/account', methods=['DELETE'])
@login_required
def delete_account():
    """
    Delete the current user's account and all associated data.

    This endpoint permanently removes:
    - All quiz attempts
    - All learning progress
    - All search history
    - All sessions
    - The user account itself

    Returns:
        JSON response with success status
    """
    try:
        user_id = current_user.id
        user_email = current_user.email

        logger.info(f'Starting account deletion for user {user_email} (ID: {user_id})')

        # Delete all related records in order (respecting foreign key constraints)
        # 1. Delete quiz attempts
        quiz_attempts_count = QuizAttempt.query.filter_by(user_id=user_id).delete()
        logger.info(f'Deleted {quiz_attempts_count} quiz attempts for user {user_email}')

        # 2. Delete learning progress
        learning_progress_count = UserLearningProgress.query.filter_by(user_id=user_id).delete()
        logger.info(f'Deleted {learning_progress_count} learning progress records for user {user_email}')

        # 3. Delete search history
        searches_count = UserSearch.query.filter_by(user_id=user_id).delete()
        logger.info(f'Deleted {searches_count} search records for user {user_email}')

        # 4. Delete sessions
        sessions_count = Session.query.filter_by(user_id=user_id).delete()
        logger.info(f'Deleted {sessions_count} sessions for user {user_email}')

        # 5. Delete the user account
        user = User.query.get(user_id)
        if user:
            db.session.delete(user)
            logger.info(f'Deleted user account for {user_email}')

        # Commit all deletions
        db.session.commit()

        # Log out the user
        logout_user()
        logger.info(f'User {user_email} logged out after account deletion')

        return jsonify({
            'success': True,
            'message': 'Account deleted successfully'
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.exception(f'Error deleting account for user {current_user.email}: {str(e)}')
        return jsonify({
            'success': False,
            'error': 'Failed to delete account. Please try again later.'
        }), 500