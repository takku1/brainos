"""Crash recovery is tested across real process death, not mocked close()."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from brainos import Refused, Runtime, Unresolved
from brainos.effects import LocalReceiptSink


class CrashRecoveryTests(unittest.TestCase):
    def crash(self, root, point):
        result = subprocess.run([sys.executable, "tests/crash_driver.py", str(root), point],
                                capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 73, result.stdout + result.stderr)
        return json.loads((root / "witness.json").read_text(encoding="utf-8"))

    def test_atomic_manifest_publication_before_and_after_commit(self):
        for point in ("before_manifest_commit", "after_manifest_commit"):
            with self.subTest(point=point), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                witness = self.crash(root, point)
                with Runtime(root / "core.sqlite3") as runtime:
                    state = runtime.manifest()
                    committed = point == "after_manifest_commit"
                    self.assertEqual(state["revision"], witness["old_revision"] + int(committed))
                    self.assertEqual(state["bindings"]["total"], witness["new_provider"] if committed else witness["old_provider"])
                    self.assertEqual(state["phase"], "PUBLISHED")
                    runtime.store.verify()
                    with self.assertRaises(Refused):
                        runtime.transactor.commit(witness["candidate"])

    def test_crashed_invocation_has_terminal_state_and_spend(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            witness = self.crash(root, "after_invocation_start")
            with Runtime(root / "core.sqlite3") as runtime:
                self.assertEqual(runtime.tasks.task(witness["task"], "demo")["state"], "FAILED")
                self.assertEqual(runtime.resources.budget(witness["budget"], "demo")["spent"]["attempts"], 1)
                with self.assertRaises(Refused):
                    runtime.tasks.run_task(witness["task"], witness["token"], "demo")

    def test_effect_crash_does_not_assume_failure_or_duplicate_application(self):
        for point in ("before_effect_apply", "after_effect_applied"):
            with self.subTest(point=point), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                witness = self.crash(root, point)
                with Runtime(root / "core.sqlite3") as runtime, LocalReceiptSink(root / "sink.sqlite3") as sink:
                    self.assertEqual(runtime.store.get("effect", witness["effect"])["state"], "UNKNOWN")
                    if point == "before_effect_apply":
                        with self.assertRaises(Unresolved):
                            runtime.effects.reconcile_effect(witness["effect"], "demo", sink)
                        self.assertEqual(sink.store.journal(), [])
                    else:
                        receipt = runtime.effects.reconcile_effect(witness["effect"], "demo", sink)
                        self.assertEqual(receipt["payload"], {"total": 3})
                        self.assertEqual(len(sink.store.journal()), 1)
                        self.assertEqual(runtime.resources.budget(witness["budget"], "demo")["spent"]["attempts"], 2)
                        self.assertEqual(runtime.effects.reconcile_effect(witness["effect"], "demo", sink), receipt)
