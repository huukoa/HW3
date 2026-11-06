"""Normal loss functions, quantiles, safe numerics and input validation."""
from __future__ import annotations

import math
from collections.abc import Mapping

from scipy.stats import norm

from inventory_solver.schema import ModelInputError
from inventory_solver.numeric_input import parse_numeric


def number(values: Mapping[str, object], key: str, *, positive: bool = False, nonnegative: bool = False) -> float:
    try:
        value = parse_numeric(values[key], field=key)
    except KeyError as exc:
        raise ModelInputError(f"{key}: a value is required.") from exc
    if not math.isfinite(value):
        raise ModelInputError(f"{key}: value must be finite.")
    if positive and value <= 0:
        raise ModelInputError(f"{key}: must be > 0.")
    if nonnegative and value < 0:
        raise ModelInputError(f"{key}: must be >= 0.")
    return value


def ensure(condition: bool, message: str) -> None:
    if not condition:
        raise ModelInputError(message)


def normal_quantile(level: float) -> float:
    ensure(0 < level < 1, "Critical ratio must be strictly between 0 and 1.")
    return float(norm.ppf(level))


def loss(q: float, mu: float, sigma: float) -> tuple[float, float]:
    """Expected shortage, overage for X~N(mu,sigma**2); no premature rounding."""
    z = (q - mu) / sigma
    u = sigma * (norm.pdf(z) - z * norm.sf(z))
    # Guard tiny floating-point subtraction for extreme right tails.
    u = max(0.0, float(u))
    o = max(0.0, float(u + q - mu))
    return u, o


def optimal_normal_quantity(mu: float, sigma: float, cu: float, co: float) -> float:
    ensure(cu > 0 and co > 0, "Underage and overage costs must both be > 0.")
    return max(0.0, mu + sigma * normal_quantile(cu / (cu + co)))


def integer_normal_quantity(q: float, mu: float, sigma: float, cu: float, co: float) -> int:
    """Evaluate adjacent nonnegative integer decisions, not blind rounding."""
    a = max(0, math.floor(q))
    b = a + 1
    def objective(n: int) -> float:
        u, o = loss(float(n), mu, sigma)
        return cu * u + co * o
    return a if objective(a) <= objective(b) else b


def annual_cost_b1(q: float, k: float, d: float, a: float, b1: float, h: float, sigma: float) -> float:
    return d * (a + b1 * norm.sf(k)) / q + h * (q / 2 + k * sigma)


def latex_num(value: float, digits: int = 3) -> str:
    """Display-only; use '\\,' for thousands separators in LaTeX."""
    if not math.isfinite(value):
        return r"\mathrm{undefined}"
    displayed = f"{value:,.{digits}f}"
    return displayed.replace(",", r"\,")


def ratio_num(n: float, d: float) -> str:
    return rf"\frac{{{latex_num(n)}}}{{{latex_num(d)}}}"
