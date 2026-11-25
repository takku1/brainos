# BrainOS run results — 2026-11-25

Base commit `08cdd17` (first executable Core). Two runs on the same host:
**baseline**, the committed code as reviewed, and **corrected**, the working tree
after the corrective pass, the typed fabric and the first composition experiment.
Host: Windows 11 (10.0.26200), CPython 3.12.10, SQLite 3.49.1. No third-party
runtime dependencies.

Reproduce: `py tools/run_acceptance.py docs/results/2026-11-25T043902Z`
(writes `corrected/`). Baseline artifacts are `baseline*.json|log` in this folder.

## 1. Baseline (committed 08cdd17)

| Check | Result |
|---|---|
| Demo (`py -m brainos`) | exit 0, 1.0 s: total 60, lost ack reconciled to one application, restart revoked old permit, `sum_loop` replacement returned 60, 4 of 8 attempts spent |
| Runtime tests | 36/36 pass, 12.8 s |

All six review findings **reproduced** on the baseline (`baseline-findings.json`):

| ID | Observed on baseline |
|---|---|
| B01 | A task with `{"attempts": 0}` ran and returned 3; budget spent 0 |
| B02 | Revocation after durable `DISPATCHED` did not stop application; no linearization contract existed |
| B03 | Two candidates validated with 0 attempts charged to any ledger budget |
| B04 | One simulated catalogue edit changed the identity of all 4 providers |
| B05 | A different receipt database with the same display name was accepted as the target |
| B06 | Unrelated Certified evidence admitted a consequential effect |

## 2. Corrected profile

| Suite | Result |
|---|---|
| Demo | exit 0, 1.1 s; same outcomes as baseline; receipt now carries the stable `endpoint:<uid>` |
| Runtime tests (core + crash + corrective) | **71/71** pass (36 existing + 35 new), 50 s |
| Reference regressions | 23/23 |
| Document structural checks | 19/19 |
| Document negative checks | 15/15 |
| L1 harness | 17/17 decisive; 2 indeterminate (recorded, not counted) |
| Dependency closure | 8/8 |

Fixes (contracts in Doc 21 §21.10):

| ID | Now enforced | Regression |
|---|---|---|
| B01 | Grant derived from trusted spec cost; below-requirement grants refused; attempt spent at invocation start | `B01MinimumGrant` (4) |
| B02 | Durable dispatch-admission commit is the linearization point. Revoke, challenge or publish before it: refused, nothing applied. After it: effect confirmed, not recalled. Admission recorded separately from confirmation | `B02DispatchLinearization` (3) |
| B03 | Validation reserves and spends from a durable ledger budget, refunds unspent work, survives restart | `B03ValidationAccounting` (4) |
| B04 | Per-primitive code digest + version + declared dependency digests; unrelated edits leave other IDs unchanged | `B04ArtifactIdentity` (3) |
| B05 | Persisted endpoint identity; same-name impostor refused at dispatch and reconcile | `B05EndpointIdentity` (3) |
| B06 | Evidence support must equal {task, target, operation, context, claim}; checked at issue and dispatch | `B06EvidenceScope` (2) |

None of the six findings were left unreproduced. Behavior changes for callers:
effects target `sink.identity`, not `sink.name`. Consequential evidence needs
`support=effects.required_support(...)`. Storage schema version is now 2, and
version-1 stores are refused.

## 3. First developmental composition

Demand: *text → integer, "1,2,3" → 6, "10, -4" → 6*. The active catalogue has
six primitives: `parse_csv`, `sum`, `sum_loop`, `count`, `text_length` and
`negate`. No single primitive satisfies the demand; the only text→integer
primitive is `text_length`, and it fails the examples. The operator supplied no
workflow.

| Measure | Typed search | Memoized typed search |
|---|---|---|
| Outcome | ACQUIRED `parse_csv → sum` | ACQUIRED `parse_csv → sum` |
| Search attempts (expansions + example runs) | 12 | 11 |
| Validation attempts (4 admission cases × 2 nodes) | 8 | 8 |
| Trials retained | 2 rejected, 1 nominated, 1 acquired | same |
| Parent bindings unchanged | yes | yes |
| Wall time | 1.78 s | 1.68 s |

Rejected trials were `text_length` (wrong value) and `parse_csv → count`
(wrong value). The composite was published as a new role `csv-sum`. It runs
through the normal permit/task path and records both intermediate results
with provenance.

**Competition.** A second demand with the first path excluded acquired
`parse_csv → sum_loop` as `csv-sum-alt`. Median of 5 runs:

| Input size | parse+sum | parse+sum_loop |
|---|---|---|
| 1 | 233 ms | 240 ms |
| 100 | 237 ms | 241 ms |
| 2000 | 241 ms | 247 ms |

Both are correct at every size. Each node is a fresh provider subprocess,
which costs about 115 ms per node, so start-up dominates. The 3–6 ms gap is
not a meaningful difference at this sample size. **Neither composition is
shown to be more useful.** Telling them apart needs a cheaper invocation path
or workloads where the providers really differ.

## 4. What this does and does not show

- Shows: under a bounded, trusted catalogue, BrainOS found, validated and
  published a composite ability from a demand. It used independent admission
  cases, ledger-accounted search and validation, and retained failure records.
  Parents were left unchanged.
- Memoization saved 1 of 12 search attempts on this tiny catalogue. That is a
  baseline comparison, not evidence for any learned method.
- Does not show: primitive invention, abstraction learning, open-ended
  search or scientific superiority. The search space here is 6 primitives
  at depth ≤ 2.
- Limits still open: nested graphs and non-identity adapters, scheduling and
  backpressure, hostile-code sandboxing, and physical CPU/RAM limits. The kernel
  validation budget is a fixed 128 attempts per store and is never replenished.
  Cancellation applies only at pure node boundaries.
