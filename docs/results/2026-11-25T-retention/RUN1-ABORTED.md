# Run 1 of X2c/X1b: aborted by an implementation defect (no results)

- **Frozen commit:** 7b651fe (preregistration digest 53170de8…, unchanged).
- **Started:** 2026-11-25 01:28 local. **Crashed:** 01:32, during seed 105, condition R3.
  Traceback: `run1-crash-stderr.log`.
- **Outputs:** `coexistence-correction.json` (B18 rescoring of v1/v2; verdicts
  unchanged) was written before X2c started. No X1b or X2c result was written,
  scored or printed. No X2c outcome was observed.

## Defect

1. Under `dormancy_first`, a DORMANT member was retired. The population
   verified the assessment and archived it (ecology decision 78 in
   `R3-105.sqlite3`).
2. `EcologyService._apply` handles `retire` with `policy.members.remove(member)`,
   which assumes the member is ACTIVE. For a dormant member this raised
   `ValueError` after the population had already accepted the retirement.
3. The runner's `review()` caught it with a broad `except Exception` and
   recorded a successful retirement as `retire-refused`. The policy kept the
   archived member in its dormant list.
4. The next review asked the population to assess that archived member. The
   population correctly refused, and the run crashed.

The same silent path can occur in any R3/R4 replay, so seeds 101–104, which
completed in memory, are also invalid. This is an implementation defect in
the frozen code (ecology.py and the runner's exception handling), not a
property of any retention strategy. A unit test of retirement from dormancy
through EcologyService was missing.

## Disposition

Correcting it requires changing frozen code. That needs a new, disclosed
freeze commit before any rerun; the preregistered design, hypotheses and
thresholds stay unchanged.
