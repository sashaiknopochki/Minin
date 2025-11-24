from flask import Blueprint, jsonify
from models.language import Language

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