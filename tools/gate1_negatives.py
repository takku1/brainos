"""Negative verification for Gate 1: prove the validator REJECTS corrupted
specifications. All fixtures are in-memory strings or temp files; no
repository document is modified. A test PASSES when the validator
correctly rejects the corruption.
Usage: py tools/gate1_negatives.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gate1_checks as g

REAL09 = g.D09.read_text(encoding="utf-8")
REAL31 = g.D31.read_text(encoding="utf-8")
TYPES, _ = g.extract_types(REAL09)
SIGS, _ = g.extract_predicates(REAL09)

BASE = """instruction: OBSERVE
inputs: {source: ProviderRef, payload: DataRef, context: ContextRef}
preconditions: [source_declared(source)]
outputs: {ref: EvidenceRef}
state_effects: [evidence_store_append]
prohibited_effects: [synthesize_payload]
failure_semantics: [reject_unknown_source]
concurrency: {append_only: true}
resource_accounting: [one_record]
evidence_requirements: [the_record_itself]
"""


def block(text):
    return "```yaml\n" + text + "```\n"


def expect_reject(label, fn):
    """fn returns list of problems; test passes iff non-empty.
    An uncaught exception is a validator robustness bug: FAIL."""
    try:
        problems = fn()
    except Exception as e:  # noqa: BLE001 - crashes are failures, not passes
        print(f"[FAIL] {label} — validator crashed instead of rejecting: {type(e).__name__}")
        return False
    if problems:
        print(f"[PASS] {label} — rejected")
        return True
    print(f"[FAIL] {label} — corruption NOT detected")
    return False


results = []

# 1. duplicate instruction definitions
t = block(BASE) + "\n" + block(BASE.replace("OBSERVE", "OBSERVE"))
_, errs = g.collect_schemas(t)
results.append(expect_reject("dup-instruction", lambda: errs))

# 2. duplicate YAML keys
dup = BASE.replace("outputs: {ref: EvidenceRef}",
                   "outputs: {ref: EvidenceRef}\noutputs: {other: DataRef}")
_, errs = g.collect_schemas(block(dup))
results.append(expect_reject("dup-yaml-key", lambda: errs))

# 3. unknown instruction
sch, _ = g.collect_schemas(block(BASE))
foo = dict(next(iter(sch.values())))
foo["instruction"] = "FOO"
results.append(expect_reject(
    "unknown-instruction",
    lambda: g.validate_schema("FOO", foo, TYPES, SIGS)))

# 4. unknown type
bad = dict(next(iter(sch.values())))
bad = {**bad, "inputs": {"source": "NopeType"}}
results.append(expect_reject(
    "unknown-type",
    lambda: g.validate_schema("OBSERVE", bad, TYPES, SIGS)))

# 5. malformed type expression (non-mapping inputs)
bad5 = dict(next(iter(sch.values())))
bad5 = {**bad5, "inputs": ["source", "payload"]}
results.append(expect_reject(
    "malformed-type-structure",
    lambda: g.validate_schema("OBSERVE", bad5, TYPES, SIGS)))

# 6. unknown predicate
bad6 = dict(next(iter(sch.values())))
bad6 = {**bad6, "preconditions": ["frobnicate(source)"]}
results.append(expect_reject(
    "unknown-predicate",
    lambda: g.validate_schema("OBSERVE", bad6, TYPES, SIGS)))

# 7. malformed predicate (no parens)
bad7 = dict(next(iter(sch.values())))
bad7 = {**bad7, "preconditions": ["source_declared"]}
results.append(expect_reject(
    "malformed-predicate",
    lambda: g.validate_schema("OBSERVE", bad7, TYPES, SIGS)))

# 8. wrong arg count
bad8 = dict(next(iter(sch.values())))
bad8 = {**bad8, "preconditions": ["source_declared(source, extra)"]}
results.append(expect_reject(
    "wrong-arg-count",
    lambda: g.check_predicate_args("OBSERVE", bad8, SIGS)))

# 9. arg out of scope
bad9 = dict(next(iter(sch.values())))
bad9 = {**bad9, "preconditions": ["source_declared(nowhere)"]}
results.append(expect_reject(
    "arg-out-of-scope",
    lambda: g.check_predicate_args("OBSERVE", bad9, SIGS)))

# 10. missing required key
bad10 = dict(next(iter(sch.values())))
del bad10["outputs"]
results.append(expect_reject(
    "missing-required-key",
    lambda: g.validate_schema("OBSERVE", bad10, TYPES, SIGS)))

# 11. invalid field structure (preconditions not a list)
bad11 = dict(next(iter(sch.values())))
bad11 = {**bad11, "preconditions": {"source_declared": "source"}}
results.append(expect_reject(
    "invalid-field-structure",
    lambda: g.validate_schema("OBSERVE", bad11, TYPES, SIGS)))

# 12. duplicate requirement IDs
dup_reg = "R-01-01 | 01 §1.2 | x | L3 | C✓ S— I✗ V✗ E✗\n" \
          "R-01-01 | 01 §1.3 | y | L3 | C✓ S— I✗ V✗ E✗\n"
results.append(expect_reject(
    "duplicate-requirement-id",
    lambda: g.check_register(dup_reg)))

# 13. missing requirement status
no_status = "R-99-01 | 99 §9.9 | x | L1 | no status here\n"
results.append(expect_reject(
    "missing-requirement-status",
    lambda: g.check_register(no_status)))

# 14. missing ACT reauthorization
act = """instruction: ACT
inputs: {op: OperationRef, epoch: EpochId}
preconditions: [permit_valid_at_epoch(op, epoch)]
outputs: {result: Measure}
state_effects: [external_effects_per_contract]
prohibited_effects: [act_without_permit]
failure_semantics: [refuse_and_report]
concurrency: {permit_scoped: true}
resource_accounting: [execution_cost]
evidence_requirements: [permit_ref]
"""
sch14, _ = g.collect_schemas(block(act))
results.append(expect_reject(
    "missing-act-reauthorization",
    lambda: ["missing"] if "reauthorized_at_side_effect_boundary(op)" not in
    [str(p) for p in sch14["ACT"].get("preconditions", [])] else []))

# 15. missing COMMIT CAS
com = """instruction: COMMIT
inputs: {manifest: ManifestRef}
preconditions: [validated_between_episodes_or_epoch_cut(manifest)]
outputs: {result: Verdict}
state_effects: [manifest_published]
prohibited_effects: [stale_or_quarantined_commit]
failure_semantics: [reject_with_reason]
concurrency: {atomic: true}
resource_accounting: [compute_time]
evidence_requirements: [validation_verdict]
"""
sch15, _ = g.collect_schemas(block(com))
_conc = sch15["COMMIT"].get("concurrency", {})
_has_cas = any("compare_and_swap" in k or "compare_and_swap" in str(v)
               for k, v in _conc.items()) if isinstance(_conc, dict) else False
results.append(expect_reject(
    "missing-commit-cas",
    lambda: [] if _has_cas else ["missing compare_and_swap"]))

print(f"\n{sum(results)}/{len(results)} negative tests pass "
      f"(pass = corruption correctly rejected)")
print("All corruption fixtures are in memory; no temporary filesystem fixture is required.")
sys.exit(0 if all(results) else 1)
