# BrainOS run results: X3 bounded assimilation (preregistered)

**Provenance.** The run executed once from frozen commit 6c83409, with
preregistration digest 293679fa…, over seeds 201–205 on the persistent profile.
It took 194 s and exited cleanly. Raw records (every candidate verdict, the
post-publication tables, ledgers, live checks and recovery drills) are in
`experiment-results.json`. Mechanism: Doc 21 §21.13.

## Verdicts

| Hypothesis | Result | Detail |
|---|---|---|
| H1 correct rejection (SC) | **pass** | 0/5 published; every candidate violated a tolerance and had negative per-epoch savings |
| H2 acceptance without false acceptance | **FAIL** | SA 4/5 and SB 4/5 published, but **4 incorrect acceptances** (every SB publication) |
| H3 out-of-sample competence | **FAIL** | zero output mismatches anywhere (post-publication table, 84 live tasks, downstream composite). But SB's exact-lookup latency ratio was 3.30–4.74x against a 3.0x tolerance |
| H4 full-cost economics (SB) | **FAIL** | assimilation 1032–1093 ms vs originals 28–30 ms over 30 epochs, because construction costs about 1 s |
| H5 vs shared-state control (SB) | **FAIL** | as H4 |
| H6 state reduction (SB) | **pass** | 77.7 KB to 29.4 KB maintained per epoch (−62%) on every publishing seed |
| H7 recovery (SB) | **pass** | 4/4 drills restored correct outputs (including the composite), rebound the parent after fresh validation (9 attempts, ~28 ms wall) and refused the permit issued under the assimilation |

## Ledgers (median over seeds)

| | SA | SB | SC |
|---|---|---|---|
| Post-horizon compute, originals | 15.5 ms | 29.5 ms | 43.3 ms |
| Post-horizon compute, assimilation (incl. construction) | 129.7 ms | 1063.5 ms | = originals |
| Construction compute (all evaluations) | 118 ms | 1033 ms | 10.9 s |
| Predicted / realized break-even | 32–50 / 1015–1178 epochs | 36–45 / 3916–5380 epochs | – |
| Publication wall / validation compute | 3 ms / ~0 | 28 ms / 0.01 ms | – |
| Live end-to-end per task | 14.1 ms | 14.3 ms | – |

## What failed, and why

1. **Construction cost was undercounted (implementation defect).**
   - The gate's break-even charged each candidate only its *own* evaluation.
     The preregistered accounting, correctly, charges all evaluations the
     nomination required.
   - So predicted break-even (32–50 epochs) was 20–120x too optimistic.
2. **No early termination (implementation defect).**
   - Candidates 170–460x slower than their parents were evaluated on every
     input.
   - In SB about 1 s of construction, and in SC 10–13 s, was spent proving
     hopeless candidates hopeless.
3. **Latency tolerance compared as a point estimate (gate design weakness).**
   - `exact_sorted` vs `exact_hash` runs at about 3.3–4.7x, straddling SB's
     3.0x tolerance.
   - Small in-sample medians fell below 3.0 on 4 of 5 seeds and passed;
     out-of-sample they did not. All 4 incorrect acceptances are this.
   - A gate needs a confidence margin, e.g. an upper bound on the ratio
     against the tolerance.
4. **Undeclared internal state (catalogue gap).**
   - Older primitives such as `range_bisect` and `range_hash` build structures
     inside their answer stage without declaring `prepare`.
   - The nominator therefore offered them as "structure-elimination"
     candidates: their state is hidden from both accounting and sharing.
5. **Duplicate removal does not reduce state (SA).**
   - An idle duplicate never builds its index, so SA's only saving was
     declared upkeep (50 µs per provider-epoch).
   - That is too small to repay any realistic evaluation.

## What held

- **Rejection.** The gate rejected every incompatible consolidation (SC,
  5/5) and every consolidation with negative savings.
- **Correctness.** No output-incorrect assimilation was ever published.
  Downstream dependents were rebuilt and stayed correct.
- **State.** Structural factoring produced a real, measured state reduction
  (−62%).
- **Publication and recovery.**
  - Publication was atomic.
  - Recovery restored parent competence only with fresh validation, and did
    not revive the assimilation's authority.

## Assessment

The assimilation mechanism (nomination, isolation, atomic publication, hidden-
dependency refusal and recovery) works and is safe on correctness. The
*decision rule* is not yet sound: it accepted candidates on noisy point
estimates and on economics that ignored most of their cost. In this domain,
with microsecond-scale lookups and thirty-epoch horizons, assimilation was not
economically justified once full costs are counted. Correcting the gate
(complete cost accounting, early termination, confidence-bounded tolerances,
declared internal state) is the next step. Any change requires its own
preregistration, and this result stands as recorded.
