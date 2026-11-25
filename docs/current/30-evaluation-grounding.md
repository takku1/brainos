# 30 — Evaluation Grounding and Trust Termination

Status: research — hypotheses and proposed mechanisms; nothing this document owns is implemented or validated.

Evaluators evaluating evaluators must terminate somewhere, or the
ecology becomes exceptionally competent at satisfying its own
detached judgments (Doc 23 §23.2). This document states where the
regress stops.

## 30.1 Termination conditions

| Grounding | Establishes |
|---|---|
| Empirical | Observed behavior or environmental outcomes |
| Formal | Properties under stated mathematical assumptions |
| Preference | Human judgments or preferences |
| Policy | Permitted behavior and delegated authority |

Policy authorization never establishes empirical truth: a trusted
policy can permit an action but cannot make a factual prediction
correct, and these two uses of one policy must be recorded
separately. The termination of each chain is recorded with the
verdict; a verdict that cannot name its termination is inadmissible
for L3 and for any authority decision.

## 30.2 Rules

Distance-to-grounding is reported as diagnostic metadata: how many
evaluator layers sit between a verdict and its termination. Chain
length is not a reliability penalty by itself — a long chain of
independently verified reasoning may beat a short chain resting on
one unreliable observation. Any distance-based discount must be
justified by a stated reliability model and evaluated like any
other claim, never assumed. Trust propagates on calibration,
dependence, uncertainty, verification assumptions, and reliability
— accounted per layer, with uncertainty propagated (not averaged
away) and evidence dependence discounted, not double-counted.
Circular justification is a defect: an evaluator chain that
terminates, directly or transitively, in a verdict produced by the
provider under evaluation (or its dependents) is rejected, with
the cycle named. Adjudication of evaluator disagreement
(Doc 23 §23.3) must itself terminate: the adjudicator names its
termination or the dispute is escalated, never resolved by another
unevaluated evaluator. Grounding is re-checked, not grandfathered:
external feeds drift, human preferences shift, policies expire —
termination conditions carry validity intervals and expiration
like any evidence (Doc 05); expired grounding invalidates
dependent verdicts through the same invalidation propagation, and
compromised evaluators trigger quarantine of everything they
verified within the affected window. An unresolved evaluation
(insufficient evidence either way) is distinct from a failed one
(evidence against): unresolved suspends dependent decisions and
requests specified missing evidence. Failed evaluations do NOT
invert dependent decisions — failure of a claim invalidates the
justification it provided, and dependents are recomputed from the
remaining admissible evidence. Inversion would treat "not shown
beneficial" as "shown harmful", which the evidence does not support.
This distinction is load-bearing for kernel implementation.
