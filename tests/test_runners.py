"""Execution profiles share one contract: same checks, same outputs, visible failures."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from brainos import Refused, Runtime
from brainos.__main__ import install
from brainos import providers
from brainos.runner import PROFILES, make_runner

WORKLOAD = {"data": [5, 1, 9, 3, 3], "queries": [[0, 3], [3, 9], [10, 20]]}


class RunnerProfiles(unittest.TestCase):
    def setUp(self):
        self.runners = {p: make_runner(p) for p in PROFILES}

    def tearDown(self):
        for runner in self.runners.values():
            runner.close()

    def test_identical_outputs_and_timing_fields(self):
        expected = {}
        for name in ("sum", "range_scan", "range_scan_list", "range_bisect", "range_hash"):
            spec = providers.specification(name)
            value = [1, 2, 3] if name == "sum" else WORKLOAD
            for profile, runner in self.runners.items():
                timings = []
                out = runner.compute(spec, value, 10, on_timing=timings.append)
                expected.setdefault(name, out)
                with self.subTest(name=name, profile=profile):
                    self.assertEqual(out, expected[name])
                    self.assertEqual(set(timings[0]), {"profile", "provider", "compute_ns", "serialize_ns",
                                                       "transport_ns", "startup_ns", "total_ns", "prepare_ns",
                                                       "answer_ns", "cache_hit", "state_bytes"})
                    self.assertEqual(timings[0]["profile"], profile)
        self.assertEqual(expected["range_hash"], [3, 4, 0])   # [0,3]: 1,3,3  [3,9]: 5,9,3,3

    def test_every_profile_refuses_forged_artifacts_and_bad_inputs(self):
        spec = providers.specification("sum")
        forged = dict(spec, artifact="0" * 64)
        for profile, runner in self.runners.items():
            with self.subTest(profile=profile):
                with self.assertRaisesRegex(Refused, "artifact"):
                    runner.compute(forged, [1], 10)
                with self.assertRaises(Refused):
                    runner.compute(spec, [True], 10)
                with self.assertRaises(Refused):
                    runner.compute(spec, list(range(4097)), 10)
                big = dict(data=list(range(20001)), queries=[])
                with self.assertRaises(Refused):
                    runner.compute(providers.specification("range_scan"), big, 10)

    def test_persistent_worker_is_reused(self):
        runner = self.runners["persistent"]
        spec = providers.specification("sum")
        timings = []
        for _ in range(5):
            runner.compute(spec, [1, 2], 10, on_timing=timings.append)
        self.assertEqual(runner.starts, 1)
        self.assertGreater(timings[0]["startup_ns"], 0)
        self.assertTrue(all(t["startup_ns"] == 0 for t in timings[1:]))

    def test_runtime_profiles_record_invocation_timing(self):
        for profile in PROFILES:
            with self.subTest(profile=profile), tempfile.TemporaryDirectory() as d:
                with Runtime(Path(d) / "c.db", profile=profile) as r:
                    install(r, {"total": "sum"}, {"total": [([1, 2], 3)]})
                    budget = r.resources.create_budget("alice", {"attempts": 4})
                    task = r.tasks.create_task("alice", "total", [1, 2], budget)
                    self.assertEqual(r.tasks.run_task(task, r.tasks.authorize(task, "alice"), "alice"), 3)
                    invocation = r.tasks.invocation(r.tasks.task(task, "alice")["invocation"], "alice")
                    self.assertEqual(invocation["profile"], profile)
                    self.assertGreater(invocation["total_ns"], 0)
                    self.assertEqual(len(invocation["timings"]), 1)

    def test_unknown_profile_refused(self):
        with self.assertRaises(Refused):
            make_runner("gpu")


HEAVY = {"data": list(range(20000)), "queries": [[0, 20000]] * 2000}   # ~1-2 s of scanning
SCAN_CASES = {"scan": [({"data": [1, 5], "queries": [[0, 2]]}, [1])]}


class RunnerFailureVisibility(unittest.TestCase):
    def test_persistent_timeout_kills_restarts_and_is_journaled(self):
        with tempfile.TemporaryDirectory() as d, Runtime(Path(d) / "c.db", profile="persistent") as r:
            install(r, {"scan": "range_scan"}, SCAN_CASES)
            budget = r.resources.create_budget("alice", {"attempts": 4})
            starts = r.runner.starts
            task = r.tasks.create_task("alice", "scan", HEAVY, budget, timeout=0.2)
            with self.assertRaisesRegex(Refused, "wall-clock"):
                r.tasks.run_task(task, r.tasks.authorize(task, "alice"), "alice")
            record = r.tasks.task(task, "alice")
            self.assertEqual(record["state"], "FAILED")
            self.assertIn("wall-clock", r.tasks.invocation(record["invocation"], "alice")["error"])
            stopped = [e for e in r.store.journal() if e["kind"] == "worker-stopped"]
            self.assertEqual(stopped[-1]["reason"], "timeout")
            self.assertIsNone(r.runner.process)
            task = r.tasks.create_task("alice", "scan", {"data": [1, 5], "queries": [[0, 2]]}, budget)
            self.assertEqual(r.tasks.run_task(task, r.tasks.authorize(task, "alice"), "alice"), [1])
            self.assertEqual(r.runner.starts, starts + 1)                # a fresh worker served it

    def test_persistent_worker_death_fails_closed_then_recovers(self):
        runner = make_runner("persistent")
        try:
            spec = providers.specification("sum")
            self.assertEqual(runner.compute(spec, [1], 10), 1)
            runner.process.kill()
            runner.process.wait(5)
            self.assertEqual(runner.compute(spec, [2], 10), 2)        # dead worker detected and replaced
            self.assertEqual(runner.starts, 2)
        finally:
            runner.close()

    def test_inprocess_overrun_is_refused_after_completion(self):
        runner = make_runner("inprocess")
        heavy = {"data": list(range(5000)), "queries": [[0, 5000]] * 200}
        with self.assertRaisesRegex(Refused, "wall-clock"):
            runner.compute(providers.specification("range_scan"), heavy, 0.001)


if __name__ == "__main__":
    unittest.main()
