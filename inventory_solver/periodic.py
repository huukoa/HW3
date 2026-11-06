"""Ehrhardt–Mosier revised-power periodic (R,s,S) approximation (HW2)."""
from __future__ import annotations

import math
from collections.abc import Mapping

from inventory_solver.common import ensure, latex_num as f, number, normal_quantile
from inventory_solver.schema import Metric, Solution, Step


def hw2(raw: Mapping[str, object]) -> Solution:
    d = {key: number(raw, key, positive=True) for key in
         ("D", "v", "A", "r", "B3", "R", "L", "sigmaP", "weeks")}
    ensure(d["weeks"] >= d["R"], "Review period exceeds weeks per year; check units.")
    r_years = d["R"] / d["weeks"]
    l_years = d["L"] / d["weeks"]
    mu_r = d["D"] * r_years
    mu_p = d["D"] * (r_years + l_years)
    r_period = d["r"] * r_years
    qp = (1.30 * mu_r**0.494 * (d["A"] / (d["v"] * r_period))**0.506
          * (1 + d["sigmaP"]**2 / mu_r**2)**0.116)
    zp = math.sqrt(qp * r_period / (d["sigmaP"] * d["B3"]))
    sp = 0.973 * mu_p + d["sigmaP"] * (0.183 / zp + 1.063 - 2.192 * zp)
    ratio = qp / mu_r
    branch = "A" if ratio > 1.5 else "B"
    s0 = None
    if branch == "A":
        s, cap = sp, sp + qp
    else:
        alpha = d["B3"] / (d["B3"] + r_period)
        s0 = mu_p + d["sigmaP"] * normal_quantile(alpha)
        s, cap = min(sp, s0), min(sp + qp, s0)
    # The textbook example and manual use nearest whole-unit recommendations.
    s_unit = round(s)
    cap_unit = round(cap)
    out = Solution("HW2", "Periodic Review · Revised Power Approximation")
    out.data = {"Qp": qp, "zp": zp, "sp": sp, "ratio": ratio,
                "s": s, "S": cap, "s_integer": s_unit, "S_integer": cap_unit,
                "branch": branch, "S0": s0, "muR": mu_r, "muP": mu_p, "rR": r_period}
    out.metrics = [Metric("Review interval R", d["R"], "weeks"),
                   Metric("Reorder trigger s", s_unit, "units"),
                   Metric("Order-up-to S", cap_unit, "units"), Metric("Branch", branch)]
    out.steps = [
        Step("1 · Convert units to one review period", (
            rf"R_{{yr}}=\frac{{R}}{{w}}=\frac{{{f(d['R'])}}}{{{f(d['weeks'])}}}={f(r_years,6)}",
            rf"L_{{yr}}=\frac{{L}}{{w}}=\frac{{{f(d['L'])}}}{{{f(d['weeks'])}}}={f(l_years,6)}",
            rf"\mu_R=DR_{{yr}}={f(d['D'])}\left(\frac{{{f(d['R'])}}}{{{f(d['weeks'])}}}\right)={f(mu_r)}",
            rf"\mu_P=D(R_{{yr}}+L_{{yr}})={f(d['D'])}\!\left(\frac{{{f(d['R'])}+{f(d['L'])}}}{{{f(d['weeks'])}}}\right)={f(mu_p)}",
            rf"r_R=rR_{{yr}}={f(d['r'])}\!\left(\frac{{{f(d['R'])}}}{{{f(d['weeks'])}}}\right)={f(r_period,6)}",
        ), "Convert the annual demand and holding rate to the review-period units.", True),
        Step("2 · Revised-power intermediate values", (
            rf"Q_p=1.30\mu_R^{{0.494}}\!\left(\frac{{A}}{{vr_R}}\right)^{{0.506}}\!\left(1+\frac{{\sigma_P^2}}{{\mu_R^2}}\right)^{{0.116}}"
            rf"=1.30({f(mu_r)})^{{0.494}}\!\left(\frac{{{f(d['A'])}}}{{{f(d['v'])}({f(r_period,6)})}}\right)^{{0.506}}"
            rf"\!\left(1+\frac{{{f(d['sigmaP'])}^2}}{{{f(mu_r)}^2}}\right)^{{0.116}}={f(qp)}",
            rf"z_p=\sqrt{{\frac{{Q_pr_R}}{{\sigma_P B_3}}}}=\sqrt{{\frac{{{f(qp)}({f(r_period,6)})}}{{{f(d['sigmaP'])}({f(d['B3'])})}}}}={f(zp)}",
            rf"s_p=0.973\mu_P+\sigma_P\left(\frac{{0.183}}{{z_p}}+1.063-2.192z_p\right)"
            rf"=0.973({f(mu_p)})+{f(d['sigmaP'])}\left(\frac{{0.183}}{{{f(zp)}}}+1.063-2.192({f(zp)})\right)={f(sp)}",
        ), open_by_default=True),
        Step("3 · Choose the correct branch", (
            rf"H=\frac{{Q_p}}{{\mu_R}}=\frac{{{f(qp)}}}{{{f(mu_r)}}}={f(ratio)}",
            (rf"H>1.5\quad\Rightarrow\quad {f(ratio)}>1.5\quad\Rightarrow\quad\mathrm{{Branch\ A}}"
             if branch == "A" else
             rf"H\le 1.5\quad\Rightarrow\quad {f(ratio)}\le 1.5\quad\Rightarrow\quad\mathrm{{Branch\ B}}"),
        ), (f"H = {ratio:,.3f} > 1.5, so select Branch A." if branch == "A" else
            f"H = {ratio:,.3f} ≤ 1.5, so select Branch B."), True),
    ]
    if branch == "A":
        out.steps.append(Step("4 · Branch A order levels", (
            rf"s=s_p={f(sp)}={f(s)}",
            rf"S=s_p+Q_p={f(sp)}+{f(qp)}={f(cap)}",
        ), "At a review, order S − IP units when the inventory position is at or below s."))
    else:
        assert s0 is not None
        out.steps.append(Step("4 · Branch B limiting (R,S) policy", (
            rf"S_0=\mu_P+\sigma_P\Phi^{{-1}}\!\left(\frac{{B_3}}{{B_3+r_R}}\right)"
            rf"={f(mu_p)}+{f(d['sigmaP'])}\Phi^{{-1}}\!\left(\frac{{{f(d['B3'])}}}{{{f(d['B3'])}+{f(r_period,6)}}}\right)={f(s0)}",
            rf"s=\min(s_p,S_0)=\min({f(sp)},{f(s0)})={f(s)}",
            rf"S=\min(s_p+Q_p,S_0)=\min({f(sp+qp)},{f(s0)})={f(cap)}",
        ), "The limiting level S₀ caps the computed order-up-to level S."))
    out.steps.append(Step("5 · Whole-unit policy", (
        rf"s_{{int}}=\operatorname{{round}}(s)=\operatorname{{round}}({f(s)})={s_unit}",
        rf"S_{{int}}=\operatorname{{round}}(S)=\operatorname{{round}}({f(cap)})={cap_unit}",
        rf"(R,s_{{int}},S_{{int}})=({f(d['R'])}\ \mathrm{{weeks}},\ {s_unit},\ {cap_unit})",
    )))
    out.notices = [
        "Sources: lecture slides 8–13; Complete Manual §6.1–6.8; Silver, Pyke & Thomas §7.5.1.",
        "Revised Power Approximation is empirical. No bisection/fixed-point iteration is required.",
        "Order only at review times if IP ≤ s; order quantity is S − current IP.",
    ]
    if s_unit < 0 or cap_unit <= s_unit:
        out.notices.append("Caution: rounded policy has a nonpositive or reversed level; review parameter validity before operating.")
    return out
