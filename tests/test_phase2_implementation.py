"""Test script to verify Phase 2 implementation

This script tests:
1. New cost tracking fields in models
2. Session cost aggregator functionality
"""

from app import create_app
from models import db
from models.phrase_translation import PhraseTranslation
from models.quiz_attempt import QuizAttempt
from models.session import Session
from models.user import User
from services.session_cost_aggregator import add_translation_cost, add_quiz_cost, get_session_cost_summary
from decimal import Decimal
import uuid

def test_phase2_implementation():
    """Test Phase 2 cost tracking implementation"""
    app = create_app('testing')

    with app.app_context():
        print("=" * 60)
        print("Phase 2 Implementation Test")
        print("=" * 60)

        # Test 1: Verify PhraseTranslation has new cost fields
        print("\n1. Testing PhraseTranslation model...")
        pt = PhraseTranslation()
        assert hasattr(pt, 'prompt_tokens'), "Missing prompt_tokens field"
        assert hasattr(pt, 'completion_tokens'), "Missing completion_tokens field"
        assert hasattr(pt, 'total_tokens'), "Missing total_tokens field"
        assert hasattr(pt, 'cached_tokens'), "Missing cached_tokens field"
        assert hasattr(pt, 'estimated_cost_usd'), "Missing estimated_cost_usd field"
        assert hasattr(pt, 'cost_calculated_at'), "Missing cost_calculated_at field"
        print("   ✓ PhraseTranslation has all cost tracking fields")

        # Test 2: Verify QuizAttempt has new cost fields
        print("\n2. Testing QuizAttempt model...")
        qa = QuizAttempt()
        assert hasattr(qa, 'question_gen_prompt_tokens'), "Missing question_gen_prompt_tokens field"
        assert hasattr(qa, 'question_gen_completion_tokens'), "Missing question_gen_completion_tokens field"
        assert hasattr(qa, 'question_gen_total_tokens'), "Missing question_gen_total_tokens field"
        assert hasattr(qa, 'question_gen_cost_usd'), "Missing question_gen_cost_usd field"
        assert hasattr(qa, 'question_gen_model'), "Missing question_gen_model field"
        assert hasattr(qa, 'eval_prompt_tokens'), "Missing eval_prompt_tokens field"
        assert hasattr(qa, 'eval_completion_tokens'), "Missing eval_completion_tokens field"
        assert hasattr(qa, 'eval_total_tokens'), "Missing eval_total_tokens field"
        assert hasattr(qa, 'eval_cost_usd'), "Missing eval_cost_usd field"
        assert hasattr(qa, 'eval_model'), "Missing eval_model field"
        print("   ✓ QuizAttempt has all cost tracking fields")

        # Test 3: Verify Session has cost aggregation fields
        print("\n3. Testing Session model...")
        s = Session()
        assert hasattr(s, 'total_translation_cost_usd'), "Missing total_translation_cost_usd field"
        assert hasattr(s, 'total_quiz_cost_usd'), "Missing total_quiz_cost_usd field"
        assert hasattr(s, 'total_cost_usd'), "Missing total_cost_usd field"
        assert hasattr(s, 'operations_count'), "Missing operations_count field"
        print("   ✓ Session has all cost aggregation fields")

        # Test 4: Test session cost aggregator with a test session
        print("\n4. Testing Session Cost Aggregator...")

        # Create test data
        db.create_all()

        # Create test user
        test_user = User(
            google_id=f"test_google_id_{uuid.uuid4().hex[:8]}",
            email=f"test_{uuid.uuid4().hex[:8]}@example.com",
            primary_language_code="en"
        )
        db.session.add(test_user)
        db.session.flush()

        # Create test session
        test_session_id = str(uuid.uuid4())
        test_session = Session(
            session_id=test_session_id,
            user_id=test_user.id
        )
        db.session.add(test_session)
        db.session.commit()

        print(f"   Created test session: {test_session_id}")

        # Get initial state
        initial_summary = get_session_cost_summary(test_session_id)
        print(f"   Initial state:")
        print(f"     - Translation cost: ${initial_summary['total_translation_cost_usd']}")
        print(f"     - Quiz cost: ${initial_summary['total_quiz_cost_usd']}")
        print(f"     - Total cost: ${initial_summary['total_cost_usd']}")
        print(f"     - Operations: {initial_summary['operations_count']}")

        # Add translation cost
        test_translation_cost = Decimal('0.001234')
        success = add_translation_cost(test_session_id, test_translation_cost)
        assert success, "Failed to add translation cost"
        print(f"   ✓ Added translation cost: ${test_translation_cost}")

        # Add quiz cost
        test_quiz_cost = Decimal('0.000567')
        success = add_quiz_cost(test_session_id, test_quiz_cost)
        assert success, "Failed to add quiz cost"
        print(f"   ✓ Added quiz cost: ${test_quiz_cost}")

        # Verify final state
        final_summary = get_session_cost_summary(test_session_id)
        print(f"   Final state:")
        print(f"     - Translation cost: ${final_summary['total_translation_cost_usd']}")
        print(f"     - Quiz cost: ${final_summary['total_quiz_cost_usd']}")
        print(f"     - Total cost: ${final_summary['total_cost_usd']}")
        print(f"     - Operations: {final_summary['operations_count']}")

        # Verify increments (Note: session table uses DECIMAL(10,4) so values are rounded)
        # The detailed operation tables use DECIMAL(10,6), but session aggregates use DECIMAL(10,4)
        expected_translation = Decimal('0.0012')  # Rounded from 0.001234
        expected_quiz = Decimal('0.0006')  # Rounded from 0.000567
        expected_total = Decimal('0.0018')  # 0.0012 + 0.0006
        expected_ops = 2

        assert final_summary['total_translation_cost_usd'] == expected_translation, f"Translation cost mismatch: {final_summary['total_translation_cost_usd']} != {expected_translation}"
        assert final_summary['total_quiz_cost_usd'] == expected_quiz, f"Quiz cost mismatch: {final_summary['total_quiz_cost_usd']} != {expected_quiz}"
        assert final_summary['total_cost_usd'] == expected_total, f"Total cost mismatch: {final_summary['total_cost_usd']} != {expected_total}"
        assert final_summary['operations_count'] == expected_ops, f"Operations count mismatch: {final_summary['operations_count']} != {expected_ops}"

        print("   ✓ Cost aggregation working correctly!")

        # Cleanup
        db.session.rollback()

        print("\n" + "=" * 60)
        print("✓ All Phase 2 tests passed!")
        print("=" * 60)

if __name__ == '__main__':
    test_phase2_implementation()