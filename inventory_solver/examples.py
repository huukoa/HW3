"""Canonical source input sets and UI field contracts; not a cache of answers."""
from __future__ import annotations

from copy import deepcopy

HW_ORDER = ("HW1", "HW3", "HW2", "HW4", "HW6", "HW5")
TITLES = {
    "HW1": "Simultaneous (s, Q) · Iterative B1",
    "HW3": "Fixed EOQ · Expediting Cost",
    "HW2": "Periodic Review (R, s, S)",
    "HW4": "Budget-Constrained Newsvendor",
    "HW6": "Delayed Financial Commitment",
    "HW5": "Postponement · Value of Flexibility",
}
GROUPS = {
    "Class A · Continuous Review": ("HW1", "HW3"),
    "Periodic Review": ("HW2",),
    "Constrained Newsvendor": ("HW4",),
    "Postponement": ("HW6", "HW5"),
}
FIELDS = {
    "HW1": [("D", "Annual demand (units/year)"), ("v", "Unit acquisition cost ($/unit)"),
             ("A", "Fixed order cost ($/order)"), ("r", "Annual holding fraction"),
             ("B1", "Shortage charge ($/stockout event)"), ("muL", "Mean lead-time demand (units)"),
             ("sigmaL", "Lead-time demand SD (units)")],
    "HW3": [("D", "Annual demand (units/year)"), ("v", "Unit acquisition cost ($/unit)"),
             ("A", "Fixed order cost ($/order)"), ("r", "Annual holding fraction"),
             ("B1", "Expediting cost ($/event)"), ("muL", "Mean lead-time demand (units)"),
             ("sigmaL", "Lead-time demand SD (units)"), ("increase_pct", "Alternative Q increase (%)")],
    "HW2": [("D", "Annual demand (units/year)"), ("v", "Unit acquisition cost ($/unit)"),
             ("A", "Fixed order cost ($/order)"), ("r", "Annual holding fraction"),
             ("B3", "Fractional shortage charge / review period"),
             ("R", "Review interval (weeks)"), ("L", "Lead time (weeks)"),
             ("sigmaP", "Protection-period demand SD (units)"), ("weeks", "Weeks per year")],
    "HW4": [("W", "Acquisition budget ($)")],
    "HW6": [("mu", "Mean seasonal demand (units)"), ("sigma", "Seasonal demand SD (units)"),
             ("p", "Selling price ($/unit)"), ("v", "Finished product cost ($/unit)"),
             ("g", "Finished salvage value ($/unit)"), ("B", "Additional shortage penalty ($/unit)"),
             ("v0", "Base item cost ($/unit)"), ("t", "Finishing cost when sold ($/unit)"),
             ("g0", "Base salvage value ($/unit)")],
    "HW5": [("v0", "Unfinished base cost ($/unit)"), ("g0", "Base salvage value ($/unit)")],
}
ITEM_FIELDS = {
    "HW4": [("name", "Item"), ("p", "Selling price ($/unit)"), ("v", "Purchase cost ($/unit)"),
             ("g", "Salvage value ($/unit)"), ("B", "Shortage penalty ($/unit)"),
             ("mu", "Mean demand (units)"), ("sigma", "Demand SD (units)")],
    "HW5": [("name", "Design"), ("p", "Selling price ($/unit)"), ("v", "Finished cost ($/unit)"),
             ("g", "Finished salvage ($/unit)"), ("B", "Shortage penalty ($/unit)"),
             ("mu", "Mean demand (units)"), ("sigma", "Demand SD (units)"),
             ("t", "Finishing cost ($/sold unit)")],
}

# Symbols are display-only. Keys remain stable for calculation and Excel import.
NOTATION = {
    'D': 'D', 'v': 'v', 'A': 'A', 'r': 'r', 'B1': 'B₁', 'B3': 'B₃',
    'muL': 'μ_L', 'sigmaL': 'σ_L', 'R': 'R', 'L': 'L', 'sigmaP': 'σ_(R+L)',
    'weeks': 'N', 'increase_pct': 'ΔQ (%)', 'W': 'W', 'mu': 'μ',
    'sigma': 'σ', 'p': 'p', 'g': 'g', 'B': 'B', 'v0': 'v₀',
    'g0': 'g₀', 't': 't',
}


def field_caption(key: str, label: str) -> str:
    """Render a notation-prefixed input label without changing the stored key."""
    return f'{NOTATION[key]} — {label}' if key in NOTATION else label
EXAMPLES: dict[str, dict] = {
    "HW1": {"D": 2500, "v": 10, "A": 5, "r": 0.25, "B1": 100, "muL": 500, "sigmaL": 100},
    "HW3": {"D": 1920, "v": 20, "A": 15, "r": 0.2, "B1": 200, "muL": 150, "sigmaL": 60, "increase_pct": 5},
    "HW2": {"D": 800, "v": 1.5, "A": 20, "r": 0.26, "B3": 0.30, "R": 1, "L": 2, "sigmaP": 14.2, "weeks": 52},
    "HW4": {"W": 80000, "items": [
        {"name": "Snowblower 1", "v": 60, "p": 100, "g": 51, "B": 0, "mu": 540, "sigma": 170},
        {"name": "Snowblower 2", "v": 80, "p": 110, "g": 70, "B": 0, "mu": 300, "sigma": 50},
        {"name": "Snowblower 3", "v": 130, "p": 200, "g": 120, "B": 0, "mu": 200, "sigma": 40},
    ]},
    "HW6": {"mu": 200, "sigma": 50, "p": 400, "v": 250, "g": 50, "B": 300, "v0": 230, "t": 20, "g0": 50},
    "HW5": {"v0": 16, "g0": 5, "items": [
        {"name": "Design X", "p": 30, "v": 18, "g": 5, "B": 35, "mu": 100, "sigma": 50, "t": 1.5},
        {"name": "Design Y", "p": 40, "v": 18, "g": 5, "B": 35, "mu": 90, "sigma": 30, "t": 1.5},
    ]},
}


def example(model: str) -> dict:
    return deepcopy(EXAMPLES[model])


def input_columns(model: str) -> tuple[tuple[tuple[str, str], ...], tuple[tuple[str, str], ...]]:
    """Group fields vertically, never row-major across the two input columns.

    The three review/EOQ tasks keep D, v, A, r together in the first
    column and the model-specific data in the second. Other models use
    a balanced two-column layout; field identities stay unchanged.
    """
    fields = tuple(FIELDS[model])
    by_key = dict(fields)
    primary = ('D', 'v', 'A', 'r')
    if all(key in by_key for key in primary):
        left = tuple((key, by_key[key]) for key in primary)
        right = tuple(pair for pair in fields if pair[0] not in primary)
    else:
        midpoint = (len(fields) + 1) // 2
        left, right = fields[:midpoint], fields[midpoint:]
    return left, right
