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

The fixture column below records earlier reference coverage. Actual bounded
runtime behavior and its tests are described in section 21.9; neither suite
alone discharges the remaining full-runtime obligations.

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

## 21.8 Library and repertoire payloads

These are ordinary versioned DataRef records, not new kernel instructions.
LibraryEntry: identity/revision, typed parameters and scope guards, functional
contract, lowering graph, expanded primitive bound, dependency versions,
construction lineage, validation/expiry, cost model and retirement disposition.
RepertoireEntry: organization manifest/artifact refs, lineage, measured behavioral
descriptor/schema revision, context support, uncertainty, validation/expiry,
dependencies, carrying/reuse costs and retention-policy revision.

A case stores intervention experience; a library entry supplies executable
abstraction; a repertoire entry preserves an alternative organization. Preserve
these kinds when cross-linking records. Changing an active search library is
a staged policy/configuration revision; library membership cannot publish an
artifact, issue a permit or bypass dependency checks. Record retention and
deletion use section 21.6; descriptor/guard changes preserve prior revisions.

## 21.9 First executable profile

Implementation scope: a local, trusted-operator Python API with one authority
owner and a SQLite rollback journal, not the complete eventual Core. No external
service, learned model, arbitrary provider code or distributed authority is added.
The selected data engine is reversible prototype infrastructure; records and
service ports keep storage policy separate from task/provider computation.

| State/responsibility | Owner / source | Actual boundary |
|---|---|---|
| Shared data contracts | contracts.py | Typed ProviderRunner/ReceiptEndpoint ports; immutable PermitScope excludes payloads |
| Durability, ownership, record integrity | storage.py | OS file lock; explicit SQL transactions; FULL synchronous; record checksums and hash-linked events |
| Budgets/holdings | resources.py | Atomic reserve/convert/charge/release, principal checks, released tombstones |
| Evidence and adjudication | evidence.py | Expiry, pending challenges, verdict-only verification, scoped restoration without permits |
| Authority | authority.py | Opaque recorded permit references bound to principal, target, provider, operation, context, digest, epoch/revision and expiry |
| Artifact identity | registry.py + providers.py | Independently hashed, fixed deterministic catalogue; unknown/different artifacts rejected |
| Publication | transactor.py | Prepared -> validated -> committed -> published; base/epoch/evidence CAS and bounded validation |
| Task/invocation state | execution.py | Admission and output checks, task-bound allocations, recorded failure and terminal results |
| Signal execution adapter | runner.py + worker.py | JSON protocol and subprocess timeout; no authority policy inside provider algorithms |
| Effect state / external receipt | gateways.py / effects.py | Fresh authorization, persistent intent, UNKNOWN outcomes, separate idempotent local endpoint and reconciliation |
| Restart | recovery.py | Advance epoch, revoke old starts, settle interrupted invocations, preserve unknown effect holds, finish committed publication |
| Composition and demonstration | runtime.py / __main__.py | Explicit collaborators; handwritten parse/total workflow and validated replacement |

Source paths are under src/brainos/. Services expose transaction-scoped methods
with `_tx` suffix where an encompassing storage transaction is required. Store
writes reject missing transactions. Authority consumes a PermitScope constructed
by execution/gateway services and does not hash or inspect task signal bytes.

Technology evidence: CPython 3.12.10, bundled SQLite 3.49.1 and build tooling
setuptools 78.1.0 were inspected locally. The runtime uses standard library only;
PyYAML remains an existing documentation-validator dependency. SQLite transaction
and filesystem assumptions are from its [atomic commit documentation](https://www.sqlite.org/atomiccommit.html)
and Python's [sqlite3 interface](https://docs.python.org/3/library/sqlite3.html).
Alternatives considered: predecessor JSON/checkpoint files lack the required
multi-record atomic ledger without additional machinery; a server database adds
deployment work unnecessary for this single-owner slice. Revisit SQLite if
distributed writers, remote storage or production-scale concurrency are required.

```json stack
{
  "brief": {
    "outcome": "Durable single-owner task, effect, recovery and replacement slice",
    "tags": ["local-runtime"],
    "innovation_budget": 1,
    "futures": ["Additional provider families", "Concurrent task execution", "Distributed ownership later"]
  },
  "layers": {
    "data": {
      "status": "accepted", "choice": "SQLite rollback journal",
      "provides": ["transactional-writes", "embedded-single-writer"],
      "assumes": {"runtime": ["sqlite-driver"], "platform": ["local-durable-files", "os-file-locks"]},
      "novel": true,
      "candidates": [
        {"name": "SQLite rollback journal", "provides": ["transactional-writes", "embedded-single-writer"], "assumes": {"runtime": ["sqlite-driver"], "platform": ["local-durable-files", "os-file-locks"]}, "novel": true},
        {"name": "Predecessor checkpoint files", "provides": ["local-file-store"], "assumes": {}, "novel": false}
      ]
    },
    "runtime": {
      "status": "accepted", "choice": "Python standard library",
      "provides": ["python", "sqlite-driver", "bounded-subprocesses"], "novel": false,
      "candidates": [{"name": "Python standard library", "provides": ["python", "sqlite-driver", "bounded-subprocesses"], "novel": false}]
    },
    "interface": {
      "status": "accepted", "choice": "Local Python services and typed process ports",
      "provides": ["local-api"], "assumes": {"runtime": ["python"]}, "novel": false,
      "candidates": [{"name": "Local Python services and typed process ports", "provides": ["local-api"], "assumes": {"runtime": ["python"]}, "novel": false}]
    },
    "platform": {"status": "keep-current", "choice": "Local Windows filesystem", "provides": ["local-durable-files", "os-file-locks"], "novel": false},
    "client": {"status": "out-of-scope"},
    "crosscut": {"status": "keep-current", "choice": "Trusted local host identity; no network authentication", "provides": ["trusted-operator"], "novel": false}
  },
  "rules": []
}
```

Assurance scope: verification/reliability/operations are raised by durable
records; security/maintainability by authority and adapter boundaries. There
are no real external effects, money, personal data, network service or declared
hard availability target in this profile. Tests match claims, not whole-architecture
coverage. Selected checks live in tests/test_core.py and tests/test_crash_recovery.py:

| Claim | Failure/control | Executed acceptance evidence |
|---|---|---|
| One active authority owner | Second open refused by OS lock | Same-process owner rejection; real child death releases ownership |
| No stale or wrong-scope starts | Principal/task/content/revision/expiry/revocation checks | Wrong principal/task, forged handle, content tampering, same-epoch revoke and restart tests |
| No half-published manifest | SQL atomic pointer/journal; recovery completes publication | os._exit before/after manifest commit; stale competing candidate rejected |
| Validation cannot monopolize authority control | Pin under a short transaction, compute without the store lock, recheck before accepting | Paused runner with concurrent epoch cut; stale validation rejected |
| No silent double spend/refund | One conversion; durable holding state; tombstones | Concurrent reservations, mixed operation conservation, repeated release, failure/restart charges |
| No duplicate confirmed simulated effect | Separate endpoint idempotency; UNKNOWN and receipt lookup | Child death before/after target apply; lost acknowledgment; changed-key payload rejected |
| No model framework in Core | Standard-library dependency boundary | AST import fitness checks; authority excludes signal execution imports |
| Bounded catalogue worker invocation | Subprocess timeout and input/output size/type checks | Actual deadline, malformed input, worker error and terminal-state tests |

Costs/limits: task/effect resource vectors account for declared work grants;
latency is recorded, but CPU, RAM, GPU, energy and adversarial process resource
limits are not enforced. Validation is capped at 64 cases and ten seconds of
worker budget, with attempts/elapsed time in the journal; it uses a separate
trusted bootstrap grant, not task-budget charges. Timeouts depend on OS process
startup/termination and are not certified hard real-time L_rev guarantees.
Process separation is not a sandbox for hostile code. Host/operator APIs can
ingest certified evidence and verification verdicts; they do not implement an
authentication system or independent verifier framework yet.

Arbitrary task DAGs, queues/backpressure, safe cancellation of arbitrary running
providers, snapshots/freshness across streams, generic footprint enforcement,
policy/criteria versioning, evidence deletion/GC, all 37 instruction dispatches,
and learned construction remain open. Unknown effects without a target receipt
stay UNKNOWN with funds held; no blind retries or fabricated outcomes. Local
SQLite crash tests do not certify arbitrary network filesystems, power-loss
hardware behavior, malicious database administrators, or distributed failover.

Predecessor reuse: inspected Z:/newbrain/src/brainos/kernel.py and registry.py
and tests/integration/test_kernel_txn.py for transaction race/fallback scenarios.
No neural registry/runtime code or inherited test result was copied into Core;
those scenarios were reimplemented against current service contracts. Existing
uncommitted research-document edits were preserved. Schema version 1 is new;
unsupported versions fail closed, with no destructive migration of old projects.

## 21.10 Corrective pass and first developmental composition

Scope: resolves review findings B01-B06 against the committed first profile
(08cdd17), adds the smallest typed computational fabric, and runs the first
bounded composition experiment (Doc 27 section 27.6). All six findings were
reproduced on the baseline before fixing (docs/results/, baseline-findings.json).
The profile stays trusted-catalogue, single-authority and standard-library only.

| Finding | Contract now enforced | Owner |
|---|---|---|
| B01 zero-cost execution | Execution grant derived from the trusted spec `cost`; caller amounts below it are refused; one attempt is spent at invocation start, later graph nodes pay at their boundary, unspent remainder is released | execution.py, resources.py `spend_tx` |
| B02 effect authorization race | The durable `DISPATCHED` commit is the linearization point. Revocation, challenge or publication committed before it prevents application; after it they cannot recall the admitted effect. `dispatch_admission` (epoch, revision, endpoint) is recorded separately from `CONFIRMED` receipts | gateways.py |
| B03 validation accounting | Validation reserves `cases x cost` from a durable ledger budget (kernel `_kernel_validation` budget, or a caller budget), spends per case, refunds the rest, and recovery releases interrupted validation holdings | transactor.py, runtime.py, recovery.py |
| B04 artifact identity | Each primitive is identified by its own code digest, version, declared shared-dependency digests, schema, units, cost and footprint; unrelated catalogue edits keep other identities | providers.py |
| B05 endpoint identity | Endpoints persist a stable `endpoint:<uid>` identity; effects target it, receipts carry it, and a same-name impostor is refused at dispatch and reconciliation | effects.py, gateways.py |
| B06 evidence scope | Consequential evidence must carry a support scope equal to {task, target, operation, context, claim digest}; checked at permit issue and at dispatch | evidence.py, authority.py |

Fabric (graphs.py, fabric.py, registry.py): bounded unary DAGs (1-16 primitive
nodes) with exact schema/unit connections and identity-only adapters; forward,
cyclic and duplicate references refused; composite identity is a digest of its
normalized nodes and dependency identities; intermediate results are owned
records with provenance; `impact` propagates support/resource/failure-domain
effects to dependent composites and `exclude` blocks dependent use; running
tasks cancel at the next pure node boundary with terminal `CANCELLED`.

Developmental compilation (development.py): a `CapabilityDemand` (input/output
schema plus development examples) drives budgeted breadth-first typed search
over active primitives. Development examples nominate; separate admission cases
validate through the transactor on a separate budget; the composite is
published as a new role without rebinding parents. Every trial (rejected,
nominated, acquired, non-attainment) is a retained `construction` record.
Baselines: typed search vs memoized search (same nominations, fewer attempts).
This is bounded composition over a trusted catalogue: no primitive invention,
open-ended intelligence or superiority claim.

Storage schema is now version 2; version-1 stores are refused (fail closed, no
migration). Remaining limits from section 21.9 still apply; nested graphs,
non-identity adapters, scheduling/backpressure and learned abstraction remain open.

## Assurance

Screen: verification T1 (build); reliability T1 (schema); operations T1 (schema); maintainability T1 (new_boundary); others T0

| ID | Discipline | Claim | Could fail by | Control (owner) | Check | Evidence |
|---|---|---|---|---|---|---|
| A-1 | verification | No task executes on a zero or below-requirement grant (B01) | Caller-supplied `{"attempts": 0}` amount | Grant derived from trusted spec cost; spend at invocation start (execution.py, resources.py) | tests/test_corrective.py B01MinimumGrant | tested |
| A-2 | verification | Control changes before durable dispatch admission prevent application; after admission they do not recall it, and admission is recorded apart from confirmation (B02) | Revocation/challenge/publication racing between check and endpoint call | Single-transaction admission commit is the linearization point; `dispatch_admission` record (gateways.py) | tests/test_corrective.py B02DispatchLinearization | tested |
| A-3 | reliability | Candidate validation spends a durable, bounded grant that survives restart and refunds unspent work (B03) | Validation outside the ledger; holdings leaked on crash | Validation holdings in the ledger; kernel validation budget record; recovery release (transactor.py, recovery.py, runtime.py) | tests/test_corrective.py B03ValidationAccounting | tested |
| A-4 | maintainability | Changing one primitive does not change other primitives' artifact identities (B04) | Whole-file catalogue hash | Per-function code digest + version + declared dependency digests (providers.py) | tests/test_corrective.py B04ArtifactIdentity | tested |
| A-5 | reliability | Effects bind to a stable endpoint identity; a same-name endpoint cannot receive or reconcile them (B05) | Name collision between receipt stores | Persisted endpoint identity; receipt carries endpoint (effects.py, gateways.py) | tests/test_corrective.py B05EndpointIdentity | tested |
| A-6 | verification | Consequential evidence must exactly support task, target, operation, context and claim (B06) | Unrelated Certified evidence accepted | Required support scope checked at issue and dispatch (evidence.py, authority.py) | tests/test_corrective.py B06EvidenceScope | tested |
| A-7 | maintainability | Graph connections are exactly typed; forward/cyclic/duplicate refs and unsupported adapters are refused; impact propagates to dependents | Loose schema matching; nested graph loops | graphs.specification, registry.exclude, fabric.impact (graphs.py, registry.py, fabric.py) | tests/test_corrective.py TypedFabric | tested |
| A-8 | verification | A demanded capability is discovered, independently validated and published without altering parents; failures are retained; non-attainment is reported | Development examples reused for admission; parents rebound | Separate admission cases and validation budget; construction records (development.py) | tests/test_corrective.py DevelopmentalCompilation | tested |
| A-9 | operations | Existing behavior, crash recovery and demo still hold; storage schema v2 fails closed on unknown versions | Regression from contract changes | Existing suites (tests/) | tests/test_core.py tests/test_crash_recovery.py | tested |
