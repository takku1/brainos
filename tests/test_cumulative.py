"""Regressions for review findings B07-B13 (reproduced on 08d29f3; see
docs/results/2026-11-25T-ecology/baseline-findings.json)."""
from pathlib import Path
import random
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from brainos import Refused, Runtime
from brainos.__main__ import install
from brainos.closure import compute_closure
from brainos.development import CapabilityDemand, CompositionSearch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from dep_closure import compute_closure as reference_closure  # noqa: E402

PARENTS = {"parse": "parse_csv", "total": "sum", "total_loop": "sum_loop", "count": "count",
           "length": "text_length", "negate": "negate", "double": "double"}
PARENT_CASES = {"parse": [("1,2", [1, 2])], "total": [([1, 2], 3)], "total_loop": [([1, 2], 3)],
                "count": [([1, 2], 2)], "length": [("ab", 2)], "negate": [(3, -3)], "double": [(3, 6)]}
GEN1 = CapabilityDemand("csv-sum", "text", "integer", (("1,2,3", 6), ("10, -4", 6)))
GEN1_CASES = [("4,5", 9), ("", 0), ("7", 7)]
GEN2 = CapabilityDemand("csv-neg-sum", "text", "integer", (("1,2,3", -6), ("10, -4", -6)))
GEN2_CASES = [("4,5", -9), ("", 0), ("7", -7)]
GEN3 = CapabilityDemand("csv-neg-double-sum", "text", "integer", (("1,2,3", -12), ("10, -4", -12)))
GEN3_CASES = [("4,5", -18), ("", 0), ("7", -14)]


class Case(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.now = [1000.0]
        self.r = Runtime(self.root / "core.sqlite3", clock=lambda: self.now[0], profile="persistent")
        install(self.r, PARENTS, PARENT_CASES)
        self.dev = self.r.resources.create_budget("dev", {"attempts": 600})
        self.val = self.r.resources.create_budget("dev", {"attempts": 200})
        self.search = CompositionSearch(self.r)

    def tearDown(self):
        self.r.close()
        self.temp.cleanup()

    def acquire(self, demand, cases, **kw):
        return self.search.acquire(demand, "dev", self.dev, cases, validation_budget=self.val, **kw)

    def run_role(self, role, value):
        task = self.r.tasks.create_task("dev", role, value, self.dev)
        return self.r.tasks.run_task(task, self.r.tasks.authorize(task, "dev"), "dev")


class CumulativeConstruction(Case):
    def test_three_generations_reuse_earlier_acquisitions(self):
        g1 = self.acquire(GEN1, GEN1_CASES, cumulative=True)
        g2 = self.acquire(GEN2, GEN2_CASES, cumulative=True)
        g3 = self.acquire(GEN3, GEN3_CASES, cumulative=True)
        self.assertEqual([g["status"] for g in (g1, g2, g3)], ["ACQUIRED"] * 3)
        self.assertEqual(g2["path"][0], g1["provider"])          # generation 1 is a building block
        self.assertEqual(g3["path"][0], g2["provider"])          # generation 2 is a building block
        spec = self.r.registry.resolve(g3["provider"])
        self.assertTrue(all(self.r.registry.resolve(n["provider"])["kind"] == "primitive" for n in spec["nodes"]))
        self.assertEqual(len(spec["nodes"]), 4)
        self.assertTrue({g1["provider"], g2["provider"]} <= set(spec["transitive_dependencies"]))
        self.assertEqual(self.run_role("csv-neg-double-sum", "1,2,3,4"), -20)

    def test_primitive_only_search_cannot_reach_generation_two_at_depth_two(self):
        self.acquire(GEN1, GEN1_CASES)
        self.assertEqual(self.acquire(GEN2, GEN2_CASES)["status"], "NON_ATTAINMENT")
        self.assertEqual(self.acquire(GEN2, GEN2_CASES, cumulative=True)["status"], "ACQUIRED")

    def test_blocking_an_earlier_generation_blocks_later_ones(self):
        g1 = self.acquire(GEN1, GEN1_CASES, cumulative=True)
        g2 = self.acquire(GEN2, GEN2_CASES, cumulative=True)
        self.r.fabric.apply_impact([g1["provider"]], "support", "counterexample in csv-sum")
        for provider in (g1["provider"], g2["provider"]):
            with self.assertRaisesRegex(Refused, "blocked"):
                self.r.registry.resolve(provider)
        with self.assertRaisesRegex(Refused, "blocked"):
            self.r.tasks.create_task("dev", "csv-neg-sum", "1", self.dev)

    def test_lowering_is_bounded(self):
        total = self.r.manifest()["bindings"]["negate"]
        g = self.acquire(GEN1, GEN1_CASES, cumulative=True)
        nodes = [dict(id="n0", provider=g["provider"], input="$input")]
        nodes += [dict(id=f"n{i}", provider=total, input=f"n{i-1}") for i in range(1, 16)]
        with self.assertRaisesRegex(Refused, "16"):
            self.r.registry.register_graph(dict(input="text", output="integer", output_node="n15", nodes=nodes), "x")


class CapabilityPopulation(Case):
    def test_competing_providers_share_one_capability_without_new_roles(self):
        first = self.acquire(GEN1, GEN1_CASES)
        second = self.acquire(GEN1, GEN1_CASES, exclude_paths=(tuple(first["path"]),))
        self.assertEqual(first["capability"], second["capability"])
        self.assertEqual(first["role"], "csv-sum")
        self.assertIsNone(second["role"])                         # joined the population, no new role
        self.assertEqual(self.r.manifest()["bindings"]["csv-sum"], first["provider"])
        members = {m["provider"] for m in self.r.population.members(first["capability"])}
        self.assertEqual(members, {first["provider"], second["provider"]})
        self.assertNotIn("csv-sum-alt", self.r.manifest()["bindings"])
        for member in members:
            task = self.r.tasks.create_member_task("dev", first["capability"], member, "5,6", self.dev)
            self.assertEqual(self.r.tasks.run_task(task, self.r.tasks.authorize(task, "dev"), "dev"), 11)

    def test_capability_identity_is_a_contract_not_a_role_name(self):
        first = self.acquire(GEN1, GEN1_CASES)
        self.assertTrue(first["capability"].startswith("capability:csv-sum@"))
        self.assertEqual(self.r.registry.resolve(first["provider"])["capability"], first["capability"])

    def test_membership_requires_validation_and_matching_contract(self):
        capability = self.r.population.define("range-count", "range-batch", "integers",
                                              [({"data": [1, 5, 9], "queries": [[0, 5]]}, [2])])
        wrong = self.r.registry.register("sum")
        with self.assertRaisesRegex(Refused, "contract"):
            self.r.population.admit(capability, wrong, budget=self.val, principal="dev")
        bad_cases = self.r.population.define("range-count-bad", "range-batch", "integers",
                                             [({"data": [1], "queries": [[0, 5]]}, [99])])
        scan = self.r.registry.register("range_scan")
        with self.assertRaises(Refused):
            self.r.population.admit(bad_cases, scan, budget=self.val, principal="dev")
        self.assertEqual(self.r.population.members(bad_cases), [])
        with self.assertRaisesRegex(Refused, "active member"):
            self.r.tasks.create_member_task("dev", bad_cases, scan, {"data": [], "queries": []}, self.dev)

    def test_retirement_needs_evidence_and_restore_needs_validation(self):
        capability = self.r.population.define("range-count", "range-batch", "integers",
                                              [({"data": [1, 5, 9], "queries": [[0, 5]]}, [2])])
        a, b = self.r.registry.register("range_scan"), self.r.registry.register("range_bisect")
        for p in (a, b):
            self.r.population.admit(capability, p, budget=self.val, principal="dev")
        with self.assertRaises(Refused):
            self.r.population.retire(capability, a, reason="slower on average", evidence={"justified": False})
        self.r.population.retire(capability, a, reason="redundant", evidence={"justified": True})
        with self.assertRaisesRegex(Refused, "last active member"):
            self.r.population.retire(capability, b, reason="redundant", evidence={"justified": True})
        with self.assertRaisesRegex(Refused, "active member"):
            self.r.tasks.create_member_task("dev", capability, a, {"data": [], "queries": []}, self.dev)
        spent = self.r.resources.budget(self.val, "dev")["spent"]["attempts"]
        self.r.population.restore(capability, a, budget=self.val, principal="dev")
        self.assertGreater(self.r.resources.budget(self.val, "dev")["spent"]["attempts"], spent)
        self.assertEqual(len(self.r.population.members(capability)), 2)


class ClosureConformance(unittest.TestCase):
    def test_runtime_closure_equals_reference_on_random_populations(self):
        rng = random.Random(29)
        for trial in range(300):
            nodes = [f"p{i}" for i in range(rng.randint(1, 9))]
            edges = [(rng.choice(nodes), rng.choice(nodes)) for _ in range(rng.randint(0, 8))]
            tags = ["cpu", "gpu", "sort-buffer", "hash-table", "dom-a"]
            footprints = {n: set(rng.sample(tags, rng.randint(0, 2))) for n in nodes if rng.random() > 0.1}
            isolation = {n: set(rng.sample(tags, 1)) for n in nodes if rng.random() > 0.8}
            seed = set(rng.sample(nodes, rng.randint(0, min(2, len(nodes)))))
            with self.subTest(trial=trial):
                self.assertEqual(compute_closure(seed, edges, footprints, isolation),
                                 reference_closure(seed, edges, footprints, isolation))

    def test_indirect_shared_resource_overlap_is_included(self):
        affected, _ = compute_closure({"A"}, [], {"A": {"r1"}, "B": {"r1", "r2"}, "C": {"r2"}})
        self.assertEqual(affected, {"A", "B", "C"})

    def test_non_convergence_fails_closed(self):
        with self.assertRaises(Refused):
            compute_closure({"A"}, [("B", "A"), ("C", "B")], {"A": set(), "B": set(), "C": set()}, cap=0)


class ImpactEnforcement(Case):
    def test_population_resource_impact_spreads_through_footprints_and_dependents(self):
        g = self.acquire(GEN1, GEN1_CASES)
        scan, scan_list = self.r.registry.register("range_scan"), self.r.registry.register("range_scan_list")
        impact = self.r.fabric.impact(scan_list, "resources")
        self.assertIn(scan, impact["affected"])                   # shares cpu
        self.assertIn(g["provider"], impact["affected"])          # composite of cpu primitives
        self.assertEqual(impact["action"], "reevaluate")

    def test_block_is_enforced_at_every_boundary(self):
        g = self.acquire(GEN1, GEN1_CASES)
        parse = self.r.manifest()["bindings"]["parse"]
        task = self.r.tasks.create_task("dev", "csv-sum", "1,2", self.dev)
        token = self.r.tasks.authorize(task, "dev")
        self.r.fabric.apply_impact([parse], "support", "parser counterexample")
        with self.assertRaisesRegex(Refused, "blocked"):
            self.r.tasks.run_task(task, token, "dev")             # admitted before, refused at run
        with self.assertRaisesRegex(Refused, "blocked"):
            self.r.tasks.create_task("dev", "csv-sum", "1,2", self.dev)
        with self.assertRaisesRegex(Refused, "blocked"):
            self.r.transactor.stage({"csv-sum-2": g["provider"]})
        with self.assertRaisesRegex(Refused, "blocked"):
            self.r.population.member(g["capability"], g["provider"])
        self.assertEqual(self.r.population.members(g["capability"]), [])
        self.assertNotIn(g["provider"], [s["id"] for s in self.search.catalogue(cumulative=True)])

    def test_reevaluate_invalidates_prior_performance_evidence_only(self):
        scan = self.r.registry.register("range_scan")
        revision = self.r.manifest()["evidence_revision"]
        self.assertTrue(self.r.fabric.evidence_current(scan, revision))
        self.r.fabric.apply_impact([scan], "resources", "co-tenant contention on cpu")
        self.assertFalse(self.r.fabric.evidence_current(scan, revision))
        self.assertTrue(self.r.fabric.evidence_current(scan, self.r.manifest()["evidence_revision"]))
        self.r.registry.resolve(scan)                             # outputs remain usable

    def test_unknown_impact_is_conservative(self):
        scan = self.r.registry.register("range_scan")
        affected, action = self.r.registry.preview_impact([scan], "unknown")
        self.assertEqual(set(affected), set(self.r.registry.population()))
        self.assertEqual(action, "block")


class FundingLifecycle(Case):
    def test_policy_accrues_once_per_period_up_to_ceiling(self):
        budget = self.r.resources.create_budget("dev", {"attempts": 2})
        self.r.resources.attach_policy(budget, issued_by="operator", period_seconds=60,
                                       grant={"attempts": 5}, ceiling={"attempts": 8})
        self.r.resources.reserve(budget, "dev", {"attempts": 2})
        self.assertEqual(self.r.resources.budget(budget, "dev")["available"]["attempts"], 0)
        self.now[0] += 59
        self.assertEqual(self.r.resources.budget(budget, "dev")["available"]["attempts"], 0)
        self.now[0] += 1
        self.assertEqual(self.r.resources.budget(budget, "dev")["available"]["attempts"], 5)
        self.assertEqual(self.r.resources.budget(budget, "dev")["available"]["attempts"], 5)  # once per period
        self.now[0] += 600
        record = self.r.resources.budget(budget, "dev")
        self.assertEqual(record["available"]["attempts"], 8)                       # ceiling
        self.assertEqual(record["available"]["attempts"] + record["spent"]["attempts"]
                         + 2, record["capacity"]["attempts"])                         # 2 still held
        funded = [e for e in self.r.store.journal() if e["kind"] == "funded" and e["budget"] == budget]
        self.assertEqual([e["added"]["attempts"] for e in funded], [5, 3])

    def test_development_principal_cannot_mint_or_self_fund(self):
        budget = self.r.resources.create_budget("dev", {"attempts": 1})
        for issuer in ("dev", "provider"):
            with self.subTest(issuer=issuer), self.assertRaisesRegex(Refused, "operator"):
                self.r.resources.create_budget("dev", {"attempts": 10**6}, issued_by=issuer)
            with self.subTest(issuer=issuer), self.assertRaisesRegex(Refused, "operator"):
                self.r.resources.attach_policy(budget, issued_by=issuer, period_seconds=1,
                                               grant={"attempts": 1}, ceiling={"attempts": 1})

    def test_operator_cannot_fund_its_own_budget(self):
        own = self.r.resources.create_budget("operator", {"attempts": 1})
        with self.assertRaisesRegex(Refused, "own budget"):
            self.r.resources.attach_policy(own, issued_by="operator", period_seconds=1,
                                           grant={"attempts": 1}, ceiling={"attempts": 1})

    def test_kernel_validation_budget_replenishes_instead_of_exhausting(self):
        key = self.r.store.get("system", "validation-budget")["id"]
        for _ in range(140):
            if self.r.resources.budget(key, "_kernel_validation")["available"]["attempts"] < 1:
                break
            c = self.r.transactor.stage({"total": self.r.registry.register("sum_loop")})
            self.r.transactor.validate(c, {"total": [([1], 1)]})
        with self.assertRaises(Refused):
            c = self.r.transactor.stage({"total": self.r.registry.register("sum_loop")})
            self.r.transactor.validate(c, {"total": [([1], 1)]})
        self.now[0] += 3600
        c = self.r.transactor.stage({"total": self.r.registry.register("sum_loop")})
        self.r.transactor.validate(c, {"total": [([1], 1)]})

    def test_development_and_ecology_modules_never_issue_funding(self):
        for name in ("development.py", "ecology.py", "population.py", "fabric.py"):
            source = (Path(__file__).resolve().parents[1] / "src" / "brainos" / name).read_text(encoding="utf-8")
            for call in ("create_budget", "attach_policy", "_accrue_tx"):
                self.assertNotIn(call, source, f"{name} calls {call}")


class ConstructionDeadline(Case):
    def test_overall_deadline_stops_search_and_records_non_attainment(self):
        slow = self.r.runner.compute
        def lag(*args, **kwargs):
            time.sleep(0.25)
            return slow(*args, **kwargs)
        demand = CapabilityDemand("x", "text", "integer", (("1", 1), ("2", 2), ("3", 3)),
                                  max_candidates=64, deadline_seconds=0.6)
        started = time.monotonic()
        with patch.object(self.r.runner, "compute", side_effect=lag):
            result = self.acquire(demand, [("4", 4)])
        self.assertLess(time.monotonic() - started, 3.0)
        self.assertEqual(result["status"], "NON_ATTAINMENT")
        reasons = [t.get("reason", "") for t in self.r.store.find("construction") if t["run"] == result["run"]]
        self.assertTrue(any("deadline" in reason for reason in reasons), reasons)

    def test_deadline_is_bounded(self):
        demand = CapabilityDemand("x", "text", "integer", (("1", 1),), deadline_seconds=301)
        with self.assertRaises(Refused):
            list(self.search.discover(demand, "dev", self.dev))


class GraphReachability(Case):
    def test_non_contributing_nodes_are_refused(self):
        b = self.r.manifest()["bindings"]
        dead = dict(input="text", output="integer", output_node="n1",
                    nodes=[dict(id="n0", provider=b["parse"], input="$input"),
                           dict(id="n1", provider=b["total"], input="n0"),
                           dict(id="n2", provider=b["count"], input="n0")])
        with self.assertRaisesRegex(Refused, "contribute"):
            self.r.registry.register_graph(dead, "dead")

    def test_contributing_chain_is_accepted(self):
        b = self.r.manifest()["bindings"]
        chain = dict(input="text", output="integer", output_node="n1",
                     nodes=[dict(id="n0", provider=b["parse"], input="$input"),
                            dict(id="n1", provider=b["total"], input="n0")])
        self.assertEqual(self.r.registry.resolve(self.r.registry.register_graph(chain, "ok"))["cost"],
                         {"attempts": 2})


class ConstructionProvenance(Case):
    def test_runs_and_trials_pin_state_demand_evaluation_costs_and_dependencies(self):
        g1 = self.acquire(GEN1, GEN1_CASES, cumulative=True)
        g2 = self.acquire(GEN2, GEN2_CASES, cumulative=True)
        run = self.r.store.get("construction-run", g2["run"])
        for key in ("pinned", "demand_definition", "demand_digest", "catalogue", "evaluation", "budgets",
                    "search", "validation_attempts", "consequences"):
            self.assertIn(key, run)
        self.assertEqual(run["demand_definition"]["name"], "csv-neg-sum")
        self.assertIn(g1["provider"], run["catalogue"])
        self.assertEqual(run["status"], "ACQUIRED")
        self.assertGreater(run["validation_attempts"], 0)
        self.assertEqual(run["consequences"][0]["provider"], g2["provider"])
        acquired = next(t for t in self.r.store.find("construction") if t["id"] == g2["trial"])
        self.assertIn(g1["provider"], acquired["dependencies"]["direct"])
        self.assertTrue(set(acquired["dependencies"]["transitive"]) >= set(g1["path"]))
        self.assertEqual(acquired["pinned"], run["pinned"])
        trials = [t for t in self.r.store.find("construction") if t["run"] == g2["run"]]
        self.assertTrue(all("costs" in t for t in trials if t["status"] in ("NOMINATED", "REJECTED_DEVELOPMENT")))


if __name__ == "__main__":
    unittest.main()
