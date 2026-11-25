# Preregistration: retention strategies (X2c) and matched-repertoire construction (X1b)

Written 2026-11-25. This file and `tools/run_retention.py` are committed and
pushed before execution. The runner refuses to run unless both are unchanged
at HEAD and this file matches the digest embedded in the runner. Negative
results are valid outcomes. No condition is required to beat the controls.

## Disclosure of what was observed before freezing

- **X2c**: only a `--quick` harness smoke test was run. That is 2 requests per
  segment, seed 101, a different and much smaller schedule than the one below,
  and its output is not a result. It printed H1 false, H2 true, H3 true,
  H4 true, H5 false, H6 true. The full X2c schedule has not been run.
- **X1b**: a harness smoke test ran the full X1b procedure. Its attempt counts
  are deterministic, so the X1b outcome, including Y1, was **observed before
  freezing**. Observed: primitive acquire 143 search / 54 validation, reacquire
  129 / 54; memoized 81 / 54, reacquire 75 / 54; Y1 true. The cumulative
  totals were truncated in the smoke-test output and not seen. X1b is
  therefore **descriptive only**; Y1 is reported but is not confirmatory.
- The B18 recomputation (v1 exact quantifier false, v2 true) was computed
  before freezing. It is a correction of existing data, not a hypothesis.

## X2c: retention strategies

Population: contract `range-count`; members range_scan, range_scan_list,
range_bisect, range_hash; persistent profile. Declared maintenance units per
period (active / dormant): scan 50/10, scan_list 50/10, bisect 100/20,
hash 400/80. These are synthetic declared costs, not measurements.

Seeds: 101, 102, 103, 104, 105, independent. Per seed, 150 requests in five
segments. Data are 5000 integers uniform in [0, 100000); each query has lo
uniform in [0, 100000 - width], hi = lo + width.

| Segment | Requests | Shape | Notes |
|---|---|---|---|
| E1 | 30 | single-wide: 1 query, width U[20000, 60000] | |
| E2 | 30 | many-narrow: 400 queries, width U[0, 4] | each request is many-wide (400 queries, width U[1000, 3000]) with probability 0.10: rare preview of a delayed specialist |
| E3 | 30 | single-wide | recurring environment |
| E4 | 30 | many-wide | delayed main demand |
| E5 | 30 | many-narrow | recurring environment |

**Measurement.** In a fresh store per seed, every request runs once for every
member as a capability-routed BrainOS task, with member order shuffled
(seed + 1000). Recorded per run: worker compute ns, runner total ns,
end-to-end wall ns (task create through result) and the invocation ID.
Calibration for offline-AS uses 2 requests per shape (seed + 2000).

**Replay.** Each condition runs on its own copy of the measured store, so
lifecycle transitions, assessments, wakes and regenerations are real and
independent. Observations cite the real invocation of the chosen member.
Matched across conditions:
- exploration budget: 16 initially, then 8 per period, ceiling 24;
- validation budget: 200;
- period: 10 requests;
- retention checks at every period boundary;
- policy seed equal to the workload seed; min_samples 3, margin 0.10.

| Condition | Selection | Lifecycle | Retention parameters |
|---|---|---|---|
| R0 | v2: median, breadth-first, prune at 10x, epsilon 0.05 | direct retirement of the first redundant member (population-verified); regenerate archived members on a new context | defaults |
| R1 | as R0 | as R0 | min_age 3 periods |
| R2 | as R0 | as R0 | min_coverage 3 contexts |
| R3 | as R0 | dormancy first: not-best or redundant ACTIVE members become DORMANT; DORMANT members retire only with a redundant verdict after 3 dormant periods; on a new context, wake all dormant and regenerate all archived | dormancy_first, min_dormant_age 3 |
| R4 | uncertainty-aware: log-cost LCB/UCB, prior sd 1.0 | as R3 | as R3 |
| C1 | conventional contextual selection: median, epsilon 0.05, min 3 samples, no pruning | none | - |
| C2 | conventional online algorithm selection: R4's LCB bandit | none | - |

Reference values: the per-request oracle, and offline-AS (per-shape argmin on
calibration, calibration compute charged separately).

R0 re-expresses v2 under grounded retirement, checked every 10 requests rather
than every 30. It is not a byte-identical rerun of v2.

**Ledgers, reported separately:**
1. Provider compute: summed worker compute of chosen runs.
2. End-to-end: summed end-to-end wall time of chosen runs.
3. Organizational: exploration runs; validations, with their attempts,
   compute ms and wall ms; assessment count and wall ms; maintenance units.

Total cost is defined as compute ms + validation compute ms + maintenance
units / 1000, all on the compute boundary.

**Metrics.** Cumulative regret against oracle (compute). Near-optimal rate
(<= 1.10 x oracle). Adaptation latency per segment (first r with r..r+4
near-optimal). Competence retention: the fraction of requests for which some
ACTIVE or DORMANT member is near-optimal. Mean active and dormant population.
Retirement errors: retirements of a member that is a specialist in the
seed's table, meaning the oracle-majority best in some context by more than
10% median margin over every other member. Regenerations and wakes. Refused
transitions.

**Hypotheses (pass/fail, 5 seeds):**
- **X2c-H1**: summed retirement errors for R3 and for R4 are each lower than
  for R0.
- **X2c-H2**: R3 and R4 competence retention equals 1.0 on every seed.
- **X2c-H3**: R4 total cost <= R0 total cost on at least 4 of 5 seeds.
- **X2c-H4**: R4 total cost <= 1.10 x C2 total cost on at least 4 of 5 seeds.
- **X2c-H5**: R4's maximum segment adaptation latency <= 15 on at least
  4 of 5 seeds. A segment with no qualifying run counts as failed.
- **X2c-H6 (exact coexistence quantifier)**: for R3 and R4, on every seed, at
  least 3 members are retained at the end, and each observed context has ONE
  retained member that is near-optimal on a majority of that context's
  requests.
- **Descriptive**: every ledger and metric for all conditions, offline-AS and
  oracle.

**Live check (B17, descriptive).** For seed 101, R4 selection is executed live
(only chosen members run, no lifecycle reviews). Its compute and end-to-end
totals are reported next to replay.

## X1b: matched final repertoire (descriptive; see disclosure)

All methods acquire the same repertoire {G1 csv-sum, G2 csv-neg-sum,
G3 csv-neg-double-sum} (demands and admission cases as in X1):
- **cumulative**: depth 2 with acquired composites.
- **primitive**: typed search at the minimal depths 2, 3, 4, max_candidates 256.
- **memoized**: memoized primitive search at the same depths.

Then 20 reuse tasks per capability, a support impact on the bound `sum`
primitive, and re-acquisition of the full repertoire. Reported: acquisition
and re-acquisition search/validation attempts, reuse attempts and compute,
composite count, transitive dependency edges, and impact-affected providers.
Y1 (all methods acquire the full repertoire) is reported but was observed
before freezing.
