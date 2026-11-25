"""W1 instruments: emergence meter, organizational-capability test, net-value ledger.

Kernel-side measurement over kernel records only (Doc 25 section 25.13, Doc 20
section 20.9). The meter never uses provider self-report: it reads memberships,
invocations, impacts, construction runs, assessments and ledgers.

`measure` reads the live store but writes nothing. Its admission re-checks are
pure recomputation through the same provider artifacts and admission cases;
instead of charging, the meter records its own wall time. `net_value` is pure
accounting over declared values and measured costs. `organizational_verdict`
applies its interventions (blocking, coordination removal) to throwaway copies
of the store, never the live one.

Window convention: a window is an explicit list of capability-routed task ids
for one capability. Costs are scoped by the journal span covering the window's
task-created event through its last terminal invocation event. Membership and
blocking are read at measure time: windows are recent by construction, so a
window whose organization has since changed is a different measurement.
"""
import math
import sqlite3
import tempfile
import time
from pathlib import Path
from statistics import median

from .contracts import Refused
from .population import FEATURIZERS
from . import closure, providers
from .registry import ProviderRegistry
from .runner import ExternalDispatcher, make_runner
from .storage import Store

NOV_COSTS = ("compute", "overhead", "construction", "validation", "assessment", "maintenance")

CONSTRUCTION_PURPOSES = frozenset({"typed-search-expansion", "development-example"})
VALIDATION_PURPOSES = frozenset({"assimilation-evaluation"})

TERMINAL_TASKS = frozenset({"SUCCEEDED", "FAILED", "CANCELLED"})
TERMINAL_INVOCATIONS = frozenset({"COMPLETED", "STOPPED", "FAILED"})


def _number(name, value, *, minimum=0):
    if type(value) not in (int, float) or not math.isfinite(value) or value < minimum:
        raise Refused(f"{name} must be a finite number >= {minimum}")
    return value


def _margin(value):
    _number("margin", value)
    if value > 1:
        raise Refused("margin must not exceed 1")
    return value


def _load_tasks(store, capability, task_ids):
    if not task_ids or len(set(task_ids)) != len(task_ids):
        raise Refused("a window needs distinct task ids")
    tasks = []
    for key in task_ids:
        task = store.get("task", key)
        if task.get("capability") != capability:
            raise Refused("window mixes capabilities: every task must be routed to the measured one")
        if task["state"] not in TERMINAL_TASKS:
            raise Refused("window is not closed: every task must be terminal")
        tasks.append(task)
    return tasks


def _window_invocations(store, tasks):
    invocations = {}
    for task in tasks:
        key = task.get("invocation")
        if key is None:
            invocations[task["id"]] = None
            continue
        record = store.get("invocation", key)
        if record.get("task") != task["id"]:
            raise Refused("invocation is bound to a different task")
        if record["state"] not in TERMINAL_INVOCATIONS:
            raise Refused("window is not closed: every invocation must be terminal")
        invocations[task["id"]] = record
    return invocations


def _journal_span(store, tasks, invocations):
    wanted_tasks = {t["id"] for t in tasks}
    wanted_invocations = {r["id"] for r in invocations.values() if r is not None}
    journal = store.journal()
    lo = hi = None
    for event in journal:
        if event["kind"] == "task-created" and event.get("task") in wanted_tasks:
            lo = event["seq"] if lo is None else min(lo, event["seq"])
        refs = wanted_tasks | wanted_invocations
        if any(event.get(field) in refs for field in ("task", "invocation")):
            hi = event["seq"] if hi is None else max(hi, event["seq"])
    if lo is None:
        raise Refused("window tasks left no journal trace")
    return journal, lo, hi if hi is not None and hi >= lo else lo


def _purpose_bucket(purpose):
    if isinstance(purpose, str) and purpose.startswith("maintenance:"):
        return "maintenance"
    if purpose in CONSTRUCTION_PURPOSES:
        return "construction"
    if purpose in VALIDATION_PURPOSES or (isinstance(purpose, str) and purpose.startswith("validation:")):
        return "validation"
    return "execution"


def _span_holdings(store, journal, lo, hi, notes):
    """Spend from holdings reserved inside the span, grouped by cost bucket.

    Holdings persist as tombstones, so (amount - remaining) is the spend so far
    on every charge path, including the silent charge_tx path that emits no
    spent event. Outstanding (unreleased) holdings are flagged, not ignored.
    """
    buckets, outstanding = {}, []
    for event in journal:
        if event["kind"] != "reserved" or not lo <= event["seq"] <= hi:
            continue
        try:
            holding = store.get("holding", event["holding"])
        except Refused:
            notes.append(f"holding {event['holding']} has no record: skipped")
            continue
        bucket = _purpose_bucket(holding.get("purpose"))
        spent = {k: v - holding["remaining"].get(k, 0) for k, v in holding["amount"].items()}
        total = buckets.setdefault(bucket, {})
        for k, v in spent.items():
            total[k] = total.get(k, 0) + v
        if holding["state"] != "RELEASED":
            outstanding.append(holding["id"])
    return buckets, sorted(outstanding)


class _Admission:
    """Pure admission re-checks with per-provider caching (Doc 25 section 25.13).

    A provider passes when it computes every admission case exactly. Blocked
    providers and execution failures fail; the reason is recorded. Evaluations
    performed are counted so verdicts can report the budget they spent.
    """

    def __init__(self, store, timeout, external_adapters=None):
        if not timeout > 0:
            raise Refused("admission timeout must be positive")
        self.registry = ProviderRegistry(store)
        external = (ExternalDispatcher(external_adapters, lambda kind, **fields: None)
                    if external_adapters else None)
        self.runner = make_runner("inprocess", self.registry, lambda kind, **fields: None,
                                  external=external)
        self.timeout = timeout
        self.cache = {}
        self.evaluations = 0
        self.external = external

    def close(self):
        if self.external is not None:
            self.external.close()

    def check(self, provider, cases):
        key = (provider, len(cases))
        if key in self.cache:
            return self.cache[key]
        try:
            spec = self.registry.resolve(provider)
        except Refused as exc:
            return self._store(key, False, f"unresolvable: {exc}")
        collected = []
        for value, expected in cases:
            try:
                self.evaluations += 1
                produced = []
                result = self.runner.compute(spec, value, self.timeout, on_result=produced.append,
                                             on_timing=collected.append)
            except Refused as exc:
                return self._store(key, False, f"case failed: {exc}")
            if result != expected:
                return self._store(key, False, "output differs on an admission case")
        return self._store(key, True, "passes all admission cases")

    def _store(self, key, passed, reason):
        self.cache[key] = (passed, reason)
        return passed, reason


def _contexts(contract, values):
    featurizer = FEATURIZERS.get(contract["input"])
    if featurizer is None:
        return {v: "*" for v in values}, ["no trusted featurizer: single context"]
    return {v: featurizer(values[v]) for v in values}, []


def measure(store, capability, task_ids, *, margin=0.10, latency_floor_ns=None,
            admission_timeout=10, external_adapters=None):
    """Emergence meter for one capability over one window (R-25-06).

    Returns the section 25.13 quantities N/C/Q/R/D/L/V plus reuse and
    complexity, with the window, journal span and derivation notes needed to
    reproduce them. Reads kernel records only; writes nothing.
    `external_adapters` maps implementation names to adapter commands so
    admission re-checks reach external members through the same boundary
    as live execution.
    """
    started = time.perf_counter_ns()
    margin = _margin(margin)
    if latency_floor_ns is not None:
        _number("latency_floor_ns", latency_floor_ns)
    notes = []
    contract = store.get("capability", capability)
    cases = contract["admission_cases"]
    tasks = _load_tasks(store, capability, list(task_ids))
    invocations = _window_invocations(store, tasks)
    journal, lo, hi = _journal_span(store, tasks, invocations)
    registry = ProviderRegistry(store)
    members = [m for m in store.find("member") if m["capability"] == capability]
    by_state = {}
    for row in members:
        by_state.setdefault(row["state"], []).append(row["provider"])
    provider_ids = sorted({row["provider"] for row in members})
    kinds = {}
    for pid in provider_ids:
        try:
            kinds[pid] = store.get("provider", pid).get("kind")
        except Refused:
            notes.append(f"provider {pid} has no record: skipped")
    blocked = sorted(pid for pid in provider_ids if registry.blocking_impact(pid) is not None)
    active = [p for p in by_state.get("ACTIVE", []) if p not in blocked]
    dormant = [p for p in by_state.get("DORMANT", []) if p not in blocked]
    population = {row["id"]: row for row in store.find("provider")}
    admission = _Admission(store, admission_timeout, external_adapters)

    served, coverage = [], []
    for task in tasks:
        record = invocations[task["id"]]
        ok, reason = False, "task was not served"
        if task["state"] == "SUCCEEDED" and record is not None:
            ok, reason = True, "served"
            provider = task["provider"]
            if provider not in active:
                ok, reason = False, "serving provider is not an active unblocked member"
            elif latency_floor_ns is not None and record.get("total_ns", 0) > latency_floor_ns:
                ok, reason = False, "served over the latency floor"
            else:
                passed, why = admission.check(provider, cases)
                if not passed:
                    ok, reason = False, f"serving provider fails admission: {why}"
        served.append(ok)
        coverage.append(dict(task=task["id"], served=ok, reason=reason))
    total = len(tasks)

    by_digest = {}
    for task in tasks:
        record = invocations[task["id"]]
        if task["state"] == "SUCCEEDED" and record is not None and record["state"] == "COMPLETED":
            by_digest.setdefault(task["input_digest"], []).append(
                (task["id"], task["provider"], record.get("compute_ns", 0)))
    regrets, unserved = [], 0
    for task in tasks:
        group = by_digest.get(task["input_digest"], [])
        if task["state"] != "SUCCEEDED" or not group:
            unserved += 1
            continue
        oracle = min(compute for _, _, compute in group)
        compute = next(compute for tid, _, compute in group if tid == task["id"])
        if oracle <= 0:
            regrets.append(0.0 if compute <= 0 else 1.0)
        else:
            regrets.append((compute - oracle) / oracle)

    compute_ns = sum((invocations[t["id"]] or {}).get("compute_ns", 0) for t in tasks
                     if invocations[t["id"]] is not None)
    overhead_ns = sum((invocations[t["id"]] or {}).get("total_ns", 0) -
                      (invocations[t["id"]] or {}).get("compute_ns", 0) for t in tasks
                      if invocations[t["id"]] is not None)
    buckets, outstanding = _span_holdings(store, journal, lo, hi, notes)
    assessment_ns, maintenance_units = 0, 0
    for event in journal:
        if not lo <= event["seq"] <= hi:
            continue
        if event["kind"] == "retention-assessed":
            try:
                assessment_ns += store.get("retention-assessment", event["assessment"])["wall_ns"]
            except Refused:
                notes.append(f"assessment {event['assessment']} has no record: skipped")
        elif event["kind"] == "maintenance-period" and event.get("capability") == capability:
            maintenance_units += event.get("units", 0)

    values = {t["id"]: t["value"] for t in tasks}
    contexts, notes_ctx = _contexts(contract, values)
    notes.extend(notes_ctx)
    samples = {}
    for task in tasks:
        record = invocations[task["id"]]
        if task["state"] == "SUCCEEDED" and record is not None and record["state"] == "COMPLETED":
            samples.setdefault((contexts[task["id"]], task["provider"]), []).append(
                record.get("compute_ns", 0))
    medians = {key: median(vals) for key, vals in samples.items()}
    diversity = {}
    for context in sorted({c for c, _ in medians}):
        present = {p: medians[(context, p)] for p in active if (context, p) in medians}
        if not present:
            diversity[context] = dict(covering=[], unique=False, reason="no sampled active member")
            continue
        best = min(present.values())
        covering = sorted(p for p, cost in present.items() if cost <= best * (1 + margin))
        ordered = sorted(present.values())
        unique = len(ordered) == 1 or ordered[1] > best * (1 + margin)
        pairs, disjoint = 0, 0
        for i, first in enumerate(covering):
            for second in covering[i + 1:]:
                pairs += 1
                try:
                    domains = [set(store.get("provider", p)["footprint"]["failure_domains"])
                               for p in (first, second)]
                except (Refused, KeyError):
                    continue
                if domains[0].isdisjoint(domains[1]):
                    disjoint += 1
        joint, digests = 0, {}
        for task in tasks:
            if contexts[task["id"]] != context:
                continue
            digests.setdefault(task["input_digest"], []).append(task)
        for group in digests.values():
            attempted = {t["provider"] for t in group} & set(covering)
            if len(attempted) >= 2 and all(t["state"] != "SUCCEEDED" for t in group
                                           if t["provider"] in attempted):
                joint += 1
        diversity[context] = dict(covering=covering, unique=unique,
                                  structural_independence=(disjoint / pairs if pairs else None),
                                  observed_joint_failures=joint)

    history = {}
    for inv in store.find("invocation"):
        if inv["state"] != "COMPLETED":
            continue
        try:
            other = store.get("task", inv["task"])
        except Refused:
            notes.append(f"invocation {inv['id']} cites no task: skipped")
            continue
        if other.get("capability") != capability:
            continue
        try:
            context = _contexts(contract, {other["id"]: other["value"]})[0][other["id"]]
        except (Refused, KeyError, TypeError):
            notes.append(f"task {other['id']} has no measurable context: skipped")
            continue
        history.setdefault((context, other["provider"]), []).append(inv.get("compute_ns", 0))
    past = {key: median(vals) for key, vals in history.items()}
    retained, demanded = 0, 0
    for task in tasks:
        context = contexts[task["id"]]
        costs = {p: past[(context, p)] for p in {p for c, p in past} if (context, p) in past}
        if not costs:
            continue
        demanded += 1
        best = min(costs.values())
        if any(p in active or p in dormant for p, cost in costs.items()
               if cost <= best * (1 + margin)):
            retained += 1

    turnover = dict(acquisitions=0, regenerations=0, dormancies=0, wakes=0, retirements=0,
                    assimilations=0)
    first_retire = {}
    for event in journal:
        if event["kind"] == "member-retired":
            member_id = f"{event.get('capability')}|{event.get('provider')}"
            first_retire.setdefault(member_id, event["seq"])
    acquired_here = []
    for event in journal:
        if not lo <= event["seq"] <= hi:
            continue
        kind = event["kind"]
        if kind == "member-admitted":
            turnover["acquisitions"] += 1
            member_id = f"{event.get('capability')}|{event.get('provider')}"
            if first_retire.get(member_id, hi + 1) < event["seq"]:
                turnover["regenerations"] += 1
            if event.get("capability") == capability:
                acquired_here.append(event.get("provider"))
        elif kind == "member-dormant":
            turnover["dormancies"] += 1
        elif kind == "member-woke":
            turnover["wakes"] += 1
        elif kind == "member-retired":
            turnover["retirements"] += 1
        elif kind == "assimilation-published":
            turnover["assimilations"] += 1

    pool = (set(provider_ids) - set(acquired_here)) | set(acquired_here)
    depths, memo = {}, {}

    def _depth(pid, visiting):
        if pid in memo:
            return memo[pid]
        if pid in visiting:
            return 0
        try:
            deps = store.get("provider", pid).get("transitive_dependencies", []) or []
        except Refused:
            deps = []
        links = [d for d in deps if d in pool]
        memo[pid] = 0 if not links else 1 + max(_depth(d, visiting | {pid}) for d in links)
        return memo[pid]

    reused = 0
    for pid in acquired_here:
        try:
            deps = set(store.get("provider", pid).get("transitive_dependencies", []) or [])
        except Refused:
            deps = set()
        if deps & pool:
            reused += 1
            depths[pid] = _depth(pid, set())
    retained_members = [p for p in active + dormant]
    edges = 0
    closures = []
    for pid in retained_members:
        try:
            spec = store.get("provider", pid)
        except Refused:
            continue
        edges += len(spec.get("transitive_dependencies", []) or [])
        affected, _ = closure.population_closure(population, {pid}, "support")
        closures.append(len(affected))

    report = {
        "N": dict(active=len(by_state.get("ACTIVE", [])), dormant=len(by_state.get("DORMANT", [])),
                  archived=len(by_state.get("ARCHIVED", [])),
                  providers=provider_ids,
                  composites=sorted(pid for pid, kind in kinds.items() if kind == "graph"),
                  blocked=blocked),
        "C": dict(coverage=sum(served) / total, served=sum(served), demanded=total,
                  detail=coverage),
        "Q": dict(mean_regret=sum(regrets) / len(regrets) if regrets else None,
                  served=len(regrets), unserved=unserved),
        "D": diversity,
        "L": dict(retained=retained / demanded if demanded else None,
                  retained_tasks=retained, demanded_tasks=demanded),
        "V": turnover,
        "R": dict(compute_ns=compute_ns, overhead_ns=overhead_ns,
                  construction=buckets.get("construction", {}),
                  validation=buckets.get("validation", {}),
                  assessment_ns=assessment_ns, maintenance_units=maintenance_units,
                  maintenance_spend=buckets.get("maintenance", {}),
                  execution_spend=buckets.get("execution", {}),
                  outstanding_holdings=outstanding),
        "reuse": dict(fraction=reused / len(acquired_here) if acquired_here else None,
                      acquisitions=len(acquired_here), mean_depth=(
                          sum(depths.values()) / len(depths) if depths else None)),
        "complexity": dict(transitive_edges=edges, members=len(retained_members),
                           mean_closure_size=(
                               sum(closures) / len(closures) if closures else None)),
        "meta": dict(capability=capability, window_tasks=[t["id"] for t in tasks],
                     journal_span=[lo, hi], admission_evaluations=admission.evaluations,
                     meter_wall_ns=time.perf_counter_ns() - started, notes=notes),
    }
    admission.close()
    return report


def _copy_store(store):
    """Throwaway copy of the store for interventions (the live store is untouched)."""
    tmp = tempfile.TemporaryDirectory()
    try:
        target = sqlite3.connect(str(Path(tmp.name) / "copy.sqlite3"))
        with store.mutex:
            store.db.backup(target)
        target.close()
        return tmp, Store(Path(tmp.name) / "copy.sqlite3")
    except BaseException:
        tmp.cleanup()
        raise


def organizational_verdict(store, capability, *, margin=0.10, latency_floor_ns=None,
                           admission_timeout=10, development_budget=None,
                           external_adapters=None):
    """Organizational-capability test for one capability (R-25-07).

    (1) Structure dependence: no single catalogue primitive satisfies the
    contract, both catalogue-wide and with coordination removed on a store
    copy restricted to primitive providers. (2) Substitution robustness: for
    every provider in the current support set (the ACTIVE member providers), a
    `block` impact on a store copy is followed by the capability being served
    again through another active member, a wake, or regeneration. Interventions
    never touch the live store. De-novo acquisition inside the window is an X4
    observation, not something this instrument predicts: the re-serve paths it
    checks are the kernel's own recovery paths.

    Returns per-provider results, the checks spent, and one of
    organizational / compositional-but-fragile / redundant / neither /
    inconclusive-budget.
    """
    margin = _margin(margin)
    if latency_floor_ns is not None:
        _number("latency_floor_ns", latency_floor_ns)
    if development_budget is not None:
        _number("development_budget", development_budget)
    contract = store.get("capability", capability)
    cases = contract["admission_cases"]
    support = sorted({m["provider"] for m in store.find("member")
                      if m["capability"] == capability and m["state"] == "ACTIVE"})
    if not support:
        raise Refused("no active members: nothing serves this capability")
    spent = 0

    def affordable(units):
        return development_budget is None or spent + units <= development_budget

    def sweep_list(admission, candidates):
        """Sweep provider ids: (hit, done). `done` is False on budget exhaustion."""
        nonlocal spent
        for pid in candidates:
            if not affordable(len(cases)):
                return None, False
            before = admission.evaluations
            passed, _ = admission.check(pid, cases)
            spent += admission.evaluations - before
            if passed:
                return pid, True
        return False, True

    primitives = sorted(name for name, entry in providers.PRIMITIVES.items()
                        if entry.input == contract["input"] and entry.output == contract["output"])
    standalone = make_runner("inprocess", ProviderRegistry(store), lambda kind, **fields: None)
    catalogue_served, catalogue_open = False, False
    for name in primitives:
        if not affordable(len(cases)):
            catalogue_open = True
            break
        try:
            spec = providers.specification(name)
        except Refused:
            continue
        produced, timings, passed, finished = [], [], True, True
        for value, expected in cases:
            if not affordable(1):
                catalogue_open, finished = True, False
                break
            spent += 1
            try:
                result = standalone.compute(spec, value, admission_timeout,
                                            on_result=produced.append,
                                            on_timing=timings.append)
            except Refused:
                passed = False
                break
            if result != expected:
                passed = False
                break
        if not finished:
            break
        if passed:
            catalogue_served = True
            break
    if catalogue_open and not catalogue_served:
        catalogue_served = None

    tmp, copied = _copy_store(store)
    present_probe = None
    try:
        copy_registry = ProviderRegistry(copied)
        present = sorted(row["id"] for row in copied.find("provider")
                         if row.get("kind") == "primitive"
                         and copy_registry.blocking_impact(row["id"]) is None)
        present_probe = _Admission(copied, admission_timeout, external_adapters)
        present_hit, present_done = sweep_list(present_probe, present)
    finally:
        if present_probe is not None:
            present_probe.close()
        copied.close()
        tmp.cleanup()

    structure = dict(catalogue_primitives=len(primitives),
                     catalogue_served=catalogue_served,
                     store_primitives_served=present_hit,
                     dependence=(catalogue_served is False and present_hit is False))

    substitution, robust, exhausted = {}, True, False
    for pid in support:
        if not affordable(len(cases)):
            exhausted = True
            substitution[pid] = dict(served_again=None, path="unverified-budget",
                                     reason="development budget exhausted")
            continue
        tmp, copied = _copy_store(store)
        probe = None
        try:
            copy_registry = ProviderRegistry(copied)
            copy_registry.record_impact([pid], "support", "emergence-meter substitution probe")
            probe = _Admission(copied, admission_timeout, external_adapters)
            states = [(m["provider"], m["state"]) for m in copied.find("member")
                      if m["capability"] == capability]
            path, served, done = None, False, True
            for want, label in (("ACTIVE", "active-member"), ("DORMANT", "wake"),
                                ("ARCHIVED", "regenerate")):
                candidates = sorted({p for p, s in states
                                     if s == want and copy_registry.blocking_impact(p) is None})
                hit, done = sweep_list(probe, candidates)
                if not done:
                    break
                if hit:
                    path, served = label, True
                    break
            substitution[pid] = dict(served_again=served if done else None,
                                     path=path if done else "unverified-budget",
                                     reason=("re-served" if served else "no recovery path serves")
                                     if done else "development budget exhausted")
            exhausted |= not done
            robust &= done and served
        finally:
            if probe is not None:
                probe.close()
            copied.close()
            tmp.cleanup()

    if exhausted and not all(v["served_again"] for v in substitution.values()):
        verdict = "inconclusive-budget"
    elif structure["dependence"] and robust:
        verdict = "organizational"
    elif structure["dependence"]:
        verdict = "compositional-but-fragile"
    elif robust:
        verdict = "redundant"
    else:
        verdict = "neither"
    return dict(capability=capability, support=support, structure_dependence=structure,
                substitution=substitution, verdict=verdict, checks_spent=spent,
                development_budget=development_budget)


def net_value(windows, values):
    """Net organizational value over a horizon (R-20-07).

    NOV = sum over windows of [value(served demand) - cost_total]. Every one
    of the six cost components must be present: omitting a component is how
    uneconomical development hides, so it is refused rather than defaulted.
    Served demand takes the declared per-request value, less the declared
    lateness penalty past the contract floor; unserved demand is worth zero.
    All numbers share the experiment's declared unit; conversion of native
    ledger units (nanoseconds, attempts, maintenance units) is the demand
    owner's declaration, recorded in the value table.
    """
    if not isinstance(values, dict) or not values:
        raise Refused("a declared value table per contract is required")
    table = {}
    for contract, spec in values.items():
        if not isinstance(spec, dict) or "per_request" not in spec:
            raise Refused(f"value for {contract!r} needs a per_request declaration")
        table[contract] = (spec["per_request"], spec.get("late_penalty", 0))
        _number(f"value[{contract}].per_request", table[contract][0])
        _number(f"value[{contract}].late_penalty", table[contract][1])
    if not isinstance(windows, list) or not windows:
        raise Refused("a horizon needs at least one window")
    per_window, total = [], 0.0
    for index, window in enumerate(windows):
        served = window.get("served", [])
        costs = window.get("costs", {})
        if set(costs) != set(NOV_COSTS):
            raise Refused(f"window {index}: cost_total needs exactly {NOV_COSTS}")
        cost = 0.0
        for name in NOV_COSTS:
            _number(f"windows[{index}].costs[{name}]", costs[name])
            cost += costs[name]
        value = 0.0
        for entry in served:
            if entry["contract"] not in table:
                raise Refused(f"window {index}: no declared value for {entry['contract']!r}")
            per_request, penalty = table[entry["contract"]]
            if not isinstance(entry.get("late", False), bool):
                raise Refused(f"window {index}: lateness must be a boolean")
            value += per_request - (penalty if entry.get("late", False) else 0)
        per_window.append(dict(value=value, cost=cost, net=value - cost))
        total += value - cost
    return dict(total=total, windows=per_window)
