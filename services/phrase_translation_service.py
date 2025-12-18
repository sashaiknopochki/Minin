"""
Phrase Translation Service - Manages cached translations with LLM fallback

This service implements the multi-target-language caching strategy:
1. Check if phrase exists (create if not)
2. For each target language, check phrase_translations cache
3. Return cached translations instantly
4. Call LLM only for missing translations
5. Cache new translations for future requests
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from decimal import Decimal
from models import db
from models.phrase import Phrase
from models.phrase_translation import PhraseTranslation
from services.llm_translation_service import translate_text
from services.session_cost_aggregator import add_translation_cost

logger = logging.getLogger(__name__)

# Maximum character length for a phrase to be quizzable
MAX_QUIZZABLE_LENGTH = 48


def get_or_create_phrase(
    text: str,
    language_code: str,
    phrase_type: str = 'word'
) -> Optional[Phrase]:
    """
    Get existing phrase or create a new one.

    Args:
        text: The phrase text (will be normalized to lowercase and stripped)
        language_code: ISO 639-1 language code (e.g., 'de', 'en')
        phrase_type: Type of phrase (default: 'word')

    Returns:
        Phrase object or None if creation failed
    """
    try:
        # The Phrase model validator normalizes text (strip + lowercase)
        normalized_text = text.strip().lower()

        # Try to find existing phrase
        phrase = Phrase.query.filter_by(
            text=normalized_text,
            language_code=language_code
        ).first()

        if phrase:
            logger.debug(f"Found existing phrase: {phrase.id} - '{text}' ({language_code})")
            return phrase

        # Create new phrase
        is_quizzable = len(text.strip()) <= MAX_QUIZZABLE_LENGTH

        phrase = Phrase(
            text=text,
            language_code=language_code,
            type=phrase_type,
            is_quizzable=is_quizzable,
            search_count=0
        )

        db.session.add(phrase)
        db.session.flush()  # Get the ID without committing

        logger.info(f"Created new phrase: {phrase.id} - '{text}' ({language_code}), quizzable={is_quizzable}")
        return phrase

    except Exception as e:
        logger.error(f"Failed to get or create phrase: {str(e)}", exc_info=True)
        db.session.rollback()
        return None


def get_cached_translation(
    phrase_id: int,
    target_language_code: str
) -> Optional[PhraseTranslation]:
    """
    Get cached translation for a phrase in a specific target language.

    Args:
        phrase_id: The phrase ID
        target_language_code: ISO 639-1 code for target language (e.g., 'en')

    Returns:
        PhraseTranslation object or None if not cached
    """
    try:
        cached = PhraseTranslation.query.filter_by(
            phrase_id=phrase_id,
            target_language_code=target_language_code
        ).first()

        if cached:
            logger.info(f"Cache HIT: phrase_id={phrase_id}, target={target_language_code}")
        else:
            logger.info(f"Cache MISS: phrase_id={phrase_id}, target={target_language_code}")

        return cached

    except Exception as e:
        logger.error(f"Failed to get cached translation: {str(e)}", exc_info=True)
        return None


def cache_translation(
    phrase_id: int,
    target_language_code: str,
    translations_json: Dict[str, Any],
    model_name: str,
    model_version: Optional[str] = None,
    prompt_hash: Optional[str] = None,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    total_tokens: int = 0,
    cached_tokens: int = 0,
    cost_usd: Optional[Decimal] = None
) -> Optional[PhraseTranslation]:
    """
    Cache a translation for future use with cost tracking.

    Args:
        phrase_id: The phrase ID
        target_language_code: ISO 639-1 code for target language
        translations_json: The translation data (definitions, examples, etc.)
        model_name: Name of the LLM model used
        model_version: Version of the model (optional)
        prompt_hash: Hash of the prompt used (optional)
        prompt_tokens: Number of input tokens used
        completion_tokens: Number of output tokens used
        total_tokens: Total tokens used
        cached_tokens: Number of cached tokens (OpenAI only)
        cost_usd: Estimated cost in USD

    Returns:
        PhraseTranslation object or None if caching failed
    """
    try:
        # Check if translation already exists (shouldn't happen, but be safe)
        existing = PhraseTranslation.query.filter_by(
            phrase_id=phrase_id,
            target_language_code=target_language_code
        ).first()

        if existing:
            logger.warning(
                f"Translation already cached: phrase_id={phrase_id}, target={target_language_code}. "
                f"Updating existing cache."
            )
            existing.translations_json = translations_json
            existing.model_name = model_name
            existing.model_version = model_version
            existing.prompt_hash = prompt_hash
            existing.updated_at = datetime.now(timezone.utc)

            # Update cost tracking fields
            if cost_usd is not None:
                existing.prompt_tokens = prompt_tokens
                existing.completion_tokens = completion_tokens
                existing.total_tokens = total_tokens
                existing.cached_tokens = cached_tokens
                existing.estimated_cost_usd = float(cost_usd)
                existing.cost_calculated_at = datetime.now(timezone.utc)

            db.session.flush()
            return existing

        # Create new cache entry
        translation = PhraseTranslation(
            phrase_id=phrase_id,
            target_language_code=target_language_code,
            translations_json=translations_json,
            model_name=model_name,
            model_version=model_version,
            prompt_hash=prompt_hash,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cached_tokens=cached_tokens,
            estimated_cost_usd=float(cost_usd) if cost_usd is not None else 0.0,
            cost_calculated_at=datetime.now(timezone.utc) if cost_usd is not None else None
        )

        db.session.add(translation)
        db.session.flush()

        logger.info(
            f"Cached translation: phrase_id={phrase_id}, target={target_language_code}, "
            f"model={model_name}, cost=${float(cost_usd) if cost_usd else 0:.6f}"
        )

        return translation

    except Exception as e:
        logger.error(f"Failed to cache translation: {str(e)}", exc_info=True)
        db.session.rollback()
        return None


def get_or_create_translations(
    text: str,
    source_language: str,
    source_language_code: str,
    target_languages: List[str],
    target_language_codes: List[str],
    model: str,
    native_language: str = "English",
    session_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get translations with intelligent caching and cost tracking.

    This is the main function that implements the caching workflow:
    1. Get or create the phrase
    2. Check cache for each target language
    3. Call LLM only for uncached languages
    4. Cache new translations with cost data
    5. Aggregate cost to session if session_id provided
    6. Return combined results

    Args:
        text: The phrase text to translate
        source_language: Full name of source language (e.g., "German")
        source_language_code: ISO 639-1 code (e.g., "de")
        target_languages: List of full language names (e.g., ["English", "French"])
        target_language_codes: List of ISO 639-1 codes (e.g., ["en", "fr"])
        model: OpenAI model name
        native_language: Language for definitions/contexts
        session_id: Optional session UUID for cost aggregation

    Returns:
        Dict containing:
        - success: bool
        - phrase_id: int
        - source_language: str
        - target_languages: list
        - translations: dict with language names as keys
        - cache_status: dict showing which were cached vs fresh
        - model: str (for fresh translations)
        - usage: dict (for fresh translations)
        - cost_usd: float (for fresh translations)
    """
    try:
        # Step 1: Get or create the phrase
        phrase = get_or_create_phrase(text, source_language_code)
        if not phrase:
            return {
                "success": False,
                "error": "Failed to create or retrieve phrase"
            }

        # Step 2: Check cache for each target language
        cached_translations = {}
        uncached_languages = []
        uncached_codes = []
        cache_status = {}

        for target_lang, target_code in zip(target_languages, target_language_codes):
            cached = get_cached_translation(phrase.id, target_code)

            if cached:
                # Use cached translation
                cached_translations[target_lang] = cached.translations_json
                cache_status[target_lang] = "cached"
            else:
                # Need to call LLM for this language
                uncached_languages.append(target_lang)
                uncached_codes.append(target_code)
                cache_status[target_lang] = "fresh"

        # Step 3: Get source_info (from phrase cache or LLM)
        source_info = phrase.source_info_json  # Try to get from cached phrase first

        # Call LLM only for uncached languages
        fresh_translations = {}
        usage_stats = None

        if uncached_languages:
            logger.info(
                f"Calling LLM for uncached languages: {uncached_languages} "
                f"(phrase_id={phrase.id})"
            )

            llm_result = translate_text(
                text=text,
                source_language=source_language,
                target_languages=uncached_languages,
                model=model,
                native_language=native_language
            )

            # Check if spelling issue was detected - return early without caching
            if llm_result.get('spelling_issue'):
                logger.info(f"Spelling issue detected, not caching: '{llm_result.get('sent_word')}'")
                return llm_result  # Pass through the spelling issue response

            if not llm_result.get('success'):
                # If we have some cached translations, return those with partial error
                if cached_translations:
                    return {
                        "success": True,
                        "partial": True,
                        "phrase_id": phrase.id,
                        "source_language": source_language,
                        "target_languages": target_languages,
                        "translations": cached_translations,
                        "cache_status": cache_status,
                        "error": f"LLM failed for {uncached_languages}: {llm_result.get('error')}",
                        "model": model
                    }
                else:
                    # No cached translations and LLM failed - complete failure
                    return {
                        "success": False,
                        "error": llm_result.get('error'),
                        "phrase_id": phrase.id
                    }

            # Extract fresh translations and cost data
            fresh_translations = llm_result.get('translations', {})
            usage_stats = llm_result.get('usage')
            cost_usd = llm_result.get('cost_usd')
            new_source_info = llm_result.get('source_info', [text, '', ''])

            # Update phrase with source_info if we got it from LLM and don't have it cached
            if new_source_info and not phrase.source_info_json:
                phrase.source_info_json = new_source_info
                source_info = new_source_info  # Use the fresh source_info
                logger.info(f"Cached source_info for phrase_id={phrase.id}: {new_source_info}")
            elif new_source_info:
                source_info = new_source_info  # Use fresh source_info even if we have cached

            # Step 4: Cache new translations with cost data
            for target_lang, target_code in zip(uncached_languages, uncached_codes):
                if target_lang in fresh_translations:
                    translation_data = fresh_translations[target_lang]

                    cache_translation(
                        phrase_id=phrase.id,
                        target_language_code=target_code,
                        translations_json=translation_data,
                        model_name=model,
                        model_version=llm_result.get('model'),  # Actual model used
                        prompt_tokens=usage_stats.get('prompt_tokens', 0) if usage_stats else 0,
                        completion_tokens=usage_stats.get('completion_tokens', 0) if usage_stats else 0,
                        total_tokens=usage_stats.get('total_tokens', 0) if usage_stats else 0,
                        cached_tokens=usage_stats.get('cached_tokens', 0) if usage_stats else 0,
                        cost_usd=Decimal(str(cost_usd)) if cost_usd else None
                    )

            # Step 5: Aggregate cost to session if available
            if session_id and cost_usd:
                try:
                    add_translation_cost(session_id, Decimal(str(cost_usd)))
                    logger.info(f"Added translation cost ${cost_usd:.6f} to session {session_id}")
                except Exception as e:
                    logger.error(f"Failed to add translation cost to session: {e}")

        # Step 6: Combine cached and fresh translations
        all_translations = {**cached_translations, **fresh_translations}

        # Commit all changes
        db.session.commit()

        # Increment search count
        phrase.search_count = (phrase.search_count or 0) + 1
        db.session.commit()

        logger.info(
            f"Translation complete: phrase_id={phrase.id}, "
            f"cached={len(cached_translations)}, fresh={len(fresh_translations)}"
        )

        result = {
            "success": True,
            "phrase_id": phrase.id,
            "original_text": text,
            "source_language": source_language,
            "target_languages": target_languages,
            "native_language": native_language,
            "translations": all_translations,
            "cache_status": cache_status,
            "source_info": source_info or [text, '', ''],  # Fallback if only cached data
            "model": model
        }

        if usage_stats:
            result["usage"] = usage_stats

        return result

    except Exception as e:
        logger.error(f"Failed to get or create translations: {str(e)}", exc_info=True)
        db.session.rollback()
        return {
            "success": False,
            "error": f"Translation service error: {str(e)}"
        }


def invalidate_translation_cache(
    phrase_id: int,
    target_language_code: Optional[str] = None
) -> bool:
    """
    Invalidate (delete) cached translations.

    Args:
        phrase_id: The phrase ID
        target_language_code: Optional - specific language to invalidate.
                             If None, invalidates all translations for this phrase.

    Returns:
        True if successful, False otherwise
    """
    try:
        if target_language_code:
            # Delete specific translation
            deleted = PhraseTranslation.query.filter_by(
                phrase_id=phrase_id,
                target_language_code=target_language_code
            ).delete()
            logger.info(f"Invalidated cache: phrase_id={phrase_id}, target={target_language_code}")
        else:
            # Delete all translations for this phrase
            deleted = PhraseTranslation.query.filter_by(phrase_id=phrase_id).delete()
            logger.info(f"Invalidated all caches for phrase_id={phrase_id}")

        db.session.commit()
        return True

    except Exception as e:
        logger.error(f"Failed to invalidate cache: {str(e)}", exc_info=True)
        db.session.rollback()
        return False