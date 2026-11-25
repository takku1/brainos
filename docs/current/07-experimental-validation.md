# 07 — Experimental Validation (three levels)

Status: partial — some requirements are built (Doc 31 register; Doc 21 section 21.0); the rest is specification, not implementation.

Conformance, usefulness, and superiority are three different claims.
A system conforms to BrainOS without outperforming any baseline.

## L1 — Architectural conformance (mandatory for compatibility)

Typed contracts honored; lifecycle semantics observed
(LEARN≠COMMIT≠AUTHORIZE; challenge suspends dependents at the next
epoch cut — episode boundaries included); resource accounting
present; version consistency
(manifest-pinned execution, no cross-version assembly); authority
boundaries (only Certified+Active authorizes irreversible acts).
Verified by the conformance suite: two independent implementations of
the same contract (old G1), determinism checks, interrupt/restart
persistence of manifest, bindings, and history. No performance
threshold. Pass/fail only.

## L2 — Operational qualification (deployment-specific)

Latency, availability, accuracy, retention, recovery, and safety
against the deployer's stated requirements — per track, not
universal. A robotics deployment qualifies on deadline performance and
safe degraded modes; an assistant on task success and abstention
calibration; a game on frame-budget behavior and determinism. L2
thresholds are set by the deployment, never by the architecture.

## 7.4 L3 - Research validation (hypothesis-specific)

Matched baselines for H1–H4 (Doc 01 §1.2): independent,
supervision-only, readout-state with frozen providers, shared-learning
per Doc 05. Match data, compute, task distribution, adapter capacity,
latency across arms — EXCEPT routing topology, which must be free to
vary when the claim under test is the value of adaptive topology
itself (matched-topology arms would erase the effect being measured).
Metrics: Δ_learn = J_shared − J_readout; directional transfer T_{i→j}
on held-out cross-component tasks; retention vs correction reported
separately. Improvement thresholds (≥15% precision, ≥25% tier cost
reduction, S(N) break-even per the canonical model (Doc 20)) live ONLY here as preregistered L3
hypotheses with evaluation-family-appropriate statistics (Doc 23:
≥5 seeds + CIs is the provisional minimum for stochastic families,
not a universal prescription — deterministic families verify by
proof/exhaustion, preference families by rater agreement) — never as
compatibility conditions. Parity and failure are findings; enforced
by CI.

## 7.5 Falsification

Report parity and failure as findings. Stitching-as-substrate stays
suspended (connectivity without continuity in six refuted forms).
R2b retention gap stays open until ancestor capability survives
world-change repair.

## 7.6 Test Track R — robotics (first track)

Providers: compact language/vision checkpoints behind contracts plus
a closed-loop controller, memory, and certification as software slots.
Composite sense-predict-act op gated on real perception and prediction
outputs. Direct links for fast feedback; readout for cross-domain
reasoning. 500/30/5 Hz is one test profile (Doc 06 §6.1), not the
architecture. Semantics before real-time: correctness, authority, and
recovery gates pass before deadline-performance claims. Sim-only
claims fail L3 only where the claim requires physical-world transfer
(paired-trajectory transfer metric + domain-randomization report per
manifest required); mathematical and simulated tasks with grounded
simulators can carry valid L3 results under the same gates. L1: two
independent implementations per contract + manifest persistence.
L2: deadline performance, safe degraded modes, revoke latency bound.
L3: precision/tier/economics/degeneracy hypotheses vs competent
alternatives (hand-tuned controller, external authorization controller).

## 7.7 Test Track G — game-dev NPC/crowd
Providers: BT-policy (internal execution only), utility ranking
(enabled-set ranking), GOAP-T3 planner, crowd fabric-sweep processor,
NPC-principal harness. Blackboard replaced by readout projection; tick
frames + rollback slots via Snapshot/COMMIT mechanics; LOD is a
scheduler-cost knob. L1/L2/L3 map as in §7.6 with game providers;
parity-or-worse vs a competent game-AI baseline is a finding.

## 7.8 Test Track S — science reproducibility
Providers: world-model PREDICT, simulator, PROV-O exporter,
prereg-registry, matched-ablation harness. Artifacts: registered M_k +
frozen analysis plan + content-hashed graphs. L1 conformance provides
the harness for replication (second provider, same capability; G7
frozen-manifest rerun as direct replication) but its verdict is
contract compliance only; the L3 verdict — effect generality — is
separate and never implied by L1. L3 on held-out tasks with
evaluation-family-appropriate evidence (Doc 23 and §7.4 L3 rule:
stochastic families provisional ≥5 seeds + CIs; deterministic and
formal families verify by proof/exhaustion; never a universal seed
count); sim-only/dream-only claims fail L3 only where the claim
requires physical-world transfer (per §7.6 scoping).

## 7.9 Test Track E — bounded evolution/growth
Providers: developmental provider family (specification-constrained trainable units
as one instantiation, not the definition) + assimilation by any Doc
11 method + niche-selection scheduler; BIRTH/SPLIT/FUSE/RETIRE
through Transactor.
L1: compatibility per new cell; L2: cost/latency bounds; L3:
routing/retraining/reuse-before-birth comparison + protected floors +
cooldowns; assimilation judged on union-of-parents + rare cases +
transitions vs best-parent/routed/ensemble/no-change with rollback on
drift. Open-endedness claims fail by design (bounded-gated); bounded
resources alone do not prove open-endedness impossible in general —
only that THIS track makes no such claim and its anti-open-ended
wording is a scope statement, not a theorem.

## 7.10 Interaction-driven adaptation (proposed, Track E)

Doc 27 section 27.6 fixes the initial generator/search limits. Run Doc 08's
first vertical slice before this multi-arm experiment. Doc 32 owns execution
and recovery; adaptive evaluation follows Doc 23 sections 23.5-23.6 across
research tracks. Adaptation policies cannot bypass those contracts.

Question: do capability-induced opportunities improve useful acquisition
beyond adaptation to external demand? This bounded Track E experiment
makes no open-endedness claim or new universal conformance requirement.

Start with grounded typed parsing/transform/checking tasks. Preregister
the primitive library, composition grammar, generator, contexts, novelty
boundary, competence floors, budgets, horizons, and stopping rules.
Intermediate artifacts can enable previously infeasible tasks; withhold
final evaluation tasks from discovery and construction.

| Arm | Intervention | Claim isolated |
|---|---|---|
| A | Externally fixed demand with existing adaptation | Baseline |
| B | A plus capability-induced opportunity discovery | Endogenous opportunity value |
| C | B plus bounded challenge generation and cross-context transfer | Additional curriculum/transfer value |
| D | B with interaction feedback replaced by opportunities replayed from an independent matched run | Adaptive coupling versus varied exposure |

Log replay provenance and timing, infeasible tasks, and exposure differences;
do not silently discard incompatible replay. If replay is uninterpretable,
use an explicitly matched random-opportunity control and report its limits.
Ablate generation and transfer separately in C. Separately test archive
reuse and contextual contribution before combining all mechanisms.

Match starting libraries, external workload, resource limits, and external
information access. Charge discovery, generation, failed construction,
validation, communication, and archives. Report intervention-induced
exposure/allocation differences. Freeze final independent evaluation.

Primary outcome: additional held-out functional coverage per total spend,
subject to preregistered competence floors. Also report retention, recovery,
latency, joint failure, validated lineage transfers, causal opportunity
yield (Doc 25), and invention levels (Doc 27). Use Doc 23's replication
and uncertainty rules. Parity, lost competence, gains absent on independent
tasks, or gains explained by extra compute/exposure fail to support the
mechanism. One domain supports only a bounded domain claim. Not run here.

Additional isolated trials compare frozen/current/historical-mixture
counterparts, cross-play degradation, and cycles (Docs 14, 25, 28).
Vary scarcity and incentive policy independently (Doc 20). Compare
construction operators and fixed, structured-changing, and unstructured
goals (Doc 27 section 27.5), matching primitives and search budgets.
Report validity, coverage per spend, retention, and dependency failures.
Combined interventions do not identify individual mechanism effects.

## 7.11 Controlled capacity expansion (proposed, Track E)

Test Doc 11 section 11.9 and Doc 25 section 25.10 in a grounded service
domain with fixed implementations before adding synthesis. Workloads include
stationary demand, bursts, a context-specific deficit, provider loss, a
downstream bottleneck, and delayed/noisy demand measurements. Keep workload
arrival rates and per-instance service measurements explicit.

Compare a tuned fixed pool; a competent conventional queue/utilization
autoscaler with cooldowns; deficit-driven expansion; and deficit-driven
expansion with separate temporary/persistent role assignment. Match hard
resource limits, initial implementations, and tuning budgets; count controller,
startup, validation, inactive-artifact, and failed-trial costs. These controls
test whether the proposal adds value beyond ordinary autoscaling.

Ablate pending-admission feedback, local contention feedback, and role
assignment independently. Sweep response delays and simultaneous nominations.
After service loss compare restore-the-old-count with restore-required-service
policies, preserving competence floors in both arms. Recovery events are
externally injected; a provider's self-reported loss cannot justify spending.

Measure service shortfall over time, latency, settling time, excess capacity,
total spend, coverage, retention, and correlated failure. Preregister tolerable
overshoot and competence floors; apply Doc 23 uncertainty/replication rules.
More instances or faster construction alone is no gain. Failure to outperform
the tuned autoscaler on declared outcomes, congestion amplification, repeated
expansion/retirement cycles, or lost protected competence refutes the tested
advantage. Throughput replication establishes no capability invention.
No experiment in this section has been run here.

## 7.12 Organizational prediction and planning (proposed, Track E)

Hold the construction-library revision fixed across these arms. Learning a
library is a separate intervention (section 7.13); joint testing uses section
7.16 so a stronger generator cannot be mistaken for a better outcome model.

Test Doc 19's reusable intervention knowledge using Doc 27 sections 27.6-27.7's
bounded record-processing domain with immutable providers. Freeze primitives,
grammar, depth (initially <= 2), branching/trial budgets, task generation,
acceptance criteria and data access before comparison. Core's first vertical
slice remains prerequisite for claims about actual runtime behavior.

| Arm | Adaptation mechanism | Purpose |
|---|---|---|
| Static | Tuned handwritten organization | Whether adaptation is needed |
| Selection | Contextual provider selection/portfolio | Routing versus construction |
| Search | Typed composition with memoization and bounded lookahead | Strong ordinary planning/caching baseline |
| Cases | Adaptation of full successful/failed cases | Value of experience without learned forecasts |
| Model | Cases plus learned guarded outcome forecasts and probe selection | Additional predictive mechanism |

Match primitive/history access, training exposure, horizons, tuning opportunities,
and total budgets. Search versus Model uses equal lookahead; Cases versus Model
uses equal intervention history. A one-step greedy policy can illustrate the
enabling-step example but is not the substantive planning baseline. Report
unused allocations as well as spend, including upfront learning and later model
queries, failed trials, validation, execution, storage and maintenance once.

Separate conditions: familiar tasks, held-out compositions, unseen implementations
of known contracts, semantic units/schema changes, provider removal, resource
interference, and workloads favoring no change. Transfer across implementations
is distinct from transfer across changed contracts or effect policies. Use
development/admission/final splits and adaptive-test controls (Doc 23).

Primary endpoint: total resource vector required to reach and maintain a
preregistered external coverage/retention target at a common budget limit.
Record non-attainment explicitly; report success probability and cumulative
spend rather than cost only among successes. Scalarization requires declared
weights/sensitivity. Secondary endpoints: held-out coverage, retention/floors,
adaptation latency, failed interventions, repair costs, model/footprint
invalidations, abstention, calibration, and one-/multi-step prediction errors.

Ablate learned forecasts, guard features, negative cases, dependency-driven
invalidation and lookahead separately. Count an incorrect forecast even if
admission catches it. For causal effects, assign interventions on reproducible
isolated organizations with matched workloads/resources; record randomization
or balancing, carryover, interference and cloning limits (Doc 28 section 28.5).
Observational predictions remain predictive absent identification assumptions.

Falsification: no advantage over the strongest applicable baseline after complete
overhead; gains explained by added horizon/history; failed transfer beyond guards;
or protected-floor violations do not support the proposed advantage. If memoization
or case reuse explains the gain, select that mechanism. The hand-supplied
parser/composition example demonstrates lookahead only. This experiment is
specified, not run, and establishes no primitive invention or indefinite novelty.

## 7.13 Typed abstraction learning (selected next construction experiment)

Use Doc 27 section 27.8's deterministic effect-free domain. Compare flat
primitive search, ordinary memoization, a competent handwritten macro library,
and learned typed abstractions. Share development examples, underlying primitive
access, tuning opportunities and total resource limits. Library induction uses
development traces only; freeze each learned revision before independent
admission/final evaluation. Hold the organizational prediction strategy fixed.

Bound expanded primitive graph size and measured work, not equal macro-token
depth. Count induction, search/matching, failed abstractions, validation,
maintenance, storage and execution. Test held-out structural task families,
semantic/unit restrictions, failures, and unrelated retained tasks. New constants
in a familiar template alone do not establish abstraction transfer.

Primary endpoint: total resource vector to reach/maintain a fixed external
coverage/retention target, with budget-limited non-attainment. Also report
cold-start versus later reuse, failed construction, library size/carrying cost
and search degradation. No gain over memoization/static macros after complete
costs, unearned scope generalization, or hidden extra primitive work fails to
support the advantage. A named macro is composition, not new primitive invention.

## 7.14 Collective inference (separate computation experiment)

Use a bounded relational task with checkable outcomes and controlled ambiguity.
Compare independent providers, tuned feed-forward pipelines, a conventional
constraint/factor solver, and Doc 10's coupled inference. Match observations and
total compute including iterations, scheduling, integration and recovery.
Include cases where a pipeline is sufficient. Vary graph size, update order,
staleness, conflicting evidence, support withdrawal and budgets.

Measure correctness, calibration, abstention, time to a valid answer, contradiction
handling, termination and recovery. Nonconvergence and confident correlated errors
are failures; extra observations/compute cannot explain an integration benefit.
If a conventional solver matches the outcome more cheaply, select that provider.
No global convergence or authority follows from agreement among mechanisms.

## 7.15 Repertoire retention (separate archive experiment)

On the same eligible history and retention budget compare current-best,
Pareto-diverse, behavior-diverse and cost-matched random archives (25 section
25.12). Freeze descriptor/policy revisions before task-shift evaluation; final
workloads remain independent of selection. Test provider losses, resource shifts
and stationary workloads. Match restored-candidate construction/prediction policy.

Measure time/spend to reacquire or restore required coverage, protected competence,
joint failure, final held-out coverage and actual reuse. Count descriptor evaluation,
search, storage, maintenance, restoration and revalidation. Diversity that fails
to beat simpler archives after costs is not a retention advantage. Archival
evidence does not authorize reuse without current validation.

## 7.16 Construction/prediction interaction

Only after isolated tests, compare a 2x2 design: ordinary typed search; abstraction
learning alone; organizational prediction alone; both together. Hold archive
retention, inference method, primitive access, history/exposure, organizational
planning horizon, expanded graph bounds, tuning and total resources fixed as
appropriate to the intervention. Declare any differences caused by learning.
Charge cumulative training/maintenance and report unused budgets/non-attainment.

Compare the joint arm with each single-mechanism arm. Improvement of the joint
arm alone is no evidence of positive interaction: estimate the interaction
contrast on preregistered outcomes with uncertainty and declared scalarization
if needed. Extra lookahead, hidden macro work or archive exposure are competing
explanations. None of sections 7.13-7.16 has been run in this repository.

## 7.17 Continuous developmental ecosystem (X4, proposed)

Purpose: observe the mechanisms as one organism rather than as separate
demonstrations. One persistent organization runs a long, changing demand
stream with every developmental mechanism active under one development budget
per period:
- composition and cumulative construction;
- contextual selection with the lifecycle (dormancy, wake, regeneration);
- assimilation with the corrected gate (Doc 21 sections 21.13-21.14).

Design constraints, fixed before any preregistration:
- **Demand mixes domains.** Text-derived arithmetic demands exercise
  construction; lookup demands exercise competition and assimilation. Phases
  include recurring, rare and novel demands.
- **Controls** are the section 20.9 organizations on the identical stream:
  fixed, conventionally adaptive and oracle.
- **Primary outcome** is net organizational value (section 20.9) over the
  horizon.
- **Secondary outcomes** are the section 25.13 meter series, including the
  organizational-capability verdicts.
- **Seeds.** At least five independent demand seeds. The analysis is
  per-seed, with no pooling across seeds that could hide a failing seed.
- **Live execution.** Developmental decisions use only evidence the
  organization itself observed; a measured cost table may replay controls,
  but not the developing organization.
- **Negative results are expected and valid.** A developing organization that
  costs more than it returns is a finding about when development pays.

X3b (corrected assimilation gate) is folded into X4 rather than run in
isolation: its acceptance claims are measured inside the ecosystem, where
their full costs are visible.

## Gate registry (canonical)

L1 conformance (universal — every compatible implementation):
L1-C1 typed contracts honored; L1-C2 lifecycle semantics
(LEARN≠COMMIT≠AUTHORIZE; challenge suspends dependents at epoch
cuts); L1-C3 resource accounting present; L1-C4 version consistency
(manifest-pinned execution, no cross-version assembly); L1-C5
authority boundaries (Certified+Active for irreversible acts).
L2 operational: deployment-set thresholds per track, never universal.
L3 research (historical G1–G7, ported lineage, preregistered per
claim): compatibility two-implementations-one-contract; precision
≥15% with family-appropriate statistics (§L3 rule above);
tier reduction ≥25%; escalation/demotion;
economics S(N) break-even (canonical: Doc 20); degeneracy degraded-limits; persistence
across interrupt/restart. References to G1–G7 elsewhere mean these L3
gates; universal conformance means L1-C1..C5. Two implementations
appear at both levels with different verdicts: L1 demands two
independent implementations of one contract to prove contract
compliance; L3 uses a second provider with the same capability to
prove effect generality (conceptual replication). Passing one never
implies passing the other.
