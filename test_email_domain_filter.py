#!/usr/bin/env python3
"""
Test script to verify email and domain filtering functionality
"""

import re
import sys
sys.path.append('.')
from website_spellcheck import WebsiteSpellChecker

# Test text with various email and domain patterns
test_text = """
Contact us at info@example.org for more information.
Visit our website at www.techcompany.com for details.
Check out articlesite.com for resources.
Find products on shopsite.com and marketplace.net.
Email webmaster@support.net for technical support.
The word misspelled should be caught.
Another mispelling here should be flagged.
But techcompany and marketplace are legitimate sites.
Also shopsite and articlesite are real companies.
"""

def test_email_domain_filtering():
    print("Testing Email and Domain Filtering")
    print("=" * 50)
    
    # Create a spell checker instance
    checker = WebsiteSpellChecker('config.yaml')
    
    # Manually test the filtering function
    test_cases = [
        # Format: (word, text, should_be_filtered)
        ("info", "Contact us at info@example.org", True),
        ("example", "Contact us at info@example.org", True),
        ("techcompany", "Visit www.techcompany.com for details", True),
        ("articlesite", "Check out articlesite.com for resources", True),
        ("shopsite", "Find products on shopsite.com", True),
        ("marketplace", "Also marketplace.net has products", True),
        ("misspelled", "The word misspelled should be caught", False),
        ("mispelling", "Another mispelling here should be flagged", False),
        ("support", "Email webmaster@support.net for help", True),
        ("webmaster", "Email webmaster@support.net for help", True),
    ]
    
    print("Testing individual cases:")
    print("-" * 30)
    
    correct_predictions = 0
    for word, text, should_filter in test_cases:
        # Find the word position in text
        match = re.search(r'\b' + re.escape(word) + r'\b', text, re.IGNORECASE)
        if match:
            start_pos = match.start()
            end_pos = match.end()
            
            result = checker._is_email_or_domain_fragment(word.lower(), text, start_pos, end_pos)
            status = "✅" if result == should_filter else "❌"
            action = "FILTERED" if result else "ALLOWED"
            expected = "FILTERED" if should_filter else "ALLOWED"
            
            print(f"{status} '{word}' in '{text[:50]}...' -> {action} (expected: {expected})")
            
            if result == should_filter:
                correct_predictions += 1
        else:
            print(f"❌ Could not find '{word}' in text")
    
    print(f"\nAccuracy: {correct_predictions}/{len(test_cases)} = {correct_predictions/len(test_cases)*100:.1f}%")
    
    # Test full spell checking on the sample text
    print(f"\nFull Spell Check Test:")
    print("-" * 30)
    
    errors = checker.spell_check_text(test_text, "test_url")
    
    print(f"Found {len(errors)} spelling errors:")
    for error in errors:
        print(f"  - '{error['word']}' -> {error['suggestions']}")
        print(f"    Context: {error['context'][:60]}...")
    
    # Expected: Should find "mispelling" but not domain fragments
    expected_errors = ["mispelling"]  # "misspelled" might be in dictionary
    found_words = [error['word'].lower() for error in errors]

    filtered_correctly = not any(word in found_words for word in [
        'info', 'example', 'techcompany', 'articlesite', 'shopsite', 'marketplace', 'support', 'webmaster'
    ])
    
    if filtered_correctly:
        print("\n✅ Domain/email filtering working correctly!")
    else:
        print("\n❌ Some domain/email fragments were not filtered")
        print(f"Found errors: {found_words}")

if __name__ == "__main__":
    test_email_domain_filtering()