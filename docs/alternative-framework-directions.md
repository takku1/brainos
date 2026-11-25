# Framework Direction - Decision and Integration Map

The research comparison is integrated into the existing framework under
[docs/current/](current/README.md). That directory contains one consolidated
BrainOS framework, not a set of competing frameworks. This file records the
selection and points to the authoritative sections.

**Selected next construction mechanism: developmental compilation.** Learn typed,
parameterized abstractions with scoped contracts and explicit lowerings to
existing providers. It extends the first flat-search recipe, uses the existing
execution contract, and has a direct construction-cost/coverage experiment.
This is a design priority, not a measured universal winner.

| Role within BrainOS | Canonical owner |
|---|---|
| Overall decision and reasoning | [19 section 19.10](current/19-organizational-calculus.md) |
| Abstraction learning and lowering | [27 section 27.8](current/27-candidate-construction.md) |
| Change/probe selection and organizational predictions | [19](current/19-organizational-calculus.md), [22](current/22-capability-discovery.md) |
| Bounded alternative-organization repertoire | [25 section 25.12](current/25-ecology-dynamics.md) |
| Optional collective inference | [10 section 10.1](current/10-mechanism-network.md), [04 section 4.5](current/04-shared-representation.md) |
| Library/repertoire records and dependency impacts | [21 section 21.8](current/21-reference-implementation.md), [29 section 29.6](current/29-dependency-interference.md) |
| Isolated comparisons and combined-factor test | [07 sections 7.13-7.16](current/07-experimental-validation.md) |
| Build sequence | [08](current/08-development-roadmap.md) |

Sequence: Core vertical slice -> competent typed search/memoization -> learned
abstractions versus handwritten macros -> organizational prediction with fixed
library and equal history/horizon -> controlled combination. Inference and
archive policies receive separate task-specific comparisons. A macro's expanded
work, model training, inference iterations, and archive reuse costs all count.
No direction adds a trusted opcode, mandatory shared workspace, or adoption layer.
Research sources and comparison rationale are retained in their canonical owners.
