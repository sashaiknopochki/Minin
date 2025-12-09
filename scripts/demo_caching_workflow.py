"""
Demo script showing the phrase translation caching workflow

This demonstrates the exact workflow from the specification:
1. First user searches "geben" (German → English) - creates phrase + calls LLM + caches
2. Second user searches "geben" (German → English) - instant cache hit!
3. Third user searches "geben" (German → French) - reuses phrase + fresh LLM call

Run this with: python demo_caching_workflow.py
"""

from app import create_app
from models import db
from models.language import Language
from models.phrase import Phrase
from models.phrase_translation import PhraseTranslation
from services.phrase_translation_service import get_or_create_translations
import json


def setup_demo_db():
    """Set up a fresh demo database with languages"""
    print("🔧 Setting up demo database...")

    db.create_all()

    # Add languages if they don't exist
    languages_data = [
        ('de', 'Deutsch', 'German'),
        ('en', 'English', 'English'),
        ('fr', 'Français', 'French'),
        ('ru', 'Русский', 'Russian'),
    ]

    for code, original_name, en_name in languages_data:
        if not Language.query.get(code):
            lang = Language(code=code, original_name=original_name, en_name=en_name)
            db.session.add(lang)

    db.session.commit()
    print("✅ Database ready\n")


def print_cache_stats():
    """Print current cache statistics"""
    phrase_count = Phrase.query.count()
    translation_count = PhraseTranslation.query.count()

    print("\n📊 Cache Statistics:")
    print(f"   Total phrases: {phrase_count}")
    print(f"   Total cached translations: {translation_count}")

    if translation_count > 0:
        print("\n   Cached translations breakdown:")
        translations = PhraseTranslation.query.all()
        for trans in translations:
            phrase = Phrase.query.get(trans.phrase_id)
            print(f"   - '{phrase.text}' ({phrase.language_code}) → {trans.target_language_code} "
                  f"[{trans.model_name}]")
    print()


def demo_workflow():
    """Demonstrate the complete caching workflow"""

    print("=" * 70)
    print("PHRASE TRANSLATION CACHING WORKFLOW DEMO")
    print("=" * 70)

    # Scenario 1: First user searches "geben" (German → English)
    print("\n📝 SCENARIO 1: First user searches 'geben' (German → English)")
    print("-" * 70)

    result1 = get_or_create_translations(
        text="geben",
        source_language="German",
        source_language_code="de",
        target_languages=["English"],
        target_language_codes=["en"],
        model="gpt-4.1-mini",
        native_language="English"
    )

    print(f"✅ Success: {result1['success']}")
    print(f"📦 Phrase ID: {result1['phrase_id']}")
    print(f"🎯 Cache Status: {result1['cache_status']}")
    print(f"💰 LLM Usage: {result1.get('usage', 'No usage data (cached)')}")
    print(f"\n📖 Translation:")
    print(json.dumps(result1['translations'], indent=2, ensure_ascii=False))

    phrase_id_1 = result1['phrase_id']

    # Scenario 2: Second user searches "geben" (German → English) - CACHE HIT!
    print("\n\n📝 SCENARIO 2: Second user searches 'geben' (German → English)")
    print("-" * 70)
    print("⚡ This should be an instant cache hit - no LLM call!")

    result2 = get_or_create_translations(
        text="geben",
        source_language="German",
        source_language_code="de",
        target_languages=["English"],
        target_language_codes=["en"],
        model="gpt-4.1-mini",
        native_language="English"
    )

    print(f"✅ Success: {result2['success']}")
    print(f"📦 Phrase ID: {result2['phrase_id']} (same as scenario 1: {result2['phrase_id'] == phrase_id_1})")
    print(f"🎯 Cache Status: {result2['cache_status']}")
    print(f"💰 LLM Usage: {result2.get('usage', 'No usage data (cached)')}")
    print(f"\n📖 Translation:")
    print(json.dumps(result2['translations'], indent=2, ensure_ascii=False))

    # Scenario 3: Third user searches "geben" (German → French)
    print("\n\n📝 SCENARIO 3: Third user searches 'geben' (German → French)")
    print("-" * 70)
    print("🔄 Reuses existing phrase, but needs fresh LLM call for French")

    result3 = get_or_create_translations(
        text="geben",
        source_language="German",
        source_language_code="de",
        target_languages=["French"],
        target_language_codes=["fr"],
        model="gpt-4.1-mini",
        native_language="English"
    )

    print(f"✅ Success: {result3['success']}")
    print(f"📦 Phrase ID: {result3['phrase_id']} (same phrase: {result3['phrase_id'] == phrase_id_1})")
    print(f"🎯 Cache Status: {result3['cache_status']}")
    print(f"💰 LLM Usage: {result3.get('usage', 'No usage data (cached)')}")
    print(f"\n📖 Translation:")
    print(json.dumps(result3['translations'], indent=2, ensure_ascii=False))

    # Scenario 4: Fourth user searches "geben" (German → English + French)
    print("\n\n📝 SCENARIO 4: Fourth user searches 'geben' (German → English + French)")
    print("-" * 70)
    print("🚀 Both languages should be cached now - no LLM call!")

    result4 = get_or_create_translations(
        text="geben",
        source_language="German",
        source_language_code="de",
        target_languages=["English", "French"],
        target_language_codes=["en", "fr"],
        model="gpt-4.1-mini",
        native_language="English"
    )

    print(f"✅ Success: {result4['success']}")
    print(f"📦 Phrase ID: {result4['phrase_id']} (same phrase: {result4['phrase_id'] == phrase_id_1})")
    print(f"🎯 Cache Status: {result4['cache_status']}")
    print(f"💰 LLM Usage: {result4.get('usage', 'No usage data (cached)')}")
    print(f"\n📖 Translations:")
    print(json.dumps(result4['translations'], indent=2, ensure_ascii=False))

    # Show final cache statistics
    print_cache_stats()

    # Summary
    print("\n" + "=" * 70)
    print("💡 KEY BENEFITS DEMONSTRATED:")
    print("=" * 70)
    print("✅ Same phrase stored only once in 'phrases' table")
    print("✅ Each translation (phrase + target language) cached separately")
    print("✅ Multiple users benefit from shared cache")
    print("✅ Mixed cached/fresh requests handled efficiently")
    print("✅ Significant LLM API cost savings (cached requests = $0)")
    print("=" * 70)


def main():
    """Main entry point"""
    app = create_app('development')

    with app.app_context():
        setup_demo_db()

        # Clear existing data for clean demo
        print("🧹 Clearing existing demo data...")
        PhraseTranslation.query.delete()
        Phrase.query.filter_by(text='geben').delete()
        db.session.commit()

        # Run the demo
        demo_workflow()


if __name__ == '__main__':
    print("\n⚠️  NOTE: This demo requires a valid OPENAI_API_KEY in your .env file")
    print("⚠️  It will make real LLM API calls for fresh translations\n")

    try:
        main()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure you have:")
        print("1. Set up your .env file with OPENAI_API_KEY")
        print("2. Run 'python populate_languages.py' to populate languages table")
        print("3. Installed all dependencies from requirements.txt")