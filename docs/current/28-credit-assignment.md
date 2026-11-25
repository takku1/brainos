# 28 — Organizational Credit Assignment

When five providers cooperate and the system improves 20%, which one
earned it? Wrong answers create wrong selection pressure and kill
useful components. Downstream evaluation and ablations (Docs 07, 17)
are necessary but not sufficient — this document makes attribution a
first-class mechanism.

## 28.1 Starting quantity (vector, not scalar)

```text
Δ_i(Σ,c) = U(Σ,c) − U(Σ\i,c)
```

where U is the organization utility VECTOR over the authoritative
state (per Doc 17 Pareto dimensions: capability, quality, cost,
latency, resilience), so Δ_i is a vector contribution indexed by
organizational state and context — not a graph-only quantity.
Removal notation Σ\i means the organization operating without
provider i under an explicitly declared admissible intervention
(§28.2 item 4). Scalar utility is permitted only
under an explicit, recorded scalarization policy (weights,
context, sensitivity) for the decision at hand — never as the
stored attribution. A point estimate without variance is not an
attribution. Three contribution categories are tracked separately:

- Execution contribution: present computational utility.
- Developmental contribution: historical or causal role in
  acquiring other capabilities.
- Resilience contribution: utility under failures, distribution
  shifts, and degraded operation.

## 28.2 Beyond removal

Simple removal misses synergy: two providers worthless apart,
decisive together. Required upgrades, in order of cost:

1. Leave-one-out (Δ_i above) — screening, not verdict.
2. Ablation pairs/triples on the cooperation subgraph — detects
   pairwise synergy, bounded cost.
3. Intervention-based evaluation: replay logged episodes with
   provider i's outputs replaced by baseline/ablated variants
   (counterfactual replay under the pinned manifest). Replay alone
   does not establish causality: it is valid only where the
   intervention cannot invalidate the recorded trajectory
   (stateless or short-horizon settings with stated assumptions
   on state, environment dynamics, confounding, and downstream
   reactions). In embodied or stateful settings — where a changed
   action rewrites subsequent observations — replay is
   inadmissible as proof and fresh controlled execution is
   required.
4. Coalition-aware attribution over an explicit value function
   and admissible coalition set: Shapley-style averaging over
   orderings within the responsible coalition only (sampled,
   error reported). Admissible ablations are defined up front:
   removal that invalidates the organization (infeasible
   coalition) is not a measurement — it is replaced by
   fallback-permitted ablation (ablate with the designated
   fallback active) or excluded with reason recorded.

## 28.3 Rules

Attribute before selecting: no retirement, assimilation, or budget
reallocation on cooperation gains until Δ-numbers (at least level 1,
escalating with the stakes) name the contributors. Interaction
effects are first-class findings: report synergy explicitly rather
than splitting it arbitrarily. Historical developmental credit
never justifies permanent retention by itself — retention needs
current or protected-floor justification (Doc 20 §20.3, Doc 11).
Misattribution that retires a load-bearing contributor is a Doc 12
failure (F10 developmental pathology) with lineage-based
regeneration as the remedy. Attribution carries uncertainty end to
end: retirement obligations trigger on uncertainty-aware
thresholds, never on point estimates.

## 28.4 Partner dependence and incentive separation (research extension)

Evaluate a candidate across independently developed partners and historical
versions as well as its original coalition. Record a versioned cross-play
table of utility vectors, feasibility, sample counts, and uncertainty.
Report original-partner versus new-partner degradation. [PSRO and joint-policy
correlation](https://arxiv.org/abs/1711.00832) motivate these probes;
response-to-mixture search is an optional strategy within existing gates.

Attribution estimates describe contribution under stated interventions.
They are not automatically suitable training rewards or budget rules.
Reward-policy experiments remain separate from attribution and preserve
independent organization-level evaluation (Doc 20 section 20.6).

## 28.5 Intervention effects and enabling-step credit

Transformation records distinguish assigned intervention, comparison policy,
confounders, outcomes and selection bias. Predictive correlations are not
automatically causal effects. For controlled trials use reproducible isolated
organization clones only where state, external services and resource interference
can actually be controlled; otherwise state the identification limitation and
collect fresh controlled trajectories where possible. Charge trial costs.

An enabling step receives developmental credit only through a declared path
and observed contribution to later acquisition or tested uncertainty reduction;
predicted terminal benefit is not earned credit. Retain step and whole-plan
outcomes separately. Test transfer across new implementations independently
from schema/units, statefulness and effect-policy shifts. Failure of transfer
narrows the guard; it is not successful generalization or permanent retention
justification. No causal interpretation exceeds its assignment and interference
assumptions.

## 28.6 Attribution across construction mechanisms

Keep library learning, proposal prediction, archive retention and inference
method as separate experimental factors. A better library can improve both
symbolic and model-guided search; extra archive history can improve prediction;
a macro can hide more inference work. Use the isolated and joint arms in Doc
07 sections 7.13-7.16 with full costs. Report interaction estimates rather than
assigning the combined improvement to the most recently added component.
