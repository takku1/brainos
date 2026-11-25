# 08 — Development Roadmap (three layers, four demos)

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

Historical M1-M3 describe predecessor work only; they do not mark this runtime
implemented. Current phases map to milestones as follows. Doc 31 tracks
obligations/evidence against this plan rather than maintaining another roadmap.

| Phase | Deliverable / milestone | Exit evidence |
|---|---|---|
| 1A | Contract consistency and normative inventory | No known signature/lifecycle conflicts; independently reviewed register |
| 1B | Core protocols, records, and reference models | Defined task/permit/recovery/resource semantics; reference regressions; remaining runtime tests explicitly listed |
| 2 / M4 | Minimal single-authority runtime | Durable ledger/registry -> staged CAS publication -> scoped authority/effect gateway -> bounded task executor -> process/resource enforcement; L1 against actual runtime plus crash/negative tests |
| 3A | Developmental executable semantics | Impact actions, construction operators, attribution and acquisition policies tied to executable checks |
| 3B / M5 | Typed construction and reusable abstractions | Establish flat search/memoization and intervention traces; then test parameterized abstractions against static macros (07 section 7.13) with expanded primitive bounds |
| 4 / M6 | Repair, assimilation, and recovery | Fault injection, union-of-context validation, capability restoration, and retained failures |
| 5 / M7 | Experience-guided organization and broader experiments | Guarded cases, learned forecasts on a fixed library (07 section 7.12), then independent-factor combination (7.16); test inference/repertoire separately (7.14-7.15) |
| 6 | Qualified release | Reproducible build, requirement traceability, deployment limits, no blocking defects for declared profile |

Phase numbers identify work packages, not automatic authorization or a claim
that a gate passed. Independent review remains outstanding. Perform a narrow
closest-systems prior-art screen before substantial developmental engineering;
extend it before scientific novelty claims. Construction prototypes are
allowed as bounded experiments without pretending the production kernel exists.

First vertical slice: handwritten task -> deterministic provider -> scoped
permit -> recorded result -> simulated idempotent effect -> restart recovery
-> one validated provider replacement. Prove this path before scaling provider
families, distributed authority, or learned discovery. Expand Experiment 001's
full task mixture after this smaller slice works through the same interfaces.

Next adaptation slice: pin a transformation record schema (21 section 21.7),
collect assigned intervention outcomes, and build competent typed symbolic search
with memoization. The selected next construction extension is parameterized
abstraction learning (27 section 27.8). Establish exact guarded case retrieval,
then test richer outcome models with a fixed library. Combine only under Doc
07 section 7.16's independent-factor controls. Collective inference and repertoire
retention are task-specific policies in this same framework, not new kernels.

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
