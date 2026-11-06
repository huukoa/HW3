"""Non-Normal demand extensions of manual Parts VII-IX.

Normal homework paths remain unchanged. These adapters use manual Part III's
CDF, generalized quantile, and shortage definitions without assuming a
Normal safety-factor/revised-power formula for other distributions.
"""
from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp

from inventory_solver.common import ensure, latex_num as f, number
from inventory_solver.distributions import DemandDistribution, from_inputs
from inventory_solver.schema import Metric, ModelInputError, Solution, Step


@dataclass(frozen=True)
class DemandItem:
    name: str
    p: float
    v: float
    g: float
    b: float
    demand: DemandDistribution

    @property
    def cu(self) -> float:
        return self.p-self.v+self.b

    @property
    def co(self) -> float:
        return self.v-self.g

    def quantity(self, m: float = 0) -> float:
        alpha=(self.cu-m*self.v)/(self.cu+self.co)
        if alpha <= self.demand.cdf(0):
            return 0.0
        return self.demand.quantile(alpha)

    def profit(self, q: float) -> float:
        u,o=self.demand.loss(q)
        return (self.p-self.v)*self.demand.mean-self.cu*u-self.co*o


def _items(raw: Mapping[str, object]) -> list[DemandItem]:
    rows=raw.get('items')
    ensure(isinstance(rows,list) and 2<=len(rows)<=20,'Provide between 2 and 20 products.')
    items=[]
    for i, row in enumerate(rows,1):
        ensure(isinstance(row,dict),f'Item {i}: expected a row.')
        name=str(row.get('name',f'Item {i}')).strip()[:75] or f'Item {i}'
        p=number(row,'p',positive=True);v=number(row,'v',positive=True)
        g=number(row,'g',nonnegative=True);b=number(row,'B',nonnegative=True)
        item=DemandItem(name,p,v,g,b,from_inputs(row))
        ensure(item.cu>0 and item.co>0,
               f'{name}: requires p-v+B > 0 and v-g > 0 for the standard critical-ratio model.')
        items.append(item)
    return items


def _integer_budget(items: list[DemandItem], budget: float) -> tuple[list[int],str]:
    """Exact integer marginal-unit knapsack, with size cap for public hosting."""
    costs=[];profits=[];caps=[]
    for item in items:
        cap=min(math.floor((budget+1e-8)/item.v),
                math.ceil(item.quantity())+2)
        cap=max(0,cap)
        caps.append(cap)
        if sum(caps)>12_000:
            raise ModelInputError('Integer optimization >12,000 candidate units; reduce budget or products.')
        js=np.arange(1,cap+1,dtype=float)
        profits.append(item.demand.marginal_unit_profit(js,item.cu,item.co))
        costs.append(np.full(cap,item.v,dtype=float))
    if not any(caps):
        return [0]*len(items),'Global integer optimum (empty feasible purchase)'
    gain=np.concatenate(profits)
    price=np.concatenate(costs)
    answer=milp(c=-gain, integrality=np.ones(len(gain)),
                bounds=Bounds(np.zeros(len(gain)),np.ones(len(gain))),
                constraints=LinearConstraint(price.reshape(1,-1),-np.inf,budget),
                options={'time_limit':25.0,'mip_rel_gap':1e-9})
    if answer.x is None:
        raise ModelInputError(f'Integer optimizer failed: {answer.message}')
    quantities=[];offset=0
    for cap in caps:
        quantities.append(int(np.count_nonzero(answer.x[offset:offset+cap]>=0.5)))
        offset+=cap
    spent=sum(x.v*q for x,q in zip(items,quantities))
    ensure(spent<=budget+1e-6,'Integer optimizer exceeded budget.')
    status=('Global integer optimum (MILP certified)' if answer.status==0
            else 'Feasible integer incumbent (not certified)')
    return quantities,status


def hw4_general(raw: Mapping[str,object]) -> Solution:
    budget=number(raw,'W',nonnegative=True)
    items=_items(raw)
    unlimited=[item.quantity() for item in items]
    unconstrained_spend=sum(item.v*q for item,q in zip(items,unlimited))
    logs=[]
    if unconstrained_spend<=budget:
        multiplier=0.0;qstar=unlimited;bracket=None
    elif budget==0:
        multiplier=0.0;qstar=[0.0]*len(items);bracket=None
    else:
        def residual(m:float)->float:
            return sum(x.v*x.quantity(m) for x in items)-budget
        lo,hi=0.0,1.0
        while residual(hi)>0:
            hi*=2
            ensure(hi<=1e12,'Unable to bracket the budget multiplier.')
        for j in range(80):
            mid=(lo+hi)/2
            res=residual(mid)
            logs.append((j+1,mid,res))
            if res>0:lo=mid
            else:hi=mid
            if hi-lo <= 2e-12*max(1,mid):break
        multiplier=(lo+hi)/2
        qstar=[x.quantity(multiplier) for x in items]
        bracket=(lo,hi)
    integers,quality=_integer_budget(items,budget)
    spent=sum(x.v*q for x,q in zip(items,integers))
    profit=sum(x.profit(float(q)) for x,q in zip(items,integers))
    out=Solution('HW4','Multi-item Newsvendor · Multiple Distributions')
    out.data={'M':multiplier,'continuous_q':qstar,'integer_q':integers,
              'spend':spent,'budget':budget,'profit':profit,'integer_quality':quality,
              'continuous_spend':sum(x.v*q for x,q in zip(items,qstar)),
              'unconstrained_spend':unconstrained_spend,'bisections':len(logs),
              'bracket':bracket,'distributions':[x.demand.name for x in items]}
    out.metrics=[Metric('Budget',budget,'$'),Metric('Integer purchase',spent,'$'),
                 Metric('Expected profit',profit,'$'),Metric('Multiplier reference M',multiplier)]
    equations=[]
    for i,item in enumerate(items,1):
        alpha=item.cu/(item.cu+item.co)
        equations.extend((
            rf'c_{{u,{i}}}=p_{i}-v_{i}+B_{i}={f(item.p)}-{f(item.v)}+{f(item.b)}={f(item.cu)}',
            rf'c_{{o,{i}}}=v_{i}-g_{i}={f(item.v)}-{f(item.g)}={f(item.co)}',
            rf'\alpha_{{{i}}}=\frac{{c_{{u,{i}}}}}{{c_{{u,{i}}}+c_{{o,{i}}}}}={f(alpha,6)}',
            item.demand.caption(),
        ))
    out.steps=[Step('1 · Demand distributions and unit economics',tuple(equations),open_by_default=True)]
    expressions=[]
    for i,(item,q) in enumerate(zip(items,unlimited),1):
        a=item.cu/(item.cu+item.co)
        expressions.append(rf'Q_{{u,{i}}}=F_{{{i}}}^{{-1}}(\alpha_{{{i}}})=F_{{{i}}}^{{-1}}({f(a,6)})={f(q)}')
    expressions.append(rf'W_u=\sum_i v_iQ_{{u,i}}='+'+'.join(rf'{f(x.v)}({f(q)})' for x,q in zip(items,unlimited)) +f'={f(unconstrained_spend)}')
    out.steps.append(Step('2 · Unconstrained orders and budget',tuple(expressions),
                          'Budget is binding.' if unconstrained_spend>budget else 'Budget is not binding.'))
    if logs:
        iteration_equations=[]
        for j,m,res in logs[:2]:
            quantities=[item.quantity(m) for item in items]
            iteration_equations.append(rf'M_{{{j}}}=\frac{{M_L+M_U}}{{2}}={f(m,8)}')
            for i,(item,q) in enumerate(zip(items,quantities),1):
                a=(item.cu-m*item.v)/(item.cu+item.co)
                formula=(rf'Q_{{{i}}}(M_{{{j}}})=F_{{{i}}}^{{-1}}'
                         rf'\!\left(\frac{{c_{{u,{i}}}-M_{{{j}}}v_{i}}}{{c_{{u,{i}}}+c_{{o,{i}}}}}\right)')
                iteration_equations.append(formula+rf'=F_{{{i}}}^{{-1}}({f(a,6)})={f(q)}'
                                           if a>item.demand.cdf(0) else rf'Q_{{{i}}}(M_{{{j}}})=0')
            iteration_equations.append(
                rf'G(M_{{{j}}})=\sum_i v_iQ_i(M_{{{j}}})-W={f(res)}')
        out.steps.append(Step('3 · Multiplier bracket / first two evaluations',tuple(iteration_equations),
                              'Positive residual raises the lower bound; otherwise lower the upper bound.'))
        out.rows=[{'j':j,'M':f(m,9),'G(M)':f(res)} for j,m,res in logs]
        out.columns=[{'name':k,'label':k,'field':k} for k in ('j','M','G(M)')]
    else:
        rule=(rf'W=0\Rightarrow Q_i=0' if budget==0 else rf'W_u\le W\Rightarrow M=0')
        out.steps.append(Step('3 · Multiplier branch', (rule,)))
    order_equations=[]
    for i,(item,q,ki) in enumerate(zip(items,qstar,integers),1):
        u,o=item.demand.loss(ki)
        order_equations.extend((
            rf'Q_{{{i},ref}}=F_{{{i}}}^{{-1}}(\alpha_i(M))={f(q)}',
            rf'Q_{{{i},integer}}={ki}',
            rf'U_{{{i}}}({ki})=E[(X_{i}-{ki})^+]={f(u)}',
            rf'O_{{{i}}}({ki})=U_{{{i}}}({ki})+{ki}-{f(item.demand.mean)}={f(o)}',
            rf'E[\Pi_{i}]=(p_{i}-v_{i})\mu_i-c_{{u,{i}}}U_i-c_{{o,{i}}}O_i'
            rf'={f(item.p-item.v)}({f(item.demand.mean)})-{f(item.cu)}({f(u)})-{f(item.co)}({f(o)})={f(item.profit(ki))}',
        ))
    out.steps.extend((
        Step('4 · Whole-unit decisions and expected profit',tuple(order_equations),
             'Choose integer orders maximizing total expected profit subject to the budget.'),
        Step('5 · Verify budget and total expected profit',(
            rf'W_{{used}}=\sum_i v_iQ_{{i,integer}}='+'+'.join(rf'{f(x.v)}({q})' for x,q in zip(items,integers))+f'={f(spent)}',
            rf'W_{{used}}\le W\Rightarrow {f(spent)}\le {f(budget)}',
            rf'E[\Pi_{{total}}]=\sum_i E[\Pi_i]='+'+'.join(f(x.profit(q)) for x,q in zip(items,integers))+f'={f(profit)}',
        ),quality),
    ))
    out.comparisons=[{'Item':x.name,'Distribution':x.demand.name,'Reference Q':f(q),
                      'Integer Q':qi,'Spend $':f(x.v*qi),'Expected profit $':f(x.profit(qi))}
                     for x,q,qi in zip(items,qstar,integers)]
    return out


def _profit(base:float, q:float, dist:DemandDistribution, cu:float, co:float)->float:
    u,o=dist.loss(q)
    return base*dist.mean-cu*u-co*o


def hw6_general(raw:Mapping[str,object])->Solution:
    dist=from_inputs(raw)
    d={key:number(raw,key,positive=key in ('p','v','v0'),nonnegative=key in ('g','g0','B','t'))
       for key in ('p','v','g','B','v0','t','g0')}
    cu=d['p']-d['v']+d['B'];co=d['v']-d['g']
    cu0=d['p']-d['v0']-d['t']+d['B'];co0=d['v0']-d['g0']
    ensure(min(cu,co,cu0,co0)>0,'Both policies require positive underage and overage costs.')
    alpha=cu/(cu+co);alpha0=cu0/(cu0+co0)
    qo=dist.quantile(alpha);qp=dist.quantile(alpha0)
    io=dist.integer_quantity(cu,co);ip=dist.integer_quantity(cu0,co0)
    orig=_profit(d['p']-d['v'],float(io),dist,cu,co)
    post=_profit(d['p']-d['v0']-d['t'],float(ip),dist,cu0,co0)
    orig_cont=_profit(d['p']-d['v'],qo,dist,cu,co)
    post_cont=_profit(d['p']-d['v0']-d['t'],qp,dist,cu0,co0)
    out=Solution('HW6','Postponement · Delayed Financial Commitment')
    out.data={'Q_original':qo,'Q_post':qp,'Q_original_int':io,'Q_post_int':ip,
              'profit_original_int':orig,'profit_post_int':post,'profit_original_cont':orig_cont,
              'profit_post_cont':post_cont,'gain_int':post-orig,'gain_cont':post_cont-orig_cont,
              'distribution':dist.name}
    out.metrics=[Metric('Original order',io,'finished sets'),Metric('Postponed order',ip,'unfinished sets'),
                 Metric('Original expected profit',orig,'$'),Metric('Postponed expected profit',post,'$'),
                 Metric('Profit improvement',post-orig,'$')]
    steps=[Step('1 · Demand and original economics',(
        dist.caption(),
        rf'\mu=E[X]={f(dist.mean)}',
        rf'c_u=p-v+B={f(d["p"])}-{f(d["v"])}+{f(d["B"])}={f(cu)}',
        rf'c_o=v-g={f(d["v"])}-{f(d["g"])}={f(co)}',
        rf'\alpha_{{orig}}=\frac{{c_u}}{{c_u+c_o}}=\frac{{{f(cu)}}}{{{f(cu+co)}}}={f(alpha,6)}',
    ),open_by_default=True)]
    for label,q,qi,cur,cor,base,al in (
        ('Original',qo,io,cu,co,d['p']-d['v'],alpha),
        ('Postponed',qp,ip,cu0,co0,d['p']-d['v0']-d['t'],alpha0),
    ):
        u,o=dist.loss(qi)
        equations=[
            rf'Q^*_{{{label.lower()}}}=F^{{-1}}(\alpha_{{{label.lower()}}})=F^{{-1}}({f(al,6)})={f(q)}',
        ]
        for n in sorted({max(0,math.floor(q)),max(0,math.floor(q))+1}):
            un,on=dist.loss(n)
            equations.append(rf'E[\Pi_{{{label.lower()}}}({n})]={f(base)}({f(dist.mean)})'
                             rf'-{f(cur)}({f(un)})-{f(cor)}({f(on)})={f(_profit(base,n,dist,cur,cor))}')
        equations.extend((
            rf'Q_{{{label.lower()},integer}}={qi}',
            rf'U({qi})=E[(X-{qi})^+]={f(u)}',
            rf'O({qi})=U({qi})+{qi}-{f(dist.mean)}={f(o)}',
            rf'E[\Pi_{{{label.lower()}}}]={f(base)}({f(dist.mean)})-{f(cur)}({f(u)})-{f(cor)}({f(o)})'
            rf'={f(_profit(base,qi,dist,cur,cor))}',
        ))
        if label=='Postponed':
            steps.append(Step('3 · Postponed unit economics',(
                rf'c_{{u,post}}=p-v_0-t+B={f(d["p"])}-{f(d["v0"])}-{f(d["t"])}+{f(d["B"])}={f(cu0)}',
                rf'c_{{o,post}}=v_0-g_0={f(d["v0"])}-{f(d["g0"])}={f(co0)}',
                rf'\alpha_{{post}}=\frac{{{f(cu0)}}}{{{f(cu0+co0)}}}={f(alpha0,6)}',
            )))
        steps.append(Step(('2' if label=='Original' else '4')+f' · {label} order and profit',tuple(equations)))
    steps.append(Step('5 · Compare expected profit',(
        rf'\Delta E[\Pi]=E[\Pi_{{post}}]-E[\Pi_{{orig}}]={f(post)}-{f(orig)}={f(post-orig)}',
    ),'Postponement yields higher expected profit.' if post>orig else 'Original stocking yields higher expected profit.' if post<orig else 'Equal expected profit.'))
    out.steps=steps
    out.comparisons=[{'Policy':'Original','Continuous Q':f(qo),'Integer Q':io,'Expected profit $':f(orig)},
                     {'Policy':'Postponed','Continuous Q':f(qp),'Integer Q':ip,'Expected profit $':f(post)}]
    return out


def hw5_poisson(raw:Mapping[str,object])->Solution:
    v0=number(raw,'v0',positive=True);g0=number(raw,'g0',nonnegative=True)
    co0=v0-g0
    ensure(co0>0,'Base cost must exceed base salvage value.')
    items=_items(raw)
    ensure(all(item.demand.name=='Poisson' for item in items),
           'HW5 pooling supports independent Normal (all items) or Poisson (all items).')
    rows=raw.get('items')
    assert isinstance(rows,list)
    finishing=[number(row,'t',nonnegative=True) for row in rows]
    mean=sum(x.demand.mean for x in items)
    pooled=from_inputs({'distribution':'Poisson','lam':mean})
    post_cu=[x.p-v0-t+x.b for x,t in zip(items,finishing)]
    ensure(min(post_cu)>0,'Each postponed underage cost must be > 0.')
    avg_cu=sum(x.demand.mean*cu for x,cu in zip(items,post_cu))/mean
    qo=[x.quantity() for x in items]
    qi=[x.demand.integer_quantity(x.cu,x.co) for x in items]
    qpost=pooled.quantile(avg_cu/(avg_cu+co0))
    ipost=pooled.integer_quantity(avg_cu,co0)
    orig_profit=sum(x.profit(q) for x,q in zip(items,qi))
    baseline=sum((x.p-v0-t)*x.demand.mean for x,t in zip(items,finishing))
    u,o=pooled.loss(ipost)
    post_profit=baseline-avg_cu*u-co0*o
    out=Solution('HW5','Postponement · Poisson FCFS Pooling')
    out.data={'Q_original_cont':qo,'Q_original_int':qi,'Q_post_cont':qpost,'Q_post_int':ipost,
              'profit_original':orig_profit,'profit_post_approx':post_profit,
              'gain_approx':post_profit-orig_profit,'cu_weighted':avg_cu,
              'mu_pooled':mean,'sigma_pooled':math.sqrt(mean),'distribution':'Poisson'}
    out.metrics=[Metric('Original total',sum(qi),'finished units'),
                 Metric('Pooled common base',ipost,'unfinished units'),
                 Metric('Original expected profit',orig_profit,'$'),
                 Metric('Postponed expected profit (approx.)',post_profit,'$'),
                 Metric('Estimated improvement',post_profit-orig_profit,'$')]
    economics=[];orders=[]
    for i,(item,q,qint) in enumerate(zip(items,qo,qi),1):
        alpha=item.cu/(item.cu+item.co)
        economics.extend((
            rf'X_{i}\sim\operatorname{{Pois}}({f(item.demand.mean)})',
            rf'c_{{u,{i}}}=p_{i}-v_{i}+B_{i}={f(item.p)}-{f(item.v)}+{f(item.b)}={f(item.cu)}',
            rf'c_{{o,{i}}}=v_{i}-g_{i}={f(item.v)}-{f(item.g)}={f(item.co)}',
        ))
        uu,oo=item.demand.loss(qint)
        orders.extend((
            rf'\alpha_{i}=\frac{{c_{{u,{i}}}}}{{c_{{u,{i}}}+c_{{o,{i}}}}}={f(alpha,6)}',
            rf'Q_{{{i}}}=\min\{{q\in\mathbb{{Z}}_{{\ge0}}:F_i(q)\ge{f(alpha,6)}\}}={qint}',
            rf'U_i({qint})=\lambda_i[1-F_i({qint-1})]-{qint}[1-F_i({qint})]={f(uu)}',
            rf'O_i({qint})=U_i({qint})+{qint}-{f(item.demand.mean)}={f(oo)}',
            rf'E[\Pi_i]={f(item.p-item.v)}({f(item.demand.mean)})-{f(item.cu)}({f(uu)})-{f(item.co)}({f(oo)})={f(item.profit(qint))}',
        ))
    out.steps=[
        Step('1 · Original cost and Poisson demand',tuple(economics),open_by_default=True),
        Step('2 · Original orders and expected profit',tuple(orders)+(
            rf'E[\Pi_{{orig}}]=\sum_i E[\Pi_i]='+'+'.join(f(x.profit(q)) for x,q in zip(items,qi))+f'={f(orig_profit)}',)),
        Step('3 · Pool independent Poisson demand',(
            rf'\lambda_\Sigma=\sum_i\lambda_i='+'+'.join(f(x.demand.mean) for x in items)+f'={f(mean)}',
            rf'X_\Sigma\sim\operatorname{{Pois}}({f(mean)})',
        )),
    ]
    weighted_terms='+'.join(rf'{f(item.demand.mean)}({f(c)})' for item,c in zip(items,post_cu))
    out.steps.append(Step('4 · FCFS underage cost and order',tuple(
        rf'c_{{u,{i},post}}=p_i-v_0-t_i+B_i={f(x.p)}-{f(v0)}-{f(t)}+{f(x.b)}={f(c)}'
        for i,(x,t,c) in enumerate(zip(items,finishing,post_cu),1))+(
        rf'\bar c_u=\frac{{\sum_i\mu_i c_{{u,i}}}}{{\sum_i\mu_i}}=\frac{{{weighted_terms}}}{{{f(mean)}}}={f(avg_cu)}',
        rf'c_o=v_0-g_0={f(v0)}-{f(g0)}={f(co0)}',
        rf'\alpha_{{FCFS}}=\frac{{\bar c_u}}{{\bar c_u+c_o}}={f(avg_cu/(avg_cu+co0),6)}',
        rf'Q^*_0=F_\Sigma^{{-1}}(\alpha_{{FCFS}})={f(qpost)}',
        rf'Q_{{0,integer}}={ipost}',
    )))
    out.steps.append(Step('5 · Profit comparison',(
        rf'U_\Sigma({ipost})={f(u)}',
        rf'O_\Sigma({ipost})=U_\Sigma+{ipost}-{f(mean)}={f(o)}',
        rf'E[\Pi_{{post}}]\approx {f(baseline)}-{f(avg_cu)}({f(u)})-{f(co0)}({f(o)})={f(post_profit)}',
        rf'\Delta E[\Pi]\approx E[\Pi_{{post}}]-E[\Pi_{{orig}}]={f(post_profit)}-{f(orig_profit)}={f(post_profit-orig_profit)}',
    )))
    out.comparisons=[{'Policy':'Original','Quantities':', '.join(map(str,qi)),'Expected profit $':f(orig_profit)},
                     {'Policy':'Postponed (FCFS approx.)','Quantities':str(ipost),'Expected profit $':f(post_profit)}]
    return out
