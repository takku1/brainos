# BrainOS run results: grounded retention (X2c) and matched-repertoire construction (X1b)

Contracts are in Doc 21 §21.12 and §21.12a. Host: Windows 11, CPython 3.12.10,
persistent profile. All members' outputs agreed on every measured request,
on all seeds.

## Provenance

| Item | Value |
|---|---|
| B14–B20 baseline | reproduced on 9b9e7bd (`baseline-findings.json`) |
| Freeze 1 | 7b651fe: preregistration digest 53170de8… |
| Run 1 | aborted by an implementation defect; no results written or observed (`RUN1-ABORTED.md`) |
| Freeze 2 | 63fdec4: original preregistration unchanged, plus `PREREGISTRATION-AMENDMENT-1.md` (c6307768…) |
| Run 2 | completed from 63fdec4: `experiment-results.json` (raw tables, seeds, decisions, ledgers), `experiment-brief.json`, `run2-stdout.json` |
| Pre-freeze disclosures | X1b outcome observed before freezing, so X1b is descriptive only; X2c only quick-checked on a different tiny schedule |

## B18 correction (published separately; originals untouched)

`coexistence-correction.json`: rescoring X2-H1 (v1) and X2b-H1 (v2) with the
exact preregistered quantifier gives **v1 fail** (unchanged) and **v2 pass**
(unchanged). The implementation's quantifier was weaker, but it did not change
either verdict.

## X2c: retention strategies (5 seeds, preregistered)

| Hypothesis | Result | Detail |
|---|---|---|
| H1 fewer retirement errors than R0 (R3 and R4) | **pass** | Specialist retirements summed over seeds: R0 7, R1 6, R2 0, R3 1, R4 1 |
| H2 competence retention = 1.0 (R3, R4, every seed) | **pass** | An active or dormant near-optimal member was always held. R0 0.999 |
| H3 R4 total <= R0 on >= 4/5 seeds | **pass** (4/5) | fails on seed 104 |
| H4 R4 total <= 1.10 x C2 on >= 4/5 seeds | **pass** (4/5) | fails on seed 104 |
| H5 R4 max segment adaptation latency <= 15 on >= 4/5 seeds | **FAIL** (1/5) | no condition, controls included, reached 4/5: C1 2/5, all others 1/5 |
| H6 exact coexistence (R3, R4, every seed) | **pass** | >= 3 members retained, and one near-optimal member per context |

**Total cost.** Defined as provider compute + validation compute + maintenance
units / 1000, all on the compute boundary. Values are medians over seeds, with
per-seed values in brackets.

| Condition | Median total (ms) | Per seed | Specialist retirements | Mean active / dormant |
|---|---|---|---|---|
| R0 (v2 policy, grounded) | 543 | 814, 624, 364, 440, 543 | 7 | 3.72 / 0 |
| R1 admission age | 542 | 729, 558, 341, 450, 542 | 6 | 3.96 / 0 |
| R2 coverage probation | 542 | 848, 599, 349, 387, 542 | 0 | 3.99 / 0 |
| R3 dormancy | 563 | 784, 563, 235, **2067**, 541 | 1 | 2.34 / 1.64 |
| R4 dormancy + LCB | **327** | 246, 333, 308, **2004**, 327 | 1 | 2.54 / 1.43 |
| C1 contextual epsilon-greedy | 1038 | 1575, 1231, 1038, 926, 1032 | – | 4.00 / 0 |
| C2 LCB bandit, no lifecycle | 346 | 421, 416, 346, 328, 328 | – | 4.00 / 0 |
| oracle | 49 | | | |
| offline-AS | 52 + 635 calibration | | | |

**Separate ledgers** (medians per seed and condition):
- **Provider compute:** as in the total above. Validation compute is below
  0.1 ms in every condition, and maintenance adds 6–9 ms.
- **End-to-end execution:** 2.5–3.2 s, dominated by per-task kernel overhead
  (permits, durable transactions) of about 17 ms per request, not by
  computation.
- **Organizational:**
  - Exploration runs: 26–45.
  - Validations for wake and regeneration: 0–2.4 per seed. Wakes were free
    unless stale, so they cost no validation.
  - Maintenance: 5,784–9,000 units. Dormancy saved 20–35% of upkeep.
  - Retention assessments: **about 2.1 s wall per seed** in every lifecycle
    condition, which exceeds the provider compute being managed.

**Live check (seed 101, R4 selection only, no lifecycle):** compute 159 ms,
end-to-end 2.71 s, against R4 replay with lifecycle at 242 ms / 2.93 s.

### What the failures are

**Seed 104 (R3, R4): strategy weakness, not an implementation defect.** The
trace is in `R4-104`:
1. `range_bisect` woke at the first many-wide preview in E2, but got no
   many-wide sample.
2. At the next review, "best in no observed context" held trivially for a
   context where it had zero samples, so it went dormant again.
3. The preregistered wake trigger fires only for new contexts. When many-wide
   became the main demand in E4, it was no longer new, so bisect never woke.
4. E4 was served at about 80 ms per request instead of 0.45 ms. The
   competence was retained (H2) but not recruited.

This is the absence-of-evidence problem again, this time inside the dormancy
rule. Every refused transition in run 2 was a legitimate population refusal
("not dormant long enough"); there were no implementation errors.

**H5: the adaptation criterion was not met by any condition.** The criterion
is five consecutive choices within 10% of oracle, and the strong control met
it on only 1 of 5 seeds. With single-sample measurements, near-tie members
(scan vs scan_list, hash vs bisect on narrow ranges at about 8%) make it very
strict. The result is reported as a failure, not reinterpreted.

**Assessment overhead: implementation efficiency, measured as preregistered.**
Each assessment re-verifies every cited invocation from the durable store, so
cost grows with history. Behavior is unaffected; the cost was large and is
reported as measured.

## X1b: matched final repertoire (descriptive only; observed before freezing)

All three methods acquired the full repertoire {G1, G2, G3} (Y1, not
confirmatory).

| Method | Acquire search / validation | Re-acquire after `sum` impact | Reuse (60 tasks) | Composites / dependency edges |
|---|---|---|---|---|
| cumulative | **43** / 54 | 43 / 54 | 180 attempts, 0.27 ms | 3 / 12 |
| primitive | 143 / 54 | 129 / 54 | 180, 0.28 ms | 3 / 9 |
| memoized | 81 / 54 | 75 / 54 | 180, 0.28 ms | 3 / 9 |

With matched repertoires, **cumulative construction is the cheapest to acquire
and to re-acquire**: 97 total attempts against 135 for memoized and 197 for
primitive. This reverses the X1 comparison, which set three acquisitions
against one. Validation and reuse costs are identical, because lowered
execution is identical. Cumulative carries more dependency edges (12 vs 9),
since it depends on its own earlier composites. The impact on `sum` affected 4
providers under every method.

## Assessment

Implementation: run 2 executed without defects. Grounded retirement, the
lifecycle, durability and the separate ledgers all behaved as specified. The
one implementation problem found is assessment efficiency.

Strategies:
- **Grounded retirement with coverage probation (R2) or dormancy (R3/R4)
  nearly eliminated specialist loss** (0–1 against 6–7).
- **Dormancy with uncertainty-aware selection (R4) matched or beat the strong
  conventional control on 4 of 5 seeds**, with 20–35% less maintenance. It
  failed badly on one, where a dormant specialist was never recruited.
- **No strategy beat plain uncertainty-aware selection without a lifecycle
  (C2) reliably.** At this scale, maintenance is tiny relative to computation,
  so dormancy has little to save, and its recruitment rule can fail.
- No condition met the adaptation criterion.
