# 25 — Computational Ecology Dynamics

The ecology is a dynamical system over populations, not a ranking.
This document states what equilibrium, pressure, diversity, growth,
and stability mean operationally — targets for measurement and
control, not theorems asserted.

## 25.1 Population equilibrium

Equilibrium = birth rate ≈ retirement rate within carrying capacity
set by budgets (Doc 20), with stable coverage of required
capabilities. Balance alone does not establish stability: a balanced
ecology can still thrash (churn without improvement), erode (silent
coverage loss), or ossify (no successful acquisitions). Stability is
judged separately by coverage persistence, core-vs-edge turnover,
and responsiveness to new demand — balance is necessary, never
sufficient. Measured by: population size trend, coverage per
required capability, churn rate. Disequilibrium signatures: growth
without coverage gain (bloat), coverage loss without budget cause
(erosion), churn without improvement (thrashing) — each routes to a
different intervention (tighten nomination, protect floors,
lengthen cooldowns).

## 25.2 Selection pressure

Pressure = how strongly substitutability differences drive
reallocation (scheduler weight on s(i→j,c) rankings). Too high:
premature convergence, loss of rare niches, brittleness. Too low:
bloat, stagnation, unearned persistence. Pressure is a tuned
control with reported value and effect, not a fixed virtue —
experiments vary it and report the diversity/cost frontier.

## 25.3 Diversity maintenance

Three mechanisms, each measured: protected floors (rare critical
capabilities exempt from competition — policy, not earned);
failure-domain independence (substitutes must fail differently,
measured joint failure rates per Doc 17 §17.3); exploration reserve
(bounded capacity for low-fitness candidates with option value,
Doc 20 B_explore). Diversity is an instrument for robustness and
future capability, budgeted explicitly.

## 25.4 Growth and stability control

Growth follows demand (Doc 18) within budgets (Doc 20); stability
comes from hysteresis, cooldowns, minimum evaluation windows, and
oscillation detection (birth/death cycling on the same niche
triggers longer cooldowns + review of the nomination).

## 25.5 Measured state, controls, and stability criterion

Ecological state vector (all measured per epoch, none asserted):

```text
z_t = [N_t, C_t, Q_t, R_t, D_t, L_t, V_t]
```

population, coverage, quality, resource consumption, diversity,
retention, turnover. Control inputs a_t = π(z_t, d_t, b_t):
interventions (admit, retire, protect, re-budget, cool down)
from demand d_t and budgets b_t; w_t is environmental change:

```text
z_{t+1} ~ F(z_t, a_t, w_t)
```

No universal analytical solution is claimed: specify the measured
state, admissible interventions, constraints, and experimental
control policies, and test stability empirically (Phase 5).
Stability is relative to workload and environment: bounded
resources + protected competence + responsiveness, not a fixed
point. A stationary workload may justify a completely static
organization — static is a valid stable regime, and continual edge
turnover is available behavior, never a requirement. Selection
pressure is operationalized as reallocation responsiveness to s(·)
rankings (measured, tunable); diversity as coverage-weighted
substitution breadth plus failure-domain independence. Registered
open questions (analytical where tractable, experimental otherwise;
convergence never asserted without its assumptions): under which
demand/budget regimes does the control law hold coverage; which
delays and feedbacks produce oscillation; what conditions precede
collapse. Hysteresis, cooldowns, and oscillation detection enter
decisions as explicit control parameters with logged values, not
as undescribed damping.

## 25.6 Endogenous pressure and niche construction (research proposal)

Capabilities can change what becomes feasible, scarce, or worth building.
The research question is whether this generates useful adaptation beyond
responding to externally supplied demand:

```text
capability change -> changed opportunities/resources/interactions
  -> measured demand -> nomination -> construction and evaluation
  -> validated capability change
```

This is an optional Morphogenesis proposal, not an implemented mechanism.
Pressure selects among variants; Doc 27 still owes a method for creating
them. Imbalance can produce specialization, cooperation, cycling, collapse,
or no useful change. Neither continual disturbance nor growth is a goal.

Extend experimental observations, without replacing section 25.5's state,
with e_t: task availability, resource access, artifacts, and interaction
effects. Test e_{t+1} ~ H(e_t,z_t,a_t,w_t) and demand derived from external
requests plus observed opportunities in e_t. H is a measured hypothesis,
not a biological law. Changed task labels alone establish no new niche.

## 25.7 Mechanisms to research

Biological and artificial-life evidence motivates these experiments; it
does not establish their benefit in BrainOS.

| Mechanism | Evidence or open question | Proposed computational test |
|---|---|---|
| Niche construction and ecological inheritance | Bacteria evolved environmental modifications and dependence on them [S1]. | Persist versioned tools and representations; compare successor acquisition with artifacts available versus reset. Remove artifacts to test causality and dependency. |
| Frequency-dependent selection and coevolution | Bacteria/phage experiments connect coevolution to resistance diversity [S2]. | Vary population composition; measure whether contextual contribution is greater when rare and declines when common. Rarity alone earns no reward. |
| Habitat heterogeneity and specialization | Bacterial diversification was studied in heterogeneous environments [S3]. | Compare pooled and distinct task contexts under matched resources; measure distinct competence and joint failures, not provider counts. |
| Challenge/solution co-development | POET generates environments alongside solvers and transfers solutions [S4]. | Compare generated curricula with fixed and random curricula; separately disable transfer. Keep final evaluation independently held out. |
| Historical contingency and stepping stones | Digital-organism experiments traced complex features through simpler antecedents, sometimes initially deleterious [S5]. | Retain a bounded lineage archive and test reuse in new contexts versus an equal-cost current-best archive. |
| Mutualism, cross-feeding, and division of labor | Open question requiring targeted primary-source review: when do complementary producers/consumers yield net collective value? | Compare artifact-sharing coalitions with best-parent, routed, ensemble, and no-change alternatives; charge communication and dependency costs. |
| Disturbance, succession, and recovery | Open question requiring targeted primary-source review: which change schedules support recovery or new organization? | Vary workload shifts and resource shocks independently; measure recovery and retention. Do not assume an optimal intermediate disturbance rate. |

Priority: niche construction and contextual contribution first; challenge
generation and stepping-stone reuse second; combined mechanisms only after
individual ablations. Doc 07 section 7.10 defines the initial experiment.

## 25.8 Productive change versus failure

Report separately: held-out useful acquisitions per total spend; validated
acquisitions causally linked to prior capability changes per investigated
opportunity; contextual coverage and coalition benefit; joint failure;
retention and recovery; turnover and historical-opponent performance.
Failed construction, archive maintenance, and evaluation count as costs.

An arms race beating current opponents without improving against a fixed
historical panel or independent tasks is cycling until contrary evidence
exists. Artifact dependence belongs in contracts and recovery plans.
Population growth, novelty scores, more interactions, and harder generated
tasks alone establish neither invention nor open-ended evolution.

Existing resource caps, admission gates, and protected floors still apply.
Challenge generators propose tasks, not acceptance rules or authority.
A stable deployment may coexist with bounded exploratory branches; the
deployment need not be disturbed to sustain research.

## 25.9 Primary sources and limits

### Interaction games and non-transitive selection

Preserve cross-play outcomes (Doc 28 section 28.4): A beating B, B beating
C, and C beating A is a cycle, not a universal quality ordering. Compare
latest-only selection with historical-mixture selection. [Alpha-Rank](https://arxiv.org/abs/1903.01373)
is an optional empirical-game analysis method for recurrent structures;
its ranking depends on the sampled game and parameters and establishes
neither external utility nor authority. Retain utility vectors; any scalar
payoff follows Doc 20's explicit scalarization policy.

Checked 2026-11-24. All BrainOS mappings remain untested proposals.

- [S1: Callahan, Fukami, and Fisher (2014), Rapid evolution of adaptive niche construction in experimental microbial populations](https://web.stanford.edu/~fukamit/callahan-et-al-2014.pdf).
- [S2: Competition and coevolution drive the evolution and the diversification of CRISPR immunity (2022)](https://www.nature.com/articles/s41559-022-01841-9).
- [S3: Rainey and Travisano (1998), Adaptive radiation in a heterogeneous environment](https://www.nature.com/articles/27900).
- [S4: Wang et al. (2019), POET](https://arxiv.org/abs/1901.01753), and [Enhanced POET (2020)](https://arxiv.org/abs/2003.08536). Bounded demonstrations do not prove indefinite innovation; encoding and progress measurement remain limitations.
- [S5: Lenski et al. (2003), The evolutionary origin of complex features](https://www.nature.com/articles/nature01568). Digital-organism results do not establish arbitrary program invention or general intelligence.

## 25.10 Feedback-controlled capacity allocation (research proposal)

The useful abstraction is local evidence regulating the amount and role
of capacity, while organization-wide constraints bound the result. This
does not equate physical space with compute or transfer biological rates.

For context k, record service deficit d_k, active eligible capacity n_k,
contention x_k, pending admissions p_k, and measurement delay tau. An
illustrative controller, to be identified and compared experimentally, is:

```text
proposal_k(t) = clip(Kd*d_k(t-tau) - Kx*x_k(t-tau) - Kp*p_k(t), 0, quota_k)
n_k(t+1) = n_k(t) + admitted_k(t) - retired_k(t)
```

The first expression is a bounded proposal intensity, not an instruction
to allocate, a probability, or a stability theorem. Define units and
sampling interval before selecting gains. Deficit measures actual service
shortfall, not queue length alone. Pending admissions include reserved
construction/evaluation work to reduce duplicate responses to one deficit.
The Transactor and resource reservations still decide admissible changes.

Feedback based on achieved service can suppress unnecessary expansion.
Separating expansion rate from context assignment may preserve reusable
construction capacity while filling a specific gap. Temporary pools may
absorb bursts; persistent specialization requires evidence after the burst.
Reduced demand can legitimately yield no construction and zero turnover.

Delays, parallel nominations, stale measurements, and shared bottlenecks
can produce overshoot despite hard caps. Measure settling time, excess
capacity, backlog, oscillation, and protected competence; vary gains and
delays. Local stability alone does not establish organization-wide stability.
Restoration stops when service is recovered, even if the old instance count
is not reproduced. Increasing instance count without restored coverage is
failed recovery, not successful expansion.

Primary-source basis, checked 2026-11-24; computational translations above
remain hypotheses:

- [Lander et al. (2009), feedback and staged production modeling](https://journals.plos.org/plosbiology/article?id=10.1371/journal.pbio.1000015): modeling plus experimental context motivates separate controls over continuation and output roles, not a universal AI controller.
- [Puliafito et al. (2012), quantitative local-constraint experiments](https://pmc.ncbi.nlm.nih.gov/articles/PMC3271933/): measured growth arrest under mechanical constraints motivates testing saturation feedback; contact alone was insufficient in this system.
- [Streichan et al. (2014), controlled constraint changes](https://pmc.ncbi.nlm.nih.gov/articles/PMC3992650/): imposed expansion/compression altered progression, motivating reversible demand-sensitive activation as an AI hypothesis.
- [Snippert et al. (2010), population maintenance under individual turnover](https://pubmed.ncbi.nlm.nih.gov/20887898/): motivates separating pool continuity from persistence of individual instances; random replacement is not thereby recommended for critical AI providers.

## 25.11 Forecasting organizational interventions

The population/control summaries in sections 25.5-25.10 describe measured
ecological state; they are not generally sufficient features for predicting
a particular organizational change. Doc 19's outcome model conditions on
interfaces, semantic units, dependencies, resource/state constraints and history.
The model can rank expansion, specialization, composition or recovery proposals,
but protected floors, actual capacity, and impact checks still govern every step.

Jointly changing ecology controls and predictor strategy obscures attribution.
Test them separately before combination: sections 7.10/7.11 in Doc 07 cover
interaction/expansion; section 7.12 covers reuse of intervention knowledge at
matched horizon and exposure. Equal current competence may hide different
future construction costs; measure those on declared future workloads.

## 25.12 Bounded organizational repertoire

Retain useful alternative organization artifacts for future construction or
recovery. An archived organization is distinct from an active instance, a
TransformationRecord (observed trial), and a reusable macro (library operation).
References may link them, but their roles and costs remain explicit.

Start with a small preregistered behavioral descriptor, retention budget and
policy revision. Candidate descriptors include context coverage, resource
tradeoffs, recovery behavior and measured failure-domain profiles. Graph novelty
or different names alone establish neither behavioral difference nor resilience.
Store manifest/artifact/lineage refs, supported contexts, measured descriptor
and uncertainty, validation expiry, dependencies, retrieval/revalidation costs,
and retention rationale. Protected critical floors are separate from discretionary
diversity retention. Archive membership never authorizes execution.

Compare current-best, Pareto-diverse, behavior-diverse and cost-matched random
retention on the same eligible history and budget. Charge descriptor measurement,
archive matching, search, storage, maintenance, restoration and revalidation.
Descriptor revisions change selection and require an explicit policy comparison.
Retrieval nominates a candidate; current contracts, evidence, resource footprints
and replacement gates still apply. Stationary workloads can justify a small or
empty discretionary archive. More entries, novelty and turnover are not success.

[MAP-Elites](https://arxiv.org/abs/1504.04909) motivates behavioral repertoires,
not a universal descriptor or guaranteed BrainOS advantage. Doc 07 section 7.15
tests this retention policy independently; Doc 21 owns record/retention rules.
