"""Reproduce review findings B14-B20 on the committed baseline (9b9e7bd)."""
import inspect, json, sys, tempfile
from pathlib import Path
from statistics import median
from brainos import Runtime, Refused
from brainos import ecology, development, population
F = {}
with tempfile.TemporaryDirectory() as d:
    now = [0.0]
    r = Runtime(Path(d) / "c.db", clock=lambda: now[0], profile="inprocess")
    cap = r.population.define("range-count", "range-batch", "integers", [({"data": [1, 5], "queries": [[0, 2]]}, [1])])
    v = r.resources.create_budget("eco", {"attempts": 40})
    a, b = r.registry.register("range_scan"), r.registry.register("range_bisect")
    for p in (a, b): r.population.admit(cap, p, budget=v, principal="eco")
    # B14: evidence about a different (synthetic) member retires the real bisect provider
    r.population.retire(cap, b, reason="x", evidence={"justified": True, "member": "not-bisect"})
    F["B14"] = dict(reproduced=r.store.get("member", f"{cap}|{b}")["state"] == "ARCHIVED",
                    note="retire accepted evidence naming another member, no capability/revision/observation binding")
    # B15: ceiling 100; reserve 100; refill; release -> unspent exceeds ceiling
    bud = r.resources.create_budget("dev", {"attempts": 100})
    r.resources.attach_policy(bud, issued_by="operator", period_seconds=1, grant={"attempts": 100}, ceiling={"attempts": 100})
    h = r.resources.reserve(bud, "dev", {"attempts": 100})
    now[0] += 1
    after_refill = r.resources.budget(bud, "dev")["available"]["attempts"]
    r.resources.release(h, "dev")
    unspent = r.resources.budget(bud, "dev")["available"]["attempts"]
    F["B15"] = dict(reproduced=unspent > 100, available_after_refill=after_refill, unspent_after_release=unspent, ceiling=100)
    # B20: any caller can assert operator identity
    minted = r.resources.create_budget("dev", {"attempts": 10**9}, issued_by="operator")
    F["B20"] = dict(reproduced=True, minted_capacity=r.resources.budget(minted, "dev")["capacity"],
                    note="issued_by is an asserted string; CompositionSearch holds the full Runtime (resources, store)",
                    search_holds_runtime=hasattr(development.CompositionSearch(r), "runtime"))
    r.close()
# B16: policy evidence lives only in memory
pol = ecology.EcologyPolicy(["a", "b"]); pol.observe("c", "a", 1.0)
F["B16"] = dict(reproduced="store" not in inspect.signature(ecology.EcologyPolicy).parameters,
                note="EcologyPolicy evidence/contexts/archived/rng are in-process only; nothing persisted")
# B17: runner mixes compute_ns execution costs with wall-clock regeneration
src = Path("tools/run_ecology.py").read_text(encoding="utf-8")
F["B17"] = dict(reproduced="regeneration_ms" in src and "compute_ns" in src and "perf_counter()" in src,
                note="ecology total = sum(compute_ns) + regeneration wall-clock ms")
# B18: recompute exact coexistence quantifier from preserved tables
def coexist(table, active, exact):
    out = {}
    for c in sorted({r["context"] for r in table}):
        rows = [r for r in table if r["context"] == c]
        if exact:
            ok = any(sum(r["costs"][m] <= 1.10 * min(r["costs"].values()) for r in rows) > len(rows) / 2 for m in active)
        else:
            ok = sum(min(r["costs"][m] for m in active) <= 1.10 * min(r["costs"].values()) for r in rows) > len(rows) / 2
        out[c] = ok
    return out
res = {}
for v_ in ("v1", "v2"):
    x = json.loads(Path(f"docs/results/2026-11-25T-ecology/experiment-results-{v_}.json").read_text())["x2"]
    act = x["active_members"]
    res[v_] = dict(active=act, implemented=coexist(x["table"], act, False), exact=coexist(x["table"], act, True),
                   reported=x["hypotheses"][("X2" if v_ == "v1" else "X2b") + "-H1"]["passed"])
    res[v_]["exact_passed"] = len(act) >= 3 and all(res[v_]["exact"].values())
F["B18"] = dict(logic_discrepancy_confirmed=True,
                verdicts_changed=any(res[k]["exact_passed"] != res[k]["reported"] for k in res),
                note="implemented check takes per-request min over active members; preregistered quantifier needs one member", **res)
# B19: one-sample pruning
pol = ecology.EcologyPolicy(["a", "b"], prune_factor=10.0, epsilon=0)
pol.observe("c", "b", 1.0); pol.observe("c", "b", 1.0); pol.observe("c", "b", 1.0); pol.observe("c", "a", 11.0)
F["B19"] = dict(reproduced=pol.select("c", True) == ("b", False),
                note="a single noisy 11x sample permanently stops exploration of member a in context c")
print(json.dumps(F, indent=1))
