"""Gate 1 machine verification for BrainOS docs (strict).

Checks structure, types, predicates, coverage, register integrity,
cross-references, and prose-to-schema correspondence. Reports what each
check ESTABLISHES (declarations, not runtime enforcement).
Usage: py tools/gate1_checks.py  (run from Z:\\brainos)
Exit 0 iff all checks pass.
"""
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs" / "current"
D09 = DOCS / "09-cognitive-instruction-architecture.md"
D31 = DOCS / "31-architectural-audit.md"

EXPECTED = ["LEARN", "OBSERVE", "ENCODE", "INFER", "PREDICT", "REVISE",
    "COMPARE", "PROPAGATE", "VALIDATE", "BENCHMARK", "FORK", "CONSOLIDATE",
    "ASSERT", "CHALLENGE", "VERIFY", "RETRACT", "QUARANTINE", "RESTORE",
    "BIND", "SPAWN", "CONNECT", "SNAPSHOT", "COMMIT", "AUTHORIZE", "REVOKE",
    "ACT", "BIRTH", "DIFFERENTIATE", "FUSE", "RETIRE", "RESERVE", "ALLOCATE",
    "RELEASE", "REBIND", "CANCEL", "EMIT", "RECEIVE"]
ID_KEY = "instruction"
PROP_KEYS = ["inputs", "preconditions", "outputs", "state_effects",
    "prohibited_effects", "failure_semantics", "concurrency",
    "resource_accounting", "evidence_requirements"]


class DupKeyLoader(yaml.SafeLoader):
    """YAML loader that raises on duplicate mapping keys."""


def _no_dup(loader, node, deep=False):
    mapping = {}
    for k_node, v_node in node.value:
        k = loader.construct_object(k_node, deep=True)
        if k in mapping:
            raise ValueError(f"duplicate key: {k!r}")
        mapping[k] = loader.construct_object(v_node, deep=True)
    return mapping


DupKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _no_dup)


def find_yaml_blocks(text):
    return re.findall(r"```yaml\n(.*?)```", text, re.DOTALL)


def collect_schemas(text):
    """Return (ordered {name: (dict, index)}, errors). Duplicates detected
    before dict insertion, so nothing is silently overwritten."""
    schemas = {}
    errors = []
    counts = {}
    raws = []
    for i, b in enumerate(find_yaml_blocks(text)):
        try:
            d = yaml.load(b, Loader=DupKeyLoader)
        except Exception as e:  # noqa: BLE001 - report, don't crash
            errors.append(f"block {i}: YAML error: {e}")
            continue
        if not isinstance(d, dict) or "instruction" not in d:
            errors.append(f"block {i}: no instruction mapping")
            continue
        raws.append((d["instruction"], d))
        counts[d["instruction"]] = counts.get(d["instruction"], 0) + 1
    for name in sorted(n for n, c in counts.items() if c > 1):
        errors.append(f"duplicate instruction definition: {name}")
    seen = set()
    for name, d in raws:
        if name not in seen:
            schemas[name] = d
            seen.add(name)
    return schemas, errors


def extract_types(text):
    m = re.search(r"Types registry \(shared by all schemas\):\s*\n(`[^`]+`)",
                  text)
    if not m:
        return set(), ["types registry block not found"]
    return set(re.findall(r"[A-Za-z][A-Za-z0-9_]*", m.group(1))), []


def extract_predicates(text):
    """Map predicate name -> arity from catalog call examples."""
    calls = re.findall(r"- `([a-z_][a-z0-9_]*)\(([^`]*)\)`", text)
    sigs = {}
    errors = []
    for name, argstr in calls:
        args = [a.strip() for a in argstr.split(",") if a.strip()] \
            if argstr.strip() else []
        if name in sigs and sigs[name] != len(args):
            errors.append(f"catalog arity conflict for {name}")
        sigs[name] = len(args)
    if not sigs:
        errors.append("no predicate catalog entries found")
    return sigs, errors


TYPE_RE = re.compile(r"^(?:[A-Za-z][A-Za-z0-9_]*|\[[A-Za-z][A-Za-z0-9_]*\])$")
PRED_RE = re.compile(r"^([a-z_][a-z0-9_]*)\(([^()]*)\)$")
IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def validate_schema(name, s, types, sigs):
    """Return list of structural violations (empty = valid)."""
    errs = []
    if name not in EXPECTED or s.get("instruction") not in EXPECTED:
        errs.append("unknown instruction")
    if s.get("instruction") != name:
        errs.append("instruction name does not match schema key")
    keys = set(s.keys())
    if "instruction" not in keys:
        errs.append("missing instruction key")
    for k in PROP_KEYS:
        if k not in keys:
            errs.append(f"missing key: {k}")
    extra = keys - set(PROP_KEYS) - {"instruction"}
    if extra:
        errs.append(f"unexpected keys: {sorted(extra)}")
    for slot in ("inputs", "outputs"):
        v = s.get(slot, {})
        if not isinstance(v, dict):
            errs.append(f"{slot} must be a mapping")
            continue
        for k, t in v.items():
            if not IDENT_RE.match(str(k)):
                errs.append(f"{slot} bad name: {k}")
            if not (isinstance(t, str) and TYPE_RE.match(t)):
                errs.append(f"{slot}.{k} malformed type expression: {t!r}")
                continue
            base = t.strip("[]")
            if base not in types:
                errs.append(f"{slot}.{k} unknown type: {base}")
    pres = s.get("preconditions", [])
    if not isinstance(pres, list):
        errs.append("preconditions must be a list")
        pres = []
    _ins = s.get("inputs", {})
    allowed_args = set(_ins.keys()) if isinstance(_ins, dict) else set()
    allowed_args |= set(EXPECTED)
    for p in pres:
        m = PRED_RE.match(str(p))
        if not m:
            errs.append(f"malformed predicate expression: {p!r}")
            continue
        pname, argstr = m.group(1), m.group(2)
        if pname not in sigs:
            errs.append(f"unknown predicate: {pname}")
            continue
        args = [a.strip() for a in argstr.split(",") if a.strip()]
        if len(args) != sigs[pname]:
            errs.append(
                f"{pname} arity {len(args)}, catalog declares {sigs[pname]}")
        for a in args:
            if a not in allowed_args:
                errs.append(f"{pname} arg out of scope: {a}")
    for slot in ("prohibited_effects", "failure_semantics",
                 "resource_accounting", "evidence_requirements"):
        v = s.get(slot, [])
        if not isinstance(v, list) or not all(isinstance(x, str) for x in v):
            errs.append(f"{slot} must be a list of tokens")
    if not isinstance(s.get("state_effects"), list):
        errs.append("state_effects must be a list")
    if not isinstance(s.get("concurrency"), dict):
        errs.append("concurrency must be a mapping")
    return errs
INSTRUCTION_NAMES = set(EXPECTED)

SECTION_REF_RE = re.compile(r"(\d{2}) §(\d+\.\d+)")


def check_predicate_args(name, s, sigs):
    """Enforce catalog arity and schema scope for every precondition.
    Returns list of violations."""
    problems = []
    _ins = s.get("inputs", {})
    allowed = (set(_ins.keys()) if isinstance(_ins, dict) and _ins else set()) | INSTRUCTION_NAMES
    for p in s.get("preconditions", []) or []:
        m = PRED_RE.match(str(p))
        if not m:
            problems.append(f"{name}: malformed predicate expression: {p!r}")
            continue
        pname, argstr = m.group(1), m.group(2)
        if pname not in sigs:
            problems.append(f"{name}: undeclared predicate: {pname}")
            continue
        args = [a.strip() for a in argstr.split(",") if a.strip()]
        if len(args) != sigs[pname]:
            problems.append(
                f"{name}: {pname} takes {len(args)} args, catalog declares {sigs[pname]}")
        for a in args:
            if a not in allowed:
                problems.append(f"{name}: {pname} arg out of scope: {a}")
    return problems
STATUS_RE = re.compile(
    r"C[✓~✗\u223c—-]\s*S[✓~✗\u223c—-]\s*I[✓~✗\u223c—-]\s*"
    r"V[✓~✗\u223c—-]\s*E[✓~✗\u223c—-]")


def check_register(text):
    """Validate register rows; return list of error strings."""
    errors = []
    rows = [ln for ln in text.splitlines() if re.match(r"^R-[A-Za-z0-9\-]+ \|", ln)]
    ids = [ln.split(" | ", 1)[0] for ln in rows]
    seen = set()
    for i in ids:
        if i in seen:
            errors.append(f"duplicate requirement ID: {i}")
        seen.add(i)
    if re.search(r"^R-[0-9]+-\*", text, re.M):
        errors.append("wildcard register row present")
    for ln in rows:
        parts = ln.split(" | ")
        if len(parts) < 5:
            errors.append(f"malformed register row (fields): {ln[:60]}")
            continue
        if not STATUS_RE.search(ln):
            errors.append(f"missing status block: {parts[0]}")
        for doc, sec in SECTION_REF_RE.findall(ln):
            p = DOCS / f"{doc}-*.md"
            import glob as _glob
            files = _glob.glob(str(p))
            if not files:
                errors.append(f"{parts[0]}: doc {doc} missing")
                continue
            body = Path(files[0]).read_text(encoding="utf-8")
            if not re.search(rf"^## {re.escape(sec)}(\s|$)", body, re.M):
                errors.append(f"{parts[0]}: section {sec} missing in Doc {doc}")
    return errors


def check_doc_refs(text):
    errors = []
    for r in sorted(set(re.findall(r"Doc (\d{2})", text))):
        import glob as _glob
        if not _glob.glob(str(DOCS / f"{r}-*.md")):
            errors.append(f"unresolved Doc reference: {r}")
    return errors


def check_markdown_integrity(documents):
    """Check every section title, including unnumbered ones; skip code blocks.

    documents maps Path -> Markdown. This is editorial/link integrity, not
    semantic validation of the architecture or the linked external sources.
    """
    errors = []
    for path, body in documents.items():
        if body.count("```") % 2:
            errors.append(f"{path.name}: unbalanced code fence")
        prose = re.sub(r"```.*?```", "", body, flags=re.S)
        seen = set()
        for heading in re.findall(r"^##\s+(.+?)\s*$", prose, re.M):
            normalized = " ".join(heading.casefold().split())
            if normalized in seen:
                errors.append(f"{path.name}: duplicate section title: {heading}")
            seen.add(normalized)
        for target in re.findall(r"\]\(([^)]+)\)", prose):
            if "://" in target or target.startswith("#"):
                continue
            local = target.split("#", 1)[0]
            if local and not (path.parent / local).exists():
                errors.append(f"{path.name}: missing local link: {target}")
        errors.extend(f"{path.name}: {error}" for error in check_doc_refs(prose))
    return errors


def run_all(d09_text, d31_text):
    """Run every check; return (results, failed_names)."""
    out = []

    def rec(name, ok, detail=""):
        out.append((name, bool(ok), detail))
        return ok

    schemas, collect_errors = collect_schemas(d09_text)
    for e in collect_errors:
        pass
    rec("yaml-parseable", not any("YAML error" in e for e in collect_errors),
        "; ".join(collect_errors) if collect_errors else
        f"{len(schemas)} schemas parsed")
    rec("schema-count-exact", len(schemas) == len(EXPECTED) and
        set(schemas) == set(EXPECTED),
        f"found {len(schemas)}, want {len(EXPECTED)}")
    rec("schema-names-unique", not any("duplicate instruction" in e for e in collect_errors))
    types, type_errs = extract_types(d09_text)
    for e in type_errs:
        rec("types-registry-present", False, e)
    if not type_errs:
        rec("types-registry-present", True, f"{len(types)} types registered")
    sigs, sig_errs = extract_predicates(d09_text)
    for e in sig_errs:
        rec("predicate-catalog-present", False, e)
    if not sig_errs:
        rec("predicate-catalog-present", True, f"{len(sigs)} predicates catalogued")
    bad_struct = {}
    for name, s in schemas.items():
        errs = validate_schema(name, s, types, sigs)
        if errs:
            bad_struct[name] = errs
    rec("schema-structure-valid", not bad_struct,
        str(bad_struct)[:400] if bad_struct else "all 9+1 keys, all fields typed")
    unresolved_types = set()
    for name, s in schemas.items():
        for slot in ("inputs", "outputs"):
            v = s.get(slot, {})
            if isinstance(v, dict):
                for t in v.values():
                    for base in re.findall(r"[A-Za-z][A-Za-z0-9_]*", str(t)):
                        if base not in types:
                            unresolved_types.add(f"{name}.{base}")
    rec("types-declared", not unresolved_types,
        f"undeclared={sorted(unresolved_types)}" if unresolved_types
        else "all type refs resolve (declaration only, not runtime typing)")
    unresolved_preds = set()
    for name, s in schemas.items():
        for p in s.get("preconditions", []) or []:
            m = PRED_RE.match(str(p))
            if not m:
                unresolved_preds.add(f"{name}: malformed {p!r}")
            elif m.group(1) not in sigs:
                unresolved_preds.add(f"{name}: undeclared {m.group(1)}")
    rec("predicates-declared", not unresolved_preds,
        f"{sorted(unresolved_preds)}" if unresolved_preds
        else "all predicate refs resolve (declaration only, not enforcement)")
    arg_problems = []
    for name, s in schemas.items():
        arg_problems.extend(check_predicate_args(name, s, sigs))
    rec("predicates-arity-scope-valid", not arg_problems,
        "; ".join(sorted(set(arg_problems)))[:400] if arg_problems
        else "all predicate arities match catalog; all args in schema scope or instruction names")
    reg_errors = check_register(d31_text)
    rec("register-ids-unique", not any("duplicate requirement ID" in e for e in reg_errors),
        f"{len(re.findall(r'^R-[A-Za-z0-9\\-]+', d31_text, re.M))} IDs checked")
    rec("register-no-wildcards", not any("wildcard" in e for e in reg_errors))
    rec("register-rows-wellformed", not [e for e in reg_errors if "malformed" in e or "missing status" in e],
        f"{len(reg_errors)} register errors" if reg_errors else "rows + status blocks valid")
    rec("register-sections-resolve", not [e for e in reg_errors if "missing" in e and "Doc" in e],
        "section refs resolve" if not [e for e in reg_errors if "Doc" in e] else "; ".join(e for e in reg_errors if "Doc" in e)[:300])
    doc_errors = check_doc_refs(d31_text)
    rec("doc-refs-resolve", not doc_errors,
        f"{doc_errors}" if doc_errors else "all Doc refs resolve")
    ab = re.search(r"## 9\.8 .*?(?=## 9\.9)", d09_text, re.DOTALL)
    ab_text = ab.group(0) if ab else ""
    names_in_prose = set(re.findall(
        r"\b(OBSERVE|ENCODE|INFER|PREDICT|REVISE|COMPARE|PROPAGATE|VALIDATE|"
        r"BENCHMARK|FORK|CONSOLIDATE|ASSERT|CHALLENGE|VERIFY|RETRACT|"
        r"QUARANTINE|RESTORE|BIND|SPAWN|CONNECT|SNAPSHOT|COMMIT|AUTHORIZE|"
        r"REVOKE|ACT|BIRTH|DIFFERENTIATE|FUSE|RETIRE|RESERVE|ALLOCATE|"
        r"RELEASE|REBIND|CANCEL|EMIT|RECEIVE|LEARN)\b", ab_text))
    uncovered = sorted(n for n in names_in_prose if n not in schemas)
    rec("prose-schemas-cover", not uncovered,
        f"uncovered={uncovered}" if uncovered else
        "every prose-named instruction schematized (coverage only, not semantic equivalence)")
    act = schemas.get("ACT", {})
    rec("act-declares-reauthorization",
        "reauthorized_at_side_effect_boundary(op)" in
        [str(p) for p in act.get("preconditions", [])],
        "ACT declares side-effect reauthorization (declaration only; enforcement unverified)")
    commit = schemas.get("COMMIT", {})
    conc = commit.get("concurrency", {}) if isinstance(commit.get("concurrency"), dict) else {}
    rec("commit-declares-cas",
        any("compare_and_swap" in k or "compare_and_swap" in str(v)
            for k, v in conc.items()),
        "COMMIT declares CAS publish (declaration only; atomicity unverified)")
    cons = schemas.get("CONSOLIDATE", {})
    rec("consolidate-declares-ancestry",
        "full_ancestry_or_explicit_gap" in
        [str(x) for x in cons.get("evidence_requirements", [])],
        "CONSOLIDATE declares ancestry preservation or labeled repair")
    return out


def main():
    d09 = D09.read_text(encoding="utf-8")
    d31 = D31.read_text(encoding="utf-8")
    results = run_all(d09, d31)
    documents = {p: p.read_text(encoding="utf-8") for p in (ROOT / "docs").rglob("*.md")}
    integrity_errors = check_markdown_integrity(documents)
    results.append(("all-documents-integrity", not integrity_errors,
                    "; ".join(integrity_errors) if integrity_errors else
                    "all section titles, fences, local links and Doc refs checked"))
    failed = [n for n, ok, _ in results if not ok]
    for n, ok, detail in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {n}" + (f" — {detail}" if detail else ""))
    print(f"\n{len(results) - len(failed)}/{len(results)} checks pass")
    print("Scope: declarations and references only. Runtime enforcement, semantic "
          "equivalence, and empirical validity are explicitly NOT established here.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
