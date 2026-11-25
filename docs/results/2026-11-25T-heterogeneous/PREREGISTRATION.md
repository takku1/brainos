# W2 preregistration: heterogeneous computation (L2 NL→IR sums)

Frozen before any confirmatory execution. `tools/run_heterogeneous.py`
refuses to run unless this file matches its recorded digest and both files
are committed unchanged at HEAD. Results are committed separately and
never edited. This preregistration covers Level 2 only; Level 1 is
established by committed conformance tests (deterministic + mock
interoperability), and Level 3 awaits this level's outcome.

## Question

Can a neural provider and a deterministic provider compete for and share
one functional contract inside a single BrainOS organization, with the
neural provider holding a genuine niche the deterministic provider cannot
serve — measured, not asserted?

## Design

One persistent organization per demand seed. Demand seeds: 21, 22, 23.
Per-seed analysis; no pooling across seeds. Execution profile: inprocess
for deterministic providers; the Qwen adapter process for the neural
provider (CPU).

Capability `nl-arith` (text to text): natural-language sum requests
lowered to the typed intermediate representation
`{"operation": "sum", "values": [...]}`. Members: deterministic parser
(`parse_nl_sum`, canonical grammar only) and Qwen3-0.6B behind the §2.12
adapter (frozen checkpoint per `src/models/manifest.json`).

### Provider registration (pinned; the runner must use exactly these)

Qwen provider, capability `nl-arith`:

- implementation `qwen3-lm`, input `text`, output `text`
- cost `{"attempts": 30}` per task (declared, covers ~5 s generations)
- cost schedule (declared native units): initialization 30 s, inference 5 s,
  transport 1, memory 1500 MB, accelerator 0 s, overhead 1;
  units seconds/seconds/attempts/MB/seconds/attempts;
  measured-by adapter/adapter/kernel/adapter/adapter/kernel
- artifact pin: the manifest `Qwen3-0.6B/model.safetensors` sha256 digest
  (verified by the adapter at startup and by `tools/verify_models.py`);
  algorithm sha256
- identities: model `Qwen/Qwen3-0.6B`, runtime `qwen-adapter/cpu-torch`,
  tokenizer `Qwen3-0.6B`, prompt_template `qwen-probe-sum-v1`
- sampling: temperature 0.0, top_p 1.0, max_tokens 32, seed 11
- nondeterministic true; admission policy n=3, k=2

Prompt template `qwen-probe-sum-v1` (verbatim, `{input}` substituted):

```text
Request: "Add up 4 and 6."
{"operation": "sum", "values": [4, 6]}
Request: "Please add 1 and 9."
{"operation": "sum", "values": [1, 9]}
Request: "{input}"
```

### Admission (frozen)

Deterministic parser: exact validation on the admission cases below.
Qwen: k-of-n validation (n=3, k=2) on the same cases, Wilson intervals
recorded, per-design §2.12. Admission cases (exact expected strings):

- "Add up 2 and 3." → `{"operation": "sum", "values": [2, 3]}`
- "Add up 10 and 4." → `{"operation": "sum", "values": [10, 4]}`

### Workload (8 demands per seed, fixed templates, seeded operands)

Operands are integers drawn 0-99 from `random.Random(seed)`; ground-truth
IR is generated before rendering, so neither provider judges its own
correctness. No demand, rendering or operand set changes after freezing.

| Split | Context | Template | Count |
|---|---|---|---|
| calibration | canonical | `Add up {a} and {b}.` | 2 operand draws |
| calibration | irregular | `Please add {a} and {b} together.` / `Can you add {a} to {b}?` | 1 draw each |
| held-out | canonical | `add up {a},{b}` | 2 operand draws |
| held-out | irregular | `{a} + {b} = ?` / `Add up the numbers {a}, {b} and {c}.` | 1 draw each |

The three-operand form is exploratory upside: the deterministic parser
cannot serve it by construction.

### Independent evaluation

The runner (not a provider) checks each served demand: parse the output
as JSON, normalize the operation through the alias set `{"sum", "add"}`
→ `sum` (declared here; anything else is incorrect), require integer
`values` matching the ground-truth list exactly, then execute the sum
through an admitted deterministic `sum` member task and require the
result to equal the expected total. A demand counts as served only if
interpretation AND execution are correct. Abstention, malformed output,
timeout and provider failure are recorded as distinct non-served
outcomes; the deterministic parser refusing an irregular demand is a
clean refusal, not an error.

### Controls (all live on the identical stream)

- fixed-det: deterministic parser for every demand.
- neural-only: Qwen for every demand.
- coordinated: per-context (`canonical` / `irregular`) argmin of
  calibration mean-correctness via `ecology.offline_selection`
  (deterministic provider first on ties).
- oracle: per-demand minimum compute among correct executions across
  arms; all other costs zero (declared lower bound, not achievable).

### Measurement and value

Meter windows per organization per seed over that organization's demand
tasks (terminal states only); emergence verdicts per capability at run
end (development budget 100 case evaluations). Net organizational value
with the X4 declared conversion (1 unit = 1e6 ns = 1 attempt); value 10
per served demand, lateness penalty 4 past a 300 s floor. Maintenance is
zero (no upkeep declared); construction is zero (no developmental search
in this experiment); validation spend is recorded from admission.

### Budgets and timeouts

Validation budget 2000 attempts; execution budget 4000 attempts per seed;
30 s per admission draw and 60 s per task. No maintenance budget (nothing to maintain).

### Hypotheses (confirmatory)

- H1 (completion): all 3 seeds finish; every (seed, organization) yields
  a meter report and an NOV ledger (no missing windows).
- H2 (no omitted costs): NOV is computable for all organizations on all
  seeds with all six cost components present (zeros carry the declared
  reasons above, never omissions).
- H3 (verdicts produced): `organizational_verdict` returns a verdict in
  the 5-way set with checks spent, for every seed.
- H4 (coordination value): on held-out demands, the coordinated
  organization serves strictly more demands correctly than the
  fixed-deterministic control, per seed. (Requires at least one
  irregular demand served that the parser refuses.)
- H5 (neural cost premium): Qwen mean compute per served demand is at
  least 10x the deterministic mean, per seed. (Feasibility ratio is
  ~10^4; the threshold documents the price of flexibility, not a failure.)

### Failure criteria and refusal conditions

Provider failures (wrong output, malformed output, abstention, timeout,
adapter death) are data: the demand is unserved, costs are counted, the
run continues. Admission failure removes that member from all arms that
need it (neural-only empty; coordinated falls back per its rule); the
hypotheses are evaluated as-is, and H4 may fail — a valid negative.
Infrastructure failure (adapter will not start, store error, grant
exhaustion of a sized budget) aborts the seed, which is reported as
aborted, never silently replaced; a disclosed amendment may authorize a
rerun. Refusal conditions: digest mismatch; this file or the runner not
committed unchanged at HEAD; any seed output file already present;
unknown seed.

### Feasibility disclosure (pre-freeze observations, not results)

- Prompt v0 (zero-shot instruction): base Qwen3-0.6B ignored the
  instruction and continued the text (e.g. emitting
  `{"operation": "hello", "world":` fragments). Abandoned, not tuned.
- Prompt v1 (few-shot, frozen above): exact first-line IR on canonical
  sums (~4 s per generation on CPU; ~11 s model load).
- L1 Qwen normalization: attempted with an analogous few-shot template
  and FAILED — `"  a   b  c  "` → `"a"`, `"no-change"` → `"hello world"`
  (pattern completion, not transformation). No confirmatory
  Qwen-normalize claim is made; the template was not iterated further.
- Rejected irregular formulation: `"Sum of 3 and 9?"` → `'"'` (garbage);
  excluded from the workload with this note.
- Alias evidence: `"What is 5 plus 6?"` → `{"operation": "add", ...}`,
  motivating the declared `{"sum", "add"}` alias set.
- Mock behaviors used in feasibility: echo/identity for exact-match
  admission; the mock is a test double, never evidence for Qwen.
- Probe (90 s end-to-end, discarded): Qwen admitted 3/3 and 2/3;
  irregular `"Please add 7 and 8 together."` served correctly while the
  deterministic parser refused; verdict redundant; NOV deeply negative
  at declared rates (seconds of CPU inference vs 10-unit demands).
- Deterministic parser refuses all irregulars by construction (regex
  over canonical grammar); timeouts, crashes and malformed replies
  were exercised against the mock only.

## Amendment-1 (2026-11-25): runner accounting and evaluation corrections

The original freeze (digest
`95f7125607a74b09603852306147407d6edcb74c975bd600cfa498c93092be29`,
commit `695cfb7`) is preserved in history. Static inspection of the
frozen runner found seven defects (B31-B37), each reproduced with
synthetic or mock fixtures, each corrected below with a regression
test in `tests/test_heterogeneous.py`. No workload demand, seed,
provider configuration, prompt, sampling parameter, admission
threshold or hypothesis substance is changed by this amendment; the
frozen question is unchanged. What changes is how the runner
attributes, accounts and checks: previously silent or misattributed
cases now produce explicit records, and previously passing-by-default
checks now fail loudly.

- B31 (arm attribution): served demand is attributed by experimental
  arm (`fixed`, `neural`, `coordinated`), never by provider name. A
  coordinated execution served through either member credits the
  coordinated arm only; no demand is credited twice within an arm and
  none leaks across arms.
- B32 (completeness): the complete expected arm set is required.
  Every expected arm must yield a meter report or an explicit
  nonattainment record stating why (e.g. rejected admission with its
  error, empty selection, skipped demands). Silently missing arms
  fail H1. Admission rejection and an empty organization produce
  nonattainment outcomes, not silent disappearance.
- B33 (failed-work accounting): expenditure derives from durable
  reservations, allocations, invocation records and validation
  attempts, including failed, timed-out, rejected and cancelled work.
  Refusal before resource consumption is distinguished from failure
  after consumption. Rejected admission records its draw count on the
  candidate; validation spend sums over all membership candidates
  (admitted, rejected, abstained), so rejected Qwen admission carries
  its full cost instead of zero. Terminal failed tasks stay in the
  meter windows with their measured invocations.
- B34 (economic boundary): admission, calibration, held-out execution
  and organizational assessment are charged to the arm(s) requiring
  the evidence. Calibration demands are the selection evidence: fixed
  and neural pay their own calibration through their metered tasks,
  while the coordinated arm pays the full calibration table of both
  members. Shared initialization is not amortized. The runner records
  this boundary per seed in a `setup` block (calibration demands,
  compute, overhead and validation attempts per member). The oracle
  uses held-out demands only, with zero validation/assessment cost.
- B35 (strict IR): the evaluator requires exactly
  `{"operation": <alias>, "values": [<int>, ...]}` with a string
  operation from the frozen alias set and exact-integer operands.
  Boolean and floating-point operands are rejected even where Python
  equality would accept them; unhashable operation values cannot
  satisfy membership and are rejected without crashing. No coercion
  is applied downstream. Declared abstention (`ABSTAIN`) is recorded
  separately from malformed output and incorrect interpretation.
- B36 (comparative evidence): H5 requires valid successful
  observations from both provider families and a meaningful
  denominator. Missing deterministic observations, missing neural
  observations or a zero denominator report
  `insufficient-comparative-evidence` and fail; they are never
  counted as a pass.
- B37 (freeze integrity): the freeze binds the approved
  execution-relevant source tree (`src/brainos/*.py`,
  `tools/run_heterogeneous.py`,
  `implementations/qwen_adapter.py`, `src/models/manifest.json`),
  the model artifact digest and directory listing, the prompt text
  and version, sampling, admission, seeds and runtime package
  versions, recorded in `FROZEN.json`. The runner verifies the
  manifest before execution, the launcher asserts the model digest
  at the execution boundary, and any change to a relevant file or
  identity refuses. Unrelated repository changes remain allowed
  exactly because they cannot alter the pinned execution boundary.

Additional integrity rules in force for confirmatory execution:

- Served means both correct interpretation and correct deterministic
  execution; interpretation-only success is not service.
- Every expected demand-arm pair has an explicit terminal outcome: a
  `runs` entry or a `skipped` record. H2 verifies this coverage.
- Infrastructure aborts write `seed-<n>.aborted.json` (phase, error,
  HEAD, preregistration digest) and never overwrite; results are
  still never overwritten.
- The organizational-assessment budget declared above (100 case
  evaluations) is enforced by the verdict call; budget exhaustion
  yields `inconclusive-budget` with its spend, which H3 accepts as
  a produced verdict.
- Native external-resource measurements (nanosecond compute/total
  per arm alongside converted units) are recorded in each NOV entry;
  where no defensible scalar conversion exists, native units stand
  without conversion.
- The n=3/k=2 admission remains provisional empirical admission, not
  statistical certification; abstention, malformed, timeout and
  failure outcomes are preserved per draw in the admission evidence.
