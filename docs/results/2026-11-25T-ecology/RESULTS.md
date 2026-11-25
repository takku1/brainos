# BrainOS run results: cumulative development and bounded ecology

Base commit `08d29f3`. Host: Windows 11 (10.0.26200), CPython 3.12.10, SQLite
3.49.1, standard library only. Contracts are in Doc 21 §21.11. The
preregistrations are `PREREGISTRATION.md` (X1, X2, X3) and
`PREREGISTRATION-v2.md` (X2b follow-up).

Reproduce:
- `py docs/results/2026-11-25T-ecology/reproduce_b07_b13.py`, run against 08d29f3
- `py tools/bench_runners.py`
- `py tools/run_ecology.py docs/results/2026-11-25T-ecology` (v1)
- `py tools/run_ecology.py docs/results/2026-11-25T-ecology --v2`

## 1. Repository and assurance integrity

- The baseline was confirmed as `08d29f3`, matching `origin/main`. Earlier artifacts in `docs/results/2026-11-25T043902Z/` are untouched.
- The working copy of `BrainOS_CCCM_Architecture.docx` had been deleted outside any session. The file is still in history and was restored to the working tree. Nothing was discarded; its final disposition is the owner's decision.
- This run's assurance table was screened and declared **before** any code edit, resolving the previous run's ordering exception.
- Storage schema v2 rejection is preserved: new record kinds were added with no table change, so there was no schema bump.

## 2. Findings B07–B13

All seven were reproduced on 08d29f3 (`baseline-findings.json`).

| ID | Baseline observation | Class | Now | Regression |
|---|---|---|---|---|
| B07 | G2 (`-sum`) at depth 2 was NON_ATTAINMENT; nested graph refused | documented limit | Bounded lowering; active composites join the catalogue | `CumulativeConstruction` (4) |
| B08 | Composite `capability` = `"csv-sum"` (role name); a second provider replaced the first binding | defect | Capability contracts, validated memberships and roles are separate; capability-routed tasks | `CapabilityPopulation` (4) |
| B09 | Runtime closure {A,B} vs reference {A,B,C}; impact was advisory | defect | Runtime closure equals the reference on 300 random populations; `block` enforced in resolution, `reevaluate` invalidates performance evidence | `ClosureConformance` (3), `ImpactEnforcement` (4) |
| B10 | Kernel validation exhausted after 122 validations (fixed 128) | documented limit | Operator-only periodic funding with ceilings; kernel budget funded 128/h, ceiling 256 | `FundingLifecycle` (5) |
| B11 | No deadline field; slowed search ran 8.4 s unbounded | defect | Demand deadline (≤ 300 s) checked at every expansion, example and admission | `ConstructionDeadline` (2) |
| B12 | Dead node admitted and charged (3 attempts for a 2-node result) | defect | Nodes must reach the output | `GraphReachability` (2) |
| B13 | Trial records had 7 fields (path, status, …) | documented limit | Runs pin revisions, demand definition, catalogue, evaluation digests, budgets, costs, consequences; trials carry direct and transitive dependencies | `ConstructionProvenance` (1) |

Also found and fixed during the B10 work: any caller could `create_budget` with
any capacity, which is a minting path. Budgets now record an operator issuer.
A structural test checks that the development, ecology, population and fabric
modules never call funding APIs.

## 3. Verification

| Suite | Result |
|---|---|
| Runtime tests | **117/117** (71 existing + 46 new) |
| Reference regressions | 23/23 |
| Doc structural / negative | 19/19, 15/15 |
| L1 harness | 17/17 decisive (2 indeterminate, unchanged) |
| Dependency closure reference | 8/8 |
| Demo | passes |

## 4. X3: execution profiles

Medians of 30 runs after warm-up (`runner-benchmark.json`).

| Profile | `sum`, 3 ints: total | `range_bisect`, P3 request: compute / total |
|---|---|---|
| subprocess | 124.9 ms (start-up 124.8 ms) | 0.44 ms / 125.4 ms |
| persistent | **0.064 ms** | 0.43 ms / 1.90 ms |
| inprocess | 0.023 ms | 0.56 ms / 2.23 ms |

The proposed target (persistent < 20% of subprocess for `sum`) was met: the
ratio is 0.0005. For 5000-integer payloads, the persistent profile's time is
dominated by JSON encode/decode and worker-side validation ("transport" ≈ 0.9 ms).
Computation itself is ≈ 0.4 ms.

The benchmark also exposed a measurement bias, fixed before X1/X2 ran.
`providers.compute` recomputed the artifact specification, including
`inspect.getsource`, inside the timed region, which added about 250 µs to
every measured compute. Code identity is now cached per function object, and
only the provider function is timed.

## 5. X1: cumulative construction (preregistered)

| Condition | G1 | G2 | G3 |
|---|---|---|---|
| C-cum (depth 2) | ACQUIRED `parse→sum`, 12 search | ACQUIRED `[G1]→negate`, 16 | ACQUIRED `[G2]→double`, 15 |
| C-prim2 (depth 2) | ACQUIRED, 12 | NON_ATTAINMENT, 19 | NON_ATTAINMENT, 19 |
| C-prim4 (G3 only) | – | – | ACQUIRED `parse→sum→double→negate`, 93 |
| C-memo4 (G3 only) | – | – | ACQUIRED, 45 |

- **X1-H1 pass.** Three successive generations, each built on the previous acquisition. Execution lowers to 4 primitive nodes.
- **X1-H2 pass.** Primitive-only depth-2 search cannot reach G2 or G3.
- **X1-H3 (descriptive).** G3's marginal search cost under C-cum is 15 attempts, against 93 (typed) and 45 (memoized) for primitive-only depth 4. C-cum's total over G1+G2+G3 is 43 search attempts, still below both. It also spent 54 validation attempts across three acquisitions, against 24 for the single depth-4 acquisition. Including validation, C-cum is 97 attempts vs 117 (typed) and 69 (memoized). **Memoized primitive search is cheaper than cumulative construction overall** on this tiny catalogue; the cumulative advantage is per-generation reuse.

## 6. X2: bounded ecology (preregistered v1, primary result)

Measured niches (median ms over all requests; every member's output agreed on every request):

| Context | scan | scan_list | bisect | hash | Majority best |
|---|---|---|---|---|---|
| single-wide | 0.199 | 0.189 | 0.322 | 3.495 | scan_list (39/60) |
| many-narrow | 72.5 | 68.8 | 0.439 | **0.407** | hash (22/30), 8% over bisect |
| many-wide | 73.5 | 69.9 | **0.447** | 80.2 | bisect (30/30), specialist |

| Policy | P1 | P2 | P3 | P4 | Total ms |
|---|---|---|---|---|---|
| ecology | 14.2 | 637.6 | 390.2 | 6.5 | 1048.5 |
| aggregate-retire | 14.2 | 581.9 | 745.6 | 14.1 | 1355.9 |
| static (bisect) | 9.9 | 14.5 | 15.4 | 10.4 | 50.1 + 1110.3 calibration |
| offline-AS | 6.3 | 13.9 | 15.4 | 6.5 | 42.1 + 1110.3 calibration |
| portfolio (sum) | 115.3 | 4226.9 | 6723.3 | 143.6 | 11209.1 |
| oracle | 5.6 | 12.4 | 15.4 | 5.8 | 39.2 |

| Hypothesis | Result |
|---|---|
| X2-H1 coexistence | **FAIL**: 2 active at end (bisect, scan) |
| X2-H2 retention discipline | pass: hash was retired, but its 8% margin is below the 10% specialist threshold |
| X2-H3 retention value | pass: P4 6.47 ms vs 14.13 ms (0.46×) |
| X2-H4 adaptation ≤ 15 | **FAIL**: P1 none, P2 none, P4 16 |

What failed:
- **Hash was retired after P1**, on single-wide evidence only. "Redundant in every observed context" is a weak test when only one context has been observed.
- **Exploration cost dominated.** Forced exploration ran scan and scan_list three times each in every many-query context, at about 70 ms per run against 0.4 ms for the best member.

The retired member's later task was refused, as designed.

## 7. X2b: ecology follow-up (preregistered v2)

Two changes, preregistered before running: regeneration of archived members
when a new context appears, and breadth-first exploration that prunes members
estimated at more than 10× the best. Fresh store, same seeds.

| Policy | P1 | P2 | P3 | P4 | Total ms |
|---|---|---|---|---|---|
| ecology | 9.2 | 249.5 | 282.4 | 5.8 | 546.9 + 22.4 regeneration = 569.2 |
| aggregate-retire | 9.2 | 249.4 | 286.8 | 11.4 | 556.7 |
| offline-AS | 5.3 | 11.7 | 12.7 | 5.8 | 35.5 + 1090.8 calibration |
| oracle | 5.2 | 11.2 | 12.7 | 5.5 | 34.7 |

| Hypothesis | Result |
|---|---|
| X2b-H1 coexistence | pass: all 4 active at end |
| X2b-H2 retention discipline | **FAIL**: bisect (many-wide specialist) retired after P1; regenerated in P2 |
| X2b-H3 retention value | pass: P4 5.75 ms vs 11.40 ms (0.50×) |
| X2b-H4 adaptation ≤ 15 | **FAIL**: P2 latency 24 (P1 10, P3 4, P4 4) |

Regeneration worked as a mechanism: two members were restored by fresh
validation, about 11 ms and 3 validation attempts each. It repaired the
consequence of premature retirement, not its cause. The "retired member
refused" probe does not apply in v2, because both retired members were
restored before the end.

## 8. What this shows and does not show

- **Shows:** cumulative construction works within this bounded profile, with
  acquired abilities reused across three generations, enforced dependency
  blocking and complete provenance. The ecology can keep a population of
  validated alternatives for one capability, select among them per context,
  fund exploration, retire members with recorded evidence, and regenerate them
  through validation. Its retention rule protected P4 better than the naive
  aggregate rule in both runs.
- **Does not show:** that the ecology beats conventional algorithm selection.
  Given a calibration set, offline-AS was within 2–8% of oracle execution
  cost, while the ecology paid 16–27× oracle for its online exploration.
  With calibration charged, total costs are comparable: v2 ecology about
  569 ms vs offline-AS about 1126 ms. That comparison depends heavily on how
  calibration is priced and is not a superiority claim.
- **Identified next step:** retirement must not be allowed after a single
  observed context. A probation window is the obvious candidate: minimum
  periods since admission, or a minimum number of observed contexts. It needs
  its own preregistration.
- **Limits:** one host and one run per condition; single-sample cost
  measurements per request; a tiny catalogue; a synthetic, deterministic
  workload family.
