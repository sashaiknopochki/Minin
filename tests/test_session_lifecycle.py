"""Test script to verify complete session lifecycle: login -> logout"""
import sys
sys.path.insert(0, '/')

from app import create_app
from models import db
from models.user import User
from models.session import Session
from services.session_service import create_session, get_active_session, end_session

# Create app context
app = create_app('development')

with app.app_context():
    print("=" * 60)
    print("Testing Session Lifecycle: Login -> Logout")
    print("=" * 60)

    # Get test user
    test_user = User.query.filter_by(email='test@example.com').first()
    if not test_user:
        print("ERROR: Test user not found. Run test_session_creation.py first.")
        sys.exit(1)

    print(f"\nTest User: {test_user.email} (ID: {test_user.id})")

    # Clean up any existing active sessions
    existing_active = get_active_session(test_user.id)
    if existing_active:
        print(f"Found existing active session: {existing_active.session_id}")
        print("Ending it first...")
        end_session(existing_active.session_id)

    # Simulate Login: Create a session
    print("\n" + "=" * 60)
    print("SIMULATING LOGIN")
    print("=" * 60)
    login_session = create_session(test_user.id)
    print(f"✓ Session created: {login_session.session_id}")
    print(f"  Started at: {login_session.started_at}")
    print(f"  Ended at: {login_session.ended_at}")

    # Verify active session exists
    active = get_active_session(test_user.id)
    if active and active.session_id == login_session.session_id:
        print("✓ Active session verified in database")
    else:
        print("✗ Active session not found!")

    # Simulate Logout: End the session
    print("\n" + "=" * 60)
    print("SIMULATING LOGOUT")
    print("=" * 60)
    ended_session = end_session(login_session.session_id)
    print(f"✓ Session ended: {ended_session.session_id}")
    print(f"  Started at: {ended_session.started_at}")
    print(f"  Ended at: {ended_session.ended_at}")

    # Verify no active session exists
    active_after_logout = get_active_session(test_user.id)
    if active_after_logout is None:
        print("✓ No active session found (correct after logout)")
    else:
        print(f"✗ Active session still exists: {active_after_logout.session_id}")

    # Verify session in database with ended_at set
    db_session = Session.query.get(login_session.session_id)
    if db_session and db_session.ended_at is not None:
        print("✓ Session has ended_at timestamp in database")
        duration = (db_session.ended_at - db_session.started_at).total_seconds()
        print(f"  Session duration: {duration:.2f} seconds")
    else:
        print("✗ Session ended_at not set in database")

    # Show all sessions for user
    print("\n" + "=" * 60)
    print("ALL SESSIONS FOR USER")
    print("=" * 60)
    all_sessions = Session.query.filter_by(user_id=test_user.id).order_by(Session.started_at.desc()).all()
    print(f"Total sessions: {len(all_sessions)}")
    print("\nSession Details:")
    for idx, s in enumerate(all_sessions, 1):
        status = "ACTIVE" if s.ended_at is None else "ENDED"
        print(f"\n{idx}. [{status}] {s.session_id}")
        print(f"   Started: {s.started_at}")
        print(f"   Ended:   {s.ended_at if s.ended_at else 'N/A'}")
        if s.ended_at:
            duration = (s.ended_at - s.started_at).total_seconds()
            print(f"   Duration: {duration:.2f} seconds")

    print("\n" + "=" * 60)
    print("✅ Session Lifecycle Test Complete!")
    print("=" * 60)