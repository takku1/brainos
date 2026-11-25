# 01 — Research Proposal: BrainOS as Programmable Cognitive Execution

## 1.1 Abstract

BrainOS is a programmable execution environment for heterogeneous AI
systems: independently developed models, mechanisms, memories, and tools
operating as components of one persistent, adaptive system through a
shared instruction contract, executed by a runtime and governed by an
epistemic kernel. It is not one giant network, not governance alone, and
not a substrate that must beat every model.

BrainOS separates three concerns usually blurred inside single models:
computation (what components calculate), coordination (how computations
interact), and authority (what is justified by evidence). Hypothesis: a
common cognitive execution contract supports persistent, revisable,
resource-bounded cooperation among heterogeneous learned components.
Open questions: whether that contract yields useful integration,
adaptation, recoverability, and operational advantage over competent
conventional alternatives.

Robotics (perception–prediction–actuation loops, including mobile
manipulation) is the first end-to-end test track. The same contracts must
also admit non-embodied instantiations: document QA over an LLM plus
retrieval, vision classification pipelines, scheduling assistants with
tool calls, and analytic solvers behind adapters.

## 1.2 Hypotheses (four, independently testable)

H1 Computational interoperability: heterogeneous mechanisms operate
through one common execution contract (Doc 09) — composition without
rewriting internals.

H2 Adaptive organization: changing relationships and bindings
(routing, substitution, reorganization under the Transactor) improve
collective performance under bounded resources.

H3 Computational morphogenesis: a system develops and consolidates new
computational abilities — new providers, fused procedures, retired
capacity — under explicit resource budgets (Doc 11).

H4 Recoverable intelligence: a system preserves useful knowledge while
correcting, replacing, or regenerating its components (Doc 05).

No experiment must prove all four at once. Each hypothesis names its
own track, baselines, and falsification gate in Doc 07. Organizational outcome
modeling (Doc 19) is a concrete H2/H3 strategy; its repair transfer also probes
H4. It introduces no fifth hypothesis, mandatory model, or new kernel. The original
integration inequality (collective > independent components under
matched data, compute, and information access) is the H1+H2 joint
prediction, not a standalone claim.

## 1.3 Non-hypotheses

- Not a claim that any multi-model ensemble is intelligent.
- Not a claim that symbolic rules alone model the environment.
- Not a claim that shared training automatically yields cooperation.
- Not a claim that certified evidence is true (certification attests
  procedure, never truth).

## 1.4 Research questions

1. Can independently learned representations be translated into a common
   informational space without destroying component competence?
2. Can capability-level symbolic reasoning coordinate components without
   becoming a latency or expressiveness bottleneck?
3. Does shared experience improve components beyond matched independent
   training (transfer, not pooling)?
4. Does the architecture support adding, replacing, or removing components
   while preserving established capabilities?
5. Does a common execution contract produce integration and recoverability
   advantages over competent conventional alternatives?
6. Can retained intervention experience predict which organizational changes
   will acquire, preserve or repair capabilities in new contexts, beyond
   equally informed symbolic planning, memoization and case reuse (Doc 19)?

## 1.5 Claimed contributions

1. Formal model of providers, adapters, readout state, capability graphs.
2. Supervisory-controller extension: tensor-schema contracts, state
   ownership, timestamps, representation adapters.
3. Candidate readout mechanism: attention fusion plus recurrent integration
   with provenance and uncertainty (one option among direct links and
   routed meshes).
4. Joint learning objective separating competence, alignment, prediction,
   task, and retention terms.
5. Experimental protocol centered on incremental learning benefit and
   directional transfer measures.
6. Cognitive instruction contract: typed operations with preconditions,
   version semantics, and cost accounting.

## 1.6 Scope and boundaries

In scope: interface contracts, integration, adapter learning, predictive
objectives, async coordination, compositional evaluation,
instruction-contract conformance, and bounded experience-guided organizational
prediction/planning through ordinary providers. Out of scope: specific network
backbones, hardware implementation, consciousness or biological-plausibility
claims, LLM-based low-level control as the default actuation path,
merging arbitrary networks into one parameter space, guaranteed
correctness of predictions, exact unlearning with discarded history,
and unrestricted autonomous topology discovery (self-rewiring without
validation). Distinction: Doc 11 developmental graph changes ARE in
scope — gated, validated, Transactor-committed birth/fusion/retirement
(mandatory transaction checks always; hypothesis-specific L3 gates per
preregistration — Doc 07 registry) — while autonomous discovery
(unvalidated self-rewiring) is out of scope. Gated reorganization vs
autonomous discovery.

## 1.7 Success criteria (per hypothesis and track — Doc 07 L3)

- H1 (Track R + one non-embodied track): heterogeneous providers
  execute, coordinate, and persist through one contract; composition
  without rewriting internals.
- H2 (Tracks R/G/E): changing bindings/topology improves performance
  under fixed budgets vs matched static-routing arms; experience-guided
  organizational planning additionally faces equal-horizon symbolic search
  and case-reuse controls (07 section 7.12).
- H3 (Tracks E/G + Experiment 001): development consolidates new
  abilities with retention floors held, justified by any of Doc 20
  §20.4's three values (efficiency with N*, competence, or expansion
  — expansion never owes savings); assimilation judged per method,
  never distillation-only.
- H4 (all tracks): repair transactions preserve independently
  supported knowledge while correcting the fault, cheaper than
  clean-history retraining where claimed — or a reported fail.
- All claims survive matched ablations (Doc 07 L3); parity and
  failure are findings. No criterion mentions robotics as a
  requirement: Track R is first evidence, not the bar.

## 1.8 What is distinctive (claimed direction, not established novelty)

Individual ingredients have established counterparts
(component software, VMs/runtimes, evolutionary computation, MoE,
distillation, dynamic graphs, AutoML, meta-learning, databases,
scheduling). The proposed distinction: integrating them so that
computational organization itself becomes a persistent, governable,
adaptable object. An operating system manages resources for programs
whose organization is externally defined; BrainOS manages resources
for intelligent organizations whose structure changes through
experience (Docs 11, 19, 24, 25). Whether that combination is
scientifically novel or operationally superior requires proper
literature review and experimental comparison — asserted here as
research direction, not as a novelty result.

Central design principle: the unit of development is the
computational ability. Its implementation is replaceable, its
relationships are adaptable, its competence is measurable, and its
continued existence must be justified by its contribution to the
organization.
