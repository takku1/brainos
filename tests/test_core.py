"""Actual boundary tests for the first durable Core profile."""
import ast
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import random
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

from brainos import Refused, Runtime, Unresolved
from brainos.__main__ import demo, install
from brainos.effects import LocalReceiptSink
from brainos.contracts import PermitScope


class RuntimeCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.now = [100.0]
        self.r = Runtime(self.root / "core.sqlite3", clock=lambda: self.now[0])
        install(self.r, {"total": "sum"}, {"total": [([1, 2], 3), ([], 0)]})
        self.budget = self.r.resources.create_budget("alice", {"attempts": 20})

    def tearDown(self):
        self.r.close()
        self.temp.cleanup()

    def ready(self, value=None, evidence=(), ttl=60):
        task = self.r.tasks.create_task("alice", "total", [1, 2] if value is None else value, self.budget)
        permit = self.r.tasks.authorize(task, "alice", evidence, ttl)
        return task, permit

    def completed(self):
        task, permit = self.ready()
        self.assertEqual(self.r.tasks.run_task(task, permit, "alice"), 3)
        return task

    def support(self, tier="Certified", ttl=3600):
        return self.r.evidence.record_evidence("test-checker", {"pass": True}, tier, ttl)

    def test_task_runs_only_after_admission_and_preserves_result(self):
        task = self.r.tasks.create_task("alice", "total", [4, 5], self.budget)
        with self.assertRaises(Refused):
            self.r.tasks.run_task(task, "invented", "alice")
        permit = self.r.tasks.authorize(task, "alice")
        self.assertEqual(self.r.tasks.run_task(task, permit, "alice"), 9)
        self.assertEqual(self.r.tasks.task(task, "alice")["state"], "SUCCEEDED")
        with self.assertRaises(Refused):
            self.r.tasks.run_task(task, permit, "alice")

    def test_budget_ownership_reserve_convert_and_release(self):
        grant = self.r.resources.reserve(self.budget, "alice", {"attempts": 4})
        self.r.resources.allocate(grant, "alice")
        self.assertEqual(self.r.resources.budget(self.budget, "alice")["available"], {"attempts": 16})
        with self.assertRaises(Refused):
            self.r.resources.allocate(grant, "alice")
        with self.assertRaises(Refused):
            self.r.resources.release(grant, "bob")
        self.assertEqual(self.r.resources.release(grant, "alice"), "RELEASED")
        self.assertEqual(self.r.resources.release(grant, "alice"), "ALREADY_RELEASED")
        self.assertEqual(self.r.resources.budget(self.budget, "alice")["available"], {"attempts": 20})

    def test_budget_rejects_invalid_vectors_and_overdraft(self):
        for vector in ({"attempts": -1}, {"attempts": True}, {"attempts": 1.5}, {"gpu": 1}, {"attempts": 21}):
            with self.subTest(vector=vector), self.assertRaises(Refused):
                self.r.resources.reserve(self.budget, "alice", vector)
        self.assertEqual(self.r.resources.budget(self.budget, "alice")["available"]["attempts"], 20)

    def test_atomic_concurrent_reservations(self):
        budget = self.r.resources.create_budget("alice", {"attempts": 1})
        def reserve(_):
            try:
                return self.r.resources.reserve(budget, "alice", {"attempts": 1})
            except Refused:
                return None
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(reserve, range(2)))
        self.assertEqual(sum(result is not None for result in results), 1)

    def test_budget_conservation_across_mixed_reserve_spend_release(self):
        rng = random.Random(17)
        expected_available, expected_spent = 20, 0
        for _ in range(60):
            amount = rng.randint(0, 5)
            if amount > expected_available:
                with self.assertRaises(Refused):
                    self.r.resources.reserve(self.budget, "alice", {"attempts": amount})
            else:
                grant = self.r.resources.reserve(self.budget, "alice", {"attempts": amount})
                self.r.resources.allocate(grant, "alice")
                if rng.choice((True, False)):
                    with self.r.store.transaction():
                        self.r.resources.charge_tx(grant)
                    expected_spent += amount
                    expected_available -= amount
                else:
                    self.r.resources.release(grant, "alice")
            budget = self.r.resources.budget(self.budget, "alice")
            self.assertEqual(budget["available"]["attempts"], expected_available)
            self.assertEqual(budget["spent"]["attempts"], expected_spent)
            self.assertEqual(expected_available + expected_spent, 20)

    def test_bad_inputs_are_rejected_before_spending(self):
        for value in ([True], "1,2", [2**100], list(range(4097))):
            with self.subTest(value=type(value)), self.assertRaises(Refused):
                self.r.tasks.create_task("alice", "total", value, self.budget)
        self.assertEqual(self.r.resources.budget(self.budget, "alice")["available"]["attempts"], 20)
        with self.assertRaises(Refused):
            self.r.tasks.create_task("alice", "total", [1], self.budget, amount={})

    def test_scope_forgery_wrong_principal_and_wrong_task(self):
        task, permit = self.ready()
        other, _ = self.ready()
        for key, token, principal in ((task, {}, "alice"), (task, "forged", "alice"),
                                      (task, permit, "bob"), (other, permit, "alice")):
            with self.subTest(token=type(token)), self.assertRaises(Refused):
                self.r.tasks.run_task(key, token, principal)

    def test_revocation_same_epoch_and_expiration(self):
        task, permit = self.ready()
        self.r.authority.revoke(permit)
        with self.assertRaisesRegex(Refused, "revoked"):
            self.r.tasks.run_task(task, permit, "alice")
        task, permit = self.ready(ttl=1)
        self.now[0] += 2
        with self.assertRaisesRegex(Refused, "expired"):
            self.r.tasks.run_task(task, permit, "alice")

    def test_authorized_task_content_cannot_change(self):
        task, permit = self.ready()
        with self.r.store.transaction():
            record = self.r.store.get("task", task)
            record["value"] = [999]
            self.r.store.put("task", task, record)
        with self.assertRaisesRegex(Refused, "changed"):
            self.r.tasks.run_task(task, permit, "alice")

    def test_allocated_task_cannot_be_refunded_before_execution(self):
        task, _ = self.ready()
        with self.assertRaises(Refused):
            self.r.resources.release(self.r.tasks.task(task, "alice")["holding"], "alice")
        self.r.tasks.cancel_task(task, "alice")
        self.assertEqual(self.r.resources.budget(self.budget, "alice")["available"]["attempts"], 20)

    def test_failed_worker_and_timeout_have_owned_terminal_state(self):
        task, permit = self.ready()
        with patch("brainos.runner.subprocess.run", side_effect=subprocess.TimeoutExpired("worker", 1)):
            with self.assertRaisesRegex(Refused, "wall-clock"):
                self.r.tasks.run_task(task, permit, "alice")
        self.assertEqual(self.r.tasks.task(task, "alice")["state"], "FAILED")

    def test_malformed_provider_content_fails_with_recorded_cost(self):
        install(self.r, {"parse": "parse_csv"}, {"parse": [("2,3", [2, 3])]})
        task = self.r.tasks.create_task("alice", "parse", "not-an-integer", self.budget)
        token = self.r.tasks.authorize(task, "alice")
        with self.assertRaises(Refused):
            self.r.tasks.run_task(task, token, "alice")
        self.assertEqual(self.r.tasks.task(task, "alice")["state"], "FAILED")
        self.assertEqual(self.r.resources.budget(self.budget, "alice")["spent"]["attempts"], 1)

    def test_real_subprocess_deadline(self):
        task = self.r.tasks.create_task("alice", "total", [1, 2], self.budget, timeout=0.0001)
        token = self.r.tasks.authorize(task, "alice")
        with self.assertRaisesRegex(Refused, "wall-clock"):
            self.r.tasks.run_task(task, token, "alice")
        self.assertEqual(self.r.tasks.task(task, "alice")["state"], "FAILED")

    def test_authority_receives_control_projection_not_signal_payload(self):
        captured = []
        issue = self.r.authority.issue_tx
        def trace(scope, refs, ttl):
            captured.append(scope)
            return issue(scope, refs, ttl)
        with patch.object(self.r.authority, "issue_tx", side_effect=trace):
            task, token = self.ready([123, 456])
        self.assertIsInstance(captured[0], PermitScope)
        self.assertNotIn("value", captured[0].__dataclass_fields__)
        self.assertEqual(self.r.tasks.run_task(task, token, "alice"), 579)

    def test_challenge_timing_and_verdict_only_restore(self):
        support = self.support()
        task, token = self.ready(evidence=[support])
        self.r.evidence.challenge(support, "counterexample")
        # Pure work's pre-cut permit may run; effect boundary cannot.
        self.assertEqual(self.r.tasks.run_task(task, token, "alice"), 3)
        self.r.authority.cut_epoch()
        with self.assertRaises(Refused):
            self.ready(evidence=[support])
        proof = self.r.evidence.verify(support, "PASS", "independent-check-v1")
        self.assertEqual(self.r.store.get("evidence", support)["state"], "CHALLENGED")
        self.assertIsNone(self.r.evidence.restore(support, proof))
        self.r.evidence.challenge(support, "new counterexample")
        with self.assertRaises(Refused):
            self.r.evidence.restore(support, proof)

    def test_stale_or_negative_proof_does_not_restore(self):
        support = self.support()
        self.r.evidence.challenge(support, "cause")
        proof = self.r.evidence.verify(support, "FAIL", "checker")
        with self.assertRaises(Refused):
            self.r.evidence.restore(support, proof)
        proof = self.r.evidence.verify(support, "PASS", "checker")
        self.support()
        with self.assertRaises(Refused):
            self.r.evidence.restore(support, proof)

    def test_failed_or_unvalidated_candidates_do_not_publish(self):
        original = self.r.manifest()
        candidate = self.r.transactor.stage({"total": self.r.registry.register("sum_loop")})
        with self.assertRaises(Refused):
            self.r.transactor.commit(candidate)
        with self.assertRaises(Refused):
            self.r.transactor.validate(candidate, {"total": [([1, 2], 100)]})
        self.assertEqual(self.r.manifest(), original)

    def test_validation_has_finite_case_grant_and_records_failed_work(self):
        candidate = self.r.transactor.stage({"total": self.r.registry.register("sum_loop")})
        with self.assertRaisesRegex(Refused, "64-case"):
            self.r.transactor.validate(candidate, {"total": [([1], 1)] * 65})
        with self.assertRaises(Refused):
            self.r.transactor.validate(candidate, {"total": [([1], 999)]})
        failed = [e for e in self.r.store.journal() if e["kind"] == "validation-failed"]
        self.assertEqual(failed[-1]["attempts"], 1)
        self.assertGreater(failed[-1]["elapsed_seconds"], 0)

    def test_stale_validation_and_incompatible_replacement(self):
        candidate = self.r.transactor.stage({"total": self.r.registry.register("sum_loop")})
        self.r.transactor.validate(candidate, {"total": [([1, 2], 3)]})
        self.support()
        with self.assertRaisesRegex(Refused, "stale"):
            self.r.transactor.commit(candidate)
        with self.assertRaises(Refused):
            self.r.transactor.stage({"total": self.r.registry.register("count")})

    def test_competing_manifests_use_compare_and_swap(self):
        binding = {"total": self.r.registry.register("sum_loop")}
        a, b = self.r.transactor.stage(binding), self.r.transactor.stage(binding)
        for candidate in (a, b):
            self.r.transactor.validate(candidate, {"total": [([1, 2], 3)]})
        self.r.transactor.commit(a)
        with self.assertRaisesRegex(Refused, "stale"):
            self.r.transactor.commit(b)

    def test_slow_validation_does_not_block_epoch_control(self):
        candidate = self.r.transactor.stage({"total": self.r.registry.register("sum_loop")})
        entered, release = threading.Event(), threading.Event()
        delegate = self.r.transactor.runner
        class SlowRunner:
            def compute(inner, spec, value, timeout):
                entered.set()
                if not release.wait(5):
                    raise RuntimeError("test runner was not released")
                return delegate.compute(spec, value, timeout)
        self.r.transactor.runner = SlowRunner()
        with ThreadPoolExecutor(max_workers=2) as pool:
            validation = pool.submit(self.r.transactor.validate, candidate, {"total": [([1, 2], 3)]})
            self.assertTrue(entered.wait(5))
            control = pool.submit(self.r.authority.cut_epoch)
            try:
                control.result(timeout=1)
            finally:
                release.set()
            with self.assertRaises(Refused):
                validation.result(timeout=5)

    def test_live_permit_is_stale_after_replacement(self):
        task, permit = self.ready()
        install(self.r, {"total": "sum_loop"}, {"total": [([1, 2], 3)]})
        with self.assertRaisesRegex(Refused, "stale"):
            self.r.tasks.run_task(task, permit, "alice")

    def test_registry_does_not_trust_self_reported_artifact(self):
        provider = self.r.manifest()["bindings"]["total"]
        with self.r.store.transaction():
            record = self.r.store.get("provider", provider)
            record["artifact"] = "forged"
            self.r.store.put("provider", provider, record)
        with self.assertRaisesRegex(Refused, "artifact"):
            self.ready()

    def test_only_one_authority_owns_database(self):
        with self.assertRaisesRegex(Refused, "owner"):
            Runtime(self.root / "core.sqlite3")

    def test_reopen_preserves_result_budget_and_revokes_permits(self):
        task, token = self.ready()
        self.r.tasks.run_task(task, token, "alice")
        epoch = self.r.manifest()["epoch"]
        self.r.close()
        self.r = Runtime(self.root / "core.sqlite3", clock=lambda: self.now[0])
        self.assertGreater(self.r.manifest()["epoch"], epoch)
        self.assertEqual(self.r.tasks.task(task, "alice")["result"], 3)
        self.assertEqual(self.r.resources.budget(self.budget, "alice")["spent"]["attempts"], 1)
        with self.assertRaises(Refused):
            self.r.authority.check_permit(token, "alice", "task", task)

    def test_effect_requires_certified_current_support_and_exact_endpoint(self):
        task = self.completed()
        with LocalReceiptSink(self.root / "sink.sqlite3") as sink:
            for refs in ([], [self.support("Believed")]):
                with self.assertRaises(Refused):
                    self.r.effects.prepare_effect(task, "alice", sink.name, {"x": 3}, self.budget, refs)
            support = self.support()
            effect, token = self.r.effects.prepare_effect(task, "alice", sink.name, {"x": 3}, self.budget, [support])
            self.r.evidence.challenge(support, "pending challenge")
            with self.assertRaisesRegex(Refused, "challenged"):
                self.r.effects.dispatch_effect(effect, token, "alice", sink)
            self.assertEqual(sink.store.journal(), [])

    def test_effect_revocation_and_expired_support_block_at_boundary(self):
        task = self.completed()
        support = self.support(ttl=1)
        with LocalReceiptSink(self.root / "sink.sqlite3") as sink:
            effect, token = self.r.effects.prepare_effect(task, "alice", sink.name, {}, self.budget, [support])
            self.now[0] += 2
            with self.assertRaisesRegex(Refused, "expired"):
                self.r.effects.dispatch_effect(effect, token, "alice", sink)
            self.assertEqual(sink.store.journal(), [])

    def test_idempotency_keys_and_lost_ack_reconciliation(self):
        task = self.completed()
        support = self.support()
        with LocalReceiptSink(self.root / "sink.sqlite3") as sink:
            effect, token = self.r.effects.prepare_effect(task, "alice", sink.name, {"x": 3}, self.budget, [support])
            self.r.effects.failpoint = lambda point: (_ for _ in ()).throw(OSError("lost ack")) if point == "after_effect_applied" else None
            with self.assertRaises(Unresolved):
                self.r.effects.dispatch_effect(effect, token, "alice", sink)
            with self.assertRaises(Unresolved):
                self.r.effects.dispatch_effect(effect, token, "alice", sink)
            receipt = self.r.effects.reconcile_effect(effect, "alice", sink)
            self.assertEqual(sink.apply(effect, {"x": 3}), receipt)
            with self.assertRaises(Refused):
                sink.apply(effect, {"x": 4})
            self.assertEqual(len(sink.store.journal()), 1)
            self.assertEqual(self.r.resources.budget(self.budget, "alice")["spent"]["attempts"], 2)

    def test_missing_receipt_never_becomes_assumed_failure_or_blind_retry(self):
        task = self.completed()
        with LocalReceiptSink(self.root / "sink.sqlite3") as sink:
            effect, _ = self.r.effects.prepare_effect(task, "alice", sink.name, {}, self.budget, [self.support()])
            with self.r.store.transaction():
                record = self.r.store.get("effect", effect)
                record["state"] = "UNKNOWN"
                self.r.store.put("effect", effect, record)
            with self.assertRaises(Unresolved):
                self.r.effects.reconcile_effect(effect, "alice", sink)
            with self.assertRaises(Refused):
                self.r.resources.release(record["holding"], "alice")

    def test_journal_corruption_fails_closed_on_restart(self):
        self.r.close()
        db = sqlite3.connect(self.root / "core.sqlite3")
        try:
            db.execute("UPDATE events SET body='{}' WHERE seq=1")
            db.commit()
        finally:
            db.close()
        with self.assertRaisesRegex(Refused, "journal integrity"):
            Runtime(self.root / "core.sqlite3")


class EndToEndTests(unittest.TestCase):
    def test_real_demo(self):
        with tempfile.TemporaryDirectory() as root:
            result = demo(root)
        self.assertEqual(result["total"], 60)
        self.assertEqual(result["replacement_result"], 60)
        self.assertTrue(result["old_authority_rejected"])
        self.assertTrue(result["epoch_advanced"])
        self.assertEqual(result["effect_applications"], 1)
        self.assertEqual(result["budget"]["spent"]["attempts"], 4)

    def test_kernel_imports_no_model_frameworks(self):
        allowed = set(sys.stdlib_module_names) | {"brainos", "__future__"}
        for path in Path("src/brainos").glob("*.py"):
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        self.assertIn(alias.name.split(".")[0], allowed, str(path))
                if isinstance(node, ast.ImportFrom) and node.level == 0:
                    self.assertIn(node.module.split(".")[0], allowed, str(path))

    def test_authority_layer_does_not_import_signal_execution(self):
        forbidden = {"providers", "runner", "execution", "gateways", "effects", "__main__"}
        tree = ast.parse(Path("src/brainos/authority.py").read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                self.assertNotIn(node.module, forbidden)
        self.assertEqual(set(PermitScope.__dataclass_fields__),
                         {"kind", "target", "principal", "content_digest", "provider", "context", "operation"})


if __name__ == "__main__":
    unittest.main()
