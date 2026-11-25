"""Run X4: the continuous developmental ecosystem (Doc 07 section 7.17).

    py tools/run_continuous.py docs/results/2026-11-25T-continuous [seed ...]

Refuses to run unless the preregistration matches its recorded digest and both
files are committed unchanged at HEAD. Refuses to overwrite seed outputs.
One developing organization per demand seed runs live; controls replay a
measured cost table. Results are committed separately and never edited.
"""
import hashlib
import json
import random
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))

from brainos import Refused, Runtime  # noqa: E402
from brainos import providers as trusted_providers  # noqa: E402
from brainos.__main__ import install  # noqa: E402
from brainos import emergence  # noqa: E402
from brainos.assimilation import AssimilationSearch, EvaluationSet, Gate  # noqa: E402
from brainos.development import CapabilityDemand, CompositionSearch  # noqa: E402
from brainos.devcontext import development_context  # noqa: E402
from brainos.ecology import EcologyPolicy, EcologyService  # noqa: E402
from brainos.population import featurize  # noqa: E402
from brainos.runner import make_runner  # noqa: E402
from brainos.registry import ProviderRegistry  # noqa: E402
import run_retention  # noqa: E402

RESULTS = ROOT / "docs" / "results" / "2026-11-25T-continuous"
PREREG = RESULTS / "PREREGISTRATION.md"
PREREG_SHA256 = "d697fdd22957fe6b5c84c9a7c95fbf1731e58fee1e7f736eef10ce9ddfe2c7a1"
SEEDS = (11, 12, 13, 14, 15)
PROFILE = "inprocess"
WRONG_COST = 10 ** 12
EXPLORE_PER_PHASE = 4
VERDICT_BUDGET = 1000
DEV_ATTEMPTS = 30000
DEV_MAINTENANCE = 100000
EXEC_ATTEMPTS = 100000
UNIT_NS = 10 ** 6
VALUES = {"arith": dict(per_request=10, late_penalty=4, floor_ns=5 * 10 ** 9),
          "lookup": dict(per_request=2, late_penalty=1, floor_ns=6 * 10 ** 10)}
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
KINDS = ("arith-sum", "arith-neg", "arith-double")
PHASES = [("P1", 20, "arith-sum", "single-wide"), ("P2", 15, "arith-neg", "many-narrow"),
          ("P3", 15, "arith-double", "many-wide"), ("P4", 20, "arith-sum", "single-wide")]
LOOKUP_MEMBERS = ["range_scan", "range_scan_list", "range_bisect", "range_hash"]


def digest_of(path):
    return hashlib.sha256(Path(path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def committed_unchanged(path):
    rel = Path(path).resolve().relative_to(ROOT).as_posix()
    try:
        head = subprocess.run(["git", "show", f"HEAD:{rel}"], cwd=ROOT,
                              capture_output=True, check=True).stdout
    except subprocess.CalledProcessError:
        return False
    return head.replace(b"\r\n", b"\n") == Path(path).read_bytes().replace(b"\r\n", b"\n")


def verify_frozen():
    actual = digest_of(PREREG)
    if actual != PREREG_SHA256:
        raise SystemExit(f"preregistration digest {actual} != {PREREG_SHA256}; refusing to run")
    for path in (PREREG, Path(__file__)):
        if not committed_unchanged(path):
            raise SystemExit(f"{Path(path).name} is not committed unchanged at HEAD; refusing to run")
    return actual


def gen_stream(seed):
    rng = random.Random(seed)
    demands = []
    for phase, count, akind, lctx in PHASES:
        for _ in range(count):
            xs = [rng.randint(-9, 99) for _ in range(rng.randint(2, 4))]
            text = ",".join(map(str, xs))
            demands.append(dict(idx=len(demands), phase=phase, family="arith", kind=akind,
                                value=text, expected=ARITH_FNS[akind](xs)))
            data = [rng.randrange(100000) for _ in range(2000)]
            if lctx == "single-wide":
                queries = [[lo, lo + rng.randint(20000, 60000)] for lo in [rng.randint(0, 40000)]]
            elif lctx == "many-narrow":
                queries = [[(lo := rng.randint(0, 99996)), lo + rng.randint(0, 4)] for _ in range(60)]
            else:
                queries = [[(lo := rng.randint(0, 96000)), lo + rng.randint(1000, 3000)]
                           for _ in range(60)]
            value = {"data": data, "queries": queries}
            assert featurize(value) == lctx, (seed, phase, featurize(value))
            demands.append(dict(idx=len(demands), phase=phase, family="lookup", kind=lctx,
                                value=value,
                                expected=trusted_providers.compute("range_scan", value)))
    return demands


def measure_table(rt, demands, arith_specs):
    """Pure recomputation over the identical code path; no kernel writes."""
    registry = ProviderRegistry(rt.store)
    runner = make_runner(PROFILE, registry, lambda kind, **fields: None)
    from brainos import providers as _providers
    length = _providers.specification("text_length")
    table = []
    for demand in demands:
        row = dict(idx=demand["idx"], phase=demand["phase"], family=demand["family"],
                   kind=demand["kind"],
                   context=demand["kind"] if demand["family"] == "arith"
                   else featurize(demand["value"]),
                   costs={}, totals={}, outputs={})
        if demand["family"] == "arith":
            specs = dict(arith_specs, length=length)
        else:
            specs = {name: rt.registry.resolve(rt.lookup_ids[name]) for name in LOOKUP_MEMBERS}
        for label, spec in specs.items():
            timings = []
            try:
                output = runner.compute(spec, demand["value"], 60, on_timing=timings.append)
            except Refused as exc:
                row["outputs"][label] = f"REFUSED: {exc}"
                continue
            timing = timings[-1] if timings else {}
            row["outputs"][label] = output
            row["costs"][label] = timing.get("compute_ns", 0)
            row["totals"][label] = timing.get("total_ns", 0)
        if demand["family"] == "lookup":
            from brainos.contracts import digest as _digest
            outs = {_digest(v) for v in row["outputs"].values() if not isinstance(v, str)}
            row["agree"] = len(outs) == 1 and _digest(demand["expected"]) in outs
        table.append(row)
    return table


def active_members(rt, capability):
    return [m["provider"] for m in rt.population.members(capability)]


def run_task(rt, capability, provider, value, budget, principal="dev"):
    task = rt.tasks.create_member_task(principal, capability, provider, value, budget)
    output = rt.tasks.run_task(task, rt.tasks.authorize(task, principal), principal)
    invocation = rt.tasks.invocation(rt.tasks.task(task, principal)["invocation"], principal)
    return task, output, invocation


def run_developing(seed, stream):
    """One persistent organization, live execution, all mechanisms active."""
    out = dict(seed=seed, profile=PROFILE, phases={}, assimilation=[], lifecycle=[],
               construction=[], verdicts={}, nov={}, meter_failures=[])
    with tempfile.TemporaryDirectory() as workdir:
        rt = Runtime(Path(workdir) / "c.db", profile=PROFILE)
        try:
            install(rt, PARENTS, PARENT_CASES)
            caps = {kind: rt.population.define(kind, "text", "integer", ARITH_CASES[kind])
                    for kind in KINDS}
            caps["lookup"] = rt.population.define("lookup", "range-batch", "integers",
                                                  run_retention.ADMISSION)
            rt.lookup_ids = {}
            admit = rt.resources.create_budget("eco", {"attempts": 1000})
            for name in LOOKUP_MEMBERS:
                rt.lookup_ids[name] = rt.registry.register(name)
                rt.population.admit(caps["lookup"], rt.lookup_ids[name], budget=admit,
                                    principal="eco")
                rt.population.set_maintenance(caps["lookup"], rt.lookup_ids[name],
                                              active=50, dormant=25)
            execution = rt.resources.create_budget("dev", {"attempts": EXEC_ATTEMPTS})
            ctx = development_context(rt)
            eco_lookup = EcologyService.create(ctx, caps["lookup"],
                                               {n: rt.lookup_ids[n] for n in LOOKUP_MEMBERS},
                                               min_samples=3, margin=0.10, epsilon=0.05, seed=seed)
            policies = {kind: EcologyPolicy([], min_samples=3, margin=0.10, epsilon=0.05,
                                            seed=seed) for kind in KINDS}
            out["caps"] = dict(caps)
            served_kinds = set()
            for phase, count, akind, lctx in PHASES:
                dev = rt.resources.create_budget("dev", {"attempts": DEV_ATTEMPTS})
                upkeep = rt.resources.create_budget("dev", {"maintenance": DEV_MAINTENANCE})
                explore = {kind: 0 for kind in list(KINDS) + ["lookup"]}
                phase_tasks = {cap: [] for cap in caps.values()}
                phase_demands = [d for d in stream if d["phase"] == phase]
                for demand in phase_demands:
                    cap = caps[demand["kind"]] if demand["family"] == "arith" else caps["lookup"]
                    if demand["family"] == "arith":
                        policy = policies[demand["kind"]]
                        members = [p for p in active_members(rt, cap)]
                        policy.members = list(members)
                        if not members or demand["kind"] not in served_kinds:
                            acquired = acquire_kind(rt, caps, demand, dev)
                            if acquired is not None:
                                members = [p for p in active_members(rt, cap)]
                                if acquired not in policy.members:
                                    policy.members.append(acquired)
                        label = demand["kind"]
                        can_explore = explore[demand["kind"]] < EXPLORE_PER_PHASE
                        member = policy.select(label, can_explore)[0] if members else None
                        explore[demand["kind"]] += 1
                        if member is None:
                            demand.update(served=False, reason="no member after acquisition")
                            continue
                        task, output, invocation = run_task(rt, cap, member, demand["value"],
                                                            execution)
                        correct = output == demand["expected"]
                        late = invocation["total_ns"] > VALUES["arith"]["floor_ns"]
                        demand.update(task=task, output=output, served=bool(correct), late=late,
                                      provider=member,
                                      compute_ns=invocation["compute_ns"],
                                      total_ns=invocation["total_ns"])
                        policy.observe(label, member, invocation["compute_ns"]
                                       if correct else WRONG_COST)
                        if correct:
                            served_kinds.add(demand["kind"])
                    else:
                        context = featurize(demand["value"])
                        can_explore = explore["lookup"] < EXPLORE_PER_PHASE
                        member, exploring = eco_lookup.choose(context, can_explore)
                        explore["lookup"] += 1
                        provider = rt.lookup_ids[member]
                        task, output, invocation = run_task(rt, cap, provider, demand["value"],
                                                            execution)
                        correct = demand["expected"] is not None and output == demand["expected"]
                        late = invocation["total_ns"] > VALUES["lookup"]["floor_ns"]
                        demand.update(task=task, output=output, served=bool(correct), late=late,
                                      provider=provider,
                                      compute_ns=invocation["compute_ns"],
                                      total_ns=invocation["total_ns"])
                        eco_lookup.observe(context, member, exploring, invocation["id"])
                    phase_tasks[cap].append(task)
                meters = {}
                for cap in caps.values():
                    if phase_tasks[cap]:
                        try:
                            meters[cap] = emergence.measure(rt.store, cap, phase_tasks[cap])
                        except Refused as exc:
                            out["meter_failures"].append(dict(phase=phase, capability=cap,
                                                             error=str(exc)))
                out["phases"][phase] = dict(meters=meters, demands=phase_demands)
                assimilate(rt, caps, stream, phase, dev, out)
                transition(rt, caps, eco_lookup, phase, dev, out)
                for cap in caps.values():
                    rt.population.maintain(cap, upkeep, "dev", charge=rt.resources.charge)
                if phase == "P3":
                    for member in list(eco_lookup.policy.dormant):
                        try:
                            outcome = eco_lookup.wake(member, budget=dev, principal="dev")
                        except Refused as exc:
                            outcome = dict(woke=False, error=str(exc))
                        out["lifecycle"].append(dict(phase="P4-start", op="wake", member=member,
                                                     outcome=outcome))
            for cap in caps.values():
                if active_members(rt, cap):
                    out["verdicts"][cap] = emergence.organizational_verdict(
                        rt.store, cap, development_budget=VERDICT_BUDGET)
                else:
                    out["verdicts"][cap] = dict(verdict="no-members")
            arith_specs = {row["id"]: rt.registry.resolve(row["id"])
                             for row in rt.store.find("provider")
                             if row.get("kind") == "graph"}
            out["table"] = measure_table(rt, stream, arith_specs)
            out["nov"] = developing_nov(out)
            out["head"] = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                         capture_output=True, text=True).stdout.strip()
        finally:
            rt.close()
    return out


def acquire_kind(rt, caps, demand, budget):
    """One bounded cumulative acquisition for the demand's kind capability."""
    cap = caps[demand["kind"]]
    example = CapabilityDemand(demand["kind"], "text", "integer",
                               ((demand["value"], demand["expected"]),),
                               max_depth=2, max_candidates=64, deadline_seconds=60)
    search = CompositionSearch(rt)
    try:
        result = search.acquire(example, "dev", budget, ARITH_CASES[demand["kind"]],
                                validation_budget=budget, cumulative=True, role=demand["kind"])
    except Refused as exc:
        return None
    if result["status"] != "ACQUIRED":
        return None
    rt.population.set_maintenance(cap, result["provider"], active=50, dormant=25)
    return result["provider"]


def assimilate(rt, caps, stream, phase, budget, out):
    """One corrected-gate assimilation attempt over the arith members."""
    parents = [dict(capability=cap, provider=pid) for kind in KINDS for cap in [caps[kind]]
               for pid in active_members(rt, caps[kind])]
    if len(parents) < 2:
        out["assimilation"].append(dict(phase=phase, attempted=False,
                                        reason="fewer than two parents"))
        return
    by_kind = {}
    for d in stream:
        if d["family"] == "arith":
            by_kind.setdefault(d["kind"], []).append((d["idx"], d["value"]))
    phase_idx = {d["idx"] for d in stream if d["phase"] == phase}
    phase_kinds = sorted({d["kind"] for d in stream if d["phase"] == phase
                          and d["family"] == "arith"})
    epochs, dependents = [], {}
    for kind in phase_kinds:
        values = [v for i, v in by_kind[kind] if i in phase_idx]
        held = values[::3] or values[:1]
        observed = [v for v in values if v not in held] or values
        epochs.append([(caps[kind], v, "observed") for v in observed])
        epochs.append([(caps[kind], v, "held-out") for v in held])
    bound = {role: provider for role, provider in rt.manifest()["bindings"].items()}
    for role in bound:
        if role in by_kind:
            dependents[role] = [v for _, v in by_kind[role]]
    gate = Gate(tolerance={cap: 1.5 for cap in caps.values()}, horizon_epochs=50.0)
    search = AssimilationSearch(rt)
    try:
        nominated, _ = search.nominate(parents, max_candidates=8)
    except Refused as exc:
        out["assimilation"].append(dict(phase=phase, attempted=True, nominated=0,
                                        reason=f"nomination refused: {exc}"))
        return
    verdicts = []
    for candidate in nominated:
        verdicts.append(search.evaluate(
            candidate, parents, EvaluationSet(epochs=epochs, dependents=dependents), gate,
            budget=budget, principal="dev"))
    chosen = search.select(verdicts, gate)
    record = dict(phase=phase, attempted=True, nominated=len(nominated),
                  evaluated=len(verdicts),
                  accepted=bool(chosen and chosen.get("selectable")),
                  reasons=(chosen or {}).get("final_reasons", []),
                  method=(chosen or {}).get("method"))
    if chosen and chosen.get("selectable"):
        role_cases = {role: ARITH_CASES[role] for role in bound if role in ARITH_CASES}
        try:
            aid = search.publish(chosen, parents, role_cases, budget=budget, principal="dev")
            plan = rt.store.get("assimilation", aid)
            selection = plan.get("lineage", {}).get("selection")
            lineage_ok = False
            if selection:
                try:
                    rt.store.get("assimilation-trial", selection)
                    lineage_ok = True
                except Refused:
                    pass
            record.update(assimilation=aid, lineage_ok=lineage_ok)
            if not lineage_ok:
                record.update(accepted=False,
                              publish_error="publication lineage has no recorded selection")
        except Refused as exc:
            record.update(accepted=False, publish_error=str(exc))
    out["assimilation"].append(record)


def transition(rt, caps, eco_lookup, phase, budget, out):
    """Phase-end retention transitions for the lookup population."""
    for member in list(eco_lookup.policy.members):
        try:
            assessment = eco_lookup.assess(member)
        except Refused as exc:
            out["lifecycle"].append(dict(phase=phase, op="assess", member=member,
                                         error=str(exc)))
            continue
        verdict = assessment["verdict"]
        if verdict == "redundant":
            try:
                eco_lookup.retire(member, reason=f"X4 {phase}: redundant")
                out["lifecycle"].append(dict(phase=phase, op="retire", member=member))
            except Refused as exc:
                out["lifecycle"].append(dict(phase=phase, op="retire", member=member,
                                             error=str(exc)))
        elif verdict == "not-best":
            try:
                eco_lookup.make_dormant(member)
                out["lifecycle"].append(dict(phase=phase, op="dormant", member=member))
            except Refused as exc:
                out["lifecycle"].append(dict(phase=phase, op="dormant", member=member,
                                             error=str(exc)))
        else:
            out["lifecycle"].append(dict(phase=phase, op="retain", member=member))


def developing_nov(out):
    """NOV per phase for the developing org from its own meter reports."""
    nov = {}
    for phase, data in out["phases"].items():
        value, costs = 0.0, {name: 0.0 for name in emergence.NOV_COSTS}
        served = []
        for demand in data["demands"]:
            family = VALUES[demand["family"]]
            if demand.get("served"):
                value += family["per_request"] - (family["late_penalty"] if demand["late"] else 0)
                served.append(dict(contract=demand["kind"], late=bool(demand["late"])))
        for cap, report in data["meters"].items():
            scale = 1 / UNIT_NS
            costs["compute"] += report["R"]["compute_ns"] * scale
            costs["overhead"] += report["R"]["overhead_ns"] * scale
            costs["construction"] += sum(report["R"]["construction"].values())
            costs["validation"] += sum(report["R"]["validation"].values())
            costs["assessment"] += report["R"]["assessment_ns"] * scale
            costs["maintenance"] += report["R"]["maintenance_units"]
        result = emergence.net_value([dict(served=served, costs=costs)],
                                     {d["kind"]: dict(per_request=VALUES[d["family"]]["per_request"],
                                                      late_penalty=VALUES[d["family"]]["late_penalty"])
                                      for d in data["demands"]})
        nov[phase] = dict(value=value, costs=costs, net=result["total"],
                          served=len(served), demanded=len(data["demands"]))
    return nov


def control_nov(seed_out):
    """Counterfactual NOV for fixed, adaptive and oracle from the cost table."""
    table = seed_out["table"]
    by_idx = {}
    for phase in seed_out["phases"].values():
        for d in phase["demands"]:
            by_idx[d["idx"]] = d
    setup = 0.0
    for phase in seed_out["nov"].values():
        setup += phase["costs"]["construction"] + phase["costs"]["validation"]
    orgs = {}
    fixed_lookup = {}
    for row in [r for r in table if r["phase"] == "P1" and r["family"] == "lookup"]:
        fixed_lookup.setdefault(row["context"], []).append(row)
    fixed_choice = {}
    for context, rows in fixed_lookup.items():
        costs = {m: sum(r["costs"].get(m, 10 ** 18) for r in rows[:2]) for m in LOOKUP_MEMBERS}
        fixed_choice[context] = min(costs, key=costs.get)
    arith_first = {}
    for demand in [d for phase in seed_out["phases"].values() for d in phase["demands"]]:
        if demand["family"] == "arith" and demand.get("served") and demand["kind"] not in arith_first:
            arith_first[demand["kind"]] = demand["provider"]
    means = {}
    for row in table:
        key = (row["family"], row["kind"] if row["family"] == "arith" else row["context"])
        for label, cost in row["costs"].items():
            means.setdefault(key, {}).setdefault(label, []).append(cost)
    orgs["fixed"], orgs["adaptive"], orgs["oracle"] = [], [], []
    for phase in ("P1", "P2", "P3", "P4"):
        rows = [r for r in table if r["phase"] == phase]
        for org in orgs:
            window = dict(value=0.0, costs={n: 0.0 for n in emergence.NOV_COSTS})
            orgs[org].append(window)
        for row in rows:
            demand = by_idx[row["idx"]]
            family = VALUES[demand["family"]]
            oracle_cost = min(row["costs"].values()) if row["costs"] else 0
            # fixed
            fixed_label = arith_first.get(demand["kind"]) if demand["family"] == "arith" \
                else fixed_choice.get(row["context"])
            fixed_cost = row["costs"].get(fixed_label)
            fixed_ok = fixed_cost is not None and row["outputs"].get(fixed_label) == demand["expected"]
            # adaptive: best observed mean among correct providers
            key = (row["family"], row["kind"] if row["family"] == "arith" else row["context"])
            seen = {label: sum(v) / len(v) for label, v in means[key].items()
                    if label in row["costs"]}
            adaptive_label = min(
                (label for label in seen
                 if row["outputs"].get(label) == demand["expected"]),
                key=lambda label: seen[label], default=None)
            for org, label, ok in (("fixed", fixed_label, fixed_ok),
                                   ("adaptive", adaptive_label, adaptive_label is not None),
                                   ("oracle", None, True)):
                window = orgs[org][-1]
                cost = (oracle_cost if org == "oracle"
                        else row["costs"].get(label, 0) if ok else 0)
                window["costs"]["compute"] += cost / UNIT_NS
                window["costs"]["overhead"] += max(0, (row["totals"].get(
                    label if org != "oracle" else min(row["costs"], key=row["costs"].get), 0)
                    - cost)) / UNIT_NS if ok or org == "oracle" else 0
                if ok and demand["expected"] is not None:
                    window["value"] += family["per_request"]
        orgs["adaptive"][0]["costs"]["construction"] += setup
    result = {}
    for org, windows in orgs.items():
        nets = [w["value"] - sum(w["costs"].values()) for w in windows]
        result[org] = dict(windows=windows, nets=nets, total=sum(nets))
    return result


def check_hypotheses(seed_out):
    checks = {}
    caps = seed_out["caps"]
    missing = []
    for phase, data in seed_out["phases"].items():
        demanded_caps = {caps[d["kind"]] if d["family"] == "arith" else caps["lookup"]
                         for d in data["demands"]}
        for cap in demanded_caps:
            if cap not in data["meters"]:
                missing.append(dict(phase=phase, capability=cap))
    checks["X4-H1"] = dict(passed=not seed_out["meter_failures"] and not missing
                           and len(seed_out["phases"]) == 4,
                           meter_failures=seed_out["meter_failures"], missing_windows=missing)
    try:
        for org, data in seed_out["controls"].items():
            for window in data["windows"]:
                assert set(window["costs"]) == set(emergence.NOV_COSTS)
        for phase, data in seed_out["nov"].items():
            assert set(data["costs"]) == set(emergence.NOV_COSTS)
        checks["X4-H2"] = dict(passed=True)
    except (AssertionError, KeyError) as exc:
        checks["X4-H2"] = dict(passed=False, error=str(exc))
    pubs = [a for a in seed_out["assimilation"] if a.get("assimilation")]
    trials_ok = all(a.get("nominated", -1) >= 0 and "reasons" in a
                    for a in seed_out["assimilation"] if a.get("attempted"))
    checks["X4-H3"] = dict(passed=all(a.get("lineage_ok") for a in pubs) and trials_ok,
                           publications=len(pubs),
                           lineages=[a.get("lineage_ok") for a in pubs])
    verdicts = seed_out["verdicts"]
    checks["X4-H4"] = dict(passed=all(
        v.get("verdict") in ("organizational", "compositional-but-fragile", "redundant",
                             "neither", "inconclusive-budget") and v.get("checks_spent", -1) >= 0
        for v in verdicts.values() if isinstance(v, dict) and "verdict" in v))
    return checks


def run_seed(seed, outdir):
    path = outdir / f"seed-{seed}.json"
    if path.exists():
        raise SystemExit(f"{path.name} already exists; results are never overwritten")
    stream = gen_stream(seed)
    seed_out = run_developing(seed, stream)
    seed_out["controls"] = control_nov(seed_out)
    seed_out["hypotheses"] = check_hypotheses(seed_out)
    seed_out["preregistration"] = PREREG_SHA256
    path.write_text(json.dumps(seed_out, indent=1, default=str), encoding="utf-8")
    return seed_out


def main():
    verify_frozen()
    outdir = Path(sys.argv[1]) if len(sys.argv) > 1 else RESULTS
    seeds = [int(a) for a in sys.argv[2:]] or list(SEEDS)
    outdir.mkdir(parents=True, exist_ok=True)
    for seed in seeds:
        if seed not in SEEDS:
            raise SystemExit(f"seed {seed} is not preregistered")
        started = time.perf_counter()
        seed_out = run_seed(seed, outdir)
        verdicts = {k: v.get("verdict") for k, v in seed_out["verdicts"].items()}
        print(f"seed {seed}: {time.perf_counter() - started:.1f}s "
              f"hypotheses={[k for k, v in seed_out['hypotheses'].items() if v['passed']]} "
              f"verdicts={verdicts} "
              f"nov-developing={round(sum(v['net'] for v in seed_out['nov'].values()), 1)} "
              f"nov-fixed={round(seed_out['controls']['fixed']['total'], 1)} "
              f"nov-adaptive={round(seed_out['controls']['adaptive']['total'], 1)}",
              flush=True)


if __name__ == "__main__":
    main()
