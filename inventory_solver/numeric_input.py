"""Parse student-entered arithmetic safely, keeping rational math exact until conversion.

Accepted: integers, decimal/scientific literals, fractions, + - * /, power (^ or **),
parentheses, sqrt(x), and pi. Deliberately no eval, attributes, names, indexing,
comprehensions or arbitrary function calls. All model computations remain float64.
"""
from __future__ import annotations

import ast
import math
import operator
import re
from decimal import Decimal
from fractions import Fraction
from typing import Any

from inventory_solver.schema import ModelInputError

_MAX_INPUT_LENGTH = 200
_MAX_TREE_NODES = 80
_MAX_RATIONAL_BITS = 2048
_MAX_ABS_EXPONENT = 12
_BINARY_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}


def _bound(value: Fraction) -> Fraction:
    """Prevent giant intermediate numerators/denominators from abusive expressions."""
    if max(value.numerator.bit_length(), value.denominator.bit_length()) > _MAX_RATIONAL_BITS:
        raise ModelInputError('Expression produces numbers too large to calculate safely.')
    return value


def parse_numeric(value: Any, *, field: str = 'Value') -> float:
    """Safely turn one numeric field into finite float for existing numerical solvers.

    Decimal text and fractions are evaluated exactly with Fraction first; the
    final conversion to binary64 is necessary for scipy/numpy-based calculations.
    """
    if isinstance(value, bool):
        raise ModelInputError(f'{field}: enter a number, not true/false.')
    if isinstance(value, (int, float, Decimal, Fraction)):
        try:
            result = float(value)
        except (OverflowError, ValueError) as exc:
            raise ModelInputError(f'{field}: value is outside supported numeric range.') from exc
        if not math.isfinite(result) or (result == 0 and value != 0):
            raise ModelInputError(f'{field}: value is outside supported numeric precision or range.')
        return result
    if not isinstance(value, str):
        raise ModelInputError(f'{field}: enter a number or arithmetic expression.')

    source = value.strip()
    if not source:
        raise ModelInputError(f'{field}: this field cannot be empty.')
    if len(source) > _MAX_INPUT_LENGTH:
        raise ModelInputError(f'{field}: expression is too long (max {_MAX_INPUT_LENGTH} characters).')
    # Accept common calculator caret syntax; AST then enforces normal power precedence.
    normalized = source.replace('^', '**').replace('×', '*').replace('÷', '/')
    try:
        tree = ast.parse(normalized, mode='eval')
    except (SyntaxError, ValueError, RecursionError) as exc:
        raise ModelInputError(f'{field}: invalid arithmetic expression.') from exc
    if sum(1 for _ in ast.walk(tree)) > _MAX_TREE_NODES:
        raise ModelInputError(f'{field}: expression is too complex.')

    def compute(node: ast.AST, depth: int = 0) -> Fraction:
        if depth > 24:
            raise ModelInputError(f'{field}: parentheses/expression nesting is too deep.')
        if isinstance(node, ast.Expression):
            return compute(node.body, depth + 1)
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            # Recover lexical decimal text: ast.Constant float would lose precision.
            literal = ast.get_source_segment(normalized, node)
            try:
                token = literal if literal is not None else str(node.value)
                exp = re.search(r'[eE]([+-]?\d+)$', token)
                if exp is not None and abs(int(exp.group(1))) > 300:
                    raise ModelInputError(f'{field}: scientific exponent is too large (max ±300).')
                return _bound(Fraction(token))
            except (ValueError, ZeroDivisionError) as exc:
                raise ModelInputError(f'{field}: invalid numeric literal.') from exc
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            v = compute(node.operand, depth + 1)
            return v if isinstance(node.op, ast.UAdd) else -v
        if isinstance(node, ast.BinOp):
            left = compute(node.left, depth + 1)
            right = compute(node.right, depth + 1)
            if type(node.op) in _BINARY_OPERATORS:
                if isinstance(node.op, ast.Div) and right == 0:
                    raise ModelInputError(f'{field}: division by zero.')
                return _bound(_BINARY_OPERATORS[type(node.op)](left, right))
            if isinstance(node.op, ast.Pow):
                if right.denominator != 1 or abs(right.numerator) > _MAX_ABS_EXPONENT:
                    raise ModelInputError(f'{field}: exponent must be a whole number from -12 to 12.')
                if left == 0 and right <= 0:
                    raise ModelInputError(f'{field}: zero cannot have a nonpositive exponent.')
                return _bound(left ** right.numerator)
        if isinstance(node, ast.Name) and node.id == 'pi':
            return Fraction(str(math.pi))
        if isinstance(node, ast.Call):
            if (isinstance(node.func, ast.Name) and node.func.id == 'sqrt' and
                    len(node.args) == 1 and not node.keywords):
                v = compute(node.args[0], depth + 1)
                if v < 0:
                    raise ModelInputError(f'{field}: sqrt requires a nonnegative value.')
                numerator, denominator = math.isqrt(v.numerator), math.isqrt(v.denominator)
                if numerator * numerator == v.numerator and denominator * denominator == v.denominator:
                    return Fraction(numerator, denominator)
                try:
                    return _bound(Fraction(str(math.sqrt(float(v)))))
                except (OverflowError, ValueError) as exc:
                    raise ModelInputError(f'{field}: square root is outside supported range.') from exc
        raise ModelInputError(
            f'{field}: only numbers, fractions, + - * / ^, parentheses, sqrt(x) and pi are allowed.'
        )

    exact = compute(tree)
    try:
        result = float(exact)
    except (OverflowError, ValueError) as exc:
        raise ModelInputError(f'{field}: value is outside supported numeric range.') from exc
    if not math.isfinite(result) or (result == 0.0 and exact != 0):
        raise ModelInputError(f'{field}: result is outside supported numeric precision or range.')
    return result
