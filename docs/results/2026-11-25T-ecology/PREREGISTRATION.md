# Preregistration: cumulative construction and bounded ecology

Written 2026-11-25, before any comparative run. `tools/run_ecology.py` embeds this
file's SHA-256 and refuses to run if the file changes. Negative results are
valid outcomes and are reported as such. No experiment is required to beat
its controls.

## X1. Cumulative construction

Catalogue (bound roles): parse_csv, sum, sum_loop, count, text_length, negate,
double. Execution profile: persistent. Budgets: search 2000 attempts, validation
400 attempts per condition, operator-issued. Deadline 60 s per demand.

| Generation | Demand (text -> integer) | Development examples | Admission cases |
|---|---|---|---|
| G1 csv-sum | sum | "1,2,3"->6, "10, -4"->6 | "4,5"->9, ""->0, "7"->7 |
| G2 csv-neg-sum | -sum | "1,2,3"->-6, "10, -4"->-6 | "4,5"->-9, ""->0, "7"->-7 |
| G3 csv-neg-double-sum | -2*sum | "1,2,3"->-12, "10, -4"->-12 | "4,5"->-18, ""->0, "7"->-14 |

Conditions, each on a fresh store:
- **C-cum**: cumulative typed search, max_depth 2, G1 then G2 then G3.
- **C-prim2**: primitive-only typed search, max_depth 2, G1 then G2 then G3.
- **C-prim4**: primitive-only typed search for G3 alone, max_depth 4, max_candidates 256.
- **C-memo4**: as C-prim4 with memoized example execution.

Metrics: status, search attempts (expansions plus example executions), validation
attempts, wall seconds, path.

Hypotheses:
- **X1-H1 (pass/fail)**: C-cum acquires all three generations at depth <= 2. The
  G2 path contains the G1 provider, and the G3 path contains the G2 provider.
- **X1-H2 (pass/fail)**: C-prim2 reports NON_ATTAINMENT for G2 and G3.
- **X1-H3 (descriptive)**: G3's marginal search attempts under C-cum, and C-cum
  totals over G1+G2+G3, against C-prim4 and C-memo4. Expectation, not a
  threshold: marginal cost lower, total not necessarily lower.

## X2. Bounded competitive ecology

Capability contract `range-count` (range-batch -> integers). Admission cases:
({data [1,5,9], queries [[0,5]]} -> [2]), ({data [], queries [[0,1]]} -> [0]),
({data [3,3,7], queries [[3,3],[4,8]]} -> [2,1]).
Members: range_scan, range_scan_list, range_bisect, range_hash. Profile: persistent.

Workloads (seed 2026; data redrawn per request: n = 5000 integers uniform in
[0, 100000); each query lo uniform in [0, 100000 - width], hi = lo + width):

| Phase | Requests | Queries per request | Width (hi - lo) |
|---|---|---|---|
| P1 | 30 | 1 | uniform [20000, 60000] |
| P2 | 30 | 400 | uniform [0, 4] |
| P3 | 30 | 400 | uniform [1000, 3000] |
| P4 (return) | 30 | 1 | uniform [20000, 60000] |

Context: trusted featurizer `ecology.featurize` (query-count band x median-width band).

Measurement: every request runs once for every member as a BrainOS
capability-routed task, with member order shuffled per request (seed 5). Each
task is permit-checked and budget-charged. Primary cost: worker-measured
`compute_ns` of the invocation. `total_ns` is also recorded. All policies replay
the same measured table.

Ecology policy: min_samples 3, margin 0.10, epsilon 0.05, seed 11. Exploration
budget: 16 attempts initially, with an operator funding policy of 16 per phase
(ceiling 24); one attempt per exploratory choice. After each phase, at most one
member with justified retirement evidence is retired from the BrainOS
population with that evidence recorded.

Controls:
- **static**: best mean cost over a calibration set, then fixed.
- **offline-AS**: per-context argmin over the calibration set, then fixed
  (conventional algorithm selection).
- **portfolio**: all members every request; resource cost is the sum,
  latency the minimum.
- **oracle**: per-request minimum.
- **aggregate-retire**: same online policy, but after P3 keeps only the 2
  members with the best mean estimated cost across observed contexts.

Calibration set: 4 requests from each of the three phase distributions
(seed 7), measured for all members. Its cost is charged to static and
offline-AS.

Metrics per policy and phase: summed cost; regret against oracle;
near-optimal rate (chosen cost <= 1.10 x oracle); adaptation latency (first
request index r such that requests r..r+4 are all near-optimal, else none).

Hypotheses:
- **X2-H1 coexistence (pass/fail)**: after P4, at least 3 members are active, and
  for each observed context some active member is near-optimal on a majority of
  that context's requests.
- **X2-H2 retention discipline (pass/fail)**: no retired member is a
  specialist, where a specialist is the oracle-majority best in some context
  by more than 10% over every other member.
- **X2-H3 retention value (pass/fail)**: ecology P4 summed cost <= 0.8 x the
  aggregate-retire P4 summed cost.
- **X2-H4 adaptation (pass/fail)**: ecology adaptation latency <= 15 in every phase.
- **X2-H5 (descriptive)**: totals against static, offline-AS (including
  calibration), portfolio and oracle.

## X3. Execution-profile benchmark

Profiles: subprocess, persistent, inprocess. Workloads: `sum` on 3 integers
(dispatch-dominated) and `range_bisect` on one P3 request (compute-dominated).
30 repetitions each after one warm-up. Reported: median startup, serialization,
transport, compute and total ns. Proposed target, not user-stated: persistent
median total for `sum` < 20% of subprocess median total.
