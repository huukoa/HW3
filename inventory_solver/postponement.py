"""HW6 delayed financial commitment and HW5 multi-design FCFS pooling."""
from __future__ import annotations

import math
from collections.abc import Mapping

from inventory_solver.common import (ensure, integer_normal_quantity,
                                     latex_num as f, loss, number,
                                     optimal_normal_quantity)
from inventory_solver.newsvendor import items_from
from inventory_solver.schema import Metric, Solution, Step


def _profit(mu: float, q: float, margin: float, cu: float, co: float, sigma: float) -> float:
    short, over = loss(q, mu, sigma)
    return margin * mu - cu * short - co * over


def _normal_loss_chains(q: int, mu: float, sigma: float, *, pooled: bool = False) -> tuple[str, str, str]:
    """Manual Part 3: substitute the selected integer quantity into Normal loss."""
    z = (q - mu) / sigma
    u, o = loss(float(q), mu, sigma)
    qname = r"Q_0" if pooled else "Q"
    mu_name = r"\mu_\Sigma" if pooled else r"\mu"
    sigma_name = r"\sigma_\Sigma" if pooled else r"\sigma"
    zname = r"z_\Sigma" if pooled else "z"
    uname = r"U_\Sigma(Q_0)" if pooled else "U(Q)"
    oname = r"O_\Sigma(Q_0)" if pooled else "O(Q)"
    return (
        rf"{zname}=\frac{{{qname}-{mu_name}}}{{{sigma_name}}}"
        rf"=\frac{{{q}-{f(mu)}}}{{{f(sigma)}}}={f(z)}",
        rf"{uname}={sigma_name}[\phi({zname})-{zname}(1-\Phi({zname}))]"
        rf"={f(sigma)}[\phi({f(z)})-{f(z)}(1-\Phi({f(z)}))]={f(u)}",
        rf"{oname}={uname}+{qname}-{mu_name}={f(u)}+{q}-{f(mu)}={f(o)}",
    )


def _candidate_profit_chains(
    label: str, continuous_q: float, mu: float, sigma: float,
    margin: float, cu: float, co: float,
) -> tuple[str, str, str]:
    """Show the same adjacent integer comparison as integer_normal_quantity()."""
    low = max(0, math.floor(continuous_q))
    high = low + 1
    result: list[str] = []
    for candidate in (low, high):
        u, o = loss(float(candidate), mu, sigma)
        profit = _profit(mu, float(candidate), margin, cu, co, sigma)
        result.append(
            rf"E[\Pi_{{\mathrm{{{label}}}}}({candidate})]"
            rf"=m\mu-c_uU({candidate})-c_oO({candidate})"
            rf"={f(margin)}({f(mu)})-{f(cu)}({f(u)})-{f(co)}({f(o)})={f(profit)}"
        )
    best = integer_normal_quantity(continuous_q, mu, sigma, cu, co)
    result.append(
        rf"Q_{{\mathrm{{{label}}},int}}"
        rf"=\operatorname*{{arg\,max}}_{{q\in\{{{low},{high}\}}}}E[\Pi_{{\mathrm{{{label}}}}}(q)]={best}"
    )
    return tuple(result)  # type: ignore[return-value]


def hw6(raw: Mapping[str, object]) -> Solution:
    d = {k: number(raw, k, positive=k in ("sigma", "p", "v", "v0"),
                nonnegative=k not in ("sigma", "p", "v", "v0"))
         for k in ("mu", "sigma", "p", "v", "g", "B", "v0", "t", "g0")}
    cu_original = d["p"] - d["v"] + d["B"]
    co_original = d["v"] - d["g"]
    cu_post = d["p"] - d["v0"] - d["t"] + d["B"]
    co_post = d["v0"] - d["g0"]
    ensure(min(cu_original, co_original, cu_post, co_post) > 0,
           "Both models require positive underage and overage costs.")
    original_q = optimal_normal_quantity(d["mu"], d["sigma"], cu_original, co_original)
    post_q = optimal_normal_quantity(d["mu"], d["sigma"], cu_post, co_post)
    original_i = integer_normal_quantity(original_q, d["mu"], d["sigma"], cu_original, co_original)
    post_i = integer_normal_quantity(post_q, d["mu"], d["sigma"], cu_post, co_post)
    orig_profit = _profit(d["mu"], float(original_i), d["p"] - d["v"],
                          cu_original, co_original, d["sigma"])
    post_profit = _profit(d["mu"], float(post_i), d["p"] - d["v0"] - d["t"],
                          cu_post, co_post, d["sigma"])
    orig_cont_profit = _profit(d["mu"], original_q, d["p"] - d["v"],
                               cu_original, co_original, d["sigma"])
    post_cont_profit = _profit(d["mu"], post_q, d["p"] - d["v0"] - d["t"],
                               cu_post, co_post, d["sigma"])
    u_orig, o_orig = loss(float(original_i), d['mu'], d['sigma'])
    u_post, o_post = loss(float(post_i), d['mu'], d['sigma'])
    out = Solution("HW6", "Postponement · Delayed Financial Commitment")
    out.data = {"Q_original": original_q, "Q_post": post_q,
                "Q_original_int": original_i, "Q_post_int": post_i,
                "profit_original_int": orig_profit, "profit_post_int": post_profit,
                "profit_original_cont": orig_cont_profit, "profit_post_cont": post_cont_profit,
                "gain_int": post_profit-orig_profit, "gain_cont": post_cont_profit-orig_cont_profit}
    out.metrics = [Metric("Original order", original_i, "finished sets"),
                   Metric("Postponed order", post_i, "unfinished sets"),
                   Metric("Original expected profit", orig_profit, "$"),
                   Metric("Postponed expected profit", post_profit, "$"),
                   Metric("Profit improvement", post_profit - orig_profit, "$")]
    out.steps = [
        Step("1 · Original unit economics", (
            rf"c_u=p-v+B={f(d['p'])}-{f(d['v'])}+{f(d['B'])}={f(cu_original)}",
            rf"c_o=v-g={f(d['v'])}-{f(d['g'])}={f(co_original)}",
            rf"\alpha_{{orig}}=\frac{{c_u}}{{c_u+c_o}}=\frac{{{f(cu_original)}}}{{{f(cu_original+co_original)}}}={f(cu_original/(cu_original+co_original),6)}",
        ), open_by_default=True),
        Step("2 · Original quantity, integer comparison and profit", (
            rf"Q^*_{{orig}}=\mu+\sigma\Phi^{{-1}}(\alpha_{{orig}})={f(d['mu'])}+{f(d['sigma'])}\Phi^{{-1}}({f(cu_original/(cu_original+co_original),6)})={f(original_q)}",
            *_candidate_profit_chains("orig", original_q, d["mu"], d["sigma"],
                                     d["p"]-d["v"], cu_original, co_original),
            *_normal_loss_chains(original_i, d["mu"], d["sigma"]),
            rf"E[\Pi_{{orig}}]=(p-v)\mu-c_uU(Q)-c_oO(Q)"
            rf"={f(d['p']-d['v'])}({f(d['mu'])})-{f(cu_original)}({f(u_orig)})-{f(co_original)}({f(o_orig)})={f(orig_profit)}",
        ), "Compare the expected profits of the two neighboring whole-unit quantities."),
        Step("3 · Postponed cost and critical ratio", (
            rf"c_{{u,post}}=p-v_0-t+B={f(d['p'])}-{f(d['v0'])}-{f(d['t'])}+{f(d['B'])}={f(cu_post)}",
            rf"c_{{o,post}}=v_0-g_0={f(d['v0'])}-{f(d['g0'])}={f(co_post)}",
            rf"\alpha_{{post}}=\frac{{c_{{u,post}}}}{{c_{{u,post}}+c_{{o,post}}}}=\frac{{{f(cu_post)}}}{{{f(cu_post+co_post)}}}={f(cu_post/(cu_post+co_post),6)}",
        ), "Finishing cost applies only to sold units; unsold base units retain their salvage value."),
        Step("4 · Postponed quantity, integer comparison and profit", (
            rf"Q^*_{{post}}=\mu+\sigma\Phi^{{-1}}(\alpha_{{post}})={f(d['mu'])}+{f(d['sigma'])}\Phi^{{-1}}({f(cu_post/(cu_post+co_post),6)})={f(post_q)}",
            *_candidate_profit_chains("post", post_q, d["mu"], d["sigma"],
                                     d["p"]-d["v0"]-d["t"], cu_post, co_post),
            *_normal_loss_chains(post_i, d["mu"], d["sigma"]),
            rf"E[\Pi_{{post}}]=(p-v_0-t)\mu-c_{{u,post}}U(Q_0)-c_{{o,post}}O(Q_0)"
            rf"={f(d['p']-d['v0']-d['t'])}({f(d['mu'])})-{f(cu_post)}({f(u_post)})-{f(co_post)}({f(o_post)})={f(post_profit)}",
        )),
        Step("5 · Compare policies", (
            rf"\Delta E[\Pi]=E[\Pi_{{post}}]-E[\Pi_{{orig}}]={f(post_profit)}-{f(orig_profit)}={f(post_profit-orig_profit)}",
        ), (f"Postponement increases expected profit by ${post_profit-orig_profit:,.3f}." if post_profit > orig_profit else
            f"Postponement reduces expected profit by ${orig_profit-post_profit:,.3f}." if post_profit < orig_profit else
            "Both policies yield the same expected profit.")),
    ]
    out.comparisons = [
        {"System": "Original", "Continuous Q": f(original_q), "Integer Q": original_i,
         "Expected profit $": f(orig_profit)},
        {"System": "Postponed", "Continuous Q": f(post_q), "Integer Q": post_i,
         "Expected profit $": f(post_profit)},
    ]
    out.notices = [
        "Sources: lecture slides 27–33; Complete Manual §9.1–9.5; Silver, Pyke & Thomas §9.4.1.",
        "Assumes demand is Normal and assembly can be performed on demand without delay or capacity limit.",
        "Postponement is not automatically superior if total cost, salvage, or service assumptions differ.",
        "Compare continuous optima only with continuous profits, and integer decisions only with their own evaluated profits.",
    ]
    return out


def hw5(raw: Mapping[str, object]) -> Solution:
    v0 = number(raw, "v0", positive=True)
    g0 = number(raw, "g0", nonnegative=True)
    co = v0-g0
    ensure(co > 0, "Unfinished base cost must exceed base salvage value.")
    items = items_from(raw, required=2)
    raw_items = raw["items"]
    assert isinstance(raw_items, list)
    t = [number(row, "t", nonnegative=True) for row in raw_items]
    mu = sum(x.mu for x in items)
    ensure(mu > 0, "Total mean demand must be > 0 for demand-weighted FCFS approximation.")
    sig = math.sqrt(sum(x.sigma ** 2 for x in items))
    cu_post = [x.p - v0 - finishing + x.b for x, finishing in zip(items, t)]
    ensure(all(c > 0 for c in cu_post), "Postponed underage costs must be positive for each design.")
    avg_cu = sum(x.mu * c for x, c in zip(items, cu_post)) / mu
    alpha_post = avg_cu / (avg_cu + co)
    post_q = optimal_normal_quantity(mu, sig, avg_cu, co)
    post_i = integer_normal_quantity(post_q, mu, sig, avg_cu, co)
    original_q = [optimal_normal_quantity(x.mu, x.sigma, x.cu, x.co) for x in items]
    original_i = [integer_normal_quantity(q, x.mu, x.sigma, x.cu, x.co)
                  for q, x in zip(original_q, items)]
    original_profit = sum(x.expected_profit(float(q)) for x, q in zip(items, original_i))
    post_baseline = sum((x.p-v0-ti)*x.mu for x,ti in zip(items,t))
    u,o = loss(float(post_i), mu, sig)
    post_profit = post_baseline - avg_cu*u - co*o
    out = Solution("HW5", "Postponement · FCFS Value of Flexibility")
    out.data = {"Q_original_cont": original_q, "Q_original_int": original_i,
                "Q_post_cont": post_q, "Q_post_int": post_i,
                "profit_original": original_profit, "profit_post_approx": post_profit,
                "gain_approx": post_profit - original_profit, "cu_weighted": avg_cu,
                "mu_pooled": mu, "sigma_pooled": sig}
    out.metrics = [Metric("Original total", sum(original_i), "finished units"),
                   Metric("Pooled common base", post_i, "unfinished units"),
                   Metric("Original expected profit", original_profit, "$"),
                   Metric("Postponed expected profit (approx.)", post_profit, "$"),
                   Metric("Estimated improvement", post_profit-original_profit, "$")]
    original_economics = []
    original_decisions = []
    per_item_profits = [x.expected_profit(float(qi)) for x, qi in zip(items, original_i)]
    for j,(x,q,qi) in enumerate(zip(items,original_q,original_i),1):
        original_economics.extend((
            rf"c_{{u,{j}}}=p_{j}-v_{j}+B_{j}={f(x.p)}-{f(x.v)}+{f(x.b)}={f(x.cu)}",
            rf"c_{{o,{j}}}=v_{j}-g_{j}={f(x.v)}-{f(x.g)}={f(x.co)}",
        ))
        original_decisions.append(
            rf"Q^*_{{{j}}}=\mu_{j}+\sigma_{j}\Phi^{{-1}}\!\left(\frac{{c_{{u,{j}}}}}{{c_{{u,{j}}}+c_{{o,{j}}}}}\right)"
            rf"={f(x.mu)}+{f(x.sigma)}\Phi^{{-1}}({f(x.alpha,6)})={f(q)}")
        for candidate in (max(0, math.floor(q)), max(0, math.floor(q)) + 1):
            u_candidate, o_candidate = loss(float(candidate), x.mu, x.sigma)
            candidate_profit = x.expected_profit(float(candidate))
            original_decisions.append(
                rf"E[\Pi_{{{j}}}({candidate})]=(p_{j}-v_{j})\mu_{j}"
                rf"-c_{{u,{j}}}U_{j}({candidate})-c_{{o,{j}}}O_{j}({candidate})"
                rf"={f(x.p-x.v)}({f(x.mu)})-{f(x.cu)}({f(u_candidate)})"
                rf"-{f(x.co)}({f(o_candidate)})={f(candidate_profit)}"
            )
        original_decisions.append(
            rf"Q_{{{j},int}}=\operatorname*{{arg\,max}}_{{n\in\{{{max(0,math.floor(q))},{max(0,math.floor(q))+1}\}}}}"
            rf"E[\Pi_{j}(n)]={qi}"
        )
        u_item, o_item = loss(float(qi), x.mu, x.sigma)
        original_decisions.append(
            rf"E[\Pi_{{{j}}}]=(p_{j}-v_{j})\mu_{j}-c_{{u,{j}}}U_{j}(Q_{j})-c_{{o,{j}}}O_{j}(Q_{j})"
            rf"={f(x.p-x.v)}({f(x.mu)})-{f(x.cu)}({f(u_item)})-{f(x.co)}({f(o_item)})"
            rf"={f(per_item_profits[j-1])}"
        )
    total_sd_sub = "+".join(f(x.sigma) + "^2" for x in items)
    average_num = "+".join(f(x.mu)+"("+f(c)+")" for x,c in zip(items,cu_post))
    out.steps = [
        Step("1 · Original separate-stock unit economics", tuple(original_economics), open_by_default=True),
        Step("2 · Original order decisions and profit", tuple(original_decisions) + (
            rf"E[\Pi_{{orig}}]=\sum_i E[\Pi_i(Q_{{i,int}})]"
            rf"={' + '.join(f(v) for v in per_item_profits)}={f(original_profit)}",
        ), "Each design is stocked separately, so compute its order quantity and expected profit individually."),
        Step("3 · Pool independent Normal demand", (
            rf"\mu_\Sigma=\sum_i\mu_i="+"+".join(f(x.mu) for x in items)+rf"={f(mu)}",
            rf"\sigma_\Sigma=\sqrt{{\sum_i\sigma_i^2}}=\sqrt{{{total_sd_sub}}}={f(sig)}",
        ), "Independent design demands combine by adding their means and variances."),
        Step("4 · Underage cost weighted by mean demand (FCFS)", tuple(
            rf"c_{{u,{j},post}}=p_{j}-v_0-t_{j}+B_{j}={f(x.p)}-{f(v0)}-{f(ti)}+{f(x.b)}={f(c)}"
            for j,(x,ti,c) in enumerate(zip(items,t,cu_post),1)) + (
            rf"\bar c_u=\frac{{\sum_i\mu_i c_{{u,i}}}}{{\sum_i\mu_i}}=\frac{{{average_num}}}{{{f(mu)}}}={f(avg_cu)}",
            rf"c_o=v_0-g_0={f(v0)}-{f(g0)}={f(co)}",
        ), "Weight each design’s underage cost by its share of expected demand."),
        Step("5 · Pooled base order", (
            rf"\alpha_{{FCFS}}=\frac{{\bar c_u}}{{\bar c_u+c_o}}=\frac{{{f(avg_cu)}}}{{{f(avg_cu+co)}}}={f(alpha_post,6)}",
            rf"Q^*_0=\mu_\Sigma+\sigma_\Sigma\Phi^{{-1}}(\alpha_{{FCFS}})={f(mu)}+{f(sig)}\Phi^{{-1}}({f(alpha_post,6)})={f(post_q)}",
            *_candidate_profit_chains("FCFS", post_q, mu, sig,
                                     post_baseline / mu, avg_cu, co),
        )),
        Step("6 · Approximate expected profit comparison", (
            rf"\Pi_{{base}}=\sum_i(p_i-v_0-t_i)\mu_i"
            rf"={' + '.join(f'({f(x.p)}-{f(v0)}-{f(ti)})({f(x.mu)})' for x,ti in zip(items,t))}={f(post_baseline)}",
            *_normal_loss_chains(post_i, mu, sig, pooled=True),
            rf"E[\Pi_{{post}}]\approx\Pi_{{base}}-\bar c_u U_\Sigma-c_o O_\Sigma"
            rf"={f(post_baseline)}-{f(avg_cu)}({f(u)})-{f(co)}({f(o)})={f(post_profit)}",
            rf"\Delta E[\Pi]\approx E[\Pi_{{post}}]-E[\Pi_{{orig}}]"
            rf"={f(post_profit)}-{f(original_profit)}={f(post_profit-original_profit)}",
            rf"\mathrm{{Gain}}\%\approx\frac{{\Delta E[\Pi]}}{{E[\Pi_{{orig}}]}}\times100"
            rf"=\frac{{{f(post_profit-original_profit)}}}{{{f(original_profit)}}}\times100"
            rf"={f(100*(post_profit-original_profit)/original_profit)}\%" if original_profit != 0 else
            r"\mathrm{Gain}\%\quad\mathrm{undefined\ when\ original\ profit\ is\ zero}",
        ), (f"Pooled stocking increases estimated expected profit by ${post_profit-original_profit:,.3f}." if post_profit > original_profit else
            f"Pooled stocking reduces estimated expected profit by ${original_profit-post_profit:,.3f}." if post_profit < original_profit else
            "Both policies yield the same estimated expected profit.")),
    ]
    out.comparisons = [
        {"System": "Original · separate", "Quantity": ", ".join(str(x) for x in original_i),
         "Total units": sum(original_i), "Expected profit $": f(original_profit)},
        {"System": "Postponed · pooled (approx.)", "Quantity": str(post_i),
         "Total units": post_i, "Expected profit $": f(post_profit)},
    ]
    out.notices = [
        "Sources: lecture slides 34–38; Complete Manual §9.6–9.12; Silver, Pyke & Thomas §9.4.2.",
        "Assumes independent Normal design demands, on-demand finishing of any base, no priority allocation (first-come first-served).",
        "Weighted-underage FCFS approximation may fail if customer arrival patterns or product identity affect shortage composition.",
        "Economic gain can reflect BOTH pooling and changed unit costs; do not attribute the entire improvement to pooling alone.",
    ]
    return out
