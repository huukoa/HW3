"""Chapter 3 theory, organized by homework without duplicating shared derivations.

The source of mathematical content is Chapter3_Complete_Manual.pdf.  The
section numbers in each title refer to that manual.  This module is display
content only: calculation routines remain in continuous/periodic/etc.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class TheoryLine:
    kind: Literal['text', 'math', 'bullet']
    value: str


@dataclass(frozen=True)
class TheorySection:
    title: str
    lines: tuple[TheoryLine, ...]


@dataclass(frozen=True)
class Knowledge:
    introduction: str
    sections: tuple[TheorySection, ...]


def text(value: str) -> TheoryLine:
    return TheoryLine('text', value)


def math(value: str) -> TheoryLine:
    return TheoryLine('math', value)


def bullet(value: str) -> TheoryLine:
    return TheoryLine('bullet', value)


def section(title: str, *lines: TheoryLine) -> TheorySection:
    return TheorySection(title, lines)


KNOWLEDGE: dict[str, Knowledge] = {
    'HW1': Knowledge(
        'Simultaneous continuous-review (s, Q) for a fast-moving Class A item with a cost per stockout occasion. '
        'This is the main home for the shared EOQ and B1 derivations used by HW3.',
        (
            section('4.1 · Class A items, shortage costs and (s, Q) policy',
                text('Class A items have high annual usage value Dv. In a continuous-review (s, Q) '
                     'system, inventory position is monitored continuously; when it reaches the '
                     'reorder level s, order a fixed quantity Q. The reorder point controls timing '
                     'and the order quantity controls batch size.'),
                math(r'\mathrm{IP}=\mathrm{OnHand}+\mathrm{OnOrder}-\mathrm{Backorders}'),
                math(r'\mathrm{AnnualUsageValue}=Dv'),
                text('The manual distinguishes three economically different shortage measures. '
                     'They must not be interchanged.'),
                bullet('B₁: charge per stockout occasion ($/event), used in HW1 and HW3.'),
                bullet('B₂: charge per unit backordered, expressed as a fraction of unit value in the manual.'),
                bullet('B₃: charge per unit short per specified time or review interval.'),
            ),
            section('4.2 · EOQ derived from ordering and cycle-holding costs',
                text('Let D be annual demand, A the fixed cost per order, v the unit acquisition '
                     'cost, and r the annual holding fraction (r_y in the manual). The annual '
                     'holding cost per unit is h = vr.'),
                math(r'h=vr'),
                math(r'TC_0(Q)=\frac{AD}{Q}+\frac{hQ}{2}'),
                text('Differentiate with respect to Q and set the first derivative equal to zero.'),
                math(r'\frac{dTC_0}{dQ}=-\frac{AD}{Q^2}+\frac{h}{2}=0'),
                math(r'Q^2=\frac{2AD}{h}\quad\Rightarrow\quad Q_0=EOQ=\sqrt{\frac{2AD}{h}}'),
                math(r'\frac{d^2TC_0}{dQ^2}=\frac{2AD}{Q^3}>0'),
                text('The second derivative establishes the unique minimum of this EOQ-only '
                     'cost function. EOQ is the starting point, not generally the simultaneous '
                     '(s, Q) optimum when shortage penalties are included.'),
            ),
            section('4.3 · B₁ annual relevant-cost objective',
                text('Lead-time demand is Normal with mean μ_L and standard deviation σ_L. '
                     'Use a nonnegative safety factor k and express the reorder level through '
                     'lead-time demand.'),
                math(r'X_L\sim N(\mu_L,\sigma_L^2)\quad;\quad s=\mu_L+k\sigma_L\quad(k\geq0)'),
                text('Write U_L(s) for expected shortage and O_L(s) for expected leftovers at s. '
                     'The identity is exact; the subsequent holding expression is the '
                     'approximation used in the manual.'),
                math(r'O_L(s)=s-\mu_L+U_L(s)'),
                math(r'C_{\mathrm{hold}}\approx h\left(\frac{Q}{2}+k\sigma_L\right)'),
                text('The approximate number of ordering cycles per year is D/Q, and the '
                     'probability that lead-time demand exceeds s is the Normal upper tail.'),
                math(r'P(X_L>s)=1-\Phi(k)'),
                math(r'C_{\mathrm{stockout}}=\frac{DB_1}{Q}[1-\Phi(k)]'),
                math(r'TC(Q,k)=\frac{D[A+B_1(1-\Phi(k))]}{Q}+h\left(\frac{Q}{2}+k\sigma_L\right)'),
            ),
            section('4.3 · First-order condition for Q with k fixed',
                text('Differentiate the annual cost with respect to Q, treating k as fixed.'),
                math(r'\frac{\partial TC}{\partial Q}=-\frac{D[A+B_1(1-\Phi(k))]}{Q^2}+\frac{h}{2}=0'),
                math(r'Q(k)=\sqrt{\frac{2D[A+B_1(1-\Phi(k))]}{h}}'),
                math(r'Q(k)=EOQ\sqrt{1+\frac{B_1}{A}[1-\Phi(k)]}'),
                text('This optimal Q conditional on k incorporates the probability of a '
                     'stockout event. It reduces to EOQ when the shortage term vanishes.'),
            ),
            section('4.3 · First-order condition for k and the k = 0 boundary',
                text('Differentiate with respect to k, treating Q as fixed. The standard '
                     'Normal density is φ and its cumulative distribution function is Φ.'),
                math(r'\phi(k)=\frac{e^{-k^2/2}}{\sqrt{2\pi}}'),
                math(r'\frac{\partial TC}{\partial k}=-\frac{DB_1}{Q}\phi(k)+h\sigma_L=0'),
                math(r'\phi(k)=\frac{h\sigma_L Q}{DB_1}'),
                text('Take natural logarithms, define c, and apply the nonnegative safety-factor '
                     'boundary exactly as in Manual (4.4).'),
                math(r'c=\frac{DB_1}{\sqrt{2\pi}\,h\sigma_L}'),
                math(r'k(Q)=\begin{cases}\sqrt{2\ln(c/Q)},&Q<c\\0,&Q\geq c\end{cases}'),
                text('The square-root branch applies only to Q < c; otherwise use k = 0. '
                     'A stationary pair still needs the boundary-cost comparison.'),
            ),
            section('4.3–4.5 · Simultaneous fixed-point iteration',
                text('Begin with EOQ and alternate the safety-factor and order-quantity '
                     'conditions. Retain full internal precision until the final decision.'),
                math(r'Q_0=\sqrt{\frac{2AD}{h}}'),
                math(r'k_j=\sqrt{2\ln\left(\frac{DB_1}{\sqrt{2\pi}\,h\sigma_L Q_j}\right)}\quad(Q_j<c)'),
                math(r'Q_{j+1}=EOQ\sqrt{1+\frac{B_1}{A}[1-\Phi(k_j)]}'),
                math(r's^*=\mu_L+k^*\sigma_L'),
                text('If an iteration enters the Q ≥ c branch, use k = 0 and evaluate the '
                     'corresponding cost. For valid interior iterates, repeat the two update '
                     'equations until the required numerical accuracy is reached.'),
            ),
            section('4.4 · Hessian, local optimality and fixed-point convergence',
                text('At an interior stationary pair, the Hessian and determinant of the '
                     'two-decision annual cost are given by Manual §4.4.'),
                math(r'H^*=\begin{pmatrix}h/Q^*&h\sigma_L/Q^*\\h\sigma_L/Q^*&h\sigma_L k^*\end{pmatrix}'),
                math(r'\det H^*=\frac{h^2\sigma_L}{(Q^*)^2}(k^*Q^*-\sigma_L)'),
                math(r'H^*\succ0\quad\Longleftrightarrow\quad k^*Q^*>\sigma_L'),
                text('For the interior update map T, the derivative is:'),
                math(r'T(Q)=\sqrt{\frac{2D}{h}\left[A+B_1\left(1-\Phi\left(\sqrt{2\ln(c/Q)}\right)\right)\right]}'),
                math(r'k^\prime(Q)=-\frac{1}{Qk(Q)}'),
                math(r'T^\prime(Q)=\frac{\sigma_L}{k(Q)T(Q)}'),
                math(r'T^\prime(Q^*)=\frac{\sigma_L}{k^*Q^*}'),
                text('Thus the positive-definite Hessian criterion and a local contraction '
                     'criterion coincide at the interior fixed point. Global optimality additionally '
                     'requires comparing stationary candidates with the boundary k = 0.'),
            ),
            section('2.6, 2.8 & 4.4 · Stopping, numerical accuracy and annual cost',
                text('A guaranteed iteration count needs an interval I = [a,b] mapped into '
                     'itself and an upper derivative bound valid throughout the interval, '
                     'rather than simply observing successive iterates becoming similar.'),
                math(r'T([a,b])\subseteq[a,b]\quad;\quad\sup_{Q\in[a,b]}|T^\prime(Q)|\leq\gamma<1'),
                math(r'|Q_j-Q^*|\leq\gamma^j(b-a)'),
                math(r'N\geq\max\left\{0,\left\lceil\frac{\ln[\varepsilon/(b-a)]}{\ln\gamma}\right\rceil\right\}'),
                math(r'|Q_j-Q^*|\leq\frac{\gamma}{1-\gamma}|Q_j-Q_{j-1}|'),
                text('To certify displayed rounding to m places, use enclosing bounds whose '
                     'rounded values agree. At a joint interior stationary point, the Q '
                     'first-order condition gives a shortcut for annual cost.'),
                math(r'\mathrm{Round}_m(Q_-)=\mathrm{Round}_m(Q_+)'),
                math(r'TC^*=h(Q^*+k^*\sigma_L)'),
                text('For a prescribed Q or nonstationary candidate, use the full TC(Q,k) '
                     'equation from §4.3 instead of the stationary shortcut.'),
            ),
        ),
    ),
    'HW3': Knowledge(
        'Fixed-EOQ continuous review with a charge for expediting once per stockout event. '
        'The shared (s, Q), EOQ derivation and B₁ first-order conditions are in HW1 Theory §§4.1–4.3.',
        (
            section('4.6 · Why Q is fixed at EOQ in this problem',
                text('The problem prescribes Q = EOQ rather than simultaneously optimizing '
                     'Q and s. B₁ is a fixed cost per impending stockout, independent of the '
                     'number of units short; it is not a per-unit penalty.'),
                math(r'h=vr\quad;\quad Q=EOQ=\sqrt{\frac{2AD}{h}}'),
                text('The derivation of EOQ, the definition of inventory position, and the '
                     'B₁ annual objective are given once in HW1 Theory §§4.1–4.3.'),
            ),
            section('4.3, 4.6 · Reorder point for the fixed Q',
                text('The reorder point is adjusted for the probability of a stockout '
                     'during lead time. The fixed-Q first-order condition applies with '
                     'k ≥ 0 and s = μ_L + kσ_L.'),
                math(r'\phi(k)=\frac{h\sigma_L Q}{DB_1}'),
                math(r'c=\frac{DB_1}{\sqrt{2\pi}\,h\sigma_L}'),
                math(r'k=\begin{cases}\sqrt{2\ln(c/Q)},&Q<c\\0,&Q\geq c\end{cases}'),
                math(r's=\mu_L+k\sigma_L'),
                text('This is the minimizer in k for the chosen Q. The branch is selected '
                     'before evaluating costs.'),
            ),
            section('4.6 · Ordering, holding, expediting and total annual costs',
                text('Compute the three relevant annual components separately; all use '
                     'the same fixed Q and its corresponding safety factor k.'),
                math(r'C_{\mathrm{order}}=\frac{AD}{Q}'),
                math(r'C_{\mathrm{hold}}=h\left(\frac{Q}{2}+k\sigma_L\right)'),
                math(r'C_{\mathrm{expedite}}=\frac{DB_1}{Q}[1-\Phi(k)]'),
                math(r'TC(Q,k)=C_{\mathrm{order}}+C_{\mathrm{hold}}+C_{\mathrm{expedite}}'),
                text('Use this full cost at fixed Q; the stationary shortcut from HW1 '
                     'applies only when Q also satisfies its own first-order condition.'),
            ),
            section('4.6 · Test a larger order quantity',
                text('To examine an increase of δ percent, compute a new Q, recalculate '
                     'the best k for that Q, and compare the full annual costs.'),
                math(r'Q_{\mathrm{alt}}=EOQ\left(1+\frac{\delta}{100}\right)'),
                math(r'k_{\mathrm{alt}}=k(Q_{\mathrm{alt}})\quad;\quad s_{\mathrm{alt}}=\mu_L+k_{\mathrm{alt}}\sigma_L'),
                math(r'\Delta TC=TC(Q_{\mathrm{alt}},k_{\mathrm{alt}})-TC(EOQ,k_{\mathrm{EOQ}})'),
                text('A negative difference means the larger Q reduces relevant annual '
                     'cost. EOQ minimizes ordering plus cycle holding, not necessarily '
                     'the total cost including event-based expediting.'),
            ),
        ),
    ),
    'HW2': Knowledge(
        'Periodic-review (R, s, S) with the revised power approximation. It is a '
        'decision procedure with two branches, rather than a fixed-point iterative method.',
        (
            section('6.1 · Review policy and protection period',
                text('Inventory position is checked only at review epochs separated by R. '
                     'If IP ≤ s, order enough to raise inventory position to S; otherwise '
                     'do not order. The order quantity is not necessarily S − s.'),
                math(r'Q_{\mathrm{actual}}=\begin{cases}S-\mathrm{IP},&\mathrm{IP}\leq s\\0,&\mathrm{IP}>s\end{cases}'),
                text('A demand just after a review may wait R until the next review and '
                     'then L through replenishment. The protection period is R + L.'),
                math(r'\mu_R=DR\quad;\quad\mu_P=D(R+L)\quad;\quad r_R=rR'),
                text('Convert all time inputs to the same unit before these expressions. '
                     'σ_P is the standard deviation of protection-period demand.'),
            ),
            section('6.2 · Revised power approximation',
                text('The power approximation estimates reorder-related quantities from '
                     'the review demand, acquisition economics and protection-period '
                     'variability. Its coefficients are fitted numerical constants.'),
                math(r'Q_p=a\mu_R^{1-b}\left(\frac{A}{vr_R}\right)^b\left(1+\frac{\sigma_P^2}{\mu_R^2}\right)^c'),
                math(r'a=1.30\quad;\quad b=0.506\quad;\quad c=0.116'),
                text('The coefficient of μ_R is 0.494 because 1 − b = 0.494. '
                     'No fixed-point iteration is required to compute Q_p, z_p and s_p.'),
            ),
            section('6.3 · Step 1: Q_p, z_p and s_p',
                text('First calculate review demand μ_R, protection demand μ_P and the '
                     'review-period holding fraction r_R. Then evaluate the three '
                     'revised-power intermediates in order.'),
                math(r'Q_p=1.30\mu_R^{0.494}\left(\frac{A}{vr_R}\right)^{0.506}\left(1+\frac{\sigma_P^2}{\mu_R^2}\right)^{0.116}'),
                math(r'z_p=\sqrt{\frac{Q_pr_R}{\sigma_PB_3}}'),
                math(r's_p=0.973\mu_P+\sigma_P\left(\frac{0.183}{z_p}+1.063-2.192z_p\right)'),
                text('B₃ is a fractional charge per unit short per review interval; r_R '
                     'must refer to that same interval. Retain intermediate precision.'),
            ),
            section('6.4 · Step 2: Branch A',
                text('Compare the estimated order size against expected demand over '
                     'one review interval.'),
                math(r'H=\frac{Q_p}{\mu_R}'),
                math(r'H>1.5\quad\Longrightarrow\quad s=s_p\quad;\quad S=s_p+Q_p'),
                text('When this inequality is true, use Branch A directly and then '
                     'apply the requested whole-unit convention.'),
            ),
            section('6.5 · Step 3: Branch B and limiting (R, S) policy',
                text('When H ≤ 1.5, compute the limiting order-up-to level S₀ '
                     'from protection-period expected underage and overage.'),
                math(r'C_0(S_0)=vr_R O_P(S_0)+vB_3 U_P(S_0)'),
                math(r'\frac{dC_0}{dS_0}=v[r_RF_P(S_0)-B_3(1-F_P(S_0))]=0'),
                math(r'F_P(S_0)=\frac{B_3}{B_3+r_R}'),
                math(r'S_0=\mu_P+\sigma_P\Phi^{-1}\left(\frac{B_3}{B_3+r_R}\right)'),
                math(r's=\min(s_p,S_0)\quad;\quad S=\min(s_p+Q_p,S_0)'),
                text('The S calculation in this branch is not always s + Q_p; '
                     'the two min expressions must be evaluated independently.'),
            ),
            section('6.6–6.8 · Decision flow and interpretation',
                bullet('Normalize annual/review units and compute μ_R, μ_P, r_R.'),
                bullet('Evaluate Q_p, z_p, s_p without intermediate rounding.'),
                bullet('Compare Q_p/μ_R to 1.5 to select the correct branch.'),
                bullet('Compute s and S from that branch; round final order levels.'),
                bullet('At a review, order S − IP if IP ≤ s, otherwise order zero.'),
                text('The threshold and coefficients are those of Manual §6, '
                     'not a re-derived optimizer. Protection-period demand uses R + L, '
                     'not only lead time L.'),
            ),
        ),
    ),
    'HW4': Knowledge(
        'Several seasonal products share one acquisition budget. This homework owns '
        'the shared Newsvendor critical-ratio, Normal loss and multiplier derivations '
        'also reused in the two postponement homeworks.',
        (
            section('1.1–1.7 · Expected shortage, overage and quantiles',
                text('For uncertain demand X and order quantity q, expected unmet '
                     'demand is U(q); expected leftovers are O(q). These are '
                     'positive-part expectations.'),
                math(r'U(q)=E[(X-q)^+]\quad;\quad O(q)=E[(q-X)^+]'),
                math(r'O(q)=U(q)+q-\mu'),
                math(r'E[\min(X,q)]=\mu-U(q)=q-O(q)'),
                math(r'U(q)=\int_q^\infty[1-F_X(t)]\,dt'),
                text('For a mismatch objective C(q) = c_u U(q) + c_o O(q), '
                     'differentiation gives the continuous critical fractile.'),
                math(r'C^\prime(q)=(c_u+c_o)F_X(q)-c_u'),
                math(r'\alpha=\frac{c_u}{c_u+c_o}\quad;\quad q^*=F_X^{-1}(\alpha)'),
                text('For discrete demand, use the smallest q with F_X(q) ≥ α. '
                     'Equality F_X(q)=α need not occur when probabilities jump.'),
            ),
            section('3.1 · Normal quantile, expected shortage and overage',
                text('For X normally distributed with mean μ and variance σ², '
                     'standardize by z. The Normal PDF and CDF are φ and Φ.'),
                math(r'X\sim N(\mu,\sigma^2)\quad;\quad z=\frac{q-\mu}{\sigma}'),
                math(r'F_X(q)=\Phi(z)\quad;\quad q_\alpha=\mu+\sigma\Phi^{-1}(\alpha)'),
                math(r'G_u(z)=\phi(z)-z[1-\Phi(z)]'),
                math(r'U(q)=\sigma G_u(z)\quad;\quad O(q)=U(q)+q-\mu'),
                math(r'C(q_\alpha)=\sigma(c_u+c_o)\phi(\Phi^{-1}(\alpha))'),
                text('The final mismatch-cost shortcut applies only at an '
                     'unconstrained interior optimum; constrained or rounded '
                     'quantities use the general U/O expression.'),
            ),
            section('7.1–7.4 · Single-item Newsvendor and expected profit',
                text('Choose the order quantity before seasonal demand is '
                     'observed. Selling price is p, acquisition cost v, '
                     'salvage g and an additional penalty B per unit unmet.'),
                math(r'\Pi(q,X)=p\min(X,q)+g(q-X)^+-vq-B(X-q)^+'),
                math(r'c_u=p-v+B\quad;\quad c_o=v-g'),
                math(r'E[\Pi(q,X)]=(p-v)\mu-c_uU(q)-c_oO(q)'),
                math(r'\alpha=\frac{p-v+B}{p-g+B}\quad;\quad q^*=F_X^{-1}(\alpha)'),
                math(r'E[\Pi(q,X)]=(p-g)\mu-(v-g)q-(p-g+B)U(q)'),
                text('For an integer purchase quantity from a continuous '
                     'Normal model, compare nearby integers using the general '
                     'expected-profit expression.'),
            ),
            section('2.3, 8.1 · One-budget multi-item optimization',
                text('For item i, expected mismatch cost adds across items. '
                     'The decision is Q_i ≥ 0 and the acquisition budget is W.'),
                math(r'C_i(Q_i)=c_{u,i}U_i(Q_i)+c_{o,i}O_i(Q_i)'),
                math(r'c_{u,i}=p_i-v_i+B_i\quad;\quad c_{o,i}=v_i-g_i'),
                math(r'\min_{Q_i\geq0}\sum_i C_i(Q_i)\quad\mathrm{subject\ to}\quad\sum_i v_i Q_i\leq W'),
                text('The separable convex objective and linear resource '
                     'constraint allow one Lagrange multiplier M ≥ 0.'),
                math(r'\mathcal L(Q,M)=\sum_i[C_i(Q_i)+Mv_iQ_i]-MW'),
                math(r'M\geq0\quad;\quad\sum_i v_iQ_i\leq W\quad;\quad M\left(\sum_i v_iQ_i-W\right)=0'),
            ),
            section('8.2 · Adjusted critical ratio from stationarity',
                text('For an interior differentiable item, stationarity '
                     'of the Lagrangian gives the budget-adjusted critical ratio.'),
                math(r'C_i^\prime(Q_i)+Mv_i=0'),
                math(r'F_i(Q_i)=\frac{c_{u,i}-Mv_i}{c_{u,i}+c_{o,i}}'),
                math(r'\alpha_i(M)=\frac{p_i-(1+M)v_i+B_i}{p_i-g_i+B_i}'),
                math(r'Q_i(M)=\mu_i+\sigma_i\Phi^{-1}(\alpha_i(M))\quad(\mathrm{interior})'),
                text('When α_i is at or below F_i(0), choose Q_i = 0. '
                     'Do not send probabilities outside (0, 1) to the Normal inverse CDF.'),
            ),
            section('8.3 · Determine M with a budget residual and bisection',
                text('Start with the unconstrained solution M = 0. '
                     'If its acquisition spending is at most W, M* = 0. '
                     'Otherwise the budget is binding and M* is a root of G(M).'),
                math(r'G(M)=\sum_i v_i Q_i(M)-W'),
                math(r'G(0)\leq0\quad\Rightarrow\quad M^*=0'),
                math(r'G(M^*)=0\quad(M^*>0)'),
                text('Each Q_i(M) is nonincreasing in M. Establish a bracket '
                     'with G(M_L) ≥ 0 ≥ G(M_U) and bisect it.'),
                math(r'G(M_{mid})>0\Rightarrow M_L\leftarrow M_{mid}'),
                math(r'G(M_{mid})<0\Rightarrow M_U\leftarrow M_{mid}'),
                math(r'Q_i(M_U)\leq Q_i^*\leq Q_i(M_L)'),
                text('Bracket bounds may certify displayed rounding when '
                     'both bounds round to the same number of decimal places.'),
            ),
            section('8.5 · Integer orders and a global optimality check',
                text('A continuous KKT solution is not necessarily a feasible '
                     'or optimal integer order. Preserve the budget constraint '
                     'for integer vectors; compare expected profits.'),
                math(r'Q_i\in\mathbb Z_{\geq0}\quad;\quad\sum_i v_iQ_i\leq W'),
                math(r'H_i(q)=C_i(q)+M_0v_iq'),
                math(r'H_i(k_i-1)-H_i(k_i)\geq0'),
                math(r'H_i(k_i+1)-H_i(k_i)\geq0'),
                text('For a candidate that minimizes every integer H_i '
                     'and exactly uses the budget, the manual supplies an '
                     'integer Lagrangian sufficiency certificate. The '
                     'software additionally searches feasible integer '
                     'quantities rather than rounding each item independently.'),
                math(r'E[\Pi_{total}]=\sum_i[(p_i-v_i)\mu_i-c_{u,i}U_i(Q_i)-c_{o,i}O_i(Q_i)]'),
            ),
        ),
    ),
    'HW6': Knowledge(
        'Postponement through delayed financial commitment: purchase an unfinished '
        'base now, but pay finishing/assembly cost only when a unit is sold. '
        'The general Newsvendor proof and Normal loss formulas are in HW4 Theory.',
        (
            section('9.1–9.2 · What is being postponed?',
                text('The original policy buys a finished product at cost v. '
                     'The postponed policy purchases a base item at cost v₀ '
                     'and pays finishing cost t only when a unit is actually '
                     'sold. Leftover base units can be salvaged at g₀.'),
                text('Financial commitment is distinct from pooling across '
                     'multiple end-product designs (covered in HW5).'),
            ),
            section('7.2, 9.2 · Original finished-product policy',
                text('Use the ordinary single-item Newsvendor charges for '
                     'finished products. The general expected-profit '
                     'derivation is given once in HW4 Theory §§7.1–7.4.'),
                math(r'c_{u,orig}=p-v+B\quad;\quad c_{o,orig}=v-g'),
                math(r'\alpha_{orig}=\frac{p-v+B}{p-g+B}'),
                math(r'Q_{orig}^*=F_X^{-1}(\alpha_{orig})'),
                math(r'E[\Pi_{orig}(Q)]=(p-v)\mu-c_{u,orig}U(Q)-c_{o,orig}O(Q)'),
            ),
            section('9.3 · Pointwise and expected postponed profit',
                text('When realized demand is x, only min(x,Q₀) base '
                     'units are finished. Additional shortage penalty '
                     'B is charged on unmet units.'),
                math(r'\Pi_{post}(Q_0,x)=(p-t)\min(x,Q_0)+g_0(Q_0-x)^+-v_0Q_0-B(x-Q_0)^+'),
                text('Taking expectations and using the shortage/overage '
                     'identities from HW4 gives:'),
                math(r'E[\Pi_{post}(Q_0)]=(p-t)[\mu-U(Q_0)]+g_0O(Q_0)-v_0Q_0-BU(Q_0)'),
                math(r'c_{u,post}=p-v_0-t+B\quad;\quad c_{o,post}=v_0-g_0'),
                math(r'E[\Pi_{post}(Q_0)]=(p-v_0-t)\mu-c_{u,post}U(Q_0)-c_{o,post}O(Q_0)'),
            ),
            section('9.3 · Optimal base quantity',
                text('The independent-of-Q₀ profit baseline lets the '
                     'underage/overage critical-ratio rule determine '
                     'the optimal unfinished base order.'),
                math(r'\alpha_{post}=\frac{p-v_0-t+B}{p-g_0-t+B}'),
                math(r'Q_{0}^*=F_X^{-1}(\alpha_{post})'),
                math(r'X\sim N(\mu,\sigma^2)\quad\Rightarrow\quad Q_0^*=\mu+\sigma\Phi^{-1}(\alpha_{post})'),
                text('Evaluate whole-unit candidates near the continuous '
                     'quantity with the appropriate expected-profit '
                     'function rather than rounding unconditionally.'),
            ),
            section('9.4 · Financial-commitment benefit when costs match',
                text('If the finished acquisition cost equals base plus '
                     'finishing and salvage values match, the underage '
                     'charges are identical; postponement reduces the '
                     'overage charge by t.'),
                math(r'v=v_0+t\quad;\quad g=g_0'),
                math(r'c_{u,orig}=c_{u,post}'),
                math(r'c_{o,orig}=c_{o,post}+t'),
                math(r'E[\Pi_{post}(q)]-E[\Pi_{orig}(q)]=tO(q)\geq0'),
                math(r'\max_q E[\Pi_{post}(q)]\geq\max_q E[\Pi_{orig}(q)]'),
                text('For different total costs, salvage values or '
                     'fulfillment conditions, compare the two expected '
                     'profits directly; this inequality need not hold.'),
            ),
            section('9.5 · Original versus postponed decision comparison',
                bullet('Compute original underage/overage and critical ratio.'),
                bullet('Compute postponed underage/overage and critical ratio.'),
                bullet('For both policies, compare neighboring integer order quantities.'),
                bullet('Compute expected profits with the policy-specific cost function and subtract.'),
                math(r'\Delta\Pi=E[\Pi_{post}(Q_0)]-E[\Pi_{orig}(Q)]'),
                text('For Normal demand, U(Q) and O(Q) are evaluated '
                     'using the Normal loss function from HW4 Theory §3.1.'),
            ),
        ),
    ),
    'HW5': Knowledge(
        'Value of flexibility from one common unfinished base stock for several '
        'designs. Shared Newsvendor profit/Normal-loss foundations appear once '
        'in HW4 Theory; delayed finishing economics appear in HW6 Theory.',
        (
            section('9.1 & 9.6 · Two sources of postponement value',
                text('A common base item may be finished into different '
                     'designs after demand becomes known. Pooling makes '
                     'one base unit available to whichever design needs it. '
                     'The same arrangement can also delay finishing cost.'),
                text('Value of flexibility (pooling) and delayed financial '
                     'commitment are different economic mechanisms; both '
                     'may affect expected profit in this problem.'),
            ),
            section('7.2 & 9.9 · Original separate finished inventories',
                text('Without postponement, each finished design i is '
                     'its own Newsvendor. Compute its charges, critical '
                     'ratio and order independently.'),
                math(r'c_{u,i}^{orig}=p_i-v_i+B_i\quad;\quad c_{o,i}^{orig}=v_i-g_i'),
                math(r'\alpha_i^{orig}=\frac{c_{u,i}^{orig}}{c_{u,i}^{orig}+c_{o,i}^{orig}}'),
                math(r'Q_i^{orig}=\mu_i+\sigma_i\Phi^{-1}(\alpha_i^{orig})'),
                math(r'E[\Pi_{orig}]=\sum_i[(p_i-v_i)\mu_i-c_{u,i}^{orig}U_i(Q_i)-c_{o,i}^{orig}O_i(Q_i)]'),
                text('Check neighboring integer quantities with the '
                     'same general expected-profit function.'),
            ),
            section('3.7 & 9.6 · Aggregate demand and risk pooling',
                text('Expected demands add. Variances add only after '
                     'accounting for covariances; independent Normal '
                     'demands give a Normal total with variance equal '
                     'to the sum of individual variances.'),
                math(r'X_\Sigma=\sum_iX_i\quad;\quad\mu_\Sigma=\sum_i\mu_i'),
                math(r'\sigma_\Sigma^2=\sum_i\sigma_i^2+2\sum_{i<j}\operatorname{Cov}(X_i,X_j)'),
                math(r'X_i\ \mathrm{independent\ Normal}\quad\Rightarrow\quad X_\Sigma\sim N\left(\sum_i\mu_i,\sum_i\sigma_i^2\right)'),
                math(r'\sigma_\Sigma=\sqrt{\sum_i\sigma_i^2}\quad(\mathrm{independent})'),
                text('For a common positive safety factor z, the pooled '
                     'quantity is not larger than the sum of the '
                     'separate quantities in the equal-service comparison.'),
                math(r'\sum_i\mu_i+z\sqrt{\sum_i\sigma_i^2}\leq\sum_i(\mu_i+z\sigma_i)\quad(z\geq0)'),
            ),
            section('9.7 · Exact pooling when underage charges are equal',
                text('If every design has the same underage cost, '
                     'the identity of the unsatisfied design does '
                     'not affect the aggregate shortage penalty.'),
                math(r'c_{u,i}=p_i-v_0-t_i+B_i=c_u'),
                math(r'c_o=v_0-g_0'),
                math(r'E[\Pi_{post}(Q_0)]=\sum_i(p_i-v_0-t_i)\mu_i-c_uU_\Sigma(Q_0)-c_oO_\Sigma(Q_0)'),
                math(r'Q_0^*=F_\Sigma^{-1}\left(\frac{c_u}{c_u+c_o}\right)'),
                text('This reduction requires immediate flexible '
                     'finishing without another binding capacity '
                     'or lead-time restriction.'),
            ),
            section('9.8 · Unequal underage charges with FCFS',
                text('When different designs have different shortage '
                     'charges, the exact expected loss depends on '
                     'which design is unfulfilled. Under first-come-first-served '
                     '(FCFS) service with no prioritization, the manual '
                     'uses a demand-weighted underage approximation.'),
                math(r'c_{u,i}=p_i-v_0-t_i+B_i\quad;\quad c_o=v_0-g_0'),
                math(r'E[\Pi_{post}(Q_0)]=\sum_i(p_i-v_0-t_i)\mu_i-c_oO_\Sigma(Q_0)-\sum_i c_{u,i}ES_i(Q_0)'),
                math(r'\bar c_u=\frac{\sum_i\mu_i c_{u,i}}{\sum_i\mu_i}'),
                math(r'\sum_i c_{u,i}ES_i(Q_0)\approx\bar c_u U_\Sigma(Q_0)'),
                math(r'\alpha_{FCFS}=\frac{\bar c_u}{\bar c_u+c_o}'),
                math(r'Q_{0,FCFS}\approx\mu_\Sigma+\sigma_\Sigma\Phi^{-1}(\alpha_{FCFS})'),
                text('The demand-weighted replacement is an approximation, '
                     'not an exact identity for every customer-arrival '
                     'process. The actual homework forbids design prioritization.'),
            ),
            section('9.9 · Pooled expected profit and whole-unit comparison',
                text('The profit baseline with a common base deducts '
                     'base cost v₀ and finishing t_i once per expected '
                     'unit sold. Calculate pooled overage and shortage '
                     'using the aggregate Normal distribution.'),
                math(r'E[\Pi_{post}(Q_0)]\approx\sum_i(p_i-v_0-t_i)\mu_i-c_oO_\Sigma(Q_0)-\bar c_u U_\Sigma(Q_0)'),
                math(r'U_\Sigma(Q_0)=\sigma_\Sigma G_u\left(\frac{Q_0-\mu_\Sigma}{\sigma_\Sigma}\right)'),
                math(r'O_\Sigma(Q_0)=U_\Sigma(Q_0)+Q_0-\mu_\Sigma'),
                math(r'\Delta\Pi\approx E[\Pi_{post}(Q_0)]-\sum_iE[\Pi_{orig,i}(Q_i)]'),
                text('Compare neighboring integer base quantities '
                     'under the same FCFS approximation. A gain can '
                     'reflect both pooling and differences in '
                     'acquisition/finishing costs.'),
            ),
            section('9.10 · Priority allocation: contrasting model, not HW5',
                text('If all item demands are known before allocation '
                     'and prioritization is allowed, the problem is '
                     'different from the FCFS rule of this homework. '
                     'The manual also states a priority approximation '
                     'and an exact two-item condition.'),
                math(r'c_{u,min}=\min_i c_{u,i}'),
                math(r'Q_{0,priority}^{approx}=F_\Sigma^{-1}\left(\frac{c_{u,min}}{c_{u,min}+c_o}\right)'),
                math(r'(c_o+c_{u,2})F_\Sigma(Q_0^*)+(c_{u,1}-c_{u,2})F_1(Q_0^*)=c_{u,1}'),
                text('The exact two-item equation assumes item 1 has '
                     'the higher underage cost and is served first. '
                     'Do not substitute either priority expression '
                     'into the FCFS homework.'),
            ),
        ),
    ),
}
