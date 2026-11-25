"""X3: execution-profile benchmark (see PREREGISTRATION.md).

    py tools/bench_runners.py [out.json]
"""
from pathlib import Path
import json
import random
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from brainos import providers  # noqa: E402
from brainos.runner import PROFILES, make_runner  # noqa: E402

FIELDS = ("startup_ns", "serialize_ns", "transport_ns", "compute_ns", "total_ns")


def p3_request():
    rng = random.Random(2026)
    data = [rng.randrange(100000) for _ in range(5000)]
    queries = []
    for _ in range(400):
        width = rng.randint(1000, 3000)
        lo = rng.randint(0, 100000 - width)
        queries.append([lo, lo + width])
    return {"data": data, "queries": queries}


def bench(repetitions=30):
    workloads = {"sum": [1, 2, 3], "range_bisect": p3_request()}
    report = {}
    for profile in PROFILES:
        runner = make_runner(profile)
        try:
            for name, value in workloads.items():
                spec = providers.specification(name)
                first = []
                runner.compute(spec, value, 30, on_timing=first.append)      # warm-up
                timings = []
                for _ in range(repetitions):
                    runner.compute(spec, value, 30, on_timing=timings.append)
                report.setdefault(profile, {})[name] = dict(
                    first_call_startup_ms=round(first[0]["startup_ns"] / 1e6, 3),
                    **{f"median_{f[:-3]}_us": round(statistics.median(t[f] for t in timings) / 1e3, 1) for f in FIELDS})
        finally:
            runner.close()
    sub, per = report["subprocess"]["sum"]["median_total_us"], report["persistent"]["sum"]["median_total_us"]
    report["proposed_target"] = dict(claim="persistent median total for sum < 20% of subprocess",
                                     ratio=round(per / sub, 4), met=per < 0.2 * sub)
    return report


def main():
    report = bench()
    text = json.dumps(report, indent=1)
    if len(sys.argv) > 1:
        Path(sys.argv[1]).write_text(text, encoding="utf-8")
    print(text)
    return 0 if report["proposed_target"]["met"] else 1


if __name__ == "__main__":
    sys.exit(main())
