"""W1 instruments: emergence meter, organizational-capability test, net-value ledger.

Positive controls show each instrument detecting the property it names;
negative controls show it refusing or reporting the absence honestly.
"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import run_retention  # noqa: E402

from brainos import Refused, Runtime  # noqa: E402
from brainos import emergence  # noqa: E402
from brainos.__main__ import install  # noqa: E402
from brainos.development import CapabilityDemand, CompositionSearch  # noqa: E402

PARENTS = {"parse": "parse_csv", "total": "sum", "total_loop": "sum_loop", "count": "count",
           "length": "text_length", "negate": "negate", "double": "double"}
PARENT_CASES = {"parse": [("1,2", [1, 2])], "total": [([1, 2], 3)], "total_loop": [([1, 2], 3)],
                "count": [([1, 2], 2)], "length": [("ab", 2)], "negate": [(3, -3)],
                "double": [(3, 6)]}
GEN1 = CapabilityDemand("csv-sum", "text", "integer", (("1,2,3", 6), ("10, -4", 6)))
GEN1_CASES = [("4,5", 9), ("", 0), ("7", 7)]
RANGE_SINGLE = {"data": list(range(0, 100000, 25)), "queries": [[1000, 60000]]}


def member_tasks(rt, capability, provider, values, budget, principal="dev"):
    tasks = []
    for value in values:
        task = rt.tasks.create_member_task(principal, capability, provider, value, budget)
        rt.tasks.run_task(task, rt.tasks.authorize(task, principal), principal)
        tasks.append(task)
    return tasks


class CsvCase(unittest.TestCase):
    """Two different composites serve csv-sum; no single primitive can."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.temp.name) / "c.db", profile="inprocess")
        install(self.r, PARENTS, PARENT_CASES)
        self.dev = self.r.resources.create_budget("dev", {"attempts": 6000})
        self.val = self.r.resources.create_budget("dev", {"attempts": 2000})
        self.search = CompositionSearch(self.r)
        first = self.search.acquire(GEN1, "dev", self.dev, GEN1_CASES,
                                    validation_budget=self.val, cumulative=True)
        self.assertEqual(first["status"], "ACQUIRED")
        second = self.search.acquire(GEN1, "dev", self.dev, GEN1_CASES,
                                    validation_budget=self.val, cumulative=True,
                                    exclude_paths=[tuple(first["path"])])
        self.assertEqual(second["status"], "ACQUIRED")
        self.assertNotEqual(first["provider"], second["provider"])
        self.cap = first["capability"]
        self.g1, self.g2 = first["provider"], second["provider"]

    def tearDown(self):
        self.r.close()
        self.temp.cleanup()


class Meter(CsvCase):
    def test_full_coverage_single_serving_path(self):
        tasks = member_tasks(self.r, self.cap, self.g1, ["1,2,3", "10, -4"], self.dev)
        report = emergence.measure(self.r.store, self.cap, tasks)
        self.assertEqual(report["C"]["coverage"], 1.0)
        self.assertEqual(report["N"]["active"], 2)
        self.assertEqual(len(report["N"]["composites"]), 2)
        self.assertEqual(report["N"]["blocked"], [])
        self.assertEqual(report["Q"]["mean_regret"], 0.0)
        self.assertEqual(report["Q"]["unserved"], 0)
        self.assertEqual(report["L"]["retained"], 1.0)
        # Both composites were acquired before the window opened, so the
        # window-scoped turnover is empty: the meter does not leak the past.
        self.assertEqual(report["V"],
                         dict(acquisitions=0, regenerations=0, dormancies=0, wakes=0,
                              retirements=0, assimilations=0))
        self.assertIsNone(report["reuse"]["fraction"])
        self.assertGreater(report["complexity"]["transitive_edges"], 0)
        self.assertEqual(report["meta"]["window_tasks"], tasks)
        self.assertLessEqual(*report["meta"]["journal_span"])
        for name in emergence.NOV_COSTS:
            key = {"compute": "compute_ns", "overhead": "overhead_ns",
                   "construction": "construction", "validation": "validation",
                   "assessment": "assessment_ns", "maintenance": "maintenance_units"}[name]
            self.assertIn(key, report["R"])
        self.assertEqual(report["R"]["outstanding_holdings"], [])

    def test_latency_floor_binds(self):
        tasks = member_tasks(self.r, self.cap, self.g1, ["1,2,3"], self.dev)
        over = emergence.measure(self.r.store, self.cap, tasks, latency_floor_ns=0)
        self.assertEqual(over["C"]["coverage"], 0.0)
        under = emergence.measure(self.r.store, self.cap, tasks,
                                  latency_floor_ns=10 ** 18)
        self.assertEqual(under["C"]["coverage"], 1.0)

    def test_window_must_be_one_capability_and_closed(self):
        tasks = member_tasks(self.r, self.cap, self.g1, ["1,2,3"], self.dev)
        other = self.r.population.define("other", "text", "integer", GEN1_CASES)
        with self.assertRaisesRegex(Refused, "mixes capabilities"):
            emergence.measure(self.r.store, other, tasks)
        pending = self.r.tasks.create_member_task("dev", self.cap, self.g1, "1,2", self.dev)
        with self.assertRaisesRegex(Refused, "not closed"):
            emergence.measure(self.r.store, self.cap, [pending])


class MeterCosts(unittest.TestCase):
    """Every R bucket captures activity inside the window and nothing outside."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.temp.name) / "c.db", profile="inprocess")
        self.cap, self.ids, self.exec_budget = run_retention.setup(self.r)
        self.scan = self.ids["range_scan"]
        self.bisect = self.ids["range_bisect"]

    def tearDown(self):
        self.r.close()
        self.temp.cleanup()

    def test_all_cost_buckets_are_window_scoped(self):
        first = run_retention.run_member(self.r, self.cap, self.scan,
                                         RANGE_SINGLE, self.exec_budget)
        upkeep = self.r.resources.create_budget("eco", {"maintenance": 10 ** 6})
        install(self.r, {"parse": "parse_csv", "total": "sum"},
                {"parse": [("1,2", [1, 2])], "total": [([1, 2], 3)]})
        search_budget = self.r.resources.create_budget("dev", {"attempts": 6000})
        val_budget = self.r.resources.create_budget("dev", {"attempts": 2000})
        search = CompositionSearch(self.r)
        acquired = search.acquire(GEN1, "dev", search_budget, GEN1_CASES,
                                 validation_budget=val_budget, cumulative=True)
        self.assertEqual(acquired["status"], "ACQUIRED")
        cited = [first["invocation"]]
        assessment = self.r.population.assess(self.cap, self.scan, cited)
        self.assertIn("wall_ns", assessment)
        for provider in self.ids.values():
            self.r.population.set_maintenance(self.cap, provider, active=7, dormant=3)
        self.r.population.maintain(self.cap, upkeep, "eco", charge=self.r.resources.charge)
        second = run_retention.run_member(self.r, self.cap, self.bisect,
                                          RANGE_SINGLE, self.exec_budget)
        tasks = [self.r.tasks.invocation(first["invocation"], "eco")["task"],
                   self.r.tasks.invocation(second["invocation"], "eco")["task"]]
        report = emergence.measure(self.r.store, self.cap, tasks)
        self.assertGreater(sum(report["R"]["construction"].values()), 0)
        self.assertGreater(sum(report["R"]["validation"].values()), 0)
        self.assertGreater(report["R"]["assessment_ns"], 0)
        self.assertGreater(report["R"]["maintenance_units"], 0)
        self.assertGreater(report["R"]["compute_ns"], 0)
        self.assertGreaterEqual(report["R"]["overhead_ns"], 0)
        # Both demand epochs are competently served by an active member.
        self.assertEqual(report["L"]["retained"], 1.0)
        self.assertEqual(set(report["D"]), {"single-wide"})
        self.assertGreaterEqual(len(report["D"]["single-wide"]["covering"]), 1)
        self.assertIn(report["D"]["single-wide"]["structural_independence"], (None, 0.0))
        self.assertEqual(report["D"]["single-wide"]["observed_joint_failures"], 0)


class MeterJournal(unittest.TestCase):
    """Turnover counts follow the journal span, including crafted events."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.temp.name) / "c.db", profile="inprocess")
        self.cap, self.ids, self.exec_budget = run_retention.setup(self.r)

    def tearDown(self):
        self.r.close()
        self.temp.cleanup()

    def test_turnover_counts_span_events(self):
        first = run_retention.run_member(self.r, self.cap, self.ids["range_scan"],
                                         RANGE_SINGLE, self.exec_budget)
        ghost = "ghost-provider@0:abc"
        with self.r.store.transaction():
            self.r.store.event("member-admitted", capability=self.cap, provider=ghost)
            self.r.store.event("member-retired", capability=self.cap, provider=ghost)
            self.r.store.event("member-admitted", capability=self.cap, provider=ghost)
            self.r.store.event("member-dormant", capability=self.cap, provider=ghost)
            self.r.store.event("member-woke", capability=self.cap, provider=ghost)
            self.r.store.event("member-retired", capability=self.cap, provider=ghost)
            self.r.store.event("assimilation-published", assimilation="a:1", revision=3)
        second = run_retention.run_member(self.r, self.cap, self.ids["range_bisect"],
                                          RANGE_SINGLE, self.exec_budget)
        tasks = [self.r.tasks.invocation(first["invocation"], "eco")["task"],
                   self.r.tasks.invocation(second["invocation"], "eco")["task"]]
        report = emergence.measure(self.r.store, self.cap, tasks)
        self.assertEqual(report["V"]["acquisitions"], 2)
        self.assertEqual(report["V"]["regenerations"], 1)
        self.assertEqual(report["V"]["dormancies"], 1)
        self.assertEqual(report["V"]["wakes"], 1)
        self.assertEqual(report["V"]["retirements"], 2)
        self.assertEqual(report["V"]["assimilations"], 1)

    def test_journal_survives_event_body_seq_fields(self):
        # EcologyService records decisions with their own `seq` counter; the
        # journal's ordering key must win without crashing (kernel root fix).
        with self.r.store.transaction():
            self.r.store.event("ecology-decision", ecology="e:1", seq=41)
        journal = self.r.store.journal()
        decisions = [e for e in journal if e["kind"] == "ecology-decision"]
        self.assertEqual(len(decisions), 1)
        self.assertEqual(journal[-1]["seq"], decisions[0]["seq"])


class Verdict(CsvCase):
    def test_organizational_capability(self):
        verdict = emergence.organizational_verdict(self.r.store, self.cap)
        self.assertEqual(verdict["verdict"], "organizational")
        self.assertEqual(set(verdict["support"]), {self.g1, self.g2})
        self.assertTrue(verdict["structure_dependence"]["dependence"])
        for pid, result in verdict["substitution"].items():
            self.assertTrue(result["served_again"], pid)
            self.assertEqual(result["path"], "active-member", pid)
        self.assertGreater(verdict["checks_spent"], 0)
        # The interventions ran on store copies: the live store is untouched.
        self.assertEqual(self.r.store.find("impact"), [])
        self.assertIsNotNone(self.r.registry.resolve(self.g1))
        self.assertIsNotNone(self.r.registry.resolve(self.g2))

    def test_budget_exhaustion_is_inconclusive(self):
        verdict = emergence.organizational_verdict(self.r.store, self.cap,
                                                   development_budget=1)
        self.assertEqual(verdict["verdict"], "inconclusive-budget")
        self.assertEqual(verdict["checks_spent"], 0)
        self.assertTrue(all(v["path"] == "unverified-budget"
                            for v in verdict["substitution"].values()))

    def test_compositional_but_fragile(self):
        temp = tempfile.TemporaryDirectory()
        try:
            rt = Runtime(Path(temp.name) / "c.db", profile="inprocess")
            install(rt, PARENTS, PARENT_CASES)
            dev = rt.resources.create_budget("dev", {"attempts": 6000})
            val = rt.resources.create_budget("dev", {"attempts": 2000})
            first = CompositionSearch(rt).acquire(GEN1, "dev", dev, GEN1_CASES,
                                                  validation_budget=val, cumulative=True)
            self.assertEqual(first["status"], "ACQUIRED")
            verdict = emergence.organizational_verdict(rt.store, first["capability"])
            self.assertEqual(verdict["verdict"], "compositional-but-fragile")
            self.assertTrue(verdict["structure_dependence"]["dependence"])
            self.assertFalse(all(v["served_again"]
                                 for v in verdict["substitution"].values()))
        finally:
            rt.close()
            temp.cleanup()

    def test_verdict_needs_active_members(self):
        cap = self.r.population.define("empty-capability", "text", "integer", GEN1_CASES)
        with self.assertRaisesRegex(Refused, "no active members"):
            emergence.organizational_verdict(self.r.store, cap)


class VerdictRange(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.temp.name) / "c.db", profile="inprocess")
        self.cap, self.ids, self.exec_budget = run_retention.setup(self.r)

    def tearDown(self):
        self.r.close()
        self.temp.cleanup()

    def test_redundant_primitive_capability(self):
        verdict = emergence.organizational_verdict(self.r.store, self.cap)
        self.assertEqual(verdict["verdict"], "redundant")
        self.assertFalse(verdict["structure_dependence"]["dependence"])
        self.assertTrue(all(v["served_again"] for v in verdict["substitution"].values()))

    def test_neither(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        rt = Runtime(Path(temp.name) / "c.db", profile="inprocess")
        self.addCleanup(rt.close)
        cap = rt.population.define("range-count", "range-batch", "integers",
                                     run_retention.ADMISSION)
        pid = rt.registry.register("range_scan")
        budget = rt.resources.create_budget("eco", {"attempts": 200})
        rt.population.admit(cap, pid, budget=budget, principal="eco")
        verdict = emergence.organizational_verdict(rt.store, cap)
        self.assertEqual(verdict["verdict"], "neither")
        self.assertFalse(verdict["substitution"][pid]["served_again"])

    def _two_member(self):
        cap = self.r.population.define("pair-count", "range-batch", "integers",
                                       run_retention.ADMISSION)
        budget = self.r.resources.create_budget("eco", {"attempts": 500})
        ids = {}
        for name in ("range_scan", "range_bisect"):
            ids[name] = self.r.registry.register(name)
            self.r.population.admit(cap, ids[name], budget=budget, principal="eco")
        return cap, ids

    def _cite(self, cap, ids, value, n=3):
        cited = []
        exe = self.r.resources.create_budget("eco", {"attempts": 5000})
        for name in ids:
            for _ in range(n):
                cited.append(run_retention.run_member(self.r, cap, ids[name],
                                                      value, exe)["invocation"])
        return cited

    def test_wake_path_serves(self):
        cap, ids = self._two_member()
        cited = self._cite(cap, ids, RANGE_SINGLE)
        self.r.population.set_retention_policy(cap, margin=100.0)
        assessment = self.r.population.assess(cap, ids["range_scan"], cited)
        self.assertEqual(assessment["verdict"], "redundant")
        self.r.population.make_dormant(cap, ids["range_scan"],
                                       assessment=assessment["id"])
        verdict = emergence.organizational_verdict(self.r.store, cap)
        self.assertEqual(verdict["verdict"], "redundant")
        blocked = verdict["substitution"][ids["range_bisect"]]
        self.assertTrue(blocked["served_again"])
        self.assertEqual(blocked["path"], "wake")

    def test_regenerate_path_serves(self):
        cap, ids = self._two_member()
        cited = self._cite(cap, ids, RANGE_SINGLE)
        self.r.population.set_retention_policy(cap, margin=100.0)
        assessment = self.r.population.assess(cap, ids["range_scan"], cited)
        self.assertEqual(assessment["verdict"], "redundant")
        self.r.population.retire(cap, ids["range_scan"], assessment=assessment["id"],
                                 reason="probe")
        verdict = emergence.organizational_verdict(self.r.store, cap)
        self.assertEqual(verdict["verdict"], "redundant")
        blocked = verdict["substitution"][ids["range_bisect"]]
        self.assertTrue(blocked["served_again"])
        self.assertEqual(blocked["path"], "regenerate")


class NetValue(unittest.TestCase):
    VALUES = {"csv-sum": dict(per_request=10, late_penalty=4)}

    def costs(self, **over):
        base = dict(compute=5, overhead=1, construction=20, validation=6,
                    assessment=2, maintenance=3)
        base.update(over)
        return base

    def test_arithmetic(self):
        windows = [
            dict(served=[dict(contract="csv-sum", late=False),
                         dict(contract="csv-sum", late=True)],
                 costs=self.costs()),
            dict(served=[dict(contract="csv-sum", late=False)], costs=self.costs(compute=1)),
        ]
        result = emergence.net_value(windows, self.VALUES)
        self.assertEqual(result["windows"][0], dict(value=16, cost=37, net=-21))
        self.assertEqual(result["windows"][1], dict(value=10, cost=33, net=-23))
        self.assertEqual(result["total"], -44)

    def test_development_that_costs_more_than_it_returns_is_negative(self):
        windows = [dict(served=[dict(contract="csv-sum", late=False)],
                        costs=self.costs(construction=1000))]
        result = emergence.net_value(windows, self.VALUES)
        self.assertLess(result["total"], 0)

    def test_omitted_or_extra_components_are_refused(self):
        served = [dict(contract="csv-sum", late=False)]
        short = self.costs()
        del short["maintenance"]
        with self.assertRaisesRegex(Refused, "exactly"):
            emergence.net_value([dict(served=served, costs=short)], self.VALUES)
        long = self.costs(hidden=1)
        with self.assertRaisesRegex(Refused, "exactly"):
            emergence.net_value([dict(served=served, costs=long)], self.VALUES)

    def test_undeclared_value_and_bad_lateness_are_refused(self):
        with self.assertRaisesRegex(Refused, "no declared value"):
            emergence.net_value([dict(served=[dict(contract="mystery", late=False)],
                                          costs=self.costs())], self.VALUES)
        with self.assertRaisesRegex(Refused, "lateness"):
            emergence.net_value([dict(served=[dict(contract="csv-sum", late="yes")],
                                          costs=self.costs())], self.VALUES)
        with self.assertRaisesRegex(Refused, "at least one window"):
            emergence.net_value([], self.VALUES)

    def test_meter_report_wires_to_costs(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        rt = Runtime(Path(temp.name) / "c.db", profile="inprocess")
        self.addCleanup(rt.close)
        cap, ids, budget = run_retention.setup(rt)
        first = run_retention.run_member(rt, cap, ids["range_scan"], RANGE_SINGLE, budget)
        task = rt.tasks.invocation(first["invocation"], "eco")["task"]
        report = emergence.measure(rt.store, cap, [task])
        rate = 0.001  # declared conversion: one value-unit per thousand native units
        costs = dict(compute=report["R"]["compute_ns"] * rate,
                     overhead=report["R"]["overhead_ns"] * rate,
                     construction=sum(report["R"]["construction"].values(), 0) * rate,
                     validation=sum(report["R"]["validation"].values(), 0) * rate,
                     assessment=report["R"]["assessment_ns"] * rate,
                     maintenance=report["R"]["maintenance_units"] * rate)
        values = {"range-count": dict(per_request=1)}
        result = emergence.net_value(
            [dict(served=[dict(contract="range-count", late=False)], costs=costs)], values)
        self.assertAlmostEqual(result["total"], 1 - sum(costs.values()))
