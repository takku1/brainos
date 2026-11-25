"""Qwen heterogeneous feasibility probe (disclosed, NON-CONFIRMATORY).

Runs a mixed deterministic+neural organization on a tiny fixed demand set
and prints a JSON summary to stdout. Nothing is committed; no result here
may back a confirmatory claim. Every feasibility choice below (prompt,
sampling, demands, budgets) must be disclosed in the future W2
preregistration and frozen there, not tuned against.

Covers D5.1-D5.3 in feasibility form:
  L2-lite: deterministic NL parser + Qwen behind one text-to-text
    contract, k-of-n admission, validated IR executed by an existing
    deterministic provider, meter + verdict + NOV over the window.
"""
import json
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from brainos import Refused, Runtime  # noqa: E402
from brainos import emergence  # noqa: E402

PROMPT_VERSION = "qwen-probe-sum-v1"
PROMPT_TEXT = (
    'Request: "Add up 4 and 6."\n{"operation": "sum", "values": [4, 6]}\n'
    'Request: "Please add 1 and 9."\n{"operation": "sum", "values": [1, 9]}\n'
    'Request: "{input}"\n'
)
SAMPLING = {"temperature": 0.0, "top_p": 1.0, "max_tokens": 32, "seed": 11}
ADMISSION_CASES = [
    ("Add up 2 and 3.", '{"operation": "sum", "values": [2, 3]}'),
    ("Add up 10 and 4.", '{"operation": "sum", "values": [10, 4]}'),
]
STREAM = [
    ("Add up 2 and 3.", "canonical"),
    ("Add up 10 and 4.", "canonical"),
    ("Please add 7 and 8 together.", "irregular"),
]
SCHEDULE = dict(initialization=3600, inference=30, transport=1, memory=4000,
                accelerator=0, overhead=5)
UNITS = dict(initialization="seconds", inference="seconds", transport="attempts",
             memory="MB", accelerator="seconds", overhead="attempts")
MEASURED = dict(initialization="adapter", inference="adapter", transport="kernel",
                memory="adapter", accelerator="adapter", overhead="kernel")


def main():
    started = time.perf_counter()
    manifest = json.loads((ROOT / "src" / "models" / "manifest.json").read_text())
    artifacts = {a["id"]: a for a in manifest["artifacts"]}
    digest = artifacts["Qwen3-0.6B"]["digest_sha256"]
    model_dir = str(ROOT / "src" / "models" / "Qwen3-0.6B")
    out = dict(feasibility=True, confirmatory=False, prompt_version=PROMPT_VERSION,
               prompt_text=PROMPT_TEXT, sampling=SAMPLING, stream=STREAM)
    with tempfile.TemporaryDirectory() as workdir:
        rt = Runtime(Path(workdir) / "c.db", profile="inprocess",
                     external_adapters={"qwen3-lm": [
                         sys.executable, str(ROOT / "implementations" / "qwen_adapter.py"),
                         "--model-dir", model_dir, "--artifact", digest,
                         "--prompt-text", PROMPT_TEXT, "--prompt-version", PROMPT_VERSION]})
        try:
            cap = rt.population.define("nl-arith", "text", "text", ADMISSION_CASES)
            det = rt.registry.register("parse_nl_sum")
            qwen = rt.registry.register_external(
                implementation="qwen3-lm", input="text", output="text",
                capability="nl-arith", cost={"attempts": 30},
                cost_schedule=dict(SCHEDULE), cost_units=dict(UNITS),
                measured_by=dict(MEASURED), artifact=digest, artifact_algorithm="sha256",
                identities=dict(model="Qwen/Qwen3-0.6B", runtime="qwen-adapter/cpu",
                                tokenizer="Qwen3-0.6B", prompt_template=PROMPT_VERSION),
                sampling=dict(SAMPLING), nondeterministic=True,
                admission=dict(n=3, k=2))
            out["qwen_provider"] = qwen
            val = rt.resources.create_budget("dev", {"attempts": 10000})
            exe = rt.resources.create_budget("dev", {"attempts": 10000})
            rt.population.admit(cap, det, budget=val, principal="dev")
            out["deterministic_admitted"] = True
            try:
                rt.population.admit(cap, qwen, budget=val, principal="dev")
                out["qwen_admitted"] = True
            except Refused as exc:
                out["qwen_admitted"] = False
                out["qwen_admission_error"] = str(exc)
                print(json.dumps(out, indent=1, default=str))
                return
            sum_cap = rt.population.define("probe-sum", "integers", "integer",
                                           [([1, 2], 3)])
            sum_provider = rt.registry.register("sum")
            rt.population.admit(sum_cap, sum_provider, budget=val, principal="dev")
            tasks, executions = [], []
            for value, context in STREAM:
                for pid, label in ((det, "deterministic"), (qwen, "qwen")):
                    entry = dict(demand=value, context=context, member=label)
                    try:
                        task = rt.tasks.create_member_task("dev", cap, pid, value, exe)
                        output = rt.tasks.run_task(task, rt.tasks.authorize(task, "dev"), "dev")
                        invocation = rt.tasks.invocation(
                            rt.tasks.task(task, "dev")["invocation"], "dev")
                        entry.update(served=True, output=output,
                                     compute_ns=invocation["compute_ns"],
                                     total_ns=invocation["total_ns"])
                        tasks.append(task)
                        try:
                            ir = json.loads(output)
                            assert ir["operation"] == "sum"
                            values = [int(v) for v in ir["values"]]
                            stask = rt.tasks.create_member_task("dev", sum_cap, sum_provider,
                                                                values, exe)
                            result = rt.tasks.run_task(stask, rt.tasks.authorize(stask, "dev"),
                                                       "dev")
                            entry.update(ir_valid=True, executed=result,
                                         expected=sum(values), correct=result == sum(values))
                        except (ValueError, AssertionError, KeyError, TypeError) as exc:
                            entry.update(ir_valid=False, ir_error=f"{type(exc).__name__}")
                    except Refused as exc:
                        entry.update(served=False, error=str(exc)[:200])
                    executions.append(entry)
            out["executions"] = executions
            out["meter"] = emergence.measure(
                rt.store, cap, tasks,
                external_adapters={"qwen3-lm": [
                    sys.executable, str(ROOT / "implementations" / "qwen_adapter.py"),
                    "--model-dir", model_dir, "--artifact", digest,
                    "--prompt-text", PROMPT_TEXT, "--prompt-version", PROMPT_VERSION]})
            out["verdict"] = emergence.organizational_verdict(
                rt.store, cap, external_adapters={"qwen3-lm": [
                    sys.executable, str(ROOT / "implementations" / "qwen_adapter.py"),
                    "--model-dir", model_dir, "--artifact", digest,
                    "--prompt-text", PROMPT_TEXT, "--prompt-version", PROMPT_VERSION]})
            # Declared conversion, as in X4: 1 unit = 1e6 ns = 1 attempt = 1 unit.
            scale = 10 ** -6
            native = out["meter"]["R"]
            costs = dict(compute=native["compute_ns"] * scale,
                         overhead=native["overhead_ns"] * scale,
                         construction=sum(native["construction"].values()),
                         validation=sum(native["validation"].values()),
                         assessment=native["assessment_ns"] * scale,
                         maintenance=native["maintenance_units"])
            out["nov"] = emergence.net_value(
                [dict(served=[dict(contract="nl-arith", late=False)
                              for e in executions if e.get("correct")], costs=costs)],
                {"nl-arith": dict(per_request=10)})
        finally:
            rt.close()
    out["seconds"] = round(time.perf_counter() - started, 1)
    print(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    main()
