"""External provider boundary: operator-only registration, pinned identity,
same enforcement paths (R-02-14). Nondeterministic admission with recorded
evidence (R-02-15)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

from brainos import providers as trusted_providers

MOCK = str(Path(__file__).resolve().parents[1] / "implementations" / "mock_adapter.py")


class PrimitiveContracts(unittest.TestCase):
    """New catalogue primitives behave exactly (R-21-11)."""

    def test_normalize_ws(self):
        self.assertEqual(trusted_providers.compute("normalize_ws", "  hello   world  "),
                         "hello world")
        self.assertEqual(trusted_providers.compute("normalize_ws", ""), "")
        self.assertEqual(trusted_providers.compute("normalize_ws", "a\tb\nc"), "a b c")

    def test_parse_nl_sum_canonical(self):
        self.assertEqual(trusted_providers.compute("parse_nl_sum", "Add up 2 and 3."),
                         '{"operation": "sum", "values": [2, 3]}')
        self.assertEqual(trusted_providers.compute("parse_nl_sum", "add up 10, -4"),
                         '{"operation": "sum", "values": [10, -4]}')

    def test_parse_nl_sum_rejects_noncanonical(self):
        with self.assertRaises(Refused):
            trusted_providers.compute("parse_nl_sum", "Please add 7 and 8 together.")

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import verify_models  # noqa: E402

from brainos import Refused, Runtime  # noqa: E402
from brainos.devcontext import development_context  # noqa: E402

SCHEDULE = dict(initialization=100, inference=5, transport=1, memory=200,
                accelerator=0, overhead=1)
UNITS = dict(initialization="seconds", inference="attempts", transport="attempts",
             memory="MB", accelerator="seconds", overhead="attempts")
MEASURED = dict(initialization="adapter", inference="adapter", transport="kernel",
                memory="adapter", accelerator="adapter", overhead="kernel")
IDENTITIES = dict(model="Qwen/Qwen3-0.6B", runtime="transformers@4.57.1",
                  tokenizer="tok-A", prompt_template="A")
SAMPLING = dict(temperature=0.0, top_p=1.0, max_tokens=64, seed=11)
ARTIFACT = "f47f71177f32bcd101b7573ec9171e6a57f4f4d31148d38e382306f42996874b"


def external_kwargs(**over):
    deterministic = over.get("nondeterministic", True) is False
    params = dict(implementation="qwen3-lm", input="text", output="text",
                  capability="text-normalize", cost={"attempts": 3},
                  cost_schedule=dict(SCHEDULE), cost_units=dict(UNITS),
                  measured_by=dict(MEASURED), artifact=ARTIFACT,
                  identities=dict(IDENTITIES), nondeterministic=True)
    if not deterministic:
        params.update(sampling=dict(SAMPLING), admission=dict(n=3, k=2))
    params.update(over)
    return params


class ExternalRegistration(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.temp.name) / "c.db", profile="inprocess")

    def tearDown(self):
        self.r.close()
        self.temp.cleanup()

    def test_operator_registers_and_resolves(self):
        pid = self.r.registry.register_external(**external_kwargs())
        self.assertTrue(pid.startswith("qwen3-lm@ext-"))
        spec = self.r.registry.resolve(pid)
        self.assertEqual(spec["kind"], "external")
        self.assertEqual(spec["cost"], {"attempts": 3})
        self.assertEqual(spec["cost_schedule"], SCHEDULE)
        self.assertEqual(spec["cost_units"], UNITS)
        self.assertEqual(spec["measured_by"], MEASURED)
        self.assertEqual(spec["sampling"], SAMPLING)
        self.assertEqual(spec["nondeterministic"], True)
        self.assertEqual(spec["transitive_dependencies"], [])
        self.assertEqual(len(spec["provider_digest"]), 64)
        # Idempotent: same inputs pin the same record.
        self.assertEqual(self.r.registry.register_external(**external_kwargs()), pid)

    def test_registration_refuses(self):
        cases = [
            dict(issued_by="dev"),
            dict(artifact=""),
            dict(artifact="not-a-digest"),
            dict(artifact_algorithm="md5"),
            dict(cost_schedule={"inference": 1}),
            dict(cost_schedule=dict(SCHEDULE, inference=-1)),
            dict(cost_schedule=dict(SCHEDULE, inference=float("inf"))),
            dict(cost_units={"inference": "attempts"}),
            dict(cost_units=dict(UNITS, inference="")),
            dict(measured_by=dict(MEASURED, inference="guessed")),
            dict(identities={"model": "m"}),
            dict(identities=dict(IDENTITIES, tokenizer="")),
            dict(nondeterministic="yes"),
            dict(nondeterministic=True, sampling={}),
            dict(nondeterministic=True, sampling=None),
            dict(nondeterministic=False, sampling=dict(SAMPLING)),
            dict(cost={}),
        ]
        for kwargs in cases:
            with self.assertRaises(Refused, msg=kwargs):
                self.r.registry.register_external(**external_kwargs(**kwargs))

    def test_same_weights_different_config_are_different_providers(self):
        """B26: identity binds the complete specification, not the weights."""
        base = external_kwargs()
        other = external_kwargs(sampling=dict(SAMPLING, temperature=0.9),
                                identities=dict(IDENTITIES, tokenizer="tok-B",
                                                prompt_template="B", runtime="t2"))
        first = self.r.registry.register_external(**base)
        second = self.r.registry.register_external(**other)
        self.assertNotEqual(first, second)
        self.assertEqual(self.r.registry.resolve(first)["artifact"],
                         self.r.registry.resolve(second)["artifact"])
        # Authority is not shared: blocking one leaves the other resolvable.
        self.r.registry.exclude(first, "probe")
        with self.assertRaisesRegex(Refused, "blocked"):
            self.r.registry.resolve(first)
        self.assertIsNotNone(self.r.registry.resolve(second))

    def test_reregistration_cannot_change_semantics(self):
        """B27: same weights, different cost registers a new identity;
        both records survive and resolve."""
        first = self.r.registry.register_external(**external_kwargs())
        second = self.r.registry.register_external(
            **external_kwargs(cost={"attempts": 99}))
        self.assertNotEqual(first, second)
        self.assertEqual(self.r.registry.resolve(first)["cost"], {"attempts": 3})
        self.assertEqual(self.r.registry.resolve(second)["cost"], {"attempts": 99})

    def test_deterministic_external_registers_without_sampling(self):
        pid = self.r.registry.register_external(
            **external_kwargs(nondeterministic=False, sampling=None,
                              identities=dict(model="m", runtime="r")))
        spec = self.r.registry.resolve(pid)
        self.assertEqual(spec["sampling"], {})
        self.assertEqual(spec["nondeterministic"], False)

    def test_block_impact_applies_to_external_providers(self):
        pid = self.r.registry.register_external(**external_kwargs())
        self.r.registry.exclude(pid, "probe")
        with self.assertRaisesRegex(Refused, "blocked"):
            self.r.registry.resolve(pid)

    def test_tampered_record_fails_closed(self):
        pid = self.r.registry.register_external(**external_kwargs())
        with self.r.store.transaction():
            record = self.r.store.get("provider", pid)
            record["artifact"] = "0" * 64
            self.r.store.put("provider", pid, record)
        with self.assertRaisesRegex(Refused, "catalogue|malformed|drifted|identity"):
            self.r.registry.resolve(pid)

    def test_developmental_code_has_no_external_path(self):
        ctx = development_context(self.r)
        names = [name for name in dir(ctx) if "external" in name.lower()]
        self.assertEqual(names, [])


def mock_kwargs(**over):
    params = dict(implementation="mock-external", input="text", output="text",
                  capability="mock-text", cost={"attempts": 3},
                  cost_schedule=dict(SCHEDULE), cost_units=dict(UNITS),
                  measured_by=dict(MEASURED), artifact=ARTIFACT,
                  identities=dict(model="mock", runtime="mock-adapter/1"),
                  nondeterministic=False)
    params.update(over)
    return params


class ExternalExecution(unittest.TestCase):
    """D3: external invocation through the existing task executor (R-02-14)."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.temp.name) / "c.db", profile="inprocess",
                         external_adapters={"mock-external": [sys.executable, MOCK,
                                                              "--expect-artifact", ARTIFACT]})
        self.cap = self.r.population.define("mock-text", "text", "text",
                                            [("  padded  ", "  padded  ")])
        self.val = self.r.resources.create_budget("eco", {"attempts": 500})
        self.exe = self.r.resources.create_budget("eco", {"attempts": 5000})
        self.pid = self.r.registry.register_external(**mock_kwargs())
        self.r.population.admit(self.cap, self.pid, budget=self.val, principal="eco")

    def tearDown(self):
        self.r.close()
        self.temp.cleanup()

    def run_member(self, value, timeout=5):
        task = self.r.tasks.create_member_task("eco", self.cap, self.pid, value, self.exe,
                                               timeout=timeout)
        return self.r.tasks.run_task(task, self.r.tasks.authorize(task, "eco"), "eco"), task

    def test_member_task_through_external_adapter(self):
        output, task = self.run_member("  padded  ")
        self.assertEqual(output, "  padded  ")
        invocation = self.r.tasks.invocation(
            self.r.tasks.task(task, "eco")["invocation"], "eco")
        self.assertGreaterEqual(invocation["total_ns"], invocation["compute_ns"])
        self.assertGreaterEqual(invocation["compute_ns"], 0)

    def mock(self, mode, arg=""):
        return "__mock__:%s:%s" % (mode, arg)

    def test_no_launcher_is_fail_closed(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        rt = Runtime(Path(temp.name) / "c.db", profile="inprocess")
        self.addCleanup(rt.close)
        rt.population.define("mock-text", "text", "text", [("x", "x")])
        pid = rt.registry.register_external(**mock_kwargs())
        with self.assertRaisesRegex(Refused, "no external.*launcher"):
            rt.runner.compute(rt.registry.resolve(pid), "x", 5)

    def test_faults_are_provider_failures(self):
        for mode, arg in (("error", "boom"), ("wrong-artifact", ""), ("malformed", "")):
            with self.assertRaises(Refused, msg=mode):
                self.run_member(self.mock(mode, arg))
        # The adapter process is supervised: normal service resumes.
        output, _ = self.run_member("  padded  ")
        self.assertEqual(output, "  padded  ")

    def test_crash_recovers_on_next_request(self):
        with self.assertRaises(Refused):
            self.run_member(self.mock("crash"))
        output, _ = self.run_member("  padded  ")
        self.assertEqual(output, "  padded  ")

    def test_timeout_kills_the_adapter(self):
        with self.assertRaisesRegex(Refused, "wall-clock"):
            self.run_member(self.mock("timeout", "30"), timeout=3)
        output, _ = self.run_member("  padded  ")
        self.assertEqual(output, "  padded  ")

    def test_identity_mismatch_refused_at_both_boundaries(self):
        # Adapter-side pin check: launcher expects a different digest.
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        rt = Runtime(Path(temp.name) / "c.db", profile="inprocess",
                     external_adapters={"mock-external": [sys.executable, MOCK,
                                                          "--expect-artifact", "1" * 64]})
        self.addCleanup(rt.close)
        pid = rt.registry.register_external(**mock_kwargs())
        with self.assertRaisesRegex(Refused, "pin mismatch"):
            rt.runner.compute(rt.registry.resolve(pid), "x", 5)

    def test_budget_exhaustion_refuses_before_execution(self):
        poor = self.r.resources.create_budget("eco", {"attempts": 1})
        with self.assertRaisesRegex(Refused, "grant|attempts|below|requirement|overdraft"):
            self.r.tasks.create_member_task("eco", self.cap, self.pid, "x", poor)


MOCK_ARTIFACT = "a" * 64
NORMALIZE_CASES = [("  hello   world  ", "hello world"), ("no-change", "no-change"),
                   ("", "")]


class HeterogeneousOrganization(unittest.TestCase):
    """D5.1: deterministic and external providers serve one contract (R-02-14)."""

    ADAPTERS = {"mock-normalize": [sys.executable, MOCK, "--normalize",
                                   "--expect-artifact", MOCK_ARTIFACT]}

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.temp.name) / "c.db", profile="inprocess",
                         external_adapters={
                             "mock-normalize": [sys.executable, MOCK, "--normalize",
                                                "--expect-artifact", MOCK_ARTIFACT]})
        self.cap = self.r.population.define("text-normalize", "text", "text",
                                            NORMALIZE_CASES)
        self.val = self.r.resources.create_budget("eco", {"attempts": 2000})
        self.exe = self.r.resources.create_budget("eco", {"attempts": 20000})
        self.det = self.r.registry.register("normalize_ws")
        self.mock = self.r.registry.register_external(
            implementation="mock-normalize", input="text", output="text",
            capability="text-normalize", cost={"attempts": 3},
            cost_schedule=dict(SCHEDULE), cost_units=dict(UNITS),
            measured_by=dict(MEASURED), artifact=MOCK_ARTIFACT,
            identities=dict(model="mock", runtime="mock-adapter/1"),
            nondeterministic=False)
        self.r.population.admit(self.cap, self.det, budget=self.val, principal="eco")
        self.r.population.admit(self.cap, self.mock, budget=self.val, principal="eco")

    def tearDown(self):
        self.r.close()
        self.temp.cleanup()

    def serve(self, provider, value):
        task = self.r.tasks.create_member_task("eco", self.cap, provider, value, self.exe)
        return self.r.tasks.run_task(task, self.r.tasks.authorize(task, "eco"), "eco"), task

    def test_same_contract_same_outputs(self):
        for value, expected in NORMALIZE_CASES:
            self.assertEqual(self.serve(self.det, value)[0], expected)
            self.assertEqual(self.serve(self.mock, value)[0], expected)

    def test_substitution_across_substrates(self):
        self.r.registry.exclude(self.det, "probe")
        self.assertEqual(self.serve(self.mock, "  hello   world  ")[0], "hello world")
        with self.assertRaisesRegex(Refused, "blocked"):
            self.serve(self.det, "  hello   world  ")

    def test_meter_and_verdict_on_mixed_organization(self):
        from brainos import emergence
        tasks = [self.serve(self.det, "  a  b  ")[1], self.serve(self.mock, "  c  d  ")[1]]
        report = emergence.measure(self.r.store, self.cap, tasks,
                                   external_adapters=self.ADAPTERS)
        self.assertEqual(report["C"]["coverage"], 1.0)
        self.assertEqual(set(report["N"]["providers"]), {self.det, self.mock})
        verdict = emergence.organizational_verdict(self.r.store, self.cap,
                                                  external_adapters=self.ADAPTERS)
        self.assertEqual(verdict["verdict"], "redundant")

    def test_net_value_covers_both_substrates(self):
        from brainos import emergence
        tasks = [self.serve(self.det, "  a  b  ")[1], self.serve(self.mock, "  c  d  ")[1]]
        report = emergence.measure(self.r.store, self.cap, tasks,
                                   external_adapters=self.ADAPTERS)
        # Declared conversion, as in X4: one value unit per microsecond.
        scale = 10 ** -6
        costs = dict(compute=report["R"]["compute_ns"] * scale,
                     overhead=report["R"]["overhead_ns"] * scale,
                     construction=0, validation=0, assessment=0, maintenance=0)
        result = emergence.net_value(
            [dict(served=[dict(contract="text-normalize", late=False)] * 2, costs=costs)],
            {"text-normalize": dict(per_request=10)})
        self.assertGreater(result["total"], 0)


def nondeterministic_kwargs(**over):
    params = external_kwargs(implementation="mock-external", nondeterministic=True,
                             sampling=dict(SAMPLING), admission=dict(n=3, k=2))
    params.update(over)
    return params


class NondeterministicAdmission(unittest.TestCase):
    """D4: k-of-n empirical admission with recorded evidence (R-02-15)."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.temp.name) / "c.db", profile="inprocess",
                         external_adapters={"mock-external": [sys.executable, MOCK,
                                                              "--expect-artifact", ARTIFACT]})
        self.val = self.r.resources.create_budget("eco", {"attempts": 2000})

    def tearDown(self):
        self.r.close()
        self.temp.cleanup()

    def register(self, **over):
        return self.r.registry.register_external(**nondeterministic_kwargs(**over))

    def admit(self, cap, pid):
        return self.r.population.admit(cap, pid, budget=self.val, principal="eco")

    def evidence_of(self, cap, pid):
        member = next(m for m in self.r.store.find("member")
                      if m["id"] == f"{cap}|{pid}")
        return self.r.store.get("candidate", member["candidate"])

    def test_kofn_admission_records_evidence(self):
        cap = self.r.population.define("mock-text", "text", "text",
                                       [("a", "a"), ("b", "b")])
        pid = self.register()
        self.assertEqual(self.admit(cap, pid), f"{cap}|{pid}")
        self.assertEqual(self.r.population.state(cap, pid), "ACTIVE")
        record = self.evidence_of(cap, pid)
        evidence = record["admission_evidence"]
        self.assertEqual((evidence["n"], evidence["k"]), (3, 2))
        self.assertEqual(len(evidence["draws"]), 6)
        self.assertTrue(all(d["outcome"] == "correct" for d in evidence["draws"]))
        self.assertEqual(set(evidence["per_case"]), {cap + ":0", cap + ":1"})
        for detail in evidence["per_case"].values():
            self.assertEqual((detail["agreements"], detail["draws"]), (3, 3))
            lo, hi = detail["wilson"]
            self.assertLessEqual(0.0, lo)
            self.assertLessEqual(hi, 1.0)
        self.assertEqual(evidence["identities"]["sampling"], SAMPLING)
        self.assertEqual(evidence["identities"]["provider_digest"],
                         self.r.registry.resolve(pid)["provider_digest"])

    def test_partial_agreement_passes_with_recorded_wilson(self):
        cap = self.r.population.define("mock-flaky", "text", "text",
                                       [("__mock__:alternate", "__mock__:alternate")])
        pid = self.register()
        self.admit(cap, pid)
        self.assertEqual(self.r.population.state(cap, pid), "ACTIVE")
        evidence = self.evidence_of(cap, pid)["admission_evidence"]
        detail = evidence["per_case"][cap + ":0"]
        self.assertEqual((detail["agreements"], detail["draws"]), (2, 3))
        lo, hi = detail["wilson"]
        self.assertLess(lo, 2 / 3)
        self.assertLess(2 / 3, hi)

    def test_rejection_records_reasons(self):
        cap = self.r.population.define("mock-never", "text", "text",
                                       [("a", "never"), ("b", "never")])
        pid = self.register()
        with self.assertRaisesRegex(Refused, "0/3 agreements, needs 2"):
            self.admit(cap, pid)
        self.assertIsNone(self.r.population.state(cap, pid))

    def test_abstention_counts_where_declared(self):
        cap = self.r.population.define("mock-abs", "text", "text",
                                       [("hi", "hi"), ("???", "ABSTAIN")],
                                       abstain=["ABSTAIN"])
        pid = self.register()
        member = self.r.population.admit(
            cap, pid, budget=self.r.resources.create_budget("eco", {"attempts": 500}),
            principal="eco")
        self.assertEqual(self.r.population.state(cap, pid), "ACTIVE")
        evidence = self.r.store.get("candidate", self.r.store.get(
            "member", member)["candidate"])["admission_evidence"]
        abstentions = [d for d in evidence["draws"] if d.get("abstention")]
        self.assertTrue(abstentions)
        self.assertTrue(all(d["outcome"] == "correct" for d in evidence["draws"]))

    def test_insufficient_evidence_refuses(self):
        cap = self.r.population.define("mock-text", "text", "text", [("a", "a")])
        pid = self.register()
        poor = self.r.resources.create_budget("eco", {"attempts": 1})
        with self.assertRaises(Refused):
            self.r.population.admit(cap, pid, budget=poor, principal="eco")
        self.assertIsNone(self.r.population.state(cap, pid))

    def test_new_identity_needs_fresh_admission(self):
        cap = self.r.population.define("mock-text", "text", "text", [("a", "a")])
        first = self.register()
        self.admit(cap, first)
        second = self.register(sampling=dict(SAMPLING, temperature=0.9, seed=2))
        self.assertNotEqual(first, second)
        self.assertEqual(self.r.population.state(cap, first), "ACTIVE")
        self.assertIsNone(self.r.population.state(cap, second))
        self.admit(cap, second)
        self.assertEqual(self.r.population.state(cap, second), "ACTIVE")


class ManifestVerification(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "payload.bin").write_bytes(b"staged-bytes")

    def tearDown(self):
        self.temp.cleanup()

    def manifest(self, digest, location="payload.bin"):
        path = self.root / "manifest.json"
        path.write_text(json.dumps({"version": 1, "artifacts": [
            dict(id="probe", kind="probe", location=location, digest_sha256=digest)]}),
            encoding="utf-8")
        return path

    def test_matching_payload_verifies(self):
        import hashlib
        digest = hashlib.sha256(b"staged-bytes").hexdigest()
        report = verify_models.verify_manifest(self.manifest(digest))
        self.assertEqual(report, [dict(id="probe", location="payload.bin",
                                       staged=True, digest_match=True)])

    def test_tampered_payload_is_refused(self):
        report = verify_models.verify_manifest(self.manifest("0" * 64))
        self.assertEqual(report[0]["digest_match"], False)
        with self.assertRaisesRegex(SystemExit, "digest mismatch"):
            verify_models.main([], manifest_path=self.manifest("0" * 64))

    def test_missing_payload_is_reported_not_matched(self):
        report = verify_models.verify_manifest(self.manifest("0" * 64, "absent.bin"))
        self.assertEqual(report[0], dict(id="probe", location="absent.bin",
                                         staged=False, digest_match=None))
