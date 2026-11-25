# 10 — Mechanism Network (one provider family, optional)

Dependency-aware recurrent factor network as a candidate neural core,
not a mandatory substrate. Typed variables revised by joint inference
over learned relational energies; one reusable mechanism serves many
bound instances across entities, relations, contexts, time.

Objects: world/event time t, inference iteration r, update index n kept
distinct. Variable v has typed latent x_v, binding, context, validity,
version, uncertainty. Factor a has scope S_a, mechanism type k(a),
parameters θ_{k(a)}. Four structures: factor incidence graph, unrolled
read/version DAG, learning DAG, execution manifest.

Energy-first formulation: E_t(x;Θ) = Σ w_e φ_e + Σ ψ_{θ} + prior;
w_e is bounded evidence quality, not authority; invalid evidence has
w_e = 0. Ported status: R0/R1/R2/R2b built; Oracle validates substrate
mechanics; selective state/parameter repair wins on average but no arm
wins outright; retention gap open. Use for precision-sensitive
relational inference where typed vector residuals beat scalars; do not
hardcode simulator parameters as learned mechanisms.

## 10.1 Collective inference as an optional provider strategy

Some tasks benefit from jointly revising typed uncertain variables rather than
passing completed answers through a fixed pipeline. Geometry, motion and identity
constraints, for example, can jointly resolve otherwise ambiguous tracking.
Implement this behind ordinary provider contracts; direct pipelines and standard
solvers remain eligible alternatives. It is not a new mandatory fabric or readout.

Each published variable includes type/context/version, uncertainty and support.
Mechanisms declare read/write scopes, assumptions, update algebra, cost and stop
conditions. Distinguish observation time, inference iteration and learning update.
Exact interval narrowing, probability revision, learned residual updates and
support withdrawal require different semantics. Monotone convergence reasoning
applies only when the declared algebra/order assumptions hold; it cannot certify
arbitrary recurrent learned mechanisms. Report contradiction and inconclusive
outcomes explicitly; do not average conflict away.

Bound iterations/time/resources and define residual/termination checks and
fallbacks. Withdrawn support triggers dependency-aware recomputation, not assumed
subtraction from a merged state. Iterated agreement shares its original evidence
and never increases epistemic authority through repetition. Doc 04 owns readout
integration; Docs 09/32 retain authority. Test against independent providers,
pipelines and conventional constraint/factor solvers (07 section 7.14).

The [propagator model](https://groups.csail.mit.edu/mac/users/gjs/propagators/)
is a primary implementation reference for partial information and update algebra.
Its monotonicity and merge requirements are conditions to check, not guarantees
for all BrainOS provider families. Full prior-art comparison remains task-specific.
