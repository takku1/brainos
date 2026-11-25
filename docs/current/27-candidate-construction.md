# 27 — Candidate Construction and Computational Synthesis

Status: partial — some requirements are built (Doc 31 register; Doc 21 section 21.0); the rest is specification, not implementation.

Doc 22 decides WHAT to build; this document specifies HOW candidates
come into existence. Construction is a provider family of its own:
synthesis strategies compete under the same contracts as everything
else. The four invention levels are distinct obligations:

1. Selection: choose among available algorithms (search the registry).
2. Optimization: tune an existing algorithm (configure/revise).
3. Composition: wire existing providers into a new composite
   (Doc 19 COMPOSE — no new primitive needed).
4. Invention: produce an implementation unavailable relative to a
   stated reference boundary (table below) — "previously
   unavailable" is meaningless without one.

| Reference boundary | What it establishes |
|---|---|
| Current organization | New to this installation |
| Provider library | Not previously available in its library |
| Construction grammar | New construction within a declared search space |
| External reference corpus | Not found in the specified reference set |
| Scientific prior art | Potential scientific novelty, requiring investigation |

An ordinary sorting algorithm from a synthesis provider is invention
only against boundaries it actually crosses; without a boundary, it
is selection or composition mislabeled. Every invention claim names
its boundary; scientific novelty additionally requires the master
directive's prior-art program (Phase 5), not a boundary table alone.

## 27.1 Synthesis interface

A synthesis provider implements: inputs (nomination contract per
Doc 22 + construction budget), output (candidate provider +
construction record: method, parents, data, recipes, randomness),
preconditions (budget held, nomination valid), failure semantics
(explicit non-construction with reason — running out of budget is a
finding). Supported synthesis methods include program synthesis,
architecture search, symbolic induction, evolutionary search, and
learned construction — the interface prescribes none. A synthesis
strategy that cannot emit its construction record is ineligible:
unrecorded provenance cannot enter the repair system (Doc 05).

## 27.2 Obligations

Level 4 (invention) is explicitly open research: a fair trial
(quarantine, validation, acquisition gate) is guaranteed only
conditional on eligibility, available resources, and validation
policy — an unconditional guarantee would let synthesis spend the
organization into the ground. Every acquisition records which
level produced it; a portfolio of only levels 1–3 is reported as
selection/optimization/composition, never as invention.

## 27.3 Candidate artifacts and execution discipline

Artifact types: provider implementation + construction record
(method, parents, data, recipes, randomness, expenditure) +
validation plan + failure log; non-construction (budget exhausted,
search space empty, validation infeasible) is a first-class outcome
with reason recorded. Synthesis providers reserve resources up
front (Doc 20), execute candidates under isolation levels per
Doc 29 §29.3, support cancellation with partial-artifact
disposition declared, and must reproduce their construction on
demand (same inputs + recorded randomness → same candidate, or
the nondeterminism is declared and bounded). Generated
implementations enter only through kernel validation like any
provider — synthesis confers no authority, and synthesized code is
never executed with unrestricted privileges (threat model: Doc 12
extended in Phase 2).

## 27.4 Variation and stepping-stone reuse (research extension)

Ecological pressure changes candidate usefulness, not construction ability.
Trials of Doc 25's mechanisms name the actual generator, its reachable
search space, and unsupported changes: configuration search, typed
composition, program synthesis, evolutionary operators, training, or
another declared method.

A bounded archive may retain previously uncompetitive artifacts and their
construction records. Membership confers no eligibility or authority.
Reuse creates a candidate requiring current validation and dependency
checks; storage, search, replay, and revalidation count in Doc 20 costs.
Record whether improvement arose from new variation, recombination,
archived transfer, or changed collaborators/environment. Apply section
27's invention boundaries: retrieval, renaming, and harder tasks do not
establish a new computational primitive.

## 27.5 Construction rules and capacity for useful change (research)

Separate a reusable construction specification r from the realized provider:
p = Build(r, configuration, context). The specification records component
choices, interfaces, adaptation rules, initialization, constraints, and
variation operators. It carries no certification; each realization still
requires validation. This computational abstraction applies to all provider
families and does not require developmental cells or biological machinery.

For a declared operator distribution V and fixed evaluation panel T:

```text
local_validity(r) = Pr[Build(r') satisfies declared floors | r' ~ V(r)]
useful_yield(r) = E[new validated coverage from V(r)] / total trial cost
```

These are finite-budget, context-dependent estimates, not intrinsic
intelligence scores. Report uncertainty, operator probabilities, failed
builds, and costs. High local validity can coexist with low useful yield.
Current-task equivalence does not imply equal future adaptation potential.

| Computational mechanism | Research question and controlled comparison |
|---|---|
| Typed reusable building blocks and loose coupling | Does varying routing/configuration generate valid new behavior more cheaply than rewriting implementations? Match search budget and primitive access. |
| Copy then specialize | Can an isolated copy acquire a new context while retaining its parent as fallback? Compare with in-place adaptation and charge duplicate storage/execution. |
| Compatibility-aware recombination | Do interface-compatible subgraphs combine successfully? Compare typed and unrestricted proposals; include rejected/failed attempts in costs. |
| Context-dependent activation | Can a shared implementation support multiple contexts through explicit selection rules? Compare with separate providers and test context confusion. |
| Behavior-preserving search | Can bounded movement among currently equivalent implementations reach more useful later variants? Compare with greedy improvement under equal archive/search budgets. |
| Interaction-sensitive variation | Does the effect of a change depend on collaborator changes? Test paired modifications and report synergy/interference under Doc 28. |

Theoretical motivation: [reusable processes and weak coupling](https://pmc.ncbi.nlm.nih.gov/articles/PMC1876433/).
Computational evidence: [modularly varying goals](https://pmc.ncbi.nlm.nih.gov/articles/PMC1236541/)
produced modular structures in studied models; [a solvable modularity
model](https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1000355)
provides explicit assumptions. These do not prove arbitrary change or
modularity always helps. Compare fixed goals, structured recombinations of
subgoals, and unstructured changes with matched difficulty and exposure.
Measure valid-candidate rate, held-out coverage per spend, retention,
dependency failures, and reuse. Operator adaptation itself is a versioned
candidate subject to the same accounting and validation, not self-authority.

## 27.6 First executable construction recipe

Use typed composition before general synthesis. Domain: bounded deterministic
record-processing tasks using parsing, normalization, unit conversion,
filtering, and consistency checks. A pinned primitive library declares exact
I/O, preconditions, effects, costs, and independent reference outputs. This
first recipe generates no arbitrary code or new primitives.

Complementary composition validates its nominated contract with parents
retained (Doc 24 COMPOSE); it need not substitute for parent interfaces.
Assimilation/parent retirement add replacement coverage obligations. FUSE
denotes consolidation with its union gate; general composition uses staged
construction, validation, and COMMIT without that replacement assumption.

Representation: an acyclic typed expression graph with at most L expanded
primitive operations (macro lowerings follow section 27.8),
explicit constants, source fields, and output schema. Deterministic best-first
search orders by declared cost/depth with fixed tie breaks. Operators add or
replace a type-compatible operation, or reconnect an input without cycles.
Reject incompatible units, unavailable inputs, undeclared effects, excessive
depth, and malformed graphs before execution. Preregister L, constant domains,
candidate/step limits, and wall-clock/resource limits. Exhaustion reports
non-construction and preserves partial search records.

Inputs: nomination, primitive-library revision, development examples, resource
grant, and criteria revision. Outputs: graph/interpreter configuration,
parent/primitive refs, total search expenditure, rejected-candidate counts,
and construction trace. Search reads only development examples; admission
and final tasks are independent and access-controlled under Doc 23. Execute
through the normal provider interface. Success is level 3 composition, not
primitive invention; state the library/grammar boundary.

Baselines share primitives/examples: handwritten static workflow, adaptive
provider selection, bounded portfolio execution, and typed composition.
Charge search, failed trials, evaluation, adapters, communication, and execution.
A parser exposing checker demand can test induced opportunities with this
one generator. Preserve parent workflows and validate retention/boundaries.
Add learned generators, broader grammars, cyclic/stateful compositions, and
primitive synthesis only as separately tested extensions.

## 27.7 Construction within organizational plans

Section 27.6 remains the first generator and grammar boundary. It produces
typed candidates; Doc 19 predicts the consequences of constructing or using
them; Doc 22 chooses the next trial. A learned outcome model does not silently
extend the grammar, prove type/effect compatibility, or create a new primitive.

Allow a plan of at most two declared transformations in the initial experiment.
Intermediate outputs need explicit contracts and sub-demand nominations; a
sequence can construct an enabling provider and then compose it. Cache exact
subproblems under declared identity conditions, retain full positive/negative
cases separately, and test learned guarded predictions as an additional strategy.
All arms receive the same grammar, horizon, historical access and tuning budget.
Guard/rule/library changes are versioned construction hypotheses; exact rewrite
rules require proof within their domain and cannot stand in for uncertain
replacement evidence. Construction/admission failures remain in the trial ledger.

## 27.8 Developmental compilation: selected next construction mechanism

Learn useful operations for the construction language from validated traces.
Initially an abstraction is a parameterized macro/composite with a contract and
an explicit lowering to section 27.6's existing primitives. For example,
parse -> normalize units -> check consistency can become a scoped
validated_measurements(schema, units, policy) abstraction. Its contract names
accepted formats, units, error/failure behavior, and dependencies; the name does
not imply unrestricted generality.

Start with deterministic, acyclic, effect-free record processing:

1. Collect construction traces and relevant failures using development data only.
2. Propose repeated typed fragments and parameters through structural matching.
3. Check type/unit constraints and capture input restrictions and failure paths.
4. Register a versioned candidate abstraction and exact lowering with lineage.
5. Evaluate independent structural task families and unrelated retained tasks.
6. Admit, revise or retire the library entry under measured value/carrying cost.

The lowering preserves dependency identity, evaluation order, failures and resource
accounting. Similar syntax alone proves no semantic equivalence. Distinguish
cached outputs, named reusable programs, optimized implementations and new
primitives. Replacing the lowering with an optimized executable is a separate
candidate requiring exact equivalence in its domain or independently measured
contract satisfaction. Generalization of parameter guards requires new tests.

Every trial pins a library revision. Primitive access and expansion semantics
remain explicit: bound expanded primitive operations, computation, and planning
horizon, not just macro-token count. Reject recursive/cyclic lowerings in the
first profile and include transitive dependencies in closure. A two-step
organizational plan does not acquire extra uncharged work through one macro.
Changing a library entry versions it; existing pinned programs remain reproducible
while current uses face dependency/validation checks. Parents stay available
until replacement/retirement gates are satisfied.

Compare flat search, ordinary memoization, competent handwritten macros and
learned abstractions (Doc 07 section 7.13). Charge discovery, matching, failed
abstractions, validation, storage, maintenance and execution. Success is lower
total cost or better held-out competence/retention, not shorter names or more
library entries. The compiler lowers to the same instruction contract; it does
not add trusted opcodes or another framework. Learned search guidance is an
additional independently ablated mechanism, not a hidden part of the first test.
