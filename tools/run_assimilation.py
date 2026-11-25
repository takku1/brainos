"""Preregistered X3: bounded assimilation (docs/results/2026-11-25T-assimilation).

    py tools/run_assimilation.py docs/results/2026-11-25T-assimilation [--quick]

Refuses to run unless PREREGISTRATION.md and this file are committed unchanged
at HEAD and the preregistration matches the embedded digest. `--quick` runs a
tiny, different configuration for harness checks only; it is never a result.
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
from brainos import providers  # noqa: E402
from brainos.assimilation import AssimilationSearch, EvaluationSet, Gate  # noqa: E402

RESULTS = ROOT / "docs" / "results" / "2026-11-25T-assimilation"
PREREG = RESULTS / "PREREGISTRATION.md"
PREREG_SHA256 = "293679fad3d016dfaca62e199b76e210c2ed978fd34a692071d85c45c1352018"

SEEDS = (201, 202, 203, 204, 205)
EXACT_CASES = [({"data": [1, 5, 5, 9], "queries": [5, 2]}, [2, 0]), ({"data": [], "queries": [1]}, [0])]
RANGE_CASES = [({"data": [1, 5, 9], "queries": [[0, 5]]}, [2]), ({"data": [3, 3, 7], "queries": [[3, 3]]}, [2])]
TOTAL_CASES = [({"data": [1, 5, 5, 9], "queries": [5, 9]}, 3)]
ELIGIBLE = {"exact": ["exact_hash", "exact_dict", "exact_sorted", "exact_scan"],
            "range": ["range_sorted", "range_hash_index", "range_scan_staged"]}
CONFIG = dict(n=5000, span=100000, observe_epochs=4, post_epochs=30, requests=4,
              horizon=50.0, resolution_ns=20_000.0, maintenance_ns_per_byte_epoch=1.0, upkeep_ns=50_000.0)
SCENARIOS = {
    "SA-exact-redundancy": dict(parents=["exact_hash", "exact_dict"], caps=["exact"], roles={"exact": "exact_hash"},
                                composite=False, exact_keys=200, range_queries=0, widths=(0, 0),
                                tolerance={"exact": 1.5}),
    "SB-partial-overlap": dict(parents=["exact_hash", "range_sorted"], caps=["exact", "range"],
                               roles={"exact": "exact_hash", "range": "range_sorted"}, composite=True,
                               exact_keys=50, range_queries=50, widths=(10, 2000),
                               tolerance={"exact": 3.0, "range": 1.25}),
    "SC-incompatible": dict(parents=["exact_hash", "range_sorted"], caps=["exact", "range"],
                            roles={"exact": "exact_hash", "range": "range_sorted"}, composite=True,
                            exact_keys=2000, range_queries=50, widths=(2000, 4000),
                            tolerance={"exact": 1.25, "range": 1.25}),
}


# --- integrity ---------------------------------------------------------------------
def digest_of(path):
    return hashlib.sha256(Path(path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def committed_unchanged(path):
    rel = Path(path).resolve().relative_to(ROOT).as_posix()
    try:
        head = subprocess.run(["git", "show", f"HEAD:{rel}"], cwd=ROOT, capture_output=True, check=True).stdout
    except subprocess.CalledProcessError:
        return False
    return head.replace(b"\r\n", b"\n") == Path(path).read_bytes().replace(b"\r\n", b"\n")


def verify_frozen(prereg=PREREG, expected=PREREG_SHA256, runner=Path(__file__)):
    actual = digest_of(prereg)
    if actual != expected:
        raise SystemExit(f"preregistration digest {actual} != {expected}; refusing to run")
    for path in (prereg, runner):
        if not committed_unchanged(path):
            raise SystemExit(f"{Path(path).name} is not committed unchanged at HEAD; refusing to run")
    return actual


# --- workloads ------------------------------------------------------------------------
def epoch_requests(rng, sc, kind="observed"):
    n, span = CONFIG["n"], CONFIG["span"]
    data = [rng.randrange(span) for _ in range(n)]
    out = []
    for _ in range(CONFIG["requests"]):
        if "exact" in sc["caps"]:
            keys = sc["exact_keys"] if kind != "rare" else max(1, sc["exact_keys"] // 10)
            out.append(("exact", {"data": data, "queries": [rng.randrange(span) for _ in range(keys)]}))
        if "range" in sc["caps"]:
            lo_w, hi_w = sc["widths"] if kind != "rare" else (0, 1)
            qs = []
            for _ in range(sc["range_queries"]):
                width = rng.randint(lo_w, hi_w)
                lo = rng.randint(0, span - width)
                qs.append([lo, lo + width])
            out.append(("range", {"data": data, "queries": qs}))
    return out


def build_org(rt, sc):
    budget = rt.resources.create_budget("dev", {"attempts": 200000})
    caps = {"exact": rt.population.define("exact-count", "exact-batch", "integers", EXACT_CASES),
            "range": rt.population.define("range-count", "range-batch", "integers", RANGE_CASES)}
    ids = {n: rt.registry.register(n) for c in ELIGIBLE.values() for n in c}
    ids["sum"] = rt.registry.register("sum")
    for name in sc["parents"]:
        cap = "exact" if name.startswith("exact") else "range"
        rt.population.admit(caps[cap], ids[name], budget=budget, principal="dev")
    roles = {role: ids[name] for role, name in sc["roles"].items()}
    role_cases = {"exact": EXACT_CASES, "range": RANGE_CASES}
    c = rt.transactor.stage(roles)
    rt.transactor.validate(c, {r: role_cases[r] for r in roles}, budget=budget, principal="dev")
    rt.transactor.commit(c)
    if sc["composite"]:
        graph = dict(input="exact-batch", output="integer", output_node="n1",
                     nodes=[dict(id="n0", provider=ids["exact_hash"], input="$input"),
                            dict(id="n1", provider=ids["sum"], input="n0")])
        total = rt.registry.register_graph(graph, "exact-total")
        c = rt.transactor.stage({"exact-total": total})
        rt.transactor.validate(c, {"exact-total": TOTAL_CASES}, budget=budget, principal="dev")
        rt.transactor.commit(c)
        role_cases["exact-total"] = TOTAL_CASES
    parents = [dict(capability=caps["exact" if n.startswith("exact") else "range"], provider=ids[n])
               for n in sc["parents"]]
    return budget, caps, ids, parents, role_cases


# --- measured table for post-publication replay -------------------------------------------
def measure_table(rt, sc, epochs, ids):
    """Per epoch: cold prepare per structure kind (once), then warm answers for every eligible provider."""
    table = []
    for requests in epochs:
        rt.runner.clear_prepared()
        prepared = {}
        rows = []
        for cap, value in requests:
            runs = {}
            for name in ELIGIBLE[cap]:
                spec = rt.registry.resolve(ids[name])
                timing = []
                out = rt.runner.compute(spec, value, 120, on_timing=timing.append)
                t = timing[-1]
                if spec["prepare"] is not None and spec["prepare"] not in prepared:
                    prepared[spec["prepare"]] = dict(prepare_ns=t["prepare_ns"], bytes=t["state_bytes"])
                runs[name] = dict(answer_ns=t["answer_ns"], output=providers_digest(out),
                                  prepare=spec["prepare"], total_ns=t["total_ns"])
            rows.append(dict(capability=cap, runs=runs))
        table.append(dict(rows=rows, prepared=prepared))
    return table


def providers_digest(value):
    from brainos.contracts import digest
    return digest(value)


def policy_cost(table, choose, maintained, upkeep):
    """choose(epoch_index, cap) -> provider name; returns per-epoch compute-boundary costs."""
    out = []
    for e, epoch in enumerate(table):
        answer = kinds = 0
        used = set()
        for row in epoch["rows"]:
            name = choose(e, row["capability"])
            answer += row["runs"][name]["answer_ns"]
            if row["runs"][name]["prepare"]:
                used.add(row["runs"][name]["prepare"])
        prepare = sum(epoch["prepared"][k]["prepare_ns"] for k in used)
        state = sum(epoch["prepared"][k]["bytes"] for k in used)
        cost = answer + prepare + state * CONFIG["maintenance_ns_per_byte_epoch"] + upkeep * maintained
        out.append(dict(answer_ns=answer, prepare_ns=prepare, state_bytes=state, upkeep_ns=upkeep * maintained,
                        total_ns=cost))
    return out


def best_static(table, names_by_cap):
    """Per-capability provider with the lowest answer cost in an epoch set (state-unaware)."""
    return {c: min(names, key=lambda n: sum(r["runs"][n]["answer_ns"] for ep in table for r in ep["rows"]
                                           if r["capability"] == c)) for c, names in names_by_cap.items()}


def shared_state_greedy(table, caps, upkeep):
    """Conventional shared-state optimization: each epoch pick the assignment minimizing the
    previous epoch's full cost (first epoch: cheapest answers)."""
    from itertools import product
    combos = list(product(*[ELIGIBLE[c] for c in caps]))
    choices = []
    for e in range(len(table)):
        if e == 0:
            pick = best_static(table[:1], {c: ELIGIBLE[c] for c in caps})
        else:
            prev = table[e - 1:e]
            def cost(combo):
                mapping = dict(zip(caps, combo))
                return policy_cost(prev, lambda _e, c: mapping[c], 0, 0)[0]["total_ns"]
            pick = dict(zip(caps, min(combos, key=cost)))
        choices.append(pick)
    return choices


# --- one scenario on one seed ------------------------------------------------------------------
def run_scenario(workdir, name, seed, quick=False):
    sc = SCENARIOS[name]
    rng = random.Random(seed)
    path = Path(workdir) / f"{name}-{seed}.sqlite3"
    out = dict(scenario=name, seed=seed)
    with Runtime(path, profile="persistent") as rt:
        budget, caps, ids, parents, role_cases = build_org(rt, sc)
        names = {v: k for k, v in ids.items()}
        observe = [epoch_requests(rng, sc) for _ in range(CONFIG["observe_epochs"])]
        held = epoch_requests(random.Random(seed + 7000), sc, "held-out")
        rare = epoch_requests(random.Random(seed + 9000), sc, "rare")
        epochs = [[(caps[c], v, "observed") for c, v in ep] for ep in observe]
        epochs.append([(caps[c], v, "held-out") for c, v in held])
        epochs.append([(caps[c], v, "rare") for c, v in rare])
        dependents = {"exact-total": [v for ep in epochs for c, v, _ in ep if c == caps["exact"]]} if sc["composite"] else {}
        gate = Gate(tolerance={caps[c]: t for c, t in sc["tolerance"].items()}, horizon_epochs=CONFIG["horizon"],
                    maintenance_ns_per_byte_epoch=CONFIG["maintenance_ns_per_byte_epoch"],
                    resolution_ns=CONFIG["resolution_ns"], upkeep_ns_per_provider_epoch=CONFIG["upkeep_ns"])
        search = AssimilationSearch(rt)
        nominated, controls = search.nominate(parents)
        verdicts = []
        for candidate in nominated:
            v = search.evaluate(candidate, parents, EvaluationSet(epochs=epochs, dependents=dependents), gate,
                                budget=budget, principal="dev")
            verdicts.append({k: v[k] for k in ("accepted", "reasons", "implementations", "method", "latency_ratio",
                                               "mismatches", "mean_savings_ns", "upkeep_saving_ns", "construction_ns",
                                               "break_even_epochs", "state_bytes_before", "state_bytes_after",
                                               "evaluation_wall_ns")} | dict(_full=v))
        accepted = [v for v in verdicts if v["accepted"]]
        # Deterministic choice among accepted: largest predicted per-epoch saving.
        chosen = max(accepted, key=lambda v: v["mean_savings_ns"]) if accepted else None
        out.update(nominated=len(nominated), evaluated=[{k: v for k, v in x.items() if k != "_full"} for x in verdicts],
                   accepted=chosen is not None, chosen=chosen and {k: v for k, v in chosen.items() if k != "_full"})
        construction_ns = sum(v["construction_ns"] for v in verdicts)
        publication = dict(validation_compute_ns=0, wall_ns=0)
        if chosen:
            before = {c["id"] for c in rt.store.find("candidate")}
            started = time.perf_counter_ns()
            aid = search.publish(chosen["_full"], parents, role_cases, budget=budget, principal="dev")
            publication["wall_ns"] = time.perf_counter_ns() - started
            publication["validation_compute_ns"] = sum(c.get("validation_compute_ns", 0) for c in rt.store.find("candidate")
                                                       if c["id"] not in before)
            publication["assimilation"] = aid
            publication["bindings"] = {r: names.get(p, p) for r, p in rt.manifest()["bindings"].items()}
        out["construction_compute_ns"] = construction_ns
        out["publication"] = publication
        # Post-publication horizon: measured table, replayed policies.
        post_rng = random.Random(seed + 1)
        post = [epoch_requests(post_rng, sc) for _ in range(CONFIG["post_epochs"])]
        table = measure_table(rt, sc, post, ids)
        parent_names = sc["parents"]
        by_cap_parents = {c: [n for n in parent_names if n.startswith(c)] for c in sc["caps"]}
        obs_table = measure_table(rt, sc, observe, ids)
        o_choice = best_static(obs_table, by_cap_parents)
        r_choice = best_static(obs_table, {c: ELIGIBLE[c] for c in sc["caps"]})
        all_eligible = sum(len(ELIGIBLE[c]) for c in sc["caps"])
        upkeep = CONFIG["upkeep_ns"]
        policies = {
            "originals": policy_cost(table, lambda e, c: o_choice[c], len(parent_names), upkeep),
            "wrapper": policy_cost(table, lambda e, c: o_choice[c], len(parent_names) + 1, upkeep),
            "routing": policy_cost(table, lambda e, c: r_choice[c], all_eligible, upkeep),
        }
        greedy = shared_state_greedy(table, sc["caps"], upkeep)
        policies["shared-state"] = policy_cost(table, lambda e, c: greedy[e][c], all_eligible, upkeep)
        if chosen:
            a_choice = {("exact" if cap == caps["exact"] else "range"): impl
                        for cap, impl in chosen["implementations"].items()}
            policies["assimilation"] = policy_cost(table, lambda e, c: a_choice[c], len(set(a_choice.values())), upkeep)
        else:
            policies["assimilation"] = policies["originals"]
        totals = {k: sum(e["total_ns"] for e in v) for k, v in policies.items()}
        if chosen:
            totals["assimilation"] += construction_ns + publication["validation_compute_ns"]
        out["post"] = dict(totals_ms={k: round(v / 1e6, 3) for k, v in totals.items()},
                           state_bytes_per_epoch={k: round(sum(e["state_bytes"] for e in v) / len(v))
                                                  for k, v in policies.items()},
                           routing_choice=r_choice, originals_choice=o_choice)
        # Out-of-sample competence of the chosen candidate.
        if chosen:
            mismatch = sum(1 for ep in table for r in ep["rows"]
                           if r["runs"][a_choice[r["capability"]]]["output"] != r["runs"][o_choice[r["capability"]]]["output"])
            ratios = {}
            for c in sc["caps"]:
                p = [r["runs"][o_choice[c]]["answer_ns"] for ep in table for r in ep["rows"] if r["capability"] == c]
                q = [r["runs"][a_choice[c]]["answer_ns"] for ep in table for r in ep["rows"] if r["capability"] == c]
                same = a_choice[c] in by_cap_parents[c]
                ratio = median(q) / max(1, median(p))
                ratios[c] = dict(ratio=round(ratio, 3), same_artifact=same,
                                 measurable=max(median(p), median(q)) >= CONFIG["resolution_ns"],
                                 within=same or max(median(p), median(q)) < CONFIG["resolution_ns"]
                                 or ratio <= sc["tolerance"][c])
            savings = (sum(e["total_ns"] for e in policies["originals"]) - sum(e["total_ns"] for e in policies["assimilation"])) / len(table)
            out["out_of_sample"] = dict(mismatches=mismatch, ratios=ratios,
                                        incorrect=mismatch > 0 or not all(v["within"] for v in ratios.values()),
                                        realized_saving_ns_per_epoch=round(savings),
                                        realized_break_even_epochs=round((construction_ns + publication["validation_compute_ns"]) / savings, 2)
                                        if savings > 0 else None)
            out["live"] = live_check(rt, sc, caps, post[:3], role_cases, table, a_choice, ids, budget)
            if sc["composite"]:
                out["recovery"] = recovery_drill(rt, search, publication["assimilation"], chosen["_full"], caps,
                                                 ids, role_cases, budget)
    return out


def live_check(rt, sc, caps, epochs, role_cases, table, a_choice, ids, budget):
    """Run the published organization through real tasks on the first post epochs."""
    mismatches, e2e = 0, []
    for e, requests in enumerate(epochs):
        for i, (cap, value) in enumerate(requests):
            started = time.perf_counter_ns()
            task = rt.tasks.create_task("dev", cap, value, budget)
            output = rt.tasks.run_task(task, rt.tasks.authorize(task, "dev"), "dev")
            e2e.append(time.perf_counter_ns() - started)
            if providers_digest(output) != table[e]["rows"][i]["runs"][a_choice[cap]]["output"]:
                mismatches += 1
            if cap == "exact" and sc["composite"]:
                task = rt.tasks.create_task("dev", "exact-total", value, budget)
                total = rt.tasks.run_task(task, rt.tasks.authorize(task, "dev"), "dev")
                expected = sum(providers.compute("exact_hash", value))
                mismatches += int(total != expected)
    return dict(tasks=len(e2e), mismatches=mismatches, e2e_median_ms=round(median(e2e) / 1e6, 2))


def recovery_drill(rt, search, aid, verdict, caps, ids, role_cases, budget):
    """Post-publication competence loss, then recovery with fresh validation."""
    value = {"data": [3, 3, 8, 9], "queries": [3, 8, 1]}
    task_before = rt.tasks.create_task("dev", "exact", value, budget)
    permit_before = rt.tasks.authorize(task_before, "dev")
    replacement = verdict["assignment"][caps["exact"]]
    rt.fabric.apply_impact([replacement], "support", "X3 drill: post-publication counterexample")
    spent = rt.resources.budget(budget, "dev")["spent"]["attempts"]
    started = time.perf_counter_ns()
    search.recover(aid, role_cases, budget=budget, principal="dev", reason="X3 drill")
    wall = time.perf_counter_ns() - started
    old_permit_refused = False
    try:
        rt.tasks.run_task(task_before, permit_before, "dev")
    except Refused:
        old_permit_refused = True
    task = rt.tasks.create_task("dev", "exact", value, budget)
    restored = rt.tasks.run_task(task, rt.tasks.authorize(task, "dev"), "dev")
    task = rt.tasks.create_task("dev", "exact-total", value, budget)
    total = rt.tasks.run_task(task, rt.tasks.authorize(task, "dev"), "dev")
    bindings = rt.manifest()["bindings"]
    return dict(correct=restored == [2, 1, 0] and total == 3, old_permit_refused=old_permit_refused,
                parents_bound=bindings["exact"] == ids["exact_hash"],
                parent_state=rt.population.state(caps["exact"], ids["exact_hash"]),
                validation_attempts=rt.resources.budget(budget, "dev")["spent"]["attempts"] - spent,
                wall_ms=round(wall / 1e6, 2))


def hypotheses(results, seeds):
    get = lambda s, sd: results[s][str(sd)]
    acc = lambda s: sum(get(s, sd)["accepted"] for sd in seeds)
    need = max(1, len(seeds) - 1)
    accepted = [get(s, sd) for s in SCENARIOS for sd in seeds if get(s, sd)["accepted"]]
    incorrect = sum(1 for r in accepted if r["out_of_sample"]["incorrect"])
    sb = [get("SB-partial-overlap", sd) for sd in seeds]
    return {
        "X3-H1": dict(passed=acc("SC-incompatible") == 0),
        "X3-H2": dict(passed=acc("SA-exact-redundancy") >= need and acc("SB-partial-overlap") >= need and incorrect == 0,
                      incorrect_acceptances=incorrect),
        "X3-H3": dict(passed=all(r["out_of_sample"]["mismatches"] == 0 and r["live"]["mismatches"] == 0
                                 and all(v["within"] for v in r["out_of_sample"]["ratios"].values()) for r in accepted)),
        "X3-H4": dict(passed=sum(r["post"]["totals_ms"]["assimilation"] <= r["post"]["totals_ms"]["originals"] for r in sb) >= need),
        "X3-H5": dict(passed=sum(r["post"]["totals_ms"]["assimilation"] <= 1.10 * r["post"]["totals_ms"]["shared-state"]
                                 for r in sb) >= need),
        "X3-H6": dict(passed=all(r["post"]["state_bytes_per_epoch"]["assimilation"]
                                 <= 0.70 * r["post"]["state_bytes_per_epoch"]["originals"] for r in sb if r["accepted"])
                      and any(r["accepted"] for r in sb)),
        "X3-H7": dict(passed=all(r.get("recovery", {}).get("correct") and r["recovery"]["old_permit_refused"]
                                 and r["recovery"]["parents_bound"] for r in sb if r["accepted"]) and any(r["accepted"] for r in sb)),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("out")
    parser.add_argument("--quick", action="store_true", help="harness check only; different tiny configuration")
    args = parser.parse_args()
    digest = None
    seeds = SEEDS
    if args.quick:
        CONFIG.update(n=300, span=10000, observe_epochs=1, post_epochs=2, requests=1)
        seeds = (1,)
    else:
        digest = verify_frozen()
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    work = ROOT / ".brainos" / "results" / (out.name + ("-quick" if args.quick else ""))
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    started = time.time()
    results = {s: {str(sd): run_scenario(work, s, sd, args.quick) for sd in seeds} for s in SCENARIOS}
    hyp = hypotheses(results, seeds)
    if args.quick:
        print(json.dumps({"quick": True, "harness_ok": True}))
        return
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    full = dict(preregistration_sha256=digest, commit=commit, config=CONFIG, seeds=list(seeds),
                seconds=round(time.time() - started, 1), results=results, hypotheses=hyp)
    (out / "experiment-results.json").write_text(json.dumps(full, indent=1, default=str), encoding="utf-8")
    print(json.dumps(dict(hypotheses=hyp), indent=1))


if __name__ == "__main__":
    main()
