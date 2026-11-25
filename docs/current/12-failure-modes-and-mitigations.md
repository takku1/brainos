# 12 — Failure Modes and Mitigations

F1 Unsafe actuation: only Certified+Active within revoke bounds;
in-flight work completes unless a safe stop exists. F2 Stale authority:
snapshots sequenced; challenge suspends dependents at episode boundary;
zero stale-authority exposure measured. F3 Fusion hallucination: support
refs required; derived ≠ independent. F4 Collapse/echo: competence and
diversity measured; agreement is not evidence. F5 Runaway growth:
explicit caps, protected floors, hysteresis. F6 Merger forgetting:
retention measured separately; approximate repair labeled. F7 Correlated
failure: joint failure rates measured; no fabricated availability.
F8 Starvation: liveness arbitration without safety override; fallback
specified, tested, reported. F9 Partition/split-brain: per-stream
sequences + clock-uncertainty margins; Transactor serializes on the
manifest, never wall-clock; minority side degrades, never commits
alone. F10 Developmental pathologies: niche collapse (protected floors
+ Pareto retention), churn (cooldowns + evaluation windows),
assimilation regress (rollback on drift), dead-lineage bloat
(reclamation after readers drain). F11 Conformance drift: second
implementation re-run per release; contract changes version the
contract, never silently extend it.
F12 Evaluation capture: providers optimize evaluator scores, not competence (Doc 23 integrity checks; evaluator quarantine).
F13 Ontological drift: capability definitions change, invalidating historical comparisons (versioned ontology, re-baseline on change — Doc 26 §26.4).
F14 Synthesis escape: generated implementations exceed permitted execution boundaries (isolation levels per Doc 29 §29.3; kernel validation for all generated code — Doc 27 §27.3).
F15 Credit corruption: incorrect attribution removes useful providers (uncertainty-aware thresholds; lineage-based regeneration — Doc 28).
F16 Grounding corruption: compromised observations or evaluators contaminate downstream decisions (grounding validity intervals; invalidation propagation; evaluator quarantine — Doc 30).
F17 Dependency concealment: undeclared dependencies invalidate isolation guarantees (footprint audits; concealment = contract violation — Doc 29 §29.2).
F18 Meta-adaptive instability: adaptive discovery/selection/evaluation mechanisms destabilize one another (bounded meta-adaptation with termination conditions; independently grounded evaluation of strategy changes — master directive §23).
F19 Resource-accounting evasion: providers underreport or externalize costs (single-ledger booking; audit against measured consumption — Doc 20 §20.5).
F20 Organizational deadlock: valid individual constraints block all useful progress (deadlock detection via stalled-demand metrics; escalation with explicit constraint-relaxation policy, never silent).

### Controlled-expansion research risks (F5/F10/F18 elaboration)

Duplicate nominations can spend repeatedly on one deficit; pending-admission
tracking and atomic reservations are proposed controls. Replication can
amplify a downstream bottleneck; diagnose contention before expanding.
Delayed feedback can cause burst overshoot and repeated retirement; test
delay sensitivity and settling time (Doc 07 section 7.11). Loss-triggered
restoration can become self-generated demand; independently verify service
loss and stop on recovered coverage, not a target instance count. Temporary
workers can accumulate as permanent overhead; record horizons and cleanup
outcomes. Copies do not establish independent failure domains. These are
unverified research mitigations, not additional closed audit requirements.
F2 reconciled: zero stale-authority exposure = no work executes under
authority revoked before that work's epoch cut (epoch-scoped permits,
Doc 09 §9.7). In-flight work completing after revocation runs under
its epoch's still-valid permit until a safe stop — permitted, bounded,
logged — not stale authority. Epoch permits never authorize an action
whose evidence was invalidated before its epoch cut: deployments bound
maximum revocation latency and require explicit re-authorization at
consequential side-effect boundaries. Residual: probation/dwell constants are
unjustified defaults; nonlinear generality unproven; concurrent-challenge
races beyond tested interleavings unproven.

### Organizational prediction failures (F12/F16/F18 elaboration)

Overbroad applicability guards, missing causal variables, selection-biased
case memory, compounded rollout error, stale dependencies, and correlated
model/evaluator errors can recommend harmful or wasteful changes. Retain negative
and rejected trials with outcome status; test guard transfer and one-/multi-step
calibration independently; replan after measured steps. Admission catching a
bad forecast is a model error. Search/model/archive maintenance can exceed saved
trials; compare total cost against symbolic and case-reuse baselines. Doc 19
owns the strategy; Doc 07 section 7.12 owns discriminating tests. These are
research failure modes, not new trusted-kernel powers.
