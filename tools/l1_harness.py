"""L1 conformance harness (reference, Phase 1B).

Runs checks against minimal stubs (tools/l1_stubs.py). Each check has
a conforming case (must PASS) and, where applicable, a defective twin
that the harness must REJECT (detection counts as harness PASS).
Verdicts: PASS / FAIL / INDETERMINATE (contract permits multiple
outcomes; recorded, never counted as pass). A passing stub suite
proves the harness discriminates — not that BrainOS Core exists.
Usage: py tools/l1_harness.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gate1_checks as gc
import l1_stubs as S

results = []


def check(name, kind, cond, detail=""):
    # kind: "valid" (must hold) or "defective" (violation must be caught).
    # cond None = INDETERMINATE (contract permits multiple outcomes).
    if cond is None:
        results.append((name, kind, None, detail))
        print(f"[INDETERMINATE] {name} [{kind}] — {detail}")
        return None
    ok = bool(cond)
    results.append((name, kind, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name} [{kind}]" +
          (f" — {detail}" if detail else ""))
    return ok


def run():
    results.clear()
    # H1: two independent implementations, one contract (L1-C1).
    a, b = S.CalculatorV1(), S.CalculatorV2()
    same = all(a.compute(op, 6, 7) == b.compute(op, 6, 7)
               for op in ("add", "mul"))
    check("H1 two-implementations-one-contract", "valid", same,
          "calc-v1 == calc-v2 on add/mul")

    # H2: G-01 separation probe — supervisor sees envelopes only.
    sup = S.Supervisor()
    env = {"contract": "arithmetic", "version": "v1", "tier": "Certified",
           "schema": "s", "freshness": 0, "cost": 1, "quality": 1,
           "support_refs": [], "payload_bytes": b"\x00\x01"}
    man = {"contracts": {"arithmetic": ["v1"]}, "epoch": 3}
    dec = sup.decide({"irreversible": False}, env, man)
    check("H2 separation-clean", "valid",
          dec[0] == "permit" and "payload_bytes" not in sup.accessed,
          f"decision={dec}, accessed={sup.accessed}")
    bad = S.SnoopingSupervisor()
    bad.decide({"irreversible": False}, env, man)
    check("H2 separation-defective-caught", "defective",
          "payload_bytes" in bad.accessed,
          "snooping supervisor touched payload bytes")

    # H3: challenge suspends at next epoch cut, not mid-epoch.
    # Deferred: needs an epoch-modeling harness (open Phase 1B item).
    results.append(("H3 challenge-not-mid-epoch", "valid", None,
                    "deferred: needs epoch-modeling harness"))
    print("[SKIP] H3 challenge-not-mid-epoch — deferred, needs epoch model")

    # H4: quarantine blocks the unit, not its neighbors.
    q = S.CalculatorV1(quarantined=True)
    e = S.CalculatorV1()
    p = S.make_permit(q, 1, "Certified")
    r1 = S.act(q, p, 1)
    p2 = S.make_permit(e, 1, "Certified")
    r2 = S.act(e, p2, 1)
    check("H4 quarantine-isolates", "valid",
          r1[0] == "refuse" and r2[0] == "ok", f"quarantined={r1}, peer={r2}")

    # H5: tiers — Believed-only irreversible denied; Certified+Active allowed.
    sup2 = S.Supervisor()
    d1 = sup2.decide({"irreversible": True}, {**env, "tier": "Believed"}, man)
    d2 = sup2.decide({"irreversible": True}, {**env, "tier": "Certified"}, man)
    check("H5 tiers-enforced", "valid", d1[0] == "deny" and d2[0] == "permit",
          f"believed={d1}, certified={d2}")

    # H6: revoke stops new acts; in-flight drains; side effects need re-auth.
    p3 = S.make_permit(a, 1, "Certified")
    started = S.act(a, p3, 1)
    S.revoke_permit(p3)
    r_new = S.act(a, p3, 1)  # same epoch: isolate revocation from epoch checks
    check("H6 revoke-stops-new", "valid", r_new == ("refuse", "revoked"), str(r_new))
    check("H6 existing-invocation-drains", "valid",
          S.act(a, p3, 1, invocation=started[1])[0] == "ok")
    check("H6 drain-cannot-create-effect", "valid",
          S.act(a, p3, 1, invocation=started[1], side_effect=True)[0] == "refuse")
    S.complete(started[1])
    check("H6 completed-cannot-drain", "valid",
          S.act(a, p3, 1, invocation=started[1])[0] == "refuse")
    live = S.make_permit(a, 1, "Certified")
    r_fx = S.act(a, live, 1, side_effect=True, reauthorized=True)
    check("H6 side-effect-needs-reauth", "valid", r_fx == ("refuse", "reauth-required"),
          str(r_fx))
    boundary = S.make_permit(a, 1, "Certified")
    r_fx2 = S.act(a, live, 1, side_effect=True, reauthorized=boundary)
    check("H6 reauthorized-side-effect", "valid", r_fx2[0] == "ok", str(r_fx2))

    # H7: resources — overdraft and double-spend rejected (ledger sketch).
    ledger = {"budget": 10}
    def allocate(n):
        if n > ledger["budget"]:
            return ("deny", "overdraft")
        ledger["budget"] -= n
        return ("ok", ledger["budget"])
    r_ok = allocate(4)
    r_no = allocate(7)
    check("H7 no-overdraft", "valid", r_ok[0] == "ok" and r_no[0] == "deny",
          f"ledger={ledger}")
    spent = {"x": True}
    def allocate_id(i):
        if i in spent:
            return ("deny", "double-spend")
        spent[i] = True
        return ("ok", None)
    check("H7 no-double-spend", "defective",
          allocate_id("x")[0] == "deny", "re-allocation refused")

    # H8: versions — cross-version assembly and stale manifests refused.
    stale = S.StaleCalculator()
    artifact_registry = {stale.instance_id: (S.StaleCalculator, "v1"),
                         a.instance_id: (S.CalculatorV1, "v1")}
    check("H8 registered-artifact-accepted", "valid",
          S.admit_provider(a, artifact_registry)[0] == "ok")
    check("H8 version-identity", "defective",
          S.admit_provider(stale, artifact_registry)[0] == "refuse",
          "admission rejects a version inconsistent with the trusted registry")
    sup8 = S.Supervisor()
    env8 = dict(env, contract="arithmetic", version="v2", tier="Certified")
    man8 = {"contracts": {"arithmetic": ["v1"]}, "epoch": 3}
    check("H8 unlisted-version-denied", "valid",
          sup8.decide({"irreversible": False}, env8, man8)[0] == "deny",
          "v2 not in manifest pinned to [v1] -> deny")

    # H9: schema validation of a stub call via gate1_checks (C1 wiring).
    d09 = gc.D09.read_text(encoding="utf-8")
    schemas, errs = gc.collect_schemas(d09)
    types, _ = gc.extract_types(d09)
    sigs, _ = gc.extract_predicates(d09)
    bad = dict(schemas["OBSERVE"])
    bad["preconditions"] = ["source_declared(news_source)"]
    problems = gc.validate_schema("OBSERVE", bad, types, sigs)
    check("H9 unknown-arg-rejected", "defective", len(problems) > 0,
          f"validator flagged: {problems}" if problems else "NOT flagged")

    # Indeterminate example: contract permits either outcome.
    check("H0 nondeterministic-open", "valid", None,
          "scheduler tie-break unspecified — recorded, not counted")

    passed = [n for n, k, v, _ in results if v is True]
    failed = [n for n, k, v, _ in results if v is False]
    indet = [n for n, k, v, _ in results if v is None]
    print(f"\n{len(passed)}/{len(passed) + len(failed)} decisive checks pass; "
          f"{len(indet)} indeterminate (recorded, not counted)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(run())
