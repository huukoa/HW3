# Sensitivity dashboard — live 5% slider

Navigation: **Input → Results → Sensitivity → Theory**. This feature varies one
input at a time without mutating Input or overwriting the baseline Results tab.

## Use it

1. Load an example or enter the desired inputs in **Input**.
2. Open **Sensitivity**, select **Change an input**, choose the parameter, and
   optionally choose **Percent** / **Absolute**. On HW1/HW3 you can instead
   select **Change Q / EOQ (%)**; HW1 offers the baseline EOQ or optimized Q*.
3. Choose the slider range: **±10%, ±25% (default), or ±50%**. Every preset
   uses **5% increments**, including the center (0%). The app precomputes 5,
   11 or 21 scenarios, respectively, when you click **Build dashboard**.
4. Drag the slider. **Every output metric card** updates together: new value,
   original baseline, difference and percentage difference (when the baseline
   is nonzero). The main **four charts** are shown at the same time and the
   active scenario is marked. The full scenario table is optional/collapsed.
5. To vary a zero baseline (or use units rather than percent), choose
   **Absolute** variation, enter a positive range and build the dashboard;
   it computes 11 equally spaced values from -range to +range.

No solver is called by the slider callback; the callback only looks up the
selected precomputed scenario and updates labels/charts. The expensive model
runs occur once per *Build dashboard*, on a NiceGUI background worker. Changing
model, inputs or sensitivity configuration invalidates the old dashboard.

## Outputs by model

| Model | Outputs |
|---|---|
| HW1 | Q, s, SS, safety factor, annual TC, ordering/holding/shortage costs |
| HW3 | EOQ, s, SS, k, annual TC and its cost components, alternative scenario |
| HW2 | Qp, s, S, rounded order levels, protection buffer and branch ratio |
| HW4 | Every integer SKU Q, total Q, spend, remaining budget, expected profit, multiplier |
| HW6 | Original and postponed Q, original/postponed expected profits and gain |
| HW5 | Per-design Q, pooled Q, original/postponed profits and estimated gain |

HW3 fixed-Q +5% should show `Q=126`, `TC≈1022.073` (from `Q=120`,
`TC≈1026.799`), with changed safety factor/reorder point and an annual saving.

## Engineering safeguards

- Original Normal calculations, new distribution-specific solvers and the
  associated Homework model decisions are **not changed**. Input sweeps still
  call `solve`; fixed-Q sweeps reuse the existing B1 primitives.
- Each output chart uses its own Y axis and units (don't visually compare the
  heights of charts with different measurement scales).
- A failed scenario has empty current metrics and a visible error; no fallback
  to baseline or interpolation. Percentage change is omitted when the baseline
  metric is zero rather than computing an infinite percentage.
- User sessions have independent NiceGUI page state. A background result is
  discarded if model/input/configuration changes while computing.
- Up to 21 scenarios are computed per percent sweep; HW4 integer MILP sweeps
  may take longer. Slider interaction after the sweep does not invoke MILP.
- No added packages or GPU. The app remains compatible with Python 3.12 + uv
  + NiceGUI and the existing GitHub/Render deployment configuration.

## Verification

```powershell
uv run --active python -m pytest -q
uv run --active python main.py
```

Browser smoke checks: HW3 → Sensitivity → Change Q/EOQ → Build dashboard →
move to +5%, -5% and 0%; confirm Q/s/SS/TC/cost cards and four charts update
without running the solver again. Also check an HW4 budget change, a HW6
input with a different distribution and an invalid scenario. Pure code tests
check all six Homework baselines, slider points, deltas, chart marker data,
zero baselines and invalid values; the code authoring environment does not
have NiceGUI installed, so browser interaction remains to be verified on the
user's local installation.
