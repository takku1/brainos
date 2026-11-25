"""ADR coordination core: declared bands (R-25-08), evidence-grounded
observation (R-25-08) and the replaceable developmental policy (R-07-13).

The policy proposes; it never executes. Every test below asserts on
proposals and records, never on performed transformations.
"""
import sys
import tempfile
import unittest
from pathlib import Path

from brainos import Refused, Runtime
from brainos.devcontext import development_context
from brainos import development_policy as policy


class PolicyHarness(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.temp.name) / "c.db", profile="inprocess")
        self.ctx = development_context(self.r)
        self.val = self.r.resources.create_budget("dev", {"attempts": 5000})

    def tearDown(self):
        self.r.close()
        self.temp.cleanup()

    def admit_text(self, name="t", cases=(("a", "a"),)):
        cap = self.r.population.define(name, "text", "text", list(cases))
        pid = self.r.registry.register("normalize_ws")
        self.r.population.admit(cap, pid, budget=self.val, principal="dev")
        return cap, pid


class TestBands(PolicyHarness):
    """R-25-08: viability variables with declared bands and hysteresis."""

    def test_all_doc33_variables_declared(self):
        bands = policy.default_bands()
        self.assertEqual(sorted(bands), sorted(["coverage", "retention",
                                                "budget_runway", "maintenance_share",
                                                "development_spend", "population",
                                                "churn", "recovery"]))

    def test_bands_have_hysteresis_and_cooldowns(self):
        bands = policy.default_bands()
        self.assertLess(bands["coverage"]["exit"], bands["coverage"]["enter"])
        self.assertIn("cooldown_steps", bands["development_spend"])
        self.assertIn("cooldown_steps", bands["churn"])

    def test_custom_floor_changes_proposals(self):
        cap, _ = self.admit_text()
        obs = policy.build_observation(self.ctx, [cap],
                                       budgets=[(self.val, "dev")])
        strict = dict(policy.default_bands())
        strict["budget_runway"] = dict(floor_periods=10 ** 9, enter=10 ** 9,
                                       exit=10 ** 9 + 1)
        strict_policy = policy.ViabilityPolicy(bands=strict)
        self.assertEqual(strict_policy.propose(obs, self.ctx)["action"], "defer")
        self.assertEqual(policy.ViabilityPolicy().propose(obs, self.ctx)["action"],
                         "noop")


class TestObservation(PolicyHarness):
    """R-25-08: observation derives from kernel records, unknowns labeled."""

    def test_active_membership_observed_with_cited_records(self):
        cap, pid = self.admit_text()
        obs = policy.build_observation(self.ctx, [cap])
        members = obs["capabilities"][cap]["members"]
        self.assertEqual(members["status"], "observed")
        self.assertEqual(members["ACTIVE"], 1)
        self.assertIn(f"{cap}|{pid}", members["records"])
        self.assertEqual(obs["capabilities"][cap]["demanded"]["value"], False)

    def test_demands_and_runway_observed(self):
        cap, _ = self.admit_text()
        obs = policy.build_observation(self.ctx, [cap],
                                       budgets=[(self.val, "dev")],
                                       demands=[cap])
        self.assertEqual(obs["capabilities"][cap]["demanded"]["value"], True)
        runway = obs["runway"][self.val]
        self.assertEqual(runway["status"], "observed")
        self.assertGreaterEqual(runway["available"], 0)

    def test_unreachable_state_reported_unknown(self):
        cap, _ = self.admit_text()
        obs = policy.build_observation(self.ctx, [cap])
        self.assertEqual(obs["recovery"]["status"], "unknown")

    def test_unknown_budget_labeled_not_guessed(self):
        cap, _ = self.admit_text()
        obs = policy.build_observation(self.ctx, [cap],
                                       budgets=[("nope", "dev")])
        self.assertEqual(obs["runway"]["nope"]["status"], "unknown")


class TestPolicy(PolicyHarness):
    """R-07-13: the policy proposes through evidence; it never executes."""

    def test_base_policy_abstains(self):
        cap, _ = self.admit_text()
        obs = policy.build_observation(self.ctx, [cap], demands=[cap])
        decision = policy.DevelopmentalPolicy().propose(obs, self.ctx)
        self.assertEqual(decision["action"], "noop")

    def test_noop_policy_defers_with_reason(self):
        cap, _ = self.admit_text()
        obs = policy.build_observation(self.ctx, [cap])
        decision = policy.NoopPolicy().propose(obs, self.ctx)
        self.assertEqual(decision["action"], "defer")
        self.assertTrue(decision["reason"])

    def test_unserved_demand_proposes_investigation(self):
        cap = self.r.population.define("u", "text", "text", [("a", "a")])
        obs = policy.build_observation(self.ctx, [cap], demands=[cap])
        decision = policy.ViabilityPolicy().propose(obs, self.ctx)
        self.assertEqual(decision["action"], "investigate")
        self.assertEqual(decision["target"], cap)

    def test_dormant_competence_proposes_recruit(self):
        cap, _ = self.admit_text()
        obs = dict(capabilities={cap: dict(
            members=dict(ACTIVE=0, DORMANT=1, ARCHIVED=0, status="observed",
                         source="member rows", records=[cap + "|probe"]),
            retention=dict(status="observed", source="retention-assessment rows",
                           count=1),
            demanded=dict(status="observed", value=True))},
            runway={}, churn={}, recovery={})
        decision = policy.ViabilityPolicy().propose(obs, self.ctx)
        self.assertEqual(decision["action"], "recruit")
        self.assertEqual(decision["target"], cap)
        self.assertIn(cap + "|probe", decision["evidence"]["member_rows"])

    def test_served_organization_proposes_noop(self):
        cap, _ = self.admit_text()
        obs = policy.build_observation(self.ctx, [cap], demands=[cap],
                                       budgets=[(self.val, "dev")])
        decision = policy.ViabilityPolicy().propose(obs, self.ctx)
        self.assertEqual(decision["action"], "noop")

    def test_unknown_action_is_refused(self):
        with self.assertRaises(Refused):
            policy.decide("assimilate-everything")

    def test_propose_performs_no_writes(self):
        cap, _ = self.admit_text()
        before = len(self.ctx.find("candidate"))
        obs = policy.build_observation(self.ctx, [cap], demands=[cap])
        policy.ViabilityPolicy().propose(obs, self.ctx)
        self.assertEqual(len(self.ctx.find("candidate")), before)
        self.assertEqual(self.r.population.state(cap, self.r.registry.register(
            "normalize_ws")), "ACTIVE")


class TestDecisionRecord(PolicyHarness):
    """R-07-13: decisions are journaled; execution stays with the kernel."""

    def test_record_decision_journals_through_context(self):
        decision = policy.decide("noop", reason="stable",
                                 evidence={"policy": "test"})
        policy.record_decision(self.ctx, decision, "d1")
        stored = self.ctx.get("ecology-decision", "d1")
        self.assertEqual(stored["action"], "noop")
        self.assertEqual(stored["reason"], "stable")

    def test_record_unknown_action_refused(self):
        with self.assertRaises(Refused):
            policy.record_decision(self.ctx, dict(action="nope"), "d2")

    def test_policy_versions_are_pinned(self):
        versions = {policy.DevelopmentalPolicy.version,
                    policy.NoopPolicy.version,
                    policy.ViabilityPolicy.version}
        self.assertEqual(len(versions), 3)


if __name__ == "__main__":
    unittest.main()
