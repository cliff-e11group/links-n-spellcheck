#!/usr/bin/env python3
"""
Quick test script to debug spell checking functionality
"""

from spellchecker import SpellChecker
import yaml

# Load config
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Initialize spell checker
spell_checker = SpellChecker(language=config['spell_checking']['language'])

# Load custom dictionaries
custom_words = set()
for dict_file in config['spell_checking']['custom_dictionaries']:
    try:
        with open(dict_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    custom_words.add(line.lower())
        print(f"Loaded {len(custom_words)} words from {dict_file}")
    except FileNotFoundError:
        print(f"Dictionary file not found: {dict_file}")

spell_checker.word_frequency.load_words(custom_words)

print(f"Dictionary size: {len(spell_checker.word_frequency.dictionary)}")

# Test words - mix of correct, incorrect, and custom dictionary terms
test_words = [
    "hello",      # should be correct
    "wrold",      # should be misspelled (world)
    "teh",        # should be misspelled (the)
    "website",    # should be correct (in our custom dict)
    "webinar",    # should be correct (in our custom dict)
    "online",     # should be correct
    "spellling",  # should be misspelled (spelling)
    "mispelled",  # should be misspelled (misspelled)
    "occured",    # should be misspelled (occurred)
    "notarealword" # should be misspelled
]

print("\nTesting spell checker:")
print("-" * 50)

misspelled_count = 0
for word in test_words:
    is_correct = word in spell_checker
    
    if not is_correct:
        suggestions = list(spell_checker.candidates(word))[:3]
        print(f"❌ '{word}' -> {suggestions}")
        misspelled_count += 1
    else:
        print(f"✅ '{word}' is correct")

print(f"\nFound {misspelled_count} misspelled words out of {len(test_words)} tested")

if misspelled_count == 0:
    print("⚠️  WARNING: No misspellings found. This might indicate an issue with the spell checker setup.")
else:
    print("✅ Spell checker appears to be working correctly!")