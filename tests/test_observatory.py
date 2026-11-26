"""Unified observatory executor: every policy decision goes through a
kernel gate, and every gate refusal is reported, never silent (R-07-13).

Happy paths that need verified kernel assessments are demonstrated
end-to-end in tools/run_adr.py; these tests pin the fail-closed
branches deterministically.
"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "live"))
import server as S  # noqa: E402

from brainos import Refused, Runtime  # noqa: E402
from brainos.devcontext import development_context  # noqa: E402
from brainos.development_policy import PolicyState, ViabilityPolicy  # noqa: E402
from brainos.ecology import EcologyPolicy  # noqa: E402


class ExecutorHarness(unittest.TestCase):
    def setUp(self):
        self._saved = dict(S.STATE)
        S.STATE.clear()
        self.temp = tempfile.TemporaryDirectory()
        self.rt = Runtime(Path(self.temp.name) / "c.db", profile="inprocess")
        self.ctx = development_context(self.rt)
        self.cap = self.rt.population.define("mock-text", "text", "text",
                                             [("a", "a")])
        pid = self.rt.registry.register("normalize_ws")
        self.dev = self.rt.resources.create_budget("dev", {"attempts": 5000})
        self.exe = self.rt.resources.create_budget("dev", {"attempts": 5000})
        self.rt.population.admit(self.cap, pid, budget=self.dev, principal="dev")
        self.pid = pid
        self.rcap = self.rt.population.define(
            "range-count", "range-batch", "integers",
            [({"data": [1, 5, 9], "queries": [[0, 5]]}, [2])])
        self.scan = self.rt.registry.register("range_scan")
        self.hash = self.rt.registry.register("range_hash")
        self.rt.population.admit(self.rcap, self.scan,
                                 budget=self.dev, principal="dev")
        self.rt.population.admit(self.rcap, self.hash,
                                 budget=self.dev, principal="dev")
        S.STATE.update(rt=self.rt, ctx=self.ctx,
                       caps={"mock-text": self.cap, "range-count": self.rcap},
                       dev=self.dev, execution=self.exe,
                       policy_state=PolicyState(), policy=ViabilityPolicy(),
                       policies={}, recent={}, last_demand={},
                       stats={"demanded": {}, "served": {}}, decisions=[],
                       deficiencies=[], org={}, viability={}, dev_left={},
                       phase="stable", states=[], tick=0,
                       acquiring={}, acquisitions=[], nov={},
                       recovering=False, budget_refused=False, stop=False)

    def tearDown(self):
        self.rt.close()
        self.temp.cleanup()
        S.STATE.clear()
        S.STATE.update(self._saved)

    def decide(self, action, target, evidence=None):
        return dict(action=action, target=target, capability=target,
                    kind="mock-text", value="a", expected="a",
                    reason="probe", evidence=dict(evidence or {}))


class TestExecutorDecisions(ExecutorHarness):
    """Every decision executes through a kernel gate or is refused loudly."""

    def test_suspend_without_assessment_abstains(self):
        out = S.execute_decision(self.rt, 1, self.decide("suspend", self.cap,
                                                         {"suspended": self.pid}), {})
        self.assertTrue(out.startswith("abstained"))

    def test_suspend_with_unknown_assessment_is_refused(self):
        out = S.execute_decision(self.rt, 1, self.decide(
            "suspend", self.cap, {"suspended": self.pid, "assessment": "nope"}), {})
        self.assertTrue(out.startswith("refused"))

    def test_retire_without_assessment_abstains(self):
        out = S.execute_decision(self.rt, 1, self.decide("retire", self.cap,
                                                         {"retired": self.pid}), {})
        self.assertTrue(out.startswith("abstained"))

    def test_retire_unknown_member_is_refused(self):
        out = S.execute_decision(self.rt, 1, self.decide(
            "retire", self.cap, {"retired": "ghost", "assessment": "nope"}), {})
        self.assertTrue(out.startswith("refused"))

    def test_regenerate_without_member_abstains(self):
        out = S.execute_decision(self.rt, 1, self.decide("regenerate", self.cap,
                                                         {}), {})
        self.assertTrue(out.startswith("abstained"))

    def test_regenerate_active_member_is_refused(self):
        out = S.execute_decision(self.rt, 1, self.decide(
            "regenerate", self.cap, {"regenerated": self.pid}), {})
        self.assertTrue(out.startswith("refused"))

    def test_recruit_without_dormant_abstains(self):
        out = S.execute_decision(self.rt, 1, self.decide("recruit", self.cap, {}),
                                 {})
        self.assertTrue(out.startswith("abstained"))

    def test_assimilate_without_parents_abstains(self):
        out = S.execute_decision(self.rt, 1, self.decide("assimilate",
                                                          self.rcap, {}), {})
        self.assertTrue(out.startswith("abstained"))

    def test_assimilate_single_parent_abstains(self):
        out = S.execute_decision(self.rt, 1, self.decide("assimilate", self.rcap, {
            "parents": [{"capability": self.rcap, "provider": self.scan}]}), {})
        self.assertTrue(out.startswith("abstained"))

    def test_assimilate_two_servable_parents_surfaces(self):
        out = S.execute_decision(self.rt, 1, self.decide("assimilate", self.rcap, {
            "parents": [{"capability": self.rcap, "provider": self.scan},
                        {"capability": self.rcap, "provider": self.hash}]}), {})
        self.assertTrue(out.startswith("surfaced"), out)

    def test_unknown_action_is_not_silent_success(self):
        out = S.execute_decision(self.rt, 1, self.decide("reorganize", self.cap,
                                                         {}), {})
        self.assertTrue(out.startswith("abstained"))

    def test_noop_and_defer_are_recorded(self):
        for action in ("noop", "defer", "continue"):
            out = S.execute_decision(self.rt, 1, self.decide(action, self.cap,
                                                             {}), {})
            self.assertEqual(out, "recorded")


if __name__ == "__main__":
    unittest.main()
