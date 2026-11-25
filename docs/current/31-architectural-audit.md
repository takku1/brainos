# 31 - Requirement Register and Open Obligations

Maintains stable requirement IDs and current gap dispositions. Historical
review assertions are not fresh independent verification. Doc 08 owns the
implementation plan; this register owns evidence and unresolved obligations.

## 31.0 Scope and method

The original register covers Docs 01-30; the extension below covers revised
Core protocols and recent research mechanisms. Existing rows retain IDs for
traceability. Consolidation revises meanings where explicitly stated; it does
not independently reverify every historical status cell. C/S/I/V/E distinguish
definition, semantics, implementation, verification, and empirical evidence.
Full coverage and semantic equivalence need independent review. No tool here
extracts or proves every normative requirement automatically.

## 31.1 Status dimensions (used throughout; — means not applicable, e.g. definitional or scoping rows with no executable content — and is itself an explicit claim, not a gap)

C conceptual definition present. S transition semantics complete
(domain, pre/post, failure, affected state). I implemented in this
repository. V verification obligation discharged. E empirically
tested. A requirement reads C/S/I/V/E with ✓/✗/∼ (partial).

## 31.2 Requirement register (normative core)

Format: ID | source | requirement (short) | obligation | C/S/I/V/E.

R-02-01 | 02 §2.1 | minimal provider contract; all else optional | L1-C1 conformance | C✓ S∼ I✗ V✗ E✗ (optional interfaces lack per-capability tests)
R-02-02 | 02 §2.1 | formal tuple + execution (y,x′)~F | L1-C1 | C✓ S∼ I✗ V✗ E✗ (stochastic/nondet kinds named in 24, not in 02)
R-02-03 | 02 §2.2 | output-based adapters; no hidden-state reads | L1-C1/C4 | C✓ S✓ I✗ V✗ E✗
R-02-04 | 02 §2.3 | lossy readout integration over published outputs | L1-C1 | C✓ S∼ I✗ V✗ E✗ (fusion-choice semantics per implementation)
R-02-05 | 02 §2.4 | edges only where contracts mutually satisfiable | L1-C1 | C✓ S✓ I✗ V✗ E✗
R-02-06 | 02 §2.5 | control/signal path separation | L1 (no tensor path via supervisor) | C✓ S✓ I✗ V✗ E✗ (partial reference probe; runtime boundary tests open — gap G-01)
R-02-07 | 02 §2.6 | specialization/observability/autonomy/provenance invariants | L1-C4 + L3 | C✓ S∼ I✗ V✗ E✗ (specialization check = L3 gate, unrun)
R-02-08 | 02 §2.7 | one logical authority, N readouts, per-task epistemic bars | L1-C2/C5 | C✓ S∼ I✗ V✗ E✗ (single-owner profile specified; failover deferred — gap G-02)
R-02-09 | 02 §2.8 | slots/checkpoints/adapters versioning; swaps never move certification | L1-C4 | C✓ S✓ I✗ V✗ E✗
R-02-10 | 02 §2.9 | atomic sequenced snapshots; no cross-version assembly; scheduler≠supervisor | L1-C4 | C✓ S✓ I✗ V✗ E✗
R-02-11 | 02 §2.9 | enable/revoke/preempt distinct; safe stops in contract | L1-C2/C5 | C✓ S∼ I✗ V✗ E✗ (safe-stop completeness per provider — gap G-03)
R-02-12 | 02 §2.10 | convergence sufficient conditions (norm/domain/uniform bound); switching mitigations | L3 + Phase 4 proof | C✓ S∼ I✗ V✗ E∼ (toy pins one regime — historical evidence, not proof)

R-03-01 | 03 §3.6 | eligibility from versioned facts/contracts/freshness/authority; Horn = implementation | L1-C1 | C✓ S∼ I✗ V✗ E✗ (alternative mechanisms untested)
R-03-02 | 03 §§3.2–3.5 | enabled≠authorized≠executed; incremental closure | L1-C2 | C✓ S✓ I✗ V✗ E✗
R-03-03 | 03 §3.3 | closure is capability abstraction, not physical reachability | scope note | C✓ S— I— V— E— (definitional, no executable content)
R-03-04 | 03 §3.4 | schema/ownership/timestamp/adapter preconditions | L1-C1 | C✓ S✓ I✗ V✗ E✗
R-03-05 | 03 §3.6–3.7 | tiers × validity; Certified+Active for irreversible acts within bounds | L1-C5 | C✓ S∼ I✗ V✗ E✗ (probation/dwell unjustified defaults — stated gap)
R-03-06 | 03 | federated supervisor, single-valued eligibility | — | C∼ S✗ I✗ V✗ E✗ (asserted in 02 §2.7; single-owner first profile; failover deferred — gap G-02)

R-09-01 | 09 §9.9 | LEARN full machine-readable schema (9 properties) | L1-C1 identical accept/reject | C✓ S✓ I✗ V✗ E✗ (schema exists; no implementation to check)
R-09-OBSERVE | 09 §9.10 | append-only evidence; rejects unknown sources | L1-C1 | C✓ S✓ I✗ V✗ E✗
R-09-ENCODE | 09 §9.10 | bound-model representations retaining (ref, version) | L1-C1 | C✓ S✓ I✗ V✗ E✗
R-09-INFER | 09 §9.10 | pinned-version read-only inference; refuses mixing | L1-C1 | C✓ S✓ I✗ V✗ E✗
R-09-PREDICT | 09 §9.10 | estimate + uncertainty + horizon; no uncertainty-free claims | L1-C1 | C✓ S✓ I✗ V✗ E✗
R-09-REVISE | 09 §9.10 | new-version-only revision with derivation edge | L1-C2 | C✓ S✓ I✗ V✗ E✗
R-09-COMPARE | 09 §9.10 | disagreement + differing inputs; incomparability reported | L1-C1 | C✓ S✓ I✗ V✗ E✗
R-09-PROPAGATE | 09 §9.10 | declared-dependency corrections only; partial-with-report | L1-C2 | C✓ S✓ I✗ V✗ E✗
R-09-VALIDATE | 09 §9.10 | quarantined candidates; fail-closed; never publishes | L1-C2 | C✓ S✓ I✗ V✗ E✗
R-09-BENCHMARK | 09 §9.10 | measurements vs declared workload; production read-only | L3 | C✓ S✓ I✗ V✗ E✗
R-09-FORK | 09 §9.10 | history-intact context versions; parent untouched | L1-C2 | C✓ S✓ I✗ V✗ E✗
R-09-CONSOLIDATE | 09 §9.10 | durable version + ancestry or labeled approximate repair | L1-C2 | C✓ S✓ I✗ V✗ E✗
R-09-ASSERT | 09 §9.10 | claim + evidence → id; no self-certification | L1-C2 | C✓ S✓ I✗ V✗ E✗
R-09-CHALLENGE | 09 §9.10 | suspends dependents at next epoch cut; serialized | L1-C2 | C✓ S✓ I✗ V✗ E✗
R-09-VERIFY | 09 §9.10 | procedure record; verdict-only, no status change | L1-C2 | C✓ S✓ I✗ V✗ E✗
R-09-RETRACT | 09 §9.10 | kernel-decided withdrawal; history preserved | L1-C2 | C✓ S✓ I✗ V✗ E✗
R-09-QUARANTINE | 09 §9.10 | exclusion scoped; independent work continues | L1-C2 | C✓ S✓ I✗ V✗ E✗
R-09-RESTORE | 09 §9.10 | same-target eligibility restored on scoped proof; no permit | L1-C2 | C✓ S✓ I✗ V✗ E✗
R-09-BIND | 09 §9.10 | eligibility-checked role binding | L1-C2 | C✓ S✓ I✗ V✗ E✗
R-09-SPAWN | 09 §9.10 | fresh-manifest instances; budget-gated; no shared mutable by default | L1-C2/C3 | C✓ S✓ I✗ V✗ E✗
R-09-CONNECT | 09 §9.10 | compatible declared edges only | L1-C2 | C✓ S✓ I✗ V✗ E✗
R-09-SNAPSHOT | 09 §9.10 | atomic immutable S_k + seq; torn-read retry | L1-C4 | C✓ S✓ I✗ V✗ E✗
R-09-COMMIT | 09 §9.10 | epoch-gated CAS publish; rejects stale/unvalidated/mixed | L1-C2/C4 | C✓ S✓ I✗ V✗ E✗
R-09-AUTHORIZE | 09 §9.10 | permit/deny under manifest + tier; deny-closed | L1-C5 | C✓ S✓ I✗ V✗ E✗
R-09-REVOKE | 09 §9.10 | immediate for new, safe-stop for in-flight; latency-bounded; no retroactive invalidation | L1-C2/C5 | C✓ S✓ I✗ V✗ E✗
R-09-ACT | 09 §9.10 | executes only epoch-valid permitted ops | L1-C5 | C✓ S✓ I✗ V✗ E✗
R-09-BIRTH | 09 §9.10 | compound: nomination + budget → quarantined candidate; non-construction explicit | L1 + L3 | C✓ S✓ I✗ V✗ E✗
R-09-DIFFERENTIATE | 09 §9.10 | context version without parent modification or scope overclaim | L1 + L3 | C✓ S✓ I✗ V✗ E✗
R-09-FUSE | 09 §9.10 | composite candidate, parents retained until gated retirement | L1 + L3 | C✓ S✓ I✗ V✗ E✗
R-09-RETIRE | 09 §9.10 | removal on floors + fallback with lineage; remain-with-flag on failure | L1 + L3 | C✓ S✓ I✗ V✗ E✗
R-09-RESERVE | 09 §9.10 | atomic budget debit; over-reservation rejected | L1-C3 | C✓ S✓ I✗ V✗ E✗
R-09-ALLOCATE | 09 §9.10 | committed spend against held reservation; no double-spend | L1-C3 | C✓ S✓ I✗ V✗ E✗
R-09-RELEASE | 09 §9.10 | idempotent return | L1-C3 | C✓ S✓ I✗ V✗ E✗
R-09-REBIND | 09 §9.10 | eligibility-checked rebinding with closure revalidation | L1-C2 | C✓ S✓ I✗ V✗ E✗
R-09-CANCEL | 09 §9.10 | safe-stop termination; critical sections complete with report | L1-C2 | C✓ S✓ I✗ V✗ E✗
R-09-EMIT | 09 §9.10 | sequenced channel append; bounded-drop reported | L1-C1 | C✓ S✓ I✗ V✗ E✗
R-09-RECEIVE | 09 §9.10 | cursor-advancing read; only contracted delivery guarantees | L1-C1 | C✓ S✓ I✗ V✗ E✗
R-09-03 | 09 | LEARN≠COMMIT≠AUTHORIZE≠ACT separation | L1-C2 violation tests | C✓ S✓ I✗ V✗ E✗
R-09-04 | 09 §§9.3/9.7 | manifests, epoch windows, challenge-at-cut, in-flight drain | L1-C2/C4 | C✓ S✓ I✗ V✗ E✗
R-09-05 | 09 §9.3 | claim/unit lifecycles | L1-C2 | C✓ S∼ I✗ V✗ E✗ (transitions reconciled in 32; executable lifecycle tests open — gap G-04, shared with 05)
R-09-06 | 09 §9.4 | promotion requirements incl. canonical economics pointer | L3 | C✓ S✓ I✗ V✗ E✗
R-09-07 | 09 | per-instruction conformance; unimplemented rejected | L1-C1 (Doc 21 C1) | C✓ S∼ I✗ V✗ E✗ (partial fixture harness; runtime suite incomplete)
R-09-08 | 09 §9.8 | AUTHORIZE/REVOKE: latency bounds + side-effect reauthorization | L1-C5 + deployment L2 | C✓ S✓ I✗ V✗ E✗
R-09-09 | 09 §9.8 | developmental ops as conditional compound transactions | L1 + L3 | C✓ S∼ I✗ V✗ E✗ (construction branches per Doc 27 untested)
R-09-10 | 09 §9.8 | RESERVE/ALLOCATE/RELEASE caps; failed candidates counted | L1-C3 | C✓ S✓ I✗ V✗ E✗

R-21-01 | 21 §21.1 | interface/type/Manifest/Snapshot/Evidence schemas | L1-C1 | C✓ S∼ I✗ V✗ E✗ (sketches, not machine-enforceable — stated; Phase 1B)
R-21-02 | 21 §21.2 | Transactor CAS publish; challenge serialization; transport; versioning | L1-C2/C4 | C✓ S∼ I✗ V✗ E✗ (sketches, same as R-21-01)
R-21-03 | 21 §21.3 | executable L1-C1..C5 tests | Gate 3 entry | C✓ S∼ I✗ V✗ E✗ (partial runnable fixtures; runtime coverage open — Phase 1B C4)
R-21-04 | 21 §21.4 | dependency rule (core free of framework deps; build-enforced) | CI lint | C✓ S— I✗ V✗ E✗ (no build exists to lint; S not applicable — no transition semantics claimed)

R-24-01 | 24 §24.3 | authoritative Σ; T:Σ⇀Σ′; declared transition kinds | Phase 4 | C✓ S∼ I✗ V✗ E✗ (kinds named; per-op kind assignments partial — gap G-05)
R-24-ADD | 24 §24.4 | ADD-PROVIDER: quarantined birth; resource/evaluator admission before publication; removal pre-commit | L1 + L3 | C✓ S∼ I✗ V✗ E✗
R-24-REMOVE | 24 §24.4 | REMOVE-PROVIDER: artifact≠state restoration; separate op for state | L1 + L3 | C✓ S∼ I✗ V✗ E✗
R-24-EDGE | 24 §24.4 | ADD/REMOVE-EDGE: closure-bounded revalidation beyond downstream graph | L1-C2 | C✓ S∼ I✗ V✗ E✗
R-24-REBIND | 24 §24.4 | REBIND: closure-checked; dependents revalidate | L1-C2 | C✓ S∼ I✗ V✗ E✗
R-24-COMPOSE | 24 §24.4 | COMPOSE: nominated-contract admission; parent replacement gates only on replacement; retention and impact checks | L1 + L3 | C✓ S∼ I✗ V✗ E✗
R-24-SPLIT | 24 §24.4 | SPLIT: no automatic competence preservation; partition boundaries validated | L1 + L3 | C✓ S∼ I✗ V✗ E✗
R-24-ASSIMILATE | 24 §24.4 | ASSIMILATE: 4 distinct recovery forms; rebuild-not-undo | L1 + L3 | C✓ S∼ I✗ V✗ E✗
R-24-RETIRE | 24 §24.4 | RETIRE/RESTORE: floors + fallback; reconstruction with revalidation, never time reversal | L1 + L3 | C✓ S∼ I✗ V✗ E✗
R-24-03 | 24 §24.2/24.5 | conditional frame rule; prepare/validate/commit/publish; conflict rejection | L1-C2/C4 | C✓ S∼ I✗ V✗ E✗
R-24-04 | 24 §24.5 | proof obligations labeled; no unproven guarantees | Gate 2/5 | C✓ S— I✗ V✗ E✗ (no proofs attempted — Phase 4)

R-29-01 | 29 §29.2/29.4 | fixed-point closure; directional vs symmetric; conservatism; cascading | L1-C2/C4 | C✓ S∼ I✗ V✗ E✗ (reference closure and termination specified; typed impact enforcement — Phase 1B C3)
R-29-02 | 29 §29.3 | isolation levels; scoped exclusion; quarantine semantics | L1-C2 | C✓ S✓ I✗ V✗ E✗

R-01-01 | 01 §1.2 | H1–H4 independently testable; no experiment proves all four | L3 per-hypothesis | C✓ S— I✗ V✗ E✗
R-01-02 | 01 §1.6 | gated reorganization in scope; autonomous discovery out | scope gate | C✓ S— I✗ V✗ E✗
R-01-03 | 01 §1.7 | per-hypothesis success criteria; Track R evidence, not bar | L3 | C✓ S— I✗ V✗ E✗
R-01-04 | 01 §1.8 | novelty unclaimed; direction only; central design principle | honesty gate | C✓ S— I✗ V✗ E✗
R-04-01 | 04 §4.1 | readout optional surface, never mandatory bus | L1-C1 | C✓ S✓ I✗ V✗ E✗
R-04-02 | 04 §4.2 | implementation-appropriate derivation provenance; derived≠independent | L1-C1 | C✓ S∼ I✗ V✗ E✗
R-04-03 | 04 §4.3 | multi-query arbitration with schema/freshness/epistemic minimums | L1-C1 | C✓ S∼ I✗ V✗ E✗
R-05-01 | 05 §§15.2/9.8 | training-time dependency recording; later explanations no substitute | L1 | C✓ S✓ I✗ V✗ E✗
R-05-02 | 05 §5.3/5.6 | stable core + bounded plastic units per substrate; repair broader than relearning | L1-C2 | C✓ S∼ I✗ V✗ E∼ (R2b historical only)
R-05-03 | 05 §5.4 | repair transaction: challenge→quarantine→rebuild→validate→commit; losers revalidate | L1-C2 | C✓ S∼ I✗ V✗ E✗ (entry/exit criteria partial — gap G-04)
R-05-04 | 05 §5.5 | separate competence/alignment/prediction/task/retention terms | L3 | C✓ S∼ I✗ V✗ E✗
R-06-01 | 06 §6.1/6.5 | periodic/event/on-demand/distributed all supported; fast loops never wait | L1 + L2 | C✓ S∼ I✗ V✗ E✗
R-06-02 | 06 §6.2 | atomic immutable snapshots; no cross-version assembly | L1-C4 | C✓ S✓ I✗ V✗ E✗
R-06-03 | 06 §6.3 | consume rule Δτ≤τ_max else fallback; age-aware laws; degraded modes specified | L1-C4 + L2 | C✓ S✓ I✗ V✗ E✗
R-06-04 | 06 §6.4 | liveness without safety override; anti-oscillation | L1 + L2 | C✓ S∼ I✗ V✗ E✗
R-06-05 | 06 §6.5 | per-stream sequences; clock-uncertainty margins; idempotent handlers; manifest-serialized commits | L1-C4 | C✓ S∼ I✗ V✗ E✗ (replay exactness missing — gap G-06)
R-07-01 | 07 L1 | conformance mandatory, threshold-free; two implementations one contract | Gate 3 entry | C✓ S✓ I✗ V✗ E✗
R-07-02 | 07 L2 | deployment-set thresholds, never universal | deployment | C✓ S— I✗ V✗ E✗
R-07-03 | 07 L3 | matched arms; routing free when under test; thresholds confined to L3; ≥5 seeds provisional | L3 | C✓ S∼ I✗ V✗ E✗
R-07-04 | 07 §7.8/registry | L1 harness vs L3 verdict distinct; sim-only scoped to physical transfer | method | C✓ S— I✗ V✗ E✗
R-08-01 | 08 | layers adoptable separately; dependency rule (core free of framework deps) | build gate | C✓ S— I✗ V✗ E✗
R-08-02 | 08 | Experiment 001 + Arm 0 specified; comparison baselines named | Phase 5 | C✓ S— I✗ V✗ E✗ (unrun)
R-11-01 | 11 §11.1/11.6 | developmental providers; plasticity as capability; Transactor-gated ops | L1 + L3 | C✓ S✓ I✗ V✗ E✗
R-11-02 | 11 §11.3 | niche-relative selection; directional s; Pareto vector; protected floors | L3 | C✓ S∼ I✗ V✗ E✗
R-11-03 | 11 §11.4 | assimilation = functional result; 7 methods; union-gate + rollback | L3 | C✓ S∼ I✗ V✗ E✗
R-11-04 | 11 §11.5 | grouped execution; budgets; hysteresis/cooldowns/floors; drain-before-reclaim | L1-C3 + L3 | C✓ S∼ I✗ V✗ E✗
R-11-05 | 11 §§11.7–11.8 | 3 layers; Σ-state calculus; graph transforms as topological subset | L1 + L3 | C✓ S∼ I✗ V✗ E✗
R-12-F1 | 12 | unsafe actuation only Certified+Active within revoke bounds | L1-C5 + L2 | C✓ S∼ I✗ V✗ E✗
R-12-F2 | 12 | epoch-scoped permits; reauthorization at side-effect boundaries | L1-C2/C5 | C✓ S✓ I✗ V✗ E✗
R-12-F3 | 12 | fusion requires support refs; derived≠independent | L1-C1 | C✓ S∼ I✗ V✗ E✗
R-12-F4 | 12 | competence/diversity measured; agreement≠evidence | L1 + L3 | C✓ S∼ I✗ V✗ E✗
R-12-F5 | 12 | explicit caps, protected floors, hysteresis against runaway growth | L1-C3 | C✓ S∼ I✗ V✗ E✗
R-12-F6 | 12 | retention measured separately; approximate repair labeled | L3 | C✓ S∼ I✗ V✗ E✗
R-12-F7 | 12 | joint failure rates measured; no fabricated availability | L3 | C✓ S∼ I✗ V✗ E✗
R-12-F8 | 12 | liveness arbitration without safety override; specified fallback | L1 + L2 | C✓ S∼ I✗ V✗ E✗
R-12-F9 | 12 | per-stream sequences; manifest-serialized commits; minority degrades | L1-C4 | C✓ S∼ I✗ V✗ E✗
R-12-F10 | 12 | developmental pathologies with lineage-based remedy | L3 | C✓ S∼ I✗ V✗ E✗
R-12-F11 | 12 | conformance re-run per release; contract changes version the contract | L1 | C✓ S✓ I✗ V✗ E✗
R-12-F12 | 12 | evaluator capture → integrity checks + evaluator quarantine | L1-C1 | C✓ S∼ I✗ V✗ E✗
R-12-F13 | 12 | ontological drift → versioned ontology, re-baseline on change | L1-C1 | C✓ S∼ I✗ V✗ E✗
R-12-F14 | 12 | synthesis escape → isolation levels + kernel-only validation | L1-C2 | C✓ S∼ I✗ V✗ E✗
R-12-F15 | 12 | credit corruption → uncertainty-aware thresholds + regeneration | L3 | C✓ S∼ I✗ V✗ E✗
R-12-F16 | 12 | grounding corruption → validity intervals + invalidation propagation | L1 + L3 | C✓ S∼ I✗ V✗ E✗
R-12-F17 | 12 | dependency concealment = contract violation + footprint audits | L1-C2 | C✓ S∼ I✗ V✗ E✗
R-12-F18 | 12 | meta-adaptive instability → bounded meta-adaptation, grounded strategy evaluation | L3 | C✓ S∼ I✗ V✗ E✗
R-12-F19 | 12 | resource-accounting evasion → single-ledger booking + audits | L1-C3 | C✓ S∼ I✗ V✗ E✗
R-12-F20 | 12 | organizational deadlock → stalled-demand detection + explicit relaxation policy | L2 | C✓ S∼ I✗ V✗ E✗
R-13-01 | 13 | rename table governs term collisions; reserved terms (Snapshot, Authority, etc.) | editorial | C✓ S— I✗ V✗ E✗
R-13-02 | 13 | L3-mapping note (G1–G7 historical); subsystem-vs-layer terminology | editorial | C✓ S— I✗ V✗ E✗
R-14-01 | 14 | game mappings as analogies constrained by contract, never equivalences | — | C✓ S— I✗ V✗ E✗ (interpretive mapping, gated by L3)
R-15-01 | 15 | sim-only scoped to physical transfer; evaluation-type evidence table | — | C✓ S— I✗ V✗ E✗ (interpretive, gated by L3)
R-15-02 | 15 | research-track policies (prereg/PROV-O/seeds/replication) ≠ runtime requirements | — | C✓ S— I✗ V✗ E✗ (scoping rule, no executable content)
R-16-01 | 16 | any-technique-permitted, unvalidated-acquisition-prohibited; scope statements not theorems | — | C✓ S— I✗ V✗ E✗ (interpretive, gated by L3)
R-17-01 | 17 §17.1 | capability≠contract≠provider; measurables against stated contract | L1-C1 | C✓ S— I✗ V✗ E✗
R-17-02 | 17 §17.2 | s_requirements vs p_success; uncertainty-aware floors; variance reported | L3 | C✓ S∼ I✗ V✗ E✗
R-17-03 | 17 §17.2 | weights Σ=1 from contract priorities; proof/exhaustive/sampling trichotomy; provisional seeds | L3 | C✓ S∼ I✗ V✗ E✗
R-17-04 | 17 §17.2/17.4 | correct Pareto rule; redundancy≠independence; niche decides | L3 | C✓ S— I✗ V✗ E✗
R-17-05 | 17 §§17.5–17.6 | state handover; effect-equivalence; no pure-function sub for effectful; exact-vs-estimated, transitivity rules | L1-C1 + L3 | C✓ S∼ I✗ V✗ E✗
R-17-06 | 17 §17.3/§17.4 | degeneracy test (structure+overlap); 4-record registry | L1-C1 + L3 | C✓ S∼ I✗ V✗ E✗
R-18-01 | 18 | demand-gated growth; nomination→construction→evaluation→acquisition | L3 | C✓ S∼ I✗ V✗ E✗
R-18-02 | 18 | construction order (reuse→…→instantiate, new capacity last); stopping rules; demand signals | L3 | C✓ S∼ I✗ V✗ E✗
R-19-01 | 19 | 4 adaptation targets; org learning without component learning | L3 | C✓ S∼ I✗ V✗ E✗
R-19-02 | 19 §19.2 | operator = graph transformation + preserved contracts + rollback; composites are providers | L1 + L3 | C✓ S∼ I✗ V✗ E✗
R-20-01 | 20 §20.1/20.5 | S(N) special case with stated assumptions; general S(T); no-double-counting ledgers | L3 | C✓ S✓ I✗ V✗ E✗
R-20-02 | 20 §20.2/20.4 | marginal utility vs frontier; B_explore; 3 values; subsidy rule; cost-of-asking | L3 | C✓ S∼ I✗ V✗ E✗
R-20-03 | 20 §20.3 | retention ledger; policy floors; forgetting reported | L3 | C✓ S✓ I✗ V✗ E✗
R-22-01 | 22 | Discovery Engine as competing provider family; coordination-check-first | L3 | C✓ S∼ I✗ V✗ E✗
R-22-02 | 22 | decision procedure (residual→decompose→ablate→contract→probe); stopping rules; B_explore cap | L3 | C✓ S∼ I✗ V✗ E✗
R-23-01 | 23 | 7 evaluator families with named appropriate evidence | L1-C1 + L3 | C✓ S✓ I✗ V✗ E✗
R-23-02 | 23 | integrity: provenance/calibration/independence; evaluator quarantine; no self-set criteria | L1-C1 | C✓ S∼ I✗ V✗ E✗
R-23-03 | 23 §§23.3–23.4 | adjudication terminates or escalates; trust termination per Doc 30 | L1 + L3 | C✓ S∼ I✗ V✗ E✗
R-25-01 | 25 | equilibrium≠stability; thrash/erode/ossify distinguished | L3 | C✓ S∼ I✗ V✗ E✗
R-25-02 | 25 §25.5 | measured state vector; control inputs; static-valid stability; open questions registered | L3 | C✓ S∼ I✗ V✗ E✗ (control law untested by design)
R-26-01 | 26 | exact equivalence vs non-transitive estimated substitution; resilience separate; ontology consistency rules | L1-C1 | C✓ S∼ I✗ V✗ E✗ (registry enforcement untested)
R-27-01 | 27 | 5 reference boundaries; level mislabeling prohibited | L3 | C✓ S— I✗ V✗ E✗
R-27-02 | 27 §§27.2–27.3 | conditional trial; artifact types; isolation/cancellation/reproducibility; kernel-only entry | L1 + L3 | C✓ S∼ I✗ V✗ E✗
R-28-01 | 28 §§28.1–28.2 | vector Δ; 3 categories; admissibility; replay-validity conditions; fresh execution where invalid | L3 | C✓ S∼ I✗ V✗ E✗
R-28-02 | 28 §28.3 | attribution-before-selection; no auto-retention; uncertainty-aware thresholds | L3 | C✓ S∼ I✗ V✗ E✗
R-30-01 | 30 §30.1 | 4 grounding types; policy≠truth; termination recorded or inadmissible | L1 + L3 | C✓ S✓ I✗ V✗ E✗
R-30-02 | 30 §30.2 | diagnostic depth (no auto-penalty); calibration/dependence accounting; circularity defect; expiry/invalidation; unresolved-vs-failed | L1 + L3 | C✓ S∼ I✗ V✗ E✗
R-10-01 | 10 | optional neural provider family; R0/R1/R2b results labeled historical predecessor evidence | — | C✓ S— I✗ V✗ E✗ (scoped; no new claims)

## 31.2a Consolidation requirement extension

R-02-13 | 02 §2.11 | semantic adapter checks and uncertainty mapping | adapter boundary tests | C✓ S∼ I✗ V✗ E✗ (specified; runtime/experiment evidence open)
R-20-04 | 20 §20.2 | separate discovery probe and construction grants | bounded funding tests | C✓ S∼ I✗ V✗ E✗ (specified; runtime/experiment evidence open)
R-21-05 | 21 §21.5 | owned reservation conversion and idempotent unspent release | durable concurrent ledger tests | C✓ S∼ I✗ V✗ E✗ (specified; runtime/experiment evidence open)
R-21-06 | 21 §21.6 | bounded history retention and deletion dispositions | GC and unavailable-replay tests | C✓ S∼ I✗ V✗ E✗ (specified; runtime/experiment evidence open)
R-23-04 | 23 §23.5 | adaptive evaluation access and repeated-comparison policy | holdout/access tests | C✓ S∼ I✗ V✗ E✗ (specified; runtime/experiment evidence open)
R-23-05 | 23 §23.6 | family-specific uncertainty and floor decisions | calibration/statistical checks | C✓ S∼ I✗ V✗ E✗ (specified; runtime/experiment evidence open)
R-27-03 | 27 §27.6 | bounded typed-composition recipe and baselines | executable construction experiment | C✓ S∼ I✗ V✗ E✗ (specified; runtime/experiment evidence open)
R-29-03 | 29 §29.2 | typed impact actions distinguish authority from interference | impact enforcement tests | C✓ S∼ I✗ V✗ E✗ (specified; runtime/experiment evidence open)
R-32-01 | 32 §32.1 | mechanism/stage transition declarations and envelope | runtime kind/envelope tests | C✓ S∼ I✗ V✗ E✗ (specified; runtime/experiment evidence open)
R-32-02 | 32 §32.3 | single-owner profile; failover requires fencing | restart/ownership tests | C✓ S∼ I✗ V✗ E✗ (specified; runtime/experiment evidence open)
R-32-03 | 32 §32.4 | scoped permits; revoke starts; drain existing invocation only | gateway/stop tests | C✓ S∼ I✗ V✗ E✗ (specified; runtime/experiment evidence open)
R-32-04 | 32 §32.5 | verdict-only verification; repeatable restoration; no permit | lifecycle tests | C✓ S∼ I✗ V✗ E✗ (specified; runtime/experiment evidence open)
R-32-05 | 32 §32.6 | purpose-specific replay and external trace limits | replay-profile tests | C✓ S∼ I✗ V✗ E✗ (specified; runtime/experiment evidence open)
R-32-06 | 32 §32.7 | trusted enforcement includes deadlines and effect gateway | bypass/isolation tests | C✓ S∼ I✗ V✗ E✗ (specified; runtime/experiment evidence open)
R-32-07 | 32 §32.9 | empty change and finite closure; cycles valid | reference regression plus runtime impact tests | C✓ S∼ I✗ V✗ E✗ (specified; runtime/experiment evidence open)
R-32-08 | 32 §32.11 | task ownership, orchestration, cancellation, bounded queues | executor/deadlock tests | C✓ S∼ I✗ V✗ E✗ (specified; runtime/experiment evidence open)
R-32-09 | 32 §32.12 | durable publication and uncertain-effect reconciliation | crash-injection tests | C✓ S∼ I✗ V✗ E✗ (specified; runtime/experiment evidence open)

Research additions in Docs 07/11/14/18/20/22/25/27/28 retain their
bounded experiments and source links. They are research policies, not implicit
Core requirements; normative extraction of each selected deployment policy
is part of independent review, not presumed complete in this register.

R-24-COMPOSE-02 | 24 §24.4 | complementary composition does not require parent-interface substitution; retirement has separate replacement gates | AR-01 admission/retirement cases | C✓ S∼ I✗ V✗ E✗ (specified; runtime tests open)
R-26-02 | 26 §26.4 | only exact equivalence canonicalizes; estimated overlap has no transitive closure | AR-02 overlap witness and registry tests | C✓ S∼ I✗ V✗ E✗ (specified; runtime tests open)

## 31.3 Operation inventory (completeness per operation, not per document)

Organizational-model integration requirements (conditional on selecting that
adaptation policy; Core adoption alone does not require a model):

R-19-01-M | 19 §19.4 | outcome forecasts use permitted projections/history, scoped uncertainty and unresolved result | projection/calibration tests | C✓ S∼ I✗ V✗ E✗ (specified; model unimplemented)
R-19-02-M | 19 §19.5 | observed case, applicability hypothesis and verified property are distinct | case/guard revision tests | C✓ S∼ I✗ V✗ E✗ (specified; record implementation open)
R-19-03-M | 19 §19.6 | bounded lookahead preserves every prefix constraint and replans after measured steps | plan/admission tests | C✓ S∼ I✗ V✗ E✗ (specified; planning unimplemented)
R-20-05 | 20 §20.7 | named enabling steps can be funded without terminal reward under actual bounded grants | spend/non-attainment tests | C✓ S∼ I✗ V✗ E✗ (specified; budget enforcement open)
R-21-07 | 21 §21.7 | pretrial predictions, assigned interventions, censored outcomes and costs recorded with versions | schema/history tests | C✓ S∼ I✗ V✗ E✗ (specified; records unimplemented)
R-22-03 | 22 §22.2 | discovery compares plans/probes/no-change with current guards, budgets and equal-horizon baselines | discovery tests | C✓ S∼ I✗ V✗ E✗ (specified; execution open)
R-23-06 | 23 §23.7 | forecast errors separate from admission outcomes and proposal success | calibration/abstention tests | C✓ S∼ I✗ V✗ E✗ (specified; evaluation unrun)
R-27-04 | 27 §27.7 | predictor does not expand the grammar or prove compatibility; cases/search have matched access | construction/baseline tests | C✓ S∼ I✗ V✗ E✗ (specified; experiment unrun)
R-28-03 | 28 §28.5 | causal interpretation requires assigned interventions and transport assumptions; predicted benefit is not earned credit | causal/transfer tests | C✓ S∼ I✗ V✗ E✗ (specified; identification evidence open)
R-29-04 | 29 §29.5 | stale prediction properties are suspended/narrowed by actual dependencies; model guesses cannot narrow runtime closure | invalidation tests | C✓ S∼ I✗ V✗ E✗ (specified; enforcement open)
R-32-10 | 32 §32.13 | model remains ordinary provider; predictions grant no validation, publication or authority | workflow/bypass tests | C✓ S∼ I✗ V✗ E✗ (specified; runtime absent)
R-07-05 | 07 §7.12 | Static/Selection/Search/Cases/Model comparison charges total cost and budget non-attainment | preregistered experiment | C✓ S∼ I✗ V✗ E✗ (specified; unrun)

CIA instructions: all 37 schematized in Doc 09 §§9.9–9.10 (LEARN template + 36 in §9.10), each carrying the 9-property template; per-instruction register rows R-09-* above. Developmental transformations: ADD-PROVIDER, REMOVE-PROVIDER, ADD/REMOVE-EDGE, REBIND, COMPOSE, SPLIT, ASSIMILATE, RETIRE/RESTORE — per-primitive contracts in Doc 24 §24.4 with register rows R-24-* above; machine-checked pre/post (proofs, model checks) remain Phase 3A/4 work, explicitly distinguished from these preliminary machine-readable contracts.

## 31.4 Current gap register

Consolidation replaces historical completion notes with current dispositions.
Docs 09/21/29/32 were reconciled; paper definitions do not establish runtime
enforcement. The full current set is Docs 01-32 plus README and STATUS.

| Gap | Defined owner / current disposition | Remaining evidence |
|---|---|---|
| G-01 control/signal boundary | 32 section 32.2; partial access-tracing fixture | Runtime isolation/bypass and missing-field tests |
| G-02 exclusive authority | 32 section 32.3; first profile single-owner | Durable ownership/restart tests; distributed failover deferred |
| G-03 stop/revocation | 32 section 32.4; scoped permit reference tests | Timed enforcement, noninterruptible admission, real effect gateway |
| G-04 lifecycle | 09 signatures + 32 section 32.5 reconciled | Runtime repeated challenges, verdict/adjudication separation, repair races |
| G-05 transition kinds | 32 section 32.1; mechanism/stage declarations | Executable declarations and developmental checks |
| G-06 replay | 32 section 32.6; exact/distributional/trace limits | Replay fixtures and environment/profile reproducibility |
| G-07 tasks/recovery | 21 records; 32 sections 32.11-32.12 | Executable task graph, durable transactions, crash/effect reconciliation |
| G-08 impact and scope | 29 classification; closure reference model | Property-specific impact enforcement and footprint audits |
| G-09 exploration funding | 20 section 20.2 distinguishes probe/construction | Resource grants, stopping-rule and no-surplus experiments |
| G-10 construction/adapters | 27 section 27.6; 02 section 2.11 | Implement recipe and semantic adapter checks |
| G-11 evaluation integrity | 23 sections 23.5-23.6 | Adaptive holdout access/refresh, uncertainty calibration and multiplicity controls |
| G-12 history and budgets | 21 sections 21.5-21.6 | Durable release/GC/deletion/recovery and access-control tests |
| G-13 organizational prediction/planning | 19 model/strategy; 21 section 21.7 records; 22 planner; 07 section 7.12 experiment | Implement symbolic search/cases before learned forecast; causal/guard transfer, calibration, total-cost and non-attainment evidence |

Reference permit/closure regressions cover observed bugs only. Gate 1 checks
declarations/references, not executable predicate semantics or complete
traceability. Newly revised requirements and research additions need
independent row-by-row review; the register is maintained, not certified complete.

## 31.5 Documentation review acceptance criteria

- G1-1: independent review finds no unresolved signature/protocol conflicts.
- G1-2: every selected-profile normative requirement maps to a stable ID,
  C/S/I/V/E disposition, and verification obligation; traceability reviewed
  against the current files, including consolidation additions.
- G1-3: every supported instruction/transformation has declared inputs,
  pre/postconditions, failure, concurrency, resource and evidence semantics.
  Structural schemas are not executable semantic enforcement.
- G1-4: known gaps and failed checks appear in this register with owner/action.
- G1-5: scientific novelty claims require prior-art review; hypotheses and
  untested mechanisms remain valid research proposals.

No gate is self-granted by the author or by passing structural checks.

## 31.6 Core semantic closure review

Review Doc 09 signatures, Doc 21 records, Doc 29 impacts and Doc 32 protocols
as one specification. Check epoch/lifecycle timing, owned resource release,
effect reconciliation, task cancellation, argument kinds, staged versus active
publication, and repeated challenge/restoration. Require discriminating valid
and invalid behavioral cases. Reference fixtures cover a subset; runtime
conformance and deployment qualification require the matrix in Doc 21.
The canonical build sequence is Doc 08; remaining evidence is section 31.4.

## 31.7 Plan ownership

Doc 08 owns the current implementation sequence and milestones. This register
owns unresolved obligations and evidence. Historical review rounds are not
current gates. No source runtime exists yet; reference tools are implemented
models with deliberately narrower claims. Gate/status decisions require
artifact review, not the number of documents or tests.

## 31.8 Inventory and verification scope

There are 32 numbered Markdown documents plus README in docs/current and
docs/STATUS.md. Tools contain structural validators, negative tests, a closure
model, and partial behavioral fixtures/regressions. No src/ runtime is present.
The architecture docx remains a frozen historical artifact; Markdown is the
canonical current specification. Machine checks do not certify every prose
requirement or demonstrate production conformance.

## 31.9 Consolidation disposition

Ambitious hypotheses remain in scope. This pass resolves known semantic
conflicts and provides concrete build/test decisions; it does not reduce
research ambition to match current results. Organizational outcome models now have a canonical owner in Doc 19 and a
matched experiment in Doc 07 section 7.12. The source proposal is navigation.
No new numbered documents or instruction names were added. Independent review, production implementation,
formal concurrency/security work, and empirical experiments remain open.


## 31.10 Integration acceptance cases

Organizational-model review checks: every admitted prefix preserves floors;
future predicted resources confer no spending authority; pretrial forecasts
remain immutable; rejected/unexecuted outcomes are not invented measurements;
new guard conditions need new tests; stale dependencies suspend affected
prediction properties; symbolic planning and case reuse have equal horizon
and history; no-change and budget non-attainment are reported. The parser
example is only a finite lookahead witness. Production/model evidence stays
open under G-13; existing reference tests do not discharge these obligations.
