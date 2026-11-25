# 20 — Computational Economics (canonical model)

One economic model for all transformations — promotion, assimilation,
growth, and retention. Docs 09 and 11 reference this document as
canonical; their inline equations are shorthands, not rivals.

## 20.1 Simplified model: net savings with monitoring and fallback

Simplified special case — constant per-use costs, constant fallback
probability, fixed maintenance. Assumptions stated so the model can
be checked, not smuggled: stationary workload and unit costs over
the horizon; fallback events independent with constant probability;
maintenance time-invariant; single comparable cost unit (see §20.5
for units); no capacity constraints binding (hard constraints are
separate gates, never prices).

```text
S(N) = N·(Cref − Cnew − m − f·Cfallback) − B − M
```

Cref: actual routed or joint-parent execution cost (never an
auto-summed parent total); Cnew: candidate execution cost; m:
per-use monitoring cost; f: escalation probability; Cfallback: cost
per escalation; B: construction + validation cost; M: fixed
maintenance. Break-even N* = (B+M)/(Cref−Cnew−m−f·Cfallback),
all in the same units against the same reference workload. No
net-savings claim without an earned horizon. Failed candidates,
validation compute, and fallback invocations are costs, never
externalities. No-break-even case: when marginal savings
(Cref−Cnew−m−f·Cfallback) are ≤ 0, N* is undefined — the candidate
is rejected on efficiency economics outright, and may proceed only
under competence or expansion value (§20.4) with an explicit
subsidy justification.

## 20.2 Marginal utility and two-stage exploration funding

Construction value is measured against the current Pareto frontier, not a
weak fixed baseline. Separate two decisions within the existing B_explore:

1. Discovery probe: a capped grant to reduce a named uncertainty. Record
   hypothesis, discriminating observation, maximum spend, stopping rule, and
   possible nomination. Unknown expected value is the reason for probing,
   not an automatic rejection; no positive return is presumed.
2. Construction: fund a nomination when probe/demand evidence supports the
   expected competence, efficiency, or expansion value relative to cost.
   Record estimator, uncertainty, counterfactual, and subsidy where applicable.

B_explore has an explicit owner and resource-vector cap per epoch. A deployment
may reserve a baseline research allowance without operating surplus; otherwise
exploration is disabled when surplus is absent. Never borrow protected
capacity implicitly. Repeated inconclusive probes need a new discriminating
design or explicit renewed allocation; no automatic indefinite funding.

## 20.3 Retention economics

Preserving an old ability has carrying cost (storage, validation
currency, registry weight). Retention is a budgeted decision with
its own ledger: rare-critical floors are protected by policy, not by
economics; everything above the floor competes on measured
retention value vs carrying cost. Forgetting is permitted when it is
cheaper than remembering and no floor or contract requires the
ability — reported as a finding, never silent.

## 20.4 Three forms of developmental value

Cost reduction alone is insufficient — otherwise the system becomes
an excellent optimizer of existing intelligence that never develops
new intelligence. Every candidate is scored on all three; any may
justify construction, but the justification must name which:

- Efficiency value: doing existing things more cheaply (the S(N)
  equation above; N* required).
- Competence value: doing existing things better (quality gain per
  cost delta vs the Pareto frontier; no N* required, but the
  cost-per-quality Delta is reported).
- Expansion value: doing things the organization previously could
  not do (new capability coverage; justified by demand evidence per
  Doc 18, not by efficiency savings — expansion never owes a
  break-even N, though it may produce economic returns that are
  reported when they occur).

A candidate may carry any mix, but an efficiency-only gate would
reject every expansion. Track which value justified each acquisition
in lineage; review whether the portfolio is balanced or drifting
into pure optimization.

## 20.5 General model: time-varying costs and full accounting

```text
S(T) = Σ_{t=1}^{T} (Cref,t − Cactual,t) − B − M(T)
```

Cactual,t includes execution, monitoring, fallback, coordination,
and evaluation overhead at t; M(T) is time-varying maintenance
(grows with dependency load and validation currency decay — never
assumed fixed). §20.1 is this model under stationarity. Units:
heterogeneous resources (compute, memory, bandwidth, latency,
energy) convert to comparable units only through a declared
scalarization policy with weights, context, and sensitivity
recorded — no silent commensurability; hard resource constraints
(memory, deadlines, authority) remain separate gates that no
positive valuation overrides. Opportunity cost (best foregone use
of the budget), failed construction, coordination, recovery, and
evaluation overhead are line items, never externalities; each cost
is booked once against exactly one ledger (candidate, capability,
or organization) with the booking rule recorded — double-counting
across ledgers is a defect. Competence value under multidimensional
quality is reported as cost-per-quality-delta per dimension, never
collapsed to one number without the weights. Nomination expected
value (§20.2 cost-of-asking) is estimated from the demand record
(Doc 18: persistence, expense, uncertainty) with the estimator and
its uncertainty stated; unestimated construction value blocks construction funding; bounded discovery
probes remain available under section 20.2's separate allocation rule.

## 20.6 Incentives and shared-resource effects (research extension)

A provider's local reward, measured contribution (Doc 28), and the
organization's utility are distinct. Improving a local metric can consume
shared resources, impose downstream validation costs, or create unnecessary
demand. Book these effects once under section 20.5; no new parallel ledger
or scalar fitness definition is introduced.

Test local rewards, shared rewards, and admissible contribution-based
rewards separately, holding resource limits and external evaluation fixed.
Vary scarcity independently from reward design. [Sequential social dilemma
experiments](https://arxiv.org/abs/1702.03037) motivate this separation;
they do not show scarcity reliably causes useful innovation. [Collective
reward design](https://ntrs.nasa.gov/archive/nasa/casi.ntrs.nasa.gov/20010071848.pdf)
provides candidate incentive methods, not a guarantee of aligned behavior.
Generated work earns no expansion value without Doc 18 demand evidence.

## 20.7 Multi-step adaptation and enabling value

Evaluate a bounded plan against the same goal/workload and no-change/current
frontier, including every prefix's search, model-query, trial, construction,
validation, execution, archive and repair costs. Reserve real resources for the
next admitted step; predicted future savings are not spendable balances.
Prefix costs already spent remain costs if the rest fails.

An enabling step can receive a capped grant when it serves a named goal's
prerequisite with a declared path and intermediate contract. Unknown transition
effects instead justify a discriminating probe under section 20.2. Neither
requires immediate terminal reward; both require a budget owner, finite horizon,
stop/abandon conditions, floors and recovery disposition. Whole-plan forecasts
can justify a trial but cannot certify an acquisition or guarantee completion.

Report cumulative learning/model-maintenance cost and later adaptation cost
separately, then total them once. Compare resource vectors or use an explicitly
declared scalarization. Report budget-limited non-attainment, not just average
cost among successful runs. Future usefulness of an organization is relative
to a specified future demand distribution, not an unbounded option-value bonus.

## 20.8 Abstraction and repertoire economics

Use the existing single-ledger model for abstraction induction, matching,
validation, maintenance and execution, and archive descriptor measurement,
storage, retrieval, restoration and revalidation. Link charges to their actual
library/organization/candidate artifact without double-counting shared costs.
Cache hits, shorter syntax, macro counts and descriptor coverage are diagnostics;
justify retention through efficiency, competence or expansion value on declared
future workloads. A new abstraction can enlarge branching and slow unrelated
search, which counts against its value. Account expanded primitive work and
all inference iterations even when one macro/provider invocation hides them.
