# 13 - Glossary

Definitions below identify the owning contracts; examples do not add requirements.

| Term | Definition / owner |
|---|---|
| Provider | Component implementing capability contracts; internal learning optional (02/17) |
| Capability / contract / implementation | Abstract ability / conditions and floors / executable provider (17/26) |
| Slot | Execution role/interface with contract, timing and accepted versions (02) |
| Checkpoint | Versioned durable artifact; not automatically restored runtime state (21/32) |
| Adapter | Versioned semantic transformation between published outputs (02 section 2.11) |
| Readout | Optional integration/query surface; direct/routed paths remain valid (04) |
| Manifest | Immutable compatible graph/bindings/artifact/policy/evidence revision set (21) |
| Snapshot | Immutable compatible published state with provenance, sequence and clock domain (21/06) |
| Epoch | Bounded authority generation; an episode boundary is one possible cut (09/32) |
| Supervisor | Computes capability eligibility and permission metadata (03/32) |
| Scheduler | Selects ready work and proposes priorities; trusted enforcement applies caps/stops (32) |
| Planner | Proposes task graphs, not permissions (32 section 32.11) |
| Task | Owned goal/criteria with dependencies, budget, lifecycle and outcomes (21/32) |
| Transactor | Atomic publisher of compatible organizational state (24/32) |
| Permit | Trusted scoped operation authority; cannot be self-asserted or inherited (21/32) |
| Drain | Completion of already-running work toward a safe stop; no new effects (32) |
| Tier / validity | Observed, Believed, Certified / Active, Questionable, Revoked; independent fields (03) |
| VERIFY / RESTORE / AUTHORIZE | Record verdict / restore same-target eligibility / issue operation permission (09/32) |
| COMMIT / CONSOLIDATE | Publish active manifest / make artifact durable without activation (09/21) |
| RETIRE / reconstruction | Remove active instance/version / build and validate a successor; no time reversal (24) |
| Retention / correction | Preserved competence / corrected fault, measured separately (05/07) |
| Exact equivalence | Proof-backed mutual refinement; transitive (17 section 17.6) |
| Estimated substitution | Contextual uncertain provider coverage; not transitive (17/26) |
| Degeneracy | Structurally different providers with overlapping context-dependent function (17 section 17.3) |
| Failure independence | Separately measured joint failure, not implied by diversity or duplication (17/26) |
| Composition / assimilation | Build a nominated composite with parents retained / validated replacement covering required parent contexts (24) |
| Construction specification | Reusable architecture/interface/adaptation/variation rules (11/27) |
| Impact closure | Potentially affected set; property-specific actions distinguish evidence invalidation from contention (29) |
| Grounding | Empirical, formal, preference, or policy termination; permission does not establish truth (30) |
| Developmental value | Efficiency, competence, or expansion; only efficiency claims require break-even savings (20) |
| Transition kind | D, S, N, or X, declared per mechanism/stage (24/32) |
| Unknown effect | Dispatch without confirmed outcome; reconcile before unsafe retry (32) |
| Tracks R/G/S/E | Robotics / games / science / bounded development; domain instantiations (07) |

Reserved naming: Snapshot means atomic publication; game tick frames/rollback
slots retain their distinct names. Authority means kernel-granted permission;
use sim ownership for game servers. Readout projection/typed fact store,
planning facts, fabric processor, and NPC principal are the computational
terms used in Doc 14 mappings. Older developmental-unit terminology in source
rationale does not prescribe the substrate. No track claims indefinite novelty;
bounded resources alone are not a theorem that indefinite novelty is impossible.
Neuroscience/evolution source interpretations belong in Doc 16.

## Organizational learning terms

| Term | Definition / owner |
|---|---|
| Organizational world model | Scoped predictor of transformation outcomes over permitted organization projections/history (19) |
| TransformationRecord | Observed intervention, conditions, pretrial prediction, outcome/cost and disposition (21 section 21.7) |
| Applicability guard | Versioned condition for a case/model prediction; generalization is a new hypothesis, not a proof (19) |
| Organizational plan | Bounded conditional sequence of transformations; execution remains stepwise and independently admitted (19/22) |
| Enabling step | Named prerequisite for an external goal or bounded uncertainty reduction, not automatic terminal reward (18/20) |
| Prediction / intervention effect | Forecast / causally identified measured consequence under stated assignment assumptions (23/28) |
| Developmental compilation | Learn scoped typed abstractions with explicit lowerings to existing providers (27 section 27.8) |
| Library entry / cached result | Executable parameterized abstraction / saved output for supported exact input conditions (21/27) |
| Organizational repertoire | Budgeted organization artifacts indexed by measured behavior; retrieval nominates, not authorizes (25 section 25.12) |
| Collective inference | Optional coupled hypothesis revision with declared update, support and stopping semantics (10) |
