from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
from models.language import Language
from models.user_searches import UserSearch
from models.phrase import Phrase
from models.user_learning_progress import UserLearningProgress
from models import db
from services.language_utils import get_language_code

bp = Blueprint('api', __name__, url_prefix='/api')


@bp.route('/languages', methods=['GET'])
def get_languages():
    """
    Get all supported languages ordered by display_order.

    Returns:
        JSON array of language objects with code, en_name, original_name, display_order
    """
    try:
        languages = Language.query.order_by(Language.display_order).all()

        languages_data = [{
            'code': lang.code,
            'en_name': lang.en_name,
            'original_name': lang.original_name,
            'display_order': lang.display_order
        } for lang in languages]

        return jsonify({
            'success': True,
            'data': languages_data,
            'count': len(languages_data)
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/history', methods=['GET'])
@login_required
def get_history():
    """
    Get user's search history with phrases and translations.

    Query params:
        - page: Page number (default: 1)
        - language_code: Filter by phrase language (optional, e.g., 'de', 'en')
        - stage: Filter by learning stage (optional: 'all', 'in_progress', 'learned')

    Returns:
        JSON object with searches array containing:
        - id: search ID
        - phrase: {id, text, language_code, phrase_type}
        - translations: {language_code: translation_text}
        - searched_at: ISO timestamp
        And pagination metadata:
        - pagination: {page, per_page, total, pages}
    """
    try:
        if not current_user.is_authenticated:
            return jsonify({
                'success': False,
                'error': 'User not authenticated'
            }), 401

        # Get query params
        page = request.args.get('page', 1, type=int)
        language_code = request.args.get('language_code', None, type=str)
        stage = request.args.get('stage', 'all', type=str)
        per_page = 100

        # Ensure page is at least 1
        page = max(page, 1)

        # Build query with LEFT JOIN to user_learning_progress
        query = (UserSearch.query
                 .filter_by(user_id=current_user.id)
                 .join(Phrase)
                 .outerjoin(UserLearningProgress,
                           db.and_(UserLearningProgress.user_id == current_user.id,
                                  UserLearningProgress.phrase_id == Phrase.id)))

        # Add language filter if provided
        if language_code:
            query = query.filter(Phrase.language_code == language_code)

        # Add stage filter if provided
        if stage == 'in_progress':
            # In progress: no learning progress entry OR stage != 'mastered'
            query = query.filter(
                db.or_(
                    UserLearningProgress.id.is_(None),
                    UserLearningProgress.stage != 'mastered'
                )
            )
        elif stage == 'learned':
            # Learned: stage = 'mastered'
            query = query.filter(UserLearningProgress.stage == 'mastered')
        # 'all' means no additional filter

        # Apply ordering and pagination
        pagination = (query
                      .order_by(UserSearch.searched_at.desc())
                      .paginate(page=page, per_page=per_page, error_out=False))

        # Format response
        searches_data = []
        for search in pagination.items:
            # Get translations from llm_translations_json
            # llm_translations_json has language NAMES as keys: {"English": [["cat", "noun", "..."]], "German": [...]}
            # We need to convert to language CODES with full meanings: {"en": [["cat", "noun", "..."], ["tomcat", "noun", "..."]], "de": [...]}
            translations = {}

            if search.llm_translations_json:
                for lang_name, translation_data in search.llm_translations_json.items():
                    # Convert language name to code
                    lang_code = get_language_code(lang_name)
                    if not lang_code:
                        # Fallback: assume it's already a code if conversion fails
                        lang_code = lang_name

                    # Store all translations for this language
                    if isinstance(translation_data, list) and len(translation_data) > 0:
                        # translation_data is like [["cat", "noun", "a small domesticated carnivorous mammal"], ["tomcat", "noun", "a male cat"]]
                        # We want to preserve all meanings
                        translations[lang_code] = translation_data
                    else:
                        # Fallback: wrap in array format for consistency
                        translations[lang_code] = [[str(translation_data), "", ""]]

            search_item = {
                'id': search.id,
                'phrase': {
                    'id': search.phrase.id,
                    'text': search.phrase.text,
                    'language_code': search.phrase.language_code,
                    'phrase_type': search.phrase.type
                },
                'translations': translations,
                'searched_at': search.searched_at.isoformat() if search.searched_at else None
            }
            searches_data.append(search_item)

        return jsonify({
            'success': True,
            'searches': searches_data,
            'pagination': {
                'page': pagination.page,
                'per_page': pagination.per_page,
                'total': pagination.total,
                'pages': pagination.pages
            }
        }), 200

    except Exception as e:
        print(f"Error fetching history: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/history/<int:search_id>', methods=['DELETE'])
@login_required
def delete_history_item(search_id):
    """
    Delete a specific search history item.

    Args:
        search_id: ID of the search to delete

    Returns:
        JSON object with success status
    """
    try:
        if not current_user.is_authenticated:
            return jsonify({
                'success': False,
                'error': 'User not authenticated'
            }), 401

        # Find the search item
        search = UserSearch.query.filter_by(
            id=search_id,
            user_id=current_user.id
        ).first()

        if not search:
            return jsonify({
                'success': False,
                'error': 'Search not found or does not belong to user'
            }), 404

        # Store phrase_id before deleting the search
        phrase_id = search.phrase_id

        # Delete the search from user_searches
        db.session.delete(search)

        # Also delete the learning progress for this user + phrase
        # (if it exists - it may not exist if user never took a quiz on this phrase)
        learning_progress = UserLearningProgress.query.filter_by(
            user_id=current_user.id,
            phrase_id=phrase_id
        ).first()

        if learning_progress:
            db.session.delete(learning_progress)

        # Commit both deletions
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Search and learning progress deleted successfully'
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"Error deleting history item: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500