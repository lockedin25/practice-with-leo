"""A deliberately small arithmetic evaluator for authored case formulas.

Three callers depend on this and all three need the same guarantee, which is why
it exists once rather than three times: the contribution validation gate checks
that a contributed case's numbers actually close, the derived-fact consistency
check recomputes stated implications, and the quantitative grader scores a
candidate's arithmetic.

**Why not eval().** These formulas arrive from contributors through an LLM
synthesis pass. ``eval`` on that input is arbitrary code execution by a stranger.
Even a trusted-input argument fails here, because the whole point of the
contribution engine is that the input is not trusted.

**Why not a model.** Asking an LLM to verify arithmetic reintroduces exactly the
failure the validation gate exists to catch. Multi-constraint numeric closure is
where models produce confident, plausible, wrong numbers. Arithmetic is decided
here, in code, and the model is never asked whether a sum is correct.

**Consulting math, not exact arithmetic.** :func:`grade_answer` bands a candidate
answer rather than comparing it for equality, because an interviewer cares far
more that the order of magnitude is right and the setup was sound than that the
last digit matched.
"""

from __future__ import annotations

import ast
import math
from dataclasses import dataclass
from typing import Literal


class ExpressionError(ValueError):
    """An authored formula is malformed, unsafe, or not computable."""


# Binary and unary operations an authored formula may use. Deliberately no
# bitwise, shift, matrix-multiply or floor-divide: none of them appear in case
# arithmetic, and every operator admitted is one more thing to reason about.
_BINARY_OPERATORS: dict[type[ast.operator], str] = {
    ast.Add: "+",
    ast.Sub: "-",
    ast.Mult: "*",
    ast.Div: "/",
    ast.Pow: "**",
    ast.Mod: "%",
}

_UNARY_OPERATORS = (ast.UAdd, ast.USub)

# A tiny function whitelist. These cover the shapes that genuinely appear in case
# formulas (caps, floors, rounding for presentation) without opening the door to
# attribute access or arbitrary callables.
_FUNCTIONS = {
    "min": min,
    "max": max,
    "abs": abs,
    "round": round,
}

# Guards against a formula that is syntactically fine and computationally hostile.
# ``2 ** 2 ** 2 ** 2 ** 2`` is four operators and will not return.
MAX_NODES = 200
MAX_EXPONENT = 32


def _validate(node: ast.AST, names: set[str], node_budget: list[int]) -> None:
    """Reject anything outside the arithmetic subset, before evaluating."""
    node_budget[0] -= 1
    if node_budget[0] < 0:
        raise ExpressionError(f"Formula exceeds the {MAX_NODES} node limit")

    if isinstance(node, ast.Expression):
        _validate(node.body, names, node_budget)
        return
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise ExpressionError("Only numeric literals are allowed")
        return
    if isinstance(node, ast.Name):
        if not isinstance(node.ctx, ast.Load):
            raise ExpressionError("Assignment is not allowed in a formula")
        if node.id not in _FUNCTIONS:
            names.add(node.id)
        return
    if isinstance(node, ast.BinOp):
        if type(node.op) not in _BINARY_OPERATORS:
            raise ExpressionError(f"Operator {type(node.op).__name__} is not allowed")
        if isinstance(node.op, ast.Pow) and isinstance(node.right, ast.Constant):
            if abs(node.right.value) > MAX_EXPONENT:
                raise ExpressionError(f"Exponent above {MAX_EXPONENT} is not allowed")
        _validate(node.left, names, node_budget)
        _validate(node.right, names, node_budget)
        return
    if isinstance(node, ast.UnaryOp):
        if not isinstance(node.op, _UNARY_OPERATORS):
            raise ExpressionError(f"Operator {type(node.op).__name__} is not allowed")
        _validate(node.operand, names, node_budget)
        return
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in _FUNCTIONS:
            raise ExpressionError("Only min, max, abs and round may be called")
        if node.keywords:
            raise ExpressionError("Keyword arguments are not allowed")
        for argument in node.args:
            _validate(argument, names, node_budget)
        return

    raise ExpressionError(f"{type(node).__name__} is not allowed in a formula")


def referenced_names(formula: str) -> set[str]:
    """The variable names a formula depends on.

    Used by the validation gate to check that every input a formula needs is
    actually declared, which catches a synthesis pass that invented a variable.
    """
    try:
        tree = ast.parse(formula, mode="eval")
    except SyntaxError as error:
        raise ExpressionError(f"Formula is not valid syntax: {error.msg}") from error
    names: set[str] = set()
    _validate(tree, names, [MAX_NODES])
    return names


def evaluate(formula: str, variables: dict[str, float] | None = None) -> float:
    """Compute an authored formula against named numeric inputs.

    Raises :class:`ExpressionError` rather than returning a sentinel, because a
    formula that cannot be computed is an authoring defect that must fail the
    validation gate loudly rather than silently scoring as zero.
    """
    values = dict(variables or {})
    try:
        tree = ast.parse(formula, mode="eval")
    except SyntaxError as error:
        raise ExpressionError(f"Formula is not valid syntax: {error.msg}") from error

    names: set[str] = set()
    _validate(tree, names, [MAX_NODES])
    missing = sorted(names - values.keys())
    if missing:
        raise ExpressionError(f"Formula references undefined inputs: {', '.join(missing)}")

    for key, value in values.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ExpressionError(f"Input {key} is not numeric")

    def compute(node: ast.AST) -> float:
        if isinstance(node, ast.Expression):
            return compute(node.body)
        if isinstance(node, ast.Constant):
            return float(node.value)
        if isinstance(node, ast.Name):
            return float(values[node.id])
        if isinstance(node, ast.UnaryOp):
            operand = compute(node.operand)
            return -operand if isinstance(node.op, ast.USub) else +operand
        if isinstance(node, ast.Call):
            name = node.func.id  # type: ignore[union-attr]
            arguments = [compute(argument) for argument in node.args]
            if name == "round" and len(arguments) == 2:
                # Every value here is a float by construction, but round's digit
                # count must be an int, so coerce it rather than letting a
                # perfectly ordinary formula raise a TypeError.
                if arguments[1] != int(arguments[1]):
                    raise ExpressionError("round expects a whole number of digits")
                return float(round(arguments[0], int(arguments[1])))
            try:
                return float(_FUNCTIONS[name](*arguments))
            except TypeError as error:
                raise ExpressionError(f"{name} was called with unsupported arguments") from error
        if isinstance(node, ast.BinOp):
            left = compute(node.left)
            right = compute(node.right)
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
            if isinstance(node.op, (ast.Div, ast.Mod)):
                if right == 0:
                    raise ExpressionError("Formula divides by zero")
                return left / right if isinstance(node.op, ast.Div) else math.fmod(left, right)
            if isinstance(node.op, ast.Pow):
                if abs(right) > MAX_EXPONENT:
                    raise ExpressionError(f"Exponent above {MAX_EXPONENT} is not allowed")
                return float(left**right)
        raise ExpressionError(f"{type(node).__name__} is not allowed in a formula")

    try:
        result = compute(tree)
    except OverflowError as error:
        raise ExpressionError("Formula overflowed") from error
    if not math.isfinite(result):
        raise ExpressionError("Formula did not produce a finite number")
    return result


Verdict = Literal["exact", "close", "right_magnitude", "wrong"]


@dataclass(frozen=True)
class AnswerGrade:
    """How a candidate's number compares to the authored expected value."""

    verdict: Verdict
    ratio: float | None
    expected: float
    answered: float


# Defaults chosen for consulting math rather than for arithmetic. Interviewers
# expect aggressive rounding, so a quarter either way still reads as a correct
# answer, and being within a factor of two is the real accuracy bar. A magnitude
# error is the failure worth catching.
DEFAULT_CLOSE_TOLERANCE = 0.25
DEFAULT_MAGNITUDE_FACTOR = 2.0
# Used only when the expected value is zero, where ratios are undefined.
DEFAULT_ZERO_EPSILON = 1e-9


def grade_answer(
    expected: float,
    answered: float,
    *,
    close_tolerance: float = DEFAULT_CLOSE_TOLERANCE,
    magnitude_factor: float = DEFAULT_MAGNITUDE_FACTOR,
    zero_epsilon: float = DEFAULT_ZERO_EPSILON,
) -> AnswerGrade:
    """Band a candidate's answer the way an interviewer would.

    Ratio-based, because "within 25 percent" is the meaningful judgement and an
    absolute tolerance would be wrong at every scale but one.

    The zero case is handled separately and is not a hypothetical: a contribution
    margin of exactly zero is a common and pedagogically important answer, and
    dividing by it to form a ratio would crash the grader on precisely the cases
    the product most wants to teach.
    """
    if expected == 0:
        if abs(answered) <= zero_epsilon:
            return AnswerGrade("exact", None, expected, answered)
        # Without a scale there is no meaningful "close", so anything non-zero is
        # simply wrong rather than being graded against an invented denominator.
        return AnswerGrade("wrong", None, expected, answered)

    ratio = answered / expected
    if ratio == 1:
        return AnswerGrade("exact", ratio, expected, answered)
    # A sign flip is never "close", however small the magnitude difference: it is
    # the opposite commercial conclusion.
    if ratio <= 0:
        return AnswerGrade("wrong", ratio, expected, answered)
    if abs(ratio - 1) <= close_tolerance:
        return AnswerGrade("close", ratio, expected, answered)
    if 1 / magnitude_factor <= ratio <= magnitude_factor:
        return AnswerGrade("right_magnitude", ratio, expected, answered)
    return AnswerGrade("wrong", ratio, expected, answered)
