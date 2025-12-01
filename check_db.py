"""
Database Health Check Script
Verifies that the database is working correctly
"""

from app import create_app
from models import db
from models.user import User
from models.language import Language
from models.phrase import Phrase
from models.user_learning_progress import UserLearningProgress
from models.quiz_attempt import QuizAttempt
from sqlalchemy import inspect


def check_database():
    """Check if database is working correctly"""
    app = create_app('development')

    with app.app_context():
        try:
            print("=" * 60)
            print("DATABASE HEALTH CHECK")
            print("=" * 60)

            # Check if tables exist
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()

            expected_tables = [
                'users', 'languages', 'phrases', 'phrase_translations',
                'user_searches', 'user_learning_progress', 'quiz_attempts',
                'sessions', 'alembic_version'
            ]

            missing_tables = set(expected_tables) - set(tables)
            if missing_tables:
                print(f"\n❌ MISSING TABLES: {missing_tables}")
                return False

            print(f"\n✅ All {len(expected_tables)} expected tables exist")

            # Check record counts
            print("\n📊 Record Counts:")
            counts = {
                'Users': User.query.count(),
                'Languages': Language.query.count(),
                'Phrases': Phrase.query.count(),
                'Learning Progress': UserLearningProgress.query.count(),
                'Quiz Attempts': QuizAttempt.query.count(),
            }

            for name, count in counts.items():
                print(f"  - {name}: {count}")

            # Check languages are populated
            if Language.query.count() == 0:
                print("\n⚠️  WARNING: No languages in database!")
                print("   Run: python populate_languages.py")

            print("\n" + "=" * 60)
            print("✅ DATABASE IS HEALTHY!")
            print("=" * 60)
            return True

        except Exception as e:
            print("\n" + "=" * 60)
            print(f"❌ DATABASE ERROR: {e}")
            print("=" * 60)
            return False


if __name__ == '__main__':
    check_database()
