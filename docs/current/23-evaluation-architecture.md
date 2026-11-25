# 23 — Evaluation Architecture

Status: partial — some requirements are built (Doc 31 register; Doc 21 section 21.0); the rest is specification, not implementation.

Capabilities without trustworthy evaluation evolve toward the
evaluator's flaws. Evaluators are therefore first-class providers
with their own capability contracts — competed, versioned, and
distrusted by default.

## 23.1 Evaluation families

| Family | Example | Integrity basis |
|---|---|---|
| Deterministic | Correct mathematical result | Exhaustive or property-based checks |
| Statistical | Classification accuracy | Held-out data, seeds, CIs |
| Formal | Proof or invariant verification | Proof checker, model checker |
| Environmental | RL outcomes | Instrumented environment, seeded episodes |
| Preference-based | Human evaluation | Rater agreement, blind protocols |
| Comparative | Candidate vs incumbent | Matched inputs, paired tests |
| Delayed | Long-term planning outcomes | Logged trajectories, counterfactual care |

No capability is assumed to have an obvious ground-truth target.
The nomination (Doc 22) names its evaluation family; a capability
without a named evaluator cannot enter competition.

## 23.2 Evaluator integrity (anti-Goodhart)

Evaluators carry provenance (what they measure, on which data, under
which version), validation (calibration against known-good and
known-bad providers), and independence checks (the evaluated
provider must not control the evaluator's inputs, data, or rewards;
shared ancestry between provider and evaluator is declared and
discounted). An evaluator that fails its own checks is quarantined
like any provider — optimization against a broken evaluator is a
failure mode (Doc 12), and exceptional competence at the wrong thing
is reported as evaluator failure, never provider success.

## 23.3 Evaluation of evaluators

Evaluator capability contracts compete: two evaluators of the same
family disagree → adjudication by a third family or by delayed
ground truth where available. Evaluation budgets are explicit
(Doc 20): measurement itself costs, and expensive evaluators must
earn their keep against cheaper proxies with measured fidelity gaps.

## 23.4 Trust termination (normative)

Every evaluation chain terminates per Doc 30: externally grounded
observations, formal verification, human judgment, or explicitly
trusted policy with scope and expiry. Distance-to-grounding is
reported with every verdict used for selection, authority, or
acquisition; adjudication itself must terminate or escalate, never
recurse into another unevaluated evaluator.

## 23.5 Adaptive evaluation and data access

Separate development/construction data, independent admission checks, and
final research evaluation. Record dataset/generator revisions, access roles,
query counts, and verdict details exposed to search. Repeated admission
decisions leak information even without raw examples. A repeatedly inspected
test panel is no longer untouched held-out evidence.

Before adaptive runs, choose a finite comparison budget and sequential
testing/multiplicity policy appropriate to the claim, or label the search
exploratory and confirm on a fresh panel. Log all attempts and stopping
decisions. Final-panel access ends untouched status; later optimization needs
fresh confirmation or a declared reuse method and assumptions. Criteria,
coverage definitions, and difficulty changes after results require a versioned
deviation and confirmation plan. Generators cannot set their own acceptance
criteria; generated challenges receive separate validity/relevance evaluation.

## 23.6 Uncertainty in initial evaluator families

| Evaluator | Result and decision rule |
|---|---|
| Exact deterministic bounded domain | Checked domain/property and exact verdict; sampled deterministic inputs still have coverage uncertainty |
| Bernoulli success/coverage | Success/trial counts, sampling unit/distribution, interval method and confidence level; cluster dependent repeated tasks/seeds |
| Comparative cost/quality | Paired task deltas and interval under a declared paired/clustered procedure; retain dimensions |
| Composite/fused estimate | Dependency graph and joint error model or conservative bound; unknown dependence is not independence |
| Preference | Rater/task sampling, agreement and uncertainty; distinguish disagreement from measurement error |

The initial construction recipe uses exact reference outputs, sampled task
coverage, and paired cost. Lower confidence bounds meet minimum floors;
upper bounds meet maximum limits; crossing a floor is inconclusive. Calibration
names domain and expiry. Do not average dependent confidence values or treat
sampled deterministic behavior as uncertainty-free. Unmodeled uncertainty
blocks decisions requiring that bound rather than becoming a negative verdict.

## 23.7 Organizational prediction evaluation

Evaluate predictions separately from proposal success and enforcement. Freeze
the model/guard/version and record predictions before an intervention. Compare
predicted coverage, retention, resource/latency deltas, impacts, failure and repair
against measured outcomes using each family's proper scores, intervals and
calibration tests. Report abstention/coverage and useful discrimination alongside
accuracy so an always-unresolved model is not an artificial winner.

One-step and multi-step errors are separate; shared errors cannot be treated as
independent rollout confidence. An incorrect prediction remains an error when
admission prevents harm. Rejected proposals have constraint/admission outcomes,
not measurements of unexecuted downstream effects. Evaluate applicability guards
and model/evaluator shared ancestry independently. Exact schema/type inference,
memoization and learned outcome prediction are separate explanations of success.
Model revisions use development/admission/final splits under section 23.5;
no provider can broaden its own accepted scope from its training performance.

## 23.8 Abstraction, inference and repertoire verdict scope

Abstraction evaluation pins the library and transitive lowering, checks semantic
parameters/failure behavior, and confirms on structurally held-out tasks. A macro
expansion has its declared behavior; a different optimized executable separately
owes equivalence or measured contract satisfaction. Do not infer equality from
matching syntax or a few examples. Library growth and vocabulary compression
alone establish no useful construction improvement.

Inference evaluation names update/uncertainty algebra, termination and contradiction
handling; overlapping support is not counted repeatedly. Archive descriptors
are measured selection features, not new evidence of authority or independence.
Descriptor changes version the selection policy. Separate these interventions
and their costs under Doc 07 sections 7.13-7.16 before attributing combined gains.
