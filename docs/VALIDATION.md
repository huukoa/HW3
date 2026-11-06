# Validation and unresolved boundaries

## Evidence categories

- **Input evidence:** Assignment 3 DOCX, six numerical inputs. Source lecture: Chapter 3 slides 2–38, especially slide 54 GUI instructions. Instructor workbook `(s.Q)`, `periodic`, `Budget`, `Postpone` provides other, often differently numbered cases.
- **Mathematical model evidence:** supplied `Chapter3_Complete_Manual.pdf`: §4.5 HW1, §4.6 HW3, §6.6 HW2, §8.4–8.5 HW4, §9.5 HW6, §9.9 HW5. Manual appendix A lists high-precision numerical references. Textbook 1 §§7.3, 7.5.1, 9.3, 9.4.1, 9.4.2 confirm the structural formulas.
- **Executed checks:** `pytest` exercises the independent SciPy calculations, including a separate Normal-loss numerical integral and MILP integer result. Tests do not treat handwritten answers as an oracle independent of the manual.

## Example expectations (3-digit display)

| HW | Main result | Additional check |
|---|---|---|
| HW1 | Q=171.331, s=630.017 | k=1.300, relevant annual cost=753.370 |
| HW3 | Q=120.000, s=259.698 | TC=1,026.799; Q=126 TC=1,022.073 |
| HW2 | s=46, S=338 | Qp=291.708, sp=46.230, branch A |
| HW4 | Q_int=(547,268,198) | Spend=80,000, expected profit≈38,768.349 |
| HW6 | Original 225, postponed 228 | Continuous Q 225.120 vs 228.297; compare corresponding integer profits |
| HW5 | Original (139,117), pooled 245 | Approx. original profit 1,737.587; pooled 2,328.122 |

## Independent checks and limitations

- HW1 is verified against boundary k=0 and candidate extrema of a one-dimensional reduced cost function, which still uses a finite scan and local refinement. Extreme parameters may require a more rigorous global certified optimizer. The fixed-point iterate is not itself a global proof.
- HW2 revised power approximation is **empirical** and has a second branch when Qp/μR ≤ 1.5. Holding fractions must be per review period. Final integer rounding follows the lecture, not an exact discrete-cost minimization.
- HW4 continuous multiplier is bracketed by bisection; for whole-unit procurement, an integer unit-marginal MILP enforces the common budget. MILP solver status=0 is treated as a bounded-precision optimality certificate; never label a nonzero status as certified. Models with more than 12,000 candidate marginal units reject rather than silently return an unproven answer.
- HW6 compares continuous **with continuous** and integer **with integer** profit; the manual's published continuous profit gain is not the same number as the integer gain.
- HW5 uses demand-weighted FCFS underage as a **heuristic approximation**, following textbook Eq. 9.21 and the corrected finishing-cost convention in the manual. Not valid for priority allocation or demand timing correlated with product identity without revising the model.
- The original Homework examples use Normal demand. The new HW4/HW6 extension supports all six distributions in Manual Part III, and HW5 supports independent Normal or independent Poisson pooling. HW1/HW3/HW2 remain Normal-specific. Positive underage/overage requirements remain. Normal demand can assign a small probability to negative values when μ/σ is small.
- For uploaded workbooks, instructor `Postpone` sheet consists mostly of output examples and **cannot** serve as HW5/HW6 full inputs; the included editable template does.

## Technical verification environment

The project was authored for Python 3.12 and NiceGUI 3.x. Its numeric engine/tests were executable in the authoring environment with Python 3.13 and the available SciPy/NumPy/openpyxl/pytest. The authoring environment has **no outbound DNS connectivity and no NiceGUI installation**, and it could not download Python 3.12. Therefore no browser-based UI smoke test or end-to-end Render deployment can honestly be claimed from this environment. Run `uv sync && uv run pytest -q && uv run python main.py` locally with internet; verify in a browser before pushing to a public host.

## Numeric-expression input extension

The web form now uses NiceGUI text inputs rather than fixed-format number widgets. The
shared `numeric_input.parse_numeric` parser accepts signed integer/decimal/scientific
literals, fractions, parentheses, `+ - * /`, integer powers `^`/`**`, `sqrt(x)` and `pi`.
Literal decimal arithmetic and fractions are evaluated with `fractions.Fraction`
before converting to float64 for the NumPy/SciPy model computations. It **does not**
execute Python code, nor evaluate Excel workbook formulas. Inputs remain subject to
the original model-specific feasibility and economic restrictions.

Regression tests cover all six original examples rewritten as text expressions,
malformed and malicious inputs, nonfinite values, large exponents, Excel plain-text
expressions, and uncached Excel formula rejection. The local authoring environment
passed `python -m pytest -q` with **140 tests** on Python 3.13,
including 19 step-equation coverage tests. Actual NiceGUI browser
interaction is not verified in this environment; users should run the existing
Windows/Python 3.12 NiceGUI smoke check after replacing the source files.

## UI theory and vertical input columns (November 2026)

The expanded Theory content follows the supplied Chapter3 Complete Manual and is mapped in `docs/THEORY_MAP.md`. HW1/3/2 keep `D, v, A, r` in the left input column; model-specific fields are in the right column. These UI changes do not alter the six numerical solvers. The latest full regression run reports **170 passed** (including layout and manual-section coverage tests). NiceGUI browser rendering must still be checked on the user's machine.

## Demand distribution extension (current revision)

`inventory_solver/distributions.py` implements the Part III CDF, generalized inverse and expected shortage for Normal, Uniform, Exponential, Geometric (support 0,1,...), Poisson and finite discrete PMFs. The generic Newsvendor adapters are in `general_models.py`; the original Normal solvers remain unchanged. The extension includes a new dynamic distribution selector in the Input UI, Theory formulas and `examples/distribution_inputs.xlsx`.

For HW4, the integer MILP remains the budget-constrained decision. When the CDF has jumps, the bisection output represents a multiplier reference (the continuous KKT root need not exist); exact whole-unit feasibility and the MILP objective determine the result. HW5 supports all-Normal or all-Poisson independent pooled demand, not arbitrary mixed families. Tests include Manual Part III numerical checks and a brute-force crosscheck of a small mixed-distribution HW4 case.

The authoring container does not have NiceGUI installed, so the live browser dropdown and Excel upload still need a smoke test on Windows/Python 3.12 with `uv run --active python main.py`.

## Sensitivity regression coverage (2026-11-06)

The earlier sensitivity release had **247 passing checks** in this environment. The Sensitivity feature is implemented as an independent wrapper around existing solver functions (no change to the six canonical homework algorithms). New checks cover all six input sweeps, unchanged baselines, preserved source inputs, per-product parameters, HW4 integer budget feasibility, Normal/Poisson distribution adapters, custom Discrete exclusions, zero and invalid scenarios, the HW3 exact EOQ +5% comparison, HW1 EOQ versus optimized Q* references, custom Q changes and the fourth GUI tab. The patch was applied onto the earlier 170-test release and retested separately from the complete-source archive.

This is **numerical + source-structure validation**, not an end-to-end browser/Windows certification. The available runner lacks NiceGUI and cannot fetch it from PyPI; use the existing NiceGUI installation on the user's machine for browser verification.

## Slider dashboard regression (current revision)

The current source has **266/266 passing checks** on Python 3.13 in the authoring environment. A new interactive Sensitivity dashboard precomputes 5%-spaced scenarios (5/11/21
points for ±10/25/50%), then updates metric cards and four chart markers from
cached results. `tests/test_dashboard.py` checks all six Homework outputs,
HW3 EOQ+5% (`Q=126`, `TC≈1022.073`), unchanged input dictionaries, chart axis
values/markers, zero-baseline percentages, and explicitly unavailable invalid
scenarios. Live browser rendering on NiceGUI/Windows still needs local testing.
