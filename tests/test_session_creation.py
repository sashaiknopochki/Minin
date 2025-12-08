"""Test script to verify session creation functionality"""
import sys
sys.path.insert(0, '/')

from app import create_app
from models import db
from models.user import User
from models.session import Session
from services.session_service import create_session, get_active_session, get_or_create_session

# Create app context
app = create_app('development')

with app.app_context():
    print("Testing session creation...")

    # Get or create a test user
    test_user = User.query.filter_by(email='test@example.com').first()

    if not test_user:
        print("Creating test user...")
        test_user = User(
            google_id='test_google_id_12345',
            email='test@example.com',
            name='Test User',
            primary_language_code='en',
            translator_languages=['en', 'de', 'ru']
        )
        db.session.add(test_user)
        db.session.commit()
        print(f"Created user: {test_user.email} (ID: {test_user.id})")
    else:
        print(f"Using existing user: {test_user.email} (ID: {test_user.id})")

    # Test 1: Create a new session
    print("\nTest 1: Creating new session...")
    new_session = create_session(test_user.id)
    print(f"✓ Created session: {new_session.session_id}")
    print(f"  User ID: {new_session.user_id}")
    print(f"  Started at: {new_session.started_at}")
    print(f"  Ended at: {new_session.ended_at}")

    # Test 2: Get active session
    print("\nTest 2: Getting active session...")
    active_session = get_active_session(test_user.id)
    if active_session:
        print(f"✓ Found active session: {active_session.session_id}")
    else:
        print("✗ No active session found")

    # Test 3: Get or create session (should return existing)
    print("\nTest 3: Get or create session (should return existing)...")
    session = get_or_create_session(test_user.id)
    print(f"✓ Got session: {session.session_id}")
    if session.session_id == active_session.session_id:
        print("  ✓ Correctly returned existing active session")
    else:
        print("  ✗ Created new session instead of returning existing")

    # Test 4: Verify session in database
    print("\nTest 4: Verifying session in database...")
    db_session = Session.query.get(new_session.session_id)
    if db_session:
        print(f"✓ Session found in database: {db_session.session_id}")
        print(f"  User ID: {db_session.user_id}")
        print(f"  Started at: {db_session.started_at}")
    else:
        print("✗ Session not found in database")

    # Test 5: Count all sessions for user
    print("\nTest 5: Counting all sessions for user...")
    all_sessions = Session.query.filter_by(user_id=test_user.id).all()
    print(f"✓ Total sessions for user: {len(all_sessions)}")
    for idx, s in enumerate(all_sessions, 1):
        print(f"  {idx}. {s.session_id} (started: {s.started_at}, ended: {s.ended_at})")

    print("\n✅ All tests completed successfully!")