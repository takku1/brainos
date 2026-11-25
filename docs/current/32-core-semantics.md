# 32 - Core Operational Semantics

Status: partial — some requirements are built (Doc 31 register; Doc 21 section 21.0); the rest is specification, not implementation.

Doc 09 owns instruction signatures and allowed effects; Doc 21 owns shared
records; this document owns runtime protocols; Doc 29 owns impact semantics.
Conflicts require coordinated edits, not precedence based on document age.
Research policies use these interfaces without extending the trusted kernel.
The reference tools cover selected behaviors, not a production runtime.

## 32.1 Transition kinds and execution envelope

Mechanisms declare deterministic (D), stochastic (S), nondeterministic (N),
or externally dependent (X) behavior per invocation. Compound operations
declare their stages. Instruction names alone do not determine the kind.

| Instructions | Kernel stage | Computation/environment stage |
|---|---|---|
| OBSERVE, ASSERT, CHALLENGE, RETRACT, RESTORE, QUARANTINE | D record/eligibility transitions | Observation acquisition and validation may be X |
| ENCODE, INFER, PREDICT, REVISE, COMPARE, LEARN | D result registration | D/S/N/X declared by mechanism |
| PROPAGATE | D dependency traversal | Recomputations declare their kinds |
| VALIDATE, BENCHMARK, VERIFY | D verdict registration | D/S/N/X by evaluator family |
| FORK, CONSOLIDATE, SNAPSHOT, COMMIT | D metadata/publication | Artifact creation/storage failures recorded separately |
| BIND, CONNECT, REBIND | D staged edits | Active configurations publish through COMMIT |
| SPAWN, CANCEL | D intent/lifecycle updates | X startup/stopping where outside runtime control |
| AUTHORIZE, REVOKE, RESERVE, ALLOCATE, RELEASE | D ledger transitions | Enforcement acknowledgments separately observed |
| ACT | D admission/intent | X external effects or declared internal computation |
| EMIT, RECEIVE | D queue/cursor changes | X transport delivery/arrival |
| BIRTH, DIFFERENTIATE, FUSE, RETIRE | D admission/publication | Construction/evaluation per Docs 24/27; developmental verification deferred |

Use Doc 21's operation envelope to pin identity, task, mechanism, manifest,
snapshot, context, budget, deadline, and effect policy. Retries retain logical
operation IDs and create separate attempt IDs. Record randomness when
available; a seed does not establish deterministic hardware or remote services.
Missing required envelope fields or undeclared kinds cause rejection.

## 32.2 Control/signal separation (G-01)

The supervisor consumes capability metadata and grounded control facts,
not raw provider payloads or private state. A provider may derive a control
fact from payload content; the derivation carries provenance and ordinary
evidence checks. This permits content-dependent decisions without putting
signal computation in the supervisor.

Probe input accesses during authorization: allowed metadata, rejected raw
payload access, unknown/missing fields, and at least one successful permit.
Instrument accesses at the actual boundary. Cooperative self-reporting alone
is only a stub-level check; timing side channels are outside this probe.

## 32.3 Authority ownership and deployment profiles (G-02)

The first implementation has one authority process and a durable manifest,
epoch, and permit ledger. Distributed compute/readouts do not imply
distributed authority. Concurrent proposals use manifest-revision CAS.
Restart advances the durable epoch before admission and reconciles old work
under section 32.12. Old permits cannot start new work.

A future failover profile requires an exclusive owner established by an
explicit coordination protocol, durable monotone fencing tokens, and effect
endpoints rejecting obsolete tokens. Deterministic replicas establish equal
decisions for equal inputs, not exclusive ownership during a partition.
Without enforceable fencing, use single ownership and manual recovery.
Failure detection, clock/lease assumptions, partition behavior, handoff,
and draining require specification and tests before failover support.

## 32.4 Permits, invocation state, and stopping (G-03)

AUTHORIZE creates a trusted ledger record with the bindings in Doc 21.
Handles are opaque references: caller-visible values cannot alter authority.
The effect gateway checks principal, instance/artifact, operation scope,
task/context, manifest, epoch, evidence/policy, expiry, and budget on use.

Invocation lifecycle: ADMITTED -> RUNNING -> COMPLETED or FAILED;
cancellation adds STOP_REQUESTED -> STOPPED. REVOKE denies starts immediately,
including in the issuing epoch. Only a previously recorded RUNNING invocation
may drain to its declared safe stop. IDs cannot restart completed work.
Drain never authorizes an additional consequential effect.

Each consequential boundary requires a fresh kernel check and boundary
authorization bound to operation ID, payload digest, target, current evidence,
expiry, and fencing token where applicable. A provider-supplied boolean is
not authorization. Failed checks trigger the declared stop/degradation.

Contracts declare safe-stop points, time-to-stop bounds, and noninterruptible
sections. Admission of noninterruptible work requires remaining worst-case
duration within deployment L_rev, or rejects the work. Trusted enforcement
monitors deadlines/stops/resource caps; replaceable scheduling policy only
proposes priorities. Enforcement cannot undo effects already performed.

## 32.5 Evidence and provider lifecycles (G-04)

Tier, validity, provider lifecycle, and authority are separate fields.
Verdicts do not themselves change status or grant permission.

| Current state | Event and guard | Result |
|---|---|---|
| Claim ASSERTED/RESTORED | CHALLENGE with recorded grounds | CHALLENGED; dependent authority suspends at next epoch cut |
| Claim CHALLENGED | VERIFY with declared procedure | Append verdict; remains CHALLENGED |
| Claim CHALLENGED | Kernel RESTORE accepting current scoped proof | RESTORED; recompute eligibility, no permit |
| Claim ASSERTED/RESTORED/CHALLENGED | Kernel RETRACT with cause | INVALIDATED or WITHDRAWN; distinguish causes |
| Provider CANDIDATE | VALIDATE with current isolated checks | VALIDATED candidate or failed/quarantined candidate |
| Provider VALIDATED candidate | COMMIT with fresh impact verdicts and CAS | ACTIVE new artifact version |
| Provider ACTIVE | QUARANTINE after challenge/failure | QUARANTINED; deny new work in effective exclusion scope |
| Provider QUARANTINED | RESTORE on proof the same artifact is eligible | ACTIVE eligibility; no permit or new-artifact publication |
| Provider QUARANTINED | Rebuild requested | New CANDIDATE; original stays quarantined |
| Provider ACTIVE/QUARANTINED | RETIRE after coverage/fallback checks | RETIRED version; lineage retained |

RESTORED claims can be challenged again. Invalidated/withdrawn versions stay
historical; new support creates an explicit successor. Restoration proofs
identify target/version/scope, evidence epoch, evaluator, criteria, and expiry.
Mismatched/stale proofs are rejected; inconclusive verdicts leave challenges
open. RESTORE never bypasses COMMIT for a rebuilt artifact or AUTHORIZE for
an operation. Ecological reconstruction (Doc 24 RESTORE) is a compound
construction/validation/COMMIT workflow, not this eligibility instruction.

Challenges record immediately, with dependent-authority suspension at the
next bounded epoch cut (Doc 09 section 9.7). Explicit revocation blocks starts
immediately. Fresh effect checks inspect pending challenges as well as current
validity. Existing work drains only under section 32.4. Impact scope comes
from Doc 29; unrelated work continues.

Repair is a durable workflow: challenge -> exclusion -> isolated construction
-> validation -> COMMIT. Expensive construction is not one long storage
transaction. Publication/authority changes use short atomic transactions.
Races on manifest, evidence, policy, or criteria revisions invalidate stale
validation and require reevaluation of affected scope before retry.

## 32.6 Replay semantics (G-06)

Exact replay requires logged inputs, relevant state, pinned dependencies,
randomness, and a deterministic execution profile. Declare byte equality
or semantic equality under a specified comparison. Pinning versions alone
guarantees neither.

Distributional replay uses a declared stochastic model, repeated comparable
runs, and a preregistered statistical comparison. One plausible output is
insufficient. Nondeterministic runs are checked against admissible sets and
invariants. Recorded external responses may support downstream trace replay,
but do not recreate external outcomes or causal counterfactuals.

Replay is unavailable for a claim when required state is missing or an
intervention changes subsequent observations. Use fresh controlled execution
where valid; otherwise report inconclusive. Retained invalidated evidence can
support historical reproduction, never current authority. Declare purpose,
mode, assumptions, comparison, and limits; Doc 28 governs causal admissibility.

## 32.7 Trusted enforcement boundary

Trusted responsibilities: identity/registry; eligibility; manifest transactions;
permit checks; evidence/provenance integrity; resource reservations and
measured-use enforcement; stop/deadline enforcement; impact computation;
durable journal/checkpoint recovery; and effect gateway. Implementations
may combine these responsibilities without adding architectural layers.

Providers, planners, evaluators, candidate generators, and scheduling policies
cannot bypass enforcement. Evaluator replaceability does not eliminate trust
in scoped acceptance criteria and grounding policy (Docs 23/30). Footprints
are audited and unknowns conservative. An enforcement fault blocks affected
effects, records the failure, and permits independent work where valid.

## 32.8 Threat and failure scope

The first profile covers invalid provider inputs, forged/misbound permits,
stale manifests/verdicts, duplicate requests, evaluator contamination,
undeclared dependencies, overruns, process crashes, and uncertain external
operations. Test invalid inputs and enforcement bypass at trusted boundaries.
Untrusted candidate execution needs actual process/resource isolation;
declarations alone provide none. Network adversaries, kernel supply-chain
compromise, and timing side channels require a separate deployment profile.

## 32.9 Impact computation and termination

Doc 29 owns impact semantics. `tools/dep_closure.py` models conservative
provider reachability through directional dependencies and symmetric footprint
intersections; it does not classify impact actions or verify declarations.
Empty change yields empty closure even with unknown unrelated footprints.
Unknown members of a nonempty closure expand over the known population.

For N known providers, monotone expansion has at most N growth passes plus
one equality check. Cycles are valid and terminate. Cap exhaustion means
incomplete computation/configuration, not a defective cycle. Use a pinned
finite registry revision; new nodes require a fresh computation. Unknown
node discovery outside the pinned universe triggers registry repair/retry.

## 32.10 Conformance coverage

Doc 21 section 21.3 owns the coverage matrix. The harness and regression
suite cover selected in-memory behaviors, not durability, isolation, bounded
stopping, full schema execution, or distributed ownership. A passing count
does not close untested obligations in Doc 31. Tests use observable outcomes
and invalid-input controls rather than recognizing the defective class.

## 32.11 Task orchestration

Tasks (Doc 21) carry owner, goal, criteria, context, budget, deadline,
dependencies, and result destination. CREATED -> READY when prerequisites
resolve -> RUNNING on admitted work -> SUCCEEDED, PARTIAL, FAILED, or
CANCELLED after in-flight disposition. BLOCKED names missing evidence,
resources, or inputs plus a retry condition; it is not success or a busy loop.
Terminal records retain outputs/effects; retries are linked attempts.

A planner proposes a versioned task graph; a scheduler selects ready work;
the supervisor checks eligibility; AUTHORIZE grants scoped permission; the
executor records invocation/effect outcomes. A plan cannot grant authority.
Cycles require bounded iteration and termination criteria. Concurrent tasks
declare priority and budget ownership; goal relaxation/budget transfer require
explicit policy. Bounded queues declare rejection/coalescing/drop rules;
critical inputs are never silently dropped. Cancellation propagates through
dependent tasks, releases unspent reservations, and reconciles effects before
assigning terminal status. The initial planner is a handwritten workflow.

## 32.12 Crash recovery and external effects

Durably record operation/attempt IDs, pinned versions, reservations, and effect
policy before work. Configuration publication follows PREPARED -> VALIDATED
-> COMMITTED -> PUBLISHED. The manifest pointer and commit record become
durable atomically; notifications retry using that revision. Before commitment,
a crash leaves the old manifest active and staged candidates need disposition
or revalidation. After commitment, recover the committed revision, never a mix.

Effects follow INTENT -> DISPATCHED -> CONFIRMED, FAILED, or UNKNOWN. Persist
intent and authorization scope before dispatch. A lost acknowledgment is
UNKNOWN, not failure. With durable target idempotency, retry the same logical
ID and payload; reject ID reuse with changed payload. Otherwise reconcile
through target query or explicit operator policy before a potentially duplicate
retry. Arbitrary external targets have no exactly-once guarantee. Compensation
is a new authorized effect, not history reversal.

Recovery order: verify journal/checkpoints; acquire single ownership and advance
epoch; reconcile uncertain operations; reconstruct held budgets; release orphaned
unspent reservations only after reconciliation; revalidate expired evidence and
staged candidates; reopen admission. Journal each disposition. Crash-injection
tests cover persistence/dispatch boundaries. Reference tools do not implement
this durable protocol.

## 32.13 Organizational adaptation as an ordinary workflow

Doc 19's model is an untrusted replaceable provider. Use ordinary INFER/PREDICT
over authorized projections/history and typed payload records (21 section 21.7).
The planner emits task/transform proposals; the executor reserves resources,
pins current revisions, executes one admitted step in isolation, evaluates,
and publishes validated artifacts through existing protocols. Record the
pretrial prediction and actual disposition even when construction fails.

Replan after each measured outcome. A hypothetical successor state supplies
no current eligibility, resource balance or permit. Actual prefix constraints,
pending challenges and evidence expiry are checked at each step. A model version,
guard or search-policy revision is a new candidate; authority/evaluation-policy
changes retain their separate governance. The first experiment excludes trusted
kernel self-modification and arbitrary generated code. Core deployments need
not install organizational models to conform.
