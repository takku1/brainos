"""Bounded assimilation (Doc 21 section 21.13): nomination, union gate, atomic
publication, interruption, recovery and boundaries."""
from pathlib import Path
import random
import tempfile
import unittest
from unittest.mock import patch

from brainos import Refused, Runtime
from brainos import providers
from brainos.assimilation import AssimilationSearch, EvaluationSet, Gate
from brainos.runner import make_runner

EXACT_CASES = [({"data": [1, 5, 5, 9], "queries": [5, 2]}, [2, 0]), ({"data": [], "queries": [1]}, [0])]
RANGE_CASES = [({"data": [1, 5, 9], "queries": [[0, 5]]}, [2]), ({"data": [3, 3, 7], "queries": [[3, 3]]}, [2])]
TOTAL_CASES = [({"data": [1, 5, 5, 9], "queries": [5, 9]}, 3)]


def dataset(rng, n=600):
    return [rng.randrange(5000) for _ in range(n)]


def evaluation(seed=1, wide=False, epochs=3):
    rng = random.Random(seed)
    out = []
    for e in range(epochs):
        data = dataset(rng)
        name = "observed" if e < epochs - 1 else "held-out"
        width = (2000, 3000) if wide else (5, 50)
        out.append([("exact", {"data": data, "queries": [rng.randrange(5000) for _ in range(20)]}, name),
                    ("range", {"data": data, "queries": [[lo, lo + rng.randint(*width)]
                                                          for lo in (rng.randrange(2000) for _ in range(10))]}, name)])
    return out


class Organization(unittest.TestCase):
    profile = "inprocess"

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.temp.name) / "c.db", profile=self.profile)
        r = self.r
        self.budget = r.resources.create_budget("dev", {"attempts": 4000})
        self.exact = r.population.define("exact-count", "exact-batch", "integers", EXACT_CASES)
        self.range = r.population.define("range-count", "range-batch", "integers", RANGE_CASES)
        self.ids = {n: r.registry.register(n) for n in ("exact_hash", "range_sorted", "sum")}
        r.population.admit(self.exact, self.ids["exact_hash"], budget=self.budget, principal="dev")
        r.population.admit(self.range, self.ids["range_sorted"], budget=self.budget, principal="dev")
        c = r.transactor.stage({"exact": self.ids["exact_hash"], "range": self.ids["range_sorted"]})
        r.transactor.validate(c, {"exact": EXACT_CASES, "range": RANGE_CASES}, budget=self.budget, principal="dev")
        r.transactor.commit(c)
        graph = dict(input="exact-batch", output="integer", output_node="n1",
                     nodes=[dict(id="n0", provider=self.ids["exact_hash"], input="$input"),
                            dict(id="n1", provider=self.ids["sum"], input="n0")])
        self.total = r.registry.register_graph(graph, "exact-total")
        c = r.transactor.stage({"exact-total": self.total})
        r.transactor.validate(c, {"exact-total": TOTAL_CASES}, budget=self.budget, principal="dev")
        r.transactor.commit(c)
        self.parents = [dict(capability=self.exact, provider=self.ids["exact_hash"]),
                        dict(capability=self.range, provider=self.ids["range_sorted"])]
        self.search = AssimilationSearch(r)
        self.roles = {"exact": EXACT_CASES, "range": RANGE_CASES, "exact-total": TOTAL_CASES}

    def tearDown(self):
        self.r.close()
        self.temp.cleanup()

    def evalset(self, **kw):
        epochs = evaluation(**kw)
        epochs = [[(self.exact if c == "exact" else self.range, v, s) for c, v, s in e] for e in epochs]
        dependents = {"exact-total": [v for e in epochs for c, v, s in e if c == self.exact]}
        return EvaluationSet(epochs=epochs, dependents=dependents)

    def gate(self, **kw):
        return Gate(tolerance={self.exact: kw.pop("exact", 50.0), self.range: kw.pop("range", 1.5)},
                    horizon_epochs=kw.pop("horizon", 1e12), **kw)

    def sorted_candidate(self):
        nominated, _ = self.search.nominate(self.parents)
        return next(c for c in nominated if c["implementations"][self.exact] == "exact_sorted")

    def accepted(self):
        verdict = self.search.evaluate(self.sorted_candidate(), self.parents, self.evalset(), self.gate(),
                                       budget=self.budget, principal="dev")
        self.assertTrue(verdict["accepted"], verdict["reasons"])
        return verdict

    def run_role(self, role, value):
        task = self.r.tasks.create_task("dev", role, value, self.budget)
        return task, self.r.tasks.run_task(task, self.r.tasks.authorize(task, "dev"), "dev")


class SharedRepresentation(unittest.TestCase):
    def test_only_identical_prepare_stages_share_structures(self):
        runner = make_runner("inprocess")
        runner.clear_prepared()
        data = list(range(300, 0, -1))
        seen = []
        for name, q in (("exact_sorted", [5]), ("range_sorted", [[1, 9]]), ("exact_hash", [5]), ("range_hash_index", [[1, 3]])):
            runner.compute(providers.specification(name), {"data": data, "queries": q}, 10, on_timing=seen.append)
        hits = [t["cache_hit"] for t in seen]
        self.assertEqual(hits, [False, True, False, True])          # sorted shared; hash shared; never across
        self.assertTrue(all(t["state_bytes"] > 0 for t in seen))
        self.assertEqual(seen[1]["prepare_ns"], 0)
        runner.clear_prepared()
        again = []
        runner.compute(providers.specification("range_sorted"), {"data": data, "queries": [[1, 9]]}, 10,
                       on_timing=again.append)
        self.assertFalse(again[0]["cache_hit"])

    def test_cache_is_keyed_by_data_and_never_changes_results(self):
        runner = make_runner("inprocess")
        a, b = [1, 2, 2, 3], [9, 9, 9]
        spec = providers.specification("exact_hash")
        self.assertEqual(runner.compute(spec, {"data": a, "queries": [2, 9]}, 10), [2, 0])
        self.assertEqual(runner.compute(spec, {"data": b, "queries": [2, 9]}, 10), [0, 3])
        self.assertEqual(runner.compute(spec, {"data": a, "queries": [2, 9]}, 10), [2, 0])

    def test_prepare_identity_is_part_of_artifact_identity(self):
        self.assertEqual(providers.specification("exact_sorted")["prepare"],
                         providers.specification("range_sorted")["prepare"])
        self.assertNotEqual(providers.specification("exact_hash")["prepare"],
                            providers.specification("exact_dict")["prepare"])
        self.assertIsNone(providers.specification("exact_scan")["prepare"])


class Nomination(Organization):
    def test_enumerates_admissible_candidates_not_one_answer(self):
        nominated, controls = self.search.nominate(self.parents)
        impls = {tuple(sorted(c["implementations"].values())) for c in nominated}
        self.assertIn(("exact_sorted", "range_sorted"), impls)
        self.assertIn(("exact_hash", "range_hash_index"), impls)
        self.assertIn(("exact_scan", "range_scan_staged"), impls)
        self.assertGreaterEqual(len(nominated), 3)
        self.assertTrue(all(c["structures"] < c["parent_structures"] for c in nominated))
        self.assertEqual({c["kind"] for c in controls}, {"originals", "wrapper"})
        self.assertNotIn(tuple(sorted(self.ids[n] for n in ("exact_hash", "range_sorted"))),
                         {tuple(sorted(c["assignment"].values())) for c in nominated})

    def test_duplicates_of_one_contract_nominate_selection(self):
        dict_id = self.r.registry.register("exact_dict")
        self.r.population.admit(self.exact, dict_id, budget=self.budget, principal="dev")
        parents = [dict(capability=self.exact, provider=self.ids["exact_hash"]),
                   dict(capability=self.exact, provider=dict_id)]
        nominated, _ = self.search.nominate(parents)
        methods = {(c["implementations"][self.exact], c["method"]) for c in nominated}
        self.assertIn(("exact_hash", "duplicate-selection"), methods)
        self.assertIn(("exact_dict", "duplicate-selection"), methods)
        self.assertIn(("exact_sorted", "structural-factoring"), methods)
        self.assertIn(("exact_scan", "structure-elimination"), methods)

    def test_duplicate_removal_is_justified_only_by_declared_upkeep(self):
        dict_id = self.r.registry.register("exact_dict")
        self.r.population.admit(self.exact, dict_id, budget=self.budget, principal="dev")
        parents = [dict(capability=self.exact, provider=self.ids["exact_hash"]),
                   dict(capability=self.exact, provider=dict_id)]
        nominated, _ = self.search.nominate(parents)
        keep = next(c for c in nominated if c["implementations"][self.exact] == "exact_hash")
        epochs = [[e for e in epoch if e[0] == self.exact] for epoch in self.evalset().epochs]
        evalset = EvaluationSet(epochs=epochs, dependents=self.evalset().dependents)
        none = self.search.evaluate(keep, parents, evalset, self.gate(upkeep_ns_per_provider_epoch=0),
                                    budget=self.budget, principal="dev")
        paid = self.search.evaluate(keep, parents, evalset, self.gate(upkeep_ns_per_provider_epoch=1e9),
                                    budget=self.budget, principal="dev")
        self.assertEqual(paid["upkeep_saving_ns"], 1e9)
        self.assertTrue(paid["accepted"], paid["reasons"])
        self.assertGreater(paid["mean_savings_ns"], none["mean_savings_ns"])

    def test_nomination_is_recorded(self):
        self.search.nominate(self.parents)
        self.assertEqual([t["kind"] for t in self.r.store.find("assimilation-trial")], ["nomination"])


class UnionGate(Organization):
    def test_factored_candidate_preserves_outputs_and_dependents(self):
        verdict = self.accepted()
        self.assertEqual(verdict["mismatches"], 0)
        self.assertIn("exact-total", verdict["rebuilt"])
        self.assertLess(verdict["state_bytes_after"], verdict["state_bytes_before"])

    def test_candidate_violating_a_latency_tolerance_is_rejected(self):
        nominated, _ = self.search.nominate(self.parents)
        hashed = next(c for c in nominated if c["implementations"][self.range] == "range_hash_index")
        verdict = self.search.evaluate(hashed, self.parents, self.evalset(wide=True), self.gate(),
                                       budget=self.budget, principal="dev")
        self.assertFalse(verdict["accepted"])
        self.assertTrue(any("range-count" in r and ("tolerance" in r or "early stop" in r) for r in verdict["reasons"]),
                        verdict["reasons"])

    def test_output_mismatch_is_rejected(self):
        candidate = self.sorted_candidate()
        real = self.search.ctx.compute
        sorted_id = candidate["assignment"][self.exact]
        def wrong(spec, value, timeout, **kw):
            out = real(spec, value, timeout, **kw)
            return [x + 1 for x in out] if spec["id"] == sorted_id else out
        self.search.ctx.compute = wrong
        verdict = self.search.evaluate(candidate, self.parents, self.evalset(), self.gate(),
                                       budget=self.budget, principal="dev")
        self.assertFalse(verdict["accepted"])
        self.assertTrue(any("mismatch" in r for r in verdict["reasons"]))

    def test_economic_horizon_and_missing_downstream_inputs_are_enforced(self):
        candidate = self.sorted_candidate()
        verdict = self.search.evaluate(candidate, self.parents, self.evalset(), self.gate(horizon=1e-9),
                                       budget=self.budget, principal="dev")
        self.assertFalse(verdict["accepted"])
        self.assertTrue(any("break-even" in r or "no per-epoch saving" in r for r in verdict["reasons"]))
        bare = self.evalset()
        bare.dependents = {}
        verdict = self.search.evaluate(candidate, self.parents, bare, self.gate(), budget=self.budget, principal="dev")
        self.assertTrue(any("downstream role 'exact-total' has no evaluation inputs" in r for r in verdict["reasons"]))

    def test_evaluation_is_charged_and_recorded(self):
        before = self.r.resources.budget(self.budget, "dev")["spent"]["attempts"]
        verdict = self.accepted()
        self.assertGreater(self.r.resources.budget(self.budget, "dev")["spent"]["attempts"], before)
        self.assertGreater(verdict["construction_ns"], 0)
        kinds = [t["kind"] for t in self.r.store.find("assimilation-trial")]
        self.assertIn("evaluation", kinds)


class AtomicPublication(Organization):
    def test_publication_rebinds_dependents_and_supersedes_parents(self):
        verdict = self.accepted()
        epoch = self.r.manifest()["epoch"]
        value = {"data": [4, 4, 8], "queries": [4, 7]}
        _, before_total = self.run_role("exact-total", value)
        aid = self.search.publish(verdict, self.parents, self.roles, budget=self.budget, principal="dev")
        bindings = self.r.manifest()["bindings"]
        self.assertEqual(bindings["exact"], verdict["assignment"][self.exact])
        self.assertEqual(bindings["exact-total"], verdict["rebuilt"]["exact-total"]["provider"])
        self.assertEqual(self.r.population.state(self.exact, self.ids["exact_hash"]), "DORMANT")
        self.assertEqual(self.r.population.state(self.range, self.ids["range_sorted"]), "ACTIVE")   # kept
        self.assertGreater(self.r.manifest()["epoch"], epoch)
        self.assertEqual(self.run_role("exact-total", value)[1], before_total)
        record = self.r.store.get("assimilation", aid)
        self.assertEqual(record["state"], "PUBLISHED")
        self.assertEqual([p["provider"] for p in record["parents"]], [self.ids["exact_hash"]])

    def plan(self, verdict, *, drop_binding=False, drop_member=False):
        ctx = self.search.ctx
        members = [] if drop_member else [ctx.prepare_membership(self.exact, verdict["assignment"][self.exact],
                                                                 self.budget, "dev")]
        roles = {k: v for k, v in verdict["rebuilt"].items() if not (drop_binding and k == "exact-total")}
        bindings = [ctx.prepare_binding(role, item["provider"], self.roles[role], self.budget, "dev")
                    for role, item in sorted(roles.items())]
        return dict(id="assimilation:test", parents=[self.parents[0]], kept=[self.parents[1]], members=members,
                    bindings=bindings)

    def assert_unchanged(self, manifest):
        self.assertEqual(self.r.manifest(), manifest)
        self.assertEqual(self.r.population.state(self.exact, self.ids["exact_hash"]), "ACTIVE")

    def test_hidden_dependency_and_missing_coverage_are_refused(self):
        verdict = self.accepted()
        manifest = self.r.manifest()
        with self.assertRaisesRegex(Refused, "hidden dependency: role 'exact-total'"):
            self.r.transactor.commit_assimilation(self.plan(verdict, drop_binding=True))
        self.assert_unchanged(manifest)
        with self.assertRaisesRegex(Refused, "missing parent coverage"):
            self.r.transactor.commit_assimilation(self.plan(verdict, drop_member=True))
        self.assert_unchanged(manifest)

    def test_stale_evidence_and_concurrent_publication_are_refused(self):
        verdict = self.accepted()
        first, second = self.plan(verdict), self.plan(verdict)
        self.r.transactor.commit_assimilation(first)
        with self.assertRaisesRegex(Refused, "stale"):
            self.r.transactor.commit_assimilation(dict(second, id="assimilation:second"))
        self.assertEqual(len(self.r.store.find("assimilation")), 1)

    def test_evidence_change_between_validation_and_commit_is_refused(self):
        verdict = self.accepted()
        plan = self.plan(verdict)
        manifest_before = self.r.manifest()
        self.r.fabric.apply_impact([self.ids["sum"]], "resources", "unrelated contention")
        with self.assertRaisesRegex(Refused, "stale"):
            self.r.transactor.commit_assimilation(plan)
        self.assertEqual(self.r.manifest()["bindings"], manifest_before["bindings"])

    def test_unvalidated_candidate_is_refused(self):
        verdict = self.accepted()
        plan = self.plan(verdict)
        plan["members"] = [self.r.transactor.stage_membership(self.exact, verdict["assignment"][self.exact])]
        with self.assertRaisesRegex(Refused, "no current validation"):
            self.r.transactor.commit_assimilation(plan)

    def test_candidate_validation_failure_leaves_organization_untouched(self):
        verdict = self.accepted()
        manifest = self.r.manifest()
        with patch.object(self.r.transactor.runner, "compute", side_effect=Refused("worker failed")):
            with self.assertRaises(Refused):
                self.search.publish(verdict, self.parents, self.roles, budget=self.budget, principal="dev")
        self.assert_unchanged(manifest)


class InterruptedAssimilation(Organization):
    def test_crash_inside_commit_rolls_back_and_candidates_go_stale_on_restart(self):
        verdict = self.accepted()
        plan = AtomicPublication.plan(self, verdict)
        manifest = self.r.manifest()
        self.r.transactor.failpoint = lambda point: (_ for _ in ()).throw(OSError("crash")) \
            if point == "during_assimilation_commit" else None
        with self.assertRaises(OSError):
            self.r.transactor.commit_assimilation(plan)
        AtomicPublication.assert_unchanged(self, manifest)
        self.assertFalse(self.r.store.find("assimilation"))
        path = self.r.store.path
        self.r.close()
        self.r = Runtime(path, profile=self.profile)
        for candidate in plan["members"] + plan["bindings"]:
            self.assertEqual(self.r.store.get("candidate", candidate)["state"], "STALE")
        self.assertEqual(self.r.population.state(self.exact, self.ids["exact_hash"]), "ACTIVE")


class Recovery(Organization):
    def published(self):
        verdict = self.accepted()
        return verdict, self.search.publish(verdict, self.parents, self.roles, budget=self.budget, principal="dev")

    def test_post_publication_competence_loss_restores_parents_with_fresh_validation(self):
        pre_task = self.r.tasks.create_task("dev", "exact", {"data": [1], "queries": [1]}, self.budget)
        pre_permit = self.r.tasks.authorize(pre_task, "dev")
        verdict, aid = self.published()
        mid_task = self.r.tasks.create_task("dev", "exact", {"data": [1], "queries": [1]}, self.budget)
        mid_permit = self.r.tasks.authorize(mid_task, "dev")
        self.r.fabric.apply_impact([verdict["assignment"][self.exact]], "support", "post-publication counterexample")
        with self.assertRaisesRegex(Refused, "blocked"):
            self.run_role("exact", {"data": [1], "queries": [1]})
        spent = self.r.resources.budget(self.budget, "dev")["spent"]["attempts"]
        self.search.recover(aid, self.roles, budget=self.budget, principal="dev", reason="competence loss")
        self.assertGreater(self.r.resources.budget(self.budget, "dev")["spent"]["attempts"], spent)  # revalidated
        bindings = self.r.manifest()["bindings"]
        self.assertEqual(bindings["exact"], self.ids["exact_hash"])
        self.assertEqual(bindings["exact-total"], self.total)
        self.assertEqual(self.r.population.state(self.exact, self.ids["exact_hash"]), "ACTIVE")
        self.assertEqual(self.r.population.state(self.exact, verdict["assignment"][self.exact]), "DORMANT")
        self.assertEqual(self.run_role("exact-total", {"data": [2, 2, 3], "queries": [2, 3]})[1], 3)
        for task, permit in ((pre_task, pre_permit), (mid_task, mid_permit)):
            with self.assertRaises(Refused):
                self.r.tasks.run_task(task, permit, "dev")
        self.assertEqual(self.r.store.get("assimilation", aid)["state"], "REVERTED")

    def test_recovery_requires_bindings_back_to_previous_providers(self):
        verdict, aid = self.published()
        with self.assertRaisesRegex(Refused, "needs a validated binding back"):
            self.r.transactor.revert_assimilation(aid, reason="x")
        with self.assertRaisesRegex(Refused, "cause"):
            self.r.transactor.revert_assimilation(aid, reason="")


class Boundaries(Organization):
    def test_search_holds_only_the_restricted_context(self):
        self.assertFalse(any(isinstance(v, Runtime) for v in vars(self.search).values()))
        for name in ("store", "resources", "transactor", "runtime"):
            self.assertFalse(hasattr(self.search.ctx, name))

    def test_assimilation_never_archives_and_records_every_step(self):
        verdict = self.accepted()
        aid = self.search.publish(verdict, self.parents, self.roles, budget=self.budget, principal="dev")
        self.assertNotIn("ARCHIVED", {m["state"] for m in self.r.store.find("member")})
        self.r.fabric.apply_impact([verdict["assignment"][self.exact]], "support", "drill")
        self.search.recover(aid, self.roles, budget=self.budget, principal="dev", reason="drill")
        kinds = [t["kind"] for t in self.r.store.find("assimilation-trial")]
        for kind in ("nomination", "evaluation", "publication", "recovery"):
            self.assertIn(kind, kinds)
        self.assertNotIn("ARCHIVED", {m["state"] for m in self.r.store.find("member")})


class GateCorrections(Organization):
    """X3 corrections (Doc 31 section 31.12): full nomination cost, early stop,
    confidence-bounded tolerance and declared internal state."""

    def verdicts(self, gate):
        nominated, _ = self.search.nominate(self.parents)
        evalset = self.evalset()
        return [self.search.evaluate(c, self.parents, evalset, gate, budget=self.budget, principal="dev")
                for c in nominated]

    def test_selection_charges_the_whole_nomination(self):
        gate = self.gate(maintenance_ns_per_byte_epoch=1000.0)       # make the state saving dominate
        verdicts = self.verdicts(gate)
        sorted_v = next(v for v in verdicts if v["implementations"][self.exact] == "exact_sorted")
        self.assertTrue(sorted_v["competent"], sorted_v["reasons"])
        own = sorted_v["construction_ns"] / sorted_v["mean_savings_ns"]
        total = sum(v["construction_ns"] for v in verdicts) / sorted_v["mean_savings_ns"]
        self.assertGreater(total, own)
        tight = self.gate(maintenance_ns_per_byte_epoch=1000.0, horizon=(own + total) / 2)
        self.assertIsNone(self.search.select(verdicts, tight))
        self.assertIn("nomination break-even", " ".join(sorted_v["final_reasons"]))
        roomy = self.gate(maintenance_ns_per_byte_epoch=1000.0, horizon=total * 2)
        self.assertIs(self.search.select(verdicts, roomy), sorted_v)

    def test_early_stop_bounds_the_cost_of_a_hopeless_candidate(self):
        nominated, _ = self.search.nominate(self.parents)
        scan = next(c for c in nominated if c["implementations"][self.exact] == "exact_scan")
        evalset = self.evalset(wide=True, epochs=4)
        full = self.search.evaluate(scan, self.parents, evalset, self.gate(early_stop_factor=1e12),
                                    budget=self.budget, principal="dev")
        stopped = self.search.evaluate(scan, self.parents, evalset, self.gate(early_stop_factor=3.0),
                                       budget=self.budget, principal="dev")
        self.assertTrue(stopped["early_stop"])
        self.assertFalse(stopped["accepted"])
        self.assertLess(stopped["construction_ns"], 0.6 * full["construction_ns"])

    def test_confidence_bound_rejects_a_ratio_whose_median_is_under_tolerance(self):
        candidate = self.sorted_candidate()
        sorted_id = candidate["assignment"][self.exact]
        real = self.search._run
        ratios = iter([1.5, 1.5, 1.5, 9.0, 9.0, 1.5] * 10)
        def scripted(spec, value, budget, principal, timings):
            out, timing = real(spec, value, budget, principal, timings)
            timing = dict(timing, answer_ns=100_000)
            if spec["id"] == sorted_id:
                timing["answer_ns"] = int(100_000 * next(ratios))
            return out, timing
        self.search._run = scripted
        verdict = self.search.evaluate(candidate, self.parents, self.evalset(epochs=8), self.gate(exact=3.0),
                                       budget=self.budget, principal="dev")
        ratio = verdict["latency_ratio"][self.exact]
        self.assertLess(min(v for k, v in ratio.items() if isinstance(v, float) and k != "upper_bound"), 3.0)
        self.assertGreater(ratio["upper_bound"], 3.0)
        self.assertTrue(any("upper bound" in r for r in verdict["reasons"]), verdict["reasons"])

    def test_internal_state_primitives_are_not_offered_as_stateless(self):
        self.assertTrue(providers.specification("range_bisect")["internal_state"])
        self.assertNotIn("internal_state", providers.specification("range_sorted"))
        nominated, _ = self.search.nominate(self.parents)
        stateless = [c for c in nominated if c["method"] == "structure-elimination"]
        self.assertTrue(stateless)
        for c in stateless:
            self.assertFalse({"range_bisect", "range_hash"} & set(c["implementations"].values()), c)


class FrozenPreregistration(unittest.TestCase):
    def test_runner_refuses_changed_or_uncommitted_preregistration(self):
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
        import run_assimilation
        with tempfile.TemporaryDirectory() as d:
            copy = Path(d) / "PREREGISTRATION.md"
            copy.write_text("changed", encoding="utf-8")
            with self.assertRaises(SystemExit):
                run_assimilation.verify_frozen(copy, run_assimilation.PREREG_SHA256)
        self.assertEqual(run_assimilation.digest_of(run_assimilation.PREREG), run_assimilation.PREREG_SHA256)
        probe = Path(run_assimilation.ROOT) / "docs" / "results" / "uncommitted-x3-probe.md"
        probe.write_text("probe", encoding="utf-8")
        try:
            with self.assertRaises(SystemExit):
                run_assimilation.verify_frozen(probe, run_assimilation.digest_of(probe))
        finally:
            probe.unlink()


if __name__ == "__main__":
    unittest.main()
