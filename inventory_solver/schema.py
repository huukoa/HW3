"""Readable, UI-independent result contracts."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Step:
    title: str
    # Each equation is ONE chain: general formula = substituted values = result.
    equations: tuple[str, ...] = ()
    explanation: str = ""
    open_by_default: bool = False


@dataclass(frozen=True)
class Metric:
    label: str
    value: float | int | str
    unit: str = ""


@dataclass
class Solution:
    model: str
    title: str
    metrics: list[Metric] = field(default_factory=list)
    steps: list[Step] = field(default_factory=list)
    columns: list[dict[str, str]] = field(default_factory=list)
    rows: list[dict[str, Any]] = field(default_factory=list)
    comparisons: list[dict[str, Any]] = field(default_factory=list)
    notices: list[str] = field(default_factory=list)
    data: dict[str, Any] = field(default_factory=dict)


class ModelInputError(ValueError):
    """Validation error safe to present to a student."""
