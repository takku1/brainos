# 29 — Dependency, Interference and Isolation Semantics

Graph connectivity is not the dependency model. Two providers sharing
a GPU, an evaluator, a mutable store, a scheduler, an external
service, or a failure domain interfere without sharing an edge —
and a transformation that touches neither can still break both
latency contracts. Doc 24's frame rule is therefore conditional on
this document, not on graph topology alone.

## 29.1 Interference classes

Shared computational resources (compute, memory, bandwidth);
shared mutable state (stores, caches, registries); shared
evaluators (one broken evaluator corrupts every verdict it renders);
scheduling interference (priority inversion, starvation, jitter);
external services (APIs, data feeds, simulators with their own
downtime and version drift); common failure domains (correlated
failure despite graph distance — Doc 17 §17.3).

## 29.2 Dependency closure and impact records

Providers declare versioned footprints for resources, state, evaluators,
scheduling, services, and failure domains. Compute a conservative affected
set over a pinned registry revision (section 29.4), then attach impact records:
cause/path, dependency kind, affected property/context, evidence revision,
and required action. Unknown footprints are conservative and audited.

| Impact | Default action, narrowed only by recorded evidence |
|---|---|
| Invalid support or compromised evaluator | Suspend dependent authority at the epoch cut; invalidate affected verdicts and reevaluate |
| Contract/schema/state incompatibility | Block affected bindings until compatibility/handover validates |
| Resource/schedule contention | Reevaluate affected latency/resource guarantees; throttle or suspend work relying on breached floors, not unrelated factual claims |
| Common failure domain | Reassess resilience/independence claims; does not alone make correct outputs false |
| Unknown kind or footprint | Suspend affected dependent decisions until classified/validated; preserve unrelated work where isolation is demonstrated |

Reachability identifies potential impact, not automatic empirical falsity.
Every affected property needs a current check or a scoped non-impact proof
before relying on its old verdict. Doc 24's frame rule applies unchanged
outside closure; inside closure it defers to these property-specific actions.

## 29.3 Isolation semantics

Quarantine (Doc 09) means: no authority, no publication, bounded
resources, and — for interference-affected evaluations — excluded
from shared evaluators and shared mutable state where feasible.
Candidate isolation levels (compute-only, +state, +evaluator,
full) are declared per validation; stronger claims require stronger
isolation. Perfect isolation is not promised; the achieved level is
reported with the verdict.

## 29.4 Fixed-point computation and scope

Start with graph/binding/evidence/resource items actually changed. Empty
change yields empty closure. Repeatedly add dependents of affected items
(directional) and footprint intersections (symmetric), until no additions.
Unknown footprints in a nonempty computation expand conservatively through
the pinned known population. The generic reference model uses untyped tags
and therefore may overinclude; richer implementations retain dependency class
and property paths. Scoped isolation excludes only its verified interference
class, never a direct data/evidence dependency.

Finite monotone closure terminates even with cycles; allow N growth passes
plus a final equality check for N providers. Registry changes require retry.
A cap exhausted before convergence is incomplete computation, not evidence
that a cycle is invalid. Log cascades as one event with member-specific
actions. Propagate invalidated support further, but do not turn resource
contention into unsupported factual invalidation. Doc 32 section 32.9 states
the reference tool's narrower scope and limitations.


## 29.5 Prediction and transformation-memory invalidation

Index prediction/guard records by the dependencies required for their stated
scope: contracts/units, implementation and state handover, adapters, resource
sharing, workload, evaluator/criteria, policy and grounding revisions. Changed
dependencies suspend or narrow affected predictions before decision reuse;
an unaffected property may keep its current support under a scoped non-impact
proof. Retain historical records for analysis without treating them as current
eligibility or empirical validity.

Provider-name or graph-shape equality alone is not a cache key for intervention
effects. Exact result caching requires the verified deterministic dependency
profile; empirical outcome forecasts need current calibration and applicability.
A learned dependency guess cannot exclude a required member of conservative
runtime impact computation. Model prediction of an affected set is checked
against measured effects and audited declarations, not trusted as enforcement.
