"""Bounded typed composition search, separate from Core authority and execution.

Development examples guide search. Independent admission examples are consumed
only by the acquisition orchestration, after the generator nominates a graph.
"""
from collections import deque
from dataclasses import dataclass
from .contracts import Refused, digest, uid
from . import providers


@dataclass(frozen=True)
class CapabilityDemand:
    name: str
    input: str
    output: str
    development_examples: tuple
    context: str = "default"
    max_depth: int = 2
    max_candidates: int = 32


class CompositionSearch:
    def __init__(self, runtime):
        self.runtime = runtime

    def _record(self, demand, path, status, **details):
        key = uid()
        record = dict(id=key, demand=demand.name, context=demand.context,
                      path=list(path), status=status, **details)
        with self.runtime.store.transaction():
            self.runtime.store.put("construction", key, record)
            self.runtime.store.event("construction-trial", trial=key, demand=demand.name, status=status)
        return key

    @staticmethod
    def definition(demand, path):
        return dict(input=demand.input, output=demand.output,
            nodes=[dict(id=f"n{i}", provider=provider, input="$input" if i == 0 else f"n{i-1}")
                   for i, provider in enumerate(path)], output_node=f"n{len(path)-1}")

    def discover(self, demand, principal, budget, *, mode="typed", exclude_paths=()):
        if (not isinstance(demand, CapabilityDemand) or not demand.name
                or not 1 <= demand.max_depth <= 4 or not 1 <= demand.max_candidates <= 128
                or mode not in ("typed", "memoized") or not demand.development_examples):
            raise Refused("invalid bounded capability demand or search policy")
        runtime = self.runtime
        active = set(runtime.manifest()["bindings"].values())
        catalogue = [runtime.registry.resolve(key) for key in active]
        catalogue = sorted((s for s in catalogue if s["kind"] == "primitive"),
                           key=lambda s: (s["implementation"], s["id"]))
        queue = deque([((), demand.input)])
        cache = {}
        expanded = 0
        while queue and expanded < demand.max_candidates:
            path, schema = queue.popleft()
            try:
                runtime.resources.charge(budget, principal, {"attempts": 1}, "typed-search-expansion")
            except Refused as exc:
                self._record(demand, path, "NON_ATTAINMENT", reason=str(exc), expanded=expanded)
                return
            expanded += 1
            if path and schema == demand.output and path not in exclude_paths:
                try:
                    for value, expected in demand.development_examples:
                        providers.check(demand.input, value)
                        result = value
                        for ref in path:
                            spec = runtime.registry.resolve(ref)
                            key = digest([spec["id"], result, demand.context])
                            if mode == "memoized" and key in cache:
                                result = cache[key]
                            else:
                                runtime.resources.charge(budget, principal, spec["cost"], "development-example")
                                result = runtime.runner.compute(spec, result, 5)
                                cache[key] = result
                        if result != expected:
                            raise Refused("development example mismatch")
                    self._record(demand, path, "NOMINATED", expanded=expanded, mode=mode)
                    yield path
                except Refused as exc:
                    self._record(demand, path, "REJECTED_DEVELOPMENT", reason=str(exc), expanded=expanded)
            if len(path) < demand.max_depth:
                for spec in catalogue:
                    if spec["input"] == schema:
                        queue.append(((*path, spec["id"]), spec["output"]))
        self._record(demand, (), "SEARCH_STOPPED", expanded=expanded,
                     reason="frontier exhausted" if not queue else "candidate bound")

    def acquire(self, demand, principal, budget, admission_cases, *, validation_budget,
                mode="typed", exclude_paths=()):
        for path in self.discover(demand, principal, budget, mode=mode, exclude_paths=exclude_paths):
            try:
                proposal = self.runtime.fabric.stage(self.definition(demand, path), demand.name)
                self.runtime.transactor.validate(proposal["candidate"], {demand.name: admission_cases},
                                                 budget=validation_budget, principal=principal)
                self.runtime.transactor.commit(proposal["candidate"])
                trial = self._record(demand, path, "ACQUIRED", provider=proposal["provider"], mode=mode)
                return dict(status="ACQUIRED", path=list(path), trial=trial, **proposal)
            except Refused as exc:
                self._record(demand, path, "REJECTED_ADMISSION", reason=str(exc), mode=mode)
        return dict(status="NON_ATTAINMENT", demand=demand.name)
