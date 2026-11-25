"""External provider boundary: operator-only registration, pinned identity,
same enforcement paths (R-02-14)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import verify_models  # noqa: E402

from brainos import Refused, Runtime  # noqa: E402
from brainos.devcontext import development_context  # noqa: E402

SCHEDULE = dict(initialization=100, inference=5, transport=1, memory=200,
                accelerator=0, overhead=1)
IDENTITIES = dict(model="Qwen/Qwen3-0.6B", runtime="transformers@4.57.1")
ARTIFACT = "f47f71177f32bcd101b7573ec9171e6a57f4f4d311d38e382306f42996874b"


def external_kwargs(**over):
    params = dict(implementation="qwen3-lm", input="text", output="text",
                  capability="text-normalize", cost={"attempts": 3},
                  cost_schedule=dict(SCHEDULE), artifact=ARTIFACT,
                  identities=dict(IDENTITIES), nondeterministic=True)
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
        self.assertEqual(spec["nondeterministic"], True)
        self.assertEqual(spec["transitive_dependencies"], [])
        # Idempotent: same inputs pin the same record.
        self.assertEqual(self.r.registry.register_external(**external_kwargs()), pid)

    def test_registration_refuses(self):
        cases = [
            dict(issued_by="dev"),
            dict(artifact=""),
            dict(cost_schedule={"inference": 1}),
            dict(cost_schedule=dict(SCHEDULE, inference=-1)),
            dict(cost_schedule=dict(SCHEDULE, inference=float("inf"))),
            dict(identities={"model": "m"}),
            dict(nondeterministic="yes"),
            dict(cost={}),
        ]
        for kwargs in cases:
            with self.assertRaises(Refused, msg=kwargs):
                self.r.registry.register_external(**external_kwargs(**kwargs))

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
        with self.assertRaisesRegex(Refused, "catalogue|malformed|drifted"):
            self.r.registry.resolve(pid)

    def test_developmental_code_has_no_external_path(self):
        ctx = development_context(self.r)
        names = [name for name in dir(ctx) if "external" in name.lower()]
        self.assertEqual(names, [])


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
