# 03 — Supervisory Control

Status: partial — some requirements are built (Doc 31 register; Doc 21 section 21.0); the rest is specification, not implementation.

The reference eligibility implementation uses forward-chaining Horn rules
with precondition/effect actions. Other implementations preserve section 3.6's
eligibility contract. Planning and task execution follow Doc 32 section 32.11;
eligibility is neither a plan nor execution authorization.

## 3.1 Role

Coordinates provider activation, capability dependencies, and discrete
actions. Continuous signals travel separately. Answers eligibility;
does not execute tensors.

## 3.2 Closure semantics

Symbolic facts S_t plus rules R_t; reachable Horn closure:

```text
C_t = μX ( S_t ∪ ⋃ { add(r) | r ∈ R_t, pre(r) ⊆ X } )
```

Operation a is enabled when pre(a) ⊆ C_t. Enablement is necessary but
not sufficient: execution additionally requires authorization, valid
inputs, and resources.

## 3.3 What it is not

C_t is an abstraction over capabilities, not all physically reachable
states. Horn rules do not capture continuous dynamics, stochasticity, or
unmodeled environment structure.

## 3.4 Required extensions

1. Schema references: data types/encodings, shapes/grammars, normalization, units, frames. Tensor dtype/shape is one encoding, not the definition.
2. State ownership: who grounds each fact, who may invalidate it.
3. Timestamps and staleness: facts carry time; rules require freshness.
4. Adapters as capabilities: availability and version are preconditions.

## 3.5 Coordination pattern

1. Providers publish contract-typed outputs with provenance.
2. Controller updates S_t, recomputes C_t incrementally.
3. Newly enabled ops checked for authorization, inputs, resources.
4. Authorized ops trigger fabric calls; results re-enter as facts.
5. Continuous feedback needing no discrete decision stays off-path.

## 3.6 Reference implementation vs invariant

The Horn-closure production system above is the reference
implementation, not the invariant. The invariant is capability
eligibility: the supervisor computes which operations are eligible
from versioned facts, contracts, freshness, and authority — by Horn
rules, constraint solving, policy engines, or any mechanism passing
the conformance suite (Doc 07 L1). Prescribing Horn closure
universally would turn a general architecture into one research
implementation with a universal-sounding name.

| Architectural invariant | Replaceable implementations |
|---|---|
| Capability eligibility | Horn rules, constraint solving, policy engines |
| Resource scheduling | Priority queues, EDF, distributed scheduling |
| Provider communication | Direct calls, shared memory, message buses |
| Representation integration | Attention, factor graphs, typed records |
| Learning | Gradient descent, evolutionary search, symbolic revision |
| Competition | Pareto selection, contextual ranking, constrained optimization |
| Persistence | Local storage, databases, distributed artifact stores |
| Validation | Statistical tests, formal verification, deterministic checks |

The left column defines BrainOS. The right column is replaceable.

## 3.7 Tiers and authority

Observed / Believed / Certified with hysteresis; validity
(Active/Questionable/Revoked) orthogonal to tier. Certification attests
procedure, never truth. Only Certified + Active authorizes irreversible
acts within per-capability revoke bounds. Probation counts and dwell
times are configured test parameters until empirically calibrated, not derived optima.
