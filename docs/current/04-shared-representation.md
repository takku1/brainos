# 04 — Shared Representation (readout integration)

## 4.1 Role

The readout is a queryable integration surface, not a mandatory bus.
Direct provider links serve latency-sensitive paths; routed mesh paths
serve large or growing populations. The readout serves cross-domain reasoning
over projections of provider outputs.

## 4.2 Fusion with provenance

Every fused item carries source, version, time, confidence, and support
refs. Derived messages are never independent observations. Fusion
reports implementation-appropriate derivation provenance — attention or
recurrent weights where they exist, rule firings for symbolic fusion,
score breakdowns for statistical fusion, merge logs for record fusion;
low-weight or conflicting inputs are preserved in history, not silently
dropped. No implementation is required to report weights it does not
have.

## 4.3 Multi-query arbitration

Concurrent tasks attend to different projections of z_t, so an urgent
hazard cue and a dialogue context do not compete for one vector. Queries
declare schema, freshness bound, and epistemic minimum; the readout
returns the best eligible projection or an explicit miss.

## 4.4 Failure modes

Hallucinated fusion (confident output with weak support), stale reuse
(old version presented as fresh), collapse (all providers echo z),
bypass (critical signal forced through lossy fusion). Mitigations:
version pinning, freshness preconditions, diversity checks, and direct
links where latency or fidelity forbids fusion.
