"""BrainOS ecology observatory: a projection of the persistent runtime.

Each tick the loop serves demand, builds an evidence-grounded observation,
asks the replaceable developmental policy for one decision, executes it
through the kernel's own gates, and journals the disposition. Environmental
phases are scheduled (and journaled as scheduled); organizational responses
arise from policy and evidence, never from phase position. Operator-forced
phase changes are journaled as operator interventions, distinct from the
schedule. Unresolved deficiencies are first-class records and veto viability.

Unified with the ADR coordination core (2026-11-25): the hardcoded
demonstration orchestration was replaced by development_policy. No new
authority, permits, budgets, or provider families are introduced here.

Usage: py live/server.py [--port 8137] [--tick 1.0] [--state-dir DIR] [--reset]
Reset is destructive and explicit: without it an existing store resumes.
"""
import argparse
import json
import math
import queue
import random
import signal
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from brainos import Refused, Runtime
from brainos.__main__ import install
from brainos import emergence
from brainos.assimilation import AssimilationSearch
from brainos.development import CapabilityDemand, CompositionSearch
from brainos.devcontext import development_context
from brainos.development_policy import (PolicyState, build_observation, ViabilityPolicy,
                                        record_decision, full_snapshot)
from brainos.ecology import EcologyPolicy

HERE = Path(__file__).resolve().parent

PARENTS = {"parse": "parse_csv", "total": "sum", "total_loop": "sum_loop", "count": "count",
           "length": "text_length", "negate": "negate", "double": "double"}
PARENT_CASES = {"parse": [("1,2", [1, 2])], "total": [([1, 2], 3)], "total_loop": [([1, 2], 3)],
                "count": [([1, 2], 2)], "length": [("ab", 2)], "negate": [(3, -3)],
                "double": [(3, 6)]}
ARITH_CASES = {"arith-sum": [("4,5", 9), ("", 0), ("7", 7)],
               "arith-neg": [("4,5", -9), ("", 0), ("7", -7)],
               "arith-double": [("4,5", -18), ("", 0), ("7", -14)]}
ARITH_FNS = {"arith-sum": lambda xs: sum(xs), "arith-neg": lambda xs: -sum(xs),
             "arith-double": lambda xs: -2 * sum(xs)}
WRONG_COST = 10 ** 12
DEV_ATTEMPTS = 20000
EXEC_ATTEMPTS = 1000000
VIABILITY_EVERY = 25
WINDOW = 10
ASSESS_EVERY = 200
KINDS = ("arith-sum", "arith-neg", "arith-double", "range-count")
RANGE_ADMISSION = [({"data": [1, 5, 9], "queries": [[0, 5]]}, [2]),
                   ({"data": [], "queries": [[0, 1]]}, [0]),
                   ({"data": [3, 3, 7], "queries": [[3, 3], [4, 8]]}, [2, 1])]
NOV_PER_REQUEST = 10
NOV_MODEL = "declared value 10 per served demand, 1 unit = 1e6 ns (X4 convention)"

AUTO_BOUNDS = [("stable", 0), ("drift", 60), ("novel", 120), ("scarcity", 200),
               ("disruption", 260), ("recovery", 340)]
BOUNDS = {"deadline": 15, "candidates": 64}
SCARCE_BOUNDS = {"deadline": 6, "candidates": 24}

TICK_QUEUES = []
LOCK = threading.Lock()
STATE = {}


def now():
    return time.strftime("%H:%M:%S")


def journal(kind, **fields):
    rt = STATE.get("rt")
    if rt is None:
        return
    try:
        with rt.store.mutex:
            if rt.store.closed:
                return
            if rt.store.db.in_transaction:
                rt.store.event(kind, **fields)
            else:
                with rt.store.transaction():
                    rt.store.event(kind, **fields)
    except Exception:
        pass


def _jsonable(value):
    if isinstance(value, float):
        if math.isinf(value):
            return "infinite"
        if math.isnan(value):
            return None
        return value
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return value


def snapshot():
    with LOCK:
        return (dict(STATE["org"]), dict(STATE["viability"]), dict(STATE["dev_left"]),
                STATE["phase"], list(STATE["states"]), STATE["stats"],
                [d for d in STATE["deficiencies"] if d["status"] == "open"])


def observatory_extension():
    """Runtime-derived observatory panels: competence, retention,
    runway, churn, NOV, acquisition lineage, unresolved deficiencies.
    Observed/estimated/unknown are labeled per field; nothing here is
    fabricated."""
    with LOCK:
        detail = STATE.get("viability_detail") or {}
        caps = detail.get("capabilities", {})
        competence, retention = {}, {}
        for cid, rep in caps.items():
            kind = rep.get("name", cid)
            comp = rep.get("competence", {})
            competence[kind] = dict(
                status=comp.get("status", "unknown"),
                n=comp.get("n", 0),
                kernel_success_rate=comp.get("kernel_success_rate"),
                correct_rate=comp.get("correct_rate"),
                per_context={c: dict(n=s.get("n"), thin=s.get("thin"),
                                     correct_rate=s.get("correct_rate"))
                             for c, s in comp.get("per_context", {}).items()})
            retention[kind] = {
                p: dict(state=r.get("state"), verdict=r.get("verdict"),
                        freshness=r.get("freshness"), age_steps=r.get("age_steps"))
                for p, r in rep.get("retention", {}).get("providers", {}).items()}
        runway = {b: dict(status=e.get("status"), periods=e.get("periods"),
                          available=e.get("available"), spent=e.get("spent"),
                          burn_per_step=e.get("burn_per_step"))
                  for b, e in detail.get("runway", {}).items()}
        churn = detail.get("churn", {})
        nov = STATE.get("nov", {})
        acquisitions = [dict(kind=a.get("kind"),
                             provider=(a.get("provider") or "")[:12],
                             tick=a.get("tick"))
                        for a in STATE.get("acquisitions", [])[-20:]]
        unresolved = []
        for d in STATE.get("decisions", [])[-200:]:
            disp = str(d.get("disposition", "recorded"))
            if d.get("action") in ("investigate", "construct", "recruit", "suspend",
                                   "assimilate", "regenerate") and \
                    not disp.startswith(("executed", "recorded")):
                unresolved.append(dict(tick=d.get("tick"), action=d.get("action"),
                                       target=d.get("target"), disposition=disp))
    return _jsonable(dict(competence=competence, retention=retention, runway=runway,
                          churn=churn, nov=nov, acquisitions=acquisitions,
                          unresolved=unresolved[-20:]))


def emit(record):
    with LOCK:
        STATE["decisions"].append(record)
        del STATE["decisions"][:-200]
    journal("eco-decision", **{k: str(v)[:200] for k, v in record.items()
                               if k in ("tick", "action", "detail", "phase")})
    org, viability, dev_left, phase, states, stats, open_def = snapshot()
    for q in list(TICK_QUEUES):
        try:
            q.put_nowait(dict(record, org=org, viability=viability, dev_left=dev_left,
                              phase=phase, states=states, stats=stats,
                              open_deficiencies=open_def))
        except queue.Full:
            TICK_QUEUES.remove(q)


def active_members(rt, cap):
    try:
        return [m["provider"] for m in rt.population.members(cap, states=("ACTIVE",))]
    except Exception:
        return []


def all_members(rt, cap):
    try:
        return [(m["provider"][:12], m["state"])
                for m in rt.population.members(cap, include_archived=False,
                                               states=("ACTIVE", "DORMANT"))]
    except Exception:
        return []


def refresh_org(rt):
    with LOCK:
        STATE["org"] = {kind: all_members(rt, cap) for kind, cap in STATE["caps"].items()}


def refresh_dev_left(rt):
    try:
        rec = rt.resources.budget(STATE["dev"], "dev")
        with LOCK:
            STATE["dev_left"] = dict(rec.get("available", {}))
    except Exception:
        pass


def refresh_states():
    with LOCK:
        v = STATE["viability"]
        hist = STATE["viab_history"]
        open_def = [d for d in STATE["deficiencies"] if d["status"] == "open"]
        demanded = [d for d in open_def if d.get("demanded")]
        left = STATE["dev_left"].get("attempts", 0)
        states = set()
        if not v:
            states.add("indeterminate")
        else:
            if v.get("viable") and len(hist) >= 3 and all(hist[-3:]):
                states.add("homeostatic")
            if not v.get("viable") or demanded:
                states.add("degraded")
        if STATE["developing"] or STATE["last_acquired_tick"] is not None and \
                STATE["tick"] - STATE["last_acquired_tick"] < 25:
            states.add("adapting")
        if STATE["investigating"]:
            states.add("investigating")
        if left < 0.2 * DEV_ATTEMPTS or STATE.get("budget_refused"):
            states.add("resource-constrained")
        if STATE.get("recovering"):
            states.add("recovering")
        if v.get("viable") and STATE["tick"] - STATE.get("last_dev_tick", 0) > 50:
            states.add("quiescent")
        STATE["states"] = sorted(states)


def open_deficiency(tick, kind, reason, demanded):
    with LOCK:
        for d in STATE["deficiencies"]:
            if d["status"] == "open" and d["kind"] == kind:
                return d
        d = dict(kind=kind, since_tick=tick, reason=reason, demanded=demanded,
                 status="open", steps=[])
        STATE["deficiencies"].append(d)
        return d


def step_deficiency(kind, step):
    with LOCK:
        for d in STATE["deficiencies"]:
            if d["status"] == "open" and d["kind"] == kind:
                d["steps"].append(step)


def close_deficiency(kind, resolution):
    with LOCK:
        for d in STATE["deficiencies"]:
            if d["status"] == "open" and d["kind"] == kind:
                d["status"] = "resolved"
                d["resolution"] = resolution


def ground_range(value):
    return [sum(1 for x in value["data"] if lo <= x <= hi)
            for (lo, hi) in value["queries"]]


def acquire_constructed(rt, tick, kind, value, expected, budget, bounds):
    """Bounded construction with independent held-out evaluation.
    Returns (disposition, provider_or_None); every path journals."""
    cap = STATE["caps"][kind]
    phase = STATE["phase"]
    example = CapabilityDemand(kind, "text", "integer", ((value, expected),),
                               max_depth=4, max_candidates=bounds["candidates"],
                               deadline_seconds=bounds["deadline"])
    search = CompositionSearch(rt)
    try:
        result = search.acquire(example, "dev", budget, ARITH_CASES[kind],
                                validation_budget=budget, cumulative=True, role=kind)
    except Exception as exc:
        if "overdraft" in str(exc) or "budget" in str(exc).lower():
            with LOCK:
                STATE["budget_refused"] = True
        emit(dict(tick=tick, clock=now(), action="abstained",
                  detail="%s: construction refused (%s); deficiency retained"
                  % (kind, str(exc)[:120]), phase=phase))
        return "abstained: %s" % str(exc)[:120], None
    if result["status"] != "ACQUIRED":
        emit(dict(tick=tick, clock=now(), action="abstained",
                  detail="%s: status %s; deficiency retained" % (kind, result["status"]),
                  phase=phase))
        return "abstained: %s" % result["status"], None
    provider = result["provider"]
    emit(dict(tick=tick, clock=now(), action="evaluating",
              detail="%s: candidate %s on held-out examples"
              % (kind, provider[:12]), phase=phase))
    for hv, hx in [([1, -2, 3], ARITH_FNS[kind]([1, -2, 3])), ([10], ARITH_FNS[kind]([10])),
                   ([-5, -5], ARITH_FNS[kind]([-5, -5]))]:
        task = rt.tasks.create_member_task("dev", cap, provider, ",".join(map(str, hv)),
                                           STATE["execution"])
        out = rt.tasks.run_task(task, rt.tasks.authorize(task, "dev"), "dev")
        if out != hx:
            emit(dict(tick=tick, clock=now(), action="evaluation-failed",
                      detail="%s: %s != %s on held-out" % (kind, out, hx), phase=phase))
            return "evaluation-failed", provider
    try:
        rt.population.set_maintenance(cap, provider, active=50, dormant=25)
    except Refused:
        pass
    with LOCK:
        STATE["acquisitions"].append(dict(kind=kind, provider=provider, tick=tick))
        STATE["last_acquired_tick"] = tick
        if any(d["status"] == "open" for d in STATE["deficiencies"]):
            STATE["recovering"] = True
    close_deficiency(kind, "acquired " + provider[:12])
    emit(dict(tick=tick, clock=now(), action="acquired",
              detail="%s <- %s (evaluated, maintained)" % (kind, provider[:12]),
              phase=phase))
    return "executed: acquired %s" % provider[:12], provider


def execute_investigate(rt, tick, decision, observation):
    """Investigate means: find why, using kernel gates only."""
    kind = decision.get("kind")
    cap = decision.get("capability")
    report = observation["capabilities"][cap]
    members = active_members(rt, cap)
    open_deficiency(tick, kind, decision.get("reason", ""), True)
    if not members:
        bounds = SCARCE_BOUNDS if STATE["phase"] == "scarcity" else BOUNDS
        disposition, _ = acquire_constructed(rt, tick, kind, decision.get("value"),
                                             decision.get("expected"), STATE["dev"],
                                             bounds=bounds)
        return disposition
    if kind == "range-count":
        invocations = []
        for tid in (report.get("competence", {}).get("evidence", [])[-6:]):
            try:
                invocations.append(rt.tasks.task(tid, "dev")["invocation"])
            except Refused:
                pass
        if len(invocations) >= 3:
            verdict = rt.population.assess(cap, members[0], invocations)
            if verdict["verdict"] in ("redundant", "not-best"):
                others = [m for m in members if m != members[0]]
                if others:
                    return "executed: dormant per verified %s (policy must suspend)" % verdict[
                        "verdict"]
            return "executed: assessment %s; lifecycle by policy" % verdict["verdict"]
    return ("abstained: no alternative member and no trusted assess path "
            "for this input schema; deficiency retained")


def execute_decision(rt, tick, decision, observation):
    """Execute one policy decision through kernel gates. Returns disposition."""
    action, target = decision.get("action"), decision.get("capability")
    kind = decision.get("kind", target)
    try:
        if action == "investigate":
            return execute_investigate(rt, tick, decision, observation)
        if action == "recruit":
            try:
                dormant = [m["provider"] for m in rt.population.members(
                    target, states=("DORMANT",))]
            except Refused:
                dormant = []
            if not dormant:
                return "abstained: no dormant member to wake"
            rt.population.wake(target, dormant[0], budget=STATE["dev"], principal="dev")
            with LOCK:
                if any(d["status"] == "open" for d in STATE["deficiencies"]):
                    STATE["recovering"] = True
            close_deficiency(kind, "woke " + dormant[0][:12])
            return "executed: woke %s" % dormant[0][:12]
        if action == "construct":
            use = decision.get("budget") or STATE["dev"]
            disposition, _ = acquire_constructed(
                rt, tick, kind, decision.get("value"), decision.get("expected"),
                use, BOUNDS)
            return disposition
        if action == "suspend":
            evidence = decision.get("evidence", {})
            provider, aid = evidence.get("suspended"), evidence.get("assessment")
            if not provider or not aid:
                return "abstained: suspend lacks verified assessment"
            rt.population.make_dormant(target, provider, assessment=aid)
            return "executed: dormant per verified assessment"
        return "recorded"
    except Refused as exc:
        if "overdraft" in str(exc) or "budget" in str(exc).lower():
            with LOCK:
                STATE["budget_refused"] = True
        return "refused: %s" % str(exc)[:160]
    except Exception as exc:
        return "error: %s: %s" % (type(exc).__name__, str(exc)[:120])


def draw_kind(rng, phase):
    r = rng.random()
    if phase == "stable":
        return "arith-sum" if r < 0.7 else "range-count"
    if phase == "drift":
        return "arith-neg" if r < 0.10 else "arith-sum"
    if phase == "novel":
        return "arith-neg" if r < 0.5 else "arith-sum"
    if phase == "scarcity":
        return "arith-neg" if r < 0.3 else "arith-sum"
    if phase == "disruption":
        return "arith-double" if r < 0.5 else "arith-sum"
    return "arith-double" if r < 0.2 else "arith-sum"


def draw_demand(rng, phase, kind):
    if kind in ARITH_FNS:
        hi = 99 if phase == "drift" else 999
        xs = [rng.randint(-9, hi) for _ in range(rng.randint(2, 8 if phase == "drift" else 4))]
        text = ",".join(map(str, xs))
        return text, ARITH_FNS[kind](xs)
    value = {"data": [rng.randint(-9, 99) for _ in range(rng.randint(1, 6))],
             "queries": [[rng.randint(-9, 20), rng.randint(21, 99)]
                         for _ in range(rng.randint(1, 3))]}
    return value, ground_range(value)


def serve(rt, tick, rng, kind):
    """Serve one demand through the selected member; returns an outcome
    record. Failures return unserved outcomes, never raise."""
    phase = STATE["phase"]
    value, expected = draw_demand(rng, phase, kind)
    context = "drift" if phase == "drift" else "canonical"
    with LOCK:
        STATE["stats"]["demanded"][kind] = STATE["stats"]["demanded"].get(kind, 0) + 1
        STATE["tick"] = tick
        STATE["last_demand"][kind] = (value, expected)
    cap = STATE["caps"][kind]
    members = active_members(rt, cap)
    if not members:
        return dict(kind=kind, served=False, task=None, correct=None,
                    context=context, reason="no active member")
    policy = STATE["policies"][kind]
    policy.members = list(members)
    try:
        member = policy.select(kind, False)[0]
        task = rt.tasks.create_member_task("dev", cap, member, value, STATE["execution"])
        output = rt.tasks.run_task(task, rt.tasks.authorize(task, "dev"), "dev")
    except Refused as exc:
        return dict(kind=kind, served=False, task=None, correct=None,
                    context=context, reason=str(exc)[:120])
    correct = output == expected
    policy.observe(kind, member, 0 if correct else WRONG_COST)
    with LOCK:
        STATE["recent"][kind].append((task, correct, context))
        del STATE["recent"][kind][:-40]
        if correct:
            STATE["stats"]["served"][kind] = STATE["stats"]["served"].get(kind, 0) + 1
            if STATE.get("recovering") and not any(d["status"] == "open"
                                                   for d in STATE["deficiencies"]):
                STATE["recovering"] = False
    return dict(kind=kind, served=True, task=task, correct=correct,
                context=context)


def observe_tick(rt, tick, outcomes):
    """Build the evidence-grounded observation for this tick over the
    rolling recent-outcome window (capped per capability)."""
    with LOCK:
        recent = {STATE["caps"][k]: [tuple(e) for e in v[-12:]]
                  for k, v in STATE["recent"].items()}
    budgets = [(STATE["dev"], "dev"), (STATE["execution"], "dev")]
    demanded = sorted({o["kind"] for o in outcomes})
    return build_observation(
        STATE["ctx"], list(STATE["caps"].values()), budgets=budgets,
        demands={STATE["caps"][k]: None for k in demanded},
        recent=recent, state=STATE["policy_state"], step=tick,
        names={v: k for k, v in STATE["caps"].items()})


def nov_estimate(rt, tick):
    """Estimated net organizational value from meter windows and served
    counts under the declared cost model. Estimated, never measured."""
    total, per_cap = 0.0, {}
    with LOCK:
        recent = {k: [e[0] for e in v[-WINDOW:]] for k, v in STATE["recent"].items()}
        served = {k: STATE["stats"]["served"].get(k, 0) for k in STATE["caps"]}
    for kind, cap in STATE["caps"].items():
        tids = [t for t in recent.get(kind, []) if isinstance(t, str)]
        if not tids:
            continue
        try:
            meter = emergence.measure(rt.store, cap, tids)
        except Refused:
            continue
        native = meter["R"]
        costs = dict(compute=native["compute_ns"] / 10 ** 6,
                     overhead=native["overhead_ns"] / 10 ** 6, construction=0.0,
                     validation=0.0, assessment=native["assessment_ns"] / 10 ** 6,
                     maintenance=float(native["maintenance_units"]))
        value = served.get(kind, 0) * NOV_PER_REQUEST
        net = value - sum(costs.values())
        per_cap[kind] = dict(value=value, costs=costs, net=net)
        total += net
    return dict(total=total, per_capability=per_cap, tick=tick,
                model=NOV_MODEL, status="estimated")


def record_policy_decision(tick, decision, disposition, observation=None):
    key = "t%05d-%s" % (tick, decision["action"])
    try:
        record_decision(STATE["ctx"], decision, key)
    except Refused as exc:
        disposition = "record-refused: %s" % exc
    record = dict(tick=tick, clock=now(), action=decision["action"],
                  target=decision.get("target"), detail=decision.get("reason"),
                  disposition=disposition, phase=STATE["phase"])
    emit(record)
    STATE["policy_state"].log_action(decision["action"], decision.get("target"), tick)
    ev = decision.get("evidence", {})
    comp = ev.get("competence", {})
    if comp.get("evidence"):
        STATE["policy_state"].cited[decision.get("target")] = list(comp["evidence"])
    elif ev.get("member_rows"):
        STATE["policy_state"].cited[decision.get("target")] = list(ev["member_rows"])
    if "probe_sig" in ev:
        STATE["policy_state"].probe[decision.get("target")] = [ev["probe_sig"][0],
                                                               list(ev["probe_sig"][1])]
    if observation is not None:
        report = observation["capabilities"].get(decision.get("target"), {})
        STATE["policy_state"].snapshots[(decision["action"], decision.get("target"))] = \
            sorted(full_snapshot(report))
    if decision["action"] in ("investigate", "construct", "recruit", "suspend",
                              "assimilate", "regenerate"):
        with LOCK:
            STATE["last_dev_tick"] = tick
            STATE["investigating"] = list({decision.get("target") or ""} - {""}) \
                if decision["action"] == "investigate" else []
    return record


def viability(rt, tick, observation=None):
    """Viability from the evidence-grounded observation (or a fresh
    read when none is supplied). Same record shape as before."""
    with LOCK:
        recent = {k: list(v) for k, v in STATE["recent"].items()}
    viable, notes = True, []
    obs = observation or observe_tick(rt, tick, [])
    for cap, report in obs["capabilities"].items():
        kind = report.get("name", cap)
        comp = report.get("competence", {})
        if comp.get("status") != "observed":
            notes.append(kind + ": competence unconfirmed")
            continue
        notes.append(kind + ": success %.2f correct %s n=%d" %
                     (comp.get("kernel_success_rate", 0),
                      comp.get("correct_rate"), comp.get("n", 0)))
    with LOCK:
        STATE["viability_detail"] = obs
        open_blocking = [d for d in STATE["deficiencies"]
                         if d["status"] == "open" and d.get("demanded")]
        if open_blocking:
            viable = False
            notes.append("open deficiencies: " + ", ".join(d["kind"] for d in open_blocking))
        for budget, entry in obs.get("runway", {}).items():
            if entry.get("status") == "observed" and entry.get("periods", float("inf")) < 5:
                viable = False
                notes.append("runway below floor")
                break
        was = STATE.get("was_viable")
        STATE["was_viable"] = viable
        STATE["viability"] = dict(viable=viable, notes=notes, tick=tick)
        STATE["viab_history"].append(viable)
        del STATE["viab_history"][:-5]
    refresh_states()
    if viable and was is not True:
        emit(dict(tick=tick, clock=now(), action="suspended",
                  detail="organization within viability bounds; no development",
                  phase=STATE["phase"]))
    elif not viable and was is True:
        emit(dict(tick=tick, clock=now(), action="pressure",
                  detail="; ".join(notes), phase=STATE["phase"]))
    try:
        STATE["nov"] = nov_estimate(rt, tick)
    except Exception:
        pass


def phase_entry(tick, phase, forced):
    """Environmental transitions are journaled as scheduled; operator
    forcing is journaled as an intervention, never mixed."""
    tag = "operator-forced" if forced else "scheduled"
    if phase == "scarcity":
        emit(dict(tick=tick, clock=now(), action="scarcity",
                  detail="construction bounds tightened (6s/24); spend must justify itself "
                         "(%s)" % tag, phase=phase))
    if phase == "disruption":
        emit(dict(tick=tick, clock=now(), action="disturbance",
                  detail="arith-double flood: no member serves it; investigation expected "
                         "(%s)" % tag, phase=phase))
    if phase == "recovery":
        emit(dict(tick=tick, clock=now(), action="recovery-watch",
                  detail="novel demand recedes; organization should settle if adapted "
                         "(%s)" % tag, phase=phase))


def kind_of(capability):
    for kind, cap in STATE["caps"].items():
        if cap == capability:
            return kind
    return capability


def assessment_drill(rt, tick):
    """Operator-scheduled retention probe (evidence only): serve one fixed
    single-wide workload through each active range member and assess.
    Dormancy, if ever warranted, comes only as a policy suspend proposal
    through the kernel gate, never from this schedule."""
    if "range-count" not in STATE["caps"]:
        return
    cap = STATE["caps"]["range-count"]
    members = active_members(rt, cap)
    if len(members) < 2:
        return
    value = {"data": list(range(100)), "queries": [[0, 50]]}
    expected = ground_range(value)
    invocations = {}
    try:
        for provider in members:
            for _ in range(3):
                task = rt.tasks.create_member_task("dev", cap, provider, value,
                                                   STATE["execution"], timeout=30)
                if rt.tasks.run_task(task, rt.tasks.authorize(task, "dev"),
                                     "dev") != expected:
                    return
                invocations.setdefault(provider, []).append(
                    rt.tasks.task(task, "dev")["invocation"])
        cited = [i for m in members for i in invocations.get(m, [])]
        verdict = rt.population.assess(cap, members[0], cited)
        emit(dict(tick=tick, clock=now(), action="assessed",
                  detail="range-count %s verdict=%s (drill)"
                  % (members[0][:12], verdict["verdict"]), phase=STATE["phase"]))
    except Refused:
        pass


def step_tick(rt, tick, rng, kinds):
    """One coordination step: serve, observe, propose, execute, record."""
    outcomes = []
    for kind in kinds:
        try:
            outcomes.append(serve(rt, tick, rng, kind))
        except Exception as exc:
            outcomes.append(dict(kind=kind, served=False, task=None, correct=None,
                                 context="canonical",
                                 reason="%s: %s" % (type(exc).__name__,
                                                    str(exc)[:120])))
    try:
        observation = observe_tick(rt, tick, outcomes)
        decision = STATE["policy"].propose(observation, STATE["ctx"],
                                          STATE["policy_state"])
        cap = decision.get("target")
        decision["kind"] = kind_of(cap)
        decision["capability"] = cap
        last = STATE["last_demand"].get(decision["kind"], (None, None))
        decision["value"], decision["expected"] = last
        disposition = execute_decision(rt, tick, decision, observation)
        record_policy_decision(tick, decision, disposition, observation)
    except Exception as exc:
        emit(dict(tick=tick, clock=now(), action="tick-error",
                  detail=str(exc)[:160], phase=STATE["phase"]))
    if tick % ASSESS_EVERY == 0:
        try:
            assessment_drill(rt, tick)
        except Exception as exc:
            emit(dict(tick=tick, clock=now(), action="drill-error",
                      detail=str(exc)[:160], phase=STATE["phase"]))
    if tick % VIABILITY_EVERY == 0:
        try:
            viability(rt, tick)
        except Exception as exc:
            emit(dict(tick=tick, clock=now(), action="viability-error",
                      detail=str(exc)[:160], phase=STATE["phase"]))
    refresh_dev_left(rt)
    refresh_org(rt)
    refresh_states()


def attach_runtime(rt, seed):
    """Reattach capabilities, providers, budgets and policies to a runtime."""
    names = {}
    for row in rt.store.find("capability"):
        if row.get("name"):
            names[row["name"]] = row["id"]
    missing = [k for k in KINDS if k not in names]
    if missing:
        raise SystemExit("store has no capability rows for: %s" % missing)
    STATE["caps"] = {k: names[k] for k in KINDS}
    STATE["ctx"] = development_context(rt)
    STATE["scan"] = rt.registry.register("range_scan")
    STATE["hash"] = rt.registry.register("range_hash")
    STATE["dev"] = rt.resources.create_budget("dev", {"attempts": DEV_ATTEMPTS})
    STATE["execution"] = rt.resources.create_budget("dev", {"attempts": EXEC_ATTEMPTS})
    STATE["policies"] = {k: EcologyPolicy([], min_samples=3, margin=0.10,
                                          epsilon=0.05, seed=seed) for k in KINDS}
    STATE["policy"] = ViabilityPolicy()
    STATE["recent"] = {k: [] for k in KINDS}
    STATE["last_demand"] = {}


def fresh_init(rt):
    install(rt, PARENTS, PARENT_CASES)
    for kind in ("arith-sum", "arith-neg", "arith-double"):
        rt.population.define(kind, "text", "integer", ARITH_CASES[kind])
    rt.population.define("range-count", "range-batch", "integers", list(RANGE_ADMISSION))
    attach_runtime(rt, STATE["seed"])
    for pid in (STATE["scan"], STATE["hash"]):
        rt.population.admit(STATE["caps"]["range-count"], pid,
                            budget=STATE["dev"], principal="dev")
    STATE["policy_state"] = PolicyState()
    emit(dict(tick=0, clock=now(), action="initialized",
              detail="empty arith organization; range pre-provisioned",
              phase="stable"))


def resume_runtime(rt):
    attach_runtime(rt, STATE["seed"])
    STATE["policy_state"] = PolicyState.load(STATE["ctx"])
    STATE["policy_state"].note_step(STATE["tick"])
    emit(dict(tick=STATE["tick"], clock=now(), action="resumed",
              detail="operator top-up on restart; policy state step=%s" %
                     STATE["policy_state"].step, phase=STATE["phase"]))


def loop_forever(state_dir, tick_seconds, seed, max_ticks=0):
    rng = random.Random(seed)
    fresh = not (state_dir / "eco.sqlite3").exists()
    rt = Runtime(state_dir / "eco.sqlite3", profile="inprocess")
    STATE.update(rt=rt, seed=seed,
                 decisions=[], deficiencies=[], org={}, viability={}, viab_history=[],
                 dev_left={}, phase="stable", developing=False, investigating=[],
                 auto=True, last_phase=None, tick=0, was_viable=None,
                 last_acquired_tick=None, last_dev_tick=0, recovering=False,
                 budget_refused=False, acquisitions=[], nov={},
                 stats={"demanded": {}, "served": {}}, states=["indeterminate"],
                 stop=False)
    try:
        if fresh:
            fresh_init(rt)
        else:
            resume_runtime(rt)
        refresh_org(rt)
        refresh_dev_left(rt)
        tick = STATE["tick"]
        while not STATE.get("stop"):
            tick += 1
            STATE["tick"] = tick
            if max_ticks and tick >= max_ticks:
                STATE["stop"] = True
            if STATE["auto"]:
                for name, start in reversed(AUTO_BOUNDS):
                    if tick >= start:
                        phase = name
                        break
                if phase != STATE["phase"]:
                    with LOCK:
                        STATE["phase"] = phase
                    if phase != STATE["last_phase"]:
                        STATE["last_phase"] = phase
                        phase_entry(tick, phase, forced=False)
            step_tick(rt, tick, rng, [draw_kind(rng, STATE["phase"])])
            time.sleep(tick_seconds)
    finally:
        try:
            STATE["policy_state"].save(STATE["ctx"])
        except Exception:
            pass
        rt.close()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _send(self, body, ctype):
        data = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/":
            self._send((HERE / "dashboard.html").read_text(encoding="utf-8"),
                       "text/html; charset=utf-8")
        elif self.path == "/events":
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.end_headers()
            q = queue.Queue(maxsize=256)
            TICK_QUEUES.append(q)
            try:
                while True:
                    record = q.get()
                    self.wfile.write(("data: " + json.dumps(_jsonable(record),
                                                            default=str) + "\n\n")
                                     .encode())
            except (BrokenPipeError, ConnectionResetError):
                pass
            finally:
                if q in TICK_QUEUES:
                    TICK_QUEUES.remove(q)
        elif self.path == "/health":
            with LOCK:
                snap = {k: v for k, v in STATE.items() if k != "rt"}
            self._send(json.dumps(_jsonable(snap), default=str), "application/json")
        elif self.path == "/history":
            org, viability, dev_left, phase, states, stats, open_def = snapshot()
            with LOCK:
                decisions = list(STATE["decisions"])
            self._send(json.dumps(_jsonable(dict(
                org=org, viability=viability, dev_left=dev_left, phase=phase,
                states=states, stats=stats, open_deficiencies=open_def,
                decisions=decisions, **observatory_extension())),
                default=str), "application/json")
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/env":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8") if length else "{}"
            try:
                phase = json.loads(body).get("phase", "auto")
            except Exception:
                phase = "auto"
            with LOCK:
                if phase == "auto":
                    STATE["auto"] = True
                elif phase in [b for b, _ in AUTO_BOUNDS]:
                    STATE["auto"] = False
                    STATE["phase"] = phase
                    STATE["last_phase"] = phase
            if phase != "auto":
                try:
                    # Operator intervention, explicitly distinguished from
                    # the scheduled environment (Doc 33 section 33.5).
                    phase_entry(STATE.get("tick", -1), phase, forced=True)
                except Exception:
                    pass
            self._send(json.dumps({"phase": STATE["phase"], "auto": STATE["auto"]}),
                       "application/json")
        else:
            self.send_response(404)
            self.end_headers()


def main():
    import shutil
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8137)
    parser.add_argument("--tick", type=float, default=1.0)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--ticks", type=int, default=0,
                        help="stop after this many ticks (0 = run until stopped)")
    parser.add_argument("--state-dir", default=None)
    parser.add_argument("--reset", action="store_true",
                        help="destructive: wipe the durable store first")
    args = parser.parse_args()
    state_dir = Path(args.state_dir) if args.state_dir else HERE / "state"
    if args.reset and state_dir.exists():
        shutil.rmtree(state_dir)
    state_dir.mkdir(parents=True, exist_ok=True)

    def stop(signum, frame):
        STATE["stop"] = True

    try:
        signal.signal(signal.SIGINT, stop)
        signal.signal(signal.SIGTERM, stop)
    except (ValueError, OSError):
        pass
    threading.Thread(target=loop_forever, args=(state_dir, args.tick, args.seed,
                                                      args.ticks),
                     daemon=True).start()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print("BrainOS ecology observatory: open http://127.0.0.1:%d/ in a browser" % args.port,
          flush=True)
    try:
        server.serve_forever()
    finally:
        STATE["stop"] = True
        server.server_close()


if __name__ == "__main__":
    main()
