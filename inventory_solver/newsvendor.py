"""Multi-item constrained Newsvendor: continuous dual and integer MILP (HW4)."""
from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.stats import norm

from inventory_solver.common import ensure, latex_num as f, loss, normal_quantile, number
from inventory_solver.schema import Metric, ModelInputError, Solution, Step


@dataclass(frozen=True)
class Item:
    name: str
    p: float
    v: float
    g: float
    b: float
    mu: float
    sigma: float

    @property
    def cu(self) -> float:
        return self.p - self.v + self.b

    @property
    def co(self) -> float:
        return self.v - self.g

    @property
    def alpha(self) -> float:
        return self.cu / (self.cu + self.co)

    def expected_profit(self, q: float) -> float:
        u, o = loss(q, self.mu, self.sigma)
        return (self.p - self.v) * self.mu - self.cu * u - self.co * o

    def optimal_at_multiplier(self, multiplier: float) -> float:
        alpha = (self.cu - multiplier * self.v) / (self.cu + self.co)
        if alpha <= float(norm.cdf(-self.mu / self.sigma)):
            return 0.0
        # Initial critical ratio <1, decreasing with nonnegative multiplier.
        return max(0.0, self.mu + self.sigma * normal_quantile(alpha))

    def marginal_unit_profit(self, j: np.ndarray) -> np.ndarray:
        """Profit for units (j-1,j] as exact integral of the Normal marginal profit."""
        upper = (j - self.mu) / self.sigma
        lower = (j - 1.0 - self.mu) / self.sigma
        antideriv = lambda z: z * norm.cdf(z) + norm.pdf(z)
        return self.cu - (self.cu + self.co) * self.sigma * (antideriv(upper) - antideriv(lower))


def items_from(raw: Mapping[str, object], *, required: int = 1) -> list[Item]:
    values = raw.get("items")
    ensure(isinstance(values, list) and required <= len(values) <= 20,
           f"Provide between {required} and 20 products.")
    results: list[Item] = []
    for idx, element in enumerate(values, 1):
        ensure(isinstance(element, dict), f"Item {idx}: expected a row of values.")
        el = element
        name = str(el.get("name", f"Item {idx}")).strip()[:75] or f"Item {idx}"
        p = number(el, "p", positive=True)
        v = number(el, "v", positive=True)
        g = number(el, "g", nonnegative=True)
        b = number(el, "B", nonnegative=True)
        mu = number(el, "mu", nonnegative=True)
        sigma = number(el, "sigma", positive=True)
        item = Item(name, p, v, g, b, mu, sigma)
        ensure(item.cu > 0 and item.co > 0,
               f"{name}: requires p-v+B > 0 and v-g > 0 for the standard critical-ratio model.")
        results.append(item)
    return results


def _integer_milp(items: Sequence[Item], budget: float, *, max_vars: int = 12_000) -> tuple[list[int], str]:
    """Optimize integer units using a binary marginal-unit knapsack; concavity implies a prefix optimum.

    Falls back explicitly when a model is too large for the bounded public web service.
    """
    marginal_parts: list[np.ndarray] = []
    cost_parts: list[np.ndarray] = []
    counts: list[int] = []
    for item in items:
        max_affordable = math.floor((budget + 1e-8) / item.v)
        # No optimal solution needs quantities beyond the point with nonpositive marginal gain.
        max_profitable = max(0, math.ceil(item.mu + item.sigma * normal_quantile(item.alpha)) + 2)
        cap = min(max_affordable, max_profitable)
        counts.append(cap)
        if sum(counts) > max_vars:
            raise ModelInputError(f"Integer optimization too large: >{max_vars:,} candidate units; reduce budget/products.")
        idx = np.arange(1, cap + 1, dtype=float)
        marginal_parts.append(item.marginal_unit_profit(idx))
        cost_parts.append(np.full(cap, item.v, dtype=float))
    if not any(counts):
        return [0] * len(items), "Exact (no unit affordable)"
    marginal = np.concatenate(marginal_parts)
    cost = np.concatenate(cost_parts)
    answer = milp(c=-marginal, integrality=np.ones(len(marginal)),
                  bounds=Bounds(np.zeros(len(marginal)), np.ones(len(marginal))),
                  constraints=LinearConstraint(cost[np.newaxis, :], -np.inf, budget),
                  options={"time_limit": 25.0, "mip_rel_gap": 1e-9})
    if answer.x is None:
        raise ModelInputError(f"Integer optimization did not yield a solution: {answer.message}")
    quantities = []
    offset = 0
    for cap in counts:
        quantities.append(int(np.count_nonzero(answer.x[offset:offset + cap] >= 0.5)))
        offset += cap
    used = sum(item.v * q for item, q in zip(items, quantities))
    ensure(used <= budget + 1e-6, "Integer solver returned an over-budget result; check numerical scales.")
    quality = "Global integer optimum (MILP certified)" if answer.status == 0 else "Feasible integer incumbent (not certified)"
    return quantities, quality


def hw4(raw: Mapping[str, object]) -> Solution:
    budget = number(raw, "W", nonnegative=True)
    items = items_from(raw, required=2)
    unlimited = [x.optimal_at_multiplier(0.0) for x in items]
    spend_unlimited = sum(x.v * q for x, q in zip(items, unlimited))
    bisect_log: list[tuple[int, float, float]] = []
    bisect_bounds: list[tuple[float, float]] = []  # display the first two midpoints, not all substitutions
    if spend_unlimited <= budget:
        multiplier, qstar = 0.0, unlimited
        final_bracket: tuple[float, float] | None = None
    elif budget == 0:
        # An empty acquisition budget gives exact zero orders. Avoid a tiny
        # positive residue from bisection being displayed as a real purchase.
        multiplier = max(
            (x.cu - (x.cu + x.co) * float(norm.cdf(-x.mu / x.sigma))) / x.v
            for x in items
        )
        qstar = [0.0] * len(items)
        final_bracket = None
    else:
        def q_at(m: float) -> list[float]:
            return [x.optimal_at_multiplier(m) for x in items]

        def budget_residual(m: float) -> float:
            return sum(x.v * q for x, q in zip(items, q_at(m))) - budget

        lo, hi = 0.0, 1.0
        while budget_residual(hi) > 0:
            hi *= 2
            if hi > 1e12:
                raise ModelInputError("Unable to bracket the budget multiplier; check inputs.")
        for i in range(100):
            bisect_bounds.append((lo, hi))
            mid = (lo + hi) / 2
            residual = budget_residual(mid)
            bisect_log.append((i + 1, mid, residual))
            if residual > 0:
                lo = mid
            else:
                hi = mid
            if hi - lo <= 2e-13 * max(1.0, mid):
                break
        multiplier = (lo + hi) / 2
        qstar = q_at(multiplier)
        final_bracket = (lo, hi)
    integer_q, integer_quality = _integer_milp(items, budget)
    spent = sum(x.v * q for x, q in zip(items, integer_q))
    total_profit = sum(x.expected_profit(float(q)) for x, q in zip(items, integer_q))
    out = Solution("HW4", "Multi-item Newsvendor · Budget Constraint")
    out.data = {"M": multiplier, "continuous_q": qstar, "integer_q": integer_q,
                "spend": spent, "budget": budget, "profit": total_profit,
                "integer_quality": integer_quality, "continuous_spend": sum(x.v * q for x, q in zip(items, qstar)),
                "unconstrained_spend": spend_unlimited, "bisections": len(bisect_log),
                "bracket": final_bracket}
    out.metrics = [Metric("Budget", budget, "$"), Metric("Integer purchase", spent, "$"),
                   Metric("Expected profit", total_profit, "$"), Metric("Multiplier M", multiplier)]
    def budget_terms(quantities: Sequence[float]) -> str:
        return "+".join(rf"{f(item.v)}({f(q)})" for item, q in zip(items, quantities))

    def multiplier_response(j: int, item: Item, m: float, quantity: float) -> tuple[str, str]:
        """Render the manual's active-set rule without calling inverse CDF out of range."""
        alpha = (item.cu - m * item.v) / (item.cu + item.co)
        critical = (
            rf"\alpha_{{{j}}}(M)=\frac{{c_{{u,{j}}}-Mv_{j}}}{{c_{{u,{j}}}+c_{{o,{j}}}}}"
            rf"=\frac{{{f(item.cu)}-{f(m,9)}({f(item.v)})}}{{{f(item.cu+item.co)}}}={f(alpha,6)}"
        )
        if quantity <= 0.0:
            threshold = float(norm.cdf(-item.mu / item.sigma))
            decision = (
                rf"Q_{{{j}}}(M)=0\quad\mathrm{{if}}\quad\alpha_{{{j}}}(M)\le F_{{{j}}}(0)"
                rf"\quad\Rightarrow\quad {f(alpha,6)}\le {f(threshold,6)}\quad\Rightarrow\quad 0"
            )
        else:
            decision = (
                rf"Q_{{{j}}}(M)=\mu_{j}+\sigma_{j}\Phi^{{-1}}(\alpha_{{{j}}}(M))"
                rf"={f(item.mu)}+{f(item.sigma)}\Phi^{{-1}}({f(alpha,6)})={f(quantity)}"
            )
        return critical, decision

    spend_continuous = sum(x.v*q for x, q in zip(items, qstar))
    item_profits = [x.expected_profit(float(q)) for x, q in zip(items, integer_q)]
    out.steps = [
        Step("1 · Per-item marginal economics", tuple(
            eq for j, x in enumerate(items, 1) for eq in (
                rf"c_{{u,{j}}}=p_{j}-v_{j}+B_{j}={f(x.p)}-{f(x.v)}+{f(x.b)}={f(x.cu)}",
                rf"c_{{o,{j}}}=v_{j}-g_{j}={f(x.v)}-{f(x.g)}={f(x.co)}",
            )), open_by_default=True),
        Step("2 · Unconstrained order quantities and budget check", tuple(
            eq for j, (x, q) in enumerate(zip(items, unlimited), 1)
            for eq in multiplier_response(j, x, 0.0, q)
        ) + (
            rf"W_u=\sum_i v_iQ_{{u,i}}={budget_terms(unlimited)}={f(spend_unlimited)}",
            (rf"W_u>W\quad\Rightarrow\quad {f(spend_unlimited)}>{f(budget)}\quad\Rightarrow\quad M^*>0"
             if spend_unlimited > budget else
             rf"W_u\le W\quad\Rightarrow\quad {f(spend_unlimited)}\le {f(budget)}\quad\Rightarrow\quad M^*=0"),
        ), ("The budget is zero, so all order quantities are zero." if budget == 0 else
            "Unconstrained spending exceeds the budget, so adjust quantities with M > 0." if spend_unlimited > budget else
            "Unconstrained spending fits the budget, so M = 0."), True),
        Step("3 · Lagrangian decision formula", (
            r"\alpha_i(M)=\frac{p_i-(1+M)v_i+B_i}{p_i-g_i+B_i}",
            r"Q_i(M)=\max\{0,\mu_i+\sigma_i\Phi^{-1}(\alpha_i(M))\}\quad\mathrm{(interior\ or\ zero-stock\ branch)}",
            r"G(M)=\sum_i v_iQ_i(M)-W",
            (rf"W=0\quad\Rightarrow\quad Q_i^*=0\quad\Rightarrow\quad M={f(multiplier,9)}"
             if budget == 0 else
             rf"M^*=\operatorname{{root}}\!\left(G(M)=0\right)={f(multiplier,9)}")
            if spend_unlimited > budget else
            rf"M^*=0\quad\mathrm{{because}}\quad W_u={f(spend_unlimited)}\le W={f(budget)}",
        )),
    ]
    for i, (j, m, residual) in enumerate(bisect_log[:2], 1):
        lo_before, hi_before = bisect_bounds[i-1]
        mid_equation = (
            rf"M_{{mid,{i}}}=\frac{{M_L+M_U}}{{2}}"
            rf"=\frac{{{f(lo_before,9)}+{f(hi_before,9)}}}{{2}}={f(m,9)}"
        )
        quantities = [x.optimal_at_multiplier(m) for x in items]
        per_item = tuple(
            eq for idx, (item, quantity) in enumerate(zip(items, quantities), 1)
            for eq in multiplier_response(idx, item, m, quantity)
        )
        out.steps.append(Step(f"4.{i} · Bisection iteration {i}",
            (mid_equation, *per_item,
             rf"G(M)=\sum_i v_iQ_i(M)-W={budget_terms(quantities)}-{f(budget)}={f(residual)}"),
            (f"G(M) = {residual:,.6f} > 0: set the lower bound to M = {m:.9f}." if residual > 0 else
             f"G(M) = {residual:,.6f} ≤ 0: set the upper bound to M = {m:.9f}."), i == 1))

    out.steps.append(Step("5 · Continuous optimum and budget residual",
        tuple(eq for idx, (item, q) in enumerate(zip(items, qstar), 1)
              for eq in multiplier_response(idx, item, multiplier, q)) + (
            rf"W_{{continuous}}=\sum_i v_iQ_i^*={budget_terms(qstar)}={f(spend_continuous)}",
            rf"G(M^*)=W_{{continuous}}-W={f(spend_continuous)}-{f(budget)}={f(spend_continuous-budget)}",
        )))

    out.steps.append(Step("6 · Integer decision, budget and expected profit", (
        r"\mathbf q_{int}=\operatorname*{arg\,max}_{\mathbf q\in\mathbb{Z}_{\ge0}^{n},\ \sum_i v_iq_i\le W}"
        r"\sum_i E[\Pi_i(q_i)]",
        *tuple(rf"Q_{{{idx},int}}={int(q)}\quad\mathrm{{(integer\ solver\ result)}}"
               for idx, q in enumerate(integer_q, 1)),
        rf"W_{{used}}=\sum_i v_iQ_{{i,int}}={budget_terms(integer_q)}={f(spent)}\le {f(budget)}",
        *tuple(
            rf"E[\Pi_{{{idx}}}]=(p_{idx}-v_{idx})\mu_{idx}-c_{{u,{idx}}}U_{idx}(Q_{idx})-c_{{o,{idx}}}O_{idx}(Q_{idx})"
            rf"={f(item.p-item.v)}({f(item.mu)})-{f(item.cu)}({f(loss(float(integer_q[idx-1]),item.mu,item.sigma)[0])})"
            rf"-{f(item.co)}({f(loss(float(integer_q[idx-1]),item.mu,item.sigma)[1])})={f(item_profits[idx-1])}"
            for idx, item in enumerate(items, 1)
        ),
        rf"E[\Pi_{{total}}]=\sum_i E[\Pi_i(Q_{{i,int}})]"
        rf"={' + '.join(f(profit) for profit in item_profits)}={f(total_profit)}",
    ), f"Selected whole-unit quantities spend ${spent:,.3f} of ${budget:,.3f}. {integer_quality}."))
    out.comparisons = [{"Item": x.name, "Unconstrained": f(unlimited[i]),
                        "Continuous": f(qstar[i]), "Integer": integer_q[i],
                        "Spend $": f(x.v * integer_q[i]),
                        "Expected profit $": f(x.expected_profit(float(integer_q[i])))}
                       for i, x in enumerate(items)]
    out.columns = [{"name": a, "label": b, "field": a, "align": "right"} for a, b in
                   (("j", "j"), ("M", "M mid"), ("residual", "G(M) $"))]
    out.rows = [{"j": j, "M": f(m,9), "residual": f(g)} for j,m,g in bisect_log]
    out.notices = [
        "Source: lecture slides 21–26; Complete Manual §8.1–8.7; Silver, Pyke & Thomas §9.3.",
        "Demand is approximated as Normal. Each item's expected profit is separable; the single shared constraint is acquisition budget.",
        f"Discrete status: {integer_quality}. MILP uses exact Normal marginal expected-profit integrals to optimize integer units.",
        "The dual multiplier is a local marginal value of budget for the continuous relaxation, not an exact integer-dollar guarantee.",
        "Internal precision is retained until display; budget feasibility is checked on whole units.",
    ]
    return out
