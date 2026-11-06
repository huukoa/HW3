"""Break calculation chains at readable mathematical boundaries.

This transforms *presentation only*: the computation and original LaTeX equations
remain untouched. Each resulting fragment is independently valid math markup.
"""
from __future__ import annotations


def _soft_wrap_long_term(term: str, *, target: int = 55, limit: int = 80) -> list[str]:
    """Further split a long term only at *un-grouped* additive/product boundaries.

    This is intentionally conservative: fractions, radicals, and function calls
    must remain intact. Explicit multiplication is equivalent to juxtaposition.
    """
    parts: list[str] = []
    rest = term
    while len(rest) > limit:
        braces = parentheses = brackets = 0
        boundaries: list[tuple[int, str]] = []
        for index, char in enumerate(rest):
            if braces == parentheses == brackets == 0 and index >= 20:
                if char in '+-' and rest[index - 1] not in ('e', 'E'):
                    boundaries.append((index, 'add'))
                elif rest.startswith(r'\!\left', index):
                    boundaries.append((index, 'multiply'))
            if char == '{':
                braces += 1
            elif char == '}':
                braces -= 1
            elif char == '(':
                parentheses += 1
            elif char == ')':
                parentheses -= 1
            elif char == '[':
                brackets += 1
            elif char == ']':
                brackets -= 1
        candidates = [item for item in boundaries if 20 <= item[0] <= limit]
        if not candidates:
            break
        index, kind = min(candidates, key=lambda b: abs(b[0] - target))
        parts.append(rest[:index].strip())
        if kind == 'multiply':
            rest = r'\times' + rest[index + len(r'\!'):]
        else:
            rest = rest[index:]
    parts.append(rest.strip())
    return parts


def equation_fragments(equation: str) -> tuple[str, ...]:
    """Split top-level equals into fragments that can wrap independently.

    An equals sign inside a fraction, grouped expression, or parentheses remains
    inside that expression. The separator is carried by the following fragment
    so a line break visually reads ``= substitution`` rather than an orphan ``=``.
    """
    fragments: list[str] = []
    start = 0
    braces = parentheses = brackets = 0
    for index, char in enumerate(equation):
        if char == '{':
            braces += 1
        elif char == '}':
            braces -= 1
        elif char == '(':
            parentheses += 1
        elif char == ')':
            parentheses -= 1
        elif char == '[':
            brackets += 1
        elif char == ']':
            brackets -= 1
        elif char == '=' and braces == parentheses == brackets == 0:
            before = equation[start:index].strip()
            if before:
                fragments.append(before)
                start = index  # '=' stays attached to the next mathematical fragment
    tail = equation[start:].strip()
    if tail:
        fragments.append(tail)
    wrapped = [piece for fragment in fragments for piece in _soft_wrap_long_term(fragment)]
    return tuple(wrapped) or (equation,)


def plain_table_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    """Present LaTeX-formatted thousands separators as ordinary text in tables.

    The source equations and numerical values are not changed. `latex_num` emits
    ``1\\,026.799`` for math rendering; Quasar tables require ``1,026.799``.
    """
    return [{key: value.replace(r'\,', ',') if isinstance(value, str) else value
             for key, value in row.items()} for row in rows]
