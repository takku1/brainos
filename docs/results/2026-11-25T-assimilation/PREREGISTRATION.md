# Preregistration: X3 bounded assimilation

Written 2026-11-25. This file and `tools/run_assimilation.py` are committed and
pushed before execution. The runner refuses to run unless both are unchanged
at HEAD and this file matches its embedded digest. Negative results are valid.
Constructing a consolidated provider is not, by itself, evidence that
assimilation is beneficial.

## Disclosure of what was observed before freezing

- **Mechanism probe** (arbitrary data, not an X3 workload). For 5000 random
  integers: hash-index build ~0.21 ms (48 KB encoded), sort ~0.31 ms
  (29 KB); a sorted index is reusable by exact and range lookups. This informed
  the expectation that factoring onto a sorted index saves state but not
  necessarily build time.
- **Unit tests** used 600-element synthetic data. They revealed that
  microsecond-scale latency ratios are noise. Two rules were added before this
  preregistration: same-artifact contracts skip the latency check, and ratios
  are applied only above a 20 µs resolution floor.
- **Harness check**: `--quick` ran once (n = 300, one seed, two post epochs, a
  different configuration) and printed only `harness_ok`. No X3 outcome has
  been observed.

## Mechanism under test

`src/brainos/assimilation.py` and `transactor.commit_assimilation` /
`revert_assimilation` (Doc 21 section 21.13). Candidates are enumerated from
the trusted catalogue by declared admissible transformations: structural
factoring onto one shared prepare stage, duplicate selection, and structure
elimination. The original and wrapper configurations are controls only.
Each nominated candidate passes or fails the union gate:
- exact output equality on observed, held-out and rare sets;
- the declared per-contract answer-latency tolerance, above the 20 µs floor;
- downstream dependents rebuilt and output-equal;
- full-cost break-even within 50 epochs, from construction and evaluation
  compute against per-epoch savings in prepare, answer, maintained state
  (1 ns per byte-epoch) and declared provider upkeep (50 µs per provider-epoch).

Among accepted candidates, the one with the largest predicted per-epoch saving
is published.

## Scenarios

Data: n = 5000 integers uniform in [0, 100000), redrawn per epoch.
4 requests per capability per epoch. Observation: 4 epochs plus one held-out
epoch (seed + 7000) and one rare epoch (seed + 9000; exact key count / 10,
range widths 0–1). Post-publication horizon: 30 epochs (seed + 1).
Seeds 201–205. Persistent profile.

| Scenario | Parents (roles) | Workload | Tolerances | Expectation, not a threshold |
|---|---|---|---|---|
| SA exact redundancy | exact_hash, exact_dict (both in exact-count; role `exact` bound to exact_hash) | 200 keys per exact request | exact 1.5 | safe duplicate removal possible |
| SB partial overlap | exact_hash (exact-count), range_sorted (range-count); roles `exact`, `range`; composite `exact-total` = exact_hash then sum | 50 keys; 50 range queries, width U[10, 2000] | exact 3.0, range 1.25 | sorted-index factoring may preserve competence and reduce state |
| SC incompatible | as SB | 2000 keys (latency-sensitive); 50 range queries, width U[2000, 4000] | exact 1.25, range 1.25 | every candidate should violate a tolerance |

## Post-publication comparison (matched requests and measurement)

Every eligible provider is measured on every post-publication request, with
each structure kind prepared once per epoch from a cold cache. Policies are
replayed on the same table. Per-epoch cost =
answers + prepares of the structure kinds used + maintained bytes x 1 ns +
upkeep x maintained providers.

| Policy | Definition |
|---|---|
| originals | parents only; per capability, the parent with the lowest observation-phase answer cost; parents maintained |
| wrapper | as originals plus one maintained wrapper artifact |
| routing (conventional contextual) | all eligible providers maintained; per capability, the lowest observation-phase answer cost, state-unaware |
| shared-state (conventional structural optimization) | all eligible providers maintained; each epoch, the assignment minimizing the previous epoch's full cost |
| assimilation | the published assignment (originals if none accepted), plus construction (all evaluations) and publication-validation compute |

Ledgers are kept separate. The compute boundary covers the totals above. End
to end: median task wall time on the first 3 post epochs, run live through
roles. Organizational: evaluation and publication wall time, and recovery wall
time and validation attempts.

## Hypotheses (pass/fail)

- **X3-H1 correct rejection**: SC publishes no assimilation on any seed.
- **X3-H2 acceptance without false acceptance**: SA and SB each publish on at
  least 4 of 5 seeds, and there are zero incorrect acceptances across all
  scenarios and seeds. Incorrect means: any post-publication output mismatch,
  or a measurable post-publication latency ratio over tolerance.
- **X3-H3 competence**: every published assimilation has zero output
  mismatches on all post-publication requests, zero live mismatches including
  the downstream composite, and latency within tolerance out of sample.
- **X3-H4 full-cost economics**: in SB, assimilation's total cost <=
  originals' over the 30-epoch horizon, including construction and validation,
  on at least 4 of 5 seeds.
- **X3-H5 strong control**: in SB, assimilation's total cost <= 1.10 x
  shared-state on at least 4 of 5 seeds.
- **X3-H6 state**: in every SB seed with a publication, mean maintained state
  bytes per epoch <= 0.70 x originals; at least one SB seed must publish.
- **X3-H7 recovery**: in every SB seed with a publication, a post-publication
  support impact on the replacement followed by recovery:
  - restores correct outputs, including the downstream composite;
  - rebinds the parent;
  - refuses a permit issued under the assimilation.
  At least one SB seed must publish.
- **Descriptive**: SA economics, the wrapper and routing comparisons,
  predicted vs realized break-even, end-to-end and organizational ledgers.
