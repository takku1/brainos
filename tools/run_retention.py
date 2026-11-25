"""Preregistered X2c (retention strategies) and X1b (matched-repertoire construction).

    py tools/run_retention.py docs/results/2026-11-25T-retention [--seeds 101,102] [--quick]

Refuses to run unless PREREGISTRATION.md and this file match their committed
versions (git) and the embedded digest. `--quick` is for tests only; its
output is never a result.
"""
from pathlib import Path
import argparse
import hashlib
import json
import random
import shutil
import subprocess
import sys
import tempfile
import time
from statistics import median

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from brainos import Refused, Runtime  # noqa: E402
from brainos.__main__ import install  # noqa: E402
from brainos.development import CapabilityDemand, CompositionSearch  # noqa: E402
from brainos.devcontext import development_context  # noqa: E402
from brainos.ecology import EcologyService  # noqa: E402
from brainos.population import featurize  # noqa: E402

RESULTS = ROOT / "docs" / "results" / "2026-11-25T-retention"
PREREG = RESULTS / "PREREGISTRATION.md"
PREREG_SHA256 = "53170de81c7a7a0118abd83e3a804bc6d7aa24a30f0a7f970791d95aee086779"
AMENDMENT = RESULTS / "PREREGISTRATION-AMENDMENT-1.md"
AMENDMENT_SHA256 = "c630776871fba5b9f2f74da9697d698bb1ea11393607f388276eba429d6d542a"

MEMBERS = ["range_scan", "range_scan_list", "range_bisect", "range_hash"]
ADMISSION = [({"data": [1, 5, 9], "queries": [[0, 5]]}, [2]), ({"data": [], "queries": [[0, 1]]}, [0]),
             ({"data": [3, 3, 7], "queries": [[3, 3], [4, 8]]}, [2, 1])]
MAINTENANCE = {"range_scan": (50, 10), "range_scan_list": (50, 10), "range_bisect": (100, 20), "range_hash": (400, 80)}
SEEDS = (101, 102, 103, 104, 105)
PERIOD = 10
SEGMENTS = [("E1", 30, "single-wide", 0.0), ("E2", 30, "many-narrow", 0.10), ("E3", 30, "single-wide", 0.0),
            ("E4", 30, "many-wide", 0.0), ("E5", 30, "many-narrow", 0.0)]
SHAPES = {"single-wide": (1, (20000, 60000)), "many-narrow": (400, (0, 4)), "many-wide": (400, (1000, 3000))}
CONDITIONS = {
    "R0": dict(policy=dict(mode="median", prune_factor=10.0, epsilon=0.05), lifecycle="retire", retention={}),
    "R1": dict(policy=dict(mode="median", prune_factor=10.0, epsilon=0.05), lifecycle="retire", retention=dict(min_age=3)),
    "R2": dict(policy=dict(mode="median", prune_factor=10.0, epsilon=0.05), lifecycle="retire",
               retention=dict(min_coverage=3)),
    "R3": dict(policy=dict(mode="median", prune_factor=10.0, epsilon=0.05), lifecycle="dormancy",
               retention=dict(dormancy_first=True, min_dormant_age=3)),
    "R4": dict(policy=dict(mode="lcb"), lifecycle="dormancy", retention=dict(dormancy_first=True, min_dormant_age=3)),
    "C1": dict(policy=dict(mode="median", epsilon=0.05), lifecycle=None, retention={}),
    "C2": dict(policy=dict(mode="lcb"), lifecycle=None, retention={}),
}


# --- integrity ----------------------------------------------------------------
def digest_of(path):
    return hashlib.sha256(Path(path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def committed_unchanged(path):
    """True if `path` is tracked and identical to HEAD (line endings normalized)."""
    rel = Path(path).resolve().relative_to(ROOT).as_posix()
    try:
        head = subprocess.run(["git", "show", f"HEAD:{rel}"], cwd=ROOT, capture_output=True, check=True).stdout
    except subprocess.CalledProcessError:
        return False
    return head.replace(b"\r\n", b"\n") == Path(path).read_bytes().replace(b"\r\n", b"\n")


def verify_frozen(prereg=PREREG, expected=PREREG_SHA256, runner=Path(__file__),
                  amendment=AMENDMENT, amendment_expected=AMENDMENT_SHA256):
    actual = digest_of(prereg)
    if actual != expected:
        raise SystemExit(f"preregistration digest {actual} != {expected}; refusing to run")
    if amendment is not None and digest_of(amendment) != amendment_expected:
        raise SystemExit("preregistration amendment digest changed; refusing to run")
    for path in (prereg, runner) + ((amendment,) if amendment is not None else ()):
        if not committed_unchanged(path):
            raise SystemExit(f"{Path(path).name} is not committed unchanged at HEAD; refusing to run")
    return actual


# --- scoring --------------------------------------------------------------------
def near(cost, oracle):
    return cost <= 1.10 * oracle


def coexistence_exact(rows, retained):
    """Preregistered quantifier: for every context, ONE retained member is near-optimal on a majority."""
    contexts = sorted({r["context"] for r in rows})
    per = {}
    for c in contexts:
        cr = [r for r in rows if r["context"] == c]
        per[c] = any(sum(near(r["costs"][m], min(r["costs"].values())) for r in cr) > len(cr) / 2 for m in retained)
    return per


def specialists(rows):
    out = {}
    for c in sorted({r["context"] for r in rows}):
        cr = [r for r in rows if r["context"] == c]
        tally = {m: sum(1 for r in cr if min(r["costs"], key=r["costs"].get) == m) for m in MEMBERS}
        med = {m: median(r["costs"][m] for r in cr) for m in MEMBERS}
        top = max(tally, key=tally.get)
        if tally[top] > len(cr) / 2 and all(med[top] * 1.10 < med[m] for m in MEMBERS if m != top):
            out[c] = top
    return out


def latency(flags):
    for r in range(len(flags) - 4):
        if all(flags[r:r + 5]):
            return r
    return None


# --- workloads and measurement -------------------------------------------------
def schedule(seed):
    rng = random.Random(seed)
    rows = []
    for name, count, context, rare in SEGMENTS:
        for i in range(count):
            shape = "many-wide" if rng.random() < rare else context
            q, widths = SHAPES[shape]
            data = [rng.randrange(100000) for _ in range(5000)]
            queries = []
            for _ in range(q):
                width = rng.randint(*widths)
                lo = rng.randint(0, 100000 - width)
                queries.append([lo, lo + width])
            rows.append(dict(segment=name, index=i, value={"data": data, "queries": queries}))
    return rows


def run_member(rt, capability, provider, value, budget):
    started = time.perf_counter_ns()
    task = rt.tasks.create_member_task("eco", capability, provider, value, budget, timeout=60)
    output = rt.tasks.run_task(task, rt.tasks.authorize(task, "eco"), "eco")
    e2e = time.perf_counter_ns() - started
    invocation_id = rt.tasks.task(task, "eco")["invocation"]
    invocation = rt.tasks.invocation(invocation_id, "eco")
    return dict(invocation=invocation_id, compute=invocation["compute_ns"], runner_total=invocation["total_ns"],
                e2e=e2e, output=output)


def setup(rt):
    capability = rt.population.define("range-count", "range-batch", "integers", ADMISSION)
    admit_budget = rt.resources.create_budget("eco", {"attempts": 60})
    ids = {}
    for name in MEMBERS:
        ids[name] = rt.registry.register(name)
        rt.population.admit(capability, ids[name], budget=admit_budget, principal="eco")
        rt.population.set_maintenance(capability, ids[name], active=MAINTENANCE[name][0], dormant=MAINTENANCE[name][1])
    execution = rt.resources.create_budget("eco", {"attempts": 20000})
    return capability, ids, execution


def measure_seed(directory, seed, requests):
    path = Path(directory) / f"measured-{seed}.sqlite3"
    with Runtime(path, profile="persistent") as rt:
        capability, ids, execution = setup(rt)
        order = random.Random(seed + 1000)
        table = []
        for row in requests:
            members = list(MEMBERS)
            order.shuffle(members)
            runs = {m: run_member(rt, capability, ids[m], row["value"], execution) for m in members}
            outputs = {json.dumps(r.pop("output")) for r in runs.values()}
            table.append(dict(segment=row["segment"], index=row["index"], context=featurize(row["value"]),
                              agree=len(outputs) == 1, costs={m: runs[m]["compute"] for m in MEMBERS},
                              runner_total={m: runs[m]["runner_total"] for m in MEMBERS},
                              e2e={m: runs[m]["e2e"] for m in MEMBERS},
                              invocation={m: runs[m]["invocation"] for m in MEMBERS}))
        calibration = []
        cal = random.Random(seed + 2000)
        for shape in SHAPES:
            for _ in range(2):
                q, widths = SHAPES[shape]
                data = [cal.randrange(100000) for _ in range(5000)]
                queries = []
                for _ in range(q):
                    width = cal.randint(*widths)
                    lo = cal.randint(0, 100000 - width)
                    queries.append([lo, lo + width])
                value = {"data": data, "queries": queries}
                runs = {m: run_member(rt, capability, ids[m], value, execution) for m in MEMBERS}
                calibration.append(dict(context=shape, costs={m: runs[m]["compute"] for m in MEMBERS}))
    return path, table, calibration


# --- replay one condition on a copy of the measured store -------------------------
def replay(measured, seed, condition, table, workdir):
    spec = CONDITIONS[condition]
    copy = Path(workdir) / f"{condition}-{seed}.sqlite3"
    shutil.copy(measured, copy)
    now = [0.0]
    out = dict(condition=condition, seed=seed, choices=[], transitions=[], assessments=0, assessment_wall_ns=0,
               validation=dict(count=0, compute_ns=0, wall_ns=0, attempts=0), maintenance_units=0,
               exploration=0, population=[])
    with Runtime(copy, profile="persistent", clock=lambda: now[0]) as rt:
        capability = next(c["id"] for c in rt.store.find("capability"))
        ids = {rt.store.get("provider", m["provider"])["implementation"]: m["provider"]
               for m in rt.store.find("member") if m["capability"] == capability}
        if spec["retention"]:
            rt.population.set_retention_policy(capability, **spec["retention"])
        explore = rt.resources.create_budget("eco", {"attempts": 16})
        rt.resources.attach_policy(explore, issued_by="operator", period_seconds=1,
                                   grant={"attempts": 8}, ceiling={"attempts": 24})
        validation = rt.resources.create_budget("eco", {"attempts": 200})
        upkeep = rt.resources.create_budget("eco", {"maintenance": 10 ** 9})
        ctx = development_context(rt)
        eco = EcologyService.create(ctx, capability, ids, min_samples=3, margin=0.10, seed=seed, **spec["policy"])

        def validated(fn, member):
            before = {c["id"] for c in rt.store.find("candidate")}
            started = time.perf_counter_ns()
            result = fn(member, budget=validation, principal="eco")
            out["validation"]["wall_ns"] += time.perf_counter_ns() - started
            for c in rt.store.find("candidate"):
                if c["id"] not in before and c.get("validation_compute_ns") is not None:
                    out["validation"]["count"] += 1
                    out["validation"]["compute_ns"] += c["validation_compute_ns"]
                    out["validation"]["attempts"] += c["validation_attempts"]
            return result

        for i, row in enumerate(table):
            c = row["context"]
            if spec["lifecycle"] and c not in eco.policy.contexts:
                for member in list(eco.policy.dormant):
                    outcome = validated(eco.wake, member)
                    out["transitions"].append(dict(at=i, op="wake", member=member, **outcome))
                for member in list(eco.policy.archived):
                    validated(eco.regenerate, member)
                    out["transitions"].append(dict(at=i, op="regenerate", member=member))
            can = rt.resources.budget(explore, "eco")["available"]["attempts"] >= 1
            member, exploring = eco.choose(c, can)
            if exploring:
                rt.resources.charge(explore, "eco", {"attempts": 1}, "exploration")
                out["exploration"] += 1
            eco.observe(c, member, exploring, row["invocation"][member])
            out["choices"].append(dict(at=i, member=member, exploring=exploring))
            retained = list(eco.policy.members) + list(getattr(eco.policy, "dormant", []))
            out["population"].append(dict(active=len(eco.policy.members), dormant=len(eco.policy.dormant),
                                          retained=sorted(retained)))
            if (i + 1) % PERIOD == 0:
                now[0] += 1
                out["maintenance_units"] += rt.population.maintain(capability, upkeep, "eco",
                                                                   charge=rt.resources.charge)
                if spec["lifecycle"]:
                    review(eco, spec, out, i)
        out["final_retained"] = sorted(list(eco.policy.members) + list(eco.policy.dormant))
        out["final_active"] = sorted(eco.policy.members)
        out["exploration_budget"] = rt.resources.budget(explore, "eco")["available"]
    return out


def review(eco, spec, out, i):
    """At each period boundary: at most one retirement, then dormancy for 'not-best' members."""
    def assessed(member):
        started = time.perf_counter_ns()
        a = eco.assess(member)
        out["assessments"] += 1
        out["assessment_wall_ns"] += time.perf_counter_ns() - started
        return a
    pool = list(eco.policy.dormant) if spec["lifecycle"] == "dormancy" else list(eco.policy.members)
    for member in pool:
        if len(eco.policy.members) <= 1 and member in eco.policy.members:
            continue
        verdict = assessed(member)["verdict"]
        if verdict == "redundant":
            try:
                eco.retire(member, "redundant within margin in every observed context")
                out["transitions"].append(dict(at=i, op="retire", member=member))
                break
            except Refused as exc:            # only population refusals; anything else stops the run
                out["transitions"].append(dict(at=i, op="retire-refused", member=member, reason=str(exc)))
    if spec["lifecycle"] == "dormancy":
        for member in list(eco.policy.members):
            if len(eco.policy.members) <= 1:
                break
            if assessed(member)["verdict"] in ("not-best", "redundant"):
                try:
                    eco.make_dormant(member)
                    out["transitions"].append(dict(at=i, op="dormant", member=member))
                except Refused as exc:
                    out["transitions"].append(dict(at=i, op="dormant-refused", member=member, reason=str(exc)))


def score(run, table):
    costs = [table[c["at"]]["costs"][c["member"]] for c in run["choices"]]
    e2e = [table[c["at"]]["e2e"][c["member"]] for c in run["choices"]]
    oracle = [min(r["costs"].values()) for r in table]
    flags = [near(c, o) for c, o in zip(costs, oracle)]
    segs = {}
    for name, *_ in SEGMENTS:
        idx = [i for i, r in enumerate(table) if r["segment"] == name]
        segs[name] = latency([flags[i] for i in idx])
    retention = [any(near(table[p]["costs"][m], oracle[p]) for m in run["population"][p]["retained"])
                 for p in range(len(table))]
    spec_by_ctx = specialists(table)
    retired = [t["member"] for t in run["transitions"] if t["op"] == "retire"]
    errors = sum(1 for m in retired if m in spec_by_ctx.values())
    compute_ms = sum(costs) / 1e6
    validation_ms = run["validation"]["compute_ns"] / 1e6
    maintenance_ms = run["maintenance_units"] / 1000
    return dict(
        ledgers=dict(compute_ms=round(compute_ms, 3), e2e_ms=round(sum(e2e) / 1e6, 2),
                     organizational=dict(exploration_runs=run["exploration"], validations=run["validation"]["count"],
                                         validation_attempts=run["validation"]["attempts"],
                                         validation_compute_ms=round(validation_ms, 3),
                                         validation_wall_ms=round(run["validation"]["wall_ns"] / 1e6, 2),
                                         assessments=run["assessments"],
                                         assessment_wall_ms=round(run["assessment_wall_ns"] / 1e6, 2),
                                         maintenance_units=run["maintenance_units"])),
        total_cost_ms=round(compute_ms + validation_ms + maintenance_ms, 3),
        regret_ms=round((sum(costs) - sum(oracle)) / 1e6, 3),
        near_optimal_rate=round(sum(flags) / len(flags), 3), adaptation_latency=segs,
        competence_retention=round(sum(retention) / len(retention), 4),
        mean_active=round(sum(p["active"] for p in run["population"]) / len(table), 2),
        mean_dormant=round(sum(p["dormant"] for p in run["population"]) / len(table), 2),
        retirements=retired, retirement_errors=errors, specialists=spec_by_ctx,
        regenerations=sum(1 for t in run["transitions"] if t["op"] == "regenerate"),
        wakes=sum(1 for t in run["transitions"] if t["op"] == "wake"),
        refused=[t for t in run["transitions"] if t["op"].endswith("refused")],
        final_retained=run["final_retained"],
        coexistence=coexistence_exact(table, run["final_retained"]))


def offline_as(table, calibration):
    choice = {c: min(MEMBERS, key=lambda m: median(r["costs"][m] for r in calibration if r["context"] == c))
              for c in SHAPES}
    costs = [r["costs"][choice.get(r["context"], "range_bisect")] for r in table]
    return dict(choice=choice, compute_ms=round(sum(costs) / 1e6, 3),
                calibration_compute_ms=round(sum(sum(r["costs"].values()) for r in calibration) / 1e6, 3),
                regret_ms=round((sum(costs) - sum(min(r["costs"].values()) for r in table)) / 1e6, 3))


def live_check(seed, requests, workdir):
    """B17: R4 executed live (only chosen members run) for one seed; descriptive."""
    spec = CONDITIONS["R4"]
    with Runtime(Path(workdir) / f"live-{seed}.sqlite3", profile="persistent") as rt:
        capability, ids, execution = setup(rt)
        rt.population.set_retention_policy(capability, **spec["retention"])
        explore = rt.resources.create_budget("eco", {"attempts": 24})
        eco = EcologyService.create(development_context(rt), capability, ids, min_samples=3, margin=0.10,
                                    seed=seed, **spec["policy"])
        compute = e2e = 0
        chosen = []
        for row in requests:
            c = featurize(row["value"])
            can = rt.resources.budget(explore, "eco")["available"]["attempts"] >= 1
            member, exploring = eco.choose(c, can)
            if exploring:
                rt.resources.charge(explore, "eco", {"attempts": 1}, "exploration")
            run = run_member(rt, capability, ids[member], row["value"], execution)
            eco.observe(c, member, exploring, run["invocation"])
            compute += run["compute"]
            e2e += run["e2e"]
            chosen.append(member)
    return dict(seed=seed, compute_ms=round(compute / 1e6, 3), e2e_ms=round(e2e / 1e6, 2),
                note="no lifecycle reviews; selection only, to compare live vs replay cost boundaries")


# --- X1b -------------------------------------------------------------------------
PARENTS = {"parse": "parse_csv", "total": "sum", "total_loop": "sum_loop", "count": "count",
           "length": "text_length", "negate": "negate", "double": "double"}
PARENT_CASES = {"parse": [("1,2", [1, 2])], "total": [([1, 2], 3)], "total_loop": [([1, 2], 3)],
                "count": [([1, 2], 2)], "length": [("ab", 2)], "negate": [(3, -3)], "double": [(3, 6)]}
GENERATIONS = [
    ("csv-sum", 2, (("1,2,3", 6), ("10, -4", 6)), [("4,5", 9), ("", 0), ("7", 7)]),
    ("csv-neg-sum", 3, (("1,2,3", -6), ("10, -4", -6)), [("4,5", -9), ("", 0), ("7", -7)]),
    ("csv-neg-double-sum", 4, (("1,2,3", -12), ("10, -4", -12)), [("4,5", -18), ("", 0), ("7", -14)]),
]
REUSE_INPUTS = ["1,2,3", "10,20,30,40", "-5,5", "7"] * 5


def x1b_method(workdir, method):
    with tempfile.TemporaryDirectory(dir=workdir) as d, Runtime(Path(d) / "c.db", profile="persistent") as rt:
        install(rt, PARENTS, PARENT_CASES)
        search_b = rt.resources.create_budget("dev", {"attempts": 4000})
        val_b = rt.resources.create_budget("dev", {"attempts": 800})
        use_b = rt.resources.create_budget("dev", {"attempts": 4000})
        search = CompositionSearch(rt)

        def acquire_all(tag):
            rows = []
            for name, depth, examples, cases in GENERATIONS:
                demand = CapabilityDemand(f"{name}{tag}", "text", "integer", examples,
                                          max_depth=2 if method == "cumulative" else depth,
                                          max_candidates=256, deadline_seconds=60)
                s0 = rt.resources.budget(search_b, "dev")["spent"]["attempts"]
                v0 = rt.resources.budget(val_b, "dev")["spent"]["attempts"]
                result = search.acquire(demand, "dev", search_b, cases, validation_budget=val_b,
                                        cumulative=method == "cumulative",
                                        mode="memoized" if method == "memoized" else "typed")
                rows.append(dict(generation=name, status=result["status"], provider=result.get("provider"),
                                 search=rt.resources.budget(search_b, "dev")["spent"]["attempts"] - s0,
                                 validation=rt.resources.budget(val_b, "dev")["spent"]["attempts"] - v0))
            return rows

        acquired = acquire_all("")
        reuse_attempts = reuse_compute = 0
        for name, *_ in GENERATIONS:
            for value in REUSE_INPUTS:
                task = rt.tasks.create_task("dev", name, value, use_b)
                rt.tasks.run_task(task, rt.tasks.authorize(task, "dev"), "dev")
                invocation = rt.tasks.invocation(rt.tasks.task(task, "dev")["invocation"], "dev")
                reuse_compute += invocation["compute_ns"]
            reuse_attempts = rt.resources.budget(use_b, "dev")["spent"]["attempts"]
        composites = [p for p in rt.registry.population().values() if p["kind"] == "graph"]
        edges = sum(len(p["transitive_dependencies"]) for p in composites)
        sum_provider = rt.manifest()["bindings"]["total"]
        affected, _ = rt.registry.preview_impact([sum_provider], "support")
        rt.registry.record_impact([sum_provider], "support", "X1b: counterexample in sum")
        reacquired = acquire_all("-after-impact")
        return dict(method=method, acquired=acquired, reuse=dict(tasks=len(REUSE_INPUTS) * 3,
                    attempts=reuse_attempts, compute_ms=round(reuse_compute / 1e6, 3)),
                    repertoire=dict(composites=len(composites), dependency_edges=edges),
                    impact=dict(affected=len(affected), reacquired=reacquired))


def run_x1b(workdir):
    results = {m: x1b_method(workdir, m) for m in ("cumulative", "primitive", "memoized")}
    def totals(r):
        return dict(acquire_search=sum(g["search"] for g in r["acquired"]),
                    acquire_validation=sum(g["validation"] for g in r["acquired"]),
                    reacquire_search=sum(g["search"] for g in r["impact"]["reacquired"]),
                    reacquire_validation=sum(g["validation"] for g in r["impact"]["reacquired"]))
    summary = {m: dict(totals(r), all_acquired=all(g["status"] == "ACQUIRED" for g in r["acquired"]),
                       reacquired_all=all(g["status"] == "ACQUIRED" for g in r["impact"]["reacquired"]),
                       reuse=r["reuse"], repertoire=r["repertoire"], impact_affected=r["impact"]["affected"])
               for m, r in results.items()}
    return dict(methods=results, summary=summary,
                hypotheses={"Y1": dict(passed=all(s["all_acquired"] for s in summary.values()))})


# --- X2c driver and hypotheses ----------------------------------------------------------
def run_x2c(workdir, seeds):
    per_seed = {}
    for seed in seeds:
        requests = schedule(seed)
        measured, table, calibration = measure_seed(workdir, seed, requests)
        scores = {c: score(replay(measured, seed, c, table, workdir), table) for c in CONDITIONS}
        oracle_ms = round(sum(min(r["costs"].values()) for r in table) / 1e6, 3)
        per_seed[seed] = dict(scores=scores, offline_as=offline_as(table, calibration), oracle_ms=oracle_ms,
                              agree=all(r["agree"] for r in table), table=table, calibration=calibration)
        if seed == seeds[0]:
            per_seed[seed]["live_r4"] = live_check(seed, requests, workdir)
    s = lambda seed, c: per_seed[seed]["scores"][c]
    n, need = len(seeds), max(1, len(seeds) - 1)
    hyp = {
        "X2c-H1": dict(passed=sum(s(x, "R3")["retirement_errors"] for x in seeds) < sum(s(x, "R0")["retirement_errors"] for x in seeds)
                       and sum(s(x, "R4")["retirement_errors"] for x in seeds) < sum(s(x, "R0")["retirement_errors"] for x in seeds)),
        "X2c-H2": dict(passed=all(s(x, c)["competence_retention"] == 1.0 for x in seeds for c in ("R3", "R4"))),
        "X2c-H3": dict(passed=sum(s(x, "R4")["total_cost_ms"] <= s(x, "R0")["total_cost_ms"] for x in seeds) >= need),
        "X2c-H4": dict(passed=sum(s(x, "R4")["total_cost_ms"] <= 1.10 * s(x, "C2")["total_cost_ms"] for x in seeds) >= need),
        "X2c-H5": dict(passed=sum(max((v if v is not None else 10 ** 6) for v in s(x, "R4")["adaptation_latency"].values()) <= 15
                                  for x in seeds) >= need),
        "X2c-H6": dict(passed=all(len(s(x, c)["final_retained"]) >= 3 and all(s(x, c)["coexistence"].values())
                                  for x in seeds for c in ("R3", "R4"))),
    }
    return dict(seeds=list(seeds), per_seed=per_seed, hypotheses=hyp, n=n)


def corrected_coexistence():
    """B18: rescore v1/v2 X2-H1 with the exact preregistered quantifier; originals untouched."""
    out = {}
    base = ROOT / "docs" / "results" / "2026-11-25T-ecology"
    for v in ("v1", "v2"):
        x = json.loads((base / f"experiment-results-{v}.json").read_text(encoding="utf-8"))["x2"]
        active = x["active_members"]
        per = coexistence_exact(x["table"], active)
        out[v] = dict(active=active, per_context=per, exact_passed=len(active) >= 3 and all(per.values()),
                      originally_reported=x["hypotheses"]["X2-H1" if v == "v1" else "X2b-H1"]["passed"])
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("out")
    parser.add_argument("--seeds", default=",".join(map(str, SEEDS)))
    parser.add_argument("--quick", action="store_true", help="tests only: tiny schedule, not a result")
    args = parser.parse_args()
    seeds = tuple(int(x) for x in args.seeds.split(","))
    digest = None if args.quick else verify_frozen()
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    work = ROOT / ".brainos" / "results" / (out.name + ("-quick" if args.quick else ""))
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    started = time.time()
    if args.quick:
        global SEGMENTS
        SEGMENTS = [(n, 2, c, r) for n, _, c, r in SEGMENTS]
        x2c = run_x2c(work, seeds)
        print(json.dumps(x2c["hypotheses"]))
        return
    corrections = corrected_coexistence()
    (out / "coexistence-correction.json").write_text(json.dumps(corrections, indent=1), encoding="utf-8")
    x1b = run_x1b(work)
    x2c = run_x2c(work, seeds)
    result = dict(preregistration_sha256=digest, amendment_sha256=AMENDMENT_SHA256, run=2, commit=subprocess.check_output(["git", "rev-parse", "HEAD"],
                  cwd=ROOT, text=True).strip(), started=started, seconds=round(time.time() - started, 1),
                  python=sys.version.split()[0], x1b=x1b, x2c=x2c)
    (out / "experiment-results.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    brief = dict(x1b_summary=x1b["summary"], x1b_hypotheses=x1b["hypotheses"], x2c_hypotheses=x2c["hypotheses"],
                 x2c=({str(seed): dict({c: {k: v for k, v in sc.items() if k not in ("specialists",)}
                                          for c, sc in d["scores"].items()},
                                         offline_as=d["offline_as"], oracle_ms=d["oracle_ms"], agree=d["agree"],
                                         live_r4=d.get("live_r4"))
                       for seed, d in x2c["per_seed"].items()}),
                 specialists={str(seed): next(iter(d["scores"].values()))["specialists"]
                              for seed, d in x2c["per_seed"].items()},
                 coexistence_correction=corrections)
    (out / "experiment-brief.json").write_text(json.dumps(brief, indent=1, default=str), encoding="utf-8")
    print(json.dumps(dict(x1b=x1b["summary"], x1b_h=x1b["hypotheses"], x2c_h=x2c["hypotheses"]), indent=1))


if __name__ == "__main__":
    main()
