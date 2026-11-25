# BrainOS — Current Status

## Current phase

Bounded single-authority runtime with developmental mechanisms under
preregistered study. Not full Core conformance; not independently reviewed.

## Active focus

Workstream W0 (Doc 08): keep documents and code in lockstep, and carry the
X3 corrections and X2c open items. Next: W1, an emergence meter.

## Architecture summary

`docs/current` is one consolidated specification, with each rule owned by one
document. `src/brainos` implements a standard-library Python runtime: durable
SQLite authority, scoped permits and epochs, transactor publication, an effect
gateway, typed lowered graphs, capability populations with a grounded
lifecycle, and bounded composition and assimilation. The Doc 31 register is
the source of truth for what is built. Its cells derive from
`docs/current/traceability.json` and are checked against code and tests by
`tools/check_traceability.py`. Doc 21 section 21.0 is the generated
module-to-requirement map.

## Key decisions

- Drift control (Doc 31 section 31.12): no claim of implementation without
  cited code and tests, no unclaimed code, and document status derived from
  register rows. Of 211 rows: 41 implemented, 70 partial, 85 specified,
  15 documentary.
- Experiments run only from committed, pushed, digest-matched
  preregistrations. Results are committed separately and never edited.
- Developmental code receives a restricted context; the kernel verifies every
  lifecycle, publication and recovery request.
- Workstream order (Doc 08): integrity, emergence meter, real-ecosystem
  adapter, stability theory, mechanism design, kernel as protocol, governance,
  publication arc.

## Evidence so far

| Run | Outcome |
|---|---|
| X1 / X1b | Cumulative construction works. Cheapest for a matched repertoire (descriptive). |
| X2, X2b | Ecology failed coexistence or retention discipline, and adaptation. |
| X2c | 5 of 6 passed. Dormancy cut specialist loss; it does not beat plain uncertainty-aware selection reliably. Adaptation failed. |
| X3 | Correct rejection, state reduction and recovery held. The acceptance rule was unsound (4 incorrect acceptances) and the economics were undercounted. |

## Deprecated / legacy

- Pre-31.12 register cells (all rows marked I✗) are replaced by derived cells.
- Doc 21 sections 21.9-21.13 are an increment log, kept because results cite them.
- The original DOCX is archived as superseded in docs/archive/.
- Predecessor Z:\newbrain results are historical only.

## Last updated

2026-11-25 (drift control, X3 recorded, gate corrections, roadmap W0-W7)
