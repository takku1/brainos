# 34 — W3 Organizational Dynamics and Developmental Expansion

Status: specified — W3 investigation design, richer-environment
proposal and implementation gap analysis. No confirmatory experiment
is authorized from this document; the W3 preregistration draft lives
at `docs/results/2026-11-25T-w3-homeostasis/PREREGISTRATION.md` and
is explicitly unfrozen. No new architectural subsystem is proposed.

## 33.x cross-reference

ADR (Doc 33) provides the integration vehicle: the replaceable
developmental policy, evidence-grounded observation, declared
viability bands and the unified observatory. W3 asks whether the
organism that vehicle coordinates is homeostatic or merely
stagnant, and investigates cumulative development across unfamiliar
environments. W3 owns the questions; ADR owns the instruments.

## 34.1 Operational definitions

Each definition names its measurable signature and what would
distinguish it from its look-alikes. Labels follow
`development_policy.classify_quiescence` where implemented.

- **Viability.** Every demanded capability is served by a competent
  member within declared bands, and the runway covers the assessment
  horizon. Measured: per-capability competence verdicts, retention
  freshness, runway periods. Falsified by: any demanded capability
  unserved, incompetent, or unassessed.
- **Homeostasis.** Viability maintained across environmental change
  through developmental responses, with returns to justified
  inactivity between disturbances. Measured: viability trajectory
  across regimes plus decision log. Not established by a flat line
  alone — the disturbances must be genuine and the responses must be
  policy-driven.
- **Quiescence (verified healthy).** The `verified-healthy`
  classifier output: every required viability variable assessed and
  inside bands, with nothing unknown. Measured: consecutive
  noop/defer ticks with no open deficiencies and no unknown
  viability variables.
- **Quiescence (conditional).** Assessed variables are inside bands
  but some required variables remain unknown (e.g. recovery
  readiness never exercised). The uncovered list is cited, never
  hidden. Conditional quiescence is not a homeostasis claim.
- **Blocked inactivity.** Deficiencies persist and no admissible
  action exists: members blocked, budgets exhausted, or every
  search outcome categorized (budget/deadline/validation-limited,
  stalled). Distinguished from stagnation by the logged evidence
  that action was attempted or is provably unavailable.
- **Stagnation.** Quiescence-shaped inactivity while deficiencies
  remain open, evidence is missing, or exploration is unaffordable.
  Distinguished from homeostasis by the unresolved list: stagnation
  has entries, homeostasis does not. A high no-op rate alone proves
  nothing.
- **Resource-constrained inactivity.** Deferral with measured burn
  against a runway below floor, or abstention on overdraft.
  Distinguished from stagnation by the explicit budget evidence in
  the decision record.
- **Search outcome (B45).** Failed constructions never establish
  exhaustion by themselves. `classify_search_outcome` separates:
  `succeeded`; `exhausted` (the entire declared finite space
  examined — requires explicit coverage evidence, never inferred
  from failure count); `budget-limited`; `deadline-limited`;
  `validation-limited`; `stalled` (repeated unknown outcomes with
  partial coverage); `unknown`. Exhaustion is distinguished from
  stagnation by the logged attempts plus the coverage proof:
  exhaustion has both, stagnation has neither.
- **Recovery.** Return to viability after a recorded loss, measured
  from the exclusion/impact record to the first correct re-service.
  The 10-minute and 1-hour runs show recovery only for provider loss
  via re-acquisition; recovery from competence loss (no member lost,
  outputs wrong) is untested.
- **Organizational oscillation.** Acquire→dormant→wake→retire cycles
  per capability. Healthy below the cooldown thresholds; thrash above
  them. Measured from member history transitions and the decision
  log, never from narration.

## 34.2 Perturbation and recovery experiment design

Objective: separate homeostasis from stagnation by probing the
organization with disturbances it has not seen, under matched
conditions across three controls.

**Perturbations** (independently scheduled, journaled as environment;
never scripted as organizational responses):

1. Demand shift: previously unseen input distributions over existing
   contracts (new canonical/irregular contexts).
2. Provider loss: exclusion of an active member through the kernel
   impact path (as drilled), including load-bearing specialists.
3. Resource shock: sudden grant reduction mid-run (operator act).
4. Novel requirement: a capability from the approved vocabulary
   with no serving member and no dormant candidate.
5. Recurring demand: previously mastered demands re-presented after
   long absence, to test retention vs relearning.
6. Active-but-incompetent provider: a serving member whose outputs
   turn wrong without loss of membership, to test whether
   competence evidence — not mere presence — drives investigation.

**Controls** (matched initial knowledge, matched budgets):

- Static: fixed members only, no developmental policy (defer always).
- Adaptive selection: EcologyPolicy selection among provisioned
  members, recruitment/wake enabled, no construction.
- Conventional reconstruction: a competent non-policy repair
  strategy (scripted re-admission/replacement through the same
  kernel gates, with its own cost accounting) — separates the
  value of construction as such from the value of BrainOS's
  particular developmental policy.
- Developmental: the full replaceable-policy loop (the treatment).

**Measures** (all from kernel records): time to detect (first
investigate after deficiency onset), time to initiate (first
executed transformation), time to restore (first correct service),
developmental expenditure, retention and regression (assessment
verdicts before/after), population growth, churn per 100 steps,
unresolved-deficiency duration, and return-to-quiescence time with
the classifier label at return.

**Draft hypotheses** (exploratory; the preregistration draft states
them as falsifiable claims with acceptance bounds):

- W3-H1a (functional expansion): organizations permitted
  construction restore service after capability-destroying loss
  where selection-only controls cannot, per matched loss. This
  tests what construction enables, not which policy is better.
- W3-H1b (policy effectiveness): the developmental policy restores
  service faster and cheaper than the conventional-reconstruction
  control, per matched loss with explicit cost boundaries. This
  tests BrainOS's policy against a competent alternative, not
  against a crippled one.
- W3-H2: quiescence after recovery is classified healthy, not
  unknown, within N steps of restoration. The classifier label is
  necessary but not sufficient: an independent evaluator recomputes
  viability from kernel records (never the policy's own verdict
  as the sole evidence).
- W3-H3: no capability with a fresh retain assessment is retired or
  left dormant while demanded (specialist preservation).
- W3-H4: cumulative developmental spend stays within the declared
  band across all phases including scarcity and disruption.

**Acceptance and failure criteria**, scope limits, and the explicit
non-goals (no convergence claim, no world-model learning, no neural
providers until separately justified) are in the preregistration
draft. Confirmatory W3 execution is not authorized here.

## 34.3 Richer developmental environment (proposal, not implementation)

**Audit of the trusted vocabulary** (all in `src/brainos/providers.py`):
text→text has normalize_ws and parse_nl_sum; text→integers has
parse_csv and text_length; integers→integer has sum, sum_loop and
count; integer→integer has negate and double; range-batch→integers
has seven range operators; exact-batch→integers has four exact
operators. Missing entirely: filtering and projection, aggregation
beyond sum/count, statistics, temporal and sequence operations,
memory and stateful accumulation, search beyond linear scan, and
symbolic transformation beyond fixed text mappings.

**Chosen bounded domain: capped integer-list pipelines.** Values are
bounded integer lists and `{data, queries}` workloads on the proven
`range-batch` pattern (whose trusted featurizer makes retention
assessment possible today). This domain is small enough to specify
completely and rich enough for multi-generation construction.

**Contract shape** (every provider pure and deterministic):
`{data: [int], queries: [[lo, hi], ...]}` variants plus plain
integer lists, with independently computable ground truth in the
workload generator. No generated code, no ambient state, no new
kernel contracts.

**Orthogonal candidate primitives** (B46; named with signatures;
NOT implemented — building them changes what the ecology can
express and waits on review): `range_filter(data, lo, hi) ->
[int]` (select matching elements); `range_project(data, queries)
-> [[int]]` (materialize windows); `range_count_distinct(data)
-> int`; `range_diff(a, b) -> [int]` (set difference over query
results, enabling multi-stage reuse). Each needs a featurizer
entry and admission cases before use.

Deliberately NOT proposed as primitives: `range_mean`,
`range_max` and other per-query statistics. Those are
construction TARGETS (mean from sum/count/division, maxima from
comparison folds), not building blocks — supplying them would
hand the ecology the very abilities the experiment is supposed
to discover. Divisibility and multi-input combination are open
expressivity gaps, not silent assumptions.

**Expressivity audit** (`tests/test_expressivity.py`, B46): unary
chains and cumulative reuse of acquired graphs are witnessed end
to end (csv-negsum at depth 3; csv-dblsum reusing csv-sum with
`cumulative=True`). Recorded as unrepresentable: joins of two
computed values (nodes bind exactly one input reference;
`src/brainos/graphs.py`), and means (no division primitive
exists). If either gap closes, the corresponding gap test fails
loudly so the ability is promoted to a construction target.

**Workload levels** (ground truth generated before rendering demands):

- L1 (single operations): one filter, projection or aggregation per
  demand over small lists. Establishes baseline competence.
- L2 (composed queries): two-stage demands (e.g. filter-then-count)
  that reward acquiring composites over repeated primitive chains.
- L3 (reused substructure): workloads sharing a common subquery
  across demands, so organizations that retain an intermediate
  capability (specialist) outperform ones that recompute it —
  cooperation and reuse under test, not asserted.

No workload prescribes the final graph. The experimenter generates
demands and ground truth; BrainOS discovers the structures.

## 34.4 Lifecycle integration gaps and trigger designs (B47/B48 implemented, bounded)

**Why the ecology underexercises the lifecycle** (observed, not
speculated): retention assessments run only where trusted featurizers
exist (range-batch today; text and arith have no assess path, so no
verified dormancy or retirement there); dormancy needs a verified
redundant/not-best verdict plus a serving alternative (rare by
design); wake needs a dormant member plus demand (demonstrated);
archived members do not exist yet because nothing has ever been
retired; assimilation needs a recorded selection (B21 gate, never
yet produced).

**Implemented triggers** (bounded; `ViabilityPolicy.propose`,
`tests/test_development_policy.py::TestLifecycleTriggers`,
executors pinned in
`tests/test_observatory.py::TestExecutorDecisions`):

- Retire after dormancy: a dormant member with a fresh redundant
  verdict, a serving alternative, and dormancy age beyond a declared
  threshold proposes `retire`. Dormancy-first is enforced — the
  executor abstains without a verified redundant assessment — so
  two independent confirmations (assessment + sustained dormancy)
  precede the irreversible step. Executed only through the kernel
  `retire` gate with the assessment cited.
- Regenerate from archive (B47): when a demanded capability has no
  active and no dormant member but an archived member exists, the
  policy proposes `regenerate` and the kernel re-validates admission
  from scratch. Distinct from wake (dormant member exists),
  revalidation (stale assessment on a serving member) and repair:
  the trigger keys on actual lifecycle state, never on elapsed
  dormancy alone.
- Stale-retention revalidation: serving members whose assessments
  are all stale propose `investigate` for revalidation before any
  lifecycle change is considered.
- Assimilate on overlap (B48): when every serving member of a
  demanded capability carries an adverse (redundant/not-best)
  assessment, the policy nominates consolidation candidates for
  evaluation. A single adverse member beside a healthy one still
  proposes `suspend`, preserving the overlap for later
  consolidation. Nomination never publishes: the B21 selection gate
  and kernel `assimilate` path still decide publication, and the
  executor surfaces candidates with controls rather than binding
  anything.
- Assimilate on selection: the existing B21-gated path is
  unchanged — no publication without a recorded selection.

## 34.5 Observatory deltas

Implemented in the unified `live/` server: competence per context
with evidence status, retention freshness and verdicts, runway with
measured burn, churn from member-snapshot deltas, estimated NOV
under the declared cost model, acquisition lineage with composite
depth, unresolved deficiencies, and the quiescence classifier label
with its reasons. All panels cite kernel records; estimated and
unknown values are labeled as such in the UI.

**Journal growth design** (not implemented): at ~10KB per tick, a
24/7 ecology needs bounded storage without breaking auditability.
Proposed: segment the journal by tick ranges with hash-chained
segment manifests (each segment header commits to the previous
segment's terminal checksum, preserving the tamper-evidence chain
across segments); retain decision, assessment, impact and
publication records in full; compact per-task invocation timings
older than the retention horizon into per-capability aggregates that
cite the segment they summarize. No deletion without a manifest
entry. To be specified before the 8-hour run is repeated.

**Archival vs destructive compaction.** Archival relocation (moving
records into a cited, replayable segment) preserves evidence,
provenance, replay, recovery and pending references; it is always
permitted once the segment manifest verifies. Destructive
compaction (dropping records) is permitted ONLY for per-task
invocation timings already summarized into citing aggregates —
never for decisions, assessments, impacts, publications, budget
grants, succession links or segment manifests. A manifest entry
licenses relocation, never deletion: anything without a replayable
archive stays. Historical verification requirements (frozen-run
replay, acceptance re-checks) pin their source segments against
compaction entirely.

## 34.6 History inventory (world-model preparation)

Everything a future world model needs is already recorded; nothing
here authorizes learning it yet:

- Decisions with cited evidence, est. cost, budget constraints and
  kernel disposition: `ecology-decision` records (via
  `record_decision`), plus the SSE/dashboard feed.
- Assessment outcomes and freshness: `retention-assessment` rows
  with verdicts, contexts, cited invocations and evidence revisions.
- Transformations accepted and rejected: member histories,
  assimilation trials, impact records, validation failures.
- Environmental context: scheduled vs operator-forced phase
  transitions, demand distributions per tick (loop-side), budget
  grants and runway histories (PolicyState snapshots).
- Organizational state snapshots: `policy-state-saved` records with
  spend, membership, transitions, actions and flags.

Implemented since: per-decision outcome linkage as temporal
succession (`PolicyState.note_proposal` /
`resolve_pending`, `succession_maps`;
`tests/test_development_policy.py::TestSuccession`). Each record
carries the proposed-step and observed-step membership snapshots
with their delta, labeled `succession-not-causation`: tick
proximity orders events but never attributes causation. Links
persist through `save`/`load` and are journaled (`adr-demo`
`succession` events; observatory `succession` records) by both
coordination loops. Missing and still needed: churn-vs-payoff
joins (proposed in §34.5).

## 34.7 Roadmap

Done: W2 closure, ADR coordination core, unified observatory,
10-minute and 1-hour continuous runs, extended run, quiescence and
lineage instrumentation, executor fail-closes, B38-B43, B44-B48
(trigger trichotomy/taxonomy, implemented lifecycle triggers,
fail-closed executors), B46 expressivity audit, succession
linkage. Pending review: the orthogonal vocabulary in §34.3
(needs approval before any primitive is built), the revised
preregistration draft, and the journal-growth design in §34.5.
The long-duration program (Priority 6) proceeds only after the W3
preregistration is reviewed, frozen and committed. No
confirmatory W3 execution is authorized; no construction-engine,
vocabulary or primitive change ships without review.
