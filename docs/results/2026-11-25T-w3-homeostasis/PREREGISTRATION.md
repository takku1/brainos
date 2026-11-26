# W3 homeostasis and stagnation: preregistration DRAFT (DO NOT EXECUTE)

Status: DRAFT. Unfrozen, unreviewed, no digest recorded. This file
must be reviewed, amended if needed, frozen and committed before any
confirmatory W3 execution. Running an experiment from this draft
would violate the execution discipline it defines.

## Question

Does the BrainOS developmental organization exhibit homeostasis
(viability maintained across environmental change through
developmental responses, with returns to justified quiescence), or
does it stagnate (development subsides for lack of mechanisms,
evidence or resources while deficiencies persist)?

## Design

One persistent organization per seed on a separate durable store,
driven by the unified observatory loop (Doc 33) under the reviewed
W2/W3 configuration. Four arms with matched initial knowledge and
matched resource boundaries:

- Static: fixed members only; the developmental policy always defers.
- Adaptive: EcologyPolicy selection among provisioned members, wake
  enabled, no construction.
- Conventional reconstruction: scripted re-admission/replacement
  through the same kernel gates with its own cost accounting; no
  policy-driven search. Separates construction-enabled recovery
  (developmental vs adaptive) from policy effectiveness
  (developmental vs conventional).
- Developmental: the full replaceable-policy loop.

Environmental schedule (scripted, journaled; independent of the
decisions it provokes): stable demand, drift, novelty, scarcity,
provider loss, active-but-incompetent provider episodes, recovery,
recurring on a 460-tick cycle. Phases may
repeat; organizational transformations are never scheduled by phase.

## Workload (TBD pending environment review)

The workload uses the approved bounded domain (Doc 34 §34.3) once
reviewed. Until then the exact demand distributions, admission cases
and thresholds are explicitly TBD — a workload invented here without
an approved vocabulary would prejudge the experiment. No confirmatory
claims may reference workloads constructed outside this section once
frozen.

## Measures (all from kernel records)

Time to detect (first investigate after deficiency onset), time to
initiate (first executed transformation), time to restore (first
correct service), developmental expenditure, retention and regression
(assessment verdicts before/after), population growth, churn per 100
steps, unresolved-deficiency duration, return-to-quiescence time
with the quiescence classifier label at return.

## Hypotheses (exploratory)

- W3-H1a (functional expansion): the developmental arm restores
  service after capability-destroying provider loss where the
  static and adaptive arms cannot, per matched loss.
- W3-H1b (policy effectiveness): the developmental arm restores
  service faster and at no greater measured cost than the
  conventional-reconstruction arm, per matched loss with explicit
  cost boundaries and a declared comparative margin.
- W3-H2: quiescence after recovery is classified verified-healthy
  (not conditional, not unknown) within 50 steps of restoration.
  An independent evaluator recomputes viability from kernel
  records; the policy's own classifier label is necessary but not
  sufficient evidence.
- W3-H3: no capability with a fresh retain assessment is retired or
  left dormant while demanded.
- W3-H4: cumulative developmental spend stays within the declared
  band across all phases.

## Acceptance and failure criteria

All must hold on every seed for a confirmatory pass: H1a, H1b,
H2–H4 as stated with the declared margins; no more than one
unresolved deficiency older than 100 steps at run end; zero silent
state changes (every transformation has a recorded decision and
kernel disposition); journal verifies clean. Missing observations
are censored, never imputed: a seed that aborts or loses its store
is reported as nonattainment for the affected hypotheses, not
dropped from the denominator. Failure of any criterion is a
reported negative, not a rerun trigger: no tuning, no re-freeze
without a new amendment.

## Scope and non-goals

Single organization's homeostasis vs stagnation only. No
convergence or stability theorem claimed. No organizational
world-model learning (Priority 4) — the developmental policy is
fixed for the run. No neural providers (Priority 5 is a separate
decision). No 8-hour duration (Priority 6 proceeds only after this
preregistration is reviewed, frozen and committed). Still TBD
before any freeze: approved vocabulary (Doc 34 §34.3), exact
demand distributions and admission cases, seeds, conventional-arm
procedure, independent-evaluator definition, comparative margins,
thresholds and budgets. Nothing may be tuned after freezing.
