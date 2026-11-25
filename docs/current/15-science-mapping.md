# 15 — Science Mapping (world models / sims / provenance / prereg / controls / replication)

Document role: research rationale and source mappings. Architectural rules
remain in their owning contracts/protocols (README ownership table); mappings
do not introduce additional runtime conformance requirements.


Science demands we were missing become gates, not commentary.

- World models (VAE vision + RNN memory + controller; policy in
  "dream"): OUR readout z_t + PREDICT op. ADOPT with new gate —
  calibrated uncertainty + measured sim-vs-real divergence required;
  sim-only claims fail L3 only where the claim requires
  physical-world transfer (Doc 07 §7.6 scoping) — mathematical,
  algorithmic, and game-domain claims evaluate validly in simulation.
- Simulators / sim-to-real (photoreal vs ROS-SIL vs contact/GPU
  rollouts; gap closed via domain randomization + system ID + paired
  real trajectories): ADOPT for Track R. Require paired-trajectory
  transfer metric + domain-randomization report per manifest where
  physical transfer is claimed; not required where it is not.
- Provenance/lineage (PROV-O entities/activities/agents; FAIR capture):
  OUR provenance invariant + evidence/learning graphs + M_k +
  OBSERVE/ENCODE/PROPAGATE. ADOPT — M_k/evidence graph serializes to
  PROV-O + content-hashed immutable audit store (named gap: no export
  schema today).
- Preregistration (timestamped hypotheses/methods/analysis plan;
  registered reports; counters p-hacking/HARKing): OUR M_k +
  episode-bound COMMIT + falsification reporting. ADOPT — registered M_k
  + frozen analysis plan + success thresholds before shared-learning
  runs; deviations logged as FORK, never silent edits (named gap: no
  prereg artifact today).
- Matched controls/ablations (change-one-thing; matched
  capacity/compute/tuning; multi-seed stats): OUR 4 matched arms + equal
  data/compute/latency + weak-monolith ban + Δ_learn + directional
  transfer, with routing matched EXCEPT when routing itself is the
  experimental variable (Doc 07 L3). ADOPT — family-appropriate
  statistics per Doc 23 (≥5 seeds + CIs provisional minimum for
  stochastic families only) + matched-draw controls per claim
  (named gap: no power-analysis rule today). Evidence depends on evaluation type (Doc 23) —
  five seeds are neither universally necessary nor sufficient:

| Evaluation type | Appropriate evidence |
|---|---|
| Deterministic computation | Exact test cases |
| Formal properties | Proof or model checking |
| Stochastic algorithms | Statistical estimates and uncertainty |
| Physical control | Environmental and transfer experiments |
| Human preferences | Controlled preference evaluation |
- Replication (direct same-procedure vs conceptual same-idea-new-method;
  OSC 2015 ~36/100 base rate): OUR G1 (two implementations, one
  contract) + G7 persistence/restart + repair transaction. ADOPT —
  independent-direct-replication slot (frozen-manifest rerun) +
  conceptual replication (second provider, same capability) + enforce
  parity-as-finding in CI.
Scoping rule: preregistration, PROV-O export, seed counts, and
replication slots are research-track policies (Doc 07 L3) and deployment
choices — NOT runtime requirements. A BrainOS runtime is conformant
without them; a research claim is not validated without the ones its
track preregistered. Likewise L1 independent-implementation conformance
checks contract compliance, while L3 conceptual replication checks
effect generality — related, never equivalent.

Science URLs cited with takeaways in the research sweep; independent
re-fetch of PROV-O/FAIR, OSF/prereg, ablation, and OSC sources is a
retained verification gap.
