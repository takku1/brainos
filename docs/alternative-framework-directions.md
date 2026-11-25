# Alternative Framework Directions for BrainOS

Research comparison, 24 November 2026. These are candidate directions, not
implemented capabilities or established novelty claims. They complement the
[organizational world model proposal](organizational-world-models.md).

## Assessment

BrainOS has not reached an architectural peak. Its current design establishes
an execution and adaptation framework, but leaves several substantial choices
open: how computational abstractions develop, how mechanisms reason together,
and which alternative organizations survive for future use. No experiment yet
establishes the best combination.

Three directions deserve separate investigation. Developmental compilation is
the strongest next construction experiment. Collective inference is the largest
departure in how computation happens. An evolutionary repertoire strengthens
the ecology's ability to preserve and reuse alternatives. These judgments are
design recommendations, not measured rankings.

| Direction | Object that develops | Main hypothesis | Main risk |
|---|---|---|---|
| Developmental compiler | Reusable computational abstractions and construction language | Learned abstractions make new abilities cheaper to construct | Library bloat and search overfitting |
| Collective inference fabric | Coupled hypotheses and reusable constraints | Joint revision solves tasks that separate answers and fixed pipelines handle poorly | Nonconvergence, correlated errors, inference cost |
| Evolutionary repertoire | A bounded archive of behaviorally different organizations | Alternatives improve future adaptation and recovery enough to justify their cost | Diversity without external usefulness |
| Organizational world model | Predictions about organizational interventions | Experience improves the choice and sequencing of changes | Model error, confounding, maintenance overhead |

The four address different problems. Adding all of them at once would make
attribution difficult; each should first face a strong independent baseline.

## Developmental compiler

### Core idea

Let BrainOS learn useful operations for its construction language. A recurring
procedure becomes an explicit reusable abstraction, with parameters, contracts,
dependencies, and a lowering to existing operations. Later construction can use
that abstraction rather than repeatedly search through its internal sequence.

For example:

```text
parse -> normalize units -> check consistency
                    |
                    v
         validated_measurements(schema, units, policy)
```

The learned operation must retain its context restrictions and failure behavior.
Its name alone does not establish generality. A specialization for one input
format must not silently become a universal measurement-processing ability.

Initially the new operation is a macro or composite provider. It lowers to the
existing instruction contract and does not become a trusted kernel opcode.
Optimization or compilation into a different implementation is a separate
candidate requiring equivalence or independently measured contract satisfaction.
Cached outputs, reusable abstractions, optimized implementations, and newly
invented primitives are different outcomes.

### Why it changes the developmental problem

Ordinary composition asks which arrangement of existing operations solves a
task. Developmental compilation also asks which abstractions make future
arrangements easier to discover. A shorter program is useful only if its
abstractions improve construction, execution, reliability, or comprehension at
an acceptable total cost. Renaming a sequence without changing those quantities
does not establish a developmental advantage.

This has established antecedents: DreamCoder learns program abstractions and
search guidance. The BrainOS extension would have to handle heterogeneous
provider contracts, costs, dependency invalidation, recovery, and effects rather
than assume that library learning itself is new. [DreamCoder](https://arxiv.org/abs/2006.08381)

### Minimal mechanism

1. Collect validated construction traces and failure cases from Doc 27's domain.
2. Propose parameterized repeated fragments using typed structural matching.
3. Give each abstraction a scoped contract and a dependency-preserving lowering.
4. Evaluate whether using it helps on independent tasks.
5. Retain it only when its measured value exceeds construction and carrying cost.

Begin with deterministic, acyclic, effect-free record processing. Do not infer
semantic equivalence merely from similar syntax. Unit conversions, hidden state,
evaluation order, and failure behavior can invalidate an apparently repeated
pattern. Parents remain available until any replacement obligations are met.

### Decisive experiment

Compare a flat primitive library, ordinary memoization, a human-designed macro
library, and learned abstractions under the same examples, primitive access,
search resources, and final evaluation. Charge abstraction discovery, library
matching, validation, storage, and execution. Use held-out structural task
families, not only new constants in familiar templates.

Measure total cost to reach a fixed coverage/retention target, final coverage,
failed constructions, and library maintenance. Report both cold-start cost and
later reuse. Match total resources rather than assuming an equal expression
depth is fair: a macro hides multiple primitive operations.

The hypothesis is unsupported if gains disappear against memoization or a
competent static macro library, if unrelated tasks become harder to search, or
if carrying cost exceeds future savings. A changed construction language does
not by itself establish a new primitive or broader intelligence.

### Fit with current BrainOS

[Doc 19](current/19-organizational-calculus.md) already makes composite abilities
first-class providers; [Doc 27](current/27-candidate-construction.md) already
allows reusable construction specifications. This proposal selects a concrete
learning target within that scope: which abstractions to add, parameterize,
revise, and retire. It does not require another adoption layer.

## Collective inference fabric

### Core idea

Organize some computation around shared uncertain variables and constraints.
Providers contribute partial information and revise coupled hypotheses rather
than simply pass completed answers down a fixed pipeline.

Consider ambiguous object tracking. Geometry constrains possible locations;
motion constrains changes over time; object identity constrains which detections
can refer to the same entity. Each mechanism may be inconclusive alone. Their
joint constraints can rule out interpretations that independent predictions
leave unresolved.

A propagator approach connects computational elements through cells accumulating
partial information. This is an established programming model, not a new
BrainOS invention. [Propagator model](https://groups.csail.mit.edu/mac/users/gjs/propagators/)

### What needs to be explicit

Each variable needs a type, context, version, uncertainty representation, and
provenance. Each mechanism declares the variables it reads and revises, its
assumptions, resource use, and stopping behavior. Contradiction must be an
observable result rather than something silently averaged away.

Do not assume all uncertainty updates accumulate monotonically. Exact interval
narrowing, probabilistic belief revision, neural residual updates, and removal
of challenged support have different semantics. A monotone propagator argument
does not prove convergence for arbitrary recurrent learned mechanisms.

Keep observation time separate from inference iteration. Bound computation;
define residual/termination checks and explicit inconclusive outcomes. When
support is invalidated, recompute affected conclusions from remaining support
instead of assuming an old merged state can be repaired by subtraction.

Joint agreement is not independent evidence. Iterating a mistaken premise through
several mechanisms must not amplify its authority. The fabric produces claims
and estimates; the epistemic kernel continues to govern evidence and permission.

### Decisive experiment

Use a bounded relational task with independently checkable answers and controlled
ambiguity. Compare independent providers, a tuned feed-forward pipeline, a
conventional constraint/factor solver, and the proposed heterogeneous inference
fabric. Match observation access and total compute, including all iterations.

Measure correctness, calibration, abstention, time to a valid result, sensitivity
to conflicting evidence, and recovery after withdrawing support. Vary graph size,
update ordering, stale inputs, and resource limits. Include cases where the
pipeline is sufficient, not only tasks chosen to require iterative reasoning.

If a conventional solver performs equally well more cheaply, the result supports
using that solver as a provider. If improvement requires extra observations or
extra iterations beyond the common budget, it does not establish the proposed
integration advantage. Nonconvergence and confident shared errors are failures.

### Fit with current BrainOS

[Doc 10](current/10-mechanism-network.md) already proposes a recurrent factor
mechanism family. [Doc 04](current/04-shared-representation.md) permits optional
integration surfaces and direct communication. The new investigation would
compare actual joint-inference semantics within those interfaces. It need not
make a shared workspace mandatory for every provider or application.

## Evolutionary repertoire

### Core idea

Preserve a bounded set of organizations with useful behavioral differences.
The active organization serves current work; archived alternatives can seed
future construction or recovery. An archive entry is an artifact with evidence,
not a continuously running instance and not a permit to execute.

Differences could include competence across contexts, resource tradeoffs,
recovery behavior, or failure-domain profiles. Structural diversity alone is
insufficient: different graphs can have identical behavior and correlated
failures. Likewise, an unusual behavior need not be useful.

MAP-Elites provides an established quality-diversity approach that preserves
high-performing solutions across chosen behavioral dimensions. Its results do
not establish that any particular BrainOS archive will improve adaptation.
[MAP-Elites](https://arxiv.org/abs/1504.04909)

### Minimal mechanism

Choose a small, explicit behavioral descriptor and budget. Store versioned
candidate organizations with lineage, supported contexts, validation expiry,
costs, and dependencies. Compare archive policies such as current-best,
Pareto-diverse, behavior-diverse, and cost-matched random retention.

Retrieval nominates a candidate. Before reuse, recheck contracts, evidence,
footprints, and current resource conditions. Keep diversity-related retention
separate from protected critical floors. Archive membership never excuses
admission or replacement validation.

The descriptor is itself a design choice: changing it changes what diversity
the system preserves. Record revisions and compare plausible alternatives.
Account for search and revalidation cost, not just bytes stored.

### Decisive experiment

Expose matched methods to the same history, then evaluate preregistered task
shifts, provider losses, and resource changes. Keep a final workload independent
of archive selection. Charge the complete archive budget and restoration cost.

Measure time and expenditure to restore or acquire required capability,
protected competence, held-out coverage, correlated failure, and archive reuse.
Include stationary workloads where a large archive should offer little value.

The hypothesis is unsupported if behavior-diverse retention fails to beat
cost-matched simpler archives, or if its gains vanish after search and validation
costs. More entries, more novelty, and more turnover are not success criteria.

### Fit with current BrainOS

[Doc 25](current/25-ecology-dynamics.md) already discusses diversity and stepping
stones; Doc 27 includes bounded artifact archives. The useful extension is a
specific repertoire policy and a fair test of its option value, not a claim that
BrainOS previously lacked diversity.

## How the directions can combine

Developmental compilation learns better building blocks. Collective inference
provides one kind of computational behavior those blocks may implement.
Repertoire search preserves different useful constructions. An organizational
world model predicts which changes or experiments are worth attempting.

That composition is a research hypothesis. A stronger generator can make a weak
planner look better; a larger archive can give a model extra exposure; a learned
macro can hide additional inference work. Test these factors independently
before interpreting the combined system.

A first combined experiment should use four arms with shared data and budgets:
ordinary typed search, learned abstractions alone, organizational prediction
alone, and both together. Match planning horizon, primitive access, historical
information, and tuning effort. Report each method's total expenditure and
non-attainment at the common budget limit. Do not assume the combined arm must
win or attribute its gain to synergy without the separate arms.

## Recommended sequence

1. Complete the existing minimal Core execution/recovery path.
2. Establish a competent typed-search and memoization baseline.
3. Test developmental compilation against static and learned library controls.
4. Test organizational prediction with equal history and lookahead.
5. Combine them only if the independent results justify it.
6. Investigate collective inference on a task that can distinguish its benefit
   from conventional solvers; test repertoire policies independently under shifts.

This is an implementation sequence for obtaining interpretable evidence, not a
ranking of ultimate potential. Collective inference could prove more important
than compilation; the current evidence does not decide that question.

BrainOS's strongest ambition remains a system that develops useful computational
organization. The alternatives here turn different parts of that ambition into
testable mechanisms. None establishes a universal optimum, open-ended invention,
or a reason to stop considering other frameworks.
