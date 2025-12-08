#!/usr/bin/env python3
"""
Temporary test script to verify structured output vs JSON mode
"""

import sys
import logging
from Minin.services.llm_translation_service import translate_text, GPT_4_1_MINI, O4_MINI

# Configure logging to show in terminal
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(name)s - %(message)s'
)

def test_model(model_name):
    print(f"\n{'='*60}")
    print(f"Testing model: {model_name}")
    print('='*60)

    result = translate_text(
        text="hello",
        source_language="English",
        target_languages=["Spanish", "German"],
        model=model_name,
        native_language="English"
    )

    if result['success']:
        print(f"✓ Translation successful!")
        print(f"  Translations: {result['translations']}")
        print(f"  Tokens used: {result['usage']['total_tokens']}")
    else:
        print(f"✗ Translation failed: {result['error']}")

if __name__ == "__main__":
    # Test with both models
    print("\n" + "="*60)
    print("TRANSLATION SERVICE TEST - Structured Output vs JSON Mode")
    print("="*60)

    # Test GPT-4.1-mini (should use JSON mode)
    test_model(GPT_4_1_MINI)

    # Test O4-mini (should use JSON mode)
    test_model(O4_MINI)

    # Test gpt-4o-mini (should use structured output)
    test_model("gpt-4o-mini")

    print("\n" + "="*60)
    print("Test complete!")
    print("="*60 + "\n")