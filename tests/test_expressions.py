"""The arithmetic evaluator behind formula validation and quantitative grading."""

from __future__ import annotations

import pytest

from app.expressions import (
    DEFAULT_MAGNITUDE_FACTOR,
    ExpressionError,
    evaluate,
    grade_answer,
    referenced_names,
)


# --- Arithmetic --------------------------------------------------------------


@pytest.mark.parametrize(
    ("formula", "variables", "expected"),
    [
        ("2 + 3 * 4", {}, 14.0),
        ("(2 + 3) * 4", {}, 20.0),
        ("revenue - cost", {"revenue": 120.0, "cost": 45.0}, 75.0),
        ("-margin", {"margin": 3.0}, -3.0),
        ("max(a, b)", {"a": 2.0, "b": 9.0}, 9.0),
        ("round(a / b, 2)", {"a": 10.0, "b": 3.0}, 3.33),
        (
            "rate_per_kg - (cost_per_km / (load_factor * capacity_kg))",
            {"rate_per_kg": 18.9, "cost_per_km": 94.5, "load_factor": 0.55, "capacity_kg": 10.0},
            pytest.approx(1.7181818, rel=1e-6),
        ),
    ],
)
def test_it_computes_the_shapes_case_formulas_actually_use(formula, variables, expected) -> None:
    assert evaluate(formula, variables) == expected


def test_it_reports_the_inputs_a_formula_needs() -> None:
    """The validation gate uses this to catch a synthesis pass inventing a variable."""
    assert referenced_names("price * volume - fixed_cost") == {"price", "volume", "fixed_cost"}


def test_a_whitelisted_function_is_not_reported_as_an_input() -> None:
    assert referenced_names("max(a, 0)") == {"a"}


# --- Refusals ----------------------------------------------------------------


@pytest.mark.parametrize(
    "formula",
    [
        "__import__('os').system('echo hi')",
        "().__class__.__bases__",
        "open('/etc/passwd').read()",
        "[x for x in range(10)]",
        "lambda: 1",
        "a if b else c",
        "print(1)",
        "a.b",
        "a[0]",
        "{'k': 1}",
        "'text'",
        "a and b",
        "a == b",
    ],
)
def test_it_refuses_everything_outside_arithmetic(formula: str) -> None:
    """Formulas arrive from contributors, so anything but arithmetic is refused."""
    with pytest.raises(ExpressionError):
        evaluate(formula, {"a": 1.0, "b": 2.0, "c": 3.0})


def test_it_refuses_an_exponent_that_would_never_return() -> None:
    """Syntactically tiny, computationally hostile."""
    with pytest.raises(ExpressionError, match="Exponent"):
        evaluate("2 ** 2 ** 2 ** 999")


def test_it_refuses_a_formula_that_exceeds_the_node_budget() -> None:
    with pytest.raises(ExpressionError, match="node limit"):
        evaluate(" + ".join(["1"] * 300))


def test_division_by_zero_is_an_authoring_error_not_a_crash() -> None:
    with pytest.raises(ExpressionError, match="divides by zero"):
        evaluate("a / b", {"a": 1.0, "b": 0.0})


def test_a_missing_input_names_what_is_missing() -> None:
    with pytest.raises(ExpressionError, match="load_factor"):
        evaluate("rate - load_factor", {"rate": 5.0})


def test_a_boolean_input_is_rejected_rather_than_silently_becoming_one() -> None:
    with pytest.raises(ExpressionError, match="not numeric"):
        evaluate("a + 1", {"a": True})


# --- Consulting-math grading -------------------------------------------------


def test_an_exact_answer_grades_exact() -> None:
    assert grade_answer(180_000, 180_000).verdict == "exact"


def test_aggressive_rounding_still_grades_close() -> None:
    """Rounding to keep the arithmetic tractable is correct professional behaviour."""
    assert grade_answer(183_400, 180_000).verdict == "close"
    assert grade_answer(1.0, 1.2).verdict == "close"


def test_being_within_a_factor_of_two_grades_as_the_right_magnitude() -> None:
    assert grade_answer(100.0, 170.0).verdict == "right_magnitude"
    assert grade_answer(100.0, 60.0).verdict == "right_magnitude"


def test_a_magnitude_error_grades_wrong() -> None:
    """Dropping a zero is the failure the grader most needs to catch."""
    assert grade_answer(100.0, 1_000.0).verdict == "wrong"
    assert grade_answer(100.0, 10.0).verdict == "wrong"


def test_the_magnitude_band_boundary_is_inclusive() -> None:
    assert grade_answer(100.0, 100.0 * DEFAULT_MAGNITUDE_FACTOR).verdict == "right_magnitude"
    assert grade_answer(100.0, 100.0 / DEFAULT_MAGNITUDE_FACTOR).verdict == "right_magnitude"


def test_a_sign_flip_is_never_close_however_small_the_gap() -> None:
    """Positive and negative contribution are opposite commercial conclusions."""
    assert grade_answer(0.5, -0.5).verdict == "wrong"
    assert grade_answer(-2.0, 2.0).verdict == "wrong"


def test_an_expected_value_of_zero_does_not_divide_by_zero() -> None:
    """Zero contribution margin is a real and pedagogically central answer.

    Meridian's core mechanism is exactly this, so a ratio-based grader that
    crashed here would fail on the case the product most wants to teach.
    """
    assert grade_answer(0.0, 0.0).verdict == "exact"
    assert grade_answer(0.0, 4.2).verdict == "wrong"
    assert grade_answer(0.0, 0.0).ratio is None


def test_grading_carries_the_numbers_so_feedback_can_quote_them() -> None:
    grade = grade_answer(200.0, 150.0)

    assert grade.expected == 200.0
    assert grade.answered == 150.0
    assert grade.ratio == pytest.approx(0.75)
