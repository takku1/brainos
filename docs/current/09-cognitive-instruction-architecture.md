# 09 — Cognitive Instruction Architecture (generalized contract)

## 9.1 What it is

This document owns instruction signatures and allowed effects. Doc 21 owns
shared record definitions; Doc 32 owns operational protocols and lifecycle
transitions. A conflict requires coordinated edits; document age does not
select which incompatible rule an implementation should follow.

A common execution contract for heterogeneous components: typed
operations with shared semantics for observation, inference, learning,
communication, revision, authorization, and resource use. Analogous to a
CPU instruction set in role (interoperability + execution semantics),
not in low-level semantics. A language model may serve as a
communication interface; it must not secretly do the reasoning the
mechanisms are supposed to do.

Three programmable systems: computational fabric (heterogeneous learned
mechanisms), instruction architecture (common operations and semantics),
epistemic kernel (evidence, authority, provenance, recovery).

## 9.2 Families

Observation: OBSERVE (immutable evidence ref + validity), ENCODE
(representation retaining evidence and version). Inference: INFER (pinned
snapshot), PREDICT, REVISE, COMPARE, PROPAGATE (declared dependencies).
Learning: LEARN (bounded update, never grants COMMIT), VALIDATE,
CONSOLIDATE (preserve ancestry), FORK (context-scoped version).
Epistemic: ASSERT, CHALLENGE, VERIFY, RETRACT, QUARANTINE, RESTORE
(kernel decides). Execution: BIND, SPAWN, CONNECT, SNAPSHOT, COMMIT
(validated manifest at epoch cuts), AUTHORIZE, ACT.

Every instruction carries input types, capabilities, preconditions,
allowed transitions, version/epoch semantics, failure behavior, cost,
provenance. LEARN never implies COMMIT; COMMIT never implies AUTHORIZE.

## 9.3 State, manifests, kernel

Working, episodic, learned, epistemic, execution state persists across
sessions. Episodes — bounded runs with natural boundaries — bind one
immutable manifest M_k = (graph, versions, evidence epoch, context);
new versions publish at epoch cuts. An episode boundary is one
kind of epoch cut; the general mechanism is the epoch cut (§9.7),
which continuous systems also trigger on version change, challenge
events, or bounded intervals. Claim lifecycle ASSERTED → CHALLENGED →
(invalidated | RESTORED), with RESTORED challengeable again. Candidate
providers validate before COMMIT; active versions may be quarantined or retired.
Doc 32 section 32.5 owns the full transitions. Challenge suspends
dependent authority at the next epoch cut (coinciding with the
episode boundary in episodic systems, never mid-epoch or
mid-episode); rebuilds run quarantined and publish only through
COMMIT.

## 9.4 Conformance and tiers

A component claims an instruction only by passing conformance checks
with an independent implementation of the same contract. Per-instruction
conformance; unsupported operations reject explicitly. Declared compound
implementations are permitted when they preserve the same contract.
Execution tiers characterize paths (T0 reflex … T3 deliberative);
escalate on out-of-domain input, surprise, staleness, challenged
dependencies, or breach. Promotion requires context contract, measured
accuracy, resource advantage, registered dependencies, validated
escalation, transactional publication. Economics per the canonical
model (Doc 20: monitoring and fallback costs included, break-even on
earned horizons) — inline shorthands here are never the definition.

## 9.5 Degeneracy

Organize around capabilities with contracts, not fixed identities. Many
providers may satisfy one capability; eligibility checks version,
currency, context, dependencies, quarantine, resources. Diversity must
be measured (failure domains, joint failure rates), never inferred from
different names; agreement is not independent evidence.

## 9.6 Instruction families (centerpiece specification)

Organizational prediction/planning uses these existing operations with Doc 21
section 21.7's records; Doc 32 section 32.13 defines the workflow. No model
prediction constitutes VALIDATE, COMMIT or AUTHORIZE, and no new opcode is
introduced for organizational world models.

Semantic families — not necessarily primitive opcodes. Developmental
operations may be compound transactions over simpler instructions.

| Family | Example operations |
|---|---|
| Observation | OBSERVE, ENCODE |
| Computation | INFER, PREDICT, COMPARE |
| Communication | EMIT, RECEIVE, CONNECT |
| Execution | SPAWN, BIND, REBIND, CANCEL |
| Adaptation | LEARN, REVISE, FORK |
| Development | BIRTH, DIFFERENTIATE, FUSE, RETIRE |
| Evaluation | VALIDATE, BENCHMARK |
| Knowledge | ASSERT, CHALLENGE, RETRACT |
| Persistence | SNAPSHOT, RESTORE, COMMIT |
| Authority | AUTHORIZE, REVOKE, ACT |
| Resource management | RESERVE, ALLOCATE, RELEASE |

Each operation defines inputs, outputs, preconditions, effects,
failure semantics, and resource consequences. Unimplemented
instructions reject explicitly; compound implementations preserve the same
contract. Conformance is
per-instruction (Doc 07 L1).

## 9.7 Continuous operation without episode boundaries

Systems that run continuously (control loops, assistants, live
simulations) have no natural episode boundaries. Publication uses
epoch windows: the Transactor cuts epochs on version change,
challenge events, or bounded intervals — whichever comes first —
with a declared maximum epoch length per deployment. Challenge
suspends dependent authority at the next epoch cut, never
mid-epoch. In-flight work drains or hits declared safe stops;
revocation takes effect on new invocations immediately and on
in-flight work at safe stops. Zero stale-authority exposure means no
work executes under authority revoked before the work's epoch cut —
reconciled with in-flight completion by epoch-scoped permits, not by
instant global preemption (see Doc 12 F2).

## 9.8 Instruction contracts (normative template)

Every instruction is specified by the same nine properties. Worked
example for LEARN:

| Contract property | LEARN |
|---|---|
| Inputs | Provider version, experience refs, learning policy |
| Preconditions | Trainable capability declared; experience valid + retrievable; resource reservation held |
| Output | Candidate artifact (new version; active manifest untouched) |
| State effects | Candidate-state changes only, isolated writes |
| Prohibited effects | Modification of the active manifest; authority changes |
| Failure semantics | Discard or quarantine candidate; record cause |
| Concurrency semantics | Pinned source version; isolated writes; no read of uncommitted state |
| Resource accounting | Training time, peak memory, storage |
| Evidence requirements | Training provenance and dependency refs recorded at training time |

Abridged contracts for the remaining foundational instructions (same
nine properties apply in full):

- OBSERVE: inputs declared source + payload; rejects unknown sources,
  never synthesizes; output immutable evidence ref; cost one record.
- ENCODE: pre bound model + valid ref; output representation retaining
  (ref, model version); unbound model rejected.
- INFER / PREDICT: pre version ∈ pinned manifest; reads pinned
  parameters only; version mismatch refused, never silently mixed;
  PREDICT adds uncertainty estimate + horizon.
- REVISE / COMPARE / PROPAGATE: revision records derivation edge;
  comparison reports disagreement + differing inputs; propagation only
  through declared dependencies.
- VALIDATE / BENCHMARK: independent checks on quarantined candidates;
  output pass/fail + measurements; never publishes.
- FORK: history-preserving context-scoped version; parent intact.
- CONSOLIDATE: durable version + preserved ancestry; discarded history
  downgrades the result to explicitly labeled approximate repair.
- ASSERT / CHALLENGE / VERIFY / RETRACT / QUARANTINE / RESTORE:
  kernel-decided; challenge suspends dependent authority at the next
  epoch cut (never mid-epoch); rebuilds publish only through COMMIT;
  concurrent challenges serialize on the manifest.
- BIND / SPAWN / CONNECT / SNAPSHOT / COMMIT: role binding, instance
  creation with fresh manifest copy, declared edges (undeclared edges
  untraversable); COMMIT publishes one validated manifest between
  epochs or at epoch cuts, else rejects with reason.
- AUTHORIZE / REVOKE / ACT: per-capability permits under current
  manifest and tier; revocation stops new invocations immediately and
  in-flight work at safe stops; deployment bounds maximum revocation
  latency, and consequential side-effect boundaries require explicit
  re-authorization — epoch permits never authorize an action whose
  evidence was invalidated before its epoch cut (Doc 12 F2).
- BIRTH / DIFFERENTIATE / FUSE / RETIRE: compound transactions over
  SPAWN plus construction (LEARN only when component training is
  involved; otherwise instantiate/configure/compose per Doc 27) +
  VALIDATE/COMMIT plus registry updates; all reuse the Transactor,
  manifests, and applicable gates (Doc 11).
- RESERVE / ALLOCATE / RELEASE: resource reservations with explicit
  caps; background developmental work admitted only within remaining
  budgets; failed candidates counted in totals.

## 9.9 Machine-readable contract schema (normative shape)

Descriptions (§9.8 prose) are human renderings. Schemas (§9.10) are
the conformance target, and they are typed: every input and output
names a type from the registry below, every precondition names a
predicate from the catalog with arguments. Two implementations pass
L1 only if they accept/reject identically on the same schema
instances (Doc 21 §21.3 C1). A schema validator MUST reject:
unknown instruction names, undeclared types, undeclared
predicates, missing required keys, and any instance that violates
a stated precondition or attempts a prohibited effect.

Types registry (shared by all schemas):
`OperationRef, EvidenceRef, VersionId, ManifestRef, EpochId,
SchemaId, CapabilityRef, ProviderRef, ClaimId, ContextRef,
BudgetRef, ReservationRef, AllocationRef, BindingRef, EdgeRef,
StreamRef, ChannelRef, MessageRef, SubscriptionRef, StateEstimate,
Estimate, Measure, Verdict, PermitRef, ProcedureRef, RecipeRef,
PolicyId, StateRef, CostVector, CandidateRef, DataRef, PropertyRef,
RestoreTargetRef, BudgetHoldingRef, SnapshotRef`
— each bound to Doc 21 §21.1 definitions; an unbound type name
fails validation.

Predicate catalog (each predicate states its check; defined_in
names the normative prose that fixes its meaning):
- `source_declared(s)` — source s is registered (09 §9.8 OBSERVE)
- `ref_valid(r)` — evidence ref resolves and is live (09 §9.8 OBSERVE)
- `model_bound_to_role(m, role)` — model bound for this role (09 §9.8 ENCODE)
- `version_in_manifest(v, M)` — v ∈ pinned manifest M (09 §9.3)
- `snapshot_pinned(S)` — snapshot immutable + sequenced (09 §9.7)
- `uncertainty_reported(e)` — estimate carries calibrated uncertainty (09 §9.8 PREDICT; output-side: declared here, enforced at validation — Phase 1B)
- `state_valid(x)` — state schema + freshness hold (03 §3.4, 09 §9.8 REVISE)
- `observation_valid(o)` — observation schema + freshness hold (03 §3.4, 09 §9.8 REVISE)
- `inputs_retrievable(a, b)` — both ends readable (09 §9.8 COMPARE)
- `declared_dependencies_only(c)` — closure ⊆ declared edges (09 §9.8 PROPAGATE)
- `candidate_quarantined(u)` — unit isolated, unpublished (09 §9.8 VALIDATE)
- `workload_declared(w)` — benchmark workload registered (09 §9.8 BENCHMARK)
- `mechanism_exists(m)` — mechanism registered (17 §17.4, 09 §9.8)
- `contract_declares(unit, op)` — op in unit's capability contract (17 §17.4, 09 §9.8)
- `validated(u)` — passed checks, verdict recorded (09 §9.8 VALIDATE)
- `evidence_retrievable(e)` — evidence available (09 §9.8 ASSERT)
- `claim_active(c)` — claim asserted and not retracted (09 §9.3)
- `procedure_declared(p)` — verification procedure registered (09 §9.8 VERIFY)
- `kernel_decided(d)` — kernel is the decider, not recommenders (09 §9.2)
- `challenge_or_validation_failure(u)` — quarantine trigger present (09 §9.8 QUARANTINE)
- `validation_passed(u, p)` - proof p matches target u/version/scope and current criteria (32 section 32.5)
- `provider_eligible(p, role)` — capability + version + context + authority checks pass (09 §9.5, 17 §17.1)
- `budget_available(b)` — uncommitted budget exists (09 §9.8 RESERVE)
- `budget_reserved(b)` — budget held for this purpose (09 §9.8 RESERVE)
- `reservation_held(r)` — reservation live (09 §9.8 ALLOCATE)
- `endpoints_compatible(e)` — contracts mutually satisfiable (02 §2.4)
- `stream_exists(s)` — publishing stream registered (09 §9.8 SNAPSHOT)
- `validated_between_episodes_or_epoch_cut(M)` — COMMIT timing rule (09 §§9.3/9.7)
- `permit_conditions_met(op, ctx)` — per-capability permit rule holds (09 §9.8 AUTHORIZE)
- `tier_satisfied(op)` — epistemic tier authorizes this risk class (03 §3.7)
- `revocation_triggered(p)` — challenge/invalidation demands revocation (09 §9.8 REVOKE)
- `latency_bound_declared(scope)` — deployment states max revocation latency for the scope (09 §9.7)
- `closure_revalidated(x)` — dependents in x's Doc 29 closure revalidated (09 §9.8 REBIND)
- `permit_valid_at_epoch(op, e)` — permit covers op at epoch e (09 §9.7)
- `reauthorized_at_side_effect_boundary(op)` — fresh authorization at each consequential side effect; epoch permits alone do NOT satisfy this where evidence was invalidated before the cut (09 §9.8 ACT, 12 F2)
- `nomination_valid(n)` — nomination contract + criteria + floors registered (Doc 22)
- `context_defined(c)` — differentiation context scoped (09 §9.8 DIFFERENTIATE)
- `all_parents_validated(P)` — every merged parent validated (09 §9.8 FUSE)
- `union_gate_defined(P)` — acquisition gate over union of parent contexts (11 §11.4)
- `coverage_ge_floors(i, j)` — substitution covers floors (17 §17.2)
- `fallback_demonstrated(i, j)` — safe fallback shown (09 §9.8 RETIRE)
- `holding_known(a)` — reservation/allocation or its released tombstone resolves for this owner (21 §21.5)
- `safe_stop_declared_or_completed(w)` — declared stop point or finished work (09 §9.8 CANCEL)
- `channel_declared(ch)` — channel registered (09 §9.8 EMIT)
- `subscription_active(s)` — subscription live (09 §9.8 RECEIVE)

Conformance example (LEARN), in the same typed form as §9.10:

```yaml
instruction: LEARN
inputs: {provider: ProviderRef, provider_version: VersionId, experience: "[EvidenceRef]", policy: PolicyId, budget: BudgetRef}
preconditions:
  - contract_declares(provider, LEARN)
  - evidence_retrievable(experience)
  - budget_reserved(budget)
outputs: {candidate: CandidateRef}
state_effects: [candidate_isolated_writes]
prohibited_effects: [modify_active_manifest, grant_authority]
failure_semantics: [discard_candidate, quarantine_candidate]
concurrency: {pinned_source_version: true, isolated_writes: true}
resource_accounting: [compute_time, peak_memory, storage]
evidence_requirements: [training_provenance, dependency_refs]
```

Every §9.10 schema carries exactly these nine keys with typed
values and catalogued predicates — that shape is what the
validator checks. Prose remains the human rendering; the schema
is the conformance target.

## 9.10 Machine-readable schemas (typed; predicate refs resolve in section 9.9)

```yaml
instruction: OBSERVE
inputs: {source: ProviderRef, payload: DataRef, context: ContextRef}
preconditions:
  - source_declared(source)
outputs: {ref: EvidenceRef}
state_effects: [evidence_store_append]
prohibited_effects: [synthesize_payload]
failure_semantics: [reject_unknown_source]
concurrency: {append_only: true}
resource_accounting: [one_record]
evidence_requirements: [the_record_itself]
```

```yaml
instruction: ENCODE
inputs: {ref: EvidenceRef, model: VersionId, role: CapabilityRef}
preconditions:
  - ref_valid(ref)
  - model_bound_to_role(model, role)
outputs: {representation: StateRef}
state_effects: [derived_artifact_only]
prohibited_effects: [unbound_model_use]
failure_semantics: [reject]
concurrency: {pinned_read: true}
resource_accounting: [compute_time]
evidence_requirements: [retain_ref_and_model_version]
```

```yaml
instruction: INFER
inputs: {mechanism_version: VersionId, manifest: ManifestRef, snapshot: SnapshotRef}
preconditions:
  - version_in_manifest(mechanism_version, manifest)
  - snapshot_pinned(snapshot)
outputs: {estimate: StateEstimate}
state_effects: [read_only]
prohibited_effects: [version_mixing]
failure_semantics: [refuse_version_mismatch]
concurrency: {pinned_read: true}
resource_accounting: [compute_time]
evidence_requirements: [derivation_edge]
```

```yaml
instruction: PREDICT
inputs: {state: StateRef, horizon: Measure, mechanism_version: VersionId, manifest: ManifestRef}
preconditions:
  - state_valid(state)
  - version_in_manifest(mechanism_version, manifest)
outputs: {estimate: Estimate, uncertainty: Measure}
state_effects: [read_only]
prohibited_effects: [uncertainty_free_claim]
failure_semantics: [refuse_stale_snapshot]
concurrency: {pinned_read: true}
resource_accounting: [compute_time]
evidence_requirements: [derivation_edge, horizon]
```

```yaml
instruction: REVISE
inputs: {state: StateRef, observation: EvidenceRef}
preconditions:
  - state_valid(state)
  - observation_valid(observation)
outputs: {revised: StateRef}
state_effects: [new_version_only]
prohibited_effects: [silent_overwrite]
failure_semantics: [reject_invalid_observation]
concurrency: {pinned_read: true}
resource_accounting: [compute_time]
evidence_requirements: [derivation_edge]
```

```yaml
instruction: COMPARE
inputs: {a: StateRef, b: StateRef}
preconditions:
  - inputs_retrievable(a, b)
outputs: {measure: Measure, differing: DataRef}
state_effects: [none]
prohibited_effects: [none]
failure_semantics: [report_incomparable]
concurrency: {read_only: true}
resource_accounting: [compute_time]
evidence_requirements: [inputs_cited]
```

```yaml
instruction: PROPAGATE
inputs: {correction: DataRef, closure: DataRef}
preconditions:
  - declared_dependencies_only(closure)
outputs: {corrections: DataRef}
state_effects: [new_versions_only]
prohibited_effects: [traverse_undeclared_edges]
failure_semantics: [partial_with_report]
concurrency: {pinned_read: true}
resource_accounting: [compute_time]
evidence_requirements: [dependency_path]
```

```yaml
instruction: VALIDATE
inputs: {candidate: CandidateRef, checks: PropertyRef}
preconditions:
  - candidate_quarantined(candidate)
outputs: {verdict: Verdict, measurements: Measure}
state_effects: [verdict_record_only]
prohibited_effects: [publish]
failure_semantics: [fail_closed]
concurrency: {isolated: true}
resource_accounting: [evaluation_compute]
evidence_requirements: [check_definitions, data_refs]
```

```yaml
instruction: BENCHMARK
inputs: {provider: ProviderRef, workload: DataRef}
preconditions:
  - workload_declared(workload)
outputs: {measurements: Measure}
state_effects: [read_only_production]
prohibited_effects: [modify_provider]
failure_semantics: [report_incomplete]
concurrency: {isolated_or_quota: true}
resource_accounting: [evaluation_compute]
evidence_requirements: [workload_definition]
```

```yaml
instruction: FORK
inputs: {mechanism: ProviderRef, context: ContextRef}
preconditions:
  - mechanism_exists(mechanism)
outputs: {version: VersionId}
state_effects: [new_version_history_intact]
prohibited_effects: [modify_parent]
failure_semantics: [reject]
concurrency: {isolated_writes: true}
resource_accounting: [storage]
evidence_requirements: [parent_ref, context]
```

```yaml
instruction: CONSOLIDATE
inputs: {unit: CandidateRef}
preconditions:
  - validated(unit)
outputs: {durable: VersionId}
state_effects: [durable_publication]
prohibited_effects: [silent_history_drop]
failure_semantics: [label_approximate_repair]
concurrency: {transacted: true}
resource_accounting: [storage]
evidence_requirements: [full_ancestry_or_explicit_gap]
```

```yaml
instruction: ASSERT
inputs: {claim: DataRef, evidence: EvidenceRef}
preconditions:
  - evidence_retrievable(evidence)
outputs: {id: ClaimId}
state_effects: [claim_asserted]
prohibited_effects: [self_certify]
failure_semantics: [reject_unsupported]
concurrency: {append_only: true}
resource_accounting: [one_record]
evidence_requirements: [evidence_refs]
```

```yaml
instruction: CHALLENGE
inputs: {claim: ClaimId}
preconditions:
  - claim_active(claim)
outputs: {suspension: Measure}
state_effects: [dependent_authority_suspended]
prohibited_effects: [mid_epoch_suspension, invalidation_without_record]
failure_semantics: [reject_unknown_claim]
concurrency: {serialized_on_manifest: true}
resource_accounting: [compute_time]
evidence_requirements: [challenge_grounds]
```

```yaml
instruction: VERIFY
inputs: {claim: ClaimId, procedure: ProcedureRef}
preconditions:
  - procedure_declared(procedure)
outputs: {record: EvidenceRef}
state_effects: [verdict_record_only]
prohibited_effects: [change_claim_status]
failure_semantics: [record_negative_result]
concurrency: {isolated: true}
resource_accounting: [evaluation_compute]
evidence_requirements: [procedure_definition]
```

```yaml
instruction: RETRACT
inputs: {claim: ClaimId, authority: PolicyId}
preconditions:
  - kernel_decided(authority)
outputs: {withdrawal: Verdict}
state_effects: [claim_invalidated]
prohibited_effects: [delete_history]
failure_semantics: [reject_unauthorized]
concurrency: {transacted: true}
resource_accounting: [compute_time]
evidence_requirements: [retraction_cause]
```

```yaml
instruction: QUARANTINE
inputs: {units: ProviderRef, scope: DataRef}
preconditions:
  - challenge_or_validation_failure(units)
outputs: {exclusion: Verdict}
state_effects: [unit_state_quarantined]
prohibited_effects: [block_independent_work]
failure_semantics: [fail_closed]
concurrency: {transacted: true}
resource_accounting: [compute_time]
evidence_requirements: [quarantine_cause]
```

```yaml
instruction: RESTORE
inputs: {target: RestoreTargetRef, proof: EvidenceRef}
preconditions:
  - validation_passed(target, proof)
outputs: {restoration: Verdict}
state_effects: [eligibility_restored_after_kernel_adjudication]
prohibited_effects: [restore_without_validation, grant_operation_permit, publish_new_artifact]
failure_semantics: [remain_quarantined]
concurrency: {transacted: true}
resource_accounting: [compute_time]
evidence_requirements: [validation_proof]
```

```yaml
instruction: BIND
inputs: {role: CapabilityRef, provider: ProviderRef}
preconditions:
  - provider_eligible(provider, role)
outputs: {binding: BindingRef}
state_effects: [binding_staged]
prohibited_effects: [bind_ineligible]
failure_semantics: [reject_with_reason]
concurrency: {transacted: true}
resource_accounting: [compute_time]
evidence_requirements: [eligibility_proof]
```

```yaml
instruction: SPAWN
inputs: {spec: DataRef, budget: BudgetRef}
preconditions:
  - budget_available(budget)
outputs: {instance: ProviderRef}
state_effects: [instance_created]
prohibited_effects: [shared_mutable_state_by_default]
failure_semantics: [reject_over_budget]
concurrency: {isolated: true}
resource_accounting: [spawn_cost, reservation]
evidence_requirements: [spec]
```

```yaml
instruction: CONNECT
inputs: {edge: EdgeRef}
preconditions:
  - endpoints_compatible(edge)
outputs: {edge: EdgeRef}
state_effects: [graph_edit_staged]
prohibited_effects: [undeclared_edges]
failure_semantics: [reject_incompatible]
concurrency: {transacted: true}
resource_accounting: [compute_time]
evidence_requirements: [compatibility_proof]
```

```yaml
instruction: SNAPSHOT
inputs: {stream: StreamRef}
preconditions:
  - stream_exists(stream)
outputs: {snapshot: SnapshotRef}
state_effects: [publication]
prohibited_effects: [mutable_snapshot]
failure_semantics: [retry_on_torn_read]
concurrency: {atomic_publication: true}
resource_accounting: [storage]
evidence_requirements: [version_timestamp_provenance]
```

```yaml
instruction: COMMIT
inputs: {manifest: ManifestRef}
preconditions:
  - validated_between_episodes_or_epoch_cut(manifest)
outputs: {result: Verdict}
state_effects: [manifest_published]
prohibited_effects: [stale_or_unvalidated_commit, mixed_version_state]
failure_semantics: [reject_with_reason]
concurrency: {compare_and_swap: true}
resource_accounting: [compute_time]
evidence_requirements: [validation_verdict, epoch]
```

```yaml
instruction: AUTHORIZE
inputs: {op: OperationRef, context: ContextRef}
preconditions:
  - permit_conditions_met(op, context)
  - tier_satisfied(op)
outputs: {permit: PermitRef}
state_effects: [permit_recorded]
prohibited_effects: [authorize_without_evidence]
failure_semantics: [deny_closed]
concurrency: {manifest_pinned: true}
resource_accounting: [compute_time]
evidence_requirements: [tier_proof, manifest_epoch]
```

```yaml
instruction: REVOKE
inputs: {permit: PermitRef}
preconditions:
  - revocation_triggered(permit)
  - latency_bound_declared(permit)
outputs: {stopped: Verdict}
state_effects: [permit_revoked]
prohibited_effects: [retroactive_invalidation_of_epoch_valid_work]
failure_semantics: [escalate_if_no_safe_stop]
concurrency: {immediate_for_new: true}
resource_accounting: [compute_time]
evidence_requirements: [revocation_cause, latency_bound]
```

```yaml
instruction: ACT
inputs: {op: OperationRef, epoch: EpochId}
preconditions:
  - permit_valid_at_epoch(op, epoch)
  - reauthorized_at_side_effect_boundary(op)
outputs: {result: Measure}
state_effects: [external_effects_per_contract]
prohibited_effects: [act_without_permit, act_on_invalidated_evidence]
failure_semantics: [refuse_and_report]
concurrency: {permit_scoped: true}
resource_accounting: [execution_cost]
evidence_requirements: [permit_ref]
```

```yaml
instruction: BIRTH
inputs: {nomination: DataRef, budget: BudgetRef}
preconditions:
  - nomination_valid(nomination)
  - budget_reserved(budget)
outputs: {candidate: CandidateRef}
state_effects: [candidate_registered]
prohibited_effects: [live_publication]
failure_semantics: [explicit_non_construction]
concurrency: {isolated: true}
resource_accounting: [construction_budget]
evidence_requirements: [nomination_ref, construction_record]
```

```yaml
instruction: DIFFERENTIATE
inputs: {provider: ProviderRef, context: ContextRef}
preconditions:
  - contract_declares(provider, DIFFERENTIATE)
  - context_defined(context)
outputs: {version: VersionId}
state_effects: [new_version_only]
prohibited_effects: [modify_parent, overclaim_scope]
failure_semantics: [remain_generic]
concurrency: {isolated_writes: true}
resource_accounting: [compute_time, storage]
evidence_requirements: [context_definition, validation]
```

```yaml
instruction: FUSE
inputs: {parents: "[ProviderRef]", method: RecipeRef}
preconditions:
  - all_parents_validated(parents)
  - union_gate_defined(parents)
outputs: {candidate: CandidateRef}
state_effects: [candidate_registered_parents_retained]
prohibited_effects: [parent_retirement_without_gate]
failure_semantics: [explicit_non_construction]
concurrency: {isolated: true}
resource_accounting: [construction_budget]
evidence_requirements: [parent_refs, method_record]
```

```yaml
instruction: RETIRE
inputs: {provider: ProviderRef, substitution: EvidenceRef, fallback: EvidenceRef}
preconditions:
  - coverage_ge_floors(provider, substitution)
  - fallback_demonstrated(provider, fallback)
outputs: {removal: Verdict}
state_effects: [active_graph_removal_after_gates, history_kept]
prohibited_effects: [silent_removal]
failure_semantics: [remain_with_flag]
concurrency: {transacted: true}
resource_accounting: [compute_time]
evidence_requirements: [substitution_matrix, fallback_proof]
```

```yaml
instruction: RESERVE
inputs: {resource: DataRef, amount: Measure}
preconditions:
  - budget_available(resource)
outputs: {reservation: ReservationRef}
state_effects: [budget_debited]
prohibited_effects: [over_reservation]
failure_semantics: [reject_over_budget]
concurrency: {atomic: true}
resource_accounting: [none]
evidence_requirements: [budget_ref]
```

```yaml
instruction: ALLOCATE
inputs: {reservation: ReservationRef}
preconditions:
  - reservation_held(reservation)
outputs: {allocation: AllocationRef}
state_effects: [resources_committed]
prohibited_effects: [double_spend]
failure_semantics: [reject_invalid_reservation]
concurrency: {atomic: true}
resource_accounting: [allocation_cost]
evidence_requirements: [reservation_ref]
```

```yaml
instruction: RELEASE
inputs: {holding: BudgetHoldingRef}
preconditions:
  - holding_known(holding)
outputs: {freed: Verdict}
state_effects: [resources_returned]
prohibited_effects: [none]
failure_semantics: [idempotent_ok]
concurrency: {atomic: true}
resource_accounting: [none]
evidence_requirements: [allocation_ref]
```

```yaml
instruction: REBIND
inputs: {binding: BindingRef, provider: ProviderRef}
preconditions:
  - provider_eligible(provider, binding)
  - closure_revalidated(binding)
outputs: {rebinding: BindingRef}
state_effects: [rebinding_staged]
prohibited_effects: [skip_dependent_revalidation]
failure_semantics: [keep_old_binding]
concurrency: {transacted: true}
resource_accounting: [compute_time]
evidence_requirements: [eligibility_proof, closure_check]
```

```yaml
instruction: CANCEL
inputs: {work: DataRef}
preconditions:
  - safe_stop_declared_or_completed(work)
outputs: {stopped: Verdict}
state_effects: [terminated_at_safe_stop]
prohibited_effects: [mid_critical_section_abort]
failure_semantics: [let_complete_with_report]
concurrency: {immediate: true}
resource_accounting: [compute_time]
evidence_requirements: [safe_stop_point]
```

```yaml
instruction: EMIT
inputs: {message: MessageRef, channel: ChannelRef}
preconditions:
  - channel_declared(channel)
outputs: {queued: Measure}
state_effects: [queue_append]
prohibited_effects: [unsequenced_emit]
failure_semantics: [drop_with_report_if_bounded]
concurrency: {append_only: true}
resource_accounting: [bandwidth]
evidence_requirements: [channel_ref, seq]
```

```yaml
instruction: RECEIVE
inputs: {subscription: SubscriptionRef}
preconditions:
  - subscription_active(subscription)
outputs: {message: MessageRef}
state_effects: [cursor_advanced]
prohibited_effects: [loss_guarantee_beyond_contract]
failure_semantics: [empty_on_timeout]
concurrency: {at_least_once_where_declared: true}
resource_accounting: [bandwidth]
evidence_requirements: [subscription_ref]
```
