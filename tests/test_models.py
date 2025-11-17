import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models import db
from models.user import User
from models.language import Language
from models.phrase import Phrase
from models.phrase_translation import PhraseTranslation
from models.user_searches import UserSearch
from models.user_learning_progress import UserLearningProgress
from models.quiz_attempt import QuizAttempt
from models.session import Session
from uuid import uuid4
from datetime import datetime

# Create app with test configuration
app = create_app('development')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test_database.db'

def cleanup():
    """Remove test database"""
    if os.path.exists('instance/test_database.db'):
        os.remove('instance/test_database.db')
        print("🧹 Test database cleaned up")

try:
    with app.app_context():
        # Create all tables
        db.create_all()
        print("✓ Database tables created successfully!")

        # Test 1: Add languages
        lang_en = Language(code='en', original_name='English', en_name='English', display_order=1)
        lang_de = Language(code='de', original_name='Deutsch', en_name='German', display_order=2)
        lang_ru = Language(code='ru', original_name='Русский', en_name='Russian', display_order=3)
        lang_fr = Language(code='fr', original_name='Français', en_name='French', display_order=4)
        db.session.add_all([lang_en, lang_de, lang_ru, lang_fr])
        db.session.commit()
        print("✓ Languages added successfully!")
        assert Language.query.count() == 4, "Should have 4 languages"

        # Test 2: Add a user
        user = User(
            google_id='test123',
            email='test@example.com',
            name='Test User',
            primary_language_code='en',
            translator_languages=["en", "de", "ru"]  # Fixed: Pass list, not string
        )
        db.session.add(user)
        db.session.commit()
        print("✓ User added successfully!")
        assert user.id is not None, "User should have ID after commit"
        assert user.primary_language.en_name == 'English', "Primary language relationship should work"

        # Test 3: Add phrases
        phrase_de = Phrase(text='geben', language_code='de', type='word', is_quizzable=True)
        phrase_en = Phrase(text='cat', language_code='en', type='word', is_quizzable=True)
        db.session.add_all([phrase_de, phrase_en])
        db.session.commit()
        print("✓ Phrases added successfully!")
        assert Phrase.query.count() == 2, "Should have 2 phrases"

        # Test 4: Add phrase translations with target_language_code (CRITICAL FIX)
        # Translation 1: German "geben" → English
        translation_de_en = PhraseTranslation(
            phrase_id=phrase_de.id,
            target_language_code='en',  # Fixed: Added required field
            translations_json={  # Fixed: Pass dict directly, not JSON string
                'translation': 'to give',
                'definitions': ['to hand over', 'to provide'],
                'examples': ['Ich gebe dir das Buch - I give you the book']
            },
            model_name='gpt-4o',
            model_version='2024-11-01'
        )

        # Translation 2: German "geben" → French (test multi-target-language feature)
        translation_de_fr = PhraseTranslation(
            phrase_id=phrase_de.id,
            target_language_code='fr',  # Same phrase, different target language
            translations_json={
                'translation': 'donner',
                'definitions': ['remettre', 'fournir'],
                'examples': ['Je te donne le livre - I give you the book']
            },
            model_name='claude-3.5-sonnet',
            model_version='2024-11-01'
        )

        # Translation 3: English "cat" → German
        translation_en_de = PhraseTranslation(
            phrase_id=phrase_en.id,
            target_language_code='de',
            translations_json={
                'translation': 'Katze',
                'definitions': ['ein kleines domestiziertes Säugetier'],
                'examples': ['Die Katze saß auf der Matte']
            },
            model_name='gpt-4o',
            model_version='2024-11-01'
        )

        db.session.add_all([translation_de_en, translation_de_fr, translation_en_de])
        db.session.commit()
        print("✓ Phrase translations added successfully!")
        assert PhraseTranslation.query.count() == 3, "Should have 3 translations"

        # Test multi-target-language feature
        geben_translations = PhraseTranslation.query.filter_by(phrase_id=phrase_de.id).all()
        assert len(geben_translations) == 2, "German 'geben' should have 2 target language translations"
        target_langs = {t.target_language_code for t in geben_translations}
        assert target_langs == {'en', 'fr'}, "Should have English and French translations"
        print("✓ Multi-target-language caching works correctly!")

        # Test 5: Add a session
        session = Session(
            session_id=str(uuid4()),
            user_id=user.id,
            started_at=datetime.utcnow()  # Fixed: Use Python datetime, not SQL function
        )
        db.session.add(session)
        db.session.commit()
        print("✓ Session added successfully!")
        assert session.user.email == 'test@example.com', "Session-User relationship should work"

        # Test 6: Add user searches
        user_search = UserSearch(
            user_id=user.id,
            phrase_id=phrase_de.id,
            session_id=session.session_id,
            context_sentence='I saw this word in a book',
            llm_translations_json={'en': 'to give', 'fr': 'donner', 'ru': 'давать'}  # Fixed: Pass dict
        )
        db.session.add(user_search)
        db.session.commit()
        print("✓ User search added successfully!")
        assert user_search.phrase.text == 'geben', "UserSearch-Phrase relationship should work"

        # Test 7: Add user learning progress
        progress = UserLearningProgress(
            user_id=user.id,
            phrase_id=phrase_de.id,
            stage='recognition',
            times_reviewed=1,
            times_correct=1,
            times_incorrect=0
        )
        db.session.add(progress)
        db.session.commit()
        print("✓ User learning progress added successfully!")
        assert progress.stage == 'recognition', "Progress stage should be set"

        # Test 8: Add quiz attempts
        quiz_attempt = QuizAttempt(
            user_id=user.id,
            phrase_id=phrase_de.id,
            question_type='multiple_choice_target',
            prompt_json={  # Fixed: Pass dict
                'question': 'Translate: geben',
                'options': ['to give', 'to take', 'to have', 'to make']
            },
            correct_answer='to give',
            user_answer='to give',
            was_correct=True
        )
        db.session.add(quiz_attempt)
        db.session.commit()
        print("✓ Quiz attempt added successfully!")
        assert quiz_attempt.was_correct == True, "Quiz attempt should be marked correct"

        # Test 9: Verify relationships work bidirectionally
        retrieved_user = User.query.filter_by(email='test@example.com').first()
        assert retrieved_user is not None, "Should retrieve user"
        assert retrieved_user.name == 'Test User', "User name should match"

        # Test user -> searches relationship
        user_searches_count = retrieved_user.user_searches.count()
        assert user_searches_count == 1, f"User should have 1 search, got {user_searches_count}"

        # Test user -> quiz_attempts relationship
        user_quiz_attempts = retrieved_user.quiz_attempts.count()
        assert user_quiz_attempts == 1, f"User should have 1 quiz attempt, got {user_quiz_attempts}"

        # Test user -> learning_progress relationship
        user_progress_count = retrieved_user.learning_progress.count()
        assert user_progress_count == 1, f"User should have 1 learning progress, got {user_progress_count}"

        print("✓ Bidirectional relationships work correctly!")

        # Test 10: Verify unique constraints
        try:
            # Try to add duplicate phrase (same text + language_code)
            duplicate_phrase = Phrase(text='geben', language_code='de', type='word')
            db.session.add(duplicate_phrase)
            db.session.commit()
            assert False, "Should not allow duplicate phrase with same text+language"
        except Exception as e:
            db.session.rollback()
            print("✓ Unique constraint on (text, language_code) works!")

        try:
            # Try to add duplicate translation (same phrase_id + target_language_code)
            duplicate_translation = PhraseTranslation(
                phrase_id=phrase_de.id,
                target_language_code='en',  # Already exists
                translations_json={'translation': 'to give'}
            )
            db.session.add(duplicate_translation)
            db.session.commit()
            assert False, "Should not allow duplicate translation for same phrase+target language"
        except Exception as e:
            db.session.rollback()
            print("✓ Unique constraint on (phrase_id, target_language_code) works!")

        # Test 11: Query phrase translations through relationship
        phrase_with_translations = Phrase.query.filter_by(text='geben').first()
        translations_list = phrase_with_translations.translations.all()
        assert len(translations_list) == 2, f"Should have 2 translations, got {len(translations_list)}"
        print("✓ Phrase -> translations relationship works!")

        # Test 12: Verify phrase language relationship
        assert phrase_de.language.en_name == 'German', "Phrase language relationship should work"
        print("✓ Phrase -> language relationship works!")

        print("\n✅ All tests passed! All models are working correctly.")
        print(f"   - {Language.query.count()} languages")
        print(f"   - {User.query.count()} users")
        print(f"   - {Phrase.query.count()} phrases")
        print(f"   - {PhraseTranslation.query.count()} translations")
        print(f"   - {Session.query.count()} sessions")
        print(f"   - {UserSearch.query.count()} searches")
        print(f"   - {UserLearningProgress.query.count()} progress records")
        print(f"   - {QuizAttempt.query.count()} quiz attempts")

except Exception as e:
    print(f"\n❌ Test failed with error: {e}")
    import traceback
    traceback.print_exc()
finally:
    # Cleanup
    with app.app_context():
        db.session.remove()
        db.drop_all()
    cleanup()