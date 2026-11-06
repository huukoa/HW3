"""One stable dispatch interface for UI, tests and exports."""
from __future__ import annotations

from collections.abc import Callable, Mapping

from inventory_solver.continuous import hw1, hw3
from inventory_solver.newsvendor import hw4
from inventory_solver.periodic import hw2
from inventory_solver.postponement import hw5, hw6
from inventory_solver.general_models import hw4_general, hw5_poisson, hw6_general
from inventory_solver.schema import ModelInputError, Solution

SOLVERS: dict[str, Callable[[Mapping[str, object]], Solution]] = {
    "HW1": hw1, "HW3": hw3, "HW2": hw2,
    "HW4": hw4, "HW6": hw6, "HW5": hw5,
}


def solve(model: str, inputs: Mapping[str, object]) -> Solution:
    try:
        if model in ('HW1', 'HW3', 'HW2') and str(inputs.get('distribution', 'Normal')).lower() != 'normal':
            raise ModelInputError(f'{model}: this manual model requires Normal lead-time/protection demand.')
        if model == 'HW4' and isinstance(inputs.get('items'), list) and any(
                isinstance(i, dict) and str(i.get('distribution', 'Normal')).lower() != 'normal'
                for i in inputs['items']):
            return hw4_general(inputs)
        if model == 'HW6' and str(inputs.get('distribution', 'Normal')).lower() != 'normal':
            return hw6_general(inputs)
        if model == 'HW5' and isinstance(inputs.get('items'), list) and any(
                isinstance(i, dict) and str(i.get('distribution', 'Normal')).lower() != 'normal'
                for i in inputs['items']):
            return hw5_poisson(inputs)
        return SOLVERS[model](inputs)
    except KeyError as exc:
        raise ModelInputError(f"Unknown model: {model}") from exc
