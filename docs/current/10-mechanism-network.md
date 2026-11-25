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
