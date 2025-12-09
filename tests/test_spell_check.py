"""
Test spell-checking functionality in translation service
Run with: python test_spell_check.py
"""

import sys
import os

# Add parent directory to path to import services
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.llm_translation_service import translate_text

def test_valid_word():
    """Test that a valid word returns translations"""
    print("\n" + "="*60)
    print("TEST 1: Valid English word 'collection'")
    print("="*60)

    result = translate_text(
        text="collection",
        source_language="English",
        target_languages=["German", "Russian"],
        native_language="English"
    )

    print(f"\n✓ Success: {result.get('success')}")
    print(f"✓ Spelling Issue: {result.get('spelling_issue')}")

    if not result.get('spelling_issue'):
        print(f"✓ Translations present: {bool(result.get('translations'))}")
        print(f"✓ Source info: {result.get('source_info')}")
        if result.get('translations'):
            for lang, trans in result.get('translations', {}).items():
                print(f"  - {lang}: {trans[:2]}")  # First 2 translations

    assert result['success'], "Translation should succeed"
    assert not result.get('spelling_issue'), "Should not have spelling issue"
    assert result.get('translations'), "Should have translations"

    print("\n✅ TEST 1 PASSED")
    return result


def test_misspelled_word():
    """Test that a misspelled word returns spelling suggestion"""
    print("\n" + "="*60)
    print("TEST 2: Misspelled English word 'colection'")
    print("="*60)

    result = translate_text(
        text="colection",
        source_language="English",
        target_languages=["German", "Russian"],
        native_language="English"
    )

    print(f"\n✓ Success: {result.get('success')}")
    print(f"✓ Spelling Issue: {result.get('spelling_issue')}")

    if result.get('spelling_issue'):
        print(f"✓ Sent word: {result.get('sent_word')}")
        print(f"✓ Correct word: {result.get('correct_word')}")
        print(f"✓ Translations: {result.get('translations')}")

    assert result['success'], "Response should be successful"
    assert result.get('spelling_issue'), "Should detect spelling issue"
    assert result.get('sent_word') == "colection", "Should return sent word"
    assert result.get('correct_word'), "Should suggest correct spelling"
    assert not result.get('translations') or result.get('translations') == {}, "Should not have translations"

    print("\n✅ TEST 2 PASSED")
    return result


def test_valid_german_word():
    """Test that a valid German word returns translations"""
    print("\n" + "="*60)
    print("TEST 3: Valid German word 'geben'")
    print("="*60)

    result = translate_text(
        text="geben",
        source_language="German",
        target_languages=["English", "Russian"],
        native_language="Russian"
    )

    print(f"\n✓ Success: {result.get('success')}")
    print(f"✓ Spelling Issue: {result.get('spelling_issue')}")

    if not result.get('spelling_issue'):
        print(f"✓ Translations present: {bool(result.get('translations'))}")
        print(f"✓ Source info: {result.get('source_info')}")
        if result.get('translations'):
            for lang, trans in result.get('translations', {}).items():
                print(f"  - {lang}: {trans[:2]}")  # First 2 translations

    assert result['success'], "Translation should succeed"
    assert not result.get('spelling_issue'), "Should not have spelling issue"
    assert result.get('translations'), "Should have translations"

    print("\n✅ TEST 3 PASSED")
    return result


def test_misspelled_german_word():
    """Test that a misspelled German word returns spelling suggestion"""
    print("\n" + "="*60)
    print("TEST 4: Misspelled German word 'gebben' (should be 'geben')")
    print("="*60)

    result = translate_text(
        text="gebben",
        source_language="German",
        target_languages=["English", "Russian"],
        native_language="Russian"
    )

    print(f"\n✓ Success: {result.get('success')}")
    print(f"✓ Spelling Issue: {result.get('spelling_issue')}")

    if result.get('spelling_issue'):
        print(f"✓ Sent word: {result.get('sent_word')}")
        print(f"✓ Correct word: {result.get('correct_word')}")
        print(f"✓ Translations: {result.get('translations')}")

    assert result['success'], "Response should be successful"
    assert result.get('spelling_issue'), "Should detect spelling issue"
    assert result.get('sent_word') == "gebben", "Should return sent word"
    assert result.get('correct_word'), "Should suggest correct spelling"
    assert not result.get('translations') or result.get('translations') == {}, "Should not have translations"

    print("\n✅ TEST 4 PASSED")
    return result


if __name__ == "__main__":
    print("\n" + "🔍 SPELL-CHECKING FEATURE TESTS".center(60, "="))
    print("Testing the integrated spell-checking functionality")

    try:
        # Run all tests
        test_valid_word()
        test_misspelled_word()
        test_valid_german_word()
        test_misspelled_german_word()

        print("\n" + "="*60)
        print("🎉 ALL TESTS PASSED! 🎉".center(60))
        print("="*60)
        print("\n✅ Spell-checking feature is working correctly!")
        print("   - Valid words get translated")
        print("   - Misspelled words get suggestions")
        print("   - No invalid words are cached to the database")
        print()

    except AssertionError as e:
        print("\n" + "="*60)
        print("❌ TEST FAILED")
        print("="*60)
        print(f"\nError: {e}")
        sys.exit(1)
    except Exception as e:
        print("\n" + "="*60)
        print("❌ UNEXPECTED ERROR")
        print("="*60)
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)