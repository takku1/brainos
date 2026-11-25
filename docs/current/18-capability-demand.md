# 18 — Capability Demand and Discovery

Growth is demand-driven, not population-driven. The system spawns
capacity because it has evidence of an opportunity — never because
growth is intrinsically desirable.

## 18.1 Pipeline

Unresolved computational demand → capability nomination → candidate
construction → competitive evaluation → capability acquisition.

1. Unresolved demand: repeated failure, excess expense, high
   uncertainty, or explicit unmet requests against an existing
   capability, measured over an evaluation window (not one bad tick).
2. Capability nomination: define the missing function (contract
   skeleton per Doc 17 §17.1) plus evaluation criteria and hard
   floors. A nomination is a falsifiable artifact: it states what
   would count as filling the gap.
3. Candidate construction, in order: reuse (existing eligible
   provider), configure (retune a provider-local policy), compose
   (function composition of existing providers), train (new learned
   provider), instantiate (new algorithmic/symbolic provider). New
   capacity is the last resort, not the default.
4. Competitive evaluation: candidates vs existing alternatives under
   Doc 17 §17.2 protocol + applicable L3 gates.
5. Capability acquisition: publish the validated provider or
   composite through the Transactor; retire or demote what it
   displaces only after safe fallback is demonstrated.

Persisted errors become nominations; nominations become contracts;
contracts become competitions. Demand with no nomination is a log
entry, not a growth trigger.

## 18.2 Demand signals (all measured, none vibes-based)

Error persistence (failure rate over window with CIs), cost excess
(spend vs budget on the capability), uncertainty (calibrated
uncertainty above the escalation threshold), request backlog
(explicit unmet requests with contexts), residual predictability
(errors predictable from additional observations per a held-out
probe — growth is warranted only if the gap is closable).
Each signal names its window, threshold, and preregistered
counterfactual (what reuse/configure/compose would achieve first).

## 18.3 Capability-induced demand (research extension)

Demand can originate externally or from an acquired capability changing
feasible tasks, bottlenecks, or artifacts (Doc 25 sections 25.6-25.8).
A new parser might expose documents needing a consistency checker; its
existence alone does not establish a need for another provider.

An induced-demand record identifies triggering provider/artifact versions,
before/after context, affected consumers, observed gap or bounded probe,
resource estimate, and counterfactual without the change. An opportunity
without evidence remains an exploration hypothesis with a capped probe.
Normal nomination and reuse/configure/compose checks still precede birth.
Report external and induced demand separately so self-generated work
cannot masquerade as improved service to external tasks. A stationary
workload creates no obligation to keep generating demand.

## 18.4 Enabling sub-demands

A goal can require an affordable sequence although no affordable single change
meets it. Link a prerequisite nomination to the original goal, intended successor
step, expected intermediate contract, and abandonment/recovery conditions.
For example, typed rows enable a checked-total pipeline. This is a justified
sub-demand, not newly invented external demand. Doc 22 plans the sequence;
Doc 20 section 20.7 funds bounded prefixes without requiring immediate terminal
reward. Retain failure/non-attainment and do not count prerequisite coverage
as completed external-goal coverage.
