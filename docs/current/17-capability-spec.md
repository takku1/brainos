# 17 — Capability Specification

Capabilities are the unit of organization. Providers implement them;
the supervisor reasons over them; competition compares them.

## 17.1 What a capability is

Three distinct layers (Doc 26 §26.3): an abstract capability (what can
be done), a functional contract (conditions and requirements), and a
provider implementation (what does it). A capability is not a contract
and a contract is not a provider. The contract below is the middle
layer; everything measurable in §17.2 is measured against a stated
contract, never against a bare capability name:

- Domain: input/output schemas with tolerances (dtype, shape,
  units, acceptable error).
- Contexts: the conditions under which the contract holds.
- Quality: accuracy/precision bounds per context.
- Latency and resources: time, memory, energy budgets.
- Authority tier: risk tier of operations performed under this
  capability. Capabilities never grant authority — only the kernel
  grants authority (AUTHORIZE) within the tier a capability declares.
- Failure behavior: declared degradation (refuse, degrade, escalate).

Two providers satisfy the same capability when both meet the contract
in the same contexts — regardless of internals. A neural model that
approximates square roots and a deterministic square-root algorithm
satisfy one capability within stated tolerances. An LLM that solves
algebra and a symbolic algebra engine overlap on some contexts and
diverge on others; overlap is measured, never assumed from marketing.

## 17.2 Directional substitutability (measurement spec)

For providers i, j and a context distribution P(c) over deployment
contexts:

```text
s(i→j,c) = Σ_k w_k · 1[requirement k of j's contract in c is met by i]
           subject to hard floors: quality, latency, state, authority,
           and resource minima below which s = 0 regardless of the average.
s(i→j)   = E_{c~P(c)}[s(i→j,c)] with reported variance, never a bare mean.
```

s measures requirement satisfaction (s_requirements): the fraction
of the contract's weighted requirements met. It is not the
probability of successful execution (p_success): a provider can
satisfy 90% of requirements yet succeed in far fewer — or far
more — execution contexts, because execution adds state, history,
load, interference, and environment dynamics the contract does not
cover. Report both where both are measurable; never present s as a
success probability. Hard floors are uncertainty-aware: a floor
verdict near the threshold must account for measurement
uncertainty (CIs overlapping the floor = floor status
indeterminate, not passed) — a point estimate above a floor by
less than its error bar authorizes nothing.

Weights w_k come from the capability contract's requirement priorities,
not from the substitute's strengths, normalized to Σ_k w_k = 1 per
context; the normalization and the priority source are recorded with
every reported s. Verification comes in three strengths, never
conflated: proof (mathematical guarantee under stated assumptions),
exhaustive verification (all inputs in a bounded domain checked),
and property-based testing (sampled inputs against stated properties
— a sampling method, not a guarantee). A proof-checked or
exhaustively tested substitute reports s by verification verdict
(with the checked property and domain stated); property-based
results report like statistical results, with the property, sampler,
and sample size. Statistical reporting resumes wherever behavior is
sampled rather than proven. In general s(i→j,c) ≠ s(j→i,c).
Downstream effects are measured, not assumed: replacing j with i
re-runs j's downstream consumers in the evaluation harness and reports
their deltas alongside s. Uncertainty is reported per the capability's evaluation family
(Doc 23): statistical families use ≥5 seeds + CIs as a provisional
minimum — five seeds is a floor for reporting, not evidence of
statistical adequacy (power analysis where stakes warrant);
deterministic and formal families use verification verdicts;
preference-based families use rater agreement; comparative families
use paired tests. A substitution claim without its family's
uncertainty is not a claim.
Measurement protocol (L3):

1. Fix context distribution P(c): task mix, input schemas, quality
   bars, latency budgets, authority tiers, resource caps, hard floors.
2. Run j alone (baseline), then i in j's role with identical
   inputs and budgets. No retuning between arms except declared
   provider-local configuration.
3. Report s(i→j,c) per context plus s(i→j), binding constraints
   (which floor failed first where s < 1), and downstream deltas.
4. Cost, speed, and risk ride alongside on the Pareto vector — with
   the Pareto rule stated correctly: i dominates j only if i is at
   least as good on every dimension and better on at least one. A
   90%-coverage substitute at 10x cost is NOT dominated-out by a
   cheaper 30% alternative, nor does it dominate: the two are
   Pareto-incomparable, and the niche (rare critical coverage vs
   routine cost) decides. Redundancy (mutual high substitution) and
   complementarity (asymmetric substitution across contexts) are
   reported as distinct findings; failure independence is a third,
   separately measured property (Doc 26) — never bundled into either.
   The ecology distinguishes all three; a single score cannot.

Illustrative asymmetric matrix (not measured BrainOS results) — rows
replace columns: A→B 95%, B→A 35%; A→C 80%, C→A 60%; B→C 20%, C→B 75%.
A's dominance in coverage never by itself retires B or C: cost, speed,
rare-critical floors, and failure independence decide per niche.
Competition is evaluated across capability, context, quality,
resources, and risk — never a single scalar.

## 17.3 Degeneracy, operationalized

Degeneracy (Edelman & Gally 2001) = structurally different providers,
overlapping function, context-dependent. Operational test: same
capability contract, structural difference evidenced (not asserted
from different names), and substitution profiles that differ across
contexts. Failure-domain independence is tested separately and
recorded alongside — never as part of the degeneracy verdict itself.
Agreement between providers is not independent evidence; it is one
correlated observation until failure independence is measured.

## 17.4 Capability registry

Separate identities for separate layers: capability records
(abstract ability + abstraction relations per Doc 26), contract
records (conditions, requirements, floors, evaluation family),
provider records (implementation + pinned version), relationship
records (specialization/equivalence/dependency/composition/partial
coverage with evidence refs). A registry entry joins them: contract
(per §17.1), eligible providers with pinned versions, measured
substitution matrix per context, Pareto frontier, protected-floor
flags for rare critical niches. Scheduler optimizes only over
eligible providers. Promotion, competition, and assimilation all
read this registry; none bypass it.

## 17.5 Stateful providers and external effects

Substitution compatibility for stateful providers requires state
migration or declared stateless handover: s is measured from
equivalent starting states, and the handover procedure (state
transfer, warm-up, drain) is part of the contract, not an
implementation detail. Providers with external side effects
substitute only under effect-equivalence: same observable effects,
same ordering guarantees, same failure/atomicity semantics —
verified by effect logs, not assumed from matching outputs.
A pure function is never an admissible substitute for an
effectful provider on the basis of return values alone.

## 17.6 Exact equivalence vs estimated substitutability

Exact contract equivalence (mutual refinement, Doc 26) is a
definitional relation: it holds by proof or exhaustive check and is
transitive. Empirically estimated mutual substitutability
(high s both directions) is a measurement: it holds within error
bars, in tested contexts, and is NOT transitive — do not collapse
estimated mutual-substitution cliques into equivalence classes.
Record which relation a claim uses; an estimated relation never
inherits the inference rules of an exact one.
