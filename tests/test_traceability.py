"""Drift control (Doc 31 section 31.12): the repository has no drift, and each
drift class is detected when introduced into a temporary copy."""
from pathlib import Path
import contextlib
import io
import json
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import check_traceability as ct  # noqa: E402


def run_checker(**paths):
    out = io.StringIO()
    with contextlib.ExitStack() as stack:
        for name, value in paths.items():
            stack.enter_context(patch.object(ct, name, value))
        stack.enter_context(patch.object(sys, "argv", ["check_traceability.py"]))
        with contextlib.redirect_stdout(out):
            code = ct.main()
    return code, out.getvalue()


class DriftControl(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.docs = Path(self.temp.name) / "docs"
        shutil.copytree(ct.DOCS, self.docs)
        self.paths = dict(DOCS=self.docs, MAP=self.docs / "traceability.json",
                          REGISTER=self.docs / "31-architectural-audit.md",
                          README=self.docs / "README.md", DOC21=self.docs / "21-reference-implementation.md")

    def tearDown(self):
        self.temp.cleanup()

    def mutate_map(self, fn):
        data = json.loads(self.paths["MAP"].read_text(encoding="utf-8"))
        fn(data["requirements"])
        self.paths["MAP"].write_text(json.dumps(data), encoding="utf-8")

    def test_repository_has_no_drift(self):
        code, out = run_checker()
        self.assertEqual(code, 0, out)
        self.assertIn("0 drift errors", out)

    def test_missing_code_symbol_is_drift(self):
        self.mutate_map(lambda r: r["R-09-COMMIT"]["code"].append("src/brainos/transactor.py::Transactor.publish_everything"))
        code, out = run_checker(**self.paths)
        self.assertEqual(code, 1)
        self.assertIn("defines no 'Transactor.publish_everything'", out)

    def test_missing_test_is_drift(self):
        self.mutate_map(lambda r: r["R-09-COMMIT"]["tests"].append("tests/test_core.py::NoSuchTests"))
        code, out = run_checker(**self.paths)
        self.assertIn("defines no 'NoSuchTests'", out)

    def test_status_change_without_register_update_is_drift(self):
        self.mutate_map(lambda r: r.__setitem__("R-09-COMMIT", {"status": "specified"}))
        code, out = run_checker(**self.paths)
        self.assertEqual(code, 1)
        self.assertIn("R-09-COMMIT: register says I✓ V✓, map says I✗ V✗", out)

    def test_unclaimed_module_and_test_class_are_drift(self):
        def drop(r):
            for entry in r.values():
                entry["code"] = [c for c in entry.get("code", []) if not c.startswith("src/brainos/closure.py")]
                entry["tests"] = [t for t in entry.get("tests", []) if "ClosureConformance" not in t]
                if entry.get("status") in ("implemented", "partial") and not entry["code"]:
                    entry["code"] = ["src/brainos/runtime.py::Runtime"]
                if entry.get("status") == "implemented" and not entry["tests"]:
                    entry["tests"] = ["tests/test_core.py::EndToEndTests"]
        self.mutate_map(drop)
        code, out = run_checker(**self.paths)
        self.assertIn("orphan module: src/brainos/closure.py", out)
        self.assertIn("orphan test class: tests/test_cumulative.py::ClosureConformance", out)

    def test_document_status_inconsistent_with_its_rows_is_drift(self):
        doc = self.docs / "28-credit-assignment.md"
        doc.write_text(doc.read_text(encoding="utf-8").replace("Status: research", "Status: implemented", 1),
                       encoding="utf-8")
        code, out = run_checker(**self.paths)
        self.assertIn("28-credit-assignment.md: header says implemented", out)

    def test_hand_edited_generated_map_is_drift(self):
        doc = self.paths["DOC21"]
        doc.write_text(doc.read_text(encoding="utf-8").replace("| closure.py |", "| closure.py (edited) |"),
                       encoding="utf-8")
        code, out = run_checker(**self.paths)
        self.assertIn("Doc 21 current-state map is out of date", out)

    def test_implemented_without_tests_and_specified_with_code_are_rejected(self):
        def bad(r):
            r["R-09-COMMIT"]["tests"] = []
            r["R-26-01"] = {"status": "specified", "code": ["src/brainos/runtime.py::Runtime"]}
        self.mutate_map(bad)
        code, out = run_checker(**self.paths)
        self.assertIn("R-09-COMMIT: implemented without tests", out)
        self.assertIn("R-26-01: specified must not cite implementing code", out)

    def test_cell_and_status_rules(self):
        self.assertEqual(ct.expected_cells({"status": "implemented", "tests": ["x"], "verified": "full"}), "I✓ V✓")
        self.assertEqual(ct.expected_cells({"status": "partial", "tests": ["x"]}), "I∼ V∼")
        self.assertEqual(ct.expected_cells({"status": "specified"}), "I✗ V✗")
        self.assertEqual(ct.expected_cells({"status": "documentary"}), "I— V✗")
        self.assertEqual(ct.derived_doc_status(["implemented", "specified"]), {"partial"})
        self.assertEqual(ct.derived_doc_status(["specified", "documentary"]), {"specified", "research"})
        self.assertEqual(ct.derived_doc_status(["implemented", "documentary"]), {"implemented"})


if __name__ == "__main__":
    unittest.main()
