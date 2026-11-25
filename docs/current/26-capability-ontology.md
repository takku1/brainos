# 26 — Capability Ontology and Abstraction

Status: research — hypotheses and proposed mechanisms; nothing this document owns is implemented or validated.

Capabilities need relationships, or the registry (Doc 17 §17.4)
becomes a flat catalog of narrow functions. This document defines
the relationship vocabulary; the registry implements it.

## 26.1 Relations

- Specialization: capability B is a specialized C iff every context
  of B is a context of C with tighter bounds. Specialized providers
  compete in the sub-context, inherit the parent's floors.
- Equivalence: exact mutual contract refinement over the declared domain
  and contexts, established by proof or exhaustive verification (Doc 17
  section 17.6). Only this relation supports equivalence classes and
  canonicalization. High estimated mutual substitutability is a separate,
  contextual relation with uncertainty; it is not transitive and never
  inherits equivalence-class inference rules. It may nominate a merge
  candidate, but merging still requires validation and retention checks.
  Functional identity only; resilience is separate:

| Property               | Meaning |
|---|---|
| Functional equivalence | Can perform the same required functions |
| Redundancy             | Multiple providers can fulfill a requirement |
| Failure independence   | Providers are unlikely to fail together |
| Degeneracy             | Structurally different implementations provide overlapping functions |

Two identical deterministic calculators are functionally equivalent
while sharing exactly the same failure modes. Conflating equivalence
with resilience would mistake duplication for robustness.
- Dependency: B depends on A iff B's contract assumes A's outputs;
  invalidation of A suspends B (provenance-tracked, Doc 05).
- Composition: C = compose(A, B) is a registered capability with its own
  nominated contract (Doc 24 COMPOSE), not just an edge. C need not expose or
  substitute for A's/B's interfaces while those providers remain available.
- Partial coverage: i covers subset of j's contexts — recorded as
  the coverage map, which is what makes asymmetric competition
  (Doc 17) legible instead of mysterious.
- Abstraction: a capability stated without implementation
  commitments (e.g. "planning") under which specialized
  capabilities register; abstraction levels are navigable both
  directions (refine to specialized, generalize to abstract).

## 26.2 Rules

Relations are asserted with evidence and versioned like any claim
(Doc 09 ASSERT lifecycle): a claimed specialization that fails its
tighter bounds is challenged and retracted. The ontology is
discovered and revised through use (Doc 22 may nominate missing
abstractions), never frozen by fiat. Depth is bounded by utility:
abstract capabilities that never discriminate a decision are pruned.

## 26.3 Three layers

```text
Abstract capability → Functional contract → Provider implementation
```

A capability describes what can be done. A contract describes the
conditions and requirements (Doc 17). A provider implements it.
Ontology relations live at the capability and contract layers:
specialization refines contracts, equivalence relates contracts,
composition builds composite capabilities — never bare providers.
Substitutability (Doc 17 §17.2) is measured between providers
against a shared contract; the relation it evidences belongs to the
contracts. Keeping the three layers distinct prevents confusion
when the system constructs new capabilities automatically.

## 26.4 Consistency

Only proof-backed exact equivalence canonicalizes contracts before cycle
checks. Estimated overlap has no transitive closure. For equal-size coverage
sets A=0..9, B=1..10, C=2..11, adjacent overlaps are 0.9 but A/C overlap is 0.8;
a 0.9 threshold cannot merge all three into an exact class. Keep context,
uncertainty, and evidence on each measured relation.

The adaptive ontology governs its own validity: specialization must
be acyclic once equivalent contracts are identified (a cycle is a
challenge against one of its links, not a structure to keep);
dependency cycles are permitted only with explicit execution
semantics (ordering, fixed-point discipline, or bounded iteration —
declared, not assumed); removing an abstraction never silently
invalidates descendants — dependents are re-homed to the parent
abstraction or the removal is rejected with the affected set named.
Consistency violations suspend dependent acquisitions until
resolved; the ontology, like everything else here, earns its
structure.
