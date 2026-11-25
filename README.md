# BrainOS

A specification for persistent, heterogeneous AI systems whose computational
organization can adapt under evidence, authority, resource, and recovery constraints.

Start with the [architecture guide](docs/current/README.md),
[current status](docs/STATUS.md), and
[implementation roadmap](docs/current/08-development-roadmap.md).

The canonical specification is the numbered Markdown set under `docs/current/`.
The first executable single-authority profile is under `src/brainos/`.
Reference validators and earlier partial models remain under `tools/`.
This is an initial runtime slice, not full Core conformance. The DOCX is historical.

## Run the first vertical slice

```powershell
py -m pip install -e . --no-build-isolation
py -m brainos --state-dir .brainos/demo
py -m unittest discover -s tests -v
```

The demo runs parsing and summation in bounded catalogue subprocesses, records a
simulated effect, loses its acknowledgment, reopens the durable journal, reconciles
the effect once, rejects old authority, and validates a replacement implementation.
State paths must use a local filesystem with working locks and durable writes.

`runtime.py` composes services; `contracts.py` defines ports and control projections;
`storage.py` owns transactions/ownership; `resources.py`, `evidence.py`,
`authority.py`, and `transactor.py` own their respective policies;
`execution.py` and `gateways.py` own invocation and effect lifecycles;
`runner.py`, `worker.py`, and `effects.py` implement process/endpoint adapters.
See [the implemented profile](docs/current/21-reference-implementation.md#219-first-executable-profile)
for supported behavior, evidence, and limits. No runtime third-party dependencies
or arbitrary-code execution are required.

To run the reference checks, use Python with PyYAML installed:

```powershell
py tools/gate1_checks.py
py tools/gate1_negatives.py
py tools/dep_closure.py
py tools/l1_harness.py
py -m unittest discover -s tools -p test_reference_regressions.py -v
```

These checks cover declarations and selected reference behaviors; they do not
establish production conformance or empirical adaptation benefits.
