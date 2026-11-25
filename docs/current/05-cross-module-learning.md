# 05 — Cross-Provider Learning and Recoverable Plasticity

Status: research — hypotheses and proposed mechanisms; nothing this document owns is implemented or validated.

## 5.1 Question

Can interacting providers acquire new skills, consolidate them, and
selectively repair learning from invalid evidence at lower total cost
than clean-history retraining, without losing independently supported
skills?

## 5.2 Three coupled structures

1. Evidence graph: observations, claims, procedures, challenges,
   contexts, time, validity intervals. History preserved.
2. Learning graph: immutable update units, inputs, teacher versions,
   parents, optimizer recipe, consolidation state.
3. Execution manifest: one compatible set of versions, adapters,
   permissions, evidence epoch per operation.

Dependencies recorded at training time; later explanations are not
substitutes. Shared-version changes affect every bound instance.

## 5.3 Stable core plus bounded plastic units

One common instantiation (neural): begin with frozen nonlinear
backbones and a bounded bank of small residual adapters/heads; fixed
gates first, a learned gate as another unit with its own provenance.
Other substrates begin with their own stable cores — verified solvers,
frozen prompts, indexed stores — plus bounded plastic units of their
kind. Ported result (R2b): selective rebuild matches full retraining
at 0.21–0.26x cost on corrected error; adaptation forgets the ancestor
capability (retention FAIL) — the open gap.

## 5.4 Repair transaction

Challenge → quarantine → rebuild → validate → commit as one coordinated
unit: staged candidates, epoch-pinned validation, single-swap commit
rejecting stale/quarantined units, atomic checkpoints with fallback.
Concurrent challenges serialize on the manifest; losers revalidate,
never override. A checkpoint that cannot name its parents is approximate
repair and must say so.

## 5.5 Joint objective

Separate competence, alignment, prediction, task, and retention terms so
specialization is not collapsed into copies of z without a competence
check. Report retention and correction separately; parity and failure are
findings.

## 5.6 Beyond neural parameters

Learning here means any competence change through experience: gradient
updates, evolutionary search, prompt/procedure revision, retrieval-index
rebuilds, symbolic rule edits, composition of procedures. Repair means
any quarantined rebuild through the transaction (staged candidates,
epoch-pinned validation, atomic COMMIT), not only weight rewinding.
Historical neural results are summarized in README; they do not define
the general repair pattern. A deterministic
calculator learns nothing through experience, but still needs the
repair path for software defects, configuration failures, and
dependency changes — repair is broader than relearning. An LLM-based
provider may revise prompts and retrieval while its weights stay
frozen.

## 5.7 Repair of adaptation knowledge

Organizational learning includes retained transformation cases, applicability
hypotheses and outcome predictors (Doc 19), even when task providers are frozen.
Their data dependencies enter the same evidence/learning graph and their versions
use ordinary quarantine, rebuild, validation and COMMIT. Challenges propagate
through affected cases, guards and model versions under Doc 29; an old case can
remain a historical observation while losing authority as a current prediction.

Measure correction of faulty forecasts separately from retention of supported
cases and adaptation competence. Rebuild or narrow only supported scope; removing
a failed model leaves eligible symbolic planning/case retrieval as declared
fallbacks rather than removing task capabilities automatically. A model's
preferred repair never waives independent evidence or publication checks.
