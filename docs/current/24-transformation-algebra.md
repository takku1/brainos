# 24 — Organizational Transformation Algebra

Status: partial — some requirements are built (Doc 31 register; Doc 21 section 21.0); the rest is specification, not implementation.

Doc 19 defines the topological projection T:(G,X,B)→G'. This
document gives the full calculus over the authoritative
organizational state (§24.3): the graph signature describes
topological change only, and every preservation claim below is
subject to the conditional frame rule (§24.2) and the detailed
contracts (§24.4), which win over these summaries in any conflict.

## 24.1 Primitives (summaries; §24.4 contracts are authoritative)

Every primitive declares preserved capabilities (+ floors),
resource cost, preconditions, and rollback semantics. Verdicts are
per-application, never per-operator-type.

- ADD-PROVIDER (birth): introduce a candidate vertex, quarantined.
  Preserves: all existing capabilities, subject to shared-resource
  and evaluator-footprint admission checks (Doc 29). Rollback:
  remove vertex (pre-commit) or lineage rebuild (after).
- REMOVE-PROVIDER (retirement): remove a vertex only after
  substitution coverage ≥ floors elsewhere + safe fallback
  demonstrated. Rollback: restore pinned artifact; runtime state
  restoration is a separate operation.
- ADD-EDGE / REMOVE-EDGE: change relationships. Preserves: only
  capabilities outside the Doc 29 dependency closure of the change.
  Rollback: restore edge + revalidate closure.
- COMPOSE: new composite vertex from existing vertices (function
  composition, routing, or fusion per Doc 19). Parents persist until
  the composite validates; rollback: drop composite.
- ASSIMILATE: validated replacement absorbing overlapping abilities
  (seven methods: Doc 11 §11.4+); parents retire only after the union
  gate + rollback window. Rollback: rebuild from lineage, not undo.
- SPLIT: one vertex into specialized descendants with partitioned
  contexts. Preserves: nothing automatically — each descendant
  validates its partition plus the boundary. Rollback: merge back.
- REBIND: change a binding (provider ↔ role) without changing the
  graph. Revalidates everything in the change's dependency closure,
  not just the rebound role.

## 24.2 Composition semantics

- Sequencing: T2∘T1 is a transformation with composed preconditions
  (T1's postconditions must imply T2's) and composed rollback
  (reverse order). Invalid sequences are rejected at proposal time.
- Commutativity: two transformations commute when their affected
  dependency closures (Doc 29 fixed-point, not bare vertex/edge
  sets) are disjoint and neither changes the other's
  preconditions — checked, not assumed; the Transactor serializes
  the rest on the manifest. Closure semantics here and in Doc 29
  are the same rule stated twice for auditability, not two rules.
- Reversibility: no blanket reversibility — each primitive declares
  its own class in §24.4 (configuration rollback, state restoration,
  reconstruction, compensation, or forward-only). SPLIT-then-merge
  does not restore the original organization; ADD-then-REMOVE does
  not refund resources, evidence, history, or external effects.
  "Reversible by construction" applies only where a §24.4 contract
  states it.
- Preservation (frame rule, conditional): any capability whose
  vertices, edges, and bindings are untouched by T keeps its contract
  and validity without revalidation ONLY IF its dependency closure
  (Doc 29 fixed-point: shared resources, mutable state, evaluators,
  scheduling, external services, failure domains, transitively
  closed) is also untouched; inside closure, affected properties require current
  checks or scoped non-impact proofs under Doc 29's impact actions.
  This is what lets the organization change rapidly without
  re-proving everything — and the closure, not the graph, is what
  makes it sound.

## 24.3 Authoritative organizational state

```text
Σ = (G, K, X, E, A, R, M, H)
```

G organizational graph; K capability contracts and ontology;
X provider state; E evidence and evaluation records; A authority
state; R resource state; M active manifest; H persistent history.
Transformations operate over Σ, never over G alone:

```text
T: Σ ⇀ Σ′
```

Partial-function notation covers the deterministic kind only (T is
undefined where preconditions fail). Each kind has its signature:

| Transition kind | Mathematical representation |
|---|---|
| Deterministic | T: Σ ⇀ Σ′ |
| Stochastic | T: Σ ⇀ P(Σ) (distributions over states) |
| Nondeterministic | T: Σ ⇀ 2^Σ (admissible sets with selection rule) |
| Externally dependent | T: Σ × W ⇀ Σ (W = external inputs) |

The kernel exposes one unified transaction interface over all four
semantics; the kind only changes what commitment means (a
distribution commits to its sampling procedure, an external
dependency to its contract bounds). An undeclared kind is a defect,
not a default.

## 24.4 Per-primitive contracts (normative; summaries in §24.1 defer to these)

Graph/binding changes below refer to a staged candidate organization until
COMMIT publishes it. Before publication, only permitted resource, evidence,
and history records change authoritatively; the active graph remains pinned.
RETIRE includes its validated publication as a compound workflow.

Every primitive below states all ten properties — domain,
preconditions, transition, postconditions, failure semantics,
affected state (Σ-components), resource effects, evidence effects,
reversibility class, validation obligations. (ADD-EDGE and
REMOVE-EDGE, RETIRE and RESTORE are specified separately:
combined descriptions concealed different behavior.)

- ADD-PROVIDER. Domain: graph G (add vertex + declared edges).
  Preconditions: nomination valid (Doc 22) or explicit construction
  intent; budget reserved. Transition: deterministic edit +
  externally dependent construction (Doc 27). Postconditions:
  vertex present, quarantined, unpublished; no authority granted.
  Failure: reject on budget shortfall, invalid nomination, or
  footprint conflict; candidate discarded with reason. Affected
  state: G, X (candidate-local), R (debited), M (pending),
  H (appended). Resource effects: construction budget per Doc 20;
  shared-resource and evaluator footprints checked pre-admission
  (Doc 29). Evidence effects: construction record required; no
  verdicts yet. Reversibility class: configuration rollback
  pre-commit; lineage rebuild after. Validation obligations:
  L1-C1 contract declared; applicable L3 gates before production.
- REMOVE-PROVIDER. Domain: one vertex + incident edges.
  Preconditions: substitution coverage ≥ floors (Doc 17) + safe
  fallback demonstrated + Transactor approval. Transition:
  deterministic. Postconditions: vertex removed from the active
  graph; artifact + lineage retained in H. Failure: remain with
  review flag. Affected state: G, M, H + downstream dependents per
  closure. Resource effects: reclamation after readers drain;
  carrying cost stops. Evidence effects: removal record +
  substitution proof + fallback proof. Reversibility class:
  artifact restoration from lineage (NOT runtime-state
  restoration — separate operation). Validation obligations:
  L1 manifest consistency; L3 coverage retention.
- ADD-EDGE. Domain: one declared-compatible edge. Preconditions:
  endpoints exist; contracts mutually satisfiable (02 §2.4);
  closure revalidation planned. Transition: deterministic.
  Postconditions: edge present in G and M. Failure: reject
  incompatible or undeclared edge. Affected state: G, M + full
  Doc 29 closure. Resource effects: negligible direct; induced
  traffic budgeted. Evidence effects: compatibility proof recorded.
  Reversibility class: configuration rollback (remove edge +
  revalidate closure). Validation obligations: L1-C1/C4.
- REMOVE-EDGE. Domain: one existing edge. Preconditions:
  dependents identified; affected closure computed. Transition:
  deterministic. Postconditions: edge absent; dependents revalidated
  or failed closed. Failure: keep edge + report blocking
  dependents. Affected state: G, M + closure. Resource effects:
  traffic reduction; revalidation compute. Evidence effects:
  removal record + dependent verdicts. Reversibility class:
  configuration rollback (re-add requires revalidation, never
  assumed). Validation obligations: L1-C1/C4.
- REBIND. Domain: one binding. Preconditions: new provider eligible
  (Doc 09 REBIND schema); closure computed. Transition:
  deterministic. Postconditions: binding updated in M; closure
  revalidated. Failure: keep old binding + report. Affected state:
  M + closure (never just the rebound role). Resource effects:
  revalidation compute. Evidence effects: eligibility + closure-check
  proofs. Reversibility class: configuration rollback to prior
  binding (revalidate again). Validation obligations: L1-C2/C4.
- COMPOSE. Domain: parent set + nominated composite contract + method
  (Doc 27 level 3; any invention claim states its separate boundary).
  Preconditions: parents validated for their roles; interfaces compatible;
  composite evaluation gate and organizational retention floors defined.
  Transition: externally dependent construction, then deterministic
  registration. Postconditions: composite registered quarantined; parents
  persist. Failure: explicit non-construction; parents untouched. Affected
  state: G (+composite), X (new instance), M (pending), R (construction
  budget), H (lineage links). Resource effects: construction + validation;
  failed construction counted (Doc 20). Evidence effects: construction
  record (method, parents, data, recipes, randomness); no verdict yet.
  Reversibility class: drop composite while parents remain; after parent
  retirement, restoration follows the applicable reconstruction contract.
  Validation obligations: the composite's own nominated contract, internal
  compatibility, downstream effects, and organizational retention floors
  under Doc 29 impact checks. A complementary pipeline need not substitute
  for its individual parents: a parser followed by a reducer exposes a new
  end-to-end contract while the parser remains independently available.
  If the transformation also replaces or retires parents, ASSIMILATE and
  RETIRE additionally require coverage over the required parent contexts
  and safe fallback. A union-of-parents replacement gate is not a universal
  admission condition for an additive composite.
- SPLIT. Domain: one provider + partition specification.
  Preconditions: partition covers declared scope; boundary inputs
  identified. Transition: deterministic (structural) + externally
  dependent (descendant construction). Postconditions: descendants
  registered quarantined; parent retained until descendants
  validate. Failure: remain single provider + report ambiguous
  boundary. Affected state: G, X, M, R, H. Resource effects:
  construction + validation per descendant. Evidence effects:
  partition spec + boundary assignment log. Reversibility class:
  merge back with mandatory revalidation — union competence is
  never assumed restored, it is re-proven. Validation obligations:
  per-descendant partition tests + boundary tests.
- ASSIMILATE. Domain: overlapping provider set + method (any of
  7, Doc 11 §11.4). Preconditions: union gate defined; rollback
  window declared; lineage preserved. Transition: externally
  dependent (distillation/training/composition). Postconditions:
  replacement candidate quarantined; parents retained pending
  gate. Failure: explicit non-construction; parents untouched.
  Affected state: G, X, M, R, H + downstream consumers
  (revalidation). Resource effects: construction + evaluation on
  union of contexts + monitoring delta. Evidence effects: method
  record, union evaluation, retention examples. Reversibility
  class: one of four distinct operations — configuration rollback;
  internal state restoration; capability reconstruction from
  lineage; external effect compensation (compensate, never
  un-send). Validation obligations: union-of-parents + rare cases +
  transitions + downstream + retention + cost; rollback on drift.
- RETIRE. Domain: one provider. Preconditions: substitution
  coverage ≥ floors + safe fallback demonstrated + Transactor
  approval. Transition: deterministic. Postconditions: removed
  from active graph; lineage retained. Failure: remain with review
  flag. Affected state: G, M, H; dependents revalidated.
  Resource effects: reclamation after readers drain. Evidence
  effects: substitution proof + fallback proof. Reversibility
  class: reconstruction from lineage only (see RESTORE).
  Validation obligations: L1 manifest consistency; L3 coverage
  retention.
- RESTORE. Domain: retired unit + lineage. Preconditions: lineage
  intact; revalidation passes. Transition: deterministic
  registration + externally dependent reconstruction.
  Postconditions: unit active under a new version identity (never
  the old identity silently resurrected). Failure: remain retired.
  Affected state: G, M, X (rebuilt), H. Resource effects:
  reconstruction cost. Evidence effects: revalidation proof + new
  version binding to old lineage. Reversibility class: forward
  only — re-retire via RETIRE. Validation obligations: full
  revalidation as a new version.

## 24.5 Transactions and proof obligations

Composition acceptance case (AR-01): string -> integer-list parsing followed
by list -> sum reduction creates string -> sum capability. Admit a correct
compatible pipeline with parents retained; reject broken typing/results;
block parent retirement until replacement/fallback checks pass. A composite
without its parser's list-output interface is still valid for its new contract.
These cases are specified; runtime admission tests remain open.

Doc 32 sections 32.5 and 32.12 own operational workflow and crash recovery.
Construction/evaluation can span many short durable transactions; the final
manifest swap is atomic publication. Candidate isolation before admission
is not a failed validation. COMMIT rejects stale evidence/policy/criteria,
unvalidated artifacts, and mismatched versions. CONSOLIDATE makes an artifact
durable without activating it. RESTORE here is a reconstruction workflow;
Doc 09 RESTORE restores same-target eligibility and grants no operation permit.

Prepare (affected-set + closure computation, precondition check,
resource reservation), validate (quarantined candidate evaluation),
commit (atomic manifest swap), publish, with defined failure and
recovery at each stage. Concurrent transformations serialize on
the manifest; conflicts (overlapping closures, incompatible
preconditions) reject with reason, never interleave silently.
Isolation levels per Doc 29 §29.3 gate which claims a transaction
can support. Proof obligations: invariant preservation and
atomicity are established by proof, model check, or property test
under stated assumptions — an unproven property is labeled
conjecture with its verification plan, never presented as a
guarantee (see Doc 31 acceptance criteria for the per-invariant
register).
