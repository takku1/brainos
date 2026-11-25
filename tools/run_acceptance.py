"""Run the corrected profile's acceptance suites and composition experiment.

Writes logs and a machine-readable summary into an existing results directory:
    py tools/run_acceptance.py docs/results/<stamp>
Nothing here claims benefit beyond what the recorded numbers show.
"""
from pathlib import Path
import json
import os
import platform
import sqlite3
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from brainos import Runtime  # noqa: E402
from brainos.__main__ import install  # noqa: E402
from brainos.development import CapabilityDemand, CompositionSearch  # noqa: E402

PARENTS = {"parse": "parse_csv", "total": "sum", "total_loop": "sum_loop", "count": "count",
           "length": "text_length", "negate": "negate"}
PARENT_CASES = {"parse": [("1,2", [1, 2])], "total": [([1, 2], 3)], "total_loop": [([1, 2], 3)],
                "count": [([1, 2], 2)], "length": [("ab", 2)], "negate": [(3, -3)]}
DEMAND = CapabilityDemand("csv-sum", "text", "integer", (("1,2,3", 6), ("10, -4", 6)))
ADMISSION = [("4,5", 9), ("", 0), ("7", 7), ("-3, 3, 100", 100)]
SUITES = [
    ("corrected-demo", [sys.executable, "-m", "brainos", "--state-dir"]),
    ("runtime-tests", [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"]),
    ("reference-regressions", [sys.executable, "tools/test_reference_regressions.py"]),
    ("doc-structural-checks", [sys.executable, "tools/gate1_checks.py"]),
    ("doc-negative-checks", [sys.executable, "tools/gate1_negatives.py"]),
    ("l1-harness", [sys.executable, "tools/l1_harness.py"]),
    ("dependency-closure", [sys.executable, "tools/dep_closure.py"]),
    ("traceability-drift", [sys.executable, "-X", "utf8", "tools/check_traceability.py"]),
]


def run_suites(out, state):
    env = dict(os.environ, PYTHONUTF8="1", PYTHONPATH=str(ROOT / "src"))
    results = []
    for name, args in SUITES:
        if name == "corrected-demo":
            args = args + [str(state / "demo")]
        start = time.perf_counter()
        r = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", env=env, timeout=600)
        (out / f"{name}.log").write_text(r.stdout + r.stderr, encoding="utf-8")
        results.append(dict(name=name, exit=r.returncode, seconds=round(time.perf_counter() - start, 3),
                            log=f"{name}.log"))
    return results


def fresh(root):
    runtime = Runtime(root / "core.sqlite3")
    install(runtime, PARENTS, PARENT_CASES)
    return runtime


def spent(runtime, budget):
    return runtime.resources.budget(budget, "dev")["spent"]["attempts"]


def experiment(root):
    report = {}
    # 1. Search baselines on identical catalogues: typed BFS vs memoized typed BFS.
    for mode in ("typed", "memoized"):
        with tempfile.TemporaryDirectory(dir=root) as d:
            runtime = fresh(Path(d))
            dev = runtime.resources.create_budget("dev", {"attempts": 400})
            val = runtime.resources.create_budget("dev", {"attempts": 80})
            start = time.perf_counter()
            result = CompositionSearch(runtime).acquire(DEMAND, "dev", dev, ADMISSION, validation_budget=val, mode=mode)
            elapsed = time.perf_counter() - start
            trials = runtime.store.find("construction")
            report[f"search-{mode}"] = dict(
                status=result["status"],
                path=[ref.split(":")[0] for ref in result.get("path", [])],
                search_attempts=spent(runtime, dev), validation_attempts=spent(runtime, val),
                seconds=round(elapsed, 3),
                trials={s: sum(t["status"] == s for t in trials) for s in sorted({t["status"] for t in trials})},
                parents_unchanged=all(runtime.manifest()["bindings"][r].startswith(n + "@")
                                      for r, n in PARENTS.items()))
            runtime.close()
    # 2. Competing compositions published side by side, measured on growing inputs.
    with tempfile.TemporaryDirectory(dir=root) as d:
        runtime = fresh(Path(d))
        dev = runtime.resources.create_budget("dev", {"attempts": 2000})
        val = runtime.resources.create_budget("dev", {"attempts": 80})
        search = CompositionSearch(runtime)
        first = search.acquire(DEMAND, "dev", dev, ADMISSION, validation_budget=val)
        alt = CapabilityDemand("csv-sum-alt", "text", "integer", DEMAND.development_examples)
        second = search.acquire(alt, "dev", dev, ADMISSION, validation_budget=val,
                                exclude_paths=(tuple(first["path"]),))
        competitors = {"csv-sum": first, "csv-sum-alt": second}
        sizes, repeats, timing = (1, 100, 2000), 5, {}
        for role, acquired in competitors.items():
            label = "+".join(ref.split("@")[0] for ref in acquired["path"])
            rows = []
            for n in sizes:
                value = ",".join(str(i) for i in range(n))
                durations, outputs = [], set()
                for _ in range(repeats):
                    task = runtime.tasks.create_task("dev", role, value, dev)
                    token = runtime.tasks.authorize(task, "dev")
                    start = time.perf_counter()
                    outputs.add(runtime.tasks.run_task(task, token, "dev"))
                    durations.append(time.perf_counter() - start)
                durations.sort()
                rows.append(dict(n=n, median_ms=round(1000 * durations[len(durations) // 2], 2),
                                 correct=outputs == {sum(range(n))}))
            timing[role] = dict(composition=label, rows=rows)
        report["competition"] = dict(acquired=[first["status"], second["status"]], repeats=repeats, timing=timing,
                                     note="Each run is a fresh provider subprocess per node; process start-up "
                                          "dominates, so differences between sum and sum_loop are within noise "
                                          "unless the measured medians separate clearly.")
        runtime.close()
    return report


def main():
    out = Path(sys.argv[1]).resolve() / "corrected"
    out.mkdir(parents=True, exist_ok=True)
    state = ROOT / ".brainos" / "results" / out.parent.name / "corrected"
    state.mkdir(parents=True, exist_ok=True)
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    dirty = bool(subprocess.check_output(["git", "status", "--porcelain", "src", "tests"], cwd=ROOT, text=True).strip())
    suites = run_suites(out, state)
    exp = experiment(state)
    (out / "composition-experiment.json").write_text(json.dumps(exp, indent=2), encoding="utf-8")
    summary = dict(base_commit=commit, working_tree_modified=dirty, python=sys.version.split()[0],
                   platform=platform.platform(), sqlite=sqlite3.sqlite_version, suites=suites,
                   experiment="composition-experiment.json")
    (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(dict(summary, experiment=exp), indent=2))
    return 0 if all(s["exit"] == 0 for s in suites) else 1


if __name__ == "__main__":
    sys.exit(main())
