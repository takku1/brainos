"""Run the W2 heterogeneous preregistration (Doc 07 section 7.18, L2 only).

    py tools/run_heterogeneous.py docs/results/2026-11-25T-heterogeneous [seed ...]

Refuses to run unless the preregistration matches its recorded digest and
both files are committed unchanged at HEAD. Refuses to overwrite seed
outputs. Confirmatory execution requires a reviewed preregistration;
this runner executes only a frozen one. Results are committed separately
and never edited.
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

from brainos import Refused, Runtime  # noqa: E402
from brainos import emergence  # noqa: E402
from brainos import ecology  # noqa: E402

RESULTS = ROOT / "docs" / "results" / "2026-11-25T-heterogeneous"
PREREG = RESULTS / "PREREGISTRATION.md"
PREREG_SHA256 = "95f7125607a74b09603852306147407d6edcb74c975bd600cfa498c93092be29"
SEEDS = (21, 22, 23)
PROFILE = "inprocess"
OP_ALIASES = {"sum": "sum", "add": "sum"}
VALUES = {"nl-arith": dict(per_request=10, late_penalty=4, floor_ns=300 * 10 ** 9)}
DEV_ATTEMPTS = 2000
EXEC_ATTEMPTS = 4000
DRAW_TIMEOUT = 30.0
TASK_TIMEOUT = 60.0
UNIT_NS = 10 ** 6
N_ADMIT, K_ADMIT = 3, 2
ADMISSION_CASES = [("Add up 2 and 3.", '{"operation": "sum", "values": [2, 3]}'),
                   ("Add up 10 and 4.", '{"operation": "sum", "values": [10, 4]}')]
PROMPT_VERSION = "qwen-probe-sum-v1"
PROMPT_TEXT = ('Request: "Add up 4 and 6."\n{"operation": "sum", "values": [4, 6]}\n'
               'Request: "Please add 1 and 9."\n{"operation": "sum", "values": [1, 9]}\n'
               'Request: "{input}"\n')
SAMPLING = {"temperature": 0.0, "top_p": 1.0, "max_tokens": 32, "seed": 11}
QWEN_COST = {"attempts": 30}
QWEN_SCHEDULE = dict(initialization=30, inference=5, transport=1, memory=1500,
                     accelerator=0, overhead=1)
QWEN_UNITS = dict(initialization="seconds", inference="seconds", transport="attempts",
                  memory="MB", accelerator="seconds", overhead="attempts")
QWEN_MEASURED = dict(initialization="adapter", inference="adapter", transport="kernel",
                     memory="adapter", accelerator="adapter", overhead="kernel")


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

    def add(split, context, value, expected):
        demands.append(dict(idx=len(demands), split=split, context=context, value=value,
                            expected=expected))

    for _ in range(2):
        a, b = rng.randint(0, 99), rng.randint(0, 99)
        add("calibration", "canonical", f"Add up {a} and {b}.",
            {"operation": "sum", "values": [a, b]})
    a, b = rng.randint(0, 99), rng.randint(0, 99)
    add("calibration", "irregular", f"Please add {a} and {b} together.",
        {"operation": "sum", "values": [a, b]})
    a, b = rng.randint(0, 99), rng.randint(0, 99)
    add("calibration", "irregular", f"Can you add {a} to {b}?",
        {"operation": "sum", "values": [a, b]})
    for _ in range(2):
        a, b = rng.randint(0, 99), rng.randint(0, 99)
        add("held-out", "canonical", f"add up {a},{b}",
            {"operation": "sum", "values": [a, b]})
    a, b = rng.randint(0, 99), rng.randint(0, 99)
    add("held-out", "irregular", f"{a} + {b} = ?",
        {"operation": "sum", "values": [a, b]})
    a, b, c = rng.randint(0, 99), rng.randint(0, 99), rng.randint(0, 99)
    add("held-out", "irregular", f"Add up the numbers {a}, {b} and {c}.",
        {"operation": "sum", "values": [a, b, c]})
    return demands


def interpret(output, expected):
    """Independent evaluator: JSON parse, alias normalization, exact IR match."""
    try:
        parsed = json.loads(output)
    except (ValueError, TypeError):
        return False, "unparseable"
    if not isinstance(parsed, dict):
        return False, "not-an-object"
    op = parsed.get("operation")
    if op not in OP_ALIASES:
        return False, "unknown-operation"
    if parsed.get("values") != expected["values"] or OP_ALIASES[op] != "sum":
        return False, "mismatch"
    return True, "match"


def qwen_launcher():
    manifest = json.loads((ROOT / "src" / "models" / "manifest.json").read_text(encoding="utf-8"))
    digest = next(a["digest_sha256"] for a in manifest["artifacts"] if a["id"] == "Qwen3-0.6B")
    return ({"qwen3-lm": [sys.executable, str(ROOT / "implementations" / "qwen_adapter.py"),
                           "--model-dir", str(ROOT / "src" / "models" / "Qwen3-0.6B"),
                           "--artifact", digest,
                           "--prompt-text", PROMPT_TEXT,
                           "--prompt-version", PROMPT_VERSION]}, digest)


def run_task(rt, capability, provider, value, budget, timeout=TASK_TIMEOUT):
    task = rt.tasks.create_member_task("dev", capability, provider, value, budget, timeout=timeout)
    output = rt.tasks.run_task(task, rt.tasks.authorize(task, "dev"), "dev")
    invocation = rt.tasks.invocation(rt.tasks.task(task, "dev")["invocation"], "dev")
    return task, output, invocation


def validation_cost_of(rt, cap, provider, cost_attempts):
    """Validation spend in attempts for one admitted member (0 if absent)."""
    member = next((m for m in rt.store.find("member")
                   if m["id"] == f"{cap}|{provider}"), None)
    if member is None:
        return 0
    record = rt.store.get("candidate", member["candidate"])
    return (record.get("validation_attempts", 0) or 0) * cost_attempts


def _run_seed(seed, outdir):
    path = outdir / f"seed-{seed}.json"
    if path.exists():
        raise SystemExit(f"{path.name} already exists; results are never overwritten")
    stream = gen_stream(seed)
    adapters, digest = qwen_launcher()
    out = dict(seed=seed, profile=PROFILE, prompt_version=PROMPT_VERSION,
               prompt_text=PROMPT_TEXT, sampling=SAMPLING,
               admission=dict(n=N_ADMIT, k=K_ADMIT), stream=stream)
    with tempfile.TemporaryDirectory() as workdir:
        rt = Runtime(Path(workdir) / "c.db", profile=PROFILE, external_adapters=adapters)
        try:
            cap = rt.population.define("nl-arith", "text", "text", ADMISSION_CASES)
            det = rt.registry.register("parse_nl_sum")
            qwen = rt.registry.register_external(
                implementation="qwen3-lm", input="text", output="text", capability="nl-arith",
                cost={"attempts": 30}, cost_schedule=dict(QWEN_SCHEDULE),
                cost_units=dict(QWEN_UNITS), measured_by=dict(QWEN_MEASURED), artifact=digest,
                artifact_algorithm="sha256",
                identities=dict(model="Qwen/Qwen3-0.6B", runtime="qwen-adapter/cpu-torch",
                                tokenizer="Qwen3-0.6B", prompt_template=PROMPT_VERSION),
                sampling=dict(SAMPLING), nondeterministic=True,
                admission=dict(n=N_ADMIT, k=K_ADMIT))
            out["qwen_provider"] = qwen
            val = rt.resources.create_budget("dev", {"attempts": 2000})
            exe = rt.resources.create_budget("dev", {"attempts": 4000})
            out["deterministic_admitted"] = bool(rt.population.admit(
                cap, det, budget=val, principal="dev"))
            try:
                rt.population.admit(cap, qwen, budget=val, principal="dev")
                out["qwen_admitted"] = True
                candidate = next(m for m in rt.store.find("member")
                                 if m["id"] == f"{cap}|{qwen}")["candidate"]
                out["qwen_admission_evidence"] = rt.store.get("candidate", candidate).get(
                    "admission_evidence")
            except Refused as exc:
                out["qwen_admitted"] = False
                out["qwen_admission_error"] = str(exc)[:300]
            sum_cap = rt.population.define("w2-sum", "integers", "integer", [([1, 2], 3)])
            sum_provider = rt.registry.register("sum")
            rt.population.admit(sum_cap, sum_provider, budget=val, principal="dev")
            members = {"deterministic": det}
            if out.get("qwen_admitted"):
                members["qwen"] = qwen
            table, tasks_by_arm = [], {"fixed": [], "neural": [], "coordinated": []}
            sum_tasks_by_arm = {"fixed": [], "neural": [], "coordinated": []}
            for demand in [d for d in stream if d["split"] == "calibration"]:
                row = dict(idx=demand["idx"], context=demand["context"], costs={},
                           outputs={}, correct={})
                for label, pid in members.items():
                    try:
                        task, output, invocation = run_task(rt, cap, pid, demand["value"], exe)
                    except Refused as exc:
                        row["outputs"][label] = f"REFUSED: {exc}"
                        row["correct"][label] = False
                        continue
                    ok, _ = interpret(output, demand["expected"])
                    row["outputs"][label] = output
                    row["correct"][label] = ok
                    row["costs"][label] = invocation["compute_ns"]
                    tasks_by_arm["fixed" if label == "deterministic" else "neural"].append(task)
                table.append(row)
            calibration = [dict(context=r["context"], costs={m: (0 if r["correct"].get(m) else 1)
                                                             for m in members}) for r in table]
            selection = ecology.offline_selection(calibration) if calibration else {}
            out["selection"] = selection
            for demand in [d for d in stream if d["split"] == "held-out"]:
                for arm, chooser in (("fixed", lambda d: "deterministic"),
                                     ("neural", lambda d: "qwen" if "qwen" in members else None),
                                     ("coordinated", lambda d: selection.get(d["context"]))):
                    label = chooser(demand)
                    if label is None or label not in members:
                        continue
                    pid = members[label]
                    entry = dict(idx=demand["idx"], arm=arm, member=label)
                    try:
                        task, output, invocation = run_task(rt, cap, pid, demand["value"], exe)
                    except Refused as exc:
                        entry.update(served=False, reason=str(exc)[:200])
                        out.setdefault("runs", []).append(entry)
                        continue
                    ok, why = interpret(output, demand["expected"])
                    entry.update(served=bool(ok), output=output, eval=why,
                                 compute_ns=invocation["compute_ns"],
                                 total_ns=invocation["total_ns"])
                    late = invocation["total_ns"] > VALUES["nl-arith"]["floor_ns"]
                    if ok:
                        try:
                            ir = json.loads(output)
                            values = [int(v) for v in ir["values"]]
                            stask, soutput, sinv = run_task(rt, sum_cap, sum_provider, values,
                                                           exe)
                            expected = sum(demand["expected"]["values"])
                            entry.update(executed=soutput, expected=expected,
                                         correct=bool(soutput == expected))
                            entry["compute_ns"] += sinv["compute_ns"]
                            entry["total_ns"] += sinv["total_ns"]
                        except (Refused, ValueError, KeyError, TypeError) as exc:
                            entry.update(executed=None, correct=False,
                                         execution_error=str(exc)[:200])
                    else:
                        entry.update(correct=False)
                    entry["late"] = bool(late and entry.get("served"))
                    tasks_by_arm[arm].append(task)
                    if entry.get("correct"):
                        sum_tasks_by_arm[arm].append(stask)
                    out.setdefault("runs", []).append(entry)
            validation_costs = {
                "deterministic": validation_cost_of(rt, cap, det, 1),
                "qwen": validation_cost_of(rt, cap, qwen, 30) if out.get("qwen_admitted") else 0,
            }
            out["validation_costs"] = validation_costs
            out["table"] = table
            out["meters"] = {}
            for arm, tids in tasks_by_arm.items():
                if not tids:
                    continue
                try:
                    out["meters"][arm] = emergence.measure(rt.store, cap, tids,
                                                           external_adapters=adapters)
                except Refused as exc:
                    out.setdefault("meter_failures", {})[arm] = str(exc)
            out["sum_meters"] = {}
            for arm, tids in sum_tasks_by_arm.items():
                if not tids:
                    continue
                try:
                    out["sum_meters"][arm] = emergence.measure(rt.store, sum_cap, tids)
                except Refused as exc:
                    out.setdefault("meter_failures", {})[f"sum-{arm}"] = str(exc)
            try:
                out["verdict"] = emergence.organizational_verdict(rt.store, cap,
                                                                 external_adapters=adapters)
            except Refused as exc:
                out["verdict"] = dict(verdict="no-members", error=str(exc)[:200])
            out["nov"] = nov_by_arm(out)
            out["oracle"] = oracle_result(out)
            out["hypotheses"] = check_hypotheses(out)
            out["head"] = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                         capture_output=True, text=True).stdout.strip()
        finally:
            rt.close()
    out["preregistration"] = PREREG_SHA256
    path.write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    return out


def arm_nov(out, arm):
    report = out["meters"][arm]
    native = report["R"]
    compute = native["compute_ns"] / UNIT_NS
    overhead = native["overhead_ns"] / UNIT_NS
    extra = out.get("sum_meters", {}).get(arm)
    if extra is not None:
        compute += extra["R"]["compute_ns"] / UNIT_NS
        overhead += extra["R"]["overhead_ns"] / UNIT_NS
    validation = sum(out["validation_costs"].values()) if arm == "coordinated" else 0.0
    if arm == "fixed":
        validation += out["validation_costs"].get("deterministic", 0)
    if arm == "neural":
        validation += out["validation_costs"].get("qwen", 0)
    costs = dict(compute=compute, overhead=overhead, construction=0.0,
                 validation=float(validation), assessment=native["assessment_ns"] / UNIT_NS,
                 maintenance=float(native["maintenance_units"]))
    by_idx = {}
    for demand in out["stream"]:
        by_idx[demand["idx"]] = demand
    served = []
    for entry in out.get("runs", []):
        if entry.get("member") != {"fixed": "deterministic", "neural": "qwen"}.get(arm, arm):
            continue
        demand = by_idx[entry["idx"]]
        if entry.get("correct"):
            served.append(dict(contract="nl-arith", late=bool(entry.get("late", False))))
    table = {"nl-arith": dict(per_request=VALUES["nl-arith"]["per_request"],
                              late_penalty=VALUES["nl-arith"]["late_penalty"])}
    result = emergence.net_value([dict(served=served, costs=costs)], table)
    return dict(value=result["total"] + sum(costs.values()), costs=costs,
                net=result["total"], served=len(served))


def nov_by_arm(out):
    return {arm: arm_nov(out, arm) for arm in out.get("meters", {})}


def oracle_result(out):
    by_idx = {}
    for demand in out["stream"]:
        by_idx[demand["idx"]] = demand
    best, total_value, windows = {}, 0.0, []
    for demand in out["stream"]:
        candidates = [e for e in out.get("runs", [])
                      if e["idx"] == demand["idx"] and e.get("correct")]
        if not candidates:
            continue
        winner = min(candidates, key=lambda e: e["compute_ns"])
        best[demand["idx"]] = winner
        total_value += VALUES["nl-arith"]["per_request"]
    compute = sum(e["compute_ns"] for e in best.values()) / UNIT_NS
    overhead = sum(max(0, e["total_ns"] - e["compute_ns"]) for e in best.values()) / UNIT_NS
    costs = dict(compute=compute, overhead=overhead, construction=0.0, validation=0.0,
                 assessment=0.0, maintenance=0.0)
    return dict(windows=[dict(value=total_value, costs=costs)], total=total_value - sum(costs.values()),
                demands_covered=len(best))


def check_hypotheses(out):
    checks = {}
    arms = [a for a in ("fixed", "neural", "coordinated") if a in out.get("meters", {})]
    checks["H1"] = dict(passed=not out.get("meter_failures") and len(arms) >= 1,
                        meter_failures=out.get("meter_failures", {}), arms=arms)
    try:
        for arm, data in out.get("meters", {}).items():
            assert set(data["R"]) >= {"compute_ns", "overhead_ns"}
        assert out["nov"] and all(set(v["costs"]) == set(emergence.NOV_COSTS)
                                 for v in out["nov"].values())
        checks["H2"] = dict(passed=True)
    except (AssertionError, KeyError) as exc:
        checks["H2"] = dict(passed=False, error=str(exc)[:200])
    verdict = out.get("verdict", {})
    checks["H3"] = dict(passed=verdict.get("verdict") in
                        ("organizational", "compositional-but-fragile", "redundant",
                         "neither", "inconclusive-budget")
                        and verdict.get("checks_spent", -1) >= 0,
                        verdict=verdict.get("verdict"))
    held_ids = {d["idx"] for d in out["stream"] if d["split"] == "held-out"}
    fixed_ok = sum(1 for e in out.get("runs", [])
                   if e.get("arm") == "fixed" and e["idx"] in held_ids and e.get("correct"))
    coord_ok = sum(1 for e in out.get("runs", [])
                   if e.get("arm") == "coordinated" and e["idx"] in held_ids and e.get("correct"))
    checks["H4"] = dict(passed=coord_ok > fixed_ok, coordinated_correct=coord_ok,
                        fixed_correct=fixed_ok)
    qwen_costs, det_costs = [], []
    for entry in out.get("runs", []):
        if entry.get("served") and entry.get("correct"):
            (qwen_costs if entry.get("member") == "qwen" else det_costs).append(
                entry["compute_ns"])
    qwen_mean = sum(qwen_costs) / len(qwen_costs) if qwen_costs else 0
    det_mean = sum(det_costs) / len(det_costs) if det_costs else 0
    checks["H5"] = dict(passed=bool(qwen_mean > 0 and (det_mean <= 0 or qwen_mean / det_mean >= 10)),
                        qwen_mean_ns=qwen_mean, det_mean_ns=det_mean)
    return checks


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    outdir = Path(args[0]) if args else RESULTS
    seeds = [int(a) for a in args[1:]] or list(SEEDS)
    verify_frozen()
    outdir.mkdir(parents=True, exist_ok=True)
    for seed in seeds:
        if seed not in SEEDS:
            raise SystemExit(f"seed {seed} is not preregistered")
        started = time.perf_counter()
        seed_out = _run_seed(seed, outdir)
        print(f"seed {seed}: {time.perf_counter() - started:.1f}s "
              f"hypotheses={[k for k, v in seed_out['hypotheses'].items() if v['passed']]} "
              f"verdict={seed_out['verdict'].get('verdict')} "
              f"nov={ {k: round(v['net'], 1) for k, v in seed_out['nov'].items()} } "
              f"oracle={round(seed_out['oracle']['total'], 1)}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
