"""Continuous-review B1 models: HW1 simultaneous and HW3 fixed EOQ."""
from __future__ import annotations

import math
from collections.abc import Mapping

import numpy as np
from scipy.optimize import minimize_scalar
from scipy.stats import norm

from inventory_solver.common import annual_cost_b1, ensure, latex_num as f, number
from inventory_solver.schema import Metric, Solution, Step


def _inputs(raw: Mapping[str, object]) -> dict[str, float]:
    d = {key: number(raw, key, positive=key not in ("muL",), nonnegative=key == "muL")
         for key in ("D", "v", "A", "r", "B1", "muL", "sigmaL")}
    return d


def _safety_for_q(q: float, c: float) -> float:
    return math.sqrt(2.0 * math.log(c / q)) if q < c else 0.0


def _base(d: dict[str, float]) -> tuple[float, float, float]:
    h = d["v"] * d["r"]
    eoq = math.sqrt(2 * d["D"] * d["A"] / h)
    c = d["D"] * d["B1"] / (math.sqrt(2 * math.pi) * h * d["sigmaL"])
    return h, eoq, c


def hw1(raw: Mapping[str, object]) -> Solution:
    d = _inputs(raw)
    h, eoq, c = _base(d)
    q = eoq
    records: list[dict[str, float]] = []
    converged = False
    for j in range(500):
        k = _safety_for_q(q, c)
        s = d["muL"] + k * d["sigmaL"]
        next_q = math.sqrt(2 * d["D"] * (d["A"] + d["B1"] * norm.sf(k)) / h)
        records.append({"iteration": j, "Q": q, "k": k, "s": s, "Q_next": next_q, "delta": abs(next_q - q)})
        if abs(next_q - q) < 1e-11 * max(1.0, q):
            q = next_q
            converged = True
            break
        q = next_q
    k_fixed = _safety_for_q(q, c)
    cost_fixed = annual_cost_b1(q, k_fixed, d["D"], d["A"], d["B1"], h, d["sigmaL"])

    # Independent 1-D reduced-objective check: q(k) minimizes cost at fixed k.
    def q_at(k0: float) -> float:
        return math.sqrt(2 * d["D"] * (d["A"] + d["B1"] * norm.sf(k0)) / h)

    def reduced(k0: float) -> float:
        return h * (q_at(k0) + k0 * d["sigmaL"])

    k_bound = _safety_for_q(eoq, c)
    k_upper = max(9.0, k_bound + 1.0)
    grid = np.linspace(0.0, k_upper, max(181, math.ceil(k_upper * 20) + 1))
    candidates: list[tuple[float, float]] = [(reduced(0.0), 0.0)]
    vals = [reduced(float(x)) for x in grid]
    for idx in range(1, len(grid) - 1):
        if vals[idx] <= vals[idx - 1] and vals[idx] <= vals[idx + 1]:
            res = minimize_scalar(reduced, bounds=(float(grid[idx - 1]), float(grid[idx + 1])),
                                  method="bounded", options={"xatol": 1e-13})
            candidates.append((float(res.fun), float(res.x)))
    # A stationary fixed point can be a local optimum; never silently trust it.
    best_cost, best_k = min(candidates)
    if converged and cost_fixed <= best_cost + 1e-6:
        result_q, result_k = q, k_fixed
        method = "Fixed-point iteration; reduced-cost cross-check passed"
    else:
        result_q, result_k = q_at(best_k), best_k
        method = "Global candidate from reduced-cost scan; iteration not certified"
    result_s = d["muL"] + result_k * d["sigmaL"]
    cost = annual_cost_b1(result_q, result_k, d["D"], d["A"], d["B1"], h, d["sigmaL"])
    boundary_cost = reduced(0.0)
    out = Solution("HW1", "Simultaneous (s, Q) · B1 cost")
    out.data = {"Q": result_q, "s": result_s, "k": result_k, "cost": cost,
                "EOQ": eoq, "h": h, "boundary_cost": boundary_cost,
                "converged": converged, "iterations": len(records), "method": method}
    out.metrics = [Metric("Order quantity Q*", result_q, "units"),
                   Metric("Reorder point s*", result_s, "units"),
                   Metric("Safety factor k*", result_k),
                   Metric("Annual relevant cost", cost, "$/year")]
    out.steps = [
        Step("1 · Annual holding cost", (rf"h=vr={f(d['v'])}\times {f(d['r'])}={f(h)}",), open_by_default=True),
        Step("2 · Initial EOQ", (rf"Q_0=\sqrt{{\frac{{2AD}}{{h}}}}=\sqrt{{\frac{{2({f(d['A'])})({f(d['D'])})}}{{{f(h)}}}}}={f(eoq)}",), open_by_default=True),
        Step("3 · General update formulas (shown once)", (
            rf"c=\frac{{DB_1}}{{\sqrt{{2\pi}}h\sigma_L}}"
            rf"=\frac{{{f(d['D'])}({f(d['B1'])})}}{{\sqrt{{2\pi}}({f(h)})({f(d['sigmaL'])})}}={f(c)}",
            rf"k_j=\sqrt{{2\ln\left(\frac{{c}}{{Q_j}}\right)}}"
            rf"=\sqrt{{2\ln\left(\frac{{{f(c)}}}{{Q_j}}\right)}}\quad (Q_j<c)",
            r"k_j=0\quad (Q_j\ge c)",
            rf"Q_{{j+1}}=\sqrt{{\frac{{2D[A+B_1(1-\Phi(k_j))]}}{{h}}}}"
            rf"=\sqrt{{\frac{{2({f(d['D'])})[{f(d['A'])}+{f(d['B1'])}(1-\Phi(k_j))]}}{{{f(h)}}}}}",
            rf"s_j=\mu_L+k_j\sigma_L={f(d['muL'])}+k_j({f(d['sigmaL'])})",
        )),
    ]
    for rec in records[:2]:
        i = int(rec["iteration"])
        out.steps.append(Step(f"4.{i+1} · Iteration {i+1}", (
            (rf"k_{{{i}}}=\sqrt{{2\ln\!\left(\frac{{{f(c)}}}{{{f(rec['Q'])}}}\right)}}={f(rec['k'])}"
             if rec['Q'] < c else
             rf"k_{{{i}}}=0\quad (Q_{{{i}}}={f(rec['Q'])}\ge c={f(c)})"),
            rf"Q_{{{i+1}}}=\sqrt{{\frac{{2({f(d['D'])})[{f(d['A'])}+{f(d['B1'])}(1-\Phi({f(rec['k'])}))]}}{{{f(h)}}}}}={f(rec['Q_next'])}",
            rf"s_{{{i}}}=\mu_L+k_{{{i}}}\sigma_L={f(d['muL'])}+{f(rec['k'])}({f(d['sigmaL'])})={f(rec['s'])}",
        ), open_by_default=i == 0))
    out.steps.append(Step("5 · Final order quantity, reorder point & cost", (
        rf"Q^*=\sqrt{{\frac{{2D[A+B_1(1-\Phi(k^*))]}}{{h}}}}"
        rf"=\sqrt{{\frac{{2({f(d['D'])})[{f(d['A'])}+{f(d['B1'])}(1-\Phi({f(result_k)}))]}}{{{f(h)}}}}}={f(result_q)}",
        rf"s^*=\mu_L+k^*\sigma_L={f(d['muL'])}+{f(result_k)}({f(d['sigmaL'])})={f(result_s)}",
        rf"TC^*=\frac{{D[A+B_1(1-\Phi(k^*))]}}{{Q^*}}+h\left(\frac{{Q^*}}{{2}}+k^*\sigma_L\right)"
        rf"=\frac{{{f(d['D'])}[{f(d['A'])}+{f(d['B1'])}(1-\Phi({f(result_k)}))]}}{{{f(result_q)}}}"
        rf"+{f(h)}\left(\frac{{{f(result_q)}}}{{2}}+{f(result_k)}({f(d['sigmaL'])})\right)={f(cost)}",
    )))
    out.columns = [{"name": x, "label": label, "field": x, "align": "right"} for x, label in
                   [("iteration", "j"), ("Q", "Qⱼ"), ("k", "kⱼ"), ("s", "sⱼ"), ("delta", "|Qⱼ₊₁ − Qⱼ|")]]
    out.rows = [{"iteration": int(r["iteration"]), **{x: f(r[x]) for x in ("Q", "k", "s", "delta")}}
                for r in records]
    out.notices = [
        "Source: lecture slides 3–6; Complete Manual §4.2–4.5; Silver, Pyke & Thomas §7.3.",
        "B1 is cost per stockout occasion, not per short unit. Lead-time demand is approximated as Normal.",
        "The holding-cost expression is the textbook approximation. Iteration convergence alone does not prove global optimality.",
        f"Method check: {method}. Boundary k=0 annual cost = ${boundary_cost:,.3f}.",
        "Continuous quantities are shown to 3 decimals. Operational integer decisions require separate policy evaluation.",
    ]
    return out


def hw3(raw: Mapping[str, object]) -> Solution:
    d = _inputs(raw)
    p = number(raw, "increase_pct", nonnegative=True)
    ensure(p <= 1000, "Increase percent must be <= 1000%.")
    h, q, c = _base(d)
    k = _safety_for_q(q, c)
    s = d["muL"] + k * d["sigmaL"]
    tc = annual_cost_b1(q, k, d["D"], d["A"], d["B1"], h, d["sigmaL"])
    q_new = q * (1 + p / 100)
    k_new = _safety_for_q(q_new, c)
    s_new = d["muL"] + k_new * d["sigmaL"]
    tc_new = annual_cost_b1(q_new, k_new, d["D"], d["A"], d["B1"], h, d["sigmaL"])
    saved = tc - tc_new
    out = Solution("HW3", "EOQ and expediting cost")
    out.data = {"EOQ": q, "Q_alt": q_new, "k": k, "s": s, "s_alt": s_new,
                "cost": tc, "cost_alt": tc_new, "savings": saved}
    out.metrics = [Metric("Fixed EOQ", q, "units"), Metric("Reorder point s", s, "units"),
                   Metric("Current annual cost", tc, "$/year"), Metric("Cost change benefit", saved, "$/year")]
    ordering = d["A"] * d["D"] / q
    holding = h * (q / 2 + k * d["sigmaL"])
    expediting = d["D"] * d["B1"] / q * norm.sf(k)
    ordering_new = d["A"] * d["D"] / q_new
    holding_new = h * (q_new / 2 + k_new * d["sigmaL"])
    expediting_new = d["D"] * d["B1"] / q_new * norm.sf(k_new)
    out.steps = [
        Step("1 · Holding cost and EOQ", (
            rf"h=vr={f(d['v'])}({f(d['r'])})={f(h)}",
            rf"Q_{{EOQ}}=\sqrt{{\frac{{2AD}}{{h}}}}=\sqrt{{\frac{{2({f(d['A'])})({f(d['D'])})}}{{{f(h)}}}}}={f(q)}"), open_by_default=True),
        Step("2 · Safety factor and reorder point", (
            (rf"k=\sqrt{{2\ln\!\left(\frac{{DB_1}}{{\sqrt{{2\pi}}h\sigma_L Q}}\right)}}=\sqrt{{2\ln\!\left(\frac{{{f(c)}}}{{{f(q)}}}\right)}}={f(k)}"
             if q < c else rf"k=0\quad (Q={f(q)}\ge c={f(c)})"),
            rf"s=\mu_L+k\sigma_L={f(d['muL'])}+{f(k)}({f(d['sigmaL'])})={f(s)}"), open_by_default=True),
        Step("3 · Annual ordering, carrying and expediting costs", (
            rf"C_{{order}}=\frac{{AD}}{{Q}}=\frac{{{f(d['A'])}({f(d['D'])})}}{{{f(q)}}}={f(ordering)}",
            rf"C_{{hold}}=h\left(\frac{{Q}}{{2}}+k\sigma_L\right)"
            rf"={f(h)}\left(\frac{{{f(q)}}}{{2}}+{f(k)}({f(d['sigmaL'])})\right)={f(holding)}",
            rf"C_{{expedite}}=\frac{{DB_1}}{{Q}}[1-\Phi(k)]"
            rf"=\frac{{{f(d['D'])}({f(d['B1'])})}}{{{f(q)}}}[1-\Phi({f(k)})]={f(expediting)}",
            rf"TC=C_{{order}}+C_{{hold}}+C_{{expedite}}"
            rf"={f(ordering)}+{f(holding)}+{f(expediting)}={f(tc)}",
        ), "Expediting cost counts stockout events, regardless of shortage size."),
        Step(f"4 · Alternative: Q increased by {p:.3f}%", (
            rf"Q_{{new}}=Q\left(1+\frac{{{f(p)}}}{{100}}\right)={f(q)}(1+{f(p/100)})={f(q_new)}",
            (rf"k_{{new}}=\sqrt{{2\ln\!\left(\frac{{{f(c)}}}{{{f(q_new)}}}\right)}}={f(k_new)}"
             if q_new < c else rf"k_{{new}}=0\quad (Q_{{new}}={f(q_new)}\ge c={f(c)})"),
            rf"s_{{new}}=\mu_L+k_{{new}}\sigma_L={f(d['muL'])}+{f(k_new)}({f(d['sigmaL'])})={f(s_new)}",
            rf"C_{{order,new}}=\frac{{AD}}{{Q_{{new}}}}=\frac{{{f(d['A'])}({f(d['D'])})}}{{{f(q_new)}}}={f(ordering_new)}",
            rf"C_{{hold,new}}=h\left(\frac{{Q_{{new}}}}{{2}}+k_{{new}}\sigma_L\right)"
            rf"={f(h)}\left(\frac{{{f(q_new)}}}{{2}}+{f(k_new)}({f(d['sigmaL'])})\right)={f(holding_new)}",
            rf"C_{{expedite,new}}=\frac{{DB_1}}{{Q_{{new}}}}[1-\Phi(k_{{new}})]"
            rf"=\frac{{{f(d['D'])}({f(d['B1'])})}}{{{f(q_new)}}}[1-\Phi({f(k_new)})]={f(expediting_new)}",
            rf"TC_{{new}}=C_{{order,new}}+C_{{hold,new}}+C_{{expedite,new}}"
            rf"={f(ordering_new)}+{f(holding_new)}+{f(expediting_new)}={f(tc_new)}",
            rf"\mathrm{{Savings}}=TC-TC_{{new}}={f(tc)}-{f(tc_new)}={f(saved)}",
        ), (f"Increasing Q by {p:g}% reduces annual cost by ${saved:,.3f}." if saved > 1e-7 else
            f"Increasing Q by {p:g}% increases annual cost by ${-saved:,.3f}." if saved < -1e-7 else
            "Both quantities give the same annual cost.")),
    ]
    out.comparisons = [
        {"Policy": "Fixed EOQ", "Q": f(q), "k": f(k), "s": f(s), "Cost $/year": f(tc)},
        {"Policy": f"EOQ + {p:g}%", "Q": f(q_new), "k": f(k_new), "s": f(s_new), "Cost $/year": f(tc_new)},
    ]
    out.notices = [
        "Source: lecture slides 3–6; Complete Manual §4.6; Assignment 3 Problem 3; Silver §7.3.",
        "The expediting cost is B1 ($ per stockout event); a fixed EOQ minimizes only ordering + cycle holding costs.",
        "Both scenarios select k based on their own Q; negative savings mean the alternative is worse.",
    ]
    return out
