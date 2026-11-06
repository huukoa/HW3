"""One-at-a-time input sensitivity and fixed-Q comparisons for all six models.

All input sweeps call the canonical :func:`solve`; no shadow inventory models.
The separate fixed-Q sweep reuses the same B1 policy primitives as HW1/HW3.
No sweep modifies the caller's inputs or its displayed baseline solution.
"""
from __future__ import annotations

import math
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Mapping

from inventory_solver.common import annual_cost_b1, number
from inventory_solver.continuous import _base, _inputs, _safety_for_q
from inventory_solver.distributions import PARAMETERS
from inventory_solver.examples import FIELDS, ITEM_FIELDS, field_caption
from inventory_solver.schema import ModelInputError, Solution
from inventory_solver.solve import solve


@dataclass(frozen=True)
class Parameter:
    path: str
    label: str
    value: float


@dataclass(frozen=True)
class Output:
    key: str
    label: str
    unit: str = ''


@dataclass(frozen=True)
class Point:
    change: float       # percentage for relative sweeps, input units for absolute sweeps
    value: float        # actual input value or fixed order quantity
    metrics: dict[str, float] | None
    error: str = ''
    quality: str = ''


@dataclass(frozen=True)
class Study:
    model: str
    mode: str
    variable: str
    baseline_value: float
    outputs: tuple[Output, ...]
    baseline: dict[str, float]
    points: tuple[Point, ...]
    delta_key: str
    x_label: str
    note: str = ''
    highlight_change: float | None = None




@dataclass(frozen=True)
class MetricComparison:
    """One dashboard tile; an invalid scenario never borrows baseline values."""
    key: str
    label: str
    unit: str
    baseline: float
    current: float | None
    delta: float | None
    percent: float | None


def dashboard_point(study: Study, change: float) -> Point:
    """Select a precomputed scenario without re-running the inventory solver."""
    if not math.isfinite(change):
        raise ModelInputError('Slider position must be finite.')
    for point in study.points:
        if math.isclose(point.change, change, abs_tol=1e-8, rel_tol=0):
            return point
    raise ModelInputError('Selected percentage is outside the precomputed slider positions.')


def dashboard_comparisons(study: Study, change: float) -> tuple[MetricComparison, ...]:
    """Baseline, adjusted result and change for *every* available output."""
    point = dashboard_point(study, change)
    items: list[MetricComparison] = []
    for output in study.outputs:
        before = study.baseline[output.key]
        if point.metrics is None:
            items.append(MetricComparison(output.key, output.label, output.unit,
                                          before, None, None, None))
            continue
        after = point.metrics[output.key]
        diff = after - before
        percent = 100 * diff / abs(before) if before != 0 else None
        items.append(MetricComparison(output.key, output.label, output.unit,
                                      before, after, diff, percent))
    return tuple(items)


def dashboard_chart_options(study: Study, key: str, change: float) -> dict[str, Any]:
    """One independently scaled mini-chart, including the selected slider marker."""
    output = next((output for output in study.outputs if output.key == key), None)
    if output is None:
        raise ModelInputError('Unknown chart metric.')
    selected = dashboard_point(study, change)
    data = [[float(p.change), round(float(p.metrics[key]), 10) if p.metrics else None]
            for p in study.points]
    highlight = ([{'name': 'Selected', 'coord': [float(change),
                                                 float(selected.metrics[key])],
                   'itemStyle': {'color': '#1d649b'}, 'symbolSize': 11}]
                 if selected.metrics else [])
    return {
        'animation': False,
        'tooltip': {'trigger': 'axis'},
        'grid': {'left': 68, 'right': 22, 'top': 24, 'bottom': 42, 'containLabel': False},
        'xAxis': {'type': 'value', 'name': '% change' if study.mode == 'Fixed Q' or
                  study.x_label.endswith('(% change)') else 'Absolute change',
                  'nameLocation': 'middle', 'nameGap': 28,
                  'min': float(study.points[0].change),
                  'max': float(study.points[-1].change)},
        'yAxis': {'type': 'value', 'scale': True,
                  'axisLabel': {'hideOverlap': True}},
        'series': [{'type': 'line', 'name': output.label,
                    'data': data, 'smooth': False,
                    'lineStyle': {'width': 2, 'color': '#5794c6'},
                    'itemStyle': {'color': '#5794c6'},
                    'showSymbol': False,
                    'connectNulls': False,
                    'markLine': {'silent': True, 'symbol': 'none',
                                 'label': {'show': False},
                                 'lineStyle': {'type': 'dashed', 'width': 1, 'color': '#94a9c0'},
                                 'data': [{'xAxis': 0.0}, {'xAxis': float(change)}]},
                    'markPoint': {'data': highlight}}],
    }

def _family(row: Mapping[str, Any]) -> str:
    return str(row.get('distribution', 'Normal'))


def available_parameters(model: str, raw: Mapping[str, Any]) -> tuple[Parameter, ...]:
    """Only expose numeric fields valid for the selected model/distribution.

    Paths are generated by this function, not accepted as free-form expressions.
    Custom discrete PMF tables stay editable in Input but are not scalar sweeps.
    """
    if model not in FIELDS:
        raise ModelInputError(f'Unsupported model: {model}')
    choices: list[Parameter] = []

    def append(row: Mapping[str, Any], prefix: str, fields: list[tuple[str, str]]) -> None:
        family = _family(row)
        for key, label in fields:
            if key == 'name' or (key in ('mu', 'sigma') and family != 'Normal'):
                continue
            if key not in row:
                continue
            choices.append(Parameter(prefix + key, field_caption(key, label), number(row, key)))
        for key, label in PARAMETERS.get(family, ()):
            if key in ('support', 'probabilities') or key not in row:
                continue
            if any(x.path == prefix + key for x in choices):
                continue
            choices.append(Parameter(prefix + key, label, number(row, key)))

    append(raw, '', FIELDS[model])
    if model in ITEM_FIELDS:
        rows = raw.get('items', [])
        if not isinstance(rows, list):
            raise ModelInputError('Products must be a list.')
        for i, item in enumerate(rows):
            if not isinstance(item, dict):
                raise ModelInputError(f'Product {i + 1} must be a mapping.')
            start = len(choices)
            append(item, f'items:{i}:', ITEM_FIELDS[model])
            tag = str(item.get('name') or f'Item {i + 1}')
            for j in range(start, len(choices)):
                p = choices[j]
                choices[j] = Parameter(p.path, f'{tag} · {p.label}', p.value)
    return tuple(choices)


def _replace(raw: Mapping[str, Any], chosen: Parameter, value: float) -> dict[str, Any]:
    copied = deepcopy(dict(raw))
    if chosen.path.startswith('items:'):
        _, row, key = chosen.path.split(':', 2)
        copied['items'][int(row)][key] = value
    else:
        copied[chosen.path] = value
    return copied


def outputs_for(model: str, solution: Solution, raw: Mapping[str, Any]) -> tuple[dict[str, float], tuple[Output, ...], str]:
    """Semantic numeric metrics from existing solver data, never formatted strings."""
    data = solution.data
    metrics: dict[str, float] = {}
    labels: list[Output] = []

    def put(key: str, label: str, value: Any, unit: str = '') -> None:
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
            raise ModelInputError(f'Non-finite sensitivity result for {label}.')
        metrics[key] = float(value)
        labels.append(Output(key, label, unit))

    if model in ('HW1', 'HW3'):
        q = data['Q'] if model == 'HW1' else data['EOQ']
        s, k = data['s'], data['k']
        h = number(raw, 'v', positive=True) * number(raw, 'r', positive=True)
        d, a = number(raw, 'D', positive=True), number(raw, 'A', positive=True)
        sig, b = number(raw, 'sigmaL', positive=True), number(raw, 'B1', positive=True)
        from scipy.stats import norm
        put('Q', 'Order quantity Q', q, 'units')
        put('s', 'Reorder point s', s, 'units')
        put('SS', 'Safety stock SS', k * sig, 'units')
        put('k', 'Safety factor k', k)
        put('TC', 'Annual relevant cost TC', data['cost'], '$/year')
        put('order', 'Ordering cost', a * d / q, '$/year')
        put('hold', 'Holding cost', h * (q / 2 + k * sig), '$/year')
        put('stockout', 'Expediting / stockout cost', d * b / q * norm.sf(k), '$/year')
        if model == 'HW3':
            put('Q_alt', 'Alternative Q', data['Q_alt'], 'units')
            put('s_alt', 'Alternative s', data['s_alt'], 'units')
            put('TC_alt', 'Alternative annual cost', data['cost_alt'], '$/year')
            put('savings', 'Annual savings', data['savings'], '$/year')
        return metrics, tuple(labels), 'TC'

    if model == 'HW2':
        put('Qp', 'Power-approx. Qp', data['Qp'], 'units')
        put('s', 'Reorder point s', data['s'], 'units')
        put('S', 'Order-up-to level S', data['S'], 'units')
        put('s_whole', 'Rounded s', data['s_integer'], 'units')
        put('S_whole', 'Rounded S', data['S_integer'], 'units')
        put('buffer', 'Protection buffer s − μP', data['s'] - data['muP'], 'units')
        put('ratio', 'Branch ratio Qp / μR', data['ratio'])
        return metrics, tuple(labels), 's'

    if model == 'HW4':
        sizes = data['integer_q']
        put('Q_total', 'Total integer quantity', sum(sizes), 'units')
        for i, item_q in enumerate(sizes):
            item = raw['items'][i]
            name = str(item.get('name') or f'Item {i + 1}')
            put(f'Q_{i}', f'{name} · Integer Q', item_q, 'units')
        put('spend', 'Budget used', data['spend'], '$')
        put('remaining', 'Budget remaining', data['budget'] - data['spend'], '$')
        put('profit', 'Total expected profit', data['profit'], '$')
        put('M', 'Multiplier reference M', data['M'])
        return metrics, tuple(labels), 'profit'

    if model == 'HW6':
        put('Q_original', 'Original integer Q', data['Q_original_int'], 'units')
        put('Q_post', 'Postponed integer Q', data['Q_post_int'], 'units')
        put('profit_original', 'Original expected profit', data['profit_original_int'], '$')
        put('profit_post', 'Postponed expected profit', data['profit_post_int'], '$')
        put('gain', 'Expected profit improvement', data['gain_int'], '$')
        return metrics, tuple(labels), 'gain'

    if model == 'HW5':
        originals = data['Q_original_int']
        put('Q_total', 'Original total Q', sum(originals), 'units')
        for i, q in enumerate(originals):
            name = str(raw['items'][i].get('name') or f'Design {i + 1}')
            put(f'Q_{i}', f'{name} · Original Q', q, 'units')
        put('Q_pool', 'Pooled base Q', data['Q_post_int'], 'units')
        put('profit_original', 'Original expected profit', data['profit_original'], '$')
        put('profit_post', 'Pooled expected profit (approx.)', data['profit_post_approx'], '$')
        put('gain', 'Estimated profit improvement', data['gain_approx'], '$')
        return metrics, tuple(labels), 'gain'
    raise ModelInputError(f'Unsupported model: {model}')


def _grid(radius: float, points: int) -> tuple[float, ...]:
    if not math.isfinite(radius) or not (0 < radius <= 200):
        raise ModelInputError('Sweep range must be > 0 and ≤ 200.')
    if points not in (5, 7, 9, 11, 21):
        raise ModelInputError('Use 5, 7, 9, 11 or 21 scenario points.')
    return tuple(radius * (2 * j / (points - 1) - 1) for j in range(points))


def input_study(model: str, raw: Mapping[str, Any], parameter: str, *, radius: float = 20,
                points: int = 9, scale: str = 'Percent') -> Study:
    """Re-solve changed input independently at every scenario; original data untouched."""
    candidates = {p.path: p for p in available_parameters(model, raw)}
    if parameter not in candidates:
        raise ModelInputError('Choose a numeric input in this model before running sensitivity.')
    chosen = candidates[parameter]
    if scale not in ('Percent', 'Absolute'):
        raise ModelInputError('Variation must be Percent or Absolute.')
    if scale == 'Percent' and chosen.value == 0:
        raise ModelInputError(f'{chosen.label} is zero: select Absolute variation to change it.')
    changes = _grid(radius, points)
    baseline_solution = solve(model, deepcopy(dict(raw)))
    baseline, outputs, delta = outputs_for(model, baseline_solution, raw)
    rows: list[Point] = []
    for change in changes:
        val = chosen.value * (1 + change / 100) if scale == 'Percent' else chosen.value + change
        try:
            if change == 0:
                metrics = baseline
                result = baseline_solution
            else:
                candidate = _replace(raw, chosen, val)
                result = solve(model, candidate)
                metrics, current_outputs, _ = outputs_for(model, result, candidate)
                if tuple(out.key for out in current_outputs) != tuple(out.key for out in outputs):
                    raise ModelInputError('Output metric set changed across scenarios.')
            quality = ''
            if model == 'HW4' and 'not certified' in str(result.data.get('integer_quality', '')).lower():
                quality = 'Feasible (not certified optimal)'
            rows.append(Point(change, float(val), dict(metrics), quality=quality))
        except (ModelInputError, ValueError, OverflowError, ZeroDivisionError) as exc:
            rows.append(Point(change, float(val), None, str(exc)))
    return Study(model, 'Input', chosen.label, chosen.value, outputs, baseline,
                 tuple(rows), delta, f'{chosen.label} ({"% change" if scale == "Percent" else "absolute change"})',
                 'One input changes at a time; other inputs stay fixed.')


def fixed_q_study(model: str, raw: Mapping[str, Any], *, radius: float = 20,
                  points: int = 9, reference: str = 'EOQ', specific_pct: float = 5) -> Study:
    """Sweep fixed order quantities; re-optimize k and s at each Q, not Q itself.

    HW1 offers EOQ or jointly optimized Q* as a reference. HW3 uses EOQ.
    """
    if model not in ('HW1', 'HW3'):
        raise ModelInputError('Change Q / EOQ is available only for HW1 and HW3.')
    if reference not in ('EOQ', 'Optimized Q*') or (model != 'HW1' and reference != 'EOQ'):
        raise ModelInputError('Invalid Q reference for this model.')
    values = _inputs(raw)
    h, eoq, c = _base(values)
    baseline_solution = solve(model, deepcopy(dict(raw)))
    base_q = eoq if reference == 'EOQ' else baseline_solution.data['Q']
    percent_grid = _grid(radius, points)
    if not math.isfinite(specific_pct) or not (-100 < specific_pct <= 1000):
        raise ModelInputError('Specific Q change must be > -100% and ≤ 1000%.')
    if not any(abs(change - specific_pct) < 1e-9 for change in percent_grid):
        percent_grid = tuple(sorted((*percent_grid, float(specific_pct))))
    from scipy.stats import norm

    def evaluate(q: float) -> dict[str, float]:
        k = _safety_for_q(q, c)
        sig = values['sigmaL']
        order = values['A'] * values['D'] / q
        hold = h * (q / 2 + k * sig)
        expedite = values['D'] * values['B1'] * norm.sf(k) / q
        return {'Q': q, 's': values['muL'] + k * sig, 'SS': k * sig, 'k': k,
                'TC': annual_cost_b1(q, k, values['D'], values['A'], values['B1'], h, sig),
                'order': order, 'hold': hold, 'stockout': expedite}

    outputs = (Output('Q', 'Fixed order quantity Q', 'units'),
               Output('s', 'Reorder point s', 'units'), Output('SS', 'Safety stock SS', 'units'),
               Output('k', 'Safety factor k'), Output('TC', 'Annual relevant cost TC', '$/year'),
               Output('order', 'Ordering cost', '$/year'), Output('hold', 'Holding cost', '$/year'),
               Output('stockout', 'Expediting / stockout cost', '$/year'))
    rows = [Point(change, base_q * (1 + change / 100), evaluate(base_q * (1 + change / 100)))
            if 1 + change / 100 > 0 else Point(change, 0.0, None, 'Q must be positive.')
            for change in percent_grid]
    return Study(model, 'Fixed Q', f'Q relative to {reference}', float(base_q), outputs,
                 evaluate(base_q), tuple(rows), 'TC', f'Q change from {reference} (%)',
                 'Q is held fixed in each scenario; safety factor k and reorder point s are recalculated. '
                 f'EOQ = {eoq:,.3f}; jointly optimized Q* = {baseline_solution.data["Q"]:,.3f}.'
                 if model == 'HW1' else
                 'Q is held fixed in each scenario; safety factor k and reorder point s are recalculated.',
                 highlight_change=specific_pct)
