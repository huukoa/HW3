# Formula coverage — implementation map

Source of truth for formula flow: **Chapter3_Complete_Manual.pdf**. This document
maps already-established manual formulas to calculation-step presentation; it
does not change or re-prove the mathematical models.

| Model | Manual sections / equations | Code module | Expanded Results sequence |
|---|---|---|---|
| HW1 | §4.2–4.5, (4.1)–(4.8), Part II for convergence | `continuous.py::hw1` | holding → EOQ → rules once → iterations 1–2 → final Q, s, TC |
| HW3 | §4.6, (4.1)–(4.4) | `continuous.py::hw3` | EOQ → safety factor → three annual costs → increased-Q alternative |
| HW2 | §6.1–6.6, (6.2)–(6.5) | `periodic.py::hw2` | normalize periods → Qp, zp, sp → branch → A or B → whole units |
| HW4 | §8.1–8.5, (8.1)–(8.6), Part II bisection | `newsvendor.py::hw4` | costs → unconstrained spend → multiplier rule → first two midpoints → continuous quantities → integer budget and profit |
| HW6 | §9.1–9.5, (9.1)–(9.5), Part III loss formulas | `postponement.py::hw6` | original economics → original integer check → postponed economics → postponed integer check → profit difference |
| HW5 | §9.6–9.9, (9.6)–(9.12), Parts III/VII | `postponement.py::hw5` | separate economics → original quantities/profits → pooling → weighted underage → integer base comparison → expected profit |

## Presentation contract

1. Every expandable solution step contains at least one full numeric calculation
   chain, except that general symbolic update rules may be shown once before their
   numerical substitutions in iteration steps.
2. Bisection/fixed-point loops retain **all** iteration rows, but render numeric
   substitutions only for the **first two** iterations.
3. Every number in a formula is dynamically derived from that solve's inputs;
   reference examples are loaded through `examples.py`, not hard-coded answers.
4. No displayed formula is used to **perform** the calculation. The math engine
   returns the values and the UI/HTML report consumes the same `Step.equations`.
5. Model-specific boundaries are not forced through invalid interior inverse-CDF
   or square-root/log formulas. HW4's exactly-zero acquisition budget returns
   explicit zero quantities; otherwise the original continuous/bisection logic
   and bounded integer MILP are retained.
6. All formula chains and variable quantities are tested in
   `tests/test_formula_step_coverage.py`; the six numerical reference cases and
   additional edge cases remain in `tests/test_reference.py`.

## Verification commands

On the user's already active uv environment:

```powershell
uv run --active python -m pytest -q
uv run --active python main.py
```

The numerical and report tests pass in the authoring environment. A browser
rendering check for MathJax/KaTeX and accordion layout still requires the
user's installed NiceGUI runtime.
