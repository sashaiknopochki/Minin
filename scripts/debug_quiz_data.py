"""
Debug script to check quiz-eligible phrases in the database.
Run this to see what phrases should appear in Practice page.
"""

from app import create_app
from models import db
from models.user_learning_progress import UserLearningProgress
from models.phrase import Phrase
from models.user import User
from datetime import date

app = create_app()

with app.app_context():
    # Get the first user (or specify user_id)
    user = User.query.first()
    
    if not user:
        print("❌ No users found in database")
        exit()
    
    print(f"🔍 Checking quiz data for user: {user.email}")
    print(f"   Primary language: {user.primary_language_code}")
    print(f"   Translator languages: {user.translator_languages}")
    print(f"   Quiz mode enabled: {user.quiz_mode_enabled}")
    print(f"   Quiz frequency: {user.quiz_frequency}")
    print(f"   Searches since last quiz: {user.searches_since_last_quiz}")
    print()
    
    # Query all user_learning_progress entries
    all_progress = UserLearningProgress.query.filter_by(user_id=user.id).all()
    print(f"📊 Total learning progress entries: {len(all_progress)}")
    print()
    
    # Check entries with times_reviewed = 0 and next_review_date = today
    today = date.today()
    eligible_entries = UserLearningProgress.query.join(
        Phrase, UserLearningProgress.phrase_id == Phrase.id
    ).filter(
        UserLearningProgress.user_id == user.id,
        UserLearningProgress.times_reviewed == 0,
        UserLearningProgress.next_review_date == today
    ).all()
    
    print(f"✅ Entries with times_reviewed=0 AND next_review_date=today ({today}):")
    print(f"   Count: {len(eligible_entries)}")
    
    for progress in eligible_entries:
        phrase = progress.phrase
        print(f"\n   📝 Phrase ID: {phrase.id}")
        print(f"      Text: '{phrase.text}'")
        print(f"      Language: {phrase.language_code}")
        print(f"      Is quizzable: {phrase.is_quizzable}")
        print(f"      Stage: {progress.stage}")
        print(f"      Next review date: {progress.next_review_date}")
        print(f"      Times reviewed: {progress.times_reviewed}")
    
    print("\n" + "="*60)
    
    # Now test the actual query used by get_filtered_phrases_for_practice
    # with filters set to 'all'
    print("\n🔬 Testing Practice page query (filters: all/all/due=false):")
    
    query = UserLearningProgress.query.join(
        Phrase, UserLearningProgress.phrase_id == Phrase.id
    ).filter(
        UserLearningProgress.user_id == user.id,
        Phrase.is_quizzable == True
    )
    
    # Language filter: 'all' means use translator_languages
    if user.translator_languages:
        query = query.filter(Phrase.language_code.in_(user.translator_languages))
    
    # NO due_for_review filter when due=false
    # NO stage filter when stage='all'
    
    query = query.order_by(UserLearningProgress.next_review_date.asc())
    
    results = query.all()
    print(f"   Results found: {len(results)}")
    
    for progress in results[:5]:  # Show first 5
        phrase = progress.phrase
        print(f"\n   📝 Phrase: '{phrase.text}' ({phrase.language_code})")
        print(f"      Stage: {progress.stage}, Next review: {progress.next_review_date}")
        print(f"      Times reviewed: {progress.times_reviewed}")
    
    print("\n" + "="*60)
    
    # Now test with due_for_review=True
    print("\n🔬 Testing Practice page query (filters: all/all/due=true):")
    
    query = UserLearningProgress.query.join(
        Phrase, UserLearningProgress.phrase_id == Phrase.id
    ).filter(
        UserLearningProgress.user_id == user.id,
        Phrase.is_quizzable == True,
        UserLearningProgress.next_review_date <= today  # DUE FILTER APPLIED
    )
    
    if user.translator_languages:
        query = query.filter(Phrase.language_code.in_(user.translator_languages))
    
    query = query.order_by(UserLearningProgress.next_review_date.asc())
    
    results = query.all()
    print(f"   Results found: {len(results)}")
    
    for progress in results[:5]:  # Show first 5
        phrase = progress.phrase
        print(f"\n   📝 Phrase: '{phrase.text}' ({phrase.language_code})")
        print(f"      Stage: {progress.stage}, Next review: {progress.next_review_date}")
        print(f"      Times reviewed: {progress.times_reviewed}")
    
    print("\n" + "="*60)
    
    # Test get_phrase_for_quiz query (used on Translate page)
    print("\n🔬 Testing Translate page query (get_phrase_for_quiz):")
    
    query = UserLearningProgress.query.join(
        Phrase, UserLearningProgress.phrase_id == Phrase.id
    ).filter(
        UserLearningProgress.user_id == user.id,
        UserLearningProgress.stage != 'mastered',  # Exclude mastered
        UserLearningProgress.next_review_date <= today,  # Due or overdue
        Phrase.is_quizzable == True
    )
    
    if user.translator_languages:
        query = query.filter(Phrase.language_code.in_(user.translator_languages))
    
    query = query.order_by(UserLearningProgress.next_review_date.asc())
    
    results = query.all()
    print(f"   Results found: {len(results)}")
    
    for progress in results[:5]:  # Show first 5
        phrase = progress.phrase
        print(f"\n   📝 Phrase: '{phrase.text}' ({phrase.language_code})")
        print(f"      Stage: {progress.stage}, Next review: {progress.next_review_date}")
        print(f"      Times reviewed: {progress.times_reviewed}")
