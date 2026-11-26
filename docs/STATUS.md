# BrainOS — Current Status

## Current phase

W1 is closed: the emergence meter, the organizational-capability test and
the net-value ledger are implemented and were exercised in the X4
continuous ecosystem. W2 L2 confirmatory execution is COMPLETE: all
five hypotheses passed on all three seeds (f950f91), Qwen admitted
k-of-n everywhere, coordinated exceeding fixed on held-out demands.
Track B (autonomous developmental runtime): the replaceable policy
interface is implemented with stateful homeostatic regulation
(B38-B43), and a persistent integration demonstration ran the full
disturbance-recovery arc on a separate store. Not full Core
conformance; not independently reviewed.

## Active focus

Two tracks, experimentally isolated. Track A (scientific validation):
B31-B37 corrected with mock-only/synthetic reproductions and 58
regression tests; final clearance (NOV arm set in H2, model content
digests, abort exit codes, seed re-execution refusal) verified, then
executed in a pinned worktree — H1-H5 pass on seeds 21-23, verdict
redundant on all seeds, Qwen admitted everywhere. NOV is deeply
negative for neural/coordinated arms at declared CPU-inference rates
(descriptive, disclosed pre-freeze). Results committed separately.
Track B (living organization): Doc 33 specifies the autonomous
developmental runtime as an integration milestone, not a new subsystem;
R-25-08 and R-07-13 are partial with the coordination core
(`src/brainos/development_policy.py`), R-02-16 stays specified. The
ADR demo (tools/run_adr.py) showed demand-triggered construction,
incompetence-triggered investigation, tiny-grant exhaustion abstain,
provider-loss recovery through dependency closure, persistence across
restart and sustained quiescence — with unsuccessful adaptations
preserved. Policy-driven dormancy (verified redundant) and recruitment
(wake after loss) are demonstrated end to end. `live/server.py` is
unified on the ADR policy: same HTTP/SSE/dashboard contract with
extended panels (competence, retention freshness, runway, churn,
estimated NOV, lineage, unresolved), explicit init/resume/--reset,
operator-forced phases journaled distinctly from the schedule.
The Qwen probe ran disclosed and non-confirmatory (admission passed,
irregular demand served where the deterministic parser refused).
Carried forward:
demand-triggered recruitment, incremental retention assessment, kernel
overhead, non-vacuous assimilation validation, organizational fragility,
adaptation latency, and economic comparison against independently
initialized adaptive controls.

## Architecture summary

`docs/current` is one consolidated specification with each rule owned by
one document. The Doc 31 register is the source of truth — register: 221
requirements (implemented 46, partial 72, specified 88, documentary 15),
derived from `docs/current/traceability.json`, never copied from older
status text. `src/brainos` implements a standard-library Python runtime:
durable SQLite authority, scoped permits and epochs, transactor
publication, an effect gateway, typed lowered graphs, capability
populations with a grounded lifecycle, and bounded composition and
assimilation. W1 added kernel-side measurement (`src/brainos/emergence.py`:
meter, capability test, value ledger); X4 ran one persistent developing
organization per seed against fixed, adaptive and oracle controls.

## Implementation vs validation

Implemented means built and tested, not validated. X4's confirmatory
claims cover instrumentation integrity, complete cost accounting and
operational discipline — not the economics. The ordering adaptive >
developing > fixed held on all five seeds but is descriptive, conditional
on declared and uncalibrated resource exchange rates. No arith capability
is robust (all compositional-but-fragile); lookup is redundant: resilient
emergent organizational competence is not demonstrated. Assimilation
publication never occurred, so live gate enforcement is untested (X3b
remains experimentally unresolved). Thin per-phase samples drove a true
specialist dormant in P1.

## Evidence so far

| Run | Outcome |
|---|---|
| X1 / X1b | Cumulative construction works. Cheapest for a matched repertoire (descriptive). |
| X2, X2b | Ecology failed coexistence or retention discipline, and adaptation. |
| X2c | 5 of 6 passed. Dormancy cut specialist loss; it does not beat plain uncertainty-aware selection reliably. Adaptation failed. |
| X3 | Correct rejection, state reduction and recovery held. The acceptance rule was unsound (4 incorrect acceptances) and the economics were undercounted. |
| X4 | 5 seeds, all hypotheses pass. Developing NOV > fixed on every seed; adaptive > developing on every seed (descriptive, declared rates). Coverage 1.0, regret 0.0, retention 1.0 throughout. Verdicts: arith fragile, lookup redundant. Zero assimilation nominations after P1; P1 specialist dormancy on thin samples. |

360 runtime tests pass, drift check reports zero errors, document checks
19/19, negatives 15/15, L1 harness 17/17 and dependency closure clean
(verified 2026-11-25 with the W2 clearance corrections, confirmatory
seeds 21-23, the ADR policy/demo work, the live observatory
unification, and the W3 investigation design; test counts are
point-in-time, register counts are derived).

## Key decisions

- Drift control (Doc 31 section 31.12): no claim of implementation without
  cited code and tests, no unclaimed code, and document status derived from
  register rows. STATUS.md synchronization is a mandatory workstream exit
  check, verified by the same gate.
- W1 closed: R-25-06 (meter), R-25-07 (capability test) and R-20-07
  (net-value ledger) implemented with positive and negative controls.
- W2 feasibility probe (disclosed, non-confirmatory, no committed
  results): Qwen3-0.6B admitted k-of-n on canonical sums and served an
  irregular demand the deterministic parser refused; deterministic+neural
  substitution, meter, verdict (redundant) and NOV all ran through the
  existing kernel paths. Full details in the session record.
- Store.journal() root fix: an event body carrying `seq` crashed every
  journal reader; the journal sequence now wins, with a regression test.
- Model payloads are optional external assets: `src/models/` payloads are
  git-ignored, a tracked manifest records identity, version, digest,
  license, provenance, requirements and contract compatibility, and Core
  never depends on a model, framework, accelerator or model directory.
- Experiments run only from committed, pushed, digest-matched
  preregistrations. Results are committed separately and never edited.
- Developmental code receives a restricted context; the kernel verifies
  every lifecycle, publication and recovery request.
- Track A exit (W2 L2 corrections): B31 arm attribution, B32
  completeness with explicit nonattainment, B33 failed-work accounting
  (kernel records validation spend on rejected candidates), B34 economic
  boundary with coordinated calibration charge and held-out oracle, B35
  strict IR, B36 comparative-evidence rule, B37 freeze manifest binding
  source, model, prompt, sampling, admission, seeds and runtime versions.
  Amendment-1 preserves the 695cfb7 freeze in history; confirmatory
  execution remains blocked pending review.
- ADR specified (Doc 33), not implemented: R-25-08, R-02-16, R-07-13
  created as specified rows with ownership and acceptance criteria; the
  live observatory effort is adopted as the ADR baseline, not a
  competing runtime. W3 keeps formal stability results.
- W2 L2 confirmatory (f950f91): executed in a pinned worktree after
  clearance; H1-H5 pass on all seeds, verdict redundant (9/100 budget),
  coordinated > fixed on held-out demands every seed, neural compute
  premium ~2.6-2.8e5x per served demand (H5: qwen_mean_ns/det_mean_ns =
  ~3.7e9/~1.4e4 ns, seeds 21-23). Correction 2026-11-25: an earlier
  status line reported "30-40x" from no record; that figure is
  withdrawn — nothing in the seed files supports it. Fixed NOV
  +17.6/seed; neural/coordinated deeply negative at declared rates.
  Original 695cfb7 freeze preserved in history; results embed head
  35d5182 and preregistration digest.
- ADR coordination core (B38-B43): hysteresis flags and cooldowns are
  stateful with member-snapshot comparison (blocked members count as a
  changed world); burn measured per step, never cumulative;
  membership never implies competence (grounded task outcomes required);
  retention from fresh assessments or youth implication, never counts;
  churn from member-snapshot deltas; unknown viability blocks
  unconditional within-bounds verdicts. Demo found and fixed two live
  defects (id-vs-name member matching; blocked members counted as
  serving). Dormancy/wake unexercised (drill verdict was retain);
  arith-neg recovery needs recurring demand after closure block.

## Deprecated / legacy

- Pre-31.12 register cells (all rows marked I…) are replaced by derived cells.
- Doc 21 sections 21.9-21.13 are an increment log, kept because results cite them.
- The frozen X3 runner reproduces only at 6c83409 by design: the kernel now
  refuses publication without a selection record.
- The original DOCX is archived as superseded in docs/archive/.
- Predecessor Z:\newbrain results are historical only.

## Last updated

2026-11-25 (Track A complete: clearance 35d5182, confirmatory f950f91
with H1-H5 on all seeds; Track B: B38-B43 policy upgrades, ADR demo
with disturbance-recovery arc, unified live observatory on the ADR
policy with extended panels and init/resume/--reset, quiescence and
lineage instrumentation, executor fail-closes, 360 tests green;
10-min run (638 decisions, restart preserved), 1-hour run (3600
decisions, 99.7% noop) and extended run (10273 decisions, 7
investigates, development confined to the first regime cycle, then
sustained quiescence; journal intact, ~10KB/tick); W3 program opened
with Doc 34 (definitions, perturbation design, environment proposal,
lifecycle gaps, journal-growth design, history inventory) and a DRAFT
W3 preregistration — no confirmatory W3 execution authorized)
