# Demand distributions — Manual Part III

The application implements **Normal, Uniform, Exponential, Geometric, Poisson, and arbitrary finite Discrete** demand, using the CDF, generalized quantile and expected shortage identities from *Chapter3_Complete_Manual.pdf*, Parts I and III.

## Where distribution selection is available

| Model | Choices | Computation |
|---|---|---|
| HW1 / HW3 | Normal only | The manual's Normal-specific B₁ safety-factor formula and fixed-point or fixed-EOQ policy |
| HW2 | Normal only | The manual's Normal-specific revised-power approximation |
| HW4 | All six, **per item**, mixed distributions allowed | Critical fractiles, optional multiplier reference, exact integer-unit budget MILP |
| HW6 | All six | Original versus postponed order and expected profit using the selected distribution's quantile and expected shortages |
| HW5 | **All Normal** or **all Poisson** | Independent Normal pooling or independent Poisson pooling; FCFS mean-demand-weighted underage cost |

The six canonical homework examples still default to Normal and produce their original expected results. We intentionally do **not** extrapolate HW1, HW3 or HW2 formulas to unrelated demand distributions. In HW5, independent Uniform/Exponential/Geometric/Discrete pooling has no standard closed form in the supplied manual; the app gives a clear validation error instead of computing an unjustified pooled distribution.

## Input fields

| Distribution | Enter | Example | Meaning |
|---|---|---|---|
| Normal | `mu`, `sigma` | `200`, `50` | Mean μ and standard deviation σ |
| Uniform | `a`, `b` | `100`, `300` | Endpoints a, b with a < b |
| Exponential | `rate` | `1/200` | λ > 0; mean is 1/λ |
| Geometric | `rho` | `1/2` | 0 < ρ < 1; support starts at **zero** |
| Poisson | `lam` | `200` | λ > 0, mean and variance |
| Discrete | `support`, `probabilities` | `0,1,3` and `0.2,0.5,0.3` | Matching finite lists of **integer** demand values and probabilities |

Fractions and arithmetic work in each numeric field, e.g. `1/52` and `sqrt(4)`. For a Discrete probability list, each comma-separated entry may itself be a fraction; probabilities must total 1 (tolerance 1e-9) and support values must be unique nonnegative integers. Discrete ordering is by integer demand units; sorting of support values is handled internally.

## Calculation contract

For an arbitrary supported demand X with mean μ:

```text
cu = p - v + B
co = v - g
alpha = cu / (cu + co)
q* = smallest q with F_X(q) >= alpha
U(q) = E[max(X-q, 0)]
O(q) = U(q) + q - mu
E[profit(q)] = (p-v)*mu - cu*U(q) - co*O(q)
```

For continuous distributions, the best **integer** order is selected by comparing adjacent whole-unit objective values. For discrete distributions, the generalized CDF quantile is already a valid integer decision. HW4 uses marginal-unit integer optimization under the shared budget; a zero-budget input returns zero orders exactly. For a mixed-distribution HW4 problem with jumps in the CDF, the displayed `M` and `Q_ref` are **dual/reference** values rather than an asserted continuous KKT optimum; the integer MILP is the actual budget-constrained decision. A time-limited MILP is never marked globally certified unless its solver status confirms optimality.

## Excel Import

The original `examples/inventory_inputs.xlsx` still works unchanged for the Normal homework examples. Use **Distribution template** in the Input tab to download `examples/distribution_inputs.xlsx`, with three editable example pairs:

- `HW4` + `Items HW4`: two items using Uniform and Discrete distributions;
- `HW5` + `Items HW5`: two Poisson designs;
- `HW6`: one Exponential demand model.

For HW6, worksheet column A holds names `p`, `v`, `g`, `B`, `v0`, `t`, `g0`, `distribution`, and the selected distribution's parameter names; column B holds values. The `mu` and `sigma` rows are only needed for Normal.

For HW4/HW5, the `Items HW4` / `Items HW5` worksheets hold each item's `distribution` column and the applicable parameter columns. Blank cells for **other** distributions are ignored. For Normal items, provide `mu` and `sigma` columns. For Poisson items, provide `lam`. For Discrete, fill the `support` and `probabilities` cells as literal text.

The instructor workbook imports continue to map to their original Normal-based worked examples. The uploaded workbook is read in memory; no server-side persistent storage is added.

## Verification

Run `uv run --active python -m pytest -q` on the user's existing activated uv environment. The distribution tests cover the manual's discrete/Geometric/Poisson/Exponential numeric examples, the CDF and shortage formulas, parameter validation, HW4 mixed-budget brute-force crosschecks, HW5 Poisson pooling, all six HW6 distributions, the new Excel template, and unchanged Normal homework results. Test the actual dropdown in a browser with `uv run --active python main.py`.
