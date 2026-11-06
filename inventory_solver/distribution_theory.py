"""Reusable Part III formulas for the selectable demand distributions.

The manual provides each derivation once. These sections are shared between
HW4, HW6 and the Normal/Poisson pooling mode of HW5.
"""
from __future__ import annotations

DISTRIBUTION_THEORY: tuple[tuple[str, tuple[str, ...]], ...] = (
    ('3.1 · Normal', (
        r'X\sim N(\mu,\sigma^2),\quad z=\frac{q-\mu}{\sigma}',
        r'F_X(q)=\Phi(z),\quad q_\alpha=\mu+\sigma\Phi^{-1}(\alpha)',
        r'U(q)=\sigma[\phi(z)-z(1-\Phi(z))]',
        r'O(q)=U(q)+q-\mu',
    )),
    ('3.2 · Uniform', (
        r'X\sim\operatorname{Unif}(a,b),\quad \mu=\frac{a+b}{2}',
        r'F_X(q)=\frac{q-a}{b-a}\ (a\le q\le b)',
        r'q_\alpha=a+(b-a)\alpha',
        r'U(q)=\frac{(b-q)^2}{2(b-a)}\ (a\le q\le b)',
        r'U(q)=\mu-q\ (q<a),\quad U(q)=0\ (q>b)',
    )),
    ('3.3 · Exponential', (
        r'X\sim\operatorname{Exp}(\lambda),\quad \mu=\frac1\lambda',
        r'F_X(q)=1-e^{-\lambda q}\ (q\ge0)',
        r'q_\alpha=-\frac{\ln(1-\alpha)}\lambda',
        r'U(q)=\frac{e^{-\lambda q}}{\lambda}\ (q\ge0)',
    )),
    ('3.4 · Geometric (support starts at 0)', (
        r'P(X=x)=(1-\rho)\rho^x,\quad x=0,1,2,\dots',
        r'F_X(q)=1-\rho^{q+1}\quad (q\in\mathbb{Z}_{\ge0})',
        r'q_\alpha=\max\!\left\{0,\left\lceil\frac{\ln(1-\alpha)}{\ln\rho}-1\right\rceil\right\}',
        r'U(q)=\frac{\rho^{q+1}}{1-\rho}\quad (q\in\mathbb{Z}_{\ge0})',
    )),
    ('3.5 · Poisson', (
        r'X\sim\operatorname{Pois}(\lambda),\quad E[X]=\operatorname{Var}(X)=\lambda',
        r'F_X(q)=e^{-\lambda}\sum_{j=0}^{q}\frac{\lambda^j}{j!}',
        r'q_\alpha=\min\{q\in\mathbb{Z}_{\ge0}:F_X(q)\ge\alpha\}',
        r'U(q)=\lambda[1-F_X(q-1)]-q[1-F_X(q)]',
    )),
    ('3.6 · Arbitrary discrete demand', (
        r'P(X=x_j)=p_j,\quad \sum_j p_j=1',
        r'F_j=\sum_{r\le j}p_r,\quad q_\alpha=x_{\min\{j:F_j\ge\alpha\}}',
        r'U(q)=\sum_{x_j>q}(x_j-q)p_j',
        r'O(q)=U(q)+q-\mu',
    )),
    ('1.7 / 7.3 · Critical fractile and expected profit', (
        r'c_u=p-v+B,\quad c_o=v-g,\quad\alpha=\frac{c_u}{c_u+c_o}',
        r'q^*=F_X^{-1}(\alpha)\ \mathrm{(generalized\ quantile)}',
        r'E[\Pi(q)]=(p-v)\mu-c_u U(q)-c_o O(q)',
    )),
    ('3.7 / 9.6 · Independent demand aggregation', (
        r'\mu_\Sigma=\sum_i\mu_i',
        r'\sigma_\Sigma^2=\sum_i\sigma_i^2\quad\mathrm{(independent)}',
        r'\sum_i\operatorname{Pois}(\lambda_i)\sim\operatorname{Pois}\!\left(\sum_i\lambda_i\right)',
    )),
)
