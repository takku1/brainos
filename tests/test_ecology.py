"""Ecology mechanism: contextual selection, funded exploration, evidence-based retention."""
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

from brainos import Refused, Runtime
from brainos import ecology
from brainos.ecology import EcologyPolicy, featurize

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import run_ecology  # noqa: E402

# Synthetic medians (ms) shaped like the measured niches: scan pair near-duplicates,
# hash best on many-narrow, bisect best on wide/mid, both scan and hash terrible on average.
COSTS = {
    "single-wide": {"scan": 0.18, "scan_list": 0.16, "bisect": 0.27, "hash": 3.0},
    "many-narrow": {"scan": 54.0, "scan_list": 51.0, "bisect": 0.37, "hash": 0.30},
    "many-wide": {"scan": 55.0, "scan_list": 52.0, "bisect": 0.36, "hash": 45.0},
}


def drive(policy, context, n, explore=True):
    picks = []
    for _ in range(n):
        member, _ = policy.select(context, explore)
        policy.observe(context, member, COSTS[context][member])
        picks.append(member)
    return picks


class Selection(unittest.TestCase):
    def test_featurizer_bands(self):
        self.assertEqual(featurize({"data": [], "queries": [[0, 40000]]}), "single-wide")
        self.assertEqual(featurize({"data": [], "queries": [[5, 7]] * 400}), "many-narrow")
        self.assertEqual(featurize({"data": [], "queries": [[0, 2000]] * 400}), "many-wide")
        self.assertEqual(featurize({"data": [], "queries": [[0, 2]] * 8}), "few-narrow")

    def test_converges_to_context_specialist_after_funded_exploration(self):
        policy = EcologyPolicy(list(COSTS["single-wide"]), epsilon=0.0)
        for context, best in (("single-wide", "scan_list"), ("many-narrow", "hash"), ("many-wide", "bisect")):
            picks = drive(policy, context, 20)
            self.assertEqual(picks[-5:], [best] * 5, context)
            self.assertEqual(sum(picks[:12].count(m) for m in COSTS[context]), 12)   # 4 members x 3 samples

    def test_no_exploration_without_budget(self):
        policy = EcologyPolicy(list(COSTS["single-wide"]), epsilon=1.0)
        drive(policy, "single-wide", 12)
        picks = [policy.select("single-wide", False) for _ in range(20)]
        self.assertTrue(all(not exploring for _, exploring in picks))

    def test_invalidated_evidence_forces_remeasurement(self):
        stale = {"bisect"}
        policy = EcologyPolicy(list(COSTS["single-wide"]), epsilon=0.0,
                               current=lambda member, revision: not (member in stale and revision < 5))
        drive(policy, "many-wide", 12)
        member, exploring = policy.select("many-wide", True)
        self.assertEqual((member, exploring), ("bisect", True))


class FollowUpMechanisms(unittest.TestCase):
    """X2b (PREREGISTRATION-v2.md): pruning and regeneration; off by default (v1)."""

    def test_pruning_skips_hopeless_members_and_blocks_their_retirement(self):
        policy = EcologyPolicy(list(COSTS["single-wide"]), epsilon=0.0, prune_factor=10.0)
        picks = drive(policy, "many-narrow", 12)
        self.assertEqual(picks.count("scan"), 1)                  # one sample at ~150x best, then pruned
        self.assertEqual(picks.count("scan_list"), 1)
        self.assertEqual(picks[-3:], ["hash"] * 3)
        self.assertFalse(policy.retirement_evidence("scan")["justified"])   # insufficient evidence

    def test_v1_default_explores_every_member_fully(self):
        policy = EcologyPolicy(list(COSTS["single-wide"]), epsilon=0.0)
        self.assertEqual(drive(policy, "many-narrow", 12).count("scan"), 3)

    def test_retire_archives_and_restore_returns_member(self):
        policy = EcologyPolicy(list(COSTS["single-wide"]), epsilon=0.0)
        drive(policy, "single-wide", 12)
        policy.retire("hash")
        self.assertEqual(policy.archived, ["hash"])
        self.assertTrue(policy.is_new("many-narrow"))
        policy.restore("hash")
        self.assertIn("hash", policy.members)
        self.assertEqual(drive(policy, "many-narrow", 20)[-1], "hash")


class Retention(unittest.TestCase):
    def populated(self):
        policy = EcologyPolicy(list(COSTS["single-wide"]), epsilon=0.0)
        for context in COSTS:
            drive(policy, context, 12)
        return policy

    def test_specialists_with_poor_aggregate_are_retained(self):
        policy = self.populated()
        for member in ("hash", "bisect", "scan_list"):
            evidence = policy.retirement_evidence(member)
            self.assertFalse(evidence["justified"], member)
            self.assertIn("specialist", {v["verdict"] for v in evidence["contexts"].values()})
        kept, dropped = ecology.aggregate_retirement(policy, keep=2)
        self.assertIn("hash", dropped + kept)                     # the naive rule ranks by mean cost
        self.assertNotIn("scan_list", kept)                       # and would drop the single-query specialist

    def test_redundant_duplicate_is_the_only_candidate(self):
        policy = self.populated()
        candidate = policy.retirement_candidate()
        self.assertEqual(candidate["member"], "scan")
        self.assertTrue(all(v["verdict"] == "redundant" for v in candidate["contexts"].values()))
        policy.retire("scan")
        self.assertIsNone(policy.retirement_candidate())          # scan_list is no longer redundant

    def test_unmeasured_context_blocks_retirement(self):
        policy = self.populated()
        policy.contexts.append("few-narrow")
        drive(policy, "few-narrow", 0)
        self.assertFalse(policy.retirement_evidence("scan")["justified"])


class PopulationIntegration(unittest.TestCase):
    def test_retire_and_restore_through_brainos(self):
        with tempfile.TemporaryDirectory() as d, Runtime(Path(d) / "c.db", profile="inprocess") as rt:
            cap = rt.population.define("range-count", "range-batch", "integers", run_ecology.ADMISSION)
            budget = rt.resources.create_budget("eco", {"attempts": 60})
            ids = {n: rt.registry.register(n) for n in run_ecology.MEMBERS}
            for provider in ids.values():
                rt.population.admit(cap, provider, budget=budget, principal="eco")
            value = {"data": [4, 8, 15, 16, 23, 42], "queries": [[5, 20], [40, 50]]}
            outputs = set()
            for provider in ids.values():
                task = rt.tasks.create_member_task("eco", cap, provider, value, budget)
                outputs.add(tuple(rt.tasks.run_task(task, rt.tasks.authorize(task, "eco"), "eco")))
            self.assertEqual(outputs, {(3, 1)})
            policy = Retention().populated()
            evidence = policy.retirement_candidate()
            rt.population.retire(cap, ids["range_scan"], reason="redundant", evidence=evidence)
            self.assertEqual(len(rt.population.members(cap)), 3)
            with self.assertRaises(Refused):
                rt.tasks.create_member_task("eco", cap, ids["range_scan"], value, budget)
            stored = [r for r in rt.store.find("retirement")]
            self.assertEqual(stored[0]["evidence"]["rule"], "redundant-within-margin-in-every-observed-context")
            rt.population.restore(cap, ids["range_scan"], budget=budget, principal="eco")
            self.assertEqual(len(rt.population.members(cap)), 4)


class PreregistrationIntegrity(unittest.TestCase):
    def test_runner_refuses_changed_preregistration(self):
        self.assertEqual(run_ecology.verify_preregistration(), run_ecology.PREREG_SHA256)
        with tempfile.TemporaryDirectory() as d:
            copy = Path(d) / "PREREGISTRATION.md"
            shutil.copy(run_ecology.PREREG, copy)
            copy.write_text(copy.read_text(encoding="utf-8").replace("<= 15", "<= 25"), encoding="utf-8")
            with self.assertRaises(SystemExit):
                run_ecology.verify_preregistration(copy)

    def test_line_endings_do_not_change_the_digest(self):
        with tempfile.TemporaryDirectory() as d:
            copy = Path(d) / "p.md"
            copy.write_bytes(run_ecology.PREREG.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
            self.assertEqual(run_ecology.verify_preregistration(copy), run_ecology.PREREG_SHA256)


if __name__ == "__main__":
    unittest.main()
