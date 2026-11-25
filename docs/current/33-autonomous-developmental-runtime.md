# 33 — Autonomous Developmental Runtime (ADR)

Status: specified — design proposal under review. No new developmental
semantics are implemented here, and none may be implemented until this
design is reviewed (Doc 08 rule 4 governs workstream entry; this
document is the entry gate for autonomous behavior).

An integration milestone using the existing Core, Plasticity and
Morphogenesis architecture — not a new architectural subsystem, not a new
authority, not a new layer. The question it answers: what happens when
the mechanisms we have already built and tested run together,
continuously, under their own developing policy instead of a script?

Two tracks proceed in parallel. Track A (scientific validation) continues
the frozen confirmatory program unchanged: B31–B37 first, then re-freeze,
then execution. Track B (this document) builds the persistent integration
environment. Track B never weakens a frozen preregistration and never
borrows confirmatory results; feasibility probes are disclosed and kept
separate, as in W2.

## 33.0 Scope and non-goals

ADR coordinates implemented mechanisms; it does not invent them. Every
transformation below runs through an already-built, already-tested gate.
What is new here is the *coordination*: a replaceable developmental
policy that observes organizational state and proposes the next
transformation, plus the homeostatic regulation, persistent environment
and live observatory that make continuous development observable and safe.

Non-goals for ADR: new permit types, new budget dimensions, new
authority rules, neural self-modification of the policy, arbitrary code
generation, uncontrolled provider spawning, developmental self-funding
(impossible by construction — see §33.7), and any stability theorem.
Stability results belong to W3; ADR uses heuristic, declared parameters
and says so (§33.8).

## 33.1 Implementation inventory

"Auto-triggered" means some running code path invokes the mechanism on
observed organizational conditions without a human-written script step.
Nothing below qualifies today.

| Mechanism | State | Entry points | Tests | Register |
|---|---|---|---|---|
| Task execution | implemented, callable; scripted only | `src/brainos/execution.py::TaskExecutor.run_task` | `tests/test_core.py`, `tests/test_runners.py` | R-09-ACT, R-32-03 |
| External execution | implemented, callable; scripted only | `src/brainos/runner.py::ExternalDispatcher`, `mock_adapter.py`, `qwen_adapter.py` | `tests/test_external.py::ExternalExecution` | R-02-14 |
| External registration | implemented, callable | `src/brainos/registry.py::ProviderRegistry.register_external` | `tests/test_external.py::ExternalRegistration` | R-02-14 |
| k-of-n admission | implemented, callable | `src/brainos/transactor.py::validate_nondeterministic`, `population.py::admit` | `tests/test_external.py::NondeterministicAdmission` | R-02-15 |
| Candidate construction | implemented, callable; scripted only | `src/brainos/development.py::CompositionSearch.acquire` | `tests/test_cumulative.py` | R-24-COMPOSE, R-27-03 |
| Contextual selection | implemented, callable; scripted only | `src/brainos/ecology.py::EcologyPolicy.select`, `EcologyService.choose` | `tests/test_ecology.py`, `tests/test_retention.py::RecoverableEcology` | R-25-05 |
| Retention assessment | implemented, callable; scripted only | `src/brainos/population.py::assess` (kernel records only) | `tests/test_retention.py::GroundedRetirement` | R-25-04 |
| Dormancy / wake / retire / regenerate | implemented, callable; scripted only | `population.py::make_dormant/wake/retire/restore`, `ecology.py::EcologyService` wrappers | `tests/test_retention.py::ProviderLifecycle` | R-25-04 |
| Assimilation | implemented, callable; scripted only | `src/brainos/assimilation.py::AssimilationSearch.*`, `transactor.py::commit_assimilation` (B21–B25 enforced) | `tests/test_assimilation.py` | R-24-ASSIMILATE-02 |
| Budgets and funding | implemented; operator-created only | `src/brainos/resources.py::ResourceLedger` | `tests/test_retention.py::FundingCeiling` | R-20-06, R-21-05 |
| Restricted developmental surface | implemented | `src/brainos/devcontext.py::development_context` (no ledger, store, runtime, funding) | `tests/test_retention.py::DevelopmentBoundary` | R-21-10 |
| Emergence meter, capability test, net-value ledger | implemented; observation only | `src/brainos/emergence.py::measure`, `::organizational_verdict`, `::net_value` | `tests/test_emergence.py` | R-25-06, R-25-07, R-20-07 |
| Impact records and dependency closure | implemented; scripted only | `src/brainos/registry.py::record_impact`, `src/brainos/closure.py` | `tests/test_cumulative.py::ClosureConformance` | R-29-01, R-29-03 |
| Demand generation | absent from kernel and `src/` | experiment scripts own their streams (`tools/run_continuous.py::gen_stream`, `tools/run_heterogeneous.py::gen_stream`) | runners (not unit-tested) | — (runner discipline: R-07-10) |
| Persistent environment | absent | X4/W2 runs use per-seed temporary stores and exit | — | — |
| Long-lived process operation | untested | crash recovery is tested (`tests/test_crash_recovery.py`); continuous operation is not | partial (R-32-09 covers restart, not tenure) | R-32-09 |
| Homeostatic regulation | specified only (§33.4; no code, no rows) | — | — | maps to R-25-05, R-20-02, R-32-03 |
| Organizational world models | specified only | Doc 19 §19.10 decision; no implementation | — | R-19-01-M..R-19-04-M, R-32-10 |
| Live observatory | absent | `docs/visual/x4-dashboard.html` is a static frozen-results viewer (untracked; provenance unknown; no live data path) | — | — |
| Live clock demonstration | not found in this repository (`tools/`, `docs/`, `src/` searched for clock/observatory/dashboard/live with no in-repo result) | — | — | — |

Every row whose state is "scripted only" is integrated *by schedule*,
not by condition: X4 runs assimilation and transitions at phase ends and
wakes at P4-start; the W2 runner admits, serves and measures in fixed
order. No mechanism anywhere in `src/` invokes another mechanism on
observed conditions. That absence is the ADR gap, stated plainly.

## 33.2 Gap analysis

1. **Implemented and independently callable.** Everything in the
   inventory table: each mechanism runs alone through its public entry
   point with committed tests.
2. **Integrated into continuous execution.** Nothing, except by
   hand-written scripts. `tools/run_continuous.py::run_developing` is the
   closest existing thing to continuous orchestration and it is a fixed
   schedule: serve, measure, assimilate, transition, maintain, repeat.
   Its phase boundaries are stream positions, not organizational
   conditions; its wakes happen because the script says "P4", not
   because retention evidence changed.
3. **Automatically triggered by organizational conditions.** Nothing.
   This is the single structural gap ADR closes, and it closes it with
   a replaceable policy (§33.3), not with new mechanism authority.
4. **Dependent on manually scripted orchestration.** All of §33.1's
   "scripted only" rows, plus demand generation, budgeting per phase,
   and every experiment runner in `tools/`.
5. **Specified but not implemented.** Homeostatic regulation (§33.4 is
   its first specification), organizational world models (Doc 19),
   the W2 L2/L3 demonstration (R-07-12, frozen but unexecuted), and a
   live observatory (§33.6 specifies it; only a static viewer exists).

## 33.3 Autonomous developmental coordination

A replaceable developmental policy observes organizational state through
the restricted development context and returns one decision per
coordination step. The policy proposes; it never authorizes. Every
mutating action below executes only through its existing gate, which
re-verifies everything at execution time.

| Decision | Existing mechanism it invokes | Gate that actually authorizes |
|---|---|---|
| continue | `TaskExecutor.run_task` on the selected member | task permits, budget holds, bindings |
| recruit | `EcologyService.wake` → `population.wake` | re-validation when stale (R-25-04) |
| investigate | `population.assess` on cited invocations (evidence only) | assessment is computed, never trusted (§21.12) |
| construct | `CompositionSearch.acquire` with operator-provided budgets | admission validation on contract cases |
| evaluate-candidate | `AssimilationSearch.evaluate` (records trials) | union gate + selection record (B21–B25) |
| reorganize | new compositions plus `retire`/`make_dormant` (graph-rewrite primitives are not exposed to developmental code) | same gates as construct and retire |
| assimilate | `commit_assimilation` via the restricted context | B21 selection binding, lineage, atomic CAS |
| suspend / retire | `make_dormant` / `retire` via the restricted context | verified `redundant`/`not-best` assessments only |
| regenerate | `regenerate` via the restricted context | fresh validation on restore |
| defer / noop | nothing; the reason is recorded as a decision with evidence | — (first-class abstention, §33.4) |

The policy itself runs inside the restricted development context
(Doc 21 §21.12, R-21-10): it can read kernel records through the
whitelisted kinds, spend from budgets it was given, and request
lifecycle transitions the population independently verifies. It cannot
mint funding, touch the raw store, stage outside candidates, or reach
the transactor. Policy replacement is an operator act, recorded with
the replaced version pinned — policies do not self-modify under ADR.
No action, however proposed, receives authority merely because the
policy proposed it: the table's third column is the complete list of
what makes anything happen.

## 33.4 Homeostatic regulation

Viability is a set of measured variables with declared bands, not a
mood. Every variable below derives from kernel records or the W1
instruments; thresholds are declared per deployment, re-estimated from
meter history (evidence-dependent), and invalidated on regime change.
Entering a band and leaving it use different thresholds (hysteresis);
transitions start cooldowns; `defer`/`noop` with recorded reasons are
always available and are never counted as failures.

| Viability variable | Source | Band form | Breaching response |
|---|---|---|---|
| Capability coverage | member rows; meter C | per-capability floor | investigate → construct or recruit |
| Competence retention | retention assessments; meter L | floor on near-optimal coverage | wake, re-assess, regenerate |
| Budget runway | budgets/holdings spend vs capacity | floor in periods at current burn | defer development; never mint |
| Maintenance burden | upkeep charges as share of spend | ceiling | retire/dormant per verified verdicts |
| Development spend share | construction+validation+assessment vs total | band with hysteresis | cool down probing; never forced |
| Population size | member counts | soft bounds | tighten nomination (Doc 25 §25.1 bloat rule) |
| Organizational churn | transitions per window (journal) | ceiling + cooldown | lengthen cooldowns; review nomination (Doc 25 §25.1 thrashing rule) |
| Recovery readiness | freshness of last successful wake/regeneration evidence | floor | probe recovery paths (assessment only) |

Periodic *observation* is permitted and expected (the meter runs on a
cadence). Periodic *forced restructuring* is forbidden: no transition
happens without a violated viability condition *and* a passing gate.
The X4 dormancy-on-thin-samples episode is the standing cautionary
example — assessments need declared minimum evidence before they move
members, and the minimum itself is a declared, reviewable parameter.

## 33.5 Persistent environment

One durable organization, one durable store, many environmental regimes.
The environment presents, at minimum: stable demand, recurring demand,
novel demand, distribution drift, resource scarcity (finite budgets with
an explicit operator top-up policy — top-up is an operator transfer,
never developmental minting), provider disruption (impacts, deaths,
timeouts), and recovery periods. Environmental events may be fully
scripted for reproducibility; the schedule format mirrors the X4
generators. Organizational responses must arise from the developmental
policy and observed evidence alone — a response that only a script
branch can explain is a failed run, not an adaptation.

Persistence requirements: organizational state survives process restarts
on one durable store (crash recovery exists and is tested; long-lived
tenure is the untested part and must be exercised before any
equilibrium claim). Budgets are finite by construction; scarcity is a
first-class regime, not an error path.

## 33.6 Live observatory

`docs/visual/x4-dashboard.html` (untracked, provenance unknown at
drafting time) shows a reasonable *layout* for an observatory. Whatever
its data path turns out to be, the ADR observatory contract is: panels
derived from live kernel records through a read-only projector, as
follows:

- Capability population and dependency graph (member rows; closure).
- Active, dormant, candidate and archived providers, with blocking
  impacts marked (member rows; `member-admitted/dormant/woke/retired`
  journal events).
- Competence and specialization (invocation records; retention
  assessments; meter D/L).
- Resource consumption and remaining budgets (holdings, budgets, meter
  R; runway derived, labeled estimated).
- Developmental decisions and their justifications (policy decision log
  with cited evidence — the policy must write its reasons as records).
- Accepted and rejected transformations with trial records
  (assimilation trials, validation outcomes).
- Organizational value (NOV ledger; meter R).
- Homeostatic variables with their bands (§33.4).
- Recovery and retention (member histories; wake/regeneration outcomes).

The projector is a read-only view over the store: it takes no authority,
needs no permits, stages nothing and charges nothing. Because the store
takes a single-writer ownership lock, the projector runs in the runtime
process and publishes snapshots (records plus journal positions) that
the dashboard polls; it never blocks the kernel, and a dead dashboard
never affects the organization. Every displayed number cites its record
source. Three epistemic kinds are visually distinct and never mixed:
**observed** (kernel records), **estimated** (meter/verdict/NOV
outputs), **predicted** (world-model outputs — absent until Doc 19
mechanisms exist, so no prediction panels until then). Static playback
of frozen results stays available but must be labeled as frozen, the way
the current file's header already does.

## 33.7 Safety and experimental separation

The autonomous environment and frozen confirmatory experiments never
share a store or a process. ADR runs under explicit ceilings: operator
budgets (no developmental funding path exists — `DevelopmentBoundary`
tests), bounded nomination and draw budgets
(`max_candidates`, `DRAW_BUDGET`), per-draw and per-task timeouts, and
the kernel's existing cancellation, timeout and refusal paths. Shutdown
is drain-then-close on a durable store; restart replays through the
tested recovery coordinator. Long-lived tenure, bounded task queues and
adversarial-provider behavior are open gaps, stated here rather than
assumed away.

Forbidden under ADR, without a separate reviewed design: an
unrestricted LLM controller (the policy is versioned code running
inside the restricted context, never a prompted model with ambient
authority), arbitrary code generation (providers arrive only via the
trusted catalogue, validated composition, or operator-registered
external endpoints), uncontrolled provider spawning (every execution is
a budgeted task), and developmental self-funding. The developmental
policy stays replaceable and stays under the kernel: replacement is an
operator act, and the kernel verifies every lifecycle, publication and
recovery request exactly as it does today.

## 33.8 W3 overlap map

ADR needs from W3: stability results that turn today's heuristic
hysteresis bands and cooldowns into derived control parameters, and
coverage conditions under which the coordination law holds (the control
law's assumptions are the coordinator's confidence). ADR stands alone
without them: the policy interface, the observatory, the environment,
the safety envelope and every mechanism integration in §33.1 work with
declared, reviewable parameters. ADR prejudges nothing in W3: no
convergence is asserted, no point is called an equilibrium, and
"development slowed" is reported as measured churn decline, never as
proof of stability.

## 33.9 Open questions for review

1. Is this document's `specified` status and Doc 33 placement accepted,
   or should the ADR design live elsewhere?
2. Candidate register rows are deliberately *not* created yet: R-25-08
   (homeostatic viability variables and bands), R-02-16 (read-only
   runtime projector with no authority), R-07-13 (persistent
   developmental environment with scripted regimes). Create on approval?
3. `docs/visual/x4-dashboard.html` is untracked with unknown provenance.
   Adopt it (track + rewire to the §33.6 projector), rewrite it, or
   leave it alone?
4. A parallel effort appeared in this workspace during drafting:
   `live/server.py` (described by its own `OBSERVATORY-DESIGN.md` header
   as "the live clock"), plus `docs/visual/x4-dashboard.html`. Both are
   untracked, both postdate the last commit, and neither was inspected
   beyond headers for this design. If that effort is the live clock,
   §33.6's baseline should be it rather than the static X4 dashboard —
   and the two designs (this document and `live/OBSERVATORY-DESIGN.md`,
   which converge on viability regions and policy-as-proposal) need
   explicit reconciliation, not parallel evolution.
5. Are the §33.4 viability variables the right set, and is "no periodic
   forced restructuring" the right hard rule, or should named regimes
   be allowed scheduled consolidation windows?

## 33.10 Review resolutions (2026-11-25)

1. Placement approved: this document is the canonical ADR integration
   specification; status stays `specified`. ADR is an integration
   milestone, not a fourth architectural layer or an independent
   runtime. W3 keeps formal stability results.
2. Rows created on approval, all `specified` at creation: R-25-08
   (§33.4 bands), R-02-16 (§33.6 projector), R-07-13 (§33.5
   environment). R-25-08 and R-07-13 moved to `partial` with the
   coordination core (`src/brainos/development_policy.py`: declared
   bands, evidence-grounded observation, replaceable policy,
   decision journaling) and its tests; R-02-16 stays `specified`
   (no projector artifact built). No new row is marked `implemented`.
3. `docs/visual/x4-dashboard.html` reviewed: static concept mockup with
   illustrative values, no runtime data path. It stays untracked and is
   not adopted as evidence; only its layout may inform the §33.6
   projector. The parallel effort's own design doc agrees illustrative
   values must never ship (§6 of `live/OBSERVATORY-DESIGN.md`).
4. Reconciled read-only 2026-11-25: `live/server.py` is adopted as the
   ADR observatory baseline; no competing server or runtime is
   created. Alignments: existing kernel mechanisms only, decisions
   journaled (including suspensions), bounded development, no LLM
   controller, no codegen, no self-funding, viability from kernel
   records. Gaps recorded for bounded implementation: the policy is
   hardcoded server logic, not a replaceable artifact under the
   restricted context (ADR-3); forced-vs-scheduled phase transitions
   are indistinguishable in the journal; bands are inline constants,
   not declared parameters (ADR-5); the store is wiped on every start
   (`unlink`), so restart recovery is untested (ADR-1/ADR-7);
   dormancy/wake/retire/regenerate/assimilation are not exercised
   (ADR-4); churn-vs-payoff is not computed (ADR-2/ADR-5). The
   `live/OBSERVATORY-DESIGN.md` §7 fencing ("no edits to
   `docs/current/` or the register") is superseded for R-25-08,
   R-02-16 and R-07-13 by explicit authorization, and otherwise
   respected. `live/state/` databases and lock files were not touched;
   the port-8137 server was observed live and left running.
5. Standing rule kept: periodic observation permitted, periodic forced
   restructuring forbidden. The §33.4 variable set stands for the
   bounded implementation; evidence-dependent re-estimation belongs to
   W3, not ADR.
