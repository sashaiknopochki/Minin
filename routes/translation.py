from flask import Blueprint, jsonify, request
from services.llm_translation_service import translate_text, GPT_4_1_MINI

bp = Blueprint('translation', __name__, url_prefix='/translation')


@bp.route('/test')
def test():
    return jsonify({'message': 'Translation blueprint working'})


@bp.route('/translate', methods=['POST'])
def translate():
    """
    Translate text from source language to multiple target languages.

    Request body:
    {
        "text": "собака",
        "source_language": "Russian",
        "target_languages": ["English", "German"],
        "native_language": "Russian",  // optional, defaults to "English"
        "model": "gpt-4.1-mini"  // optional, defaults to GPT_4_1_MINI
    }

    Response:
    {
        "success": true,
        "original_text": "собака",
        "source_language": "Russian",
        "target_languages": ["English", "German"],
        "native_language": "Russian",
        "translations": {
            "English": [["dog", "(домашнее животное)"]],
            "German": [["Hund", "(домашнее животное)"]]
        },
        "model": "gpt-4.1-mini",
        "usage": {
            "prompt_tokens": 150,
            "completion_tokens": 50,
            "total_tokens": 200
        }
    }
    """
    try:
        data = request.get_json()

        # Validate required fields
        if not data:
            return jsonify({
                'success': False,
                'error': 'No JSON data provided'
            }), 400

        text = data.get('text')
        source_language = data.get('source_language')
        target_languages = data.get('target_languages')

        if not text:
            return jsonify({
                'success': False,
                'error': 'Missing required field: text'
            }), 400

        if not source_language:
            return jsonify({
                'success': False,
                'error': 'Missing required field: source_language'
            }), 400

        if not target_languages or not isinstance(target_languages, list):
            return jsonify({
                'success': False,
                'error': 'Missing or invalid field: target_languages (must be a list)'
            }), 400

        # Optional fields
        native_language = data.get('native_language', 'English')
        model = data.get('model', GPT_4_1_MINI)

        # Call translation service
        result = translate_text(
            text=text,
            source_language=source_language,
            target_languages=target_languages,
            model=model,
            native_language=native_language
        )

        # Return result with appropriate status code
        status_code = 200 if result['success'] else 500
        return jsonify(result), status_code

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500
