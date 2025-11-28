from flask import Blueprint, jsonify, request
from flask_login import current_user
from services.llm_translation_service import translate_text, GPT_4_1_MINI
from services.user_search_service import log_user_search
from services.session_service import get_or_create_session
from services.language_utils import get_language_code
from services.phrase_translation_service import get_or_create_translations
from services.learning_progress_service import initialize_learning_progress_on_search

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

        # Convert language names to codes
        source_language_code = get_language_code(source_language)
        if not source_language_code:
            return jsonify({
                'success': False,
                'error': f'Unsupported source language: {source_language}'
            }), 400

        target_language_codes = []
        for target_lang in target_languages:
            code = get_language_code(target_lang)
            if not code:
                return jsonify({
                    'success': False,
                    'error': f'Unsupported target language: {target_lang}'
                }), 400
            target_language_codes.append(code)

        # Call translation service with caching
        result = get_or_create_translations(
            text=text,
            source_language=source_language,
            source_language_code=source_language_code,
            target_languages=target_languages,
            target_language_codes=target_language_codes,
            model=model,
            native_language=native_language
        )

        # Log the search to database if user is authenticated and translation succeeded
        if current_user.is_authenticated and result.get('success'):
            try:
                # Get or create session for this user
                session = get_or_create_session(current_user.id)

                # Log the search - convert result to format expected by log_user_search
                llm_response = {
                    'success': result['success'],
                    'translations': result.get('translations', {}),
                    'source_info': result.get('source_info', [text, '', '']),
                    'model': result.get('model', model),
                    'usage': result.get('usage', {})
                }

                context_sentence = data.get('context_sentence')  # Optional context
                user_search = log_user_search(
                    user_id=current_user.id,
                    phrase_text=text,
                    source_language_code=source_language_code,
                    llm_response=llm_response,
                    session_id=session.session_id,
                    context_sentence=context_sentence
                )

                # Initialize learning progress if this is the user's first search for this phrase
                if user_search:
                    try:
                        # Get the phrase from the user_search to check if it's quizzable
                        phrase = user_search.phrase
                        initialize_learning_progress_on_search(
                            user_id=current_user.id,
                            phrase_id=user_search.phrase_id,
                            is_quizzable=phrase.is_quizzable
                        )
                    except Exception as progress_error:
                        # Log error but don't fail the request
                        print(f"Failed to initialize learning progress: {str(progress_error)}")

            except Exception as e:
                # Log error but don't fail the request
                print(f"Failed to log user search: {str(e)}")

        # Return result with appropriate status code
        status_code = 200 if result['success'] else 500
        return jsonify(result), status_code

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500
