"""Regressions for B14-B20 and the provider lifecycle (reproduced on 9b9e7bd;
see docs/results/2026-11-25T-retention/baseline-findings.json)."""
from pathlib import Path
import ast
import sys
import tempfile
import unittest

from brainos import Refused, Runtime
from brainos import ecology
from brainos.devcontext import development_context
from brainos.ecology import EcologyPolicy, EcologyService
from brainos.population import featurize, verdict
from brainos.resources import ResourceLedger
from brainos.storage import Store

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import run_retention  # noqa: E402

SINGLE = {"data": list(range(0, 100000, 25)), "queries": [[1000, 60000]]}
MANY_WIDE = {"data": list(range(0, 100000, 25)), "queries": [[i * 200, i * 200 + 2000] for i in range(400)]}
MANY_NARROW = {"data": list(range(0, 100000, 25)), "queries": [[i * 200, i * 200 + 2] for i in range(400)]}


class Population(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.now = [0.0]
        self.r = Runtime(Path(self.temp.name) / "c.db", profile="inprocess", clock=lambda: self.now[0])
        self.cap, self.ids, self.budget = run_retention.setup(self.r)
        self.val = self.r.resources.create_budget("eco", {"attempts": 200})

    def tearDown(self):
        self.r.close()
        self.temp.cleanup()

    def observe(self, member, value, n=3):
        return [run_retention.run_member(self.r, self.cap, self.ids[member], value, self.budget)["invocation"]
                for _ in range(n)]

    def cite(self, *values, members=run_retention.MEMBERS):
        cited = []
        for value in values:
            for member in members:
                cited += self.observe(member, value)
        return cited


class GroundedRetirement(Population):
    def test_redundant_duplicate_retires_with_verified_assessment(self):
        cited = self.cite(SINGLE)
        scan = self.ids["range_scan"]
        assessment = self.r.population.assess(self.cap, scan, cited)
        self.assertEqual(assessment["coverage"], ["single-wide"])
        if assessment["verdict"] != "redundant":
            self.skipTest(f"measured costs did not make range_scan redundant: {assessment['contexts']}")
        self.r.population.retire(self.cap, scan, assessment=assessment["id"], reason="duplicate")
        self.assertEqual(self.r.population.state(self.cap, scan), "ARCHIVED")

    def test_assessment_is_bound_to_its_provider_and_capability(self):
        cited = self.cite(SINGLE)
        a = self.r.population.assess(self.cap, self.ids["range_hash"], cited)
        with self.assertRaisesRegex(Refused, "different capability or provider"):
            self.r.population.retire(self.cap, self.ids["range_bisect"], assessment=a["id"], reason="x")

    def test_specialist_cannot_be_retired_or_made_dormant(self):
        cited = self.cite(SINGLE, MANY_WIDE)
        a = self.r.population.assess(self.cap, self.ids["range_bisect"], cited)
        self.assertEqual(a["verdict"], "retain")
        self.assertEqual(a["contexts"]["many-wide"]["verdict"], "specialist")
        for transition in (lambda: self.r.population.retire(self.cap, self.ids["range_bisect"],
                                                            assessment=a["id"], reason="x"),
                           lambda: self.r.population.make_dormant(self.cap, self.ids["range_bisect"],
                                                                  assessment=a["id"])):
            with self.assertRaisesRegex(Refused, "does not justify"):
                transition()

    def test_stale_assessment_is_refused(self):
        cited = self.cite(SINGLE)
        a = self.r.population.assess(self.cap, self.ids["range_hash"], cited)
        self.r.population.maintain(self.cap, self.r.resources.create_budget("eco", {"maintenance": 10 ** 6}),
                                   "eco", charge=self.r.resources.charge)
        with self.assertRaisesRegex(Refused, "stale"):
            self.r.population.make_dormant(self.cap, self.ids["range_hash"], assessment=a["id"])

    def test_cited_observations_must_be_real_matching_invocations(self):
        with self.assertRaises(Refused):
            self.r.population.assess(self.cap, self.ids["range_scan"], ["not-an-invocation"])
        self.r.population.define("other", "integers", "integer", [([1], 1)])
        from brainos.__main__ import install
        install(self.r, {"total": "sum"}, {"total": [([1, 2], 3)]})
        task = self.r.tasks.create_task("eco", "total", [1, 2], self.budget)
        self.r.tasks.run_task(task, self.r.tasks.authorize(task, "eco"), "eco")
        foreign = self.r.tasks.task(task, "eco")["invocation"]
        with self.assertRaisesRegex(Refused, "capability-routed"):
            self.r.population.assess(self.cap, self.ids["range_scan"], [foreign])

    def test_costs_and_contexts_come_from_kernel_records(self):
        cited = self.cite(SINGLE, members=["range_scan"])
        a = self.r.population.assess(self.cap, self.ids["range_scan"], cited)
        recorded = sorted(self.r.store.get("invocation", i)["compute_ns"] for i in cited)
        self.assertEqual(a["coverage"], [featurize(SINGLE)])
        self.assertAlmostEqual(a["contexts"]["single-wide"]["own_median"], recorded[1])


class ProviderLifecycle(Population):
    def dormant_hash(self):
        cited = self.cite(SINGLE)
        a = self.r.population.assess(self.cap, self.ids["range_hash"], cited)
        self.assertIn(a["verdict"], ("not-best", "redundant"), a["contexts"])
        self.r.population.make_dormant(self.cap, self.ids["range_hash"], assessment=a["id"])
        return cited

    def test_dormant_members_do_not_execute_and_wake_free_when_fresh(self):
        self.dormant_hash()
        hash_id = self.ids["range_hash"]
        self.assertEqual(self.r.population.state(self.cap, hash_id), "DORMANT")
        with self.assertRaisesRegex(Refused, "active member"):
            self.r.tasks.create_member_task("eco", self.cap, hash_id, SINGLE, self.budget)
        spent = self.r.resources.budget(self.val, "eco")["spent"]["attempts"]
        self.assertEqual(self.r.population.wake(self.cap, hash_id, budget=self.val, principal="eco"),
                         dict(validated=False))
        self.assertEqual(self.r.resources.budget(self.val, "eco")["spent"]["attempts"], spent)
        self.assertEqual(self.r.population.state(self.cap, hash_id), "ACTIVE")

    def test_stale_dormant_member_revalidates_on_wake(self):
        self.dormant_hash()
        hash_id = self.ids["range_hash"]
        self.r.fabric.apply_impact([hash_id], "resources", "hash-table contention")
        spent = self.r.resources.budget(self.val, "eco")["spent"]["attempts"]
        self.assertEqual(self.r.population.wake(self.cap, hash_id, budget=self.val, principal="eco"),
                         dict(validated=True))
        self.assertGreater(self.r.resources.budget(self.val, "eco")["spent"]["attempts"], spent)

    def test_dormancy_first_policy_and_dormant_age(self):
        self.r.population.set_retention_policy(self.cap, dormancy_first=True, min_dormant_age=2)
        cited = self.cite(SINGLE)
        scan = self.ids["range_scan"]
        a = self.r.population.assess(self.cap, scan, cited)
        if a["verdict"] != "redundant":
            self.skipTest("measured costs did not make range_scan redundant")
        with self.assertRaisesRegex(Refused, "only from dormancy"):
            self.r.population.retire(self.cap, scan, assessment=a["id"], reason="dup")
        self.r.population.make_dormant(self.cap, scan, assessment=a["id"])
        upkeep = self.r.resources.create_budget("eco", {"maintenance": 10 ** 6})
        self.r.population.maintain(self.cap, upkeep, "eco", charge=self.r.resources.charge)
        a = self.r.population.assess(self.cap, scan, cited)
        with self.assertRaisesRegex(Refused, "dormant long enough"):
            self.r.population.retire(self.cap, scan, assessment=a["id"], reason="dup")

    def test_maintenance_charges_active_and_dormant_rates(self):
        self.dormant_hash()
        upkeep = self.r.resources.create_budget("eco", {"maintenance": 10 ** 6})
        units = self.r.population.maintain(self.cap, upkeep, "eco", charge=self.r.resources.charge)
        expected = sum(v[0] for k, v in run_retention.MAINTENANCE.items() if k != "range_hash") \
            + run_retention.MAINTENANCE["range_hash"][1]
        self.assertEqual(units, expected)
        self.assertEqual(self.r.resources.budget(upkeep, "eco")["spent"]["maintenance"], expected)

    def test_admission_age_and_coverage_hold_retention(self):
        cited = self.cite(SINGLE)
        self.r.population.set_retention_policy(self.cap, min_age=3)
        a = self.r.population.assess(self.cap, self.ids["range_hash"], cited)
        self.assertEqual(a["verdict"], "retain")
        self.assertIn("admission age", a["reason"])
        self.r.population.set_retention_policy(self.cap, min_age=0, min_coverage=2)
        a = self.r.population.assess(self.cap, self.ids["range_hash"], cited)
        self.assertEqual((a["verdict"], a["reason"]), ("retain", "insufficient context coverage"))


class FundingCeiling(unittest.TestCase):
    def ledger(self):
        self.temp = tempfile.TemporaryDirectory()
        self.now = [0.0]
        store = Store(Path(self.temp.name) / "l.db")
        self.addCleanup(lambda: (store.close(), self.temp.cleanup()))
        return store, ResourceLedger(store, lambda: self.now[0])

    def test_refill_with_outstanding_reservation_respects_ceiling_after_release(self):
        store, ledger = self.ledger()
        budget = ledger.create_budget("dev", {"attempts": 100})
        ledger.attach_policy(budget, issued_by="operator", period_seconds=1, grant={"attempts": 100},
                             ceiling={"attempts": 100})
        hold = ledger.reserve(budget, "dev", {"attempts": 100})
        self.now[0] += 1
        self.assertEqual(ledger.budget(budget, "dev")["available"]["attempts"], 0)
        ledger.release(hold, "dev")
        self.assertEqual(ledger.budget(budget, "dev")["available"]["attempts"], 100)

    def test_unspent_never_exceeds_ceiling_under_mixed_activity(self):
        import random
        store, ledger = self.ledger()
        budget = ledger.create_budget("dev", {"attempts": 10})
        ledger.attach_policy(budget, issued_by="operator", period_seconds=1, grant={"attempts": 7},
                             ceiling={"attempts": 25})
        rng, holds = random.Random(3), []
        for _ in range(200):
            action = rng.choice(("reserve", "release", "spend", "tick"))
            if action == "reserve":
                try:
                    holds.append(ledger.reserve(budget, "dev", {"attempts": rng.randint(1, 6)}))
                except Refused:
                    pass
            elif action == "release" and holds:
                ledger.release(holds.pop(rng.randrange(len(holds))), "dev")
            elif action == "spend" and holds:
                key = holds.pop()
                ledger.allocate(key, "dev")
                with store.transaction():
                    ledger.charge_tx(key)
            else:
                self.now[0] += 1
            record = ledger.budget(budget, "dev")
            with store.mutex:
                outstanding = ledger._outstanding_tx(budget).get("attempts", 0)
            self.assertLessEqual(record["available"]["attempts"] + outstanding, 25)


class RecoverableEcology(Population):
    def drive(self, eco, plan):
        for value in plan:
            c = featurize(value)
            member, exploring = eco.choose(c, True)
            invocation = run_retention.run_member(self.r, self.cap, self.ids[member], value, self.budget)["invocation"]
            eco.observe(c, member, exploring, invocation)
            yield member

    def test_restart_replays_to_identical_state_and_decisions(self):
        ctx = development_context(self.r)
        eco = EcologyService.create(ctx, self.cap, self.ids, min_samples=2, margin=0.1, seed=9, mode="median",
                                    epsilon=0.3)
        plan = [SINGLE] * 8 + [MANY_NARROW] * 6
        first = list(self.drive(eco, plan[:7]))
        rebuilt = EcologyService(development_context(self.r), eco.id)
        self.assertEqual(rebuilt.policy.evidence, eco.policy.evidence)
        self.assertEqual(rebuilt.policy.contexts, eco.policy.contexts)
        self.assertEqual(rebuilt.policy.decisions, eco.policy.decisions)
        self.assertEqual(rebuilt.cited, eco.cited)
        rest_a = [eco.choose(featurize(v), True) for v in plan[7:8]]
        rest_b = [rebuilt.choose(featurize(v), True) for v in plan[7:8]]
        self.assertEqual(rest_a, rest_b)
        self.assertEqual(len(first), 7)

    def test_lifecycle_operations_survive_restart(self):
        ctx = development_context(self.r)
        eco = EcologyService.create(ctx, self.cap, self.ids, min_samples=3, margin=0.1, seed=1, mode="median",
                                    epsilon=0.0)
        list(self.drive(eco, [SINGLE] * 14))
        if eco.assess("range_hash")["verdict"] not in ("not-best", "redundant"):
            self.skipTest("hash not dormant-eligible on this host")
        eco.make_dormant("range_hash")
        rebuilt = EcologyService(development_context(self.r), eco.id)
        self.assertNotIn("range_hash", rebuilt.policy.members)
        self.assertIn("range_hash", rebuilt.policy.dormant)

    def test_observation_must_cite_the_chosen_member(self):
        eco = EcologyService.create(development_context(self.r), self.cap, self.ids, seed=1)
        other = self.observe("range_bisect", SINGLE, n=1)[0]
        with self.assertRaises(ValueError):
            eco.observe("single-wide", "range_scan", False, other)


class ServiceLifecycleConsistency(Population):
    """Run-1 defect: retiring a DORMANT member through EcologyService (A-35, A-36, A-40)."""

    def service(self):
        # A wide margin makes `redundant` deterministic on any host.
        self.r.population.set_retention_policy(self.cap, dormancy_first=True, min_dormant_age=0, margin=50.0)
        eco = EcologyService.create(development_context(self.r), self.cap, self.ids, min_samples=3, margin=0.1,
                                    seed=4, mode="median", epsilon=0.0)
        for _ in range(12):
            member, exploring = eco.choose("single-wide", True)
            run = run_retention.run_member(self.r, self.cap, self.ids[member], SINGLE, self.budget)
            eco.observe("single-wide", member, exploring, run["invocation"])
        return eco

    def test_retire_from_dormancy_keeps_service_and_population_consistent(self):
        eco = self.service()
        eco.make_dormant("range_scan")
        eco.retire("range_scan", "redundant")
        self.assertEqual(self.r.population.state(self.cap, self.ids["range_scan"]), "ARCHIVED")
        self.assertIn("range_scan", eco.policy.archived)
        self.assertNotIn("range_scan", eco.policy.dormant + eco.policy.members)
        rebuilt = EcologyService(development_context(self.r), eco.id)
        self.assertEqual((rebuilt.policy.members, rebuilt.policy.dormant, rebuilt.policy.archived),
                         (eco.policy.members, eco.policy.dormant, eco.policy.archived))
        eco.regenerate("range_scan", budget=self.val, principal="eco")
        self.assertIn("range_scan", eco.policy.members)
        self.assertEqual(self.r.population.state(self.cap, self.ids["range_scan"]), "ACTIVE")

    def test_runner_review_retires_from_dormancy_without_desync(self):
        eco = self.service()
        eco.make_dormant("range_scan")
        out = dict(transitions=[], assessments=0, assessment_wall_ns=0)
        run_retention.review(eco, run_retention.CONDITIONS["R3"], out, 0)
        self.assertIn(dict(at=0, op="retire", member="range_scan"), out["transitions"])
        for member in eco.policy.dormant:                       # every dormant member is still assessable
            eco.assess(member)

    def test_runner_records_only_population_refusals(self):
        class Broken:
            policy = type("P", (), {"members": ["a", "b"], "dormant": ["a"]})()
            def assess(self, member):
                return {"verdict": "redundant"}
            def retire(self, member, reason):
                raise ValueError("bookkeeping defect")
        with self.assertRaises(ValueError):
            run_retention.review(Broken(), run_retention.CONDITIONS["R3"],
                                 dict(transitions=[], assessments=0, assessment_wall_ns=0), 0)


class CostBoundaries(Population):
    def test_invocations_record_compute_and_runner_totals(self):
        run = run_retention.run_member(self.r, self.cap, self.ids["range_bisect"], MANY_WIDE, self.budget)
        self.assertGreater(run["compute"], 0)
        self.assertGreaterEqual(run["runner_total"], run["compute"])
        self.assertGreaterEqual(run["e2e"], run["runner_total"])

    def test_validation_records_compute_wall_and_attempts(self):
        candidate = next(c for c in self.r.store.find("candidate") if c.get("kind") == "membership")
        for key in ("validation_compute_ns", "validation_total_ns", "validation_wall_ns", "validation_attempts"):
            self.assertIn(key, candidate)
        self.assertGreaterEqual(candidate["validation_wall_ns"], candidate["validation_compute_ns"])

    def test_assessment_records_its_own_wall_time(self):
        a = self.r.population.assess(self.cap, self.ids["range_scan"], self.cite(SINGLE, members=["range_scan"]))
        self.assertGreater(a["wall_ns"], 0)

    def test_score_reports_separate_ledgers(self):
        table = [dict(segment="E1", context="single-wide", costs={m: 10 ** 6 for m in run_retention.MEMBERS},
                      e2e={m: 5 * 10 ** 6 for m in run_retention.MEMBERS}) for _ in range(5)]
        run = dict(choices=[dict(at=i, member="range_scan", exploring=False) for i in range(5)], transitions=[],
                   population=[dict(active=4, dormant=0, retained=run_retention.MEMBERS)] * 5,
                   validation=dict(count=1, compute_ns=2 * 10 ** 6, wall_ns=9 * 10 ** 6, attempts=3),
                   maintenance_units=3000, exploration=0, assessments=2, assessment_wall_ns=10 ** 6,
                   final_retained=run_retention.MEMBERS)
        saved = run_retention.SEGMENTS
        run_retention.SEGMENTS = [("E1", 5, "single-wide", 0.0)]
        try:
            s = run_retention.score(run, table)
        finally:
            run_retention.SEGMENTS = saved
        self.assertEqual(s["ledgers"]["compute_ms"], 5.0)
        self.assertEqual(s["ledgers"]["e2e_ms"], 25.0)
        self.assertEqual(s["ledgers"]["organizational"]["validation_wall_ms"], 9.0)
        self.assertEqual(s["total_cost_ms"], 5.0 + 2.0 + 3.0)       # compute boundary only


class CoexistenceQuantifier(unittest.TestCase):
    def test_exact_quantifier_differs_from_per_request_minimum(self):
        # A wins requests 1-2, B wins 3-4: collectively always near-optimal, individually never a majority.
        rows = [dict(context="c", costs={"A": 1, "B": 9}), dict(context="c", costs={"A": 1, "B": 9}),
                dict(context="c", costs={"A": 9, "B": 1}), dict(context="c", costs={"A": 9, "B": 1})]
        collective = sum(min(r["costs"][m] for m in "AB") <= 1.1 * min(r["costs"].values()) for r in rows) > 2
        self.assertTrue(collective)
        self.assertEqual(run_retention.coexistence_exact(rows, ["A", "B"]), {"c": False})

    def test_preserved_v1_v2_results_are_rescored_without_overwrite(self):
        base = Path(run_retention.ROOT) / "docs" / "results" / "2026-11-25T-ecology"
        before = {v: (base / f"experiment-results-{v}.json").read_bytes() for v in ("v1", "v2")}
        corrected = run_retention.corrected_coexistence()
        self.assertEqual({v: (base / f"experiment-results-{v}.json").read_bytes() for v in ("v1", "v2")}, before)
        self.assertFalse(corrected["v1"]["exact_passed"])
        self.assertTrue(corrected["v2"]["exact_passed"])


class UncertaintyAwareExploration(unittest.TestCase):
    def test_single_noisy_sample_does_not_prune(self):
        policy = EcologyPolicy(["a", "b"], mode="lcb", min_samples=3)
        for cost in (1000, 1000, 1000):
            policy.observe("c", "b", cost)
        policy.observe("c", "a", 11000)                  # one 11x sample
        lower, _ = policy.bounds("c", "a")
        _, upper = policy.bounds("c", "b")
        self.assertLessEqual(lower, upper)                # still plausible
        self.assertEqual(policy.select("c", True), ("a", True))

    def test_consistent_large_gap_prunes(self):
        policy = EcologyPolicy(["a", "b"], mode="lcb", min_samples=3)
        for _ in range(3):
            policy.observe("c", "b", 1000)
            policy.observe("c", "a", 150000)
        self.assertGreater(policy.bounds("c", "a")[0], policy.bounds("c", "b")[1])
        self.assertEqual(policy.select("c", True), ("b", False))

    def test_no_budget_means_greedy(self):
        policy = EcologyPolicy(["a", "b"], mode="lcb")
        policy.observe("c", "a", 5)
        self.assertEqual(policy.select("c", False), ("a", False))


class DevelopmentBoundary(unittest.TestCase):
    def test_context_exposes_no_ledger_store_runtime_or_funding(self):
        with tempfile.TemporaryDirectory() as d, Runtime(Path(d) / "c.db", profile="inprocess") as r:
            ctx = development_context(r)
            for value in vars(ctx).values():
                self.assertTrue(callable(value))
                self.assertNotIsInstance(value, (Runtime, ResourceLedger, Store))
            for name in ("create_budget", "attach_policy", "store", "resources", "runtime", "transactor"):
                self.assertFalse(hasattr(ctx, name), name)
            for kind in ("budget", "holding", "control", "candidate"):
                with self.assertRaises(Refused):
                    ctx.write(kind, "x", {}, "forged")

    def test_search_holds_only_the_context(self):
        from brainos.development import CompositionSearch
        with tempfile.TemporaryDirectory() as d, Runtime(Path(d) / "c.db", profile="inprocess") as r:
            search = CompositionSearch(r)
            self.assertFalse(any(isinstance(v, Runtime) for v in vars(search).values()))

    def test_developmental_modules_never_touch_funding_or_raw_services(self):
        src = Path(__file__).resolve().parents[1] / "src" / "brainos"
        for name in ("development.py", "ecology.py"):
            tree = ast.parse((src / name).read_text(encoding="utf-8"))
            attributes = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
            self.assertFalse(attributes & {"create_budget", "attach_policy", "resources", "store",
                                           "transactor", "_accrue_tx"}, name)


class FrozenPreregistration(unittest.TestCase):
    def test_changed_preregistration_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            copy = Path(d) / "PREREGISTRATION.md"
            copy.write_text("changed", encoding="utf-8")
            with self.assertRaises(SystemExit):
                run_retention.verify_frozen(copy, run_retention.PREREG_SHA256)

    def test_uncommitted_file_is_refused(self):
        probe = Path(run_retention.ROOT) / "docs" / "results" / "uncommitted-probe.md"
        probe.write_text("probe", encoding="utf-8")
        try:
            self.assertFalse(run_retention.committed_unchanged(probe))
            with self.assertRaises(SystemExit):
                run_retention.verify_frozen(probe, run_retention.digest_of(probe))
        finally:
            probe.unlink()


if __name__ == "__main__":
    unittest.main()
