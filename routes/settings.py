from flask import Blueprint, jsonify
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