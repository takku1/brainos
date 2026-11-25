# 11 — Developmental Ecology (CCCM growth layer, optional)

Status: partial — some requirements are built (Doc 31 register; Doc 21 section 21.0); the rest is specification, not implementation.

## 11.1 Position

CCCM population dynamics are an optional growth layer atop Docs 02–09,
not a replacement. Fixed pretrained models, solvers, controllers, tools,
and mechanism networks remain first-class providers. Trainable developmental units
are one additional provider family. Every birth, split, fusion, and
retirement reuses the same Transactor and manifests (mandatory
transaction checks always; applicable L3 gates per preregistration —
Doc 07 registry, where historical G1–G7 now live).

## 11.2 Construction specifications and trainable units

A reusable construction specification declares architectures, interfaces,
initialization, adaptation rules, variation operators, and limits; it is not
a pretrained solution. A trainable unit is one possible provider instance
with parameters, private recurrent state, neighbors, adaptation rules,
resources, and immutable artifact version. Providers sharing a specification
can specialize differently. Most providers need no trainable internal state.
Doc 27 sections 27.5-27.6 own construction/variation mechanisms.

## 11.3 Competitive ecology

Selection acts on functional niches, not a global accuracy leaderboard.
Directional substitutability s(i→j,c): fraction of j's required behavior
in context c preserved when i replaces j under quality, latency, state,
authority constraints. Asymmetric in general. Utility is a
context-weighted vector (loss, retention, latency, cost, robustness,
unique coverage); keep Pareto alternatives; reserve capacity for rare
critical niches and bounded exploration. Growth triggers (persistent
error/demand/uncertainty) nominate opportunities; compare better routing,
retraining, reuse, then new capacity. One possible optimization
policy (not the canonical definition) is scalar collective fitness
J(G) = E[Ltask] + λC + μR with explicit per-resource caps. The
general evaluation is the vector U(Σ,c) across capability coverage,
quality, retention, resource efficiency, latency, and resilience
(Doc 28): selection depends on context, hard constraints, Pareto
dominance, and explicitly justified trade-offs — never on a single
aggregate score. A specialist must not disappear merely because
another provider scores higher in aggregate.

## 11.4 Assimilation and organization

Preserve acquired abilities, not necessarily carriers. Construct
candidate D by any permitted technique — distillation, weight
averaging, crossover, composition, synthesis — from overlapping
specialists plus grounded outcomes and retention examples; every
technique faces the same validation and acquisition gate, and what
is prohibited is unvalidated acquisition, not any technique.
Recurring pathways may become reusable procedures or composite providers
with their own contracts and preserved dependencies. Promotion optimizes
a path; assimilation constructs a replacement candidate — both use the
same publication infrastructure and economics accounting (canonical model: Doc 20).

Assimilation is defined by functional result, not mechanism: a validated
organizational transformation that preserves required abilities while
reducing cost, complexity, or redundancy, or improving collective
utility. Methods:

| Assimilation method | Result |
|---|---|
| Neural distillation | Smaller learned model |
| Algorithmic composition | Hybrid algorithm |
| Procedural compilation | Optimized executable procedure |
| Symbolic consolidation | Simplified rule system |
| Retrieval consolidation | Improved knowledge index |
| Structural factoring | Shared implementation of common operations |
| Routing consolidation | Efficient specialized execution path |

Distillation is one method among seven, not the definition.
Every method is judged by the same acquisition gate: union-of-parents
contexts, rare cases, state transitions, downstream consumers, vs
best-parent / routed / ensemble / no-change, with rollback on drift.

## 11.5 Metabolism and homeostasis

Group providers by construction-family, contract shape, encoding, and
cadence; preallocated slots, masks, stable ids, batched execution
where the substrate batches (recurrence batching is the neural
instantiation, not the rule). Budget CPU/GPU/VRAM/RAM/comm/storage/
energy separately; reserve critical capacity; count failed candidates in
costs. Hysteresis, cooldowns, evaluation windows, protected floors, and
reclamation only after readers drain prevent oscillation and rare-niche
extinction.

## 11.6 Developmental providers (generalization of trainable units)

CCCM generalizes from developmental cells to developmental providers:
any provider family under the operations below, with neural cells as
one implementation. Neural predictors specializing/competing/distilling;
search algorithms competing across problem classes and composing into
hybrids; reasoning strategies, retrieval configurations, and prompts
competing and consolidating into cheaper paths; behavior policies
competing across environments; predictive mechanisms competing as
explanations — all are the same developmental principle over different
substrates.

| Developmental operation | Generalized meaning |
|---|---|
| Birth | Construct a new candidate provider |
| Differentiation | Develop context-specific competence |
| Mutation | Modify a candidate's implementation or configuration |
| Competition | Compare substitutable capabilities |
| Cooperation | Compose complementary capabilities |
| Assimilation | Consolidate useful behavior into a replacement |
| Reproduction | Instantiate an independent descendant |
| Retirement | Remove unnecessary or inferior capacity |
| Regeneration | Reacquire a lost capability |

Not every provider supports every operation — intrinsic developmental
plasticity is a capability, not a required property. A deterministic
calculator supports no intrinsic operations; it participates
extrinsically through external lifecycle eligibility (retirement,
replacement, composition around it — §11.8). An LLM may be immutable
but replaceable (retirement + birth, no mutation). A trainable unit may support all nine. A procedure
evolves through composition rather than gradient descent. The
capability contract (Doc 02 §2.1) declares which operations each
provider supports; the Transactor admits only declared operations.

## 11.7 Layers of adoption

BrainOS Core (execution, communication, coordination, persistence) may
be adopted alone. BrainOS Plasticity (learning, adaptation,
consolidation, recovery — Doc 05) adds the second layer. BrainOS
Morphogenesis / CCCM (this document: emergence, competition,
cooperation, reorganization, disappearance) is the third. The central
idea becomes intelligence whose computational organization is itself
adaptable, not merely intelligence whose parameters are trainable.
The unit of evolution is a computational ability, not necessarily a
neural network.

## 11.8 Developmental calculus (substrate-independent)

Development operates over the authoritative organizational state
(Doc 24 §24.3), not over the graph alone:

```text
Σ = (G, K, X, E, A, R, M, H)
T: Σ ⇀ Σ′
```

(Graph, contracts + ontology, provider state, evidence, authority,
resources, manifest, history; partial-function notation per Doc 24.)
Graph transformations G_{t+1} = T(G_t, X_t, B_t) — with E_t the edge
set and X_t experience/evidence kept distinct — are the topological
subset: an organization can change without changing its topology
(revising contracts, reallocating resources, updating
implementations, revising ontology, changing evaluation policies,
invalidating evidence), and the calculus covers all of it. Every
developmental operator proposes a candidate organization; the
Transactor admits it only through manifests + L1 conformance +
applicable L3 gates. The operator defines the desired organizational
transformation; the provider determines how to realize it.

| Operation | Neural realization | Algorithmic realization |
|---|---|---|
| Birth | Initialize network | Instantiate candidate algorithm |
| Mutation | Parameter or topology change | Configuration or code revision |
| Differentiation | Contextual training | Contextual optimization |
| Cooperation | Learned communication | Function composition |
| Assimilation | Knowledge distillation | Hybrid algorithm or compiled procedure |
| Regeneration | Retraining | Reconstructing a lost procedure |

This calculus is independent of gradient descent: no operator above
requires differentiable parameters. Internal plasticity (a provider
changing itself) and external development (replacement, composition,
retirement around an unchanged provider) are distinct paths to the
same graph transformation — a deterministic calculator with no
internal plasticity still participates via external replacement,
composition, and retirement.

## 11.9 Controlled capacity expansion (research extension)

Treat expansion as a regulated allocation of computational capacity, with
three distinct reasons: throughput replication, functional specialization,
and recovery of lost service. Replicas may improve throughput without
adding competence or independent failure protection. New instances inherit
construction records, not certification or authority. No new lifecycle
instruction is introduced; existing construction, validation, allocation,
and publication semantics apply.

| Proposed mechanism | Computational meaning | Evidence required before expansion |
|---|---|---|
| Local saturation feedback | Inhibit duplication where eligible capacity already meets a context's demand; account for contention and downstream bottlenecks. | Measured service deficit and a probe that extra instances improve service rather than amplify congestion. |
| Separate rate and role controls | Decide how much capacity to add separately from which contexts it should serve. | Throughput gain versus new functional coverage measured independently. |
| Staged expansion | Use a bounded temporary worker pool before maintaining persistent specialized providers. | Explicit pool quota, trial horizon, promotion criteria, and cleanup disposition. |
| Reversible inactivity | Keep a validated implementation available without allocating active execution capacity. | Carrying costs, evidence freshness, and reactivation checks; an inactive artifact is not an active authorized instance. |
| Deficit-driven restoration | Restore required coverage after failure or removal. | Independently measured service loss, dependency diagnosis, and a valid replacement plan; a retirement event alone is insufficient. |
| Population-level continuity | Preserve coverage while individual instances are replaced. | Retention and failure-domain checks across the pool; equivalent instances may still share failure causes. |

Expansion proposals record reason, target context, demand window, parent
versions, intended role, resource reservation, maximum concurrent instances,
trial horizon, stop conditions, and rollback. These are experimental proposal
records, not additions to the typed instruction schemas. A descendant can
propose further expansion only through normal demand and budget gates;
construction ancestry grants no recursive allocation privilege.

Doc 25 section 25.10 owns the feedback model and research sources;
Doc 07 section 7.11 owns the discriminating experiment. Construction
mechanisms remain in Doc 27 and all costs remain in Doc 20.

## 11.10 Experience-guided development

Developmental operators generate changes; Doc 19's ordinary prediction/planning
providers learn when those changes may help. Existing ecological controls and
construction specifications remain available without a model. Positive/negative
intervention memory can guide composition, specialization, capacity and repair;
actual admission, prefix retention, budgets and publication remain independently
enforced. Cases and models compete against symbolic planning; prediction is
neither acquisition nor permission. Doc 07 section 7.12 isolates this strategy
before combining it with interaction/expansion mechanisms.
