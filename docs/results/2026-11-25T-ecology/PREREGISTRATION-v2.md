# Preregistration v2: ecology follow-up (X2b)

Written 2026-11-25, after X2 (v1) was run and reported, and before X2b runs.
v1 remains the primary confirmatory result; X2b is a separate follow-up and
cannot retroactively change v1. `tools/run_ecology.py --v2` embeds this file's
SHA-256 and refuses to run if it changes.

## Why a follow-up

v1 failed X2-H1 (coexistence) and X2-H4 (adaptation). Two causes were observed
in the v1 data:

1. `range_hash` was retired after P1, on evidence from the only context
   observed so far. Archived members are designed to return through fresh
   validation, but nothing triggered regeneration when a new context appeared.
2. Forced exploration ran every member min_samples times in each new context,
   including members whose first sample was about 150x the best (about 70 ms
   vs 0.4 ms). That cost dominated P2 regret.

## Changes (the only differences from v1; all enabled by `--v2`)

- **Regeneration on new demand**: when a context is first observed, every
  archived member is restored through `population.restore` (fresh validation
  on the contract's admission cases, charged to the validation budget) and
  rejoins selection and exploration.
- **Exploration pruning**: forced exploration of a member in a context stops
  once it has at least one sample there whose estimate exceeds 10x the best
  current estimate in that context. A pruned member counts as non-covering
  evidence for its own retirement only where its samples meet min_samples.
  Otherwise that context is insufficient evidence, which blocks retirement.
  To make pruning compare against measured rivals, forced exploration under
  v2 is breadth-first: each member is sampled once before any second sample.
  This was added before X2b ran, after a unit test showed depth-first
  exploration makes the pruning comparison vacuous.

Everything else is identical to v1 X2: members, admission cases, workloads,
seeds (2026 table, 7 calibration, 5 order, 11 policy), budgets, funding
policy, controls, metrics and thresholds X2-H1..H5. The measured table is
re-measured in a fresh store. v1's table is not reused.

## Hypotheses (same thresholds as v1)

- **X2b-H1 coexistence**: after P4, at least 3 members are active, and each
  observed context has an active member that is near-optimal on a majority of
  its requests.
- **X2b-H2 retention discipline**: no retired member is a specialist (v1
  definition).
- **X2b-H3 retention value**: ecology P4 cost <= 0.8 x aggregate-retire P4 cost.
- **X2b-H4 adaptation**: ecology adaptation latency <= 15 in every phase.
- **X2b-H5 (descriptive)**: totals against the controls; regeneration
  validation cost is reported separately and included in the ecology total.
