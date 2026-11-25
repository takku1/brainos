# 14 — Game-Dev Mapping (BT / Utility / GOAP / ECS / Netcode → OUR concepts)

Status: documentary — vocabulary, rationale or claims policy; adds no runtime requirement.

Document role: research rationale and source mappings. Architectural rules
remain in their owning contracts/protocols (README ownership table); mappings
do not introduce additional runtime conformance requirements.


All game terms below are renamed on import. Supervisor eligibility is never bypassed.

- BT composites/selectors + decorators/services + tick: one
  provider-internal execution policy UNDER supervisor eligibility. Leaves
  are capability invocations requiring pre(a)⊆C_t + AUTHORIZE +
  resources. Decorators are freshness/validity preconditions. Services are
  ENCODE/OBSERVE refreshers. RENAME: Blackboard → readout projection /
  typed fact store; tick snapshot/rollback slot → tick frame / rollback
  slot (Snapshot S_k reserved).
- Utility AI (considerations × curves → argmax/inertia/softmax): ranking
  over the supervisor-enabled set ONLY (enabled-then-authorized). Inertia
  ≈ dwell/hysteresis anti-oscillation. Curves are provider-local θ_i.
  ADOPT as ranking discipline; utility never self-authorizes.
- GOAP/HTN (actions {pre,effect,cost} + plan search; HTN nested tasks):
  T3 deliberative path producing a plan run via BIND/SPAWN/CONNECT +
  per-step AUTHORIZE; effects enter as ASSERTED claims via the kernel
  lifecycle. RENAME GOAP WorldState → planning facts (subset view of S_t/C_t).
- ECS (entity ID, component data, systems sweep; DOTS/Mass): entity ≈
  slot occupant or NPC principal; component ≈ versioned contract-typed
  datum in S_k; RENAME system → fabric sweep/processor (signal path, NOT
  supervisor). Mass-style processors inform Transactor/quarantined-rebuild
  sweeps + routed-mesh path.
- NPC coordination/crowd + AI LOD: degeneracy (many providers per
  capability) + scheduler/liveness. Eligibility identical at all LODs.
  Keep LOD for render/crowd cost scaling only (scheduler concern), never
  for epistemic tiers.
- World-sim tick (discrete ticks, fixed-timestep accumulator): episode /
  epoch boundaries for COMMIT (new versions between episodes). RENAME
  authoritative server → sim ownership (authority reserved for kernel).
- Netcode snapshots/rollback (predicted inputs, per-tick ring,
  restore/resimulate, determinism; snapshot-interp buffers): ADOPT
  mechanics for Snapshot/COMMIT; interp buffer ≈ consume rule
  Δτ≤τ_max + age-aware laws; input-only replication ≈ control-vs-signal
  split. Determinism mirrors conformance checks.

Thin-source gaps: DF tick from wiki/snippets only; Mass Entity from
tutorial secondaries not Epic primary; fixed-timestep primary not
fetched. No claim above depends on closing them. Caveat on use: every
mapping above is an analogy constrained by OUR contract, not an
equivalence — adopting BT/utility/GOAP/ECS mechanics never imports
their authority, state, or identity semantics; where the game term and
the BrainOS term collide, the rename table (Doc 13) governs.

## 14.1 Interaction design as a research instrument

Beyond execution techniques, game design offers a way to study how rules
produce population behavior. Translate the [MDA framework](https://users.cs.northwestern.edu/~hunicke/pubs/MDA.pdf)
into declared interaction rules -> measured dynamics -> externally tested
capability outcomes. This is a proposed adaptation of a design framework,
not evidence that a particular rule creates intelligence.

An interaction manifest records resource access, information visibility,
available actions, collaboration rules, feedback delays, and local rewards.
Change one rule family at a time. Intended specialization or cooperation
counts only when measured; designer intent is not an outcome.

[Multi-agent autocurricula](https://arxiv.org/abs/1909.07528) demonstrate
strategic changes that create new challenges for other agents. Test frozen,
current, and historical-mixture counterparts under matched budgets, then
measure transfer to independent tasks. Environment exploits and counterpart
overfitting are findings, not new general capabilities. Doc 25 owns dynamics,
Doc 20 owns incentives/costs, and Doc 07 owns experiment criteria.
