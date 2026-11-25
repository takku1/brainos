# 02 — Formal Architecture (generalized)

Status: partial — some requirements are built (Doc 31 register; Doc 21 section 21.0); the rest is specification, not implementation.

## 2.1 System definition

Let the system be N heterogeneous providers:

```text
S = {P_1, P_2, ..., P_N}
```

Minimal provider contract — identity, interface, execution, resource
requirements. Everything else is an optional capability interface;
no provider must pretend to be a neural network:

- Stateful / Stateless (persistent h_i or pure function).
- Trainable (gradient, evolutionary, or symbolic revision — or none).
- Forkable, Composable, Checkpointable, Replaceable.
- Inspectable (reports provenance/uncertainty) and Interruptible
  (safe stopping points declared).
- Developmental (supports BIRTH/DIFFERENTIATE/FUSE/RETIRE ops — or none).

Formal provider model (primary — mathematics generalizes first):

```text
P_i = (I_i, O_i, X_i, F_i, K_i, R_i, V_i)
```

| Symbol | Meaning |
|---|---|
| I_i | Input contracts |
| O_i | Output contracts |
| X_i | Optional internal state (absent for stateless providers) |
| F_i | Computational behavior |
| K_i | Supported capability interfaces |
| R_i | Resource requirements |
| V_i | Version identity |

Execution:

```text
(y_i, x_i') ~ F_i(u_i, x_i, c)
```

Inputs u_i under contracts I_i plus context c produce outputs y_i
under O_i and optional next state x_i'. The ~ admits deterministic,
stochastic, stateful, and stateless providers alike: a neural network
is one realization of F_i; a database query, a symbolic proof engine,
and a stochastic sampler are others. Specialize second, never first.

One common instantiation for stateful learned providers:

```text
h_i^{t+1} = f_{θ_i}(h_i^t, o_i^t, m_i^t)
```

- `o_i^t`: provider observation at t (typed; may be empty).
- `m_i^t`: inbound information from other providers.
- `h_i^t`: private state (never assumed fully shareable).

A stateless API, symbolic solver, database, or stochastic service uses
the minimal contract directly and ignores the stateful equation. A
provider may be an LLM, encoder, analytic solver, controller,
deterministic tool, memory store, learned mechanism, or developmental
unit. No definition mentions embodiment. Integration is incremental:
existing systems implement the contract around their internals without
rewriting them.

## 2.2 Adapters

Providers communicate through published outputs, not internal state.
Versioned directional adapters translate contract-compatible outputs
under a context:

```text
m_{i→j} = A_{ij}(y_i, c)
```

y_i is any contract-compatible output — tensor, JSON record, proof,
graph, program, image, event, or probability distribution — and c is
context (schema version, task, authority tier). Same output shape with
different adapter parameters is a different semantic mapping.
Incompatible endpoints (unaccepted schema or version, no translating
adapter) are rejected at load with rollback. Neural messaging uses an explicitly published projection y_i = Publish(h_i);
adapters read y_i, never private h_i directly.

## 2.3 Shared readout state

A readout state z_t integrates provider outputs:

```text
z_{t+1} = F_ψ(z_t, Aggregate({A_i(y_i, c)}))
```

F_ψ may use attention, recurrence, estimation, typed-record merge, or
a hybrid. It is lossy by design: providers retain private information.
This preserves specialization and bounds what coordination can reason
about. Generalize first: integration operates over published outputs
y_i, never over hidden states h_i.

## 2.4 Active graph and contracts

```text
G_t = (V_t, E_t)
```

Active graph of providers and compatible interfaces at t. Each provider
exposes a capability contract: input schemas, output types plus
confidence semantics, execution constraints (latency, resources, safety),
available operations, and risk tier per operation (reversible vs
irreversible; sets whether Believed or Certified facts authorize it).
Edges exist only where contracts are mutually satisfiable. The
supervisor reasons over this graph; it does not carry payloads.

## 2.5 Separation of paths

- Control path (supervisor): discrete, capability-level; answers what
  combinations are eligible.
- Signal path (fabric): continuous, low-latency, tensor/typed values;
  answers what the content is.

Conflating them yields a symbolic bottleneck or ungoverned execution.

## 2.6 Design invariants

1. Specialization preserved: no objective may collapse all h_i into z
   copies without a competence check.
2. Partial observability: coordination acts on projections, never full
   private state.
3. Local autonomy: safety-critical loops run even if higher layers stall.
4. Provenance required: every fused representation carries source, time,
   confidence, version.

## 2.7 Concurrent multi-task coordination

One logical supervisor authority and any number of readout surfaces
serve many concurrent tasks (e.g. dialogue plus background retrieval
plus a control loop); the supervisor may be federated or redundant
internally provided eligibility semantics stay single-valued, and the
readout is one optional surface among direct links and routed paths
(Doc 04). Tasks carry different
epistemic bars on the same fact store: drafting a reversible reply
proceeds on Believed while an irreversible actuation waits for Certified.
Bandwidth is arbitrated by queries over projections of z_t. Preemption
across tasks uses the same authority-limit rule as control.

## 2.8 Slots, checkpoints, adapters

A slot is an execution-domain interface (contract, cadence, accepted
versions, kind). A checkpoint is a versioned artifact implementing a
slot role, replaceable independently. An adapter translates between
representation versions of published outputs. Memory, certification, and enforcement are
ordinary software slots. Swapping a model never moves certification rules.

## 2.9 Execution model

Slots are execution domains sharing one logical supervisor authority
with zero, one, or multiple readout surfaces — not necessarily OS
processes. Zero readouts is a valid system (direct links only);
multiple readouts are federated projections, never competing
authorities. Scheduler owns deadlines and allocation;
supervisor owns permissions. A fast loop never waits on symbolic closure:
it consumes the latest certified snapshot or falls back. Publication is
atomic immutable S_k = (z_k, t_k, v_k, p_k). Enable, revoke, and preempt
are distinct; safe stopping is part of the contract. Two data pathways:
direct provider links for latency-sensitive coordination and readout
integration for cross-domain cognition.

## 2.10 Async convergence and switching (conditional)

With joint state h and idealized update F, one sufficient (not
necessary) regime for stale-view convergence: F contractive with a
stated norm, stated domain (bounded latent region with enforced
projection), and a uniform bound q < 1 on the contraction factor;
pointwise spectral radius < 1 alone is insufficient in general
(non-normal dynamics can transiently amplify despite stable
eigenvalues). Every required node keeps updating, and old info is
replaced. Non-contractive systems may still converge or operate
usefully without converging; the toy pins one sufficient
regime, not the boundary of safe operation. Switching breaks mode-wise stability: a checkpoint stable when
run continuously need not be stable under switching. Enforced mitigations:
minimum dwell, hysteresis, pinned safe fallback, bounded switching cost.
Scope: these constrain the authoritative core, not speculative workers.

## 2.11 Semantic adapter compatibility

Schema compatibility is necessary but insufficient. An adapter contract states
semantics, units, reference frames, supported contexts, discarded information,
failure behavior, provenance, and uncertainty mapping. Schema hashes identify
encodings, not semantic accuracy. Reject incompatible units/frames without
an explicit transformation.

Validate paired semantic examples, boundary cases, downstream competence,
information loss, shifts, and calibration under pinned source/adapter/consumer
versions. Round-trip checks alone do not establish correctness for lossy
mappings. A stated local differentiable error model may propagate covariance
through its Jacobian; otherwise validate uncertainty empirically or report
it unresolved. Provider/adapter revisions revalidate affected mappings through
Doc 29. The initial experiment uses exact typed schema/unit transformations;
learned latent alignment is a separate experiment.

Operational ownership: Doc 32 sections 32.3 and 32.11 govern the single-owner
initial profile and task orchestration. Federation is a future deployment
profile requiring explicit fencing, not a property of multiple readouts.

## 2.12 External provider adapters (W2 design; specified, not implemented)

One computational ability must be independent of its implementation
substrate: a neural checkpoint and a deterministic program serve the same
capability contract through the same kernel paths. No neural kernel is
built, and language models get no special authority rules. The adapter is
an ordinary external process; the kernel verifies claims about it, never
its weights.

- **Registration (R-02-14).** External providers register through an
  operator-only path that records a pinned artifact digest (see
  `src/models/manifest.json`), declared schemas, units, cost schedule and
  endpoint — not through the trusted catalogue, which stays closed to
  external code. The resulting provider record carries
  `kind: "external"` and is resolved, blocked, selected, charged and
  retired through the identical registry, impact, task, ledger and
  lifecycle paths as any member. Impact `block` enforcement, permit
  scopes and budget dimensions apply unchanged.
- **Execution.** The adapter speaks the existing worker wire protocol
  (verified requests, bounded replies, mandatory timing fields) from
  outside `src/brainos`. Adapter-reported timings are recorded alongside
  kernel-measured wall time; persistent disagreement is evidence, never
  silently corrected. Adapter death, timeout or malformed reply is a
  provider failure: the task is refused cleanly, the failure is
  journaled, and selection observes the cost. No new runner authority is
  created; cancellation and deadlines behave as in Doc 32.
- **Nondeterministic validation (R-02-15).** Exact output equality is the
  wrong gate for a sampler, and a bare success rate is the wrong evidence.
  Admission is empirical evidence, never guaranteed correctness: each case
  runs n times and passes on k-of-n agreement with the expected output
  (declared n, k per provider), and every reported rate carries its
  approximate 95% Wilson score interval — 19 of 20 is an observed 95%
  with an interval of roughly 76–99%, and is recorded as such.
  Membership rows flag nondeterministic providers, and every downstream
  equality check (assimilation union gate, downstream competence) uses
  the consistency form for flagged providers: agreement of the
  deterministic output with the recorded sample set, never single-shot
  equality. Assimilation nominates deterministic providers only;
  nondeterministic members are excluded from candidacy by rule, and the
  exclusion is recorded rather than scored as a failure.
- **Admission records distinguish what was measured.** Per case: the
  independent workload identities, the repeated stochastic draws, the
  sampling configuration and seeds where the runtime supports them, and
  the pinned model, tokenizer, prompt-template and runtime identities.
  Per draw, exactly one outcome: correct, malformed, abstention, timeout
  or failure. Abstention counts as correct only where the contract
  declares abstain outputs; elsewhere it is incorrect. Competence is
  estimated per context and per evaluation set — pooled success never
  conceals weak performance in a required context (the B23 discipline
  applied to providers). Evidence is invalidated by any change to the
  pinned identities or sampling configuration: prior admission evidence
  must be revalidated, checked the same way preregistration digests are
  checked before a run, and stale evidence refuses admission.
- **Semantic interoperability is measured (R-02-13).** Sharing a contract
  is the hypothesis, not the proof. The W2 demonstration (§7.18) records
  admission agreement, output agreement rates on a shared demand sample
  (deterministic output against the adapter's k-of-n set), ecology
  substitution in both directions, and the adapter's self-reported
  confidence calibrated against empirical agreement. Uncertainty that
  cannot be calibrated is reported unresolved per §2.11.
- **Isolation.** The adapter process holds no kernel handles: no store,
  no ledger, no authority. It receives verified requests and returns
  bounded replies. A compromised or faulty adapter can waste its granted
  budget and produce wrong outputs — both priced and observed like any
  provider failure — but cannot mint funding, forge evidence tiers, or
  bypass admission. Placement: adapter clients live outside
  `src/brainos` (see `implementations/`); `src/brainos` gains no
  model-framework imports or accelerator dependencies.
- **Cost schedule and measurement split.** Registration declares the full
  schedule: initialization (model load, one-time), inference
  per request, transport, memory residency, accelerator usage, and the
  kernel-observed organizational overhead. Kernel charges use the same
  budget dimensions as any task; the schedule maps declared native units
  onto them. Both timings are recorded per execution — adapter-reported
  and kernel-observed — and the meter uses the kernel-observed side;
  persistent disagreement is evidence, never silently corrected.
- **Threat model: trusted local adapter.** Process separation alone is not
  a hostile-code sandbox, and this design never represents it as one.
  The adapter is trusted local code at the same privilege as the worker
  processes: it may be buggy, nondeterministic and stateful, but it is
  not adversarial infrastructure. Stronger isolation (sandboxing,
  remote attestation, untrusted weights) is explicitly out of scope until
  implemented and tested; until then, external checkpoints run only from
  the pinned manifest on operator-controlled machines.
