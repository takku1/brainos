"""Bounded typed composition search, separate from Core authority and execution.

Development examples guide search; the capability contract's own admission
cases are used only for validation after the generator nominates a graph.
With `cumulative=True` the catalogue includes previously acquired composites,
which are lowered into primitive execution (graphs.py), so earlier acquisitions
can serve as building blocks for later ones.

This module never issues funding: budgets come from an operator.
"""
from collections import deque
from dataclasses import asdict, dataclass
import time
from types import SimpleNamespace

from .contracts import Refused, digest, uid
from .devcontext import development_context
from . import providers

MAX_DEADLINE_SECONDS = 300


@dataclass(frozen=True)
class CapabilityDemand:
    name: str
    input: str
    output: str
    development_examples: tuple
    context: str = "default"
    max_depth: int = 2
    max_candidates: int = 32
    deadline_seconds: float = 30.0


class CompositionSearch:
    def __init__(self, runtime):
        # Keep only the restricted capability surface; never the Runtime itself.
        self.ctx = runtime if isinstance(runtime, SimpleNamespace) else development_context(runtime)

    # --- provenance -------------------------------------------------------
    def _open_run(self, demand, principal, mode, cumulative, catalogue, admission_cases, budget, validation_budget):
        ctx = self.ctx
        state = ctx.manifest()
        key = uid()
        definition = dict(asdict(demand), development_examples=[list(e) for e in demand.development_examples])
        record = dict(id=key, demand=demand.name, demand_definition=definition, demand_digest=digest(definition),
            principal=principal, mode=mode, cumulative=cumulative, context=demand.context,
            pinned=dict(revision=state["revision"], epoch=state["epoch"], evidence_revision=state["evidence_revision"]),
            catalogue=[s["id"] for s in catalogue],
            evaluation=dict(development_examples_digest=digest(definition["development_examples"]),
                            admission_cases_digest=digest(admission_cases) if admission_cases is not None else None),
            budgets=dict(search=budget, validation=validation_budget),
            started_wall=time.time(), status="RUNNING", consequences=[])
        ctx.write("construction-run", key, record, "construction-run-started", run=key, demand=demand.name)
        return record

    def _close_run(self, run, status, **totals):
        run.update(status=status, **totals)
        self.ctx.write("construction-run", run["id"], run, "construction-run-finished", run=run["id"], status=status)

    def _record(self, run, path, status, **details):
        ctx = self.ctx
        key = uid()
        lowered = set()
        for ref in path:
            spec = ctx.get("provider", ref)
            lowered.update(spec.get("transitive_dependencies", [ref]))
        record = dict(id=key, run=run["id"] if run else None, demand=run["demand"] if run else None,
                      context=run["context"] if run else None, path=list(path),
                      dependencies=dict(direct=list(path), transitive=sorted(lowered)),
                      pinned=run["pinned"] if run else None, status=status, **details)
        ctx.write("construction", key, record, "construction-trial", trial=key, demand=record["demand"], status=status)
        return key

    @staticmethod
    def definition(demand, path):
        return dict(input=demand.input, output=demand.output,
            nodes=[dict(id=f"n{i}", provider=provider, input="$input" if i == 0 else f"n{i-1}")
                   for i, provider in enumerate(path)], output_node=f"n{len(path)-1}")

    def catalogue(self, *, cumulative, exclude_capability=None):
        ctx = self.ctx
        specs = {}
        for key in ctx.active_providers():
            try:
                spec = ctx.resolve(key)
            except Refused:
                continue  # blocked by an impact: not available as a building block
            if spec["kind"] == "graph" and (not cumulative or spec["capability"] == exclude_capability):
                continue
            specs[spec["id"]] = spec
        return sorted(specs.values(), key=lambda s: (s["kind"], s["implementation"], s["id"]))

    # --- search -----------------------------------------------------------
    def discover(self, demand, principal, budget, *, mode="typed", exclude_paths=(), cumulative=False,
                 _run=None, _deadline=None):
        own = _run is None
        run_box = {}
        try:
            yield from self._discover(demand, principal, budget, mode, exclude_paths, cumulative,
                                      _run, _deadline, run_box)
        finally:
            if own and "run" in run_box:
                self._close_run(run_box["run"], "SEARCH_ONLY")

    def _discover(self, demand, principal, budget, mode, exclude_paths, cumulative, _run, _deadline, run_box):
        if (not isinstance(demand, CapabilityDemand) or not demand.name
                or not 1 <= demand.max_depth <= 4 or not 1 <= demand.max_candidates <= 256
                or not 0 < demand.deadline_seconds <= MAX_DEADLINE_SECONDS
                or mode not in ("typed", "memoized") or not demand.development_examples):
            raise Refused("invalid bounded capability demand or search policy")
        ctx = self.ctx
        deadline = _deadline or time.monotonic() + demand.deadline_seconds
        catalogue = self.catalogue(cumulative=cumulative, exclude_capability=_run and _run.get("capability"))
        run = _run or self._open_run(demand, principal, mode, cumulative, catalogue, None, budget, None)
        run_box["run"] = run
        queue = deque([((), demand.input)])
        cache = {}
        expanded = attempts = 0
        started = time.monotonic()

        def out_of_time():
            return time.monotonic() >= deadline

        while queue and expanded < demand.max_candidates:
            if out_of_time():
                self._record(run, (), "NON_ATTAINMENT", reason="construction deadline exceeded", expanded=expanded)
                run["search"] = dict(expanded=expanded, attempts=attempts, seconds=time.monotonic() - started)
                return
            path, schema = queue.popleft()
            try:
                ctx.charge(budget, principal, {"attempts": 1}, "typed-search-expansion")
                attempts += 1
            except Refused as exc:
                self._record(run, path, "NON_ATTAINMENT", reason=str(exc), expanded=expanded)
                run["search"] = dict(expanded=expanded, attempts=attempts, seconds=time.monotonic() - started)
                return
            expanded += 1
            trivial = len(path) == 1 and ctx.get("provider", path[0])["kind"] == "graph"
            if path and schema == demand.output and path not in exclude_paths and not trivial:
                trial_attempts, trial_started = 0, time.monotonic()
                try:
                    for value, expected in demand.development_examples:
                        providers.check(demand.input, value)
                        result = value
                        for ref in path:
                            if out_of_time():
                                raise Refused("construction deadline exceeded")
                            spec = ctx.resolve(ref)
                            key = digest([spec["id"], result, demand.context])
                            if mode == "memoized" and key in cache:
                                result = cache[key]
                            else:
                                ctx.charge(budget, principal, spec["cost"], "development-example")
                                trial_attempts += spec["cost"]["attempts"]
                                result = ctx.compute(spec, result, max(0.05, min(5, deadline - time.monotonic())))
                                cache[key] = result
                        if result != expected:
                            raise Refused("development example mismatch")
                    attempts += trial_attempts
                    self._record(run, path, "NOMINATED", expanded=expanded, mode=mode,
                                 costs=dict(attempts=trial_attempts, seconds=time.monotonic() - trial_started))
                    run["search"] = dict(expanded=expanded, attempts=attempts, seconds=time.monotonic() - started)
                    yield path
                except Refused as exc:
                    attempts += trial_attempts
                    status = "NON_ATTAINMENT" if "deadline" in str(exc) else "REJECTED_DEVELOPMENT"
                    self._record(run, path, status, reason=str(exc), expanded=expanded,
                                 costs=dict(attempts=trial_attempts, seconds=time.monotonic() - trial_started))
                    if status == "NON_ATTAINMENT":
                        run["search"] = dict(expanded=expanded, attempts=attempts, seconds=time.monotonic() - started)
                        return
            if len(path) < demand.max_depth:
                for spec in catalogue:
                    if spec["input"] == schema:
                        queue.append(((*path, spec["id"]), spec["output"]))
        run["search"] = dict(expanded=expanded, attempts=attempts, seconds=time.monotonic() - started)
        self._record(run, (), "SEARCH_STOPPED", expanded=expanded,
                     reason="frontier exhausted" if not queue else "candidate bound")

    def acquire(self, demand, principal, budget, admission_cases, *, validation_budget,
                mode="typed", exclude_paths=(), cumulative=False, role=None):
        """Discover, validate as a member of the demanded capability, and optionally bind a role.

        The role defaults to the demand name and is bound only if it is free;
        further providers of the same capability join the population instead.
        """
        ctx = self.ctx
        capability = ctx.define_capability(demand.name, demand.input, demand.output, admission_cases)
        deadline = time.monotonic() + demand.deadline_seconds
        catalogue = self.catalogue(cumulative=cumulative, exclude_capability=capability)
        run = self._open_run(demand, principal, mode, cumulative, catalogue, admission_cases, budget, validation_budget)
        run["capability"] = capability
        role = role or demand.name
        val_before = ctx.spent(validation_budget, principal)["attempts"]
        for path in self.discover(demand, principal, budget, mode=mode, exclude_paths=exclude_paths,
                                  cumulative=cumulative, _run=run, _deadline=deadline):
            if time.monotonic() >= deadline:
                self._record(run, path, "NON_ATTAINMENT", reason="construction deadline exceeded before admission")
                break
            try:
                provider = ctx.register_composite(self.definition(demand, path), capability)
                member = ctx.admit(capability, provider, budget=validation_budget, principal=principal)
                bound = None
                if role not in ctx.manifest()["bindings"]:
                    bound = ctx.bind_role(role, provider, admission_cases, validation_budget, principal)
                spent = ctx.spent(validation_budget, principal)["attempts"] - val_before
                trial = self._record(run, path, "ACQUIRED", provider=provider, mode=mode, member=member,
                                     bound_role=bound, evaluation=dict(validation_attempts=spent))
                run["consequences"].append(dict(membership=member, provider=provider, bound_role=bound))
                self._close_run(run, "ACQUIRED", validation_attempts=spent)
                return dict(status="ACQUIRED", path=list(path), trial=trial, run=run["id"], provider=provider,
                            capability=capability, member=member, role=bound)
            except Refused as exc:
                self._record(run, path, "REJECTED_ADMISSION", reason=str(exc), mode=mode)
        spent = ctx.spent(validation_budget, principal)["attempts"] - val_before
        self._close_run(run, "NON_ATTAINMENT", validation_attempts=spent)
        return dict(status="NON_ATTAINMENT", demand=demand.name, capability=capability, run=run["id"])
