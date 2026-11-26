"""ADR coordination core: declared bands (R-25-08), evidence-grounded
observation (R-25-08) and the replaceable developmental policy (R-07-13).

The policy proposes; it never executes. Every test below asserts on
proposals and records, never on performed transformations.
"""
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

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

    def test_verified_redundant_with_alternative_proposes_suspend(self):
        pol = policy.ViabilityPolicy()
        ret = dict(status="observed", count=1, providers={
            "p-bad": dict(state="ACTIVE", verdict="redundant",
                          freshness="fresh", age_steps=2, assessment="a1"),
            "p-good": dict(state="ACTIVE", verdict="retain",
                           freshness="fresh", age_steps=2, assessment="a2")})
        obs = hand_obs(comp=ok_comp(), retention=ret, runway=funded_runway())
        decision = pol.propose(obs, self.ctx)
        self.assertEqual(decision["action"], "suspend")
        self.assertEqual(decision["evidence"]["suspended"], "p-bad")
        self.assertEqual(decision["evidence"]["assessment"], "a1")

    def test_dormant_adverse_member_needs_no_suspension(self):
        pol = policy.ViabilityPolicy()
        ret = dict(status="observed", count=1, providers={
            "p-old": dict(state="DORMANT", verdict="redundant",
                          freshness="fresh", age_steps=2, assessment="a1"),
            "p-good": dict(state="ACTIVE", verdict="retain",
                           freshness="fresh", age_steps=2, assessment="a2")})
        obs = hand_obs(comp=ok_comp(), retention=ret, runway=funded_runway())
        self.assertNotEqual(pol.propose(obs, self.ctx)["action"], "suspend")

    def test_adverse_without_alternative_stays_investigate(self):
        pol = policy.ViabilityPolicy()
        ret = dict(status="observed", count=1, providers={
            "p-bad": dict(state="ACTIVE", verdict="not-best",
                          freshness="fresh", age_steps=2, assessment="a1")})
        obs = hand_obs(comp=ok_comp(), retention=ret, runway=funded_runway())
        self.assertEqual(pol.propose(obs, self.ctx)["action"], "investigate")

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


class TestQuiescence(unittest.TestCase):
    """B43/F: a high noop rate never establishes health by itself."""

    def obs(self, **over):
        base = dict(capabilities={
            "c": dict(name="c",
                      members=dict(ACTIVE=1, DORMANT=0, ARCHIVED=0, BLOCKED=0,
                                   status="observed", source="m", records=["m1"],
                                   snapshot=["m1"]),
                      competence=dict(status="observed", n=5, thin=False,
                                      kernel_success_rate=1.0, correct_rate=1.0,
                                      attested=5, per_context={}, evidence=["t"]),
                      retention=dict(status="observed", count=1, providers={
                          "p": dict(state="ACTIVE", verdict="retain",
                                    freshness="fresh", age_steps=2, assessment="a")}),
                      demanded=dict(status="observed", value=True, contexts=None))},
            runway={"b": dict(status="observed", available=100, spent=10,
                              burn_per_step=2, periods=50, source="s")},
            churn=dict(status="estimated"), transitions=[], step=10,
            recovery=dict(status="unknown", reason="unseen"))
        base.update(over)
        return base

    def test_healthy_requires_everything_known(self):
        label, reasons = policy.classify_quiescence(
            self.obs(), policy.PolicyState(), policy.default_bands())
        self.assertEqual(label, "verified-healthy")

    def test_unknown_runway_blocks_health(self):
        obs = self.obs()
        obs["runway"] = {"b": dict(status="unknown", available=100, spent=5,
                                   reason="no burn yet")}
        label, reasons = policy.classify_quiescence(
            obs, policy.PolicyState(), policy.default_bands())
        self.assertEqual(label, "unknown")
        self.assertTrue(any("runway" in r for r in reasons))

    def test_blocked_members_with_no_serve_are_blocked_inactivity(self):
        obs = self.obs()
        obs["capabilities"]["c"]["members"] = dict(
            ACTIVE=0, DORMANT=0, ARCHIVED=0, BLOCKED=1, status="observed",
            source="m", records=[], snapshot=[])
        label, _ = policy.classify_quiescence(
            obs, policy.PolicyState(), policy.default_bands())
        self.assertEqual(label, "blocked-inactivity")

    def test_unserved_without_attempt_is_pressure(self):
        obs = self.obs()
        obs["capabilities"]["c"]["members"] = dict(
            ACTIVE=0, DORMANT=0, ARCHIVED=0, BLOCKED=0, status="observed",
            source="m", records=[], snapshot=[])
        label, _ = policy.classify_quiescence(
            obs, policy.PolicyState(), policy.default_bands())
        self.assertEqual(label, "unresolved-pressure")

    def test_unserved_after_construct_without_coverage_is_pressure(self):
        # B45: a failed attempt alone never proves exhaustion.
        obs = self.obs()
        obs["capabilities"]["c"]["members"] = dict(
            ACTIVE=0, DORMANT=0, ARCHIVED=0, BLOCKED=0, status="observed",
            source="m", records=[], snapshot=[])
        state = policy.PolicyState()
        state.log_action("construct", "c", 5)
        state.note_attempt("construct", "c", 5, "abstained: NON_ATTAINMENT")
        label, reasons = policy.classify_quiescence(obs, state, policy.default_bands())
        self.assertEqual(label, "unresolved-pressure")

    def test_unserved_with_proven_coverage_is_exhausted(self):
        obs = self.obs()
        obs["capabilities"]["c"]["members"] = dict(
            ACTIVE=0, DORMANT=0, ARCHIVED=0, BLOCKED=0, status="observed",
            source="m", records=[], snapshot=[])
        state = policy.PolicyState()
        state.note_attempt("construct", "c", 5, "abstained: NON_ATTAINMENT",
                           category="exhausted")
        label, _ = policy.classify_quiescence(obs, state, policy.default_bands())
        self.assertEqual(label, "exhausted-search")

    def test_repeated_limited_failures_are_blocked(self):
        obs = self.obs()
        obs["capabilities"]["c"]["members"] = dict(
            ACTIVE=0, DORMANT=0, ARCHIVED=0, BLOCKED=0, status="observed",
            source="m", records=[], snapshot=[])
        state = policy.PolicyState()
        state.note_attempt("construct", "c", 4, "refused: budget overdraft")
        state.note_attempt("construct", "c", 6, "refused: budget overdraft")
        label, reasons = policy.classify_quiescence(obs, state, policy.default_bands())
        self.assertEqual(label, "blocked-inactivity")
        self.assertTrue(any("budget-limited" in r for r in reasons))

    def test_repeated_unknown_failures_are_stalled_pressure(self):
        obs = self.obs()
        obs["capabilities"]["c"]["members"] = dict(
            ACTIVE=0, DORMANT=0, ARCHIVED=0, BLOCKED=0, status="observed",
            source="m", records=[], snapshot=[])
        state = policy.PolicyState()
        state.note_attempt("construct", "c", 4, "abstained: NON_ATTAINMENT")
        state.note_attempt("construct", "c", 6, "abstained: NON_ATTAINMENT")
        label, reasons = policy.classify_quiescence(obs, state, policy.default_bands())
        self.assertEqual(label, "unresolved-pressure")
        self.assertTrue(any("repeated" in r for r in reasons))

    def test_implied_youth_is_conditional_not_verified(self):
        obs = self.obs()
        obs["capabilities"]["c"]["retention"]["providers"] = {
            "p": dict(state="ACTIVE", verdict=None,
                      freshness="implied-youth", age_steps=None, assessment=None)}
        label, _ = policy.classify_quiescence(
            obs, policy.PolicyState(), policy.default_bands())
        self.assertEqual(label, "conditional-quiescence")

    def test_unspent_unassessed_runway_is_conditional(self):
        obs = self.obs()
        obs["runway"] = {"b": dict(status="unknown", available=100, spent=0,
                                   reason="no samples yet")}
        label, _ = policy.classify_quiescence(
            obs, policy.PolicyState(), policy.default_bands())
        self.assertEqual(label, "conditional-quiescence")

    def test_poor_competence_is_pressure(self):
        obs = self.obs()
        obs["capabilities"]["c"]["competence"] = dict(
            status="observed", n=5, thin=False, kernel_success_rate=0.2,
            correct_rate=0.2, attested=5, per_context={}, evidence=["t"])
        label, _ = policy.classify_quiescence(
            obs, policy.PolicyState(), policy.default_bands())
        self.assertEqual(label, "unresolved-pressure")

    def test_low_runway_is_deferral(self):
        obs = self.obs()
        obs["runway"] = {"b": dict(status="observed", available=10, spent=90,
                                    burn_per_step=30, periods=0.33, source="s")}
        label, _ = policy.classify_quiescence(
            obs, policy.PolicyState(), policy.default_bands())
        self.assertEqual(label, "resource-deferral")

    def test_recovering_flag_wins(self):
        label, _ = policy.classify_quiescence(
            self.obs(), policy.PolicyState(), policy.default_bands(),
            recovering=True)
        self.assertEqual(label, "recovery")

    def test_lineage_counts_composite_depth(self):
        specs = {"g2": dict(kind="graph", transitive_dependencies=["g1", "prim"]),
                 "g1": dict(kind="graph", transitive_dependencies=["prim"]),
                 "prim": dict(kind="primitive", transitive_dependencies=[])}
        ctx = SimpleNamespace(resolve=lambda pid: specs[pid])
        chain = dict(policy.construction_lineage(ctx, "g2"))
        self.assertEqual(chain["g2"], 1)
        self.assertEqual(chain["g1"], 0)

    def test_lineage_cuts_cycles(self):
        specs = {"a": dict(kind="graph", transitive_dependencies=["b"]),
                 "b": dict(kind="graph", transitive_dependencies=["a"])}
        ctx = SimpleNamespace(resolve=lambda pid: specs[pid])
        chain = policy.construction_lineage(ctx, "a")
        self.assertEqual([p for p, _ in chain], ["a", "b"])

    def test_lineage_unknown_provider_is_depth_zero(self):
        ctx = SimpleNamespace(resolve=lambda pid: (_ for _ in ()).throw(
            __import__("brainos").Refused("nope")))
        self.assertEqual(policy.construction_lineage(ctx, "ghost"), [("ghost", 0)])


class TestSearchOutcomes(unittest.TestCase):
    """B45: failed search is not proven exhaustion."""

    def test_succeeded_on_acquired(self):
        cat, detail = policy.classify_search_outcome(
            status="ACQUIRED", reason="ok")
        self.assertEqual(cat, "succeeded")

    def test_exhausted_requires_explicit_coverage(self):
        cat, _ = policy.classify_search_outcome(
            status="NON_ATTAINMENT", reason="no candidate found",
            coverage={"examined": 12, "total": 10})
        self.assertEqual(cat, "exhausted")

    def test_no_coverage_claim_without_proof(self):
        cat, _ = policy.classify_search_outcome(
            status="NON_ATTAINMENT", reason="no candidate found")
        self.assertEqual(cat, "unknown")

    def test_budget_limited(self):
        cat, _ = policy.classify_search_outcome(reason="refused: budget overdraft")
        self.assertEqual(cat, "budget-limited")

    def test_deadline_limited(self):
        cat, _ = policy.classify_search_outcome(
            reason="construction deadline exceeded")
        self.assertEqual(cat, "deadline-limited")

    def test_validation_limited(self):
        cat, _ = policy.classify_search_outcome(
            reason="evaluation-failed: mismatch on held-out")
        self.assertEqual(cat, "validation-limited")

    def test_stalled_on_repeated_unknown(self):
        prior = ["unknown", "unknown"]
        cat, detail = policy.classify_search_outcome(
            reason="abstained", prior=prior, coverage={"examined": 3, "total": 10})
        self.assertEqual(cat, "stalled")
        self.assertIn("repeated", detail)


def _obs_with(**kw):
    base = dict(
        capabilities={"c": dict(
            name="c",
            members=dict(ACTIVE=1, DORMANT=0, ARCHIVED=0, status="observed",
                         source="m", records=["m1"], snapshot=["m1"]),
            competence=dict(status="observed", n=5, thin=False,
                            kernel_success_rate=1.0, correct_rate=1.0,
                            attested=5, per_context={}, evidence=["t"]),
            retention=dict(status="observed", count=1, providers={
                "p": dict(state="ACTIVE", verdict="retain",
                          freshness="fresh", age_steps=2, assessment="a")}),
            demanded=dict(status="observed", value=True, contexts=None))},
        runway={"b": dict(status="observed", available=100, spent=10,
                          burn_per_step=2, periods=50, source="s")},
        churn=dict(status="estimated"), transitions=[], step=10,
        recovery=dict(status="unknown", reason="unseen"))
    for k, v in kw.items():
        if k == "providers":
            base["capabilities"]["c"]["retention"]["providers"] = v
        elif k == "members":
            base["capabilities"]["c"]["members"].update(v)
        elif k == "params":
            base["capabilities"]["c"]["retention"]["params"] = v
        else:
            base["capabilities"]["c"][k] = v
    return base


class TestLifecycleTriggers(unittest.TestCase):
    """B47/B48: wake/revalidate/replace/regenerate/assimilate triggers."""

    def test_regenerate_archived_when_no_serving_member(self):
        obs = _obs_with(members=dict(ACTIVE=0, DORMANT=0, ARCHIVED=1,
                                     status="observed", source="m",
                                     records=["m-arch"], snapshot=["m-arch"]),
                        providers={"m-arch": dict(
                            state="ARCHIVED", verdict=None, freshness="unknown",
                            age_steps=None, assessment=None)})
        pol = policy.ViabilityPolicy()
        d = pol.propose(obs, None, policy.PolicyState())
        self.assertEqual(d["action"], "regenerate")
        self.assertEqual(d["evidence"]["regenerated"], "m-arch")

    def test_no_regenerate_when_dormant_exists(self):
        obs = _obs_with(members=dict(ACTIVE=0, DORMANT=1, ARCHIVED=1,
                                     status="observed", source="m",
                                     records=["m-d", "m-arch"],
                                     snapshot=["m-d", "m-arch"]),
                        providers={
                            "m-d": dict(state="DORMANT", verdict=None,
                                        freshness="unknown", age_steps=None,
                                        assessment=None),
                            "m-arch": dict(state="ARCHIVED", verdict=None,
                                           freshness="unknown", age_steps=None,
                                           assessment=None)})
        pol = policy.ViabilityPolicy()
        d = pol.propose(obs, None, policy.PolicyState())
        self.assertEqual(d["action"], "recruit")

    def test_stale_retention_triggers_revalidation(self):
        obs = _obs_with(providers={
            "p": dict(state="ACTIVE", verdict=None,
                      freshness="stale", age_steps=99, assessment="a-old")})
        pol = policy.ViabilityPolicy()
        d = pol.propose(obs, None, policy.PolicyState())
        self.assertEqual(d["action"], "investigate")
        self.assertIn("revalidation", d["reason"])

    def test_retire_after_dormancy_threshold(self):
        obs = _obs_with(members=dict(ACTIVE=1, DORMANT=1, ARCHIVED=0,
                                     status="observed", source="m",
                                     records=["m1", "m2"], snapshot=["m1", "m2"]),
                        providers={
                            "m1": dict(state="ACTIVE", verdict="retain",
                                       freshness="fresh", age_steps=1,
                                       assessment="a1"),
                            "m2": dict(state="DORMANT", verdict="redundant",
                                       freshness="fresh", age_steps=3,
                                       assessment="a2", dormant_periods=10)},
                        params={"dormancy_first": True, "min_dormant_age": 5})
        pol = policy.ViabilityPolicy()
        d = pol.propose(obs, None, policy.PolicyState())
        self.assertEqual(d["action"], "retire")
        self.assertEqual(d["evidence"]["retired"], "m2")

    def test_no_retire_without_dormancy_first(self):
        obs = _obs_with(members=dict(ACTIVE=1, DORMANT=1, ARCHIVED=0,
                                     status="observed", source="m",
                                     records=["m1", "m2"], snapshot=["m1", "m2"]),
                        providers={
                            "m1": dict(state="ACTIVE", verdict="retain",
                                       freshness="fresh", age_steps=1,
                                       assessment="a1"),
                            "m2": dict(state="DORMANT", verdict="redundant",
                                       freshness="fresh", age_steps=3,
                                       assessment="a2", dormant_periods=10)},
                        params={"dormancy_first": False, "min_dormant_age": 0})
        pol = policy.ViabilityPolicy()
        d = pol.propose(obs, None, policy.PolicyState())
        self.assertNotEqual(d["action"], "retire")

    def test_assimilate_nominates_overlapping_pair(self):
        # B48: both serving members adversely assessed -> suspend would
        # destroy the overlap; nominate consolidation instead.
        obs = _obs_with(
            providers={
                "m1": dict(state="ACTIVE", verdict="redundant",
                           freshness="fresh", age_steps=1, assessment="a1"),
                "m2": dict(state="ACTIVE", verdict="not-best",
                           freshness="fresh", age_steps=1, assessment="a2")})
        pol = policy.ViabilityPolicy()
        d = pol.propose(obs, None, policy.PolicyState())
        self.assertEqual(d["action"], "assimilate")
        self.assertEqual(len(d["evidence"]["parents"]), 2)

    def test_single_adverse_with_alternative_suspends(self):
        # One redundant member beside a healthy one: suspend, not assimilate.
        obs = _obs_with(
            providers={
                "m1": dict(state="ACTIVE", verdict="redundant",
                           freshness="fresh", age_steps=1, assessment="a1"),
                "m2": dict(state="ACTIVE", verdict="retain",
                           freshness="fresh", age_steps=1, assessment="a2")})
        pol = policy.ViabilityPolicy()
        d = pol.propose(obs, None, policy.PolicyState())
        self.assertEqual(d["action"], "suspend")

    def test_assimilate_needs_two_servable(self):
        obs = _obs_with(
            providers={
                "m1": dict(state="ACTIVE", verdict="redundant",
                           freshness="fresh", age_steps=1, assessment="a1")})
        pol = policy.ViabilityPolicy()
        d = pol.propose(obs, None, policy.PolicyState())
        self.assertNotEqual(d["action"], "assimilate")

    def test_note_attempt_roundtrip(self):
        import tempfile
        from brainos import Runtime
        from brainos.devcontext import development_context
        with tempfile.TemporaryDirectory() as d:
            from pathlib import Path
            rt = Runtime(Path(d) / "t.db", profile="inprocess")
            ctx = development_context(rt)
            st = policy.PolicyState()
            st.note_attempt("construct", "cap", 7, "abstained: timeout", "deadline-limited")
            key = st.save(ctx)
            self.assertEqual(key, policy.STATE_KEY)
            loaded = policy.PolicyState.load(ctx)
            self.assertEqual(len(loaded.attempts), 1)
            self.assertEqual(loaded.attempts[0][3], "abstained: timeout")
            rt.close()


class TestSuccession(unittest.TestCase):
    """Doc 34 section 34.6: durable decision-to-outcome linkage as
    temporal succession, never a causal claim."""

    def obs(self, **caps):
        return dict(capabilities={
            c: dict(members=dict(snapshot=list(m))) for c, m in caps.items()})

    def test_resolve_records_delta_with_noncausal_label(self):
        st = policy.PolicyState()
        st.note_proposal("recruit", "c", 5, ["m-d"])
        closed = st.resolve_pending(6, {"c": ["m-d", "m-n"]})
        self.assertEqual(len(closed), 1)
        link = closed[0]
        self.assertEqual(link["added"], ["m-n"])
        self.assertEqual(link["removed"], [])
        self.assertEqual(link["relation"], "succession-not-causation")
        self.assertEqual(link["proposed_step"], 5)
        self.assertEqual(link["observed_step"], 6)

    def test_absent_target_stays_pending(self):
        st = policy.PolicyState()
        st.note_proposal("recruit", "c", 5, ["m-d"])
        self.assertEqual(st.resolve_pending(6, {"other": ["x"]}), [])
        self.assertEqual(len(st.pending), 1)

    def test_succession_survives_save_load(self):
        import tempfile
        from pathlib import Path
        from brainos import Runtime
        from brainos.devcontext import development_context
        with tempfile.TemporaryDirectory() as d:
            rt = Runtime(Path(d) / "t.db", profile="inprocess")
            ctx = development_context(rt)
            st = policy.PolicyState()
            st.note_proposal("retire", "c", 5, ["m1", "m2"])
            st.resolve_pending(6, {"c": ["m1"]})
            st.note_proposal("recruit", "c2", 6, [])
            st.save(ctx)
            rt.close()
            rt2 = Runtime(Path(d) / "t.db", profile="inprocess")
            loaded = policy.PolicyState.load(development_context(rt2))
            self.assertEqual(len(loaded.successions), 1)
            self.assertEqual(loaded.successions[0][6], [])
            self.assertEqual(loaded.successions[0][7], ["m2"])
            self.assertEqual(len(loaded.pending), 1)
            rt2.close()

    def test_adr_record_opens_and_closes_links(self):
        import sys
        import tempfile
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]
                               / "tools"))
        import run_adr
        with tempfile.TemporaryDirectory() as d:
            demo = run_adr.Demo(Path(d), seed=1)
            demo.open()
            demo.caps = {}
            dec = dict(action="recruit", target="cap1", reason="probe",
                       evidence={})
            demo.record(dec, "executed: woke m-d",
                        self.obs(cap1=["m-d"]))
            self.assertEqual(len(demo.state.pending), 1)
            demo.tick = 1
            demo.record(dict(action="noop", target="cap1", reason="q",
                             evidence={}),
                        "recorded",
                        self.obs(cap1=["m-d", "m-n"]))
            self.assertEqual(len(demo.state.pending), 1)
            self.assertEqual(len(demo.state.successions), 1)
            link = demo.state.successions[0]
            self.assertEqual(link[6], ["m-n"])
            rows = [r.get("body", r) for r in demo.rt.store.journal()]
            self.assertTrue(any(isinstance(r, dict)
                                and r.get("action") == "succession"
                                for r in rows))
            demo.rt.close()


if __name__ == "__main__":
    unittest.main()
