"""B46: compositional expressivity audit.

Executable witnesses for what the graph construction engine can and
cannot express.  The engine composes unary chains only
(development.definition builds n0 -> n1 -> ...; graphs.py binds exactly
one input reference per node), so supported cases must construct and
verify end to end while join/mean demands record the exact gap.
Higher-level abilities (mean, max) are construction TARGETS, never
primitives.
"""
import tempfile
import unittest
from pathlib import Path

from brainos import Runtime, providers
from brainos.__main__ import install
from brainos.development import CapabilityDemand, CompositionSearch

PARENTS = {"parse": "parse_csv", "total": "sum", "count": "count",
           "length": "text_length", "negate": "negate", "double": "double"}
PARENT_CASES = {"parse": [("1,2", [1, 2])], "total": [([1, 2], 3)],
                "count": [([1, 2], 2)], "length": [("ab", 2)],
                "negate": [(3, -3)], "double": [(3, 6)]}


class AuditCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.temp.name) / "core.sqlite3")
        install(self.r, PARENTS, PARENT_CASES)
        self.dev = self.r.resources.create_budget("dev", {"attempts": 300})
        self.val = self.r.resources.create_budget("dev", {"attempts": 60})

    def tearDown(self):
        self.r.close()
        self.temp.cleanup()

    def acquire(self, demand, admission, **kw):
        return CompositionSearch(self.r).acquire(
            demand, "dev", self.dev, admission,
            validation_budget=self.val, **kw)

    def run_role(self, role, value):
        task = self.r.tasks.create_task("dev", role, value, self.dev)
        return self.r.tasks.run_task(
            task, self.r.tasks.authorize(task, "dev"), "dev")


class TestSupportedChains(AuditCase):
    """Witnesses: multi-stage unary composition, serving included."""

    def test_three_stage_chain_verifies_and_serves(self):
        demand = CapabilityDemand("csv-negsum", "text", "integer",
                                  (("1,2", -3), ("5,5", -10)),
                                  max_depth=3)
        out = self.acquire(demand, [(("4,5", -9)), (("", 0)), (("7", -7))])
        self.assertEqual(out["status"], "ACQUIRED")
        self.assertEqual(self.run_role("csv-negsum", "1,2,3"), -6)

    def test_cumulative_reuse_of_acquired_graph(self):
        first = self.acquire(
            CapabilityDemand("csv-sum", "text", "integer",
                             (("1,2,3", 6), ("10,-4", 6))),
            [(("4,5", 9)), (("", 0)), (("7", 7))])
        self.assertEqual(first["status"], "ACQUIRED")
        second = self.acquire(
            CapabilityDemand("csv-dblsum", "text", "integer",
                             (("1,2", 6), ("3,3", 12))),
            [(("4,5", 18))],
            cumulative=True)
        self.assertEqual(second["status"], "ACQUIRED")
        self.assertIn(first["provider"], second["path"])
        self.assertEqual(self.run_role("csv-dblsum", "1,2,3"), 12)


class TestGapRecords(AuditCase):
    """B46 gap records: exact boundary between supported and missing."""

    def test_join_is_unrepresentable(self):
        # No chain over this vocabulary yields (6, 17): the sum and the
        # length must be JOINED, and nodes bind exactly one input
        # reference (graphs.py).  Unary search must abstain honestly.
        demand = CapabilityDemand("len_plus_sum", "text", "integer",
                                  (("1,2", 6), ("3,4,5", 17)))
        out = self.acquire(demand, [(("0,0", 0))])
        self.assertEqual(out["status"], "NON_ATTAINMENT")

    def test_mean_needs_division_primitive(self):
        # B46: mean = sum/count/div is a construction TARGET.  While no
        # division primitive exists the demand must abstain; if division
        # lands, this test fails loudly so the target gets promoted.
        self.assertFalse(hasattr(providers, "divide"),
                         "gap closed: division primitive exists; "
                         "promote mean to a construction-target witness")
        demand = CapabilityDemand("csv-mean", "text", "integer",
                                  (("10,20,30", 20), ("2,4", 3)))
        out = self.acquire(demand, [(("6,6,6", 6))])
        self.assertEqual(out["status"], "NON_ATTAINMENT")

    def test_unreachable_demand_abstains(self):
        # 999 is not reachable from text_length via negate/double, and
        # parse_csv rejects non-numeric text: honest abstention.
        demand = CapabilityDemand("magic", "text", "integer", (("a", 999),))
        out = self.acquire(demand, [(("b", 999))])
        self.assertEqual(out["status"], "NON_ATTAINMENT")


if __name__ == "__main__":
    unittest.main()
