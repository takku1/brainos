# W2 L2 confirmatory results: heterogeneous computation (NL→IR sums)

Executed after clearance in a pinned worktree at 35d5182; verified
frozen before execution. Results committed separately, never edited.
Seeds 21–23. This file records outcomes; it makes no claims beyond
what the numbers show.

## Hypotheses

| Seed | H1 completion | H2 accounting | H3 verdict | H4 coordination | H5 cost premium |
|---|---|---|---|---|---|
| 21 | pass | pass | pass (redundant, 9/100) | pass (4 vs 2) | pass (~278000×) |
| 22 | pass | pass | pass (redundant, 9/100) | pass (4 vs 2) | pass (~263000×) |
| 23 | pass | pass | pass (redundant, 9/100) | pass (4 vs 2) | pass (~257000×) |

15/15 hypothesis evaluations pass. Qwen admitted k-of-n on all three
seeds. No aborts; no reruns; no tuning (frozen workload, prompt,
sampling, thresholds).

## Net organizational value (declared CPU-inference cost model)

| Seed | Fixed | Neural | Coordinated | Oracle |
|---|---|---|---|---|
| 21 | +17.6 | −29941.0 | −22527.2 | −7469.8 |
| 22 | +17.6 | −29574.8 | −22391.5 | −7339.7 |
| 23 | +17.6 | −28588.6 | −21828.4 | −6981.5 |

Higher is better. Units are declared attempts (1 unit = 1e6 ns).

## What this establishes — and what it does not

1. **Interoperability succeeded.** A neural provider (Qwen3-0.6B) and a
   deterministic provider served demands through the same member-task
   contracts, permits, budgets, ledgers and evidence records, with no
   neural-specific authority rules. A1, A7 hold.
2. **Competence improved.** Coordinated execution served strictly more
   held-out demands correctly than the fixed control on every seed
   (4 vs 2): the neural provider covered irregular formulations the
   deterministic parser refuses by construction. H4 holds.
3. **Economic superiority failed.** Under the declared valuation (10
   per served demand) and the measured CPU-inference cost model, the
   additional competence did not justify the neural provider's cost
   on any seed: neural and coordinated NOV are deeply negative, and
   the oracle lower bound is negative too. This is a negative
   economic finding, not a hypothesis failure — it bounds where this
   neural provider pays, consistent with the preregistered
   expectation that feasibility ratios would be extreme.
4. **No emergent heterogeneous competence demonstrated.** The
   organizational verdict is `redundant` on all three seeds (9/100
   assessment budget spent): substitution analysis finds the
   capability re-servable without the organization as a whole. We
   have demonstrated heterogeneous coordination, not organizational
   dependence. Do not claim emergence here.
5. **Limited scope.** One capability family (NL arithmetic sums),
   four held-out demands per seed, one neural checkpoint, one
   deterministic parser, declared-not-calibrated exchange rates,
   provisional n=3/k=2 empirical admission (not statistical
   certification). A4 isolation evidence is conformance-test based
   (mock-adapter kill/crash/timeout), not confirmatory-run based;
   A5 determinism holds by construction for the parser and within
   the declared (n, k) bound for the adapter; A6 gaps are recorded
   in R-02-13 with uncalibrated uncertainty left unresolved.

Acceptance A1–A7 (Doc 07 §7.18) all hold under these qualifications:
A2 via H2 (all six cost components, complete arm set including
nonattainment); A3 via recorded (n, k) evidence with the abstention
taxonomy, and vacuously for assimilation (none attempted in L2 — no
neural assimilation exists to exclude). No economic superiority and
no emergent organizational competence may be claimed from this run.
