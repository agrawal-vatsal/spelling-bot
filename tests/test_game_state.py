"""Unit tests for SpellBeeGame."""

import pytest
from app.game.state import SESSION_LENGTH, SpellBeeGame


FIXED_WORDS = ["apple", "banana", "carrot", "daisy", "echo"]


def make_game(words=None):
    return SpellBeeGame(word_pool=words or FIXED_WORDS)


# ------------------------------------------------------------------ #
# Construction
# ------------------------------------------------------------------ #

def test_starts_at_word_one():
    g = make_game()
    assert g.word_number == 1


def test_total_words_equals_session_length():
    g = make_game()
    assert g.total_words == SESSION_LENGTH


def test_initial_score_is_zero():
    g = make_game()
    assert g.score == 0


def test_not_finished_initially():
    g = make_game()
    assert not g.is_finished()


def test_word_pool_larger_than_session_length():
    pool = [f"word{i}" for i in range(20)]
    g = SpellBeeGame(word_pool=pool)
    assert g.total_words == SESSION_LENGTH


def test_word_pool_small_uses_all():
    # Pool exactly session_length — should use all of them.
    pool = [f"w{i}" for i in range(SESSION_LENGTH)]
    g = SpellBeeGame(word_pool=pool)
    collected = []
    while not g.is_finished():
        collected.append(g.current_word())
        g.record_result(True)
        g.advance()
    assert len(collected) == SESSION_LENGTH
    assert set(collected) == set(pool)


# ------------------------------------------------------------------ #
# current_word
# ------------------------------------------------------------------ #

def test_current_word_returns_string():
    g = make_game()
    assert isinstance(g.current_word(), str)
    assert len(g.current_word()) > 0


def test_current_word_raises_when_finished():
    g = make_game()
    for _ in range(SESSION_LENGTH):
        g.record_result(False)
        g.advance()
    assert g.is_finished()
    with pytest.raises(IndexError):
        g.current_word()


# ------------------------------------------------------------------ #
# record_result / score
# ------------------------------------------------------------------ #

def test_correct_answer_increments_score():
    g = make_game()
    g.record_result(True)
    assert g.score == 1


def test_incorrect_answer_does_not_increment_score():
    g = make_game()
    g.record_result(False)
    assert g.score == 0


def test_multiple_correct_answers_accumulate():
    g = make_game()
    for _ in range(3):
        g.record_result(True)
        g.advance()
    assert g.score == 3


# ------------------------------------------------------------------ #
# advance / is_finished
# ------------------------------------------------------------------ #

def test_advance_moves_to_next_word():
    g = make_game()
    w1 = g.current_word()
    g.record_result(False)
    g.advance()
    assert g.word_number == 2
    # We don't assert g.current_word() != w1 because the shuffled pool
    # could coincidentally place the same word at index 1.


def test_session_finishes_after_session_length_advances():
    g = make_game()
    for _ in range(SESSION_LENGTH):
        g.record_result(False)
        g.advance()
    assert g.is_finished()


def test_word_number_clamped_when_finished():
    g = make_game()
    for _ in range(SESSION_LENGTH):
        g.record_result(False)
        g.advance()
    assert g.word_number == SESSION_LENGTH


def test_perfect_score():
    g = make_game()
    for _ in range(SESSION_LENGTH):
        g.record_result(True)
        g.advance()
    assert g.score == SESSION_LENGTH
    assert g.is_finished()
