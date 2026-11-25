# BrainOS

A specification for persistent, heterogeneous AI systems whose computational
organization can adapt under evidence, authority, resource, and recovery constraints.

Start with the [architecture guide](docs/current/README.md),
[current status](docs/STATUS.md), and
[implementation roadmap](docs/current/08-development-roadmap.md).

The canonical specification is the numbered Markdown set under `docs/current/`.
Reference validators and partial behavioral models are under `tools/`.
No production runtime is implemented yet. The DOCX is a frozen historical artifact.

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
