"""W2 runner corrections B31-B37: regression tests (Amendment-1).

Mock-only and synthetic fixtures. No Qwen execution: every behavioral
claim is reproduced against mock adapters or hand-built runner outputs.
"""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import run_heterogeneous as H  # noqa: E402

from brainos import Refused, Runtime  # noqa: E402
from brainos import emergence  # noqa: E402

MOCK = str(Path(__file__).resolve().parents[1] / "implementations" / "mock_adapter.py")
ARTIFACT = "f47f71177f32bcd101b7573ec9171e6a57f4f4d31148d38e382306f42996874b"
SCHEDULE = dict(initialization=100, inference=5, transport=1, memory=200,
                accelerator=0, overhead=1)
UNITS = dict(initialization="seconds", inference="attempts", transport="attempts",
             memory="MB", accelerator="seconds", overhead="attempts")
MEASURED = dict(initialization="adapter", inference="adapter", transport="kernel",
                memory="adapter", accelerator="kernel", overhead="kernel")
IDENTITIES = dict(model="mock-model", runtime="mock-adapter/1",
                  tokenizer="tok-A", prompt_template="A")
SAMPLING = dict(temperature=0.0, top_p=1.0, max_tokens=64, seed=11)
ADAPTERS = {"mock-external": [sys.executable, MOCK, "--expect-artifact", ARTIFACT]}


def mock_kwargs(**over):
    params = dict(implementation="mock-external", input="text", output="text",
                  capability="mock-text", cost={"attempts": 3},
                  cost_schedule=dict(SCHEDULE), cost_units=dict(UNITS),
                  measured_by=dict(MEASURED), artifact=ARTIFACT,
                  identities=dict(IDENTITIES), nondeterministic=True,
                  sampling=dict(SAMPLING), admission=dict(n=3, k=2))
    params.update(over)
    return params


def meter(compute_ns=1000, overhead_ns=100, assessment_ns=50, maintenance=0):
    return {"R": dict(compute_ns=compute_ns, overhead_ns=overhead_ns,
                      assessment_ns=assessment_ns, maintenance_units=maintenance)}


def stream():
    return ([dict(idx=i, split="calibration",
                  context="canonical" if i < 2 else "irregular",
                  value=f"cal {i}", expected={"operation": "sum", "values": [i, 1]})
             for i in range(4)]
            + [dict(idx=i, split="held-out",
                    context="canonical" if i < 6 else "irregular",
                    value=f"held {i}", expected={"operation": "sum", "values": [i, 1]})
               for i in range(4, 8)])


def full_out():
    """A complete consistent synthetic seed output: all arms metered."""
    out = dict(seed=21, stream=stream(), selection={"canonical": "deterministic",
                                                   "irregular": "deterministic"},
               qwen_admitted=True, deterministic_admitted=True,
               validation_costs={"deterministic": 2, "qwen": 180},
               table=[], meters={a: meter() for a in H.EXPECTED_ARMS},
               sum_meters={}, nonattainment={},
               verdict={"verdict": "redundant", "checks_spent": 5},
               skipped=[])
    out["setup"] = H.build_setup(out, [], {"deterministic": "d", "qwen": "q"},
                                 out["validation_costs"], 2, 6)
    runs = []
    for idx in range(4, 8):
        for arm, member in (("fixed", "deterministic"), ("neural", "qwen"),
                            ("coordinated", "deterministic")):
            runs.append(dict(idx=idx, arm=arm, member=member, served=True, correct=True,
                             output='{"operation": "sum", "values": [%d, 1]}' % idx,
                             eval="match", compute_ns=1000, total_ns=1100, late=False))
    out["runs"] = runs
    out["nov"] = H.nov_by_arm(out)
    return out


class StrictIR(unittest.TestCase):
    """B35: the typed intermediate representation is strictly validated."""

    def test_exact_match(self):
        ok, why = H.interpret('{"operation": "sum", "values": [2, 3]}',
                              {"operation": "sum", "values": [2, 3]})
        self.assertEqual((ok, why), (True, "match"))

    def test_valid_alias_matches(self):
        ok, why = H.interpret('{"operation": "add", "values": [2, 3]}',
                              {"operation": "sum", "values": [2, 3]})
        self.assertEqual((ok, why), (True, "match"))

    def test_bool_operands_rejected(self):
        # Python: [True, 2] == [1, 2]. The contract still rejects bool.
        ok, why = H.interpret('{"operation": "sum", "values": [true, 2]}',
                              {"operation": "sum", "values": [1, 2]})
        self.assertEqual((ok, why), (False, "bad-values"))

    def test_float_operands_rejected(self):
        ok, why = H.interpret('{"operation": "sum", "values": [1.0, 2]}',
                              {"operation": "sum", "values": [1, 2]})
        self.assertEqual((ok, why), (False, "bad-values"))

    def test_string_operands_rejected(self):
        ok, why = H.interpret('{"operation": "sum", "values": ["2", 3]}',
                              {"operation": "sum", "values": [2, 3]})
        self.assertEqual((ok, why), (False, "bad-values"))

    def test_unparseable(self):
        self.assertEqual(H.interpret("nope", {"operation": "sum", "values": [1]})[1],
                         "unparseable")

    def test_not_an_object(self):
        ok, why = H.interpret("[1, 2]", {"operation": "sum", "values": [1, 2]})
        self.assertEqual((ok, why), (False, "not-an-object"))

    def test_missing_field_rejected(self):
        ok, why = H.interpret('{"operation": "sum"}',
                              {"operation": "sum", "values": [1]})
        self.assertEqual((ok, why), (False, "bad-shape"))

    def test_extra_key_rejected(self):
        ok, why = H.interpret('{"operation": "sum", "values": [2, 3], "note": "hi"}',
                              {"operation": "sum", "values": [2, 3]})
        self.assertEqual((ok, why), (False, "bad-shape"))

    def test_unknown_operation(self):
        ok, why = H.interpret('{"operation": "multiply", "values": [2, 3]}',
                              {"operation": "sum", "values": [2, 3]})
        self.assertEqual((ok, why), (False, "unknown-operation"))

    def test_unhashable_operation_cannot_crash(self):
        ok, why = H.interpret('{"operation": ["sum"], "values": [2, 3]}',
                              {"operation": "sum", "values": [2, 3]})
        self.assertEqual((ok, why), (False, "unhashable-operation"))

    def test_null_operation_rejected(self):
        ok, why = H.interpret('{"operation": null, "values": [2, 3]}',
                              {"operation": "sum", "values": [2, 3]})
        self.assertEqual((ok, why), (False, "unknown-operation"))

    def test_abstention_recorded_separately(self):
        self.assertEqual(H.interpret("ABSTAIN", {"operation": "sum", "values": [1]}),
                         (False, "abstained"))
        self.assertEqual(H.interpret("  ABSTAIN\n", {"operation": "sum", "values": [1]}),
                         (False, "abstained"))

    def test_mismatch(self):
        ok, why = H.interpret('{"operation": "sum", "values": [2, 4]}',
                              {"operation": "sum", "values": [2, 3]})
        self.assertEqual((ok, why), (False, "mismatch"))


class ArmAttribution(unittest.TestCase):
    """B31: outcomes are attributed by experimental arm, not provider name."""

    def test_coordinated_gets_own_outcomes_whichever_member_served(self):
        out = full_out()
        # Coordinated executions served through the deterministic member
        # still serve the coordinated arm (old code credited nobody).
        self.assertEqual(out["nov"]["coordinated"]["served"], 4)
        self.assertEqual(out["nov"]["fixed"]["served"], 4)

    def test_no_cross_arm_leakage_or_double_credit(self):
        out = full_out()
        out["runs"] = [dict(idx=4, arm="fixed", member="deterministic",
                            served=True, correct=True, compute_ns=1000,
                            total_ns=1100, late=False)]
        out["nov"] = H.nov_by_arm(out)
        self.assertEqual(out["nov"]["fixed"]["served"], 1)
        self.assertEqual(out["nov"]["coordinated"]["served"], 0)
        self.assertEqual(out["nov"]["neural"]["served"], 0)

    def test_neural_member_serving_fixed_counts_for_fixed(self):
        out = full_out()
        out["runs"] = [dict(idx=4, arm="fixed", member="qwen",
                            served=True, correct=True, compute_ns=4000,
                            total_ns=4100, late=False)]
        out["nov"] = H.nov_by_arm(out)
        self.assertEqual(out["nov"]["fixed"]["served"], 1)
        self.assertEqual(out["nov"]["neural"]["served"], 0)


class Completeness(unittest.TestCase):
    """B32: the complete expected arm set is required, loudly."""

    def test_full_set_passes(self):
        out = full_out()
        checks = H.check_hypotheses(out)
        self.assertTrue(checks["H1"]["passed"], checks["H1"])
        self.assertTrue(checks["H2"]["passed"], checks["H2"])

    def test_silently_missing_arm_fails_h1(self):
        out = full_out()
        del out["meters"]["neural"]
        out["runs"] = [e for e in out["runs"] if e["arm"] != "neural"]
        out["nov"] = H.nov_by_arm(out)
        checks = H.check_hypotheses(out)
        self.assertFalse(checks["H1"]["passed"])
        self.assertEqual(checks["H1"]["missing"], ["neural"])

    def test_explicit_nonattainment_passes_h1(self):
        out = full_out()
        del out["meters"]["neural"]
        out["runs"] = [e for e in out["runs"] if e["arm"] != "neural"]
        out["qwen_admitted"] = False
        out["qwen_admission_error"] = "nondeterministic admission failed: ..."
        for idx in range(4, 8):
            out["skipped"].append(dict(idx=idx, arm="neural",
                                       reason="qwen not admitted"))
        out["nonattainment"] = H.build_nonattainment(out)
        out["nov"] = H.nov_by_arm(out)
        self.assertIn("neural", out["nonattainment"])
        self.assertTrue(out["nov"]["neural"]["nonattained"])
        for name in emergence.NOV_COSTS:
            self.assertEqual(out["nov"]["neural"]["costs"][name], 0.0)
        checks = H.check_hypotheses(out)
        self.assertTrue(checks["H1"]["passed"], checks["H1"])
        self.assertTrue(checks["H2"]["passed"], checks["H2"])
        self.assertEqual(checks["H1"]["nonattained"], ["neural"])

    def test_meter_failure_fails_h1(self):
        out = full_out()
        out["meter_failures"] = {"neural": "boom"}
        checks = H.check_hypotheses(out)
        self.assertFalse(checks["H1"]["passed"])

    def test_missing_pair_fails_h2(self):
        out = full_out()
        out["runs"] = [e for e in out["runs"]
                       if not (e["idx"] == 4 and e["arm"] == "coordinated")]
        checks = H.check_hypotheses(out)
        self.assertFalse(checks["H2"]["passed"], checks["H2"])

    def test_skip_covers_pair(self):
        out = full_out()
        out["runs"] = [e for e in out["runs"]
                       if not (e["idx"] == 4 and e["arm"] == "coordinated")]
        out["skipped"].append(dict(idx=4, arm="coordinated",
                                   reason="no-provider-selected"))
        checks = H.check_hypotheses(out)
        self.assertTrue(checks["H2"]["passed"], checks["H2"])

    def test_nov_missing_arm_fails_h2(self):
        out = full_out()
        del out["nov"]["neural"]
        checks = H.check_hypotheses(out)
        self.assertFalse(checks["H2"]["passed"], checks["H2"])

    def test_nonattained_arm_needs_marking_in_nov(self):
        out = full_out()
        del out["meters"]["neural"]
        out["runs"] = [e for e in out["runs"] if e["arm"] != "neural"]
        for idx in range(4, 8):
            out["skipped"].append(dict(idx=idx, arm="neural",
                                       reason="qwen not admitted"))
        out["qwen_admitted"] = False
        out["qwen_admission_error"] = "refused"
        out["nonattainment"] = H.build_nonattainment(out)
        out["nov"] = H.nov_by_arm(out)
        del out["nov"]["neural"]["nonattained"]
        checks = H.check_hypotheses(out)
        self.assertFalse(checks["H2"]["passed"], checks["H2"])


class ComparativeEvidence(unittest.TestCase):
    """B36: H5 needs valid observations from both families."""

    def runs(self, qwen_ns, det_ns):
        runs = []
        for ns in qwen_ns:
            runs.append(dict(idx=4, arm="neural", member="qwen",
                             served=True, correct=True, compute_ns=ns,
                             total_ns=ns + 100, late=False))
        for ns in det_ns:
            runs.append(dict(idx=4, arm="fixed", member="deterministic",
                             served=True, correct=True, compute_ns=ns,
                             total_ns=ns + 100, late=False))
        return runs

    def check_h5(self, qwen_ns, det_ns):
        out = full_out()
        out["runs"] = self.runs(qwen_ns, det_ns)
        return H.check_hypotheses(out)["H5"]

    def test_missing_deterministic_is_insufficient_not_pass(self):
        h5 = self.check_h5([40000], [])
        self.assertFalse(h5["passed"])
        self.assertEqual(h5["reason"], "insufficient-comparative-evidence")

    def test_missing_neural_is_insufficient_not_pass(self):
        h5 = self.check_h5([], [1000])
        self.assertFalse(h5["passed"])
        self.assertEqual(h5["reason"], "insufficient-comparative-evidence")

    def test_zero_denominator_is_insufficient_not_pass(self):
        h5 = self.check_h5([40000], [0])
        self.assertFalse(h5["passed"])
        self.assertEqual(h5["reason"], "insufficient-comparative-evidence")

    def test_ratio_below_threshold_fails(self):
        h5 = self.check_h5([5000], [1000])
        self.assertFalse(h5["passed"])
        self.assertEqual(h5["ratio"], 5.0)

    def test_ratio_meeting_threshold_passes(self):
        h5 = self.check_h5([40000], [1000])
        self.assertTrue(h5["passed"])
        self.assertEqual(h5["ratio"], 40.0)


class FailedCostAccounting(unittest.TestCase):
    """B33: failed, refused, timed-out and cancelled work stays accounted."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.temp.name) / "c.db", profile="inprocess",
                         external_adapters=dict(ADAPTERS))
        self.val = self.r.resources.create_budget("dev", {"attempts": 5000})
        self.exe = self.r.resources.create_budget("dev", {"attempts": 5000})
        self.cap = self.r.population.define("mock-text", "text", "text",
                                            [("  padded  ", "  padded  ")])
        self.pid = self.r.registry.register_external(**mock_kwargs())
        self.r.population.admit(self.cap, self.pid, budget=self.val, principal="dev")

    def tearDown(self):
        self.r.close()
        self.temp.cleanup()

    def run_task(self, value, timeout=5):
        return H.run_task(self.r, self.cap, self.pid, value, self.exe,
                          timeout=timeout)

    def test_success_returns_task_output_invocation_no_error(self):
        task, output, invocation, error = self.run_task("  padded  ")
        self.assertEqual(output, "  padded  ")
        self.assertIsNone(error)
        self.assertGreaterEqual(invocation["total_ns"], invocation["compute_ns"])
        self.assertTrue(H._terminal(self.r, task))

    def test_refusal_returns_task_and_error(self):
        task, output, invocation, error = self.run_task("__mock__:error:boom")
        self.assertIsNone(output)
        self.assertTrue(error)
        self.assertTrue(H._terminal(self.r, task))
        self.assertEqual(self.r.tasks.task(task, "dev")["state"], "FAILED")

    def test_timeout_returns_task_and_error(self):
        task, output, invocation, error = self.run_task("__mock__:timeout:30",
                                                        timeout=2)
        self.assertIsNone(output)
        self.assertTrue(error)
        self.assertTrue(H._terminal(self.r, task))

    def test_rejected_admission_records_attempts(self):
        cap = self.r.population.define("mock-never", "text", "text",
                                       [("a", "never"), ("b", "never")])
        pid = self.r.registry.register_external(**mock_kwargs())
        with self.assertRaises(Refused):
            self.r.population.admit(cap, pid, budget=self.val, principal="dev")
        # 2 cases x 3 draws: the 9-attempt shape from B33, generalized.
        self.assertEqual(H.validation_attempts_of(self.r.store, cap, pid), 6)
        self.assertEqual(H.validation_cost_of(self.r, cap, pid, 3), 18)

    def test_admitted_spend_matches_candidate_record(self):
        self.assertEqual(H.validation_attempts_of(self.r.store, self.cap, self.pid), 3)
        self.assertEqual(H.validation_cost_of(self.r, self.cap, self.pid, 3), 9)


class OracleBound(unittest.TestCase):
    """B34: the oracle uses the declared held-out horizon only."""

    def test_calibration_success_does_not_inflate_oracle(self):
        out = full_out()
        out["runs"].append(dict(idx=0, arm="fixed", member="deterministic",
                                served=True, correct=True, compute_ns=1,
                                total_ns=2, late=False))
        oracle = H.oracle_result(out)
        self.assertEqual(oracle["demands_covered"], 4)
        plain = H.oracle_result(full_out())
        self.assertEqual(oracle["total"], plain["total"])

    def test_oracle_ignores_non_held_out_entries(self):
        out = full_out()
        out["runs"] = [dict(idx=0, arm="fixed", member="deterministic",
                            served=True, correct=True, compute_ns=1,
                            total_ns=2, late=False)]
        oracle = H.oracle_result(out)
        self.assertEqual(oracle["demands_covered"], 0)
        self.assertEqual(oracle["total"], 0.0)


class CoordinatedCharge(unittest.TestCase):
    """B34: coordinated selection pays the full calibration evidence cost."""

    def test_coordinated_pays_both_members_calibration(self):
        out = full_out()
        out["setup"]["calibration"] = {
            "deterministic": dict(demands=4, compute_ns=4000000, overhead_ns=400000),
            "qwen": dict(demands=4, compute_ns=8000000, overhead_ns=800000)}
        out["nov"] = H.nov_by_arm(out)
        coordinated = out["nov"]["coordinated"]["costs"]
        self.assertAlmostEqual(coordinated["compute"], 0.001 + 4.0 + 8.0)
        self.assertAlmostEqual(coordinated["overhead"], 0.0001 + 0.4 + 0.8)
        fixed = out["nov"]["fixed"]["costs"]
        self.assertAlmostEqual(fixed["compute"], 0.001)
        self.assertIn("admission, calibration", out["setup"]["boundary"])


class AssessmentBudget(unittest.TestCase):
    """The preregistered organizational-assessment budget is enforced."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.temp.name) / "c.db", profile="inprocess",
                         external_adapters=dict(ADAPTERS))
        self.cap = self.r.population.define("mock-text", "text", "text",
                                            [("  padded  ", "  padded  ")])
        pid = self.r.registry.register_external(**mock_kwargs())
        val = self.r.resources.create_budget("dev", {"attempts": 5000})
        self.r.population.admit(self.cap, pid, budget=val, principal="dev")

    def tearDown(self):
        self.r.close()
        self.temp.cleanup()

    def test_declared_budget_bounds_assessment(self):
        verdict = emergence.organizational_verdict(
            self.r.store, self.cap, external_adapters=dict(ADAPTERS),
            development_budget=H.VERDICT_BUDGET)
        self.assertLessEqual(verdict["checks_spent"], H.VERDICT_BUDGET)
        self.assertIn(verdict["verdict"], ("organizational",
                                           "compositional-but-fragile",
                                           "redundant", "neither",
                                           "inconclusive-budget"))

    def test_zero_budget_aborts_assessment_with_spent_zero(self):
        verdict = emergence.organizational_verdict(
            self.r.store, self.cap, external_adapters=dict(ADAPTERS),
            development_budget=0)
        self.assertEqual(verdict["verdict"], "inconclusive-budget")
        self.assertEqual(verdict["checks_spent"], 0)

    def test_inconclusive_budget_satisfies_h3(self):
        out = full_out()
        out["verdict"] = {"verdict": "inconclusive-budget", "checks_spent": 100}
        checks = H.check_hypotheses(out)
        self.assertTrue(checks["H3"]["passed"], checks["H3"])


class FreezeManifest(unittest.TestCase):
    """B37: the freeze binds the execution boundary; tampering refuses."""

    def test_live_tree_matches_its_own_state(self):
        state = H.current_freeze_state()
        self.assertEqual(H.check_frozen(state), state)

    def test_tampered_source_refuses(self):
        state = copy.deepcopy(H.current_freeze_state())
        key = next(iter(state["files"]))
        state["files"][key] = "0" * 64
        with self.assertRaises(SystemExit):
            H.check_frozen(state)

    def test_missing_file_refuses(self):
        state = copy.deepcopy(H.current_freeze_state())
        state["files"]["src/brainos/deleted_module.py"] = "0" * 64
        with self.assertRaises(SystemExit):
            H.check_frozen(state)

    def test_tampered_model_digest_refuses(self):
        state = copy.deepcopy(H.current_freeze_state())
        state["model"]["digest_sha256"] = "0" * 64
        with self.assertRaises(SystemExit):
            H.check_frozen(state)

    def test_tampered_prompt_refuses(self):
        state = copy.deepcopy(H.current_freeze_state())
        state["prompt"]["sha256"] = "0" * 64
        with self.assertRaises(SystemExit):
            H.check_frozen(state)

    def test_tampered_packages_refuse(self):
        state = copy.deepcopy(H.current_freeze_state())
        state["packages"]["torch"] = "0.0.0-fake"
        with self.assertRaises(SystemExit):
            H.check_frozen(state)

    def test_tampered_sampling_refuses(self):
        state = copy.deepcopy(H.current_freeze_state())
        state["sampling"]["temperature"] = 0.9
        with self.assertRaises(SystemExit):
            H.check_frozen(state)

    def test_extra_file_does_not_invalidate(self):
        state = H.current_freeze_state()
        key = next(iter(state["files"]))
        subset = copy.deepcopy(state)
        subset["files"] = {key: state["files"][key]}
        # Untracked extra files cannot alter pinned behavior.
        self.assertEqual(H.check_frozen(subset)["files"][key],
                         state["files"][key])

    def test_model_content_change_detected_without_rename(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "tok.json").write_text('{"a": 1}', encoding="utf-8")
            before = H.hash_model_dir(root)
            (root / "tok.json").write_text('{"a": 2}', encoding="utf-8")
            after = H.hash_model_dir(root)
            self.assertNotEqual(before["files"]["tok.json"],
                                after["files"]["tok.json"])
            self.assertEqual(before["bytes_total"], after["bytes_total"])

    def test_frozen_manifest_hashes_every_model_artifact(self):
        state = H.current_freeze_state()
        names = set(state["model"]["files"])
        self.assertTrue({"model.safetensors", "tokenizer.json", "vocab.json",
                         "merges.txt", "config.json"}.issubset(names),
                        names)
        self.assertGreater(state["model"]["bytes_total"], 10 ** 9)

    def test_model_file_removed_from_manifest_refuses(self):
        state = copy.deepcopy(H.current_freeze_state())
        state["model"]["files"].pop(next(iter(state["model"]["files"])))
        with self.assertRaises(SystemExit):
            H.check_frozen(state)


class RunIntegrity(unittest.TestCase):
    """Clearance: aborts fail the process; seeds never execute twice."""

    def fake(self, calls, behavior):
        def run(seed, outdir, status=None):
            calls.append(seed)
            if isinstance(behavior, Exception):
                status["phase"] = "metering"
                raise behavior
            return dict(seed=seed, hypotheses={}, verdict={}, nov={},
                        oracle={"total": 0.0})
        return run

    def test_abort_writes_record_and_counts_seed(self):
        import tempfile
        real = H._run_seed
        calls = []
        H._run_seed = self.fake(calls, RuntimeError("boom"))
        try:
            with tempfile.TemporaryDirectory() as tmp:
                completed, aborted = H.run_seeds(Path(tmp), [21])
                self.assertEqual((completed, aborted), ([], [21]))
                abort = json.loads((Path(tmp) / "seed-21.aborted.json")
                                   .read_text(encoding="utf-8"))
                self.assertEqual(abort["phase"], "metering")
                self.assertIn("boom", abort["error"])
        finally:
            H._run_seed = real

    def test_existing_abort_refuses_before_execution(self):
        import tempfile
        # Real _run_seed: the abort check precedes any Qwen work, so this
        # exercises the actual refusal path with no model execution.
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "seed-21.aborted.json").write_text("{}", encoding="utf-8")
            with self.assertRaises(SystemExit):
                H.run_seeds(Path(tmp), [21])

    def test_existing_result_refuses_before_execution(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "seed-21.json").write_text("{}", encoding="utf-8")
            with self.assertRaises(SystemExit):
                H.run_seeds(Path(tmp), [21])

    def test_unknown_seed_refuses(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(SystemExit):
                H.run_seeds(Path(tmp), [99])

    def test_main_exit_code_reflects_aborts(self):
        real_verify, real_run = H.verify_frozen, H.run_seeds
        H.verify_frozen = lambda: None
        try:
            H.run_seeds = lambda outdir, seeds: ([21], [])
            self.assertEqual(H.main([]), 0)
            H.run_seeds = lambda outdir, seeds: ([22], [21])
            self.assertEqual(H.main([]), 1)
        finally:
            H.verify_frozen, H.run_seeds = real_verify, real_run

    def test_committed_freeze_manifest_matches_tree(self):
        expect = json.loads(H.FROZEN.read_text(encoding="utf-8"))
        self.assertEqual(expect["preregistration_sha256"], H.PREREG_SHA256)
        H.check_frozen(expect)


if __name__ == "__main__":
    unittest.main()
