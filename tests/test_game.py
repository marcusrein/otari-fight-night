import random

from fightnight.game import (
    CODE_LENGTH,
    DIGITS,
    Rules,
    compare_rounds,
    make_secret,
    parse_guess,
    score,
)


def test_score_all_exact():
    assert score([1, 2, 3, 4], [1, 2, 3, 4]) == (4, 0)


def test_score_none():
    assert score([1, 1, 1, 1], [2, 2, 2, 2]) == (0, 0)


def test_score_mixed_with_repeats():
    # secret has two 1s; guess has one 1 in the wrong place and one 2 exact
    assert score([1, 1, 2, 3], [4, 2, 2, 1]) == (1, 1)


def test_score_misplaced_counts_each_digit_once():
    # guess repeats a digit the secret has only once
    assert score([1, 2, 3, 4], [4, 4, 4, 4]) == (1, 0)
    assert score([1, 2, 3, 4], [2, 1, 1, 1]) == (0, 2)


def test_parse_plain():
    assert parse_guess("1234") == [1, 2, 3, 4]
    assert parse_guess("1 2 3 4") == [1, 2, 3, 4]
    assert parse_guess("1, 2, 3, 4") == [1, 2, 3, 4]
    assert parse_guess("1-2-3-4") == [1, 2, 3, 4]


def test_parse_takes_last_group_in_chatty_reply():
    text = "Last time I guessed 1 1 2 2 and got 1 exact. My next guess: 1 3 2 5."
    assert parse_guess(text) == [1, 3, 2, 5]


def test_parse_ignores_digits_outside_range():
    assert parse_guess("Guess 7: 1 2 3 4") == [1, 2, 3, 4]
    assert parse_guess("9876") is None


def test_parse_rejects_wrong_length_and_garbage():
    assert parse_guess("123") is None
    assert parse_guess("I give up") is None
    assert parse_guess("") is None


def test_parse_five_digits_in_a_row_is_not_a_guess():
    # 12345 is ambiguous; the parser must not silently take a 4-digit slice of it
    assert parse_guess("12345") is None


def test_make_secret_is_seeded_and_in_range():
    a = make_secret(random.Random(7))
    b = make_secret(random.Random(7))
    assert a == b
    assert len(a) == CODE_LENGTH
    assert all(d in DIGITS for d in a)


def test_compare_rounds_fewer_guesses_wins():
    assert compare_rounds((3, 10.0), (5, 2.0)) == "a"
    assert compare_rounds((6, 1.0), (4, 9.0)) == "b"


def test_compare_rounds_speed_breaks_ties():
    assert compare_rounds((4, 3.2), (4, 3.9)) == "a"
    assert compare_rounds((4, 5.0), (4, 4.0)) == "b"
    assert compare_rounds((4, 5.0), (4, 5.0)) == "tie"


def test_custom_rules_three_digits_one_to_four():
    r = Rules(code_length=3, max_digit=4)
    assert make_secret(random.Random(1), r) and all(d in (1, 2, 3, 4) for d in make_secret(random.Random(1), r))
    assert parse_guess("my guess is 1 2 3", r) == [1, 2, 3]
    assert parse_guess("1234", r) is None  # too long for a 3-digit code
    assert parse_guess("125", r) is None  # 5 is out of range
