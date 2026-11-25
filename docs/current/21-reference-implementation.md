# 21 - Reference Implementation Specification

This document owns shared records and reference-profile choices. Doc 09 owns
instruction signatures; Doc 32 owns protocols; Doc 17 owns capability contracts.
The records below specify required fields and validation rules. They are not
yet an executable serialization library. IDs are typed, immutable references;
wire encoding must preserve type, schema revision, and identity on round trip.

## 21.1 Shared records and type definitions

Every reference resolves to a versioned record of its declared kind. Missing,
wrong-kind, stale, or unauthorized references fail before invocation. Lists
validate each element. Optional fields are explicitly absent, never silently
filled from a different manifest. Measures carry value, unit, and comparison
semantics; estimates additionally state uncertainty and calibration scope.

| Doc 09 type | Meaning / required record contents |
|---|---|
| OperationRef | Operation ID, attempt ID, principal, task ID, provider instance/version, mechanism/version, arguments digest, context, manifest, snapshot refs, kind, deadline, budget/holding refs, effect policy |
| EvidenceRef | Source, immutable payload ref/hash, context, time/clock domain, provenance/support refs, evidence revision, validity interval, tier and validity |
| VersionId | Immutable artifact/schema/policy identity in an explicit namespace; includes content digest or registry mapping |
| ManifestRef | Graph revision, bindings, provider/adapter versions, evidence revision, policy/criteria revisions, context, epoch, compatible snapshot set |
| EpochId | Monotone authority generation within a named authority domain |
| SchemaId | Encoding/grammar, shape where relevant, units/frames, tolerances, revision |
| CapabilityRef | Capability identity resolving through Doc 17's registry |
| ProviderRef | Unique runtime instance, artifact version, supported contracts, lifecycle, state ownership, footprint, resource/stop declarations |
| ClaimId | Claim statement/version, context, support refs, status, tier/validity, challenge/adjudication records |
| ContextRef | Versioned task/deployment conditions, input distribution assumptions, risk and freshness constraints |
| BudgetRef | Owner, resource dimensions/units, limits, held/committed/spent balances, revision |
| ReservationRef | Owner/purpose, budget, amount vector, expiry, HELD/CONVERTED/RELEASED status |
| AllocationRef | Reservation lineage, resource grant, measured spend, unspent balance, status |
| BudgetHoldingRef | Tagged ReservationRef or AllocationRef, including released tombstone |
| BindingRef | Role/contract, provider instance/version, context and manifest revision |
| EdgeRef | Endpoints/versions, adapter/schema, channel policy, footprint, revision |
| StreamRef | Publisher, schema, sequence domain, clock domain/skew bound, retention policy |
| ChannelRef | Endpoints/schema, capacity, ordering, retry/deduplication and overflow policy |
| MessageRef | Payload ref/hash, source version, context, timestamp/clock domain, sequence, support refs |
| SubscriptionRef | Channel, consumer, cursor, delivery guarantees, timeout, lifecycle |
| StateRef | State artifact, schema, owner, version, context, provenance, freshness |
| SnapshotRef | Immutable compatible state refs, timestamp/clock domain, sequence, manifest/evidence revisions, provenance |
| StateEstimate, Estimate | Target/state estimate, context/horizon, uncertainty model, support/calibration refs, version |
| Measure | Typed scalar/vector with units, sampling window and uncertainty where sampled |
| Verdict | PASS/FAIL/INCONCLUSIVE, target/version/scope, criteria/evaluator versions, evidence revision, measurements, grounding, expiry |
| PermitRef | Trusted ledger identity bound to principal, task/context, provider instance/version, operation/argument scope, manifest/epoch, evidence/policy refs, expiry, budget, revocation and invocation state |
| ProcedureRef | Executable evaluation procedure/version, criteria, data-access and termination rules |
| RecipeRef | Construction/rebuild steps, parent/data refs, parameters, randomness, environment assumptions |
| PolicyId | Versioned authority/selection policy with scope, owner and expiry |
| CostVector | Measured/estimated resource dimensions with units and uncertainty; scalarization only per Doc 20 |
| CandidateRef | Isolated artifact/version, nomination/construction refs, parents, validation state, reservation and disposition |
| DataRef | Immutable typed data reference, schema, digest, owner and access policy |
| PropertyRef | Named check, target domain, tolerance/floors, evaluator family, procedure/version |
| RestoreTargetRef | Tagged ClaimId or ProviderRef; target/version/scope must match restoration proof |

Task records (no new instruction required): task ID/version, owner/principal,
goal, acceptance criteria, context, priority/deadline, budget ownership,
dependency graph, planned operation refs, status/retry condition, outputs,
effect dispositions, and lineage. Lifecycle is in Doc 32 section 32.11.

## 21.2 Protocol ownership and first reference profile

Doc 32 owns invocation, epoch, publication, recovery, and effect protocols.
First profile: one authority process; local transactional durable journal;
typed immutable artifacts referenced from that journal; process-isolated
candidate workers; handwritten task graphs; bounded local queues; a measured
resource ledger and effect gateway. Storage engine and wire encoding are
implementation choices subject to crash and round-trip tests, not unspecified
behavior. Remote APIs declare independent version/delivery/effect contracts.

Graph/binding changes are staged, validated, and published through COMMIT.
CONSOLIDATE makes an artifact durable without changing the active manifest.
SPAWN creates an instance but does not make it eligible or authorized. Registry
admission checks artifact identity independently of provider self-report.

## 21.3 Conformance coverage matrix

| Obligation | Current reference evidence | Still required for runtime conformance |
|---|---|---|
| L1-C1 signatures/types | Gate 1 structural validator; calculator fixtures | Resolve/type-check operation records, enforce predicates/effects, fuzz boundaries across independent implementations |
| L1-C2 lifecycle | Permit/regression fixtures; epoch challenge check deferred | Challenge-at-cut, repeated challenge/restore, verdict-only VERIFY, staged publication, cancellation and bounded drain |
| L1-C3 resources | Harness arithmetic examples only | Durable reservation conversion/release, ownership, concurrent overdraft/double-spend, measured overruns, restart recovery |
| L1-C4 versions | Registry/version-denial fixtures and closure reference model | Manifest CAS, incompatible snapshot rejection, crash consistency, restored-version correctness |
| L1-C5 authority | Scoped opaque-handle fixtures, revoke/drain and effect-boundary checks | Real trusted gateway, current-evidence checks, expiry/clock/fencing tests and enforcement bypass attempts |

`tools/test_reference_regressions.py` tests observed permit/closure defects;
`tools/l1_harness.py` is a partial in-memory behavioral harness. Passing them
does not close the last column. Bad inputs must be rejected by the same
admission/execution path used for good inputs, not identified by class names.
Doc 07 separates conformance, deployment qualification, and research benefit.

## 21.4 Dependency rule

Core packages do not require torch/CUDA, model APIs, simulators, or embedding
models. Providers own those dependencies. Enforce this with dependency lint
when a build exists. A deployment may include framework-specific providers
without making that framework a prerequisite for the kernel.

## 21.5 Reservation and release semantics

RESERVE moves an amount from available to HELD atomically, checking resource
dimensions, nonnegative quantities, owner/purpose, and total limits. ALLOCATE
converts a live reservation once; it does not debit the same amount again.
Measured usage consumes allocation balances and is never refunded as unspent.
RELEASE accepts a held reservation or allocation: return only its unspent
balance once, retain a tombstone, and return ALREADY_RELEASED on repeat for
the same owner. Unknown or wrong-owner references fail. Converted reservation
release points to the allocation and cannot refund it independently. Expiry
and crashes follow reconciliation in Doc 32, not automatic silent refunds.

## 21.6 Artifact retention and bounded history

Append-only means retained records are not rewritten, not infinite storage.
Distinguish compact audit metadata, executable artifacts, training payloads,
and active runtime state. Define per-class retention horizons, legal/policy
deletion obligations, access control, encryption/secret handling, and garbage
collection roots. Active manifests, live proofs, unresolved effects, protected
capabilities, and declared rollback windows pin their needed records.
Reclaim payloads only after readers drain and dependencies/repair guarantees
are updated; preserve permitted tombstones/digests and report unavailable
replay or approximate repair. Digests alone do not recreate deleted evidence.
Retention/deletion policies can restrict what is retained; no guarantee of
exact repair survives removal of required history. All carrying costs use
Doc 20's existing ledger rather than a separate economic model.

## 21.7 Transformation and prediction records

These are typed DataRef payload schemas used by ordinary adaptation providers;
they add no instruction, trusted subsystem or mandatory Core service.

TransformationRecord fields: record/attempt IDs; source manifest/organization
projection and relevant history; goal and workload context; matched graph/interface
pattern; transformation/parameters and applicability assumptions; declared impact
footprint; pretrial PredictionRecord ref or explicit absence; intervention
assignment/evaluation protocol; actual observations and uncertainty; outcome
status; complete cost records; recovery/disposition; support, versions and expiry.
Outcome status distinguishes proposed, rejected-before-execution, cancelled,
executed-success, executed-failure, non-construction, budget-non-attainment,
and unresolved/pending. Missing observations are not fabricated negative labels.

PredictionRecord fields: target intervention or conditional sequence; source
revision; feature/projection schema; context/horizon; model/guard versions;
predicted outcome distribution/bounds or UNRESOLVED; support and dependencies;
calibration scope; validity/expiry; and pretrial timestamp/sequence. Outcomes,
prediction errors and revisions append linked records rather than overwriting
what the model predicted before the trial. Separate observation, applicability
hypothesis and verified property in the record kind.

Plan records use existing task graph/envelope types (32 section 32.11) with
ordered/conditional transformations, named sub-demands, prefix constraints,
budget/horizon, predicted outcomes, next executable step and abandon/replan
conditions. Later-step references are speculative until their prerequisites
actually hold. History retention/access/deletion follows section 21.6; guard
broadening creates a new version requiring independent evaluation.
