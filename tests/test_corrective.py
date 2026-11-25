"""Discriminating regressions for review findings B01-B06 and the composition fabric.

Each B-test fails on the committed baseline (08cdd17) and passes on the corrected
profile; docs/results/*/baseline-findings.json records the baseline reproduction.
"""
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from brainos import Refused, Runtime
from brainos.__main__ import install
from brainos.contracts import Cancelled
from brainos.development import CapabilityDemand, CompositionSearch
from brainos.effects import LocalReceiptSink
from brainos import providers

PARENTS = {"parse": "parse_csv", "total": "sum", "total_loop": "sum_loop", "count": "count",
           "length": "text_length", "negate": "negate"}
PARENT_CASES = {"parse": [("1,2", [1, 2])], "total": [([1, 2], 3)], "total_loop": [([1, 2], 3)],
                "count": [([1, 2], 2)], "length": [("ab", 2)], "negate": [(3, -3)]}
SUM_DEMAND = CapabilityDemand("csv-sum", "text", "integer", (("1,2,3", 6), ("10, -4", 6)))
ADMISSION = [("4,5", 9), ("", 0), ("7", 7)]


class Case(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.now = [100.0]
        self.r = Runtime(self.root / "core.sqlite3", clock=lambda: self.now[0])
        install(self.r, {"total": "sum"}, {"total": [([1, 2], 3)]})
        self.budget = self.r.resources.create_budget("alice", {"attempts": 40})

    def tearDown(self):
        self.r.close()
        self.temp.cleanup()

    def spent(self, budget=None, principal="alice"):
        return self.r.resources.budget(budget or self.budget, principal)["spent"]["attempts"]

    def available(self, budget=None, principal="alice"):
        return self.r.resources.budget(budget or self.budget, principal)["available"]["attempts"]

    def completed(self):
        task = self.r.tasks.create_task("alice", "total", [1, 2], self.budget)
        self.r.tasks.run_task(task, self.r.tasks.authorize(task, "alice"), "alice")
        return task

    def scoped(self, task, sink, payload):
        return self.r.evidence.record_evidence("checker", {"pass": True}, "Certified",
            support=self.r.effects.required_support(task, "alice", sink.identity, payload))


class B01MinimumGrant(Case):
    def test_zero_or_partial_grant_is_refused_before_reservation(self):
        for amount in ({"attempts": 0}, {}, {"gpu": 1}):
            with self.subTest(amount=amount), self.assertRaises(Refused):
                self.r.tasks.create_task("alice", "total", [1, 2], self.budget, amount=amount)
        self.assertEqual(self.available(), 40)

    def test_default_grant_is_derived_and_actually_spent(self):
        self.completed()
        self.assertEqual(self.spent(), 1)

    def test_zero_capacity_budget_cannot_execute(self):
        empty = self.r.resources.create_budget("alice", {"attempts": 0})
        with self.assertRaises(Refused):
            self.r.tasks.create_task("alice", "total", [1, 2], empty)

    def test_trusted_primitive_cost_must_be_positive(self):
        broken = providers.Primitive(providers.sum_builtin, "integers", "integer", "sum-integers", attempts=0)
        with patch.dict(providers.PRIMITIVES, {"sum": broken}), self.assertRaisesRegex(Refused, "positive"):
            providers.specification("sum")


class B02DispatchLinearization(Case):
    """Durable dispatch admission is the linearization point; it is not application."""

    def prepared(self, sink, payload=None):
        payload = {"x": 3} if payload is None else payload
        task = self.completed()
        return self.r.effects.prepare_effect(task, "alice", sink.identity, payload, self.budget,
                                             [self.scoped(task, sink, payload)])

    def test_control_changes_before_admission_prevent_application(self):
        changes = {
            "revoke": lambda token, support: self.r.authority.revoke(token),
            "challenge": lambda token, support: self.r.evidence.challenge(support, "counterexample"),
            "publish": lambda token, support: install(self.r, {"total": "sum_loop"}, {"total": [([1, 2], 3)]}),
        }
        for label, change in changes.items():
            with self.subTest(change=label), LocalReceiptSink(self.root / f"{label}.db") as sink:
                effect, token = self.prepared(sink)
                support = self.r.store.get("permit", token)["evidence"][0]
                fired = []
                def failpoint(point):
                    if point == "before_effect_admission" and not fired:
                        fired.append(point)
                        change(token, support)
                self.r.effects.failpoint = failpoint
                with self.assertRaises(Refused):
                    self.r.effects.dispatch_effect(effect, token, "alice", sink)
                self.assertEqual(fired, ["before_effect_admission"])
                self.assertEqual(sink.applied_events(), [])
                self.assertEqual(self.r.store.get("effect", effect)["state"], "INTENT")
                self.r.effects.failpoint = lambda point: None

    def test_control_changes_after_admission_do_not_recall_admitted_effect(self):
        with LocalReceiptSink(self.root / "after.db") as sink:
            effect, token = self.prepared(sink)
            support = self.r.store.get("permit", token)["evidence"][0]
            def failpoint(point):
                if point == "before_effect_apply":
                    self.r.authority.revoke(token)
                    self.r.evidence.challenge(support, "late counterexample")
            self.r.effects.failpoint = failpoint
            receipt = self.r.effects.dispatch_effect(effect, token, "alice", sink)
            record = self.r.store.get("effect", effect)
            self.assertEqual(record["state"], "CONFIRMED")
            self.assertEqual(record["dispatch_admission"]["linearization"], "durable-dispatch-commit")
            self.assertEqual(receipt["endpoint"], sink.identity)
            self.assertEqual(len(sink.applied_events()), 1)

    def test_admission_is_reported_separately_from_confirmed_application(self):
        with LocalReceiptSink(self.root / "split.db") as sink:
            effect, token = self.prepared(sink)
            observed = {}
            def failpoint(point):
                if point == "before_effect_apply":
                    observed.update(self.r.store.get("effect", effect))
            self.r.effects.failpoint = failpoint
            self.r.effects.dispatch_effect(effect, token, "alice", sink)
            self.assertEqual(observed["state"], "DISPATCHED")
            self.assertIn("dispatch_admission", observed)
            self.assertIsNone(observed["receipt"])
            kinds = [e["kind"] for e in self.r.store.journal() if e.get("effect") == effect]
            self.assertIn("effect-dispatched", kinds)
            self.assertNotIn("effect-dispatched", kinds[-1:])


class B03ValidationAccounting(Case):
    def stage_loop(self):
        return self.r.transactor.stage({"total": self.r.registry.register("sum_loop")})

    def test_validation_spends_a_durable_grant(self):
        vb = self.r.resources.create_budget("alice", {"attempts": 3})
        self.r.transactor.validate(self.stage_loop(), {"total": [([1, 2], 3), ([], 0)]}, budget=vb, principal="alice")
        self.assertEqual(self.spent(vb), 2)
        self.assertEqual(self.available(vb), 1)

    def test_repeated_validation_exhausts_shared_budget(self):
        vb = self.r.resources.create_budget("alice", {"attempts": 2})
        for _ in range(2):
            self.r.transactor.validate(self.stage_loop(), {"total": [([1, 2], 3)]}, budget=vb, principal="alice")
        with self.assertRaises(Refused):
            self.r.transactor.validate(self.stage_loop(), {"total": [([1, 2], 3)]}, budget=vb, principal="alice")
        self.assertEqual(self.spent(vb), 2)

    def test_failed_validation_charges_work_done_and_refunds_rest(self):
        vb = self.r.resources.create_budget("alice", {"attempts": 5})
        with self.assertRaises(Refused):
            self.r.transactor.validate(self.stage_loop(), {"total": [([1], 999), ([2], 2), ([3], 3)]},
                                       budget=vb, principal="alice")
        self.assertEqual(self.spent(vb), 1)
        self.assertEqual(self.available(vb), 4)

    def test_kernel_validation_budget_is_durable_across_restart(self):
        key = self.r.store.get("system", "validation-budget")["id"]
        before = self.spent(key, "_kernel_validation")
        self.assertGreater(before, 0)
        self.r.close()
        self.r = Runtime(self.root / "core.sqlite3", clock=lambda: self.now[0])
        self.assertEqual(self.r.store.get("system", "validation-budget")["id"], key)
        self.assertEqual(self.spent(key, "_kernel_validation"), before)


class B04ArtifactIdentity(unittest.TestCase):
    def test_unrelated_change_preserves_other_identities(self):
        before = {name: providers.specification(name)["id"] for name in providers.PRIMITIVES}
        def count_v2(value):
            return sum(1 for _ in value)
        changed = providers.Primitive(count_v2, "integers", "integer", "count-integers", version="2")
        with patch.dict(providers.PRIMITIVES, {"count": changed}):
            after = {name: providers.specification(name)["id"] for name in providers.PRIMITIVES}
        self.assertNotEqual(before["count"], after["count"])
        for name in set(before) - {"count"}:
            self.assertEqual(before[name], after[name], name)

    def test_code_change_without_version_bump_still_changes_identity(self):
        def count_other(value):
            return len(list(value))
        before = providers.specification("count")
        with patch.dict(providers.PRIMITIVES, {"count": providers.Primitive(
                count_other, "integers", "integer", "count-integers")}):
            after = providers.specification("count")
        self.assertEqual(before["version"], after["version"])
        self.assertNotEqual(before["artifact"], after["artifact"])

    def test_identity_declares_shared_dependencies(self):
        spec = providers.specification("sum")
        self.assertEqual(set(spec["dependencies"]), {"schema-check/v1", "int-list/v1"})
        self.assertTrue(spec["id"].startswith("sum@1:"))


class B05EndpointIdentity(Case):
    def test_same_name_endpoints_have_distinct_stable_identities(self):
        with LocalReceiptSink(self.root / "a.db") as a, LocalReceiptSink(self.root / "b.db") as b:
            self.assertEqual(a.name, b.name)
            self.assertNotEqual(a.identity, b.identity)
            identity = a.identity
        with LocalReceiptSink(self.root / "a.db") as again:
            self.assertEqual(again.identity, identity)

    def test_dispatch_and_reconcile_refuse_same_name_impostor(self):
        task = self.completed()
        with LocalReceiptSink(self.root / "a.db") as a, LocalReceiptSink(self.root / "b.db") as b:
            effect, token = self.r.effects.prepare_effect(task, "alice", a.identity, {"x": 1}, self.budget,
                                                          [self.scoped(task, a, {"x": 1})])
            with self.assertRaisesRegex(Refused, "endpoint"):
                self.r.effects.dispatch_effect(effect, token, "alice", b)
            with self.assertRaisesRegex(Refused, "endpoint"):
                self.r.effects.reconcile_effect(effect, "alice", b)
            self.assertEqual(b.applied_events(), [])

    def test_display_name_is_not_an_identity(self):
        task = self.completed()
        with LocalReceiptSink(self.root / "a.db") as a:
            with self.assertRaisesRegex(Refused, "endpoint identity"):
                self.r.effects.prepare_effect(task, "alice", a.name, {"x": 1}, self.budget,
                                              [self.scoped(task, a, {"x": 1})])


class B06EvidenceScope(Case):
    def test_unscoped_or_mismatched_certified_evidence_is_refused(self):
        task, other = self.completed(), self.completed()
        with LocalReceiptSink(self.root / "a.db") as a, LocalReceiptSink(self.root / "b.db") as b:
            payload = {"x": 1}
            wrong = {
                "unscoped": self.r.evidence.record_evidence("checker", {}, "Certified"),
                "other-task": self.scoped(other, a, payload),
                "other-endpoint": self.scoped(task, b, payload),
                "other-claim": self.scoped(task, a, {"x": 2}),
            }
            for label, ref in wrong.items():
                with self.subTest(label=label), self.assertRaisesRegex(Refused, "does not support"):
                    self.r.effects.prepare_effect(task, "alice", a.identity, payload, self.budget, [ref])
            self.r.effects.prepare_effect(task, "alice", a.identity, payload, self.budget,
                                          [self.scoped(task, a, payload)])

    def test_scope_is_rechecked_at_dispatch(self):
        task = self.completed()
        with LocalReceiptSink(self.root / "a.db") as a:
            ref = self.scoped(task, a, {"x": 1})
            effect, token = self.r.effects.prepare_effect(task, "alice", a.identity, {"x": 1}, self.budget, [ref])
            with self.r.store.transaction():
                record = self.r.store.get("evidence", ref)
                record["support"] = dict(record["support"], context="elsewhere")
                self.r.store.put("evidence", ref, record)
            with self.assertRaisesRegex(Refused, "does not support"):
                self.r.effects.dispatch_effect(effect, token, "alice", a)
            self.assertEqual(a.applied_events(), [])


class FabricCase(Case):
    def setUp(self):
        super().setUp()
        install(self.r, PARENTS, PARENT_CASES)
        self.dev = self.r.resources.create_budget("dev", {"attempts": 300})
        self.val = self.r.resources.create_budget("dev", {"attempts": 60})

    def acquire(self, demand=SUM_DEMAND, **kw):
        return CompositionSearch(self.r).acquire(demand, "dev", self.dev, ADMISSION, validation_budget=self.val, **kw)

    def ids(self, *names):
        bindings = self.r.manifest()["bindings"]
        return [bindings[n] for n in names]

    def graph(self, *nodes):
        return dict(input="text", output="integer", output_node=nodes[-1]["id"], nodes=list(nodes))

    def run_role(self, role, value):
        task = self.r.tasks.create_task("dev", role, value, self.dev)
        return task, self.r.tasks.run_task(task, self.r.tasks.authorize(task, "dev"), "dev")


class TypedFabric(FabricCase):
    def test_type_mismatched_connection_is_refused(self):
        parse, negate = self.ids("parse", "negate")
        with self.assertRaisesRegex(Refused, "schema"):
            self.r.registry.register_graph(self.graph(dict(id="n0", provider=parse, input="$input"),
                                                      dict(id="n1", provider=negate, input="n0")), "bad")

    def test_forward_cyclic_and_duplicate_references_are_refused(self):
        parse, total = self.ids("parse", "total")
        for nodes in ((dict(id="n0", provider=parse, input="n1"), dict(id="n1", provider=total, input="n0")),
                      (dict(id="n0", provider=parse, input="$input"), dict(id="n0", provider=total, input="n0"))):
            with self.subTest(nodes=nodes), self.assertRaises(Refused):
                self.r.registry.register_graph(self.graph(*nodes), "bad")

    def test_unsupported_adapter_is_refused(self):
        parse, total = self.ids("parse", "total")
        with self.assertRaisesRegex(Refused, "adapter"):
            self.r.registry.register_graph(self.graph(dict(id="n0", provider=parse, input="$input"),
                dict(id="n1", provider=total, input="n0", adapter="coerce")), "bad")

    def test_graph_parents_must_be_active(self):
        parse, = self.ids("parse")
        with self.assertRaises(Refused):
            self.r.fabric.stage(self.graph(dict(id="n0", provider=parse, input="$input"),
                                           dict(id="n1", provider="sum@9:forged", input="n0")), "csv-sum")
        self.assertNotIn("csv-sum", self.r.manifest()["bindings"])

    def test_composite_cost_is_fully_accounted_and_results_have_provenance(self):
        self.acquire()
        before = self.spent(self.dev, "dev")
        task, value = self.run_role("csv-sum", "1,2,3,4")
        self.assertEqual(value, 10)
        self.assertEqual(self.spent(self.dev, "dev") - before, 2)
        rows = self.r.fabric.results(task, "dev")
        self.assertEqual([(row["node"], row["value"]) for row in rows], [("n0", [1, 2, 3, 4]), ("n1", 10)])
        self.assertTrue(all(row["principal"] == "dev" and row["dependencies"] for row in rows))
        with self.assertRaises(Refused):
            self.r.fabric.results(task, "mallory")

    def test_cancellation_stops_at_node_boundary_and_refunds_unspent(self):
        self.acquire()
        task = self.r.tasks.create_task("dev", "csv-sum", "1,2", self.dev)
        token = self.r.tasks.authorize(task, "dev")
        before = self.spent(self.dev, "dev")
        real = subprocess.run
        def first_node_then_cancel(*args, **kwargs):
            result = real(*args, **kwargs)
            self.assertEqual(self.r.tasks.cancel_task(task, "dev"), "STOP_REQUESTED")
            return result
        with patch("brainos.runner.subprocess.run", side_effect=first_node_then_cancel):
            with self.assertRaises(Cancelled):
                self.r.tasks.run_task(task, token, "dev")
        record = self.r.tasks.task(task, "dev")
        self.assertEqual(record["state"], "CANCELLED")
        self.assertEqual(self.spent(self.dev, "dev") - before, 1)
        self.assertEqual(self.r.store.get("holding", record["holding"])["state"], "RELEASED")
        with self.assertRaises(Refused):
            self.r.authority.check_permit(token, "dev", "task", task)

    def test_scoped_impact_blocks_dependent_composites(self):
        acquired = self.acquire()
        parse, count = self.ids("parse", "count")
        impact = self.r.fabric.impact(parse)
        self.assertIn(acquired["provider"], impact["affected"])
        self.assertNotIn(count, impact["affected"])
        self.r.registry.exclude(parse, "counterexample in parser")
        with self.assertRaisesRegex(Refused, "excluded"):
            self.r.registry.resolve(acquired["provider"])


class DevelopmentalCompilation(FabricCase):
    def test_no_single_primitive_satisfies_the_demand(self):
        for spec in map(self.r.registry.resolve, self.r.manifest()["bindings"].values()):
            if spec["input"] == "text" and spec["output"] == "integer":
                self.assertNotEqual(spec["implementation"], "typed-dag")
                with self.subTest(spec=spec["implementation"]):
                    self.assertNotEqual(providers.compute(spec["implementation"], "1,2,3"), 6)

    def test_discovers_validates_and_publishes_composition(self):
        result = self.acquire()
        self.assertEqual(result["status"], "ACQUIRED")
        names = [ref.split("@")[0] for ref in result["path"]]
        self.assertEqual(names[0], "parse_csv")
        self.assertIn(names[1], ("sum", "sum_loop"))
        self.assertEqual(self.r.manifest()["bindings"]["csv-sum"], result["provider"])

    def test_parents_preserved_and_failures_retained(self):
        parents = {role: self.r.manifest()["bindings"][role] for role in PARENTS}
        self.acquire()
        self.assertEqual({role: self.r.manifest()["bindings"][role] for role in PARENTS}, parents)
        statuses = [row["status"] for row in self.r.store.find("construction")]
        self.assertIn("REJECTED_DEVELOPMENT", statuses)
        self.assertIn("ACQUIRED", statuses)

    def test_admission_cases_are_independent_of_development_examples(self):
        result = CompositionSearch(self.r).acquire(SUM_DEMAND, "dev", self.dev, [("4,5", 999)],
                                                   validation_budget=self.val)
        self.assertEqual(result["status"], "NON_ATTAINMENT")
        self.assertNotIn("csv-sum", self.r.manifest()["bindings"])
        self.assertIn("REJECTED_ADMISSION", [row["status"] for row in self.r.store.find("construction")])

    def test_unsatisfiable_demand_reports_non_attainment(self):
        demand = CapabilityDemand("csv-product", "text", "integer", (("2,3", 6),))
        self.assertEqual(self.acquire(demand)["status"], "NON_ATTAINMENT")
        self.assertNotIn("csv-product", self.r.manifest()["bindings"])

    def test_search_budget_exhaustion_is_recorded(self):
        tiny = self.r.resources.create_budget("dev", {"attempts": 2})
        result = CompositionSearch(self.r).acquire(SUM_DEMAND, "dev", tiny, ADMISSION, validation_budget=self.val)
        self.assertEqual(result["status"], "NON_ATTAINMENT")
        self.assertIn("NON_ATTAINMENT", [row["status"] for row in self.r.store.find("construction")])
        self.assertEqual(self.available(tiny, "dev"), 0)

    def test_invalid_demand_or_policy_is_refused(self):
        for demand, mode in ((CapabilityDemand("x", "text", "integer", ()), "typed"),
                             (CapabilityDemand("x", "text", "integer", (("1", 1),), max_depth=9), "typed"),
                             (SUM_DEMAND, "neural")):
            with self.subTest(mode=mode), self.assertRaises(Refused):
                list(CompositionSearch(self.r).discover(demand, "dev", self.dev, mode=mode))

    def test_memoized_baseline_spends_less_for_the_same_nominations(self):
        costs = {}
        for mode in ("typed", "memoized"):
            budget = self.r.resources.create_budget("dev", {"attempts": 300})
            paths = list(CompositionSearch(self.r).discover(SUM_DEMAND, "dev", budget, mode=mode))
            costs[mode] = (self.spent(budget, "dev"), paths)
        self.assertEqual(costs["typed"][1], costs["memoized"][1])
        self.assertLess(costs["memoized"][0], costs["typed"][0])

    def test_competing_composition_can_be_acquired_separately(self):
        first = self.acquire()
        demand = CapabilityDemand("csv-sum-alt", "text", "integer", SUM_DEMAND.development_examples)
        second = self.acquire(demand, exclude_paths=(tuple(first["path"]),))
        self.assertEqual(second["status"], "ACQUIRED")
        self.assertNotEqual(first["path"], second["path"])
        for role in ("csv-sum", "csv-sum-alt"):
            self.assertEqual(self.run_role(role, "5,6")[1], 11)


if __name__ == "__main__":
    unittest.main()
