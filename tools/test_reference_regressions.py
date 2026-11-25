"""Behavioral regressions for reference models, not production conformance."""
import unittest

import l1_stubs as s
import gate1_checks as g
from dep_closure import compute_closure


class PermitRegressionTests(unittest.TestCase):
    def setUp(self):
        self.provider = s.CalculatorV1()
        self.permit = s.make_permit(self.provider, 1, "Certified")

    def test_revoked_same_epoch_cannot_start(self):
        s.revoke_permit(self.permit)
        self.assertEqual(s.act(self.provider, self.permit, 1)[0], "refuse")

    def test_provider_binding(self):
        self.assertEqual(s.act(s.CalculatorV2(), self.permit, 1)[0], "refuse")

    def test_distinct_instance_binding(self):
        self.assertEqual(s.act(s.CalculatorV1(), self.permit, 1)[0], "refuse")

    def test_version_binding(self):
        self.provider.version = "v2"
        self.assertEqual(s.act(self.provider, self.permit, 1)[0], "refuse")

    def test_unissued_permit(self):
        self.assertEqual(s.act(self.provider, dict(self.permit), 1)[0], "refuse")

    def test_modified_issued_permit(self):
        self.permit["epoch"] = 2
        self.assertEqual(s.act(self.provider, self.permit, 2)[0], "refuse")

    def test_operation_scope(self):
        self.assertEqual(s.act(self.provider, self.permit, 1, operation="delete")[0], "refuse")

    def test_principal_scope(self):
        self.assertEqual(s.act(self.provider, self.permit, 1, principal="other")[0], "refuse")

    def test_context_scope(self):
        self.assertEqual(s.act(self.provider, self.permit, 1, context="other")[0], "refuse")

    def test_boolean_cannot_authorize_effect(self):
        self.assertEqual(s.act(self.provider, self.permit, 1, side_effect=True,
                               reauthorized=True), ("refuse", "reauth-required"))

    def test_issued_boundary_permit_allows_effect(self):
        boundary = s.make_permit(self.provider, 1, "Certified")
        self.assertEqual(s.act(self.provider, self.permit, 1, side_effect=True,
                               reauthorized=boundary)[0], "ok")

    def test_revoked_boundary_permit_denies_effect(self):
        boundary = s.make_permit(self.provider, 1, "Certified")
        s.revoke_permit(boundary)
        self.assertEqual(s.act(self.provider, self.permit, 1, side_effect=True,
                               reauthorized=boundary)[0], "refuse")

    def test_drain_only_preexisting_work(self):
        started = s.act(self.provider, self.permit, 1)
        s.revoke_permit(self.permit)
        self.assertEqual(s.act(self.provider, self.permit, 1, invocation=started[1])[0], "ok")
        self.assertEqual(s.act(self.provider, self.permit, 1, invocation=started[1],
                               side_effect=True)[0], "refuse")
        s.complete(started[1])
        self.assertEqual(s.act(self.provider, self.permit, 1, invocation=started[1])[0], "refuse")


class ClosureRegressionTests(unittest.TestCase):
    def test_no_change_does_not_invalidate_unknown(self):
        affected, _ = compute_closure(set(), [("A", "B")], {"A": {"cpu"}})
        self.assertEqual(affected, set())

    def test_cycle_is_valid(self):
        affected, _ = compute_closure({"A"}, [("A", "B"), ("B", "A")],
                                      {"A": set(), "B": set()})
        self.assertEqual(affected, {"A", "B"})

    def test_zero_cap_fails_for_growing_closure(self):
        from dep_closure import ClosureFault
        with self.assertRaises(ClosureFault):
            compute_closure({"A"}, [("B", "A")],
                            {"A": set(), "B": set()}, cap=0)


class StructuralValidatorRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = g.D09.read_text(encoding="utf-8")
        cls.register = g.D31.read_text(encoding="utf-8")
        cls.schemas, _ = g.collect_schemas(cls.text)
        cls.types, _ = g.extract_types(cls.text)
        cls.predicates, _ = g.extract_predicates(cls.text)

    def test_full_pipeline_rejects_duplicate_instruction(self):
        block = g.find_yaml_blocks(self.text)[0]
        results = g.run_all(self.text + "\n```yaml\n" + block + "```\n", self.register)
        self.assertTrue(any(not ok for _, ok, _ in results))

    def test_unknown_instruction_rejected_by_schema_validator(self):
        bad = {**self.schemas["OBSERVE"], "instruction": "UNKNOWN"}
        self.assertTrue(g.validate_schema("UNKNOWN", bad, self.types, self.predicates))

    def test_mismatched_instruction_rejected(self):
        self.assertTrue(g.validate_schema("INFER", self.schemas["OBSERVE"],
                                          self.types, self.predicates))

    def test_unbalanced_type_brackets_rejected(self):
        bad = {**self.schemas["OBSERVE"], "outputs": {"ref": "[EvidenceRef"}}
        self.assertTrue(g.validate_schema("OBSERVE", bad, self.types, self.predicates))


class DocumentIntegrityRegressionTests(unittest.TestCase):
    def test_repeated_unnumbered_section_rejected(self):
        body = "# Index\n\n## Ownership\nFirst\n\n## Ownership\nSecond\n"
        errors = g.check_markdown_integrity({g.DOCS / "README.md": body})
        self.assertTrue(any("duplicate section" in error for error in errors))

    def test_distinct_sections_accepted(self):
        body = "# Index\n\n## Ownership\nFirst\n\n## Reading order\nSecond\n"
        self.assertEqual(g.check_markdown_integrity({g.DOCS / "README.md": body}), [])

    def test_example_headings_inside_fences_are_ignored(self):
        body = "# Index\n\n## Ownership\n```text\n## Ownership\n```\n"
        self.assertEqual(g.check_markdown_integrity({g.DOCS / "README.md": body}), [])


if __name__ == "__main__":
    unittest.main()
