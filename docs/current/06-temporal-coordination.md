# 06 — Temporal Coordination

Status: partial — some requirements are built (Doc 31 register; Doc 21 section 21.0); the rest is specification, not implementation.

## 6.1 Multi-rate reality

Providers run at different periods; execution is async with timestamped
messages and no global barrier. Rate groups are a scheduler concern, not
a supervisor concern: fast loops never wait on symbolic closure. The
500/30/5 Hz profile is one robotics test instantiation, not architecture.

## 6.2 Snapshot publication

Shared state publishes as immutable snapshots with atomic publication:

```text
S_k = (z_k, t_k, v_k, p_k)
```

Timestamp, version, provenance, monotonic sequence. Consumers read one
consistent S_k or retry; assembling across versions is a defect. At scale,
publish per-stream snapshots with per-entry timestamps.

## 6.3 Consume rule

```text
consume(m): accept iff Δτ ≤ τ_max(context); else fallback
```

Every consumer enforces per-edge freshness bounds as contract
preconditions, uses age-aware laws (downweight/extrapolate, never use
slow state as fresh), keeps specified degraded modes, and avoids
synchronous mid-trajectory rerouting unless the loop budget allows it.

## 6.4 Liveness

Safety must not become denial of service. Version validation alone
starves slow producers; liveness arbitration escalates on repeated
rejection without overriding safety, and swap dwell plus hysteresis
prevent oscillation. Jitter and deadlock tests are integration gates.

## 6.5 Event-driven and distributed execution

Periodic rates are one scheduling discipline, not the architecture.
Providers may run event-driven (wake on message, interrupt, or
threshold), on-demand (query-triggered inference), or on remote/distributed
clocks. Requirements that survive distribution: timestamped messages
with declared clock domains and skew bounds; snapshot sequence numbers
per publishing stream (global sequence is not required); consume-rule
freshness bounds per edge with explicit clock-uncertainty margins;
idempotent handlers where delivery is at-least-once; Transactor commits
that serialize on the manifest, never on wall-clock order. A provider
that cannot meet a stream's skew or freshness bound is ineligible for
that edge — reported, not silently accommodated.

## 6.6 Protocol references

Doc 21 defines operation/snapshot/channel records and bounded queue policies.
Doc 32 owns task admission, stop/epoch behavior, replay, and crash recovery.
Snapshot sequence and clock domains do not replace manifest compatibility.
Use consumer-declared acceptable snapshot sets; reject incompatible revisions
rather than treating messages from one stream as a global atomic snapshot.
