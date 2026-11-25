# X4 preregistration: continuous developmental ecosystem

Frozen before any X4 run. `tools/run_continuous.py` refuses to run unless this
file matches its recorded digest and both files are committed unchanged at
HEAD. Results are committed separately and never edited.

## Question

Under what conditions does a self-developing organization become more valuable
than a fixed or conventionally adaptive one, after the complete cost of its
development (Doc 20 section 20.9)? X4 runs one persistent organization with
every mechanism active and compares it against controls on the identical
demand stream. Negative results are expected and valid.

## Design

One developing organization per demand seed. Five demand seeds: 11, 12, 13,
14, 15. Per-seed analysis; no pooling across seeds. Execution profile:
inprocess (deterministic pure computation; wall-clock varies, outcomes do not
depend on it except through declared search deadlines, which are generous).

### Demand stream (140 demands per seed: 70 alternating arith/lookup pairs)

Pairs alternate arith then lookup. Values are drawn from
`random.Random(seed)` up front, so every organization faces the identical
stream.

| Phase | Pairs | Arith demand | Lookup demand | Character |
|---|---|---|---|---|
| P1 | 20 | csv-sum | single-wide | recurring |
| P2 | 15 | csv-neg-sum | many-narrow | rare |
| P3 | 15 | csv-neg-double-sum | many-wide | novel (construction expected) |
| P4 | 20 | csv-sum (fresh values) | single-wide (fresh values) | recurring return |

- Arith values: 2-4 integers in [-9, 99] as a comma string. Expected outputs:
  csv-sum = sum, csv-neg-sum = -sum, csv-neg-double-sum = -2sum.
- Lookup values: data = 2000 integers in [0, 100000); single-wide = 1 query
  with width in [20000, 60000); many-narrow = 60 queries with width in [0, 4];
  many-wide = 60 queries with width in [1000, 3000]. Query lower bounds are
  drawn in range. Bands follow the trusted featurizer (single <= 2 queries,
  many > 32; narrow median width <= 16). Lookup expected outputs are the
  range_scan reference outputs, computed up front as declared ground truth;
  the cost table verifies every member agrees with them.
- Contracts, one capability per demand kind: arith-sum, arith-neg and
  arith-double are text->integer with 3 admission cases each (sums; negated
  sums; negated doubled sums); lookup is range-batch->integers with the
  X2/retention admission (3 cases). A composite that serves one arith kind
  cannot be admitted to another kind's capability: kind contracts are exact.

### Developing organization (live execution only)

- Capabilities defined once: arith-sum, arith-neg, arith-double, lookup.
  Lookup admits the four range primitives up front. Each arith kind admits
  composites as construction acquires them.
- Selection: one EcologyService for lookup and one raw EcologyPolicy per
  arith kind (median mode, min_samples 3, margin 0.10, epsilon 0.05,
  demand-seed draws). Same policy core; the service adds durable records
  where the member set is stable (lookup), the raw policy supports a growing
  member set (arith). Contexts are demand kinds for arith kinds (the text
  schema has no trusted featurizer, so contexts are declared labels, never
  measured features) and featurized bands for lookup. Exploration is allowed
  for the first 4 demands of each phase per capability, then disabled. A
  wrong output is observed at cost 10**12 ns (finite, effectively infinite).
- Construction: a demand whose kind was never served correctly triggers one
  CompositionSearch acquire for that kind's capability (cumulative,
  max_depth 2, max_candidates 64, deadline 60 s) on the phase development
  budget. NON_ATTAINMENT leaves the demand unserved; no demand is retried
  after acquisition (development pays forward). Acquire admits the member
  and binds the role only if free.
- Lifecycle (lookup only): at each phase end, assess every member citing that
  phase's invocations; redundant -> retire (reason recorded), not-best ->
  make dormant, retain -> nothing. At P4 start, wake every dormant member.
  No regeneration attempts. Arith has no lifecycle transitions: retention
  assessment needs a trusted featurizer and the text schema has none, so
  `assess` refuses by design; arith members are retained for the run.
- Assimilation (X3b folded in): at each phase end, one AssimilationSearch
  attempt over the arith member providers (max_candidates 8). Evaluation sets:
  observed = phase arith values, held-out = reserved phase values (2:1
  split). Dependents: bound roles with that phase's arith values. Gate:
  tolerance 1.5 per capability, horizon 50 epochs, defaults otherwise.
  role_cases covers every bound role with the arith admission cases. Publish
  if and only if the corrected gate selects a candidate. Every trial,
  rejection reason and publication is recorded.
- Maintenance: rates active 50 / dormant 25 per member per period, set at
  admission; `maintain` runs at each phase end.
- Budgets: one development budget pair per phase: attempts {30000} funds
  search, validation and evaluation; upkeep {maintenance: 100000} funds
  maintenance. The pair is the period's development funding: ledger charges
  require exact resource dimensions, so upkeep cannot share the attempts
  budget. One execution budget per seed: {attempts: 100000}.
- Measurement: `emergence.measure` per capability over each phase's demand
  tasks (after serving, before lifecycle transitions). `emergence.net_value`
  per phase per organization from the value table below. Verdicts per
  capability at run end (development budget 1000 case evaluations).

### Controls (counterfactual replay over a measured cost table)

The table measures every demand value on every candidate provider once
(lookup: 4 primitives; arith: every composite acquired that seed plus the
length primitive). Controls never execute live.

- fixed: per arith kind, the first composite acquired for that kind that
  seed (neg/double kinds with no acquisition are unserved at zero cost);
  lookup = per-context argmin over the first two P1 table rows per context.
  No development costs. Fixed builds are outside the horizon and uncounted:
  a declared limitation that favors fixed.
- adaptive: catalogue = all composites acquired that seed (setup cost = the
  developing run's total recorded construction+validation spend, counted in
  P1); lookup = the four primitives; per-kind (arith) and per-context
  (lookup) best-by-observed-mean selection among correct providers, else
  unserved. No lifecycle, assimilation or maintenance.
- oracle: per-demand minimum compute over the table; all other costs zero
  (declared lower bound, not an achievable organization).

### Value and units (declared before the run)

Value per served demand (output == expected, else zero): arith 10, lookup 2.
Latency floor: arith 5e9 ns, lookup 6e10 ns; lateness penalty 4 (arith) and
1 (lookup), subtracted past the floor. Native ledger units convert to NOV
units at: 1 unit = 1e6 ns = 1 attempt = 1 maintenance unit. The conversion
is a demand-owner declaration recorded here, not a measured exchange rate.

### Hypotheses (confirmatory)

- X4-H1 (completion): all 5 seeds finish all 4 phases; every
  (phase, demanded-capability) pair yields a meter report (no missing
  windows).
- X4-H2 (no omitted costs): NOV is computable for all four organizations on
  all seeds: every window carries all six cost components (controls record
  explicit zeros with the justifications above, never omissions).
- X4-H3 (X3b gate holds inside the ecosystem): every assimilation
  publication in every run carries a lineage whose selection record exists;
  every trial records its nomination, evaluation and rejection reasons.
- X4-H4 (verdicts produced): `organizational_verdict` returns a verdict in
  {organizational, compositional-but-fragile, redundant, neither,
  inconclusive-budget} with checks spent for both capabilities on all seeds.

### Exploratory (descriptive, no pass/fail)

Per-seed NOV tables (developing/fixed/adaptive/oracle), meter series,
verdict labels, assimilation outcomes, retention and erosion notes. A
developing organization that costs more than it returns is a finding about
when development pays, not a failure.

### Refusal conditions

Digest mismatch; this file or the runner not committed unchanged at HEAD;
any seed output file already present.
