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

    def serve(self, cap, pid, value="  padded  "):
        task = self.r.tasks.create_member_task("dev", cap, pid, value, self.val)
        self.r.tasks.run_task(task, self.r.tasks.authorize(task, "dev"), "dev")
        return task

    def full_evidence(self, name="t", step0=0, step1=5, burn_between=0):
        """A serving organization with confirmed competence, youth-implied
        retention and measured burn: the strict noop fixture (burn_between
        extra tasks run between the two observation steps)."""
        cap, pid = self.admit_text(name)
        self.r.population.set_retention_policy(cap, min_age=1000)
        tids = [self.serve(cap, pid) for _ in range(3)]
        recent = {cap: [(t, True, "default") for t in tids]}
        state = policy.PolicyState()
        kwargs = dict(budgets=[(self.val, "dev")], demands=[cap], recent=recent,
                      state=state)
        policy.build_observation(self.ctx, [cap], step=step0, **kwargs)
        for _ in range(burn_between):
            self.serve(cap, pid)
        obs = policy.build_observation(self.ctx, [cap], step=step1, **kwargs)
        return obs, state


class TestBands(PolicyHarness):
    """R-25-08: viability variables with declared bands and hysteresis."""

    def test_all_doc33_variables_declared(self):
        bands = policy.default_bands()
        self.assertEqual(sorted(bands), sorted(["coverage", "retention",
                                                "competence", "budget_runway",
                                                "maintenance_share",
                                                "development_spend", "population",
                                                "churn", "recovery"]))

    def test_bands_have_hysteresis_and_cooldowns(self):
        bands = policy.default_bands()
        self.assertLess(bands["coverage"]["exit"], bands["coverage"]["enter"])
        self.assertIn("cooldown_steps", bands["development_spend"])
        self.assertIn("cooldown_steps", bands["churn"])

    def test_custom_floor_changes_proposals(self):
        obs, state = self.full_evidence(burn_between=1)
        strict = dict(policy.default_bands())
        strict["budget_runway"] = dict(floor_periods=10 ** 9, enter=10 ** 9,
                                       exit=10 ** 9 + 1)
        strict_policy = policy.ViabilityPolicy(bands=strict)
        self.assertEqual(strict_policy.propose(obs, self.ctx, state)["action"],
                         "defer")
        self.assertEqual(policy.ViabilityPolicy().propose(obs, self.ctx, state)
                         ["action"], "noop")


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
        # B39: one snapshot cannot establish a burn rate.
        self.assertEqual(obs["runway"][self.val]["status"], "unknown")
        state = policy.PolicyState()
        policy.build_observation(self.ctx, [cap],
                                 budgets=[(self.val, "dev")],
                                 state=state, step=0)
        obs = policy.build_observation(self.ctx, [cap],
                                       budgets=[(self.val, "dev")],
                                       state=state, step=4)
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
        obs, state = self.full_evidence()
        decision = policy.ViabilityPolicy().propose(obs, self.ctx, state)
        self.assertEqual(decision["action"], "noop")
        # B43: the verdict is conditional and names what it does not cover.
        self.assertIn("recovery readiness", decision["reason"])

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


def hand_obs(cap="c", active=1, dormant=0, demanded=True, contexts=None,
             comp=None, retention=None, runway=None, step=10):
    """Hand-built observation for policy-logic unit tests."""
    comp = dict(comp) if comp else dict(status="unknown")
    retention = dict(retention) if retention else dict(status="observed",
                                                       count=0, providers={})
    members = {"ACTIVE": active, "DORMANT": dormant, "ARCHIVED": 0,
               "status": "observed", "source": "member rows", "records": []}
    caps = {cap: dict(members=members, competence=comp, retention=retention,
                      demanded=dict(status="observed", value=demanded,
                                    contexts=contexts))}
    runway = dict(runway) if runway else {}
    return dict(capabilities=caps, runway=runway,
                churn=dict(status="unknown", reason="no member history yet"),
                transitions=[], step=step,
                recovery=dict(status="unknown", reason="unseen"))


def ok_comp(n=3, rate=1.0, contexts=None):
    per = {c: dict(n=n, ok=n, attested=n, correct=n, kernel_rate=1.0,
                   correct_rate=1.0, thin=n < 3) for c in (contexts or [])}
    return dict(status="observed", n=n, kernel_success_rate=rate,
                correct_rate=rate, attested=n, per_context=per,
                thin=n < 3, evidence=["t%d" % i for i in range(n)])


def funded_runway(periods=100):
    return {"dev": dict(status="observed", available=1000, spent=10,
                        burn_per_step=10, periods=periods,
                        source="budget view")}


class TestHomeostasis(PolicyHarness):
    """B38-B43: stateful regulation, measured burn, grounded competence,
    assessment freshness, real churn and strict unknowns."""

    def test_hysteresis_flag_persists_between_bands(self):
        pol = policy.ViabilityPolicy()
        state = policy.PolicyState()
        obs = hand_obs(comp=ok_comp(),
                       runway={"dev": dict(funded_runway()["dev"], periods=0.5)},
                       step=1)
        self.assertEqual(pol.propose(obs, self.ctx, state)["action"], "defer")
        self.assertTrue(state.flag(("runway", "dev")))
        # Between enter (5) and exit (8): a stateless check would pass,
        # the flag keeps deferring.
        obs = hand_obs(comp=ok_comp(),
                       runway={"dev": dict(funded_runway()["dev"], periods=7)},
                       step=2)
        self.assertEqual(pol.propose(obs, self.ctx, state)["action"], "defer")
        obs = hand_obs(comp=ok_comp(),
                       runway={"dev": dict(funded_runway()["dev"], periods=100)},
                       step=3)
        self.assertEqual(pol.propose(obs, self.ctx, state)["action"], "noop")
        self.assertFalse(state.flag(("runway", "dev")))

    def test_construct_cooldown_suppresses_reproposal(self):
        pol = policy.ViabilityPolicy()
        state = policy.PolicyState()
        obs = hand_obs(active=0, step=12, runway=funded_runway())
        state.log_action("investigate", "c", 5)
        state.log_action("construct", "c", 10)
        state.snapshots[("construct", "c")] = []
        decision = pol.propose(obs, self.ctx, state)
        self.assertEqual(decision["action"], "defer")
        self.assertIn("cooling down", decision["reason"])
        state2 = policy.PolicyState()
        state2.log_action("investigate", "c", 5)
        decision = pol.propose(hand_obs(active=0, step=70, runway=funded_runway()),
                               self.ctx, state2)
        self.assertEqual(decision["action"], "construct")
        self.assertEqual(decision["est_cost"], 64)

    def test_cooldown_lifts_when_members_change(self):
        pol = policy.ViabilityPolicy()
        state = policy.PolicyState()
        obs = hand_obs(active=0, step=12, runway=funded_runway())
        state.log_action("investigate", "c", 5)
        state.log_action("construct", "c", 10)
        state.snapshots[("construct", "c")] = ["m-old"]
        decision = pol.propose(obs, self.ctx, state)
        self.assertEqual(decision["action"], "construct")

    def test_blocked_member_counts_as_changed_world(self):
        import copy
        pol = policy.ViabilityPolicy()
        state = policy.PolicyState()
        base = hand_obs(active=0, step=12, runway=funded_runway())
        state.log_action("investigate", "c", 5)
        state.log_action("construct", "c", 10)
        state.snapshots[("construct", "c")] = []
        cooled = hand_obs(active=0, step=12, runway=funded_runway())
        self.assertEqual(pol.propose(cooled, self.ctx, state)["action"], "defer")
        changed = copy.deepcopy(base)
        changed["capabilities"]["c"]["members"]["snapshot"] = ["m-blocked"]
        changed["capabilities"]["c"]["members"]["BLOCKED"] = 1
        self.assertEqual(pol.propose(changed, self.ctx, state)["action"],
                         "construct")

    def test_construct_needs_funded_budget(self):
        pol = policy.ViabilityPolicy()
        state = policy.PolicyState()
        state.log_action("investigate", "c", 5)
        obs = hand_obs(active=0, step=70, runway={})
        decision = pol.propose(obs, self.ctx, state)
        self.assertEqual(decision["action"], "defer")
        self.assertIn("funded budget", decision["reason"])

    def test_burn_measured_from_two_samples(self):
        state = policy.PolicyState()
        self.assertIsNone(state.burn_per_step("b"))
        state.note_spend("b", 100, 0, 0)
        self.assertIsNone(state.burn_per_step("b"))
        state.note_spend("b", 100, 20, 5)
        self.assertEqual(state.burn_per_step("b"), 4.0)

    def test_poor_correctness_triggers_investigation(self):
        pol = policy.ViabilityPolicy()
        comp = ok_comp(n=4, rate=1.0)
        comp["correct_rate"] = 0.25
        obs = hand_obs(comp=comp, runway=funded_runway())
        decision = pol.propose(obs, self.ctx)
        self.assertEqual(decision["action"], "investigate")
        self.assertIn("poorly", decision["reason"])

    def test_unattested_correctness_is_unconfirmed(self):
        pol = policy.ViabilityPolicy()
        comp = ok_comp()
        comp["correct_rate"], comp["attested"] = None, 0
        obs = hand_obs(comp=comp, runway=funded_runway())
        decision = pol.propose(obs, self.ctx)
        self.assertEqual(decision["action"], "investigate")
        self.assertIn("unconfirmed", decision["reason"])

    def test_thin_evidence_is_unconfirmed(self):
        pol = policy.ViabilityPolicy()
        obs = hand_obs(comp=ok_comp(n=1), runway=funded_runway())
        self.assertIn("unconfirmed", pol.propose(obs, self.ctx)["reason"])

    def test_demanded_context_gap_triggers_investigation(self):
        pol = policy.ViabilityPolicy()
        obs = hand_obs(comp=ok_comp(contexts=["canonical"]),
                       contexts=["irregular"],
                       runway=funded_runway())
        decision = pol.propose(obs, self.ctx)
        self.assertEqual(decision["action"], "investigate")

    def test_stale_assessment_is_not_fresh(self):
        cap, pid = self.admit_text()
        row = {"id": "a1", "capability": cap, "provider": pid, "verdict": "retain",
               "period": -1, "reason": "old", "contexts": {}, "coverage": [],
               "params": {}, "observations": "x", "invocations": [],
               "member_state": "ACTIVE", "age": 0, "evidence_revision": 0,
               "active": [pid], "wall_ns": 0}
        with self.r.store.transaction():
            self.r.store.put("retention-assessment", "a1", row)
        obs = policy.build_observation(self.ctx, [cap])
        providers = obs["capabilities"][cap]["retention"]["providers"]
        self.assertEqual(providers[pid]["freshness"], "stale")

    def test_youth_implies_retention_when_configured(self):
        cap, _ = self.admit_text()
        self.r.population.set_retention_policy(cap, min_age=1000)
        obs = policy.build_observation(self.ctx, [cap])
        providers = obs["capabilities"][cap]["retention"]["providers"]
        self.assertEqual(len(providers), 1)
        entry = next(iter(providers.values()))
        self.assertEqual(entry["freshness"], "implied-youth")

    def test_churn_counts_real_transitions_in_window(self):
        state = policy.PolicyState()
        state.note_members({"m1": "ACTIVE", "m2": "DORMANT"}, 0)
        self.assertEqual(state.note_members({"m1": "ACTIVE", "m2": "ACTIVE",
                                             "m3": "DORMANT"}, 10),
                         [("dormant-to-active", "m2", "ACTIVE"),
                          ("added", "m3", "DORMANT")])
        self.assertEqual(state.transitions_in_window(10, 100), 2)
        self.assertEqual(state.transitions_in_window(200, 100), 0)

    def test_probe_cooldown_defers_identical_reprobe(self):
        pol, state = policy.ViabilityPolicy(), policy.PolicyState()
        obs = hand_obs(comp=ok_comp(n=1), runway=funded_runway(), step=10)
        first = pol.propose(obs, self.ctx, state)
        self.assertEqual(first["action"], "investigate")
        state.log_action("investigate", "c", 10)
        state.probe["c"] = list(first["evidence"]["probe_sig"])
        same = hand_obs(comp=ok_comp(n=1), runway=funded_runway(), step=11)
        cooled = pol.propose(same, self.ctx, state)
        self.assertEqual(cooled["action"], "defer")
        self.assertIn("cooling down", cooled["reason"])
        changed = hand_obs(comp=ok_comp(n=1), runway=funded_runway(), step=12)
        changed["capabilities"]["c"]["members"]["records"] = ["m1"]
        self.assertEqual(pol.propose(changed, self.ctx, state)["action"],
                         "investigate")

    def test_unknown_runway_with_spend_defers(self):
        pol = policy.ViabilityPolicy()
        obs = hand_obs(comp=ok_comp(), runway={"dev": dict(
            status="unknown", available=100, spent=5,
            reason="no measured burn rate yet")})
        decision = pol.propose(obs, self.ctx)
        self.assertEqual(decision["action"], "defer")
        self.assertIn("runway", decision["reason"])

    def test_state_persists_through_context(self):
        state = policy.PolicyState()
        state.note_spend("b", 90, 10, 3)
        state.log_action("investigate", "c", 3)
        state.set_flag(("runway", "b"), True)
        state.snapshots[("construct", "c")] = ["m1"]
        state.note_step(3)
        self.assertEqual(state.save(self.ctx), policy.STATE_KEY)
        loaded = policy.PolicyState.load(self.ctx)
        self.assertEqual(loaded.step, 3)
        self.assertEqual(loaded.burn_per_step("b"), None)
        loaded.note_spend("b", 80, 20, 5)
        self.assertEqual(loaded.burn_per_step("b"), 5.0)
        self.assertTrue(loaded.flag(("runway", "b")))
        self.assertEqual(loaded.actions, [(3, "investigate", "c")])
        self.assertEqual(loaded.snapshots, {("construct", "c"): ["m1"]})


if __name__ == "__main__":
    unittest.main()
