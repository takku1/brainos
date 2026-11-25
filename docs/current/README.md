# BrainOS: A Programmable Architecture for Adaptive Computational Intelligence — README

Substrate-independent specification for composing and developing
computational intelligence (November 2026). An operating system for
intelligence, not one intelligent application: primitives for
constructing, executing, coordinating, modifying, and maintaining
entire intelligent systems. Robotics is Test Track R (first
instantiation), not the architecture; CCCM is the developmental
subsystem (Morphogenesis), not BrainOS itself.

Three adoption layers: Core (how intelligence executes), Plasticity
(what intelligence learns), Morphogenesis (how intelligence is
constructed). The unit of evolution is a computational ability, not
necessarily a neural network.

## Documents

| # | Document | Contents |
|---|----------|----------|
| 01 | [Research Proposal](01-research-proposal.md) | Programmable execution thesis, hypothesis, claims, scope, success criteria |
| 02 | [Formal Architecture](02-formal-architecture.md) | Providers, adapters, readout state, contracts, graphs, slots |
| 03 | [Supervisory Control](03-supervisory-control.md) | Reachability closure, enablement vs authorization vs execution |
| 04 | [Shared Representation](04-shared-representation.md) | Readout integration, provenance, uncertainty, failure modes |
| 05 | [Cross-Provider Learning](05-cross-module-learning.md) | Joint objective, alignment, retention, recoverable plasticity |
| 06 | [Temporal Coordination](06-temporal-coordination.md) | Multi-rate async execution, snapshots, staleness, liveness |
| 07 | [Experimental Validation](07-experimental-validation.md) | Matched conditions, metrics, ablations, robotics track |
| 08 | [Development Roadmap](08-development-roadmap.md) | Canonical implementation sequence, first vertical slice, demos, Experiment 001 |
| 09 | [Cognitive Instruction Architecture](09-cognitive-instruction-architecture.md) | Typed instruction contract, kernel protocol, conformance |
| 10 | [Mechanism Network option](10-mechanism-network.md) | Dependency-aware recurrent factor core as one provider family |
| 11 | [Developmental ecology (CCCM)](11-developmental-ecology.md) | Developmental providers, operations, layers Core/Plasticity/Morphogenesis |
| 12 | [Failure Modes](12-failure-modes-and-mitigations.md) | Risks, contracts, residual risks |
| 13 | [Glossary](13-glossary.md) | Terms, symbols, conventions, rename table |
| 14 | [Game-dev mapping](14-game-dev-mapping.md) | BT/utility/GOAP/ECS/netcode shifted to OUR concepts |
| 15 | [Science mapping](15-science-mapping.md) | World models/sims/provenance/prereg/controls/replication as gates |
| 16 | [Evolution + neuroscience](16-evolution-neuroscience-mapping.md) | Adopted lineage vs rejected relabeling/pop claims |
| 17 | [Capability Specification](17-capability-spec.md) | Functional contracts, substitutability measurement, registry |
| 18 | [Capability Demand](18-capability-demand.md) | Demand-driven nomination, construction order, acquisition |
| 19 | [Organizational Adaptation and World Models](19-organizational-calculus.md) | Transformation experience, scoped outcome prediction, guarded reuse and bounded planning |
| 20 | [Computational Economics](20-computational-economics.md) | Canonical S(N), marginal utility, exploration and retention budgets |
| 21 | [Reference Implementation](21-reference-implementation.md) | Interfaces, types, protocols, L1 tests, dependency rule |
| 22 | [Capability Discovery and Planning](22-capability-discovery.md) | Demand diagnosis, case/model-guided proposals, enabling steps, probes and stopping |
| 23 | [Evaluation Architecture](23-evaluation-architecture.md) | Evaluator families, integrity, evaluation of evaluators |
| 24 | [Transformation Algebra](24-transformation-algebra.md) | Graph-operation primitives, composition, frame rule |
| 25 | [Ecology Dynamics](25-ecology-dynamics.md) | Stability, endogenous opportunities, coevolution research, cycles, sources |
| 26 | [Capability Ontology](26-capability-ontology.md) | Specialization, equivalence, dependency, composition, abstraction |
| 27 | [Candidate Construction](27-candidate-construction.md) | Synthesis, invention boundaries, construction rules, variation, artifact reuse |
| 28 | [Credit Assignment](28-credit-assignment.md) | Marginal contribution, synergy, intervention, coalition attribution |
| 29 | [Dependency & Isolation](29-dependency-interference.md) | Interference classes, closure, isolation levels |
| 30 | [Evaluation Grounding](30-evaluation-grounding.md) | Trust termination, distance-to-grounding |
| 31 | [Requirement Register](31-architectural-audit.md) | Inventory, traceability, queued fixes, closure plan, gates |
| 32 | [Core Semantics (Phase 1B)](32-core-semantics.md) | Task execution, scoped authority, lifecycles, replay, trusted enforcement, crash/effect recovery |

## Document roles and ownership

| Role | Canonical owners |
|---|---|
| Architectural contracts | 02 provider/adapter model; 09 instruction signatures; 17 capability contracts; 21 shared records; 24 transformations; 29 impact semantics; 32 operational protocols |
| Replaceable policies | 03 eligibility implementation; 04 integration; 05 learning/repair; 06 scheduling/transport; 18/22 demand/discovery and 19 organizational prediction/planning; 20 economics; 23/30 evaluation/grounding; 26 ontology; 28 attribution |
| Research hypotheses and experiments | 01 hypotheses; 07 validation; 10 optional provider family; 11/25/27 development, interaction, expansion, construction |
| Rationale and vocabulary | 13 glossary; 14-16 source mappings, which add no independent runtime requirements |
| Work plan and evidence | 08 implementation sequence; 12 failure catalog; 31 requirement/gap register; ../STATUS.md current state |

Organizational world models are replaceable adaptation providers: they learn
scoped consequences of changes and guide short plans, probes or no change.
They add no trusted kernel or opcode, and Core adoption remains independent.
The source proposal is now a [navigation map](../organizational-world-models.md).

Each rule has one owner. Other documents link to it and provide context;
summaries do not create alternate definitions. Conflicting signatures and
protocols require coordinated corrections. Core, Plasticity, and Morphogenesis
remain independently adoptable layers. Research policies become deployable
only through the same publication, evaluation, and resource interfaces.

## Reading order

- Overview: 01 -> 02 -> 09 -> 32.
- Implementation: 21 records -> 32 protocols -> 29 impacts -> 09 signatures
  -> 08 first vertical slice -> 31 open obligations.
- Adaptation: 17 -> 18 -> 19 -> 22 -> 27 sections 27.6-27.7 -> 20 -> 23 -> 07.
- Organizational learning: 19 model/strategy -> 21 section 21.7 records ->
  29 section 29.5 invalidation -> 07 section 7.12 matched experiment.
- Interaction research: 25 sections 25.6-25.9; 14 section 14.1;
  20 section 20.6; 28 section 28.4; 07 section 7.10.
- Controlled expansion: 11 section 11.9 -> 25 section 25.10 -> 07 section 7.11.

## Current status and historical evidence

The canonical current architecture is Docs 01-32. There is no src/ runtime.
tools/ contains structural validators and partial reference models/tests;
their passing results establish only their stated coverage (21 section 21.3).
Independent specification review and runtime conformance remain outstanding.

Historical predecessor evidence from Z:\newbrain: 231 tests and selective
repair at 0.21-0.26x full-retraining cost on corrected error, with retention
failure unresolved. These results are not current-runtime verification.
The docx is a frozen historical artifact; Markdown is canonical. See STATUS
and Doc 31 for current gaps rather than inferring readiness from document count.

Ambitious hypotheses remain active research targets. A proposal records its
mechanism, test, limits, and disposition; it need not already have a positive
experimental result to belong in the architecture's research program.
