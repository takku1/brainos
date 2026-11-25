# BrainOS — Current Status

## Current phase

W1 is closed: the emergence meter, the organizational-capability test and
the net-value ledger are implemented and were exercised in the X4
continuous ecosystem. The next major workstream is W2 (real-ecosystem
integration); its adapter design note is due before any implementation.
Not full Core conformance; not independently reviewed.

## Active focus

W2: bring one external provider family (frozen checkpoints staged in
`src/models/`) behind the existing contracts, with nondeterministic
validation. The adapter design is specified (Doc 02 §2.12, Doc 07 §7.18,
R-02-14, R-02-15, R-07-12); the external boundary, registration,
execution, k-of-n validation and heterogeneous feasibility are
implemented and tested (R-02-14, R-02-15) — no separate neural kernel
and no special authority rules for language models. The Qwen probe ran
disclosed and non-confirmatory (admission passed, irregular demand
served where the deterministic parser refused); confirmatory execution
awaits a reviewed prereg. Carried forward:
demand-triggered recruitment, incremental retention assessment, kernel
overhead, non-vacuous assimilation validation, organizational fragility,
adaptation latency, and economic comparison against independently
initialized adaptive controls.

## Architecture summary

`docs/current` is one consolidated specification with each rule owned by
one document. The Doc 31 register is the source of truth — register: 218
requirements (implemented 46, partial 70, specified 87, documentary 15),
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

243 runtime tests pass, drift check reports zero errors, document checks
19/19 and negatives 15/15 (verified 2026-11-25 with the W2 boundary,
registration, execution and admission work; test counts are
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

## Deprecated / legacy

- Pre-31.12 register cells (all rows marked I…) are replaced by derived cells.
- Doc 21 sections 21.9-21.13 are an increment log, kept because results cite them.
- The frozen X3 runner reproduces only at 6c83409 by design: the kernel now
  refuses publication without a selection record.
- The original DOCX is archived as superseded in docs/archive/.
- Predecessor Z:\newbrain results are historical only.

## Last updated

2026-11-25 (W2 D1-D5 feasibility: external execution, k-of-n admission,
heterogeneous demo and Qwen probe; confirmatory prereg pending)
