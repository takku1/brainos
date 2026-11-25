"""ADR persistent integration demonstration (ADR-7).

A disclosed development environment on a separate durable store. The
loop serves demand, builds an evidence-grounded observation, asks the
replaceable developmental policy for one decision per step, executes it
through the kernel's own gates, and journals every decision with its
kernel disposition. Nothing here is confirmatory evidence and nothing
is forced: unsuccessful adaptations and unresolved deficiencies are
reported, not repaired by hand.

Resume: an existing store continues (policy state reloads, acquired
organization is verified). Reset only with --reset, which is a
separately authorized destructive act.

Usage: py tools/run_adr.py [--dir PATH] [--ticks 48] [--seed 7] [--reset]
"""
import argparse
import json
import random
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from brainos import Refused, Runtime  # noqa: E402
from brainos.__main__ import install  # noqa: E402
from brainos.assimilation import AssimilationSearch  # noqa: E402
from brainos.development import CapabilityDemand, CompositionSearch  # noqa: E402
from brainos.devcontext import development_context  # noqa: E402
from brainos.development_policy import (PolicyState, build_observation,  # noqa: E402
                                        ViabilityPolicy, record_decision)
from brainos.ecology import EcologyPolicy  # noqa: E402

MOCK = str(ROOT / "implementations" / "mock_adapter.py")
ARTIFACT = "f47f71177f32bcd101b7573ec9171e6a57f4f4d31148d38e382306f42996874b"

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
RANGE_ADMISSION = [({"data": [1, 5, 9], "queries": [[0, 5]]}, [2]),
                   ({"data": [], "queries": [[0, 1]]}, [0]),
                   ({"data": [3, 3, 7], "queries": [[3, 3], [4, 8]]}, [2, 1])]
MOCK_IDENTITIES = dict(model="mock-echo", runtime="mock-adapter/1",
                       tokenizer="tok-A", prompt_template="none")
MOCK_SCHEDULE = dict(initialization=100, inference=5, transport=1, memory=200,
                     accelerator=0, overhead=1)
MOCK_UNITS = dict(initialization="seconds", inference="attempts", transport="attempts",
                  memory="MB", accelerator="seconds", overhead="attempts")
MOCK_MEASURED = dict(initialization="adapter", inference="adapter", transport="kernel",
                     memory="adapter", accelerator="kernel", overhead="kernel")
MOCK_SAMPLING = dict(temperature=0.0, top_p=1.0, max_tokens=64, seed=11)

PHASES = [("stable", 0), ("novel", 12), ("recurring", 18), ("scarcity", 24),
          ("disruption", 30), ("recovery", 36)]
BOUNDS = {"deadline": 15, "candidates": 64}
SCARCE = {"deadline": 5, "candidates": 8}
WRONG_COST = 10 ** 12


def ground_range(value):
    return [sum(1 for x in value["data"] if lo <= x <= hi)
            for (lo, hi) in value["queries"]]


def range_workload(rng):
    data = [rng.randint(-9, 99) for _ in range(rng.randint(1, 6))]
    queries = [[rng.randint(-9, 20), rng.randint(21, 99)] for _ in range(rng.randint(1, 3))]
    return {"data": data, "queries": queries}


class Demo:
    def __init__(self, state_dir, seed):
        self.state_dir = state_dir
        self.rng = random.Random(seed)
        self.seed = seed
        self.rt = None
        self.ctx = None
        self.state = PolicyState()
        self.policy = ViabilityPolicy()
        self.decisions = []
        self.unresolved = []
        self.tick = 0
        self.phase = "stable"
        self.acquired = {}
        self.recent = {}

    # -- setup ------------------------------------------------------
    def open(self):
        self.rt = Runtime(self.state_dir / "eco.db", profile="inprocess",
                          external_adapters={"mock-echo": [sys.executable, MOCK,
                                                           "--expect-artifact", ARTIFACT]})
        self.ctx = development_context(self.rt)
        return self.rt

    def initialize(self):
        rt = self.rt
        install(rt, PARENTS, PARENT_CASES)
        self.caps = {k: rt.population.define(k, "text", "integer", ARITH_CASES[k])
                     for k in ARITH_CASES}
        self.caps["range-count"] = rt.population.define(
            "range-count", "range-batch", "integers", list(RANGE_ADMISSION))
        self.caps["mock-echo"] = rt.population.define(
            "mock-echo", "text", "text", [("a", "a"), ("b", "b")])
        self.dev = rt.resources.create_budget("dev", {"attempts": 600})
        self.tiny = rt.resources.create_budget("dev", {"attempts": 6})
        self.exe = rt.resources.create_budget("dev", {"attempts": 200000})
        self.scan = rt.registry.register("range_scan")
        self.hash = rt.registry.register("range_hash")
        rt.population.admit(self.caps["range-count"], self.scan,
                            budget=self.dev, principal="dev")
        rt.population.admit(self.caps["range-count"], self.hash,
                            budget=self.dev, principal="dev")
        self.echo = rt.registry.register_external(
            implementation="mock-echo", input="text", output="text",
            capability="mock-echo", cost={"attempts": 3},
            cost_schedule=dict(MOCK_SCHEDULE), cost_units=dict(MOCK_UNITS),
            measured_by=dict(MOCK_MEASURED), artifact=ARTIFACT,
            artifact_algorithm="sha256", identities=dict(MOCK_IDENTITIES),
            sampling=dict(MOCK_SAMPLING), nondeterministic=True,
            admission=dict(n=3, k=2))
        rt.population.admit(self.caps["mock-echo"], self.echo,
                            budget=self.dev, principal="dev")
        self.policies = {k: EcologyPolicy([], min_samples=3, margin=0.10,
                                          epsilon=0.05, seed=self.seed)
                         for k in list(ARITH_CASES) + ["range-count", "mock-echo"]}
        self.journal("initialized", "empty arith organization; range + echo pre-provisioned",
                     phase="stable", scheduled=True)

    def resume(self):
        """Continue on an existing store: reattach capabilities, providers
        and operator budgets (fresh grants are journaled as top-ups)."""
        rt = self.rt
        names = {}
        for row in self.ctx.find("capability"):
            if row.get("name"):
                names[row["name"]] = row["id"]
        kinds = list(ARITH_CASES) + ["range-count", "mock-echo"]
        missing = [k for k in kinds if k not in names]
        if missing:
            raise SystemExit("resume found no capability rows for: %s" % missing)
        self.caps = {k: names[k] for k in kinds}
        self.dev = rt.resources.create_budget("dev", {"attempts": 600})
        self.tiny = rt.resources.create_budget("dev", {"attempts": 6})
        self.exe = rt.resources.create_budget("dev", {"attempts": 200000})
        self.scan = rt.registry.register("range_scan")
        self.hash = rt.registry.register("range_hash")
        self.echo = rt.registry.register_external(
            implementation="mock-echo", input="text", output="text",
            capability="mock-echo", cost={"attempts": 3},
            cost_schedule=dict(MOCK_SCHEDULE), cost_units=dict(MOCK_UNITS),
            measured_by=dict(MOCK_MEASURED), artifact=ARTIFACT,
            artifact_algorithm="sha256", identities=dict(MOCK_IDENTITIES),
            sampling=dict(MOCK_SAMPLING), nondeterministic=True,
            admission=dict(n=3, k=2))
        self.policies = {k: EcologyPolicy([], min_samples=3, margin=0.10,
                                          epsilon=0.05, seed=self.seed)
                         for k in kinds}
        self.state = PolicyState.load(self.ctx)
        self.journal("resumed", "operator top-up on restart; policy state step=%s" %
                     self.state.step, scheduled=False)

    def journal(self, action, detail, phase=None, scheduled=False, **fields):
        # The kernel journal requires an explicit transaction; a broken
        # journal breaks the demonstration, so failures propagate.
        with self.rt.store.transaction():
            self.rt.store.event("adr-demo", action=action, detail=detail[:200],
                                phase=phase or self.phase, scheduled=scheduled,
                                **fields)

    # -- demand -----------------------------------------------------
    def demands(self):
        """Scripted environmental schedule (allowed); responses must come
        from the policy, never from the schedule position."""
        phase, rng = self.phase, self.rng
        out = []
        if phase in ("stable", "recurring", "recovery"):
            out.append(("arith-sum", "text", None))
        if phase == "novel":
            out.append(("arith-neg", "text", None))
        if phase in ("scarcity", "disruption", "recovery"):
            out.append(("arith-double", "text", None))
        if phase == "disruption":
            out.append(("arith-sum", "text", None))
        out.append(("range-count", "range", None))
        out.append(("mock-echo", "text", None))
        return out

    def draw(self, kind, wtype):
        if kind in ARITH_FNS:
            hi = 99
            xs = [self.rng.randint(-9, hi) for _ in range(self.rng.randint(2, 4))]
            text = ",".join(map(str, xs))
            return text, ARITH_FNS[kind](xs)
        if kind == "range-count":
            value = range_workload(self.rng)
            return value, ground_range(value)
        value = "__mock__:alternate" if self.tick % 2 else "a"
        return value, value

    # -- serving ----------------------------------------------------
    def serve(self, kind, wtype):
        rt = self.rt
        cap = self.caps[kind]
        value, expected = self.draw(kind, wtype)
        try:
            members = [m["provider"] for m in rt.population.members(
                cap, states=("ACTIVE",))]
        except Refused:
            members = []
        if not members:
            return dict(kind=kind, served=False, task=None, correct=None,
                        context=wtype, reason="no active member")
        pol = self.policies[kind]
        pol.members = list(members)
        member = pol.select(kind, False)[0]
        task = rt.tasks.create_member_task("dev", cap, member, value, self.exe,
                                           timeout=30)
        output = rt.tasks.run_task(task, rt.tasks.authorize(task, "dev"), "dev")
        invocation = rt.tasks.invocation(rt.tasks.task(task, "dev")["invocation"],
                                         "dev")
        correct = output == expected
        pol.observe(kind, member, 0 if correct else WRONG_COST)
        return dict(kind=kind, served=True, task=task, correct=correct,
                    context=wtype, compute=invocation["compute_ns"])

    def kind_of(self, capability):
        for kind, cap in self.caps.items():
            if cap == capability:
                return kind
        return capability

    # -- observation + decision -------------------------------------
    def observe(self, outcomes, demands):
        for outcome in outcomes:
            if outcome["task"] is None:
                continue
            cap = self.caps[outcome["kind"]]
            window = self.recent.setdefault(cap, [])
            window.append((outcome["task"], outcome["correct"],
                           outcome["context"]))
            del window[:-12]
        budgets = [(self.dev, "dev"), (self.exe, "dev")]
        return build_observation(
            self.ctx, list(self.caps.values()), budgets=budgets,
            demands={self.caps[k]: None for k in demands},
            recent={c: list(v) for c, v in self.recent.items()},
            state=self.state, step=self.tick,
            names={v: k for k, v in self.caps.items()})

    def record(self, decision, disposition, observation=None):
        key = "t%05d-%s" % (self.tick, decision["action"])
        try:
            record_decision(self.ctx, decision, key)
        except Refused as exc:
            disposition = "record-refused: %s" % exc
        display = self.kind_of(decision.get("target"))
        self.decisions.append(dict(tick=self.tick, action=decision["action"],
                                   target=display,
                                   reason=decision.get("reason"),
                                   disposition=disposition))
        self.state.log_action(decision["action"], decision.get("target"),
                              self.tick)
        ev = decision.get("evidence", {})
        comp = ev.get("competence", {})
        if comp.get("evidence"):
            self.state.cited[decision.get("target")] = list(comp["evidence"])
        elif ev.get("member_rows"):
            self.state.cited[decision.get("target")] = list(ev["member_rows"])
        if "probe_sig" in ev:
            self.state.probe[decision.get("target")] = [ev["probe_sig"][0],
                                                        list(ev["probe_sig"][1])]
        members = ev.get("member_rows", [])
        if not members and "probe_sig" in ev:
            members = ev["probe_sig"][1]
        self.state.snapshots[(decision["action"], decision.get("target"))] = \
            sorted(members)
        if not disposition.startswith(("executed", "recorded")):
            self.unresolved.append(dict(tick=self.tick, action=decision["action"],
                                        target=display, disposition=disposition))
        if observation is not None:
            report = observation["capabilities"].get(decision.get("target"), {})
            members = report.get("members", {})
            self.state.snapshots[(decision["action"], decision.get("target"))] = \
                sorted(members.get("snapshot", members.get("records", [])))

    # -- execution through kernel gates --------------------------------
    def active_members(self, cap):
        try:
            return [m["provider"] for m in self.rt.population.members(
                cap, states=("ACTIVE",))]
        except Refused:
            return []

    def acquire(self, kind, budget, principal, bounds=BOUNDS):
        """Bounded construction with independent held-out evaluation."""
        rt = self.rt
        value, expected = self.draw(kind, "text")
        example = CapabilityDemand(kind, "text", "integer", ((value, expected),),
                                   max_depth=4, max_candidates=bounds["candidates"],
                                   deadline_seconds=bounds["deadline"])
        search = CompositionSearch(rt)
        result = search.acquire(example, principal, budget, ARITH_CASES[kind],
                                validation_budget=budget, cumulative=True, role=kind)
        if result["status"] != "ACQUIRED":
            return "abstained: %s" % result["status"], None
        provider = result["provider"]
        cap = self.caps[kind]
        for hv, hx in [([1, -2, 3], None), ([10], None), ([-5, -5], None)]:
            hx = ARITH_FNS[kind](hv)
            task = rt.tasks.create_member_task(principal, cap, provider,
                                               ",".join(map(str, hv)), self.exe,
                                               timeout=30)
            out = rt.tasks.run_task(task, rt.tasks.authorize(task, principal),
                                    principal)
            if out != hx:
                return "evaluation-failed: %r != %r on held-out" % (out, hx), provider
        try:
            rt.population.set_maintenance(cap, provider, active=50, dormant=25)
        except Refused:
            pass
        self.acquired[kind] = provider
        self.policies[kind].members = self.active_members(cap)
        return "executed: acquired %s" % provider[:12], provider

    def execute_investigate(self, decision, observation):
        """Investigate means: find why, using kernel gates only."""
        rt = self.rt
        cap = decision.get("target")
        kind = self.kind_of(cap)
        members = self.active_members(cap)
        report = observation["capabilities"][cap]
        if not members:
            budget, bounds = self.dev, BOUNDS
            if self.phase == "scarcity" and kind == "arith-double":
                # Operator-authorized small exploration grant (disclosed drill):
                # the bound itself is the finding when it overdrafts.
                budget, bounds = self.tiny, SCARCE
                self.journal("operator-grant",
                             "scarcity drill: arith-double exploration capped "
                             "at 6 attempts", scheduled=True)
            disposition, provider = self.acquire(kind, budget, "dev",
                                                 bounds=bounds)
            if provider is not None:
                self.journal("acquired", "%s <- %s" % (kind, provider[:12]))
            return disposition
        # Serving members exist: competition and retention evidence first.
        comp = report.get("competence", {})
        if kind == "range-count":
            invocations = []
            for tid in comp.get("evidence", [])[-6:]:
                try:
                    invocations.append(rt.tasks.task(tid, "dev")["invocation"])
                except Refused:
                    pass
            if len(invocations) >= 3:
                verdict = rt.population.assess(cap, members[0], invocations)
                self.journal("assessed", "%s %s verdict=%s" %
                             (kind, members[0][:12], verdict["verdict"]))
                if verdict["verdict"] in ("redundant", "not-best"):
                    others = [m for m in members if m != members[0]]
                    if others:
                        rt.population.make_dormant(
                            cap, members[0], assessment=verdict["id"])
                        return ("executed: dormant per verified %s; %s serves"
                                % (verdict["verdict"], others[0][:12]))
                return ("executed: assessment %s; no lifecycle change "
                        "justified" % verdict["verdict"])
        return ("abstained: no alternative member and no trusted assess path "
                "for this input schema; deficiency retained")

    def execute(self, decision, observation):
        rt, action, target = self.rt, decision["action"], decision.get("target")
        try:
            if action == "investigate":
                return self.execute_investigate(decision, observation)
            cap, kind = decision.get("target"), None
            kind = self.kind_of(cap)
            if action == "recruit":
                dormant = [m["provider"] for m in rt.population.members(
                    cap, states=("DORMANT",))]
                if not dormant:
                    return "abstained: no dormant member to wake"
                rt.population.wake(cap, dormant[0],
                                   budget=self.dev, principal="dev")
                return "executed: woke %s" % dormant[0][:12]
            if action == "construct":
                # The decision names its funding budget; the loop resolves
                # the id against operator-created budgets only.
                use = decision.get("budget") or self.dev
                disposition, provider = self.acquire(
                    kind, use, decision.get("principal") or "dev")
                if provider is not None:
                    self.journal("acquired", "%s <- %s" % (kind, provider[:12]))
                return disposition
            return "recorded"
        except Refused as exc:
            return "refused: %s" % str(exc)[:160]
        except Exception as exc:
            return "error: %s: %s" % (type(exc).__name__, str(exc)[:120])

    # -- main loop ---------------------------------------------------
    def phase_for(self, tick):
        phase = "stable"
        for name, start in PHASES:
            if tick >= start:
                phase = name
        return phase

    def step(self):
        phase = self.phase_for(self.tick)
        if phase != self.phase:
            self.phase = phase
            # Scheduled environmental transition: journaled as an
            # environment event, never as an organizational response.
            self.journal("environment", "phase -> %s (scheduled)" % phase,
                         phase=phase, scheduled=True)
            if phase == "recurring":
                disposition = self.assessment_drill()
                self.journal("assessment-drill", disposition, scheduled=True)
            if phase == "disruption":
                self.disrupt()
        outcomes = []
        for kind, wtype, _ in self.demands():
            try:
                outcomes.append(self.serve(kind, wtype))
            except Refused as exc:
                outcomes.append(dict(kind=kind, served=False, task=None,
                                     correct=None, context=wtype,
                                     reason=str(exc)[:120]))
            except Exception as exc:
                outcomes.append(dict(kind=kind, served=False, task=None,
                                     correct=None, context=wtype,
                                     reason="%s: %s" % (type(exc).__name__,
                                                        str(exc)[:120])))
        demanded = sorted({o["kind"] for o in outcomes})
        observation = self.observe(outcomes, demanded)
        decision = self.policy.propose(observation, self.ctx, self.state)
        disposition = self.execute(decision, observation)
        self.record(decision, disposition, observation)
        if self.tick % 5 == 0:
            self.state.save(self.ctx)
        self.tick += 1
        return decision, disposition

    def assessment_drill(self):
        """Operator-ordered retention probe on range-count: serve one fixed
        single-wide workload through each active member, assess both from
        the cited invocations, and retire nothing without a verified
        redundant/not-best verdict."""
        rt = self.rt
        cap = self.caps["range-count"]
        members = self.active_members(cap)
        if len(members) < 2:
            self.journal("assessment-skipped",
                         "fewer than two active range members", scheduled=True)
            return "skipped"
        value = {"data": list(range(100)), "queries": [[0, 50]]}
        expected = ground_range(value)
        invocations = {}
        try:
            for provider in members:
                for _ in range(3):
                    task = rt.tasks.create_member_task(
                        "dev", cap, provider, value, self.exe, timeout=30)
                    output = rt.tasks.run_task(
                        task, rt.tasks.authorize(task, "dev"), "dev")
                    assert output == expected, (provider, output)
                    invocations.setdefault(provider, []).append(
                        rt.tasks.task(task, "dev")["invocation"])
        except (Refused, AssertionError) as exc:
            return "abstained: probe serving failed (%s)" % str(exc)[:120]
        try:
            verdict = rt.population.assess(cap, members[0], invocations[members[0]])
        except Refused as exc:
            return "refused: %s" % str(exc)[:120]
        self.journal("assessed", "range-count %s verdict=%s (drill)" %
                     (members[0][:12], verdict["verdict"]), scheduled=True)
        if verdict["verdict"] in ("redundant", "not-best"):
            others = [m for m in members if m != members[0]]
            if others:
                rt.population.make_dormant(cap, members[0],
                                           assessment=verdict["id"])
                self.journal("dormant", "%s dormant per verified %s" %
                             (members[0][:12], verdict["verdict"]), scheduled=True)
                return "executed: dormant per verified %s" % verdict["verdict"]
        return "executed: assessment %s; no lifecycle change justified" % verdict[
            "verdict"]

    def disrupt(self):
        """Simulated provider death, executed through the kernel's own
        exclusion path and labeled as a drill in the journal."""
        victims = [p for k, p in getattr(self, "acquired", {}).items()
                   if k == "arith-sum"]
        if victims:
            self.rt.registry.exclude(
                victims[0], "adr-demo drill: simulated provider death")
            self.journal("disturbance", "arith-sum provider excluded; "
                                        "investigation expected", scheduled=True)
        else:
            self.journal("disruption-skipped",
                         "no acquired arith-sum provider to lose", scheduled=True)
        try:
            dormant = [m["provider"] for m in self.rt.population.members(
                self.caps["range-count"], states=("DORMANT",))]
        except Refused:
            dormant = []
        if dormant:
            active = [m for m in self.active_members(self.caps["range-count"])
                      if m not in dormant]
            if active:
                self.rt.registry.exclude(
                    active[0],
                    "adr-demo drill: simulated loss of active range member")
                self.journal("disturbance", "active range member excluded; "
                                            "recruit expected", scheduled=True)

    # -- restart + assimilation + report ------------------------------
    def restart(self):
        self.state.save(self.ctx)
        before = {k: sorted(self.active_members(c))
                  for k, c in self.caps.items()}
        self.rt.close()
        self.rt = Runtime(self.state_dir / "eco.db", profile="inprocess",
                          external_adapters={"mock-echo": [sys.executable, MOCK,
                                                           "--expect-artifact", ARTIFACT]})
        self.ctx = development_context(self.rt)
        self.state = PolicyState.load(self.ctx)
        after = {k: sorted(self.active_members(c))
                 for k, c in self.caps.items()}
        kept = before == after and self.state.step is not None
        self.journal("restarted", "organization %s; developmental state step=%s" %
                     ("preserved" if kept else "CHANGED", self.state.step),
                     scheduled=False)
        return kept

    def assimilation_attempt(self):
        """Surface a legitimate assimilation opportunity; never force it."""
        try:
            search = AssimilationSearch(self.rt)
            candidates, controls = search.nominate(
                [{"capability": self.caps["range-count"], "provider": self.scan},
                 {"capability": self.caps["range-count"], "provider": self.hash}],
                max_candidates=8)
            return ("surfaced: %d candidates, %d controls; awaiting selection "
                    "record, not published (B21)" % (len(candidates), len(controls)))
        except Refused as exc:
            return "refused: %s" % str(exc)[:160]
        except Exception as exc:
            return "error: %s: %s" % (type(exc).__name__, str(exc)[:120])

    def report(self):
        lines = ["# ADR integration demonstration (not evidence)",
                 "",
                 "Operator-harness run on a separate durable store. Decisions by the",
                 "replaceable policy; executions through kernel gates.",
                 ""]
        for tick in sorted({d["tick"] for d in self.decisions}):
            for d in [x for x in self.decisions if x["tick"] == tick]:
                lines.append("- t%d %s %s: %s [%s]" %
                             (d["tick"], d["action"], d["target"],
                              d["reason"], d["disposition"]))
        lines += ["",
                  "## Unresolved deficiencies",
                  ""]
        lines += ["- t%d %s %s: %s" % (u["tick"], u["action"], u["target"],
                                       u["disposition"])
                  for u in self.unresolved] or ["- none"]
        try:
            budgets = {name: self.rt.resources.budget(bid, "dev")
                       for name, bid in (("dev", self.dev), ("exe", self.exe))}
            lines += ["", "## Budgets remaining", ""]
            for name, rec in budgets.items():
                lines += ["- %s: %s" % (name, rec.get("available"))]
        except Exception:
            pass
        lines += ["", "## Members",
                  ""]
        for kind, cap in self.caps.items():
            lines += ["- %s: %s" % (kind, self.active_members(cap))]
        lines += ["",
                  "## Limits (not demonstrated)",
                  "",
                  "- neural providers (W2 owns that door)",
                  "- dormancy, wake and regeneration (assessment drill "
                  "verdict was retain, so no verified transition arose; "
                  "the paths are kernel-tested, not demo-exercised)",
                  "- arith-neg recovery after dependency-closure block "
                  "(undemanded after the disruption; recurring demand "
                  "would re-trigger investigation)",
                  "- formal stability or convergence (W3 owns that claim)",
                  ""]
        (self.state_dir / "DEMO.md").write_text("\n".join(lines), encoding="utf-8")
        return lines


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", default=None)
    parser.add_argument("--ticks", type=int, default=48)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--reset", action="store_true",
                        help="destructive: wipe the demo store first")
    args = parser.parse_args(argv)
    state_dir = Path(args.dir) if args.dir else Path(tempfile.gettempdir()) / "adr-demo"
    if args.reset and state_dir.exists():
        import shutil
        shutil.rmtree(state_dir)
    state_dir.mkdir(parents=True, exist_ok=True)
    demo = Demo(state_dir, args.seed)
    fresh = not (state_dir / "eco.db").exists()
    demo.open()
    if fresh:
        demo.initialize()
    else:
        demo.resume()
    for _ in range(args.ticks):
        demo.step()
    kept = demo.restart()
    for _ in range(3):
        demo.step()
    assimilation = demo.assimilation_attempt()
    demo.journal("assimilation", assimilation, scheduled=False)
    demo.report()
    demo.rt.close()
    print("ticks=%d decisions=%d unresolved=%d restart=%s assimilation: %s" %
          (demo.tick, len(demo.decisions), len(demo.unresolved),
           "preserved" if kept else "CHANGED", assimilation),
          flush=True)
    return 0 if kept else 2


if __name__ == "__main__":
    raise SystemExit(main())
