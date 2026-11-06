# Full Theory mapping: Chapter3 Complete Mathematical Manual

The source of the theory text and equations in the web interface is the user-supplied `Chapter3_Complete_Manual.pdf`. The theory is organized by **homework decision model**, not by repeating one chapter for every homework. Sections have the manual's numbering to make cross-reference possible.

| UI model | Manual coverage in Theory | No-repeat structure |
| --- | --- | --- |
| HW1 — Simultaneous (s,Q) | §§4.1–4.4, plus §2.6 and §2.8 for convergence/rounding | Primary location for Class A, EOQ differentiation, B₁ cost objective, two FOCs, fixed point, Hessian and convergence |
| HW3 — Fixed EOQ & Expediting | §4.6 and fixed-Q formula from §4.3 | Refers to HW1 for EOQ and B₁ derivations; contains fixed-Q cost decomposition and 5% sensitivity |
| HW2 — Periodic (R,s,S) | §§6.1–6.8 | Complete review/protection-period policy, fitted power equations, Branch A and Branch B |
| HW4 — Budgeted Multi-item Newsvendor | §1.1–1.7, §3.1, §§7.1–7.4, §2.3, §§8.1–8.5 | Primary location for Newsvendor expected loss/profit, Normal shortage, KKT and budget multiplier; integer feasibility |
| HW6 — Delayed Financial Commitment | §§9.1–9.5 | Refers to HW4 for shared Newsvendor proof, focuses on original/postponed cost/profit and benefit proof |
| HW5 — Value of Flexibility | §3.7, §§9.1, 9.6–9.10 | Refers to HW4/HW6 for shared principles, focuses on pooled demand, equal/unequal underage, FCFS and contrasting priority |

The numerical homework examples in manual §§4.5, 4.6, 6.6, 8.4–8.5, 9.5 and 9.9 are shown in **Results** rather than duplicated in Theory. The formulas and algorithm implementations remain unchanged. The former generic "Assumptions / limitations / sources" UI panel is still absent. Necessary mathematical conditions are described where they are actually used in the proof or decision rules.

## Input layout contract

- HW1/HW3/HW2: first vertical column = `D`, `v`, `A`, `r`; second vertical column = all other model-specific fields in canonical order.
- HW4/HW6/HW5: all fields preserved, distributed over two columns as applicable.
- Numeric input formats, Excel keys, `solve()` payloads and Results are unchanged.

## Verify

```powershell
uv run --active python -m pytest -q
uv run --active python main.py
```

Open `http://localhost:8080`, inspect HW1 Theory sections 4.1–4.4 and HW3 Theory 4.6, and ensure the Input layout uses a vertical left column (not alternating rows). The test suite checks source-level/UI structure but cannot replace a real browser check for layout and LaTeX rendering.

## Additional shared Part III distribution reference

The Input tab now offers selected Manual Part III demand distributions. Instead of repeating derivations in all homework screens, `inventory_solver/distribution_theory.py` contains one shared set of sections for Normal, Uniform, Exponential, Geometric, Poisson and arbitrary finite Discrete demand, plus critical-fractile and aggregation formulas. It appears inside the Theory tab of HW4 and HW6. HW5 shows the Normal and Poisson parts relevant to independent pooling. HW1/HW3/HW2 remain on their Normal-specific mathematical paths. See `docs/DISTRIBUTIONS.md` for the input and calculation contracts.
