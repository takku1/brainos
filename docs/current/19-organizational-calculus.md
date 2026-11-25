# 19 - Organizational Adaptation and World Models

BrainOS adapts computational organizations and can learn from the consequences
of those adaptations. This document owns the replaceable organizational
prediction/planning strategy. Doc 24 owns transformation contracts; Doc 21 owns
records; Doc 22 owns proposal selection; Doc 07 owns the experiment. Core can
operate without this strategy. The research target is transferable adaptation
knowledge, not a mandatory neural self-model or another authority mechanism.

## 19.1 Adaptation targets and retained experience

| Target | Change | Example |
|---|---|---|
| Provider internals | How a component computes | Train an adapter or revise rules |
| Configuration | How an implementation is used | Tune a search heuristic |
| Relationships | Which providers interact | Change bindings or compose a pipeline |
| Organization | What abilities the system can realize | Construct, specialize, consolidate, or restore capabilities |

Immutable providers can support all organizational changes around them. A
calculator need not change for a new procedure to use it effectively. Distinguish
an isolated adaptation from learning reusable knowledge: acquiring an ability
changes the organization; retaining transformation experience can improve how
later changes are selected. Measure acquired competence, retained competence,
and future adaptation cost separately. Learning a better proposal policy does
not imply learning new provider primitives.

## 19.2 Transformations over authoritative state

Use Doc 24's Sigma = (G,K,X,E,A,R,M,H), not the graph alone. A transformation
proposal tau declares applicability, affected state/dependencies, preserved
contracts/floors, resource costs, and failure/recovery behavior. Its kind may
be deterministic, stochastic, nondeterministic, or externally dependent.
Proposals do not change active state; execution uses validated staged changes
and COMMIT. General composition validates its new nominated contract with
parents retained; replacement and retirement add parent-coverage obligations.

## 19.3 Task plans and organizational plans

Task plans arrange invocations to achieve a goal (Doc 32 section 32.11).
Organizational plans arrange transformations that change which task plans are
possible or affordable. A planner may propose both, but neither grants
authority. Each transformation still needs nomination, resources, isolation,
current evaluation, and publication. A successful plan does not by itself
establish reusable capability or scientific novelty.

The organizational loop is:

```text
measured demand -> retrieve transformation experience -> generate changes
  -> predict outcomes and assumptions -> bounded plan/probe/no-change
  -> execute one admitted intervention -> independently measure outcomes
  -> publish if validated -> record error, cost and recovery -> replan
```

## 19.4 Organizational outcome model

```text
M_theta(phi(Sigma), tau, context, relevant_history)
  -> distribution or bounded set over outcome y, or UNRESOLVED

y = [acquired/retained contract coverage, quality, latency,
     construction/operating costs, dependency impacts,
     failure/non-construction, recovery requirements and costs]
```

phi is a declared projection of registry contracts, published outputs,
sanctioned measurements and provenance, never private provider state. Its
features include semantic units/frames, handover/statefulness, shared resources,
version identities and evaluator/workload context where relevant. Population
size and aggregate accuracy alone generally omit decisive information.

The projection is not asserted Markov or complete. History, unresolved hidden
conditions, and out-of-domain abstention are explicit. Equal present coverage
does not imply equal future construction cost or reachable capability: test
future usefulness against a named workload distribution, not an intrinsic
intelligence or evolvability score. A model's own revisions and broadened
applicability conditions are independently evaluated candidates.

Prediction contracts identify target transformation/sequence, source revision,
feature/schema versions, context, horizon, model version, support, uncertainty,
applicability conditions, validity/expiry, and predicted outcome dimensions.
Doc 23 owns calibration and acceptance tests. Predictions guide trials; they
never satisfy actual admission, resource reservations, authority, or retention
checks on behalf of the proposed organization.

## 19.5 Transformation knowledge and applicability

The reusable object is a TransformationRecord (Doc 21 section 21.7), including
source conditions, assigned intervention, pretrial prediction, measured outcome,
total costs, failures, and recovery. Separate an observation, a learned
applicability hypothesis, and a verified property. One successful case is not a
transformation law; a broader guard is a new hypothesis with new tests.

Start with exact supported-case retrieval. Structural or semantic matching
outside those conditions proposes a trial, not reuse of an old validation.
Negative cases narrow guards; rejected, cancelled, failed and non-attaining
trials remain visible. Admission rejection reveals a constraint violation,
not the unobserved effect that would have occurred if execution had proceeded.
Label observation status and selection policy to avoid learning only from
successful or admitted candidates.

Doc 29 invalidates affected prediction properties when contracts, artifacts,
adapters, evaluators, workloads, or resource sharing change. Stable hashes may
justify exact result reuse only within a verified deterministic profile;
empirical performance and intervention effects need their own current support.

## 19.6 Bounded planning and enabling steps

Initially allow at most two changes per plan with fixed branching, search,
trial and resource limits. Compare outcome vectors; scalarization follows
Doc 20. Report one-step prediction error separately from multi-step rollout
error, retain uncertainty/dependence, and replan after every measured change.
An uncertain intermediate state is not silently treated as a valid next state.
Every prefix must preserve protected floors and remain affordable; a promising
terminal prediction cannot justify an unsafe path.

An intermediate capability may serve a named sub-demand without immediate
terminal reward. Doc 20 section 20.7 funds a bounded enabling step or probe;
this is not automatic reward for generating new internal work. If the path
fails, record spend/non-attainment and stop or obtain a newly justified grant.

Acceptance example: demand checked total, budget 3 units. Adding a parser costs
2 and exposes typed rows; composing checked total then costs 1. A direct provider
costs 5. Depth-two search finds the affordable parser/composition path although
neither affordable one-step action reaches the terminal goal. This hand-specified
example tests lookahead, not learned prediction. A competent symbolic planner
must also solve it; learning is tested only with incomplete models and transfer.

## 19.7 Implementation order and alternative strategies

1. Record interventions and use typed symbolic planning with ordinary memoization.
2. Add full successful/failed cases and explicit exact applicability matching.
3. Test learned guarded outcome prediction and selection of informative probes.
4. Broaden model families or horizons only as separately measured extensions.

No network architecture is prescribed. Case retrieval or an ordinary planner
can remain the selected strategy if a richer model adds no useful benefit.
Construction grammars and library learning generate candidates (Doc 27);
they do not themselves model intervention outcomes. Equality saturation applies
inside proven equivalence domains, not uncertain substitutions or new abilities.
Architecture-based adaptive control is a closest-system baseline, not a novel
mechanism renamed by this document.

## 19.8 Evaluation, causality and transfer

Doc 07 section 7.12 compares Static, Selection, Search, Cases and Model under
matched access, exposure, horizons and total costs. Attribute extra lookahead
or extra experience separately from learned prediction. Some tasks should
reward no change. Cost-to-target includes non-attainment and training/maintenance
overhead, not just cheap successes. A wrong predicted effect remains model
error when admission catches it; safety rejection is not predictive accuracy.

Observational performance correlations do not identify intervention effects.
Assigned interventions on reproducible isolated organizations can support
paired comparisons under Doc 28's assumptions; inability to clone relevant
state or isolate interference limits that claim. Matching graph patterns alone
does not establish transport across new implementations, schemas, statefulness,
or effect policies. Test these shifts separately and narrow failed guards.

## 19.9 Research starting points

These source links were carried from the supplied proposal as a prior-art
screen, not a new exhaustive review or independent replication. Their role is
to select strong comparisons, not to establish BrainOS novelty:

- [Rainbow](https://www.cs.cmu.edu/~able/publications/computer04/): architectural models and reusable adaptation infrastructure.
- [Feature-model-guided online learning](https://arxiv.org/abs/1907.09158) and [lifelong self-adaptation](https://arxiv.org/abs/2211.02658): structural adaptation knowledge, changing options and models.
- [Dyna](https://mlanthology.org/icml/1990/sutton1990icml-integrated/) and [PRODIGY strategy learning](https://cdn.aaai.org/AAAI/1994/AAAI94-090.pdf): model-based planning and reuse of problem-solving episodes.
- [DreamCoder](https://arxiv.org/abs/2006.08381): reusable abstractions and search guidance.
- [egg](https://arxiv.org/abs/2004.03082) and [Ruler](https://arxiv.org/abs/2108.10436): equivalent-program search and inferred rewrite sets; exactness conditions remain essential.
- [Build Systems a la Carte](https://www.microsoft.com/en-us/research/wp-content/uploads/2018/03/build-systems-final.pdf): persistent dependency traces and rebuild strategies.
- [Godel machines](https://arxiv.org/abs/cs/0309048): theoretical self-rewriting under encoded axioms; no optimality result is imported here.

The specific research target is transferable, scoped prediction of acquisition,
retention and repair interventions across heterogeneous organizations under
the same execution contract. Both usefulness and novelty remain testable.
