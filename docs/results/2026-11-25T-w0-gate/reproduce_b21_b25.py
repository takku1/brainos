"""Reproduce review findings B21-B25 on the committed baseline (4bd0f24)."""
import json, random, sys, tempfile
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, "tests")
from brainos import Runtime, Refused
from brainos import providers
from brainos.assimilation import AssimilationSearch, EvaluationSet, Gate
import test_assimilation as ta

F = {}


class Org(ta.Organization):
    def runTest(self):
        pass


def org():
    o = Org(); o.setUp(); return o


# B21: an individually accepted candidate that fails final selection can still be published.
o = org()
gate = o.gate(maintenance_ns_per_byte_epoch=1000.0)
nominated, _ = o.search.nominate(o.parents)
evalset = o.evalset()
verdicts = [o.search.evaluate(c, o.parents, evalset, gate, budget=o.budget, principal="dev") for c in nominated]
sv = next(v for v in verdicts if v["implementations"][o.exact] == "exact_sorted")
own = sv["construction_ns"] / sv["mean_savings_ns"]
total = sum(v["construction_ns"] for v in verdicts) / sv["mean_savings_ns"]
tight = o.gate(maintenance_ns_per_byte_epoch=1000.0, horizon=(own + total) / 2)
sv["accepted"] = True                      # passes its own-cost check under a horizon above `own`
chosen = o.search.select(verdicts, tight)
published = None
try:
    published = o.search.publish(sv, o.parents, o.roles, budget=o.budget, principal="dev")
except Refused as exc:
    published = f"refused: {exc}"
F["B21"] = dict(reproduced=chosen is None and isinstance(published, str) and published.startswith("assimilation:"),
                select_result=chosen, selectable=sv.get("selectable"), publish_result=published)
o.tearDown()

# B22: an internal-state candidate is reported as maintaining zero state.
o = org()
hash_idx = o.r.registry.register("range_hash_index")
o.r.population.admit(o.range, hash_idx, budget=o.budget, principal="dev")
parents = [dict(capability=o.range, provider=o.ids["range_sorted"]), dict(capability=o.range, provider=hash_idx)]
nominated, _ = o.search.nominate(parents)
internal = [c for c in nominated if set(c["implementations"].values()) & {"range_bisect", "range_hash"}]
epochs = [[e for e in ep if e[0] == o.range] for ep in o.evalset().epochs]
reports = []
for c in internal:
    v = o.search.evaluate(c, parents, EvaluationSet(epochs=epochs), o.gate(), budget=o.budget, principal="dev")
    reports.append(dict(impl=c["implementations"], method=c["method"], state_after=v["state_bytes_after"],
                        state_before=v["state_bytes_before"]))
F["B22"] = dict(reproduced=any(r["state_after"] == 0 for r in reports), internal_candidates=reports,
                note="internal structures are rebuilt inside answer time but reported as 0 maintained bytes")
o.tearDown()

# B23: pooled confidence bound passes while one context's own bound exceeds tolerance.
o = org()
candidate = o.sorted_candidate()
sorted_id = candidate["assignment"][o.exact]
real = o.search._run
calls = {"n": 0}
def scripted(spec, value, budget, principal, timings, _sets={}):
    out, timing = real(spec, value, budget, principal, timings)
    timing = dict(timing, answer_ns=100_000)
    if spec["id"] == sorted_id:
        calls["n"] += 1
        timing["answer_ns"] = int(100_000 * (1.2 if calls["n"] <= 7 else 2.9 + 0.8 * (calls["n"] % 2)))
    return out, timing
o.search._run = scripted
v = o.search.evaluate(candidate, o.parents, o.evalset(epochs=9), o.gate(exact=3.0), budget=o.budget, principal="dev")
ratios = v["latency_ratio"][o.exact]
F["B23"] = dict(reproduced=not any("upper bound" in r for r in v["reasons"]) and ratios.get("held-out", 0) > 2.5,
                ratios=ratios, reasons=v["reasons"],
                note="pooled bound over all sets; the held-out set alone is near/over tolerance")
o.tearDown()

# B24: downstream equality checks run without charging the evaluation budget.
o = org()
candidate = o.sorted_candidate()
charged = []
orig_charge = o.search.ctx.charge
def tracking(budget, principal, amount, purpose):
    charged.append(purpose); return orig_charge(budget, principal, amount, purpose)
computes = {"n": 0}
orig_compute = o.search.ctx.compute
def counting(*a, **k):
    computes["n"] += 1; return orig_compute(*a, **k)
o.search.ctx.charge, o.search.ctx.compute = tracking, counting
o.search.evaluate(candidate, o.parents, o.evalset(), o.gate(), budget=o.budget, principal="dev")
F["B24"] = dict(reproduced=computes["n"] > len(charged), computes=computes["n"], charges=len(charged))
o.tearDown()

# B25: nomination size is the product of per-capability options per structure kind.
o = org()
extra = {f"exact_sorted_v{i}": providers.Primitive(providers.exact_on_sorted, "exact-batch", "integers",
                                                   "exact-count", version=str(i + 2), prepare=providers.prepare_sorted)
         for i in range(5)}
extra.update({f"range_sorted_v{i}": providers.Primitive(providers.range_on_sorted, "range-batch", "integers",
                                                        "range-count", version=str(i + 2), prepare=providers.prepare_sorted)
              for i in range(5)})
with patch.dict(providers.PRIMITIVES, extra):
    nominated, _ = o.search.nominate(o.parents)
F["B25"] = dict(reproduced=len(nominated) >= 36, nominated=len(nominated),
                note="6 sorted options per capability -> 36 sorted combinations, unbounded by any cap")
o.tearDown()
print(json.dumps(F, indent=1, default=str))
