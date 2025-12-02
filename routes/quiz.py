"""
Quiz Routes - Endpoints for quiz interaction.

This module provides API endpoints for the quiz system including:
- GET /api/quiz/next - Retrieve next quiz question
- POST /api/quiz/answer - Submit and evaluate quiz answer
- POST /api/quiz/skip - Skip current quiz without penalty
"""

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user

from models import db
from models.user_learning_progress import UserLearningProgress
from services.quiz_attempt_service import QuizAttemptService
from services.question_generation_service import QuestionGenerationService
from services.answer_evaluation_service import AnswerEvaluationService
from services.learning_progress_service import update_after_quiz
from services.quiz_trigger_service import QuizTriggerService

bp = Blueprint('quiz', __name__, url_prefix='/quiz')


@bp.route('/test')
def test():
    return jsonify({'message': 'Quiz blueprint working'})


@bp.route('/next', methods=['GET'])
@login_required
def get_next_quiz():
    """
    Get next quiz question.

    This endpoint retrieves or generates a quiz question for the user. It can
    be called in two modes:
    1. Auto-triggered mode: Frontend provides phrase_id from translation response
    2. Manual practice mode: System selects a phrase due for review

    Query Parameters:
        phrase_id (int, optional): Specific phrase to quiz (from auto-trigger)

    Returns:
        200: Quiz question data
            {
                "quiz_attempt_id": 123,
                "question": "What is the English translation of 'Katze'?",
                "options": ["cat", "dog", "house", "tree"],
                "question_type": "multiple_choice_target",
                "phrase_id": 456
            }
        404: No phrases available for review
            {
                "error": "No phrases due for review"
            }
        500: Server error
            {
                "error": "Error message"
            }

    Implementation Notes:
        - Resets searches_since_last_quiz counter to 0
        - Creates QuizAttempt record
        - Generates question via LLM
        - Commits all changes to database
    """
    try:
        phrase_id = request.args.get('phrase_id', type=int)

        if phrase_id:
            # Auto-triggered quiz for specific phrase
            progress = UserLearningProgress.query.filter_by(
                user_id=current_user.id,
                phrase_id=phrase_id
            ).first()
        else:
            # Manual practice mode - select phrase due for review
            progress = QuizTriggerService.get_phrase_for_quiz(current_user)

        if not progress:
            return jsonify({'error': 'No phrases due for review'}), 404

        # Create quiz attempt
        quiz_attempt = QuizAttemptService.create_quiz_attempt(
            user_id=current_user.id,
            phrase_id=progress.phrase_id
        )

        # Generate question
        question_data = QuestionGenerationService.generate_question(quiz_attempt)

        # Reset search counter
        current_user.searches_since_last_quiz = 0
        db.session.commit()

        return jsonify({
            'quiz_attempt_id': quiz_attempt.id,
            'question': question_data['question'],
            'options': question_data.get('options'),  # null for text input
            'question_type': quiz_attempt.question_type,
            'phrase_id': progress.phrase_id
        })

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Server error: {str(e)}'}), 500


@bp.route('/answer', methods=['POST'])
@login_required
def submit_quiz_answer():
    """
    Submit quiz answer and get evaluation.

    This endpoint evaluates the user's answer, updates the quiz attempt record,
    and updates the user's learning progress based on the result.

    Request Body:
        {
            "quiz_attempt_id": 123,
            "user_answer": "cat"
        }

    Returns:
        200: Evaluation result
            {
                "was_correct": true,
                "correct_answer": "cat",
                "explanation": "Correct!",
                "stage_advanced": false,
                "new_stage": "basic",
                "next_review_date": "2024-12-03"
            }
        400: Missing required fields or validation error
            {
                "error": "Missing required fields"
            }
        500: Server error
            {
                "error": "Error message"
            }

    Implementation Notes:
        - Evaluates answer using AnswerEvaluationService
        - Updates learning progress using LearningProgressService
        - Updates spaced repetition scheduling
        - May advance user to next learning stage
        - Returns null for next_review_date if phrase is mastered
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400

        quiz_attempt_id = data.get('quiz_attempt_id')
        user_answer = data.get('user_answer')

        if not quiz_attempt_id or user_answer is None:
            return jsonify({'error': 'Missing required fields'}), 400

        # Evaluate answer
        evaluation = AnswerEvaluationService.evaluate_answer(
            quiz_attempt_id=quiz_attempt_id,
            user_answer=user_answer
        )

        # Update learning progress
        progress_update = update_after_quiz(quiz_attempt_id)

        return jsonify({
            'was_correct': evaluation['was_correct'],
            'correct_answer': evaluation['correct_answer'],
            'explanation': evaluation['explanation'],
            'stage_advanced': progress_update['stage_advanced'],
            'new_stage': progress_update['new_stage'],
            'next_review_date': progress_update['next_review_date'].isoformat() if progress_update['next_review_date'] else None
        })

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Server error: {str(e)}'}), 500


@bp.route('/skip', methods=['POST'])
@login_required
def skip_quiz():
    """
    Skip current quiz without penalty.

    This endpoint allows users to skip a quiz question without affecting their
    learning progress or search counter. The phrase will appear again after
    the next quiz_frequency searches.

    Request Body:
        {
            "phrase_id": 456
        }

    Returns:
        200: Skip confirmation
            {
                "success": true,
                "message": "Quiz skipped",
                "phrase_id": 456
            }
        400: Missing required fields
            {
                "error": "Missing required field: phrase_id"
            }
        500: Server error
            {
                "error": "Error message"
            }

    Implementation Notes:
        - Does NOT reset searches_since_last_quiz counter
        - Does NOT update learning progress
        - Does NOT create quiz attempt record
        - Phrase remains eligible for future quizzes
        - No penalty applied to learning metrics
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400

        phrase_id = data.get('phrase_id')

        if not phrase_id:
            return jsonify({'error': 'Missing required field: phrase_id'}), 400

        # Just return success - no database changes needed
        # The phrase will appear again after next quiz_frequency searches
        return jsonify({
            'success': True,
            'message': 'Quiz skipped',
            'phrase_id': phrase_id
        })

    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500