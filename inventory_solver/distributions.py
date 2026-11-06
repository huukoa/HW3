"""Demand distributions from Complete Manual Part III (3.1-3.6).

A single interface supplies the CDF/critical quantile and expected shortages
used by the general Newsvendor and postponement models. In contrast, the
continuous-review and revised-power homework algorithms are Normal-specific.
"""
from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np
from scipy.stats import norm, poisson

from inventory_solver.common import ensure, number
from inventory_solver.numeric_input import parse_numeric
from inventory_solver.schema import ModelInputError

DISTRIBUTIONS = ('Normal', 'Uniform', 'Exponential', 'Geometric', 'Poisson', 'Discrete')
INTEGER_DISTRIBUTIONS = frozenset({'Geometric', 'Poisson', 'Discrete'})
PARAMETERS = {
    'Normal': (('mu', 'Mean demand μ'), ('sigma', 'Standard deviation σ')),
    'Uniform': (('a', 'Lower bound a'), ('b', 'Upper bound b')),
    'Exponential': (('rate', 'Rate λ (1/mean)'),),
    'Geometric': (('rho', 'Parameter ρ (support 0,1,2,…)'),),
    'Poisson': (('lam', 'Mean / rate λ'),),
    'Discrete': (('support', 'Support (e.g. 0,1,3)'),
                 ('probabilities', 'Probabilities (e.g. 0.2,0.5,0.3)')),
}


def _csv_values(value: object, field: str) -> tuple[float, ...]:
    if not isinstance(value, str) or not value.strip():
        raise ModelInputError(f'{field}: enter comma-separated values.')
    values = [x.strip() for x in value.split(',')]
    if not 1 <= len(values) <= 100 or any(not x for x in values):
        raise ModelInputError(f'{field}: enter 1–100 comma-separated values.')
    return tuple(parse_numeric(v, field=field) for v in values)


@dataclass(frozen=True)
class DemandDistribution:
    name: str
    mean: float
    variance: float
    parameters: tuple[float, ...]
    support: tuple[int, ...] = ()
    probabilities: tuple[float, ...] = ()

    def __post_init__(self) -> None:
        ensure(math.isfinite(self.mean) and math.isfinite(self.variance),
               f'{self.name}: demand moments exceed supported numeric range.')
        ensure(self.variance >= 0, f'{self.name}: demand variance must be nonnegative.')

    @property
    def is_discrete(self) -> bool:
        return self.name in INTEGER_DISTRIBUTIONS

    @property
    def sd(self) -> float:
        return math.sqrt(self.variance)

    def cdf(self, q: float) -> float:
        if self.name == 'Normal':
            return float(norm.cdf((q - self.mean) / self.sd))
        if self.name == 'Uniform':
            a, b = self.parameters
            return min(1.0, max(0.0, (q-a)/(b-a)))
        if self.name == 'Exponential':
            (rate,) = self.parameters
            return 0.0 if q < 0 else -math.expm1(-rate*q)
        if self.name == 'Geometric':
            (rho,) = self.parameters
            k = math.floor(q)
            return 0.0 if k < 0 else -math.expm1((k+1)*math.log(rho))
        if self.name == 'Poisson':
            (lam,) = self.parameters
            return float(poisson.cdf(math.floor(q), lam))
        return min(1.0, max(0.0, sum(p for x, p in zip(self.support, self.probabilities) if x <= q)))

    def quantile(self, alpha: float) -> float:
        ensure(0 < alpha < 1, 'Critical ratio must be between 0 and 1.')
        if self.name == 'Normal':
            result = self.mean + self.sd * float(norm.ppf(alpha))
        elif self.name == 'Uniform':
            a, b = self.parameters
            result = a + (b-a)*alpha
        elif self.name == 'Exponential':
            (rate,) = self.parameters
            result = -math.log1p(-alpha)/rate
        elif self.name == 'Geometric':
            (rho,) = self.parameters
            result = float(max(0, math.ceil(math.log1p(-alpha)/math.log(rho)-1)))
        elif self.name == 'Poisson':
            (lam,) = self.parameters
            result = float(poisson.ppf(alpha, lam))
        else:
            result = float(next(x for x in self.support if self.cdf(x) + 1e-12 >= alpha))
        if not math.isfinite(result):
            raise ModelInputError('Demand quantile is not finite for this critical ratio.')
        if self.is_discrete:
            result = float(int(result))
            # Preserve smallest generalized quantile near a discrete jump.
            while result > 0 and self.cdf(result-1) >= alpha - 1e-13:
                result -= 1
            while self.cdf(result) < alpha - 1e-13:
                result += 1
        return max(0.0, result)

    def shortage(self, q: float) -> float:
        """E[(X-q)+], with Manual (3.1), (3.3), (3.5), (3.7), (3.8), (3.10)."""
        if self.name == 'Normal':
            z = (q-self.mean)/self.sd
            return max(0.0, self.sd * (float(norm.pdf(z)) - z * float(norm.sf(z))))
        if self.name == 'Uniform':
            a, b = self.parameters
            if q < a:
                return self.mean-q
            if q <= b:
                return (b-q)**2/(2*(b-a))
            return 0.0
        if self.name == 'Exponential':
            (rate,) = self.parameters
            return self.mean-q if q < 0 else math.exp(-rate*q)/rate
        if self.name == 'Geometric':
            (rho,) = self.parameters
            k = math.floor(q)
            # The economic decisions are integer for Geometric; maintain valid
            # arbitrary q using linear interpolation between two integers.
            if q < 0:
                return self.mean-q
            first = rho**(k+1)/(1-rho)
            return max(0.0, first - (q-k)*(1-self.cdf(k)))
        if self.name == 'Poisson':
            (lam,) = self.parameters
            if q < 0:
                return self.mean-q
            k = math.floor(q)
            first = lam*float(poisson.sf(k-1,lam)) - k*float(poisson.sf(k,lam))
            return max(0.0, first - (q-k)*float(poisson.sf(k,lam)))
        return max(0.0, sum(p*max(x-q, 0.0) for x,p in zip(self.support,self.probabilities)))

    def loss(self, q: float) -> tuple[float, float]:
        u = self.shortage(q)
        return u, max(0.0, u+q-self.mean)

    def integer_quantity(self, cu: float, co: float) -> int:
        continuous = self.quantile(cu/(cu+co))
        if self.is_discrete:
            return int(continuous)
        a = max(0, math.floor(continuous))
        b = a+1
        def cost(q: int) -> float:
            u,o = self.loss(float(q))
            return cu*u+co*o
        return a if cost(a) <= cost(b) else b

    def marginal_unit_profit(self, j: np.ndarray, cu: float, co: float) -> np.ndarray:
        """Exact expected gain from increasing integer q from j-1 to j."""
        j = np.asarray(j, dtype=float)
        if self.is_discrete:
            return cu-(cu+co)*np.array([self.cdf(x-1) for x in j])
        if self.name == 'Normal':
            z1 = (j-1-self.mean)/self.sd
            z2 = (j-self.mean)/self.sd
            integral = self.sd*(z2*norm.cdf(z2)+norm.pdf(z2)-z1*norm.cdf(z1)-norm.pdf(z1))
        elif self.name == 'Uniform':
            a,b = self.parameters
            def primitive(x: np.ndarray) -> np.ndarray:
                return np.where(x <= a, 0, np.where(x >= b, x-(a+b)/2,
                                                     (x-a)**2/(2*(b-a))))
            integral = primitive(j)-primitive(j-1)
        else:
            (rate,) = self.parameters
            # For the nonnegative integer decision intervals j>=1.
            integral = 1-np.exp(-rate*(j-1))*(-np.expm1(-rate))/rate
        return cu-(cu+co)*np.asarray(integral)

    def caption(self) -> str:
        if self.name == 'Normal':
            return rf'X\sim N({self.mean:.6g},{self.variance:.6g})'
        if self.name == 'Uniform':
            a,b=self.parameters
            return rf'X\sim \operatorname{{Unif}}({a:.6g},{b:.6g})'
        if self.name == 'Exponential':
            return rf'X\sim\operatorname{{Exp}}(\lambda={self.parameters[0]:.6g})'
        if self.name == 'Geometric':
            return rf'P(X=x)=(1-\rho)\rho^x,\ \rho={self.parameters[0]:.6g}'
        if self.name == 'Poisson':
            return rf'X\sim\operatorname{{Pois}}({self.parameters[0]:.6g})'
        return r'P(X=x_j)=p_j\quad\mathrm{(table)}'


def from_inputs(raw: Mapping[str, object]) -> DemandDistribution:
    name = str(raw.get('distribution', 'Normal')).strip().title()
    ensure(name in DISTRIBUTIONS, f'Unknown demand distribution: {name}.')
    if name == 'Normal':
        mu = number(raw,'mu', nonnegative=True)
        sd = number(raw,'sigma',positive=True)
        return DemandDistribution(name,mu,sd*sd,(mu,sd))
    if name == 'Uniform':
        a = number(raw,'a',nonnegative=True)
        b = number(raw,'b',positive=True)
        ensure(a < b,'Uniform: upper bound b must exceed lower bound a.')
        return DemandDistribution(name,(a+b)/2,(b-a)**2/12,(a,b))
    if name == 'Exponential':
        rate = number(raw,'rate',positive=True)
        mean = 1/rate
        return DemandDistribution(name,mean,mean*mean,(rate,))
    if name == 'Geometric':
        rho = number(raw,'rho',positive=True)
        ensure(rho < 1,'Geometric: rho must be < 1.')
        return DemandDistribution(name,rho/(1-rho),rho/(1-rho)**2,(rho,))
    if name == 'Poisson':
        lam = number(raw,'lam',positive=True)
        return DemandDistribution(name,lam,lam,(lam,))
    support = _csv_values(raw.get('support'), 'support')
    probabilities = _csv_values(raw.get('probabilities'),'probabilities')
    ensure(len(support) == len(probabilities),'Discrete: support and probabilities must have the same length.')
    ensure(all(x >= 0 and float(x).is_integer() for x in support),
           'Discrete: support values must be nonnegative integers.')
    ensure(all(x >= 0 for x in probabilities),'Discrete: probabilities must be nonnegative.')
    ensure(len(set(support)) == len(support),'Discrete: support values must be unique.')
    ensure(math.isclose(sum(probabilities),1,rel_tol=0,abs_tol=1e-9),
           'Discrete: probabilities must sum to 1.')
    pairs = sorted(zip(support,probabilities))
    xs=tuple(int(x) for x,_ in pairs)
    ps=tuple(float(p) for _,p in pairs)
    mu=sum(x*p for x,p in zip(xs,ps))
    var=max(0.0,sum((x-mu)**2*p for x,p in zip(xs,ps)))
    return DemandDistribution(name,mu,var,(),xs,ps)


def defaults_for(name: str, raw: Mapping[str, object]) -> dict[str, object]:
    """Generate editable parameter defaults only when a user switches kind."""
    try:
        mu=float(parse_numeric(raw.get('mu',200),'mu'))
        sd=float(parse_numeric(raw.get('sigma',50),'sigma'))
    except (ValueError, TypeError):
        mu,sd=200.0,50.0
    mu=max(0.0,mu); sd=max(1.0,sd)
    if name=='Normal':
        return {'mu':mu,'sigma':sd}
    if name=='Uniform':
        return {'a':max(0.0,mu-math.sqrt(3)*sd), 'b':mu+math.sqrt(3)*sd}
    if name=='Exponential':
        return {'rate':1/max(1.0,mu)}
    if name=='Geometric':
        return {'rho':mu/(1+mu) if mu else 0.5}
    if name=='Poisson':
        return {'lam':max(1.0,mu)}
    return {'support':'0,1,3','probabilities':'0.2,0.5,0.3'}
