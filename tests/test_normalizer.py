"""Unit tests for SpellingValidator._extract_spelling."""

from app.game.state import SpellBeeGame
from app.processors.spelling_validator import SpellingValidator

# Shared validator instance (game state is irrelevant for extraction tests).
_v = SpellingValidator(SpellBeeGame())


def extract(text: str) -> str:
    return _v._extract_spelling(text)


def test_letter_by_letter():
    assert extract("a p p l e") == "apple"

def test_phonetic_names():
    assert extract("ay pee pee el ee") == "apple"

def test_hyphen_separated():
    assert extract("A-P-P-L-E") == "apple"

def test_ignores_whole_word():
    # User just said the word — not a spelling attempt.
    assert extract("apple") == ""

def test_ignores_conversational_phrase():
    # "you"→u and "I"→i are isolated (not consecutive); longest run = 1 < min.
    assert extract("can you repeat the word again? I did not get it.") == ""

def test_isolated_you_and_i_do_not_combine():
    # Regression: previously gathered globally → "ui"; now kept separate.
    assert extract("Can you repeat the word again? I did not get it.") == ""

def test_sentence_with_embedded_spelling():
    # Preamble breaks before the run; only the consecutive letters are taken.
    assert extract("the spelling is a p p l e") == "apple"

def test_phonetics_after_preamble():
    assert extract("the spelling is ay pee pee el ee") == "apple"

def test_short_run_below_minimum():
    # Two consecutive letters < _MIN_SPELLING_LETTERS (3) → "".
    assert extract("a p") == ""

def test_three_letter_run_at_minimum():
    assert extract("c a t") == "cat"

def test_empty_transcript():
    assert extract("") == ""

def test_whole_words_are_not_spelling():
    assert extract("sorry") == ""
    assert extract("repeat") == ""

def test_i_see_you_edge_case():
    # "i" + "see"→c + "you"→u form a consecutive run of 3 → "icu".
    # Accepted by the minimum-length check; won't match any real target word.
    assert extract("I see you") == "icu"
