"""Run the preregistered experiments X1 (cumulative construction) and X2 (ecology).

    py tools/run_ecology.py docs/results/2026-11-25T-ecology

Refuses to run if PREREGISTRATION.md differs from the digest recorded here.
Everything executes through BrainOS (permits, budgets, population, tasks).
"""
from pathlib import Path
import hashlib
import json
import random
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from brainos import Runtime  # noqa: E402
from brainos.__main__ import install  # noqa: E402
from brainos.development import CapabilityDemand, CompositionSearch  # noqa: E402
from brainos import ecology  # noqa: E402

PREREG = ROOT / "docs" / "results" / "2026-11-25T-ecology" / "PREREGISTRATION.md"
PREREG_SHA256 = "dba29c04e4f09759ec6e95149df203e5cb07f6881841685f4caa1eb07eca8876"
PREREG_V2 = PREREG.with_name("PREREGISTRATION-v2.md")
PREREG_V2_SHA256 = "93af226e0da0e3ffeb902dce92b5325316f105993dbdcd6747b097a09bd8f5b0"


def prereg_digest(path):
    return hashlib.sha256(Path(path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def verify_preregistration(path=PREREG, expected=PREREG_SHA256):
    actual = prereg_digest(path)
    if actual != expected:
        raise SystemExit(f"preregistration changed ({actual} != {expected}); refusing to run")
    return actual


# --- X1 -------------------------------------------------------------------
PARENTS = {"parse": "parse_csv", "total": "sum", "total_loop": "sum_loop", "count": "count",
           "length": "text_length", "negate": "negate", "double": "double"}
PARENT_CASES = {"parse": [("1,2", [1, 2])], "total": [([1, 2], 3)], "total_loop": [([1, 2], 3)],
                "count": [([1, 2], 2)], "length": [("ab", 2)], "negate": [(3, -3)], "double": [(3, 6)]}
GENERATIONS = [
    ("csv-sum", (("1,2,3", 6), ("10, -4", 6)), [("4,5", 9), ("", 0), ("7", 7)]),
    ("csv-neg-sum", (("1,2,3", -6), ("10, -4", -6)), [("4,5", -9), ("", 0), ("7", -7)]),
    ("csv-neg-double-sum", (("1,2,3", -12), ("10, -4", -12)), [("4,5", -18), ("", 0), ("7", -14)]),
]


def _x1_condition(root, generations, *, cumulative, depth, candidates=32, mode="typed"):
    rows = []
    with tempfile.TemporaryDirectory(dir=root) as d, Runtime(Path(d) / "c.db", profile="persistent") as rt:
        install(rt, PARENTS, PARENT_CASES)
        search_budget = rt.resources.create_budget("dev", {"attempts": 2000})
        validation_budget = rt.resources.create_budget("dev", {"attempts": 400})
        search = CompositionSearch(rt)
        for name, examples, cases in generations:
            demand = CapabilityDemand(name, "text", "integer", examples, max_depth=depth,
                                      max_candidates=candidates, deadline_seconds=60)
            started = time.perf_counter()
            result = search.acquire(demand, "dev", search_budget, cases, validation_budget=validation_budget,
                                    cumulative=cumulative, mode=mode)
            run = rt.store.get("construction-run", result["run"])
            rows.append(dict(generation=name, status=result["status"],
                             path=[p.split(":")[0] if not p.startswith("graph:") else p[:18] for p in result.get("path", [])],
                             provider=result.get("provider"), raw_path=result.get("path", []),
                             search_attempts=run.get("search", {}).get("attempts"),
                             expanded=run.get("search", {}).get("expanded"),
                             validation_attempts=run.get("validation_attempts"),
                             seconds=round(time.perf_counter() - started, 3)))
    return rows


def run_x1(root):
    out = dict(
        cumulative=_x1_condition(root, GENERATIONS, cumulative=True, depth=2),
        primitive_depth2=_x1_condition(root, GENERATIONS, cumulative=False, depth=2),
        primitive_depth4=_x1_condition(root, GENERATIONS[2:], cumulative=False, depth=4, candidates=256),
        memoized_depth4=_x1_condition(root, GENERATIONS[2:], cumulative=False, depth=4, candidates=256,
                                      mode="memoized"))
    cum = out["cumulative"]
    h1 = (all(r["status"] == "ACQUIRED" for r in cum)
          and cum[1]["raw_path"] and cum[1]["raw_path"][0] == cum[0]["provider"]
          and cum[2]["raw_path"] and cum[2]["raw_path"][0] == cum[1]["provider"])
    h2 = [r["status"] for r in out["primitive_depth2"][1:]] == ["NON_ATTAINMENT", "NON_ATTAINMENT"]
    total = lambda rows: sum((r["search_attempts"] or 0) for r in rows)
    out["hypotheses"] = {
        "X1-H1": dict(passed=bool(h1)), "X1-H2": dict(passed=h2),
        "X1-H3": dict(descriptive=True,
                      cumulative_g3_marginal_search=cum[2]["search_attempts"],
                      cumulative_total_search=total(cum),
                      cumulative_total_validation=sum((r["validation_attempts"] or 0) for r in cum),
                      primitive_depth4_g3_search=out["primitive_depth4"][0]["search_attempts"],
                      memoized_depth4_g3_search=out["memoized_depth4"][0]["search_attempts"])}
    return out


# --- X2 -------------------------------------------------------------------
MEMBERS = ["range_scan", "range_scan_list", "range_bisect", "range_hash"]
ADMISSION = [({"data": [1, 5, 9], "queries": [[0, 5]]}, [2]), ({"data": [], "queries": [[0, 1]]}, [0]),
             ({"data": [3, 3, 7], "queries": [[3, 3], [4, 8]]}, [2, 1])]
PHASES = [("P1", 30, 1, (20000, 60000)), ("P2", 30, 400, (0, 4)),
          ("P3", 30, 400, (1000, 3000)), ("P4", 30, 1, (20000, 60000))]


def workload(rng, queries, widths):
    data = [rng.randrange(100000) for _ in range(5000)]
    qs = []
    for _ in range(queries):
        width = rng.randint(*widths)
        lo = rng.randint(0, 100000 - width)
        qs.append([lo, lo + width])
    return {"data": data, "queries": qs}


def measure(rt, capability, members, budget, value, order_rng):
    order = list(members)
    order_rng.shuffle(order)
    costs, totals, outputs = {}, {}, {}
    for member in order:
        task = rt.tasks.create_member_task("eco", capability, member, value, budget, timeout=60)
        outputs[member] = rt.tasks.run_task(task, rt.tasks.authorize(task, "eco"), "eco")
        invocation = rt.tasks.invocation(rt.tasks.task(task, "eco")["invocation"], "eco")
        costs[member], totals[member] = invocation["compute_ns"], invocation["total_ns"]
    agree = len({json.dumps(v) for v in outputs.values()}) == 1
    return costs, totals, agree


def near_optimal(cost, oracle):
    return cost <= 1.10 * oracle


def latency(flags):
    for r in range(len(flags) - 4):
        if all(flags[r:r + 5]):
            return r
    return None


def run_x2(root, v2=False):
    now = [0.0]
    with tempfile.TemporaryDirectory(dir=root) as d, \
            Runtime(Path(d) / "c.db", profile="persistent", clock=lambda: now[0]) as rt:
        capability = rt.population.define("range-count", "range-batch", "integers", ADMISSION)
        validation = rt.resources.create_budget("eco", {"attempts": 60})
        ids = {}
        for name in MEMBERS:
            ids[name] = rt.registry.register(name)
            rt.population.admit(capability, ids[name], budget=validation, principal="eco")
        by_id = {v: k for k, v in ids.items()}
        execution = rt.resources.create_budget("eco", {"attempts": 5000})
        explore = rt.resources.create_budget("eco", {"attempts": 16})
        rt.resources.attach_policy(explore, issued_by="operator", period_seconds=1,
                                   grant={"attempts": 16}, ceiling={"attempts": 24})
        order_rng = random.Random(5)

        # Calibration (for static / offline-AS only).
        cal_rng, calibration = random.Random(7), []
        for _, _, q, widths in PHASES[:3]:
            for _ in range(4):
                value = workload(cal_rng, q, widths)
                costs, _, agree = measure(rt, capability, ids.values(), execution, value, order_rng)
                calibration.append(dict(context=ecology.featurize(value), agree=agree,
                                        costs={by_id[k]: v for k, v in costs.items()}))
        # Measured table for all phases.
        rng, table = random.Random(2026), []
        for phase, count, q, widths in PHASES:
            for i in range(count):
                value = workload(rng, q, widths)
                costs, totals, agree = measure(rt, capability, ids.values(), execution, value, order_rng)
                table.append(dict(phase=phase, index=i, context=ecology.featurize(value), agree=agree,
                                  costs={by_id[k]: v for k, v in costs.items()},
                                  totals={by_id[k]: v for k, v in totals.items()}))

        # Replay policies.
        static = ecology.static_choice(calibration)
        offline = ecology.offline_selection(calibration)
        calibration_cost = sum(sum(r["costs"].values()) for r in calibration)
        current = lambda member, revision: rt.fabric.evidence_current(ids[member], revision)
        prune = 10.0 if v2 else None
        eco = ecology.EcologyPolicy(MEMBERS, min_samples=3, margin=0.10, epsilon=0.05, seed=11, current=current,
                                    prune_factor=prune)
        naive = ecology.EcologyPolicy(MEMBERS, min_samples=3, margin=0.10, epsilon=0.05, seed=11, prune_factor=prune)
        regenerations, regeneration_ms = [], 0.0
        naive_explore = [16]
        choices = {k: [] for k in ("ecology", "aggregate-retire", "static", "offline-AS", "portfolio", "oracle")}
        retirements, revision = [], rt.manifest()["evidence_revision"]
        for p, (phase, *_rest) in enumerate(PHASES):
            if p:
                now[0] += 1          # one funding period per phase
                naive_explore[0] = min(24, naive_explore[0] + 16)
            for row in (r for r in table if r["phase"] == phase):
                c, costs = row["context"], row["costs"]
                oracle = min(costs.values())
                if v2 and eco.is_new(c) and eco.archived:
                    for member in list(eco.archived):
                        spent = rt.resources.budget(validation, "eco")["spent"]["attempts"]
                        started = time.perf_counter()
                        rt.population.restore(capability, ids[member], budget=validation, principal="eco")
                        elapsed = (time.perf_counter() - started) * 1000
                        regeneration_ms += elapsed
                        eco.restore(member)
                        regenerations.append(dict(phase=phase, context=c, member=member, wall_ms=round(elapsed, 2),
                            validation_attempts=rt.resources.budget(validation, "eco")["spent"]["attempts"] - spent))
                can = rt.resources.budget(explore, "eco")["available"]["attempts"] >= 1
                member, exploring = eco.select(c, can)
                if exploring:
                    rt.resources.charge(explore, "eco", {"attempts": 1}, "exploration")
                eco.observe(c, member, costs[member], revision)
                m2, ex2 = naive.select(c, naive_explore[0] >= 1)
                naive_explore[0] -= int(ex2)
                naive.observe(c, m2, costs[m2])
                choices["ecology"].append((phase, c, costs[member], oracle, member, exploring))
                choices["aggregate-retire"].append((phase, c, costs[m2], oracle, m2, ex2))
                s = costs[static]
                choices["static"].append((phase, c, s, oracle, static, False))
                o = offline.get(c, static)
                choices["offline-AS"].append((phase, c, costs[o], oracle, o, False))
                choices["portfolio"].append((phase, c, sum(costs.values()), oracle, "all", False))
                choices["oracle"].append((phase, c, oracle, oracle, min(costs, key=costs.get), False))
            candidate = eco.retirement_candidate()
            if candidate is not None:
                rt.population.retire(capability, ids[candidate["member"]],
                                     reason="redundant within margin in every observed context", evidence=candidate)
                eco.retire(candidate["member"])
                retirements.append(dict(after=phase, member=candidate["member"], evidence=candidate))
            if phase == "P3":
                kept, dropped = ecology.aggregate_retirement(naive, keep=2)
                naive.members = kept
                retirements.append(dict(after=phase, policy="aggregate-retire", kept=kept, dropped=dropped))

        def summarize(rows):
            out = {}
            for phase, *_ in PHASES:
                pr = [r for r in rows if r[0] == phase]
                flags = [near_optimal(r[2], r[3]) for r in pr]
                out[phase] = dict(cost_ms=round(sum(r[2] for r in pr) / 1e6, 2),
                                  regret_ms=round(sum(r[2] - r[3] for r in pr) / 1e6, 2),
                                  near_optimal_rate=round(sum(flags) / len(flags), 3),
                                  adaptation_latency=latency(flags),
                                  explorations=sum(1 for r in pr if r[5]))
            out["total_cost_ms"] = round(sum(r[2] for r in rows) / 1e6, 2)
            return out
        summary = {k: summarize(v) for k, v in choices.items()}
        summary["ecology"]["regeneration_ms"] = round(regeneration_ms, 2)
        summary["ecology"]["total_including_regeneration_ms"] = round(summary["ecology"]["total_cost_ms"]
                                                                      + regeneration_ms, 2)
        summary["static"]["calibration_cost_ms"] = summary["offline-AS"]["calibration_cost_ms"] = \
            round(calibration_cost / 1e6, 2)
        summary["static"]["choice"] = static
        summary["offline-AS"]["choice"] = offline

        # Specialists and per-context winners from the full measured table.
        contexts = sorted({r["context"] for r in table})
        winners = {}
        for c in contexts:
            rows = [r for r in table if r["context"] == c]
            tally = {m: 0 for m in MEMBERS}
            for r in rows:
                tally[min(r["costs"], key=r["costs"].get)] += 1
            from statistics import median
            med = {m: median(r["costs"][m] for r in rows) for m in MEMBERS}
            top = max(tally, key=tally.get)
            specialist = tally[top] > len(rows) / 2 and all(med[top] * 1.10 < med[m] for m in MEMBERS if m != top)
            winners[c] = dict(majority_best=top, wins=tally, median_ms={m: round(v / 1e6, 3) for m, v in med.items()},
                              specialist=specialist)
        active = [m["provider"] for m in rt.population.members(capability)]
        active_names = sorted(by_id[a] for a in active)
        retired = [r["member"] for r in retirements if "member" in r]
        h1 = len(active_names) >= 3 and all(
            sum(near_optimal(min(r["costs"][m] for m in active_names), min(r["costs"].values()))
                for r in table if r["context"] == c) > sum(1 for r in table if r["context"] == c) / 2
            for c in contexts)
        h2 = not any(winners[c]["specialist"] and winners[c]["majority_best"] in retired for c in contexts)
        h3 = summary["ecology"]["P4"]["cost_ms"] <= 0.8 * summary["aggregate-retire"]["P4"]["cost_ms"]
        h4 = all(summary["ecology"][p]["adaptation_latency"] is not None
                 and summary["ecology"][p]["adaptation_latency"] <= 15 for p, *_ in PHASES)
        retired_refused = None
        if retired:
            try:
                rt.tasks.create_member_task("eco", capability, ids[retired[0]], ADMISSION[0][0], execution)
                retired_refused = False
            except Exception:
                retired_refused = True
        return dict(
            variant="v2" if v2 else "v1", regenerations=regenerations,
            correctness=dict(all_members_agree=all(r["agree"] for r in table + calibration)),
            contexts=winners, summary=summary, retirements=retirements, active_members=active_names,
            retired_member_task_refused=retired_refused,
            exploration_budget=rt.resources.budget(explore, "eco"),
            execution_budget_spent=rt.resources.budget(execution, "eco")["spent"],
            hypotheses={f"{'X2b' if v2 else 'X2'}-H{i}": value for i, value in enumerate(
                (dict(passed=h1), dict(passed=h2), dict(passed=h3), dict(passed=h4), dict(descriptive=True)), 1)},
            table=table, calibration=calibration)


def main():
    v2 = "--v2" in sys.argv[1:]
    args = [a for a in sys.argv[1:] if a != "--v2"]
    digest = verify_preregistration(PREREG_V2, PREREG_V2_SHA256) if v2 else verify_preregistration()
    out = Path(args[0]).resolve()
    out.mkdir(parents=True, exist_ok=True)
    work = ROOT / ".brainos" / "results" / out.name
    work.mkdir(parents=True, exist_ok=True)
    started = time.time()
    x1 = None if v2 else run_x1(work)
    x2 = run_x2(work, v2=v2)
    suffix = "v2" if v2 else "v1"
    result = dict(preregistration_sha256=digest, started=started, seconds=round(time.time() - started, 1),
                  python=sys.version.split()[0], x1=x1, x2=x2)
    (out / f"experiment-results-{suffix}.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    brief = dict(x2_hypotheses=x2["hypotheses"], x2_summary=x2["summary"], x2_contexts=x2["contexts"],
                 x2_active=x2["active_members"], x2_regenerations=x2["regenerations"],
                 x2_retirements=[{k: v for k, v in r.items() if k != "evidence"} for r in x2["retirements"]],
                 x2_correct=x2["correctness"], retired_refused=x2["retired_member_task_refused"])
    if x1:
        brief = dict(x1={k: v for k, v in x1.items() if k != "hypotheses"}, x1_hypotheses=x1["hypotheses"], **brief)
    text = json.dumps(brief, indent=1, default=str)
    (out / f"experiment-brief-{suffix}.json").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
