# X4 results: continuous developmental ecosystem

Run from the frozen preregistration (`baseline-commit.json`), 2026-11-25.
Five demand seeds, per-seed analysis, no pooling. This file reports; the
seed JSONs are the evidence. Nothing here is edited after the run.

## Confirmatory hypotheses

| ID | Claim | Seed 11 | Seed 12 | Seed 13 | Seed 14 | Seed 15 |
|---|---|---|---|---|---|---|
| X4-H1 | all phases finish; every (phase, demanded-capability) yields a meter report | pass | pass | pass | pass | pass |
| X4-H2 | NOV computable for all four organizations (no omitted costs) | pass | pass | pass | pass | pass |
| X4-H3 | every assimilation publication carries a recorded selection; every trial recorded | pass (0 publications) | pass (0) | pass (0) | pass (0) | pass (0) |
| X4-H4 | verdict in the 5-way set with checks spent, both capabilities | pass | pass | pass | pass | pass |

## Net organizational value (per seed; higher is better)

| Seed | Developing (P1/P2/P3/P4) | Developing total | Fixed | Adaptive | Oracle |
|---|---|---|---|---|---|
| 11 | 225.8 / 169.3 / 168.4 / 220.0 | 783.5 | 751.7 | 787.7 | 788.6 |
| 12 | 217.8 / 164.2 / 164.4 / 214.1 | 760.5 | 752.2 | 789.0 | 789.7 |
| 13 | 216.8 / 164.3 / 163.4 / 218.6 | 763.1 | 753.4 | 791.5 | 792.0 |
| 14 | 220.0 / 164.9 / 162.7 / 219.7 | 767.3 | 753.2 | 790.3 | 790.2 |
| 15 | 219.8 / 165.3 / 164.8 / 214.5 | 764.4 | 751.7 | 788.0 | 788.3 |

On every seed: adaptive > developing > fixed, oracle at the top. The
developing organization beats the fixed one while paying its full
development costs (construction, validation, assessment, upkeep all
counted) against a fixed rival whose build is uncounted by declared
design. It loses to the adaptive control, which free-rides the developed
composite catalogue (its setup spend is counted in P1) without paying
lifecycle, assimilation or maintenance. That is a finding about when
development pays, not a failure: development beat doing nothing, and lost
to costless reuse of its own products.

## Meter series (developing organization)

Coverage 1.0, mean regret 0.0 and retention 1.0 in every phase window on
every seed, for every demanded capability. The organism served everything
it was asked, never paid a regret, and never lost competence it held. No
lateness penalties triggered (all invocations far under the declared
floors).

## Organizational verdicts (end of run, all seeds identical)

- arith-sum, arith-neg, arith-double: compositional-but-fragile. Structure
  dependence holds (no primitive serves any arith kind); substitution fails
  (one composite per kind, each load-bearing).
- lookup: redundant. No structure dependence (primitives serve it); every
  member is substitutable.

## Assimilation inside the ecosystem (X3b folded in)

No assimilation publications on any seed. P1 attempts stop early (fewer
than two parents). P2-P4 nominations return zero candidates: with one
composite per arith kind there is no shared substructure to factor and no
duplicate to select, so the corrected gate had nothing admissible to
judge. The gate's idle discipline is recorded, not assumed; X3b lineage
enforcement remains untested in the wild. A follow-up that engineers
duplicate parents (two composites per kind) would put publications and
the selection-binding check under live load.

## Lifecycle (lookup, all seeds identical)

P1 end: range_hash, range_scan and range_scan_list dormant, bisect
retained. P2-P3: bisect alone serves. P4 start: all three wake
successfully. P4 end: bisect and scan retain; hash and scan_list dormant
again. Note the sample sensitivity: ten lookup demands per phase spread
over four members leaves assessments thin, and the true single-wide
specialist (scan_list, ~100k ns vs bisect ~160k ns in the cost table)
went dormant in P1 while bisect retained. Nothing was retired: dormancy
preserved every member for waking, and the wakes restored availability.
Longer phases would give retention assessments more samples; phase length
is a sensitivity the next run should vary.

## Limitations (declared)

- Fixed builds are outside the horizon and uncounted, favoring fixed.
- inprocess profile: deterministic outcomes, wall-clock not measured as a
  cost beyond the declared floors.
- Value table, latency floors and the 1e6-ns = 1-attempt = 1-unit
  conversion are demand-owner declarations, not measured exchange rates.
- Arith has no lifecycle transitions (no trusted text featurizer; assess
  refuses by design), so arith erosion cannot be observed in this design.
- Single composite per arith kind: no consolidation pressure arose.
