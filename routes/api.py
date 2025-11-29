from flask import Blueprint, jsonify
from flask_login import current_user, login_required
from models.language import Language
from models.user_searches import UserSearch
from models.phrase import Phrase
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

    Returns:
        JSON object with searches array containing:
        - id: search ID
        - phrase: {id, text, language_code, phrase_type}
        - translations: {language_code: translation_text}
        - searched_at: ISO timestamp
    """
    try:
        if not current_user.is_authenticated:
            return jsonify({
                'success': False,
                'error': 'User not authenticated'
            }), 401

        # Query user searches with phrase join, ordered by most recent first
        searches = (UserSearch.query
                    .filter_by(user_id=current_user.id)
                    .join(Phrase)
                    .order_by(UserSearch.searched_at.desc())
                    .limit(200)
                    .all())

        # Format response
        searches_data = []
        for search in searches:
            # Get translations from llm_translations_json
            # llm_translations_json has language NAMES as keys: {"English": [["cat", "noun", "..."]], "German": [...]}
            # We need to convert to language CODES: {"en": "cat", "de": "Katze"}
            translations = {}

            if search.llm_translations_json:
                for lang_name, translation_data in search.llm_translations_json.items():
                    # Convert language name to code
                    lang_code = get_language_code(lang_name)
                    if not lang_code:
                        # Fallback: assume it's already a code if conversion fails
                        lang_code = lang_name

                    # Extract just the first translation word
                    if isinstance(translation_data, list) and len(translation_data) > 0:
                        # translation_data is like [["cat", "noun", "a small domesticated carnivorous mammal"]]
                        # We want just the first word
                        if isinstance(translation_data[0], list) and len(translation_data[0]) > 0:
                            translations[lang_code] = translation_data[0][0]
                        else:
                            translations[lang_code] = str(translation_data[0])
                    else:
                        translations[lang_code] = str(translation_data)

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
            'total': len(searches_data)
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

        # Delete the search
        db.session.delete(search)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Search deleted successfully'
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"Error deleting history item: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500