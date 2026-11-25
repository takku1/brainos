# 08 — Development Roadmap (three layers, four demos)

Status: partial — some requirements are built (Doc 31 register; Doc 21 section 21.0); the rest is specification, not implementation.

## The three layers

- BrainOS Core: arbitrary abilities execute, communicate, coordinate,
  persist (Docs 02, 03, 04, 06, 09).
- BrainOS Plasticity: abilities learn, adapt, consolidate, recover
  (Doc 05 + Doc 09 LEARN/VALIDATE/CONSOLIDATE/FORK).
- BrainOS Morphogenesis / CCCM: abilities emerge, compete, cooperate,
  reorganize, disappear (Doc 11 + developmental instructions).

Adopt Core alone, Core+Plasticity, or all three. Predecessor evidence is
summarized in README; the current plan below requires fresh runtime evidence.

## Four early demos (generality evidence, not product)

A Heterogeneous intelligence: LLM + retrieval + deterministic solver +
persistent memory through one instruction contract. Demonstrates
composition (H1).
B Developmental intelligence: population of trainable recurrent
micro-models; differentiation, competition, assimilation (H3).
C Embodied intelligence: perception + prediction + closed-loop
controller; async execution and resource isolation (H2).
D Algorithmic intelligence: competing search strategies and composable
procedures with no neural learning (H3 without gradient descent;
plasticity as capability).

If all four run through the same instruction contracts, provider
interfaces, runtime, and L1 validation, generality is evidenced. If
they need four different kernels, the architecture has not
generalized — report it as a fail.

## Milestones and executable sequence (canonical plan)

How work proceeds so that documents and code cannot drift (Doc 31 section 31.12):
1. A workstream begins with a design note in its owning document and register
   rows whose status is `specified`.
2. Code lands together with tests and a traceability entry that moves those
   rows to `partial` or `implemented`; `tools/check_traceability.py` must pass.
3. Any empirical claim needs a preregistration that is committed and pushed
   before the run. Results are committed separately and never edited.
4. A workstream closes by synchronizing `docs/STATUS.md` (phase, focus,
   register-derived counts, decisions, limitations, and the
   implementation-vs-validation distinction); the same gate verifies the
   status file, so a stale STATUS.md is drift.

Historical phases 1A-3B and M1-M3 are summarized by their evidence. Doc 31 holds
the obligations; this table holds the order.

| Delivered | Evidence |
|---|---|
| Single-authority Core: durable ledger, staged CAS publication, scoped authority, effect gateway, task executor, crash recovery | R-09-04, R-09-COMMIT, R-32-02..09; tests/test_core.py, tests/test_crash_recovery.py |
| Corrective passes B01-B20 | docs/results/2026-11-25T043902Z, -T-ecology, -T-retention |
| Typed fabric, cumulative composition, populations, lifecycle | R-24-COMPOSE, R-17-01, R-25-04; X1, X1b |
| Bounded ecology and retention study | X2, X2b, X2c (5 of 6 hypotheses passed; adaptation failed) |
| Bounded assimilation | R-24-ASSIMILATE-02; X3 (safety held; acceptance rule unsound; not economical) |
| Drift control | R-31-01; tools/check_traceability.py |

| Workstream | Goal | Entry | Exit evidence | State |
|---|---|---|---|---|
| W0 Integrity | Keep docs and code in lockstep. Correct the X3 gate (full nomination cost, early stop, confidence-bounded tolerance, declared internal state). Carry the X2c open items: recruitment of dormant specialists, incremental assessment, kernel overhead, adaptation latency | — | Drift check in acceptance; GateCorrections and DecisionBoundary tests (B21-B25, Doc 21 section 21.14); X3b preregistered before any new assimilation claim | complete, except X3b: X4 produced zero admissible nominations, so live gate enforcement is untested and carried forward |
| W1 Emergence meter and continuous ecosystem | Instrument z_t and the organizational-capability test (25 section 25.13); net organizational value (20 section 20.9); one persistent organization running every mechanism (07 section 7.17, X4) | W0 | R-25-06 and R-25-07 implemented with positive and negative controls; R-20-07 ledger; X4 preregistered and pushed, then run per seed | implemented and exercised in X4 (meter series, verdicts, NOV recorded). The meter exists; resilient emergent competence is not demonstrated |
| W2 Real-ecosystem adapter | One external provider family (for example a local LLM) behind the existing contracts, outside the standard-library kernel, with nondeterministic validation. Staging: `src/models/` holds the frozen checkpoints (Qwen3-0.6B, closed-loop motor policy) behind slot contracts; payloads git-ignored, manifest tracked | W1 | Adapter design note first (contracts, authority, accounting, acceptance criteria), then adapter process; validation that handles nondeterminism; semantic-commensurability gaps (R-02-13) measured rather than declared | active: boundary, registration, execution, k-of-n validation and heterogeneous feasibility implemented and tested (R-02-14, R-02-15); B31-B37 corrected with Amendment-1, clearance corrections applied, confirmatory executed in a pinned worktree — H1-H5 pass on seeds 21-23, verdict redundant, results committed (f950f91). Track B (ADR, Doc 33; R-25-08/R-07-13 partial, R-02-16 specified) proceeds under experimental isolation with a demonstrated disturbance-recovery arc on a separate store |
| W3 Stability of self-modification | Model learn → validate → commit → rebind as a control loop; state assumptions; prove bounded churn and no acquisition/retirement oscillation under them; test against X2c-style churn | W1 | Written result with assumptions; preregistered test; register rows for Doc 25 section 25.5 | specified |
| W4 Mechanism design | Strategic providers: bonded claims, proper scoring of reported cost and confidence, calibration-based eligibility, collusion detection | W1, W3 | Adversarial providers in the catalogue; preregistered strategic-provider experiment; Doc 20 section 20.6 made normative | specified |
| W5 Kernel as protocol | Signed claims and attestations across authorities; two-authority federation; Byzantine threat model | W4, design review | Design note reviewed before code; protocol tests with an adversarial peer; R-03-06 and R-32-02 revisited | specified |
| W6 Governance and oversight | Gate parameters learned under evidence discipline; performativity (self-impact) terms on validity; human-oversight bandwidth and escalation model | W3, W5 | Bounded meta-adaptation with grounded evaluation (R-12-F18); oversight-load measurements | specified |
| W7 Publication arc | Consolidate into three papers (Core semantics with proofs and a real demo; mechanism/economics with strategic experiments; morphogenesis results); package the preregistration machinery as a reusable standard | W2, W4 | Drafts whose claims are all traceable to register rows with evidence | specified |

The order is deliberate. W1 gives every later experiment a dependent variable,
and W3's loop model grounds W4/W5 design, so the protocol kernel (W5) is not
built before its threat and stability assumptions are stated.

## Repository structure (adopted direction)

```
brainos/
├── src/brainos/
│   ├── contracts/ instructions/ kernel/ runtime/ scheduler/
│   ├── capabilities/ fabric/ providers/ representations/ memory/
│   ├── learning/ development/
│   │   ├── operators/ specifications/ ecology/ competition/ cooperation/
│   │   ├── assimilation/ regeneration/
│   ├── resources/ validation/ persistence/
├── implementations/
│   ├── neural/ symbolic/ language/ algorithmic/ external/
├── experiments/
│   ├── integration/ learning/ development/ retention/ recovery/
├── applications/
│   ├── robotics/ assistants/ games/ science/
├── conformance/ benchmarks/ tests/ docs/
```

CCCM is a developmental framework within BrainOS (src/brainos/
development/), not the repository. Applications demonstrate BrainOS;
they never define it. Critical dependency rule: src/brainos/ must not
depend on any particular implementation or application — no required
PyTorch, CUDA, LLM API, physics simulator, or embedding model in core.
Individual providers carry those dependencies; a generalized core
wearing framework-specific dependencies is a costume, not an
architecture.

## Experiment 001: heterogeneous computational ecology (first experiment)

Deliberately heterogeneous — no neural majority. Environment: mixed
prediction, classification, search, and mathematical tasks. Providers:
linear predictor (statistical), decision tree (algorithmic), small MLP
(neural), rule engine (symbolic), nearest neighbor (memory-based),
search solver (procedural) — all through identical capability,
execution, and L1 validation contracts, under the developmental
ecology (evaluate → specialize → compete → compose → consolidate →
retire). Small cheap providers first: thousands of developmental runs
without hour-long training. Then harder environmental conditions.
Stages: (1) identical-contract execution; (2) demand-driven
specialization; (3) competition under fixed budget; (4) composition
discovery; (5) cost-reducing assimilation without capability loss;
(6) shifting task distributions; (7) regeneration of lost function;
(8) all while preserving unrelated abilities. Compare vs fixed
populations, conventional routing, standard ensembles, conventional
adaptive algorithms. This tests the generalization directly;
starting with 32 recurrent neural cells would not. Discovery follows
Doc 22, evaluation (including evaluator integrity) follows Doc 23,
transformations compose per Doc 24, population dynamics are monitored
per Doc 25, and every acquisition is costed per Doc 20. Arm 0
(non-neural control track): run the full stage sequence with
immutable deterministic components only — no trainable weights
anywhere. Organizational learning, competition, assimilation, and
regeneration demonstrated here are the strongest evidence the
abstraction holds independently of neural learning. Measurement
interfaces (prepared in Phase 1B, executed in Phase 5): fixed
provider set with frozen implementations (sorting, search, math
solvers, planning, rules, statistics); baselines — (a) static
provider selection, (b) conventional adaptive algorithm selection,
(c) portfolio-based execution, (d) BrainOS organizational adaptation
— all under matched resource budgets; primary metric is functional
improvement per resource unit vs the best baseline; controls
preregistered per Doc 07 L3 (matched draws; family-appropriate
evidence — no universal seed counts).

## Standing constraints

No monolith-as-brain. Supervisor stays authoritative over
irreversible action. Falsifiability carries over: matched controls,
preserved failures, no retuning into a pass. No release number is
assigned to CCCM; each phase is contingent on evidence.
