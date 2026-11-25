"""Run the W2 heterogeneous preregistration (Doc 07 section 7.18, L2 only).

    py tools/run_heterogeneous.py docs/results/2026-11-25T-heterogeneous [seed ...]

Refuses to run unless the preregistration matches its recorded digest and
the preregistration, this runner and the freeze manifest are committed
unchanged at HEAD, and every pinned execution file, artifact identity and
configuration matches the freeze manifest. Refuses to overwrite seed
outputs or abort records; an authorized rerun needs an explicit
amendment and a separate output location. Infrastructure aborts yield
a non-zero process status. Confirmatory execution requires a reviewed
preregistration; this runner executes only a frozen one. Results are
committed separately and never edited.
"""
import hashlib
import importlib.metadata
import json
import random
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from brainos import Refused, Runtime  # noqa: E402
from brainos import emergence  # noqa: E402
from brainos import ecology  # noqa: E402

RESULTS = ROOT / "docs" / "results" / "2026-11-25T-heterogeneous"
PREREG = RESULTS / "PREREGISTRATION.md"
PREREG_SHA256 = "02d20e2a408f69168bebd9a5391cc8a1636f3cd78943beaf9d28fe359e273a12"
SEEDS = (21, 22, 23)
PROFILE = "inprocess"
EXPECTED_ARMS = ("fixed", "neural", "coordinated")
ABSTAIN_TOKEN = "ABSTAIN"
OP_ALIASES = {"sum": "sum", "add": "sum"}
FROZEN = RESULTS / "FROZEN.json"
VERDICT_BUDGET = 100
VALUES = {"nl-arith": dict(per_request=10, late_penalty=4, floor_ns=300 * 10 ** 9)}
DEV_ATTEMPTS = 2000
EXEC_ATTEMPTS = 4000
DRAW_TIMEOUT = 30.0
TASK_TIMEOUT = 60.0
UNIT_NS = 10 ** 6
N_ADMIT, K_ADMIT = 3, 2
ADMISSION_CASES = [("Add up 2 and 3.", '{"operation": "sum", "values": [2, 3]}'),
                   ("Add up 10 and 4.", '{"operation": "sum", "values": [10, 4]}')]
PROMPT_VERSION = "qwen-probe-sum-v1"
PROMPT_TEXT = ('Request: "Add up 4 and 6."\n{"operation": "sum", "values": [4, 6]}\n'
               'Request: "Please add 1 and 9."\n{"operation": "sum", "values": [1, 9]}\n'
               'Request: "{input}"\n')
SAMPLING = {"temperature": 0.0, "top_p": 1.0, "max_tokens": 32, "seed": 11}
QWEN_COST = {"attempts": 30}
QWEN_SCHEDULE = dict(initialization=30, inference=5, transport=1, memory=1500,
                     accelerator=0, overhead=1)
QWEN_UNITS = dict(initialization="seconds", inference="seconds", transport="attempts",
                  memory="MB", accelerator="seconds", overhead="attempts")
QWEN_MEASURED = dict(initialization="adapter", inference="adapter", transport="kernel",
                     memory="adapter", accelerator="adapter", overhead="kernel")


def digest_of(path):
    return hashlib.sha256(Path(path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def committed_unchanged(path):
    rel = Path(path).resolve().relative_to(ROOT).as_posix()
    try:
        head = subprocess.run(["git", "show", f"HEAD:{rel}"], cwd=ROOT,
                              capture_output=True, check=True).stdout
    except subprocess.CalledProcessError:
        return False
    return head.replace(b"\r\n", b"\n") == Path(path).read_bytes().replace(b"\r\n", b"\n")


def verify_frozen():
    actual = digest_of(PREREG)
    if actual != PREREG_SHA256:
        raise SystemExit(f"preregistration digest {actual} != {PREREG_SHA256}; refusing to run")
    for path in (PREREG, Path(__file__)):
        if not committed_unchanged(path):
            raise SystemExit(f"{Path(path).name} is not committed unchanged at HEAD; refusing to run")
    if not FROZEN.exists():
        raise SystemExit(f"{FROZEN.name} is missing; refusing to run")
    if not committed_unchanged(FROZEN):
        raise SystemExit(f"{FROZEN.name} is not committed unchanged at HEAD; refusing to run")
    expect = json.loads(FROZEN.read_text(encoding="utf-8"))
    if expect.get("preregistration_sha256") != PREREG_SHA256:
        raise SystemExit(f"{FROZEN.name} does not match the frozen preregistration; refusing to run")
    return check_frozen(expect)


def freeze_files():
    """Source files bound to the frozen execution boundary (B37).

    The whole kernel package is bound: any kernel change can alter the
    frozen execution. Unrelated repository changes (docs, tests, other
    tools, dashboards) are allowed precisely because they are not listed
    here and cannot change the pinned behavior.
    """
    files = [Path(__file__).resolve()]
    files += sorted((ROOT / "src" / "brainos").glob("*.py"))
    files.append(ROOT / "implementations" / "qwen_adapter.py")
    files.append(ROOT / "src" / "models" / "manifest.json")
    return files


def current_freeze_state():
    """Reproducible state of the execution boundary (B37)."""
    files = {}
    for path in freeze_files():
        files[path.relative_to(ROOT).as_posix()] = digest_of(path)
    manifest = json.loads((ROOT / "src" / "models" / "manifest.json").read_text(encoding="utf-8"))
    artifact = next(a for a in manifest["artifacts"] if a["id"] == "Qwen3-0.6B")
    model_dir = ROOT / "src" / "models" / "Qwen3-0.6B"
    model_state = hash_model_dir(model_dir)
    model_state.update(id="Qwen3-0.6B", digest_sha256=artifact["digest_sha256"])
    return dict(
        files=files,
        model=model_state,
        prompt=dict(version=PROMPT_VERSION,
                    sha256=hashlib.sha256(PROMPT_TEXT.encode("utf-8")).hexdigest()),
        sampling=dict(SAMPLING), admission=dict(n=N_ADMIT, k=K_ADMIT),
        seeds=list(SEEDS),
        packages={name: importlib.metadata.version(name)
                  for name in ("torch", "transformers")})


def check_frozen(expect):
    """Refuse unless the live execution boundary matches the frozen state.

    Every pinned source file digest must match; the model, tokenizer
    directory listing, prompt, sampling, admission, seeds and runtime
    package versions must equal the frozen values. Extra untracked source
    files do not invalidate the freeze: they cannot alter the behavior
    of the pinned files. Any change to a relevant file or artifact
    identity refuses; the approved unchanged configuration is accepted.
    """
    actual = current_freeze_state()
    for rel, digest in expect.get("files", {}).items():
        if actual["files"].get(rel) != digest:
            raise SystemExit(f"freeze mismatch: {rel} changed; refusing to run")
    for section in ("model", "prompt", "sampling", "admission", "seeds", "packages"):
        if actual.get(section) != expect.get(section):
            raise SystemExit(f"freeze mismatch: {section} changed; refusing to run")
    return actual


def gen_stream(seed):
    rng = random.Random(seed)
    demands = []

    def add(split, context, value, expected):
        demands.append(dict(idx=len(demands), split=split, context=context, value=value,
                            expected=expected))

    for _ in range(2):
        a, b = rng.randint(0, 99), rng.randint(0, 99)
        add("calibration", "canonical", f"Add up {a} and {b}.",
            {"operation": "sum", "values": [a, b]})
    a, b = rng.randint(0, 99), rng.randint(0, 99)
    add("calibration", "irregular", f"Please add {a} and {b} together.",
        {"operation": "sum", "values": [a, b]})
    a, b = rng.randint(0, 99), rng.randint(0, 99)
    add("calibration", "irregular", f"Can you add {a} to {b}?",
        {"operation": "sum", "values": [a, b]})
    for _ in range(2):
        a, b = rng.randint(0, 99), rng.randint(0, 99)
        add("held-out", "canonical", f"add up {a},{b}",
            {"operation": "sum", "values": [a, b]})
    a, b = rng.randint(0, 99), rng.randint(0, 99)
    add("held-out", "irregular", f"{a} + {b} = ?",
        {"operation": "sum", "values": [a, b]})
    a, b, c = rng.randint(0, 99), rng.randint(0, 99), rng.randint(0, 99)
    add("held-out", "irregular", f"Add up the numbers {a}, {b} and {c}.",
        {"operation": "sum", "values": [a, b, c]})
    return demands


def interpret(output, expected):
    """Independent evaluator: strict typed-IR match, no coercion (B35).

    Returns (ok, reason). The declared abstention token is recorded
    separately from malformed output and incorrect interpretation. The
    operation must be a string from the frozen alias set (unhashable
    values cannot satisfy membership); the operand list must contain
    exact integers -- bool and float are rejected even where Python
    equality would accept them. Unexpected structures are rejected,
    never repaired. Reasons: match, abstained, unparseable,
    not-an-object, bad-shape, unhashable-operation, unknown-operation,
    bad-values, mismatch.
    """
    if isinstance(output, str) and output.strip() == ABSTAIN_TOKEN:
        return False, "abstained"
    try:
        parsed = json.loads(output)
    except (ValueError, TypeError):
        return False, "unparseable"
    if not isinstance(parsed, dict):
        return False, "not-an-object"
    if set(parsed) != {"operation", "values"}:
        return False, "bad-shape"
    op = parsed.get("operation")
    try:
        hash(op)
    except TypeError:
        return False, "unhashable-operation"
    if not isinstance(op, str) or op not in OP_ALIASES:
        return False, "unknown-operation"
    values = parsed.get("values")
    if (not isinstance(values, list) or not values
            or any(isinstance(v, bool) or type(v) is not int for v in values)):
        return False, "bad-values"
    if values != expected["values"] or OP_ALIASES[op] != "sum":
        return False, "mismatch"
    return True, "match"


def hash_model_dir(model_dir):
    """Content digests of every execution-relevant artifact (B37).

    Filenames alone cannot detect a swapped tokenizer or configuration:
    every file under the model directory is hashed and the total byte
    count recorded. Weight payloads are included; the one-time hashing
    cost is the price of a falsifiable freeze.
    """
    files, total = {}, 0
    for path in sorted(model_dir.rglob("*")):
        if not path.is_file():
            continue
        digest = hashlib.sha256()
        with open(path, "rb") as handle:
            for chunk in iter(lambda: handle.read(1 << 20), b""):
                digest.update(chunk)
        rel = path.relative_to(model_dir).as_posix()
        files[rel] = digest.hexdigest()
        total += path.stat().st_size
    return dict(files=files, bytes_total=total)


def qwen_launcher():
    manifest = json.loads((ROOT / "src" / "models" / "manifest.json").read_text(encoding="utf-8"))
    digest = next(a["digest_sha256"] for a in manifest["artifacts"] if a["id"] == "Qwen3-0.6B")
    # Fail closed at the execution boundary: the manifest digest must match
    # the frozen model identity whenever a freeze manifest exists (B37).
    if FROZEN.exists():
        frozen_digest = json.loads(FROZEN.read_text(encoding="utf-8")).get(
            "model", {}).get("digest_sha256")
        if frozen_digest is not None and digest != frozen_digest:
            raise SystemExit(f"model manifest digest {digest[:16]} does not match "
                             f"frozen {str(frozen_digest)[:16]}; refusing to run")
    return ({"qwen3-lm": [sys.executable, str(ROOT / "implementations" / "qwen_adapter.py"),
                           "--model-dir", str(ROOT / "src" / "models" / "Qwen3-0.6B"),
                           "--artifact", digest,
                           "--prompt-text", PROMPT_TEXT,
                           "--prompt-version", PROMPT_VERSION]}, digest)


def _terminal(rt, task):
    """True when a task reached a terminal state (safe to meter)."""
    try:
        return rt.tasks.task(task, "dev")["state"] in emergence.TERMINAL_TASKS
    except Refused:
        return False


def run_task(rt, capability, provider, value, budget, timeout=TASK_TIMEOUT):
    """Create, authorize and run one member task, always returning its id.

    Returns (task, output, invocation, error). On failure output is None
    and error carries the refusal; the invocation is returned when the
    task record has one, so failed, timed-out and cancelled work keeps
    its measured cost. The task id is always returned so every terminal
    task stays inside the accounting boundary (B33).
    """
    task = rt.tasks.create_member_task("dev", capability, provider, value, budget, timeout=timeout)
    try:
        output = rt.tasks.run_task(task, rt.tasks.authorize(task, "dev"), "dev")
    except Refused as exc:
        invocation = None
        try:
            record = rt.tasks.task(task, "dev")
        except Refused:
            return task, None, None, str(exc)[:200]
        if record.get("invocation") is not None:
            try:
                invocation = rt.tasks.invocation(record["invocation"], "dev")
            except Refused:
                invocation = None
        return task, None, invocation, str(exc)[:200]
    invocation = rt.tasks.invocation(rt.tasks.task(task, "dev")["invocation"], "dev")
    return task, output, invocation, None


def validation_attempts_of(store, capability, provider):
    """Total validation draws over every membership candidate for a provider.

    Admitted, rejected and abstained candidates are all summed: failed
    admission consumes durable reservations and invocation records, and
    must not disappear from accounting (B33).
    """
    total = 0
    for cand in store.find("candidate"):
        if cand.get("kind") == "membership" and cand.get("bindings") == {capability: provider}:
            total += cand.get("validation_attempts", 0) or 0
    return total


def validation_cost_of(rt, cap, provider, cost_attempts):
    """Validation spend in attempts over all candidates (0 if none)."""
    return validation_attempts_of(rt.store, cap, provider) * cost_attempts


def _run_seed(seed, outdir, status=None):
    path = outdir / f"seed-{seed}.json"
    if path.exists():
        raise SystemExit(f"{path.name} already exists; results are never overwritten")
    abort_path = outdir / f"seed-{seed}.aborted.json"
    if abort_path.exists():
        raise SystemExit(f"{abort_path.name} already exists; abort records are never "
                         "overwritten. An authorized rerun needs an explicit amendment "
                         "and a separate output location")
    status = {} if status is None else status
    stream = gen_stream(seed)
    adapters, digest = qwen_launcher()
    out = dict(seed=seed, profile=PROFILE, prompt_version=PROMPT_VERSION,
               prompt_text=PROMPT_TEXT, sampling=SAMPLING,
               admission=dict(n=N_ADMIT, k=K_ADMIT), stream=stream)
    with tempfile.TemporaryDirectory() as workdir:
        rt = Runtime(Path(workdir) / "c.db", profile=PROFILE, external_adapters=adapters)
        try:
            status["phase"] = "admission"
            cap = rt.population.define("nl-arith", "text", "text", ADMISSION_CASES)
            det = rt.registry.register("parse_nl_sum")
            qwen = rt.registry.register_external(
                implementation="qwen3-lm", input="text", output="text", capability="nl-arith",
                cost={"attempts": 30}, cost_schedule=dict(QWEN_SCHEDULE),
                cost_units=dict(QWEN_UNITS), measured_by=dict(QWEN_MEASURED), artifact=digest,
                artifact_algorithm="sha256",
                identities=dict(model="Qwen/Qwen3-0.6B", runtime="qwen-adapter/cpu-torch",
                                tokenizer="Qwen3-0.6B", prompt_template=PROMPT_VERSION),
                sampling=dict(SAMPLING), nondeterministic=True,
                admission=dict(n=N_ADMIT, k=K_ADMIT))
            out["qwen_provider"] = qwen
            val = rt.resources.create_budget("dev", {"attempts": 2000})
            exe = rt.resources.create_budget("dev", {"attempts": 4000})
            try:
                out["deterministic_admitted"] = bool(rt.population.admit(
                    cap, det, budget=val, principal="dev"))
            except Refused as exc:
                out["deterministic_admitted"] = False
                out["deterministic_admission_error"] = str(exc)[:300]
            try:
                rt.population.admit(cap, qwen, budget=val, principal="dev")
                out["qwen_admitted"] = True
                candidate = next(m for m in rt.store.find("member")
                                 if m["id"] == f"{cap}|{qwen}")["candidate"]
                out["qwen_admission_evidence"] = rt.store.get("candidate", candidate).get(
                    "admission_evidence")
            except Refused as exc:
                out["qwen_admitted"] = False
                out["qwen_admission_error"] = str(exc)[:300]
            status["phase"] = "setup"
            sum_cap = rt.population.define("w2-sum", "integers", "integer", [([1, 2], 3)])
            sum_provider = rt.registry.register("sum")
            rt.population.admit(sum_cap, sum_provider, budget=val, principal="dev")
            members = {}
            if out.get("deterministic_admitted"):
                members["deterministic"] = det
            if out.get("qwen_admitted"):
                members["qwen"] = qwen
            table, tasks_by_arm = [], {"fixed": [], "neural": [], "coordinated": []}
            sum_tasks_by_arm = {"fixed": [], "neural": [], "coordinated": []}
            status["phase"] = "calibration"
            for demand in [d for d in stream if d["split"] == "calibration"]:
                row = dict(idx=demand["idx"], context=demand["context"], costs={},
                           overhead={}, outputs={}, correct={})
                for label, pid in members.items():
                    arm = "fixed" if label == "deterministic" else "neural"
                    task, output, invocation, error = run_task(rt, cap, pid, demand["value"], exe)
                    if error is not None:
                        row["outputs"][label] = f"REFUSED: {error}"
                        row["correct"][label] = False
                        if _terminal(rt, task):
                            tasks_by_arm[arm].append(task)
                        continue
                    ok, _ = interpret(output, demand["expected"])
                    row["outputs"][label] = output
                    row["correct"][label] = ok
                    row["costs"][label] = invocation["compute_ns"]
                    row["overhead"][label] = max(0, invocation["total_ns"]
                                                - invocation["compute_ns"])
                    tasks_by_arm[arm].append(task)
                table.append(row)
            calibration = [dict(context=r["context"], costs={m: (0 if r["correct"].get(m) else 1)
                                                             for m in members}) for r in table]
            selection = ecology.offline_selection(calibration) if calibration else {}
            out["selection"] = selection
            status["phase"] = "held-out"
            for demand in [d for d in stream if d["split"] == "held-out"]:
                for arm, chooser in (("fixed", lambda d: "deterministic"),
                                     ("neural", lambda d: "qwen" if "qwen" in members else None),
                                     ("coordinated", lambda d: selection.get(d["context"]))):
                    label = chooser(demand)
                    if label is None or label not in members:
                        out.setdefault("skipped", []).append(dict(
                            idx=demand["idx"], arm=arm,
                            reason=("no-provider-selected" if label is None
                                    else f"unavailable-member:{label}")))
                        continue
                    pid = members[label]
                    entry = dict(idx=demand["idx"], arm=arm, member=label,
                                 correct=False, served=False)
                    task, output, invocation, error = run_task(rt, cap, pid, demand["value"], exe)
                    if error is not None:
                        entry.update(reason=error)
                        if invocation is not None:
                            entry.update(compute_ns=invocation["compute_ns"],
                                         total_ns=invocation["total_ns"])
                        out.setdefault("runs", []).append(entry)
                        if _terminal(rt, task):
                            tasks_by_arm[arm].append(task)
                        continue
                    ok, why = interpret(output, demand["expected"])
                    entry.update(output=output, eval=why,
                                 compute_ns=invocation["compute_ns"],
                                 total_ns=invocation["total_ns"])
                    late = invocation["total_ns"] > VALUES["nl-arith"]["floor_ns"]
                    if ok:
                        try:
                            values = json.loads(output)["values"]
                            stask, soutput, sinv, serror = run_task(
                                rt, sum_cap, sum_provider, values, exe)
                            if serror is not None:
                                entry.update(executed=None,
                                             execution_error=serror)
                                if _terminal(rt, stask):
                                    sum_tasks_by_arm[arm].append(stask)
                            else:
                                expected = sum(demand["expected"]["values"])
                                entry.update(executed=soutput, expected=expected,
                                             correct=bool(soutput == expected))
                                entry["compute_ns"] += sinv["compute_ns"]
                                entry["total_ns"] += sinv["total_ns"]
                                sum_tasks_by_arm[arm].append(stask)
                        except (ValueError, KeyError, TypeError) as exc:
                            entry.update(executed=None, correct=False,
                                         execution_error=str(exc)[:200])
                    else:
                        entry.update(eval=why)
                    # Served means both correct interpretation AND correct
                    # deterministic execution (integrity requirement).
                    entry["served"] = bool(ok and entry.get("correct"))
                    entry["late"] = bool(late and entry.get("served"))
                    tasks_by_arm[arm].append(task)
                    out.setdefault("runs", []).append(entry)
            status["phase"] = "accounting"
            # B33: validation spend is unconditional. Rejected admission
            # still consumed durable reservations and draws; the kernel now
            # records validation_attempts on rejected candidates, and the
            # sum below covers every membership candidate.
            validation_costs = {
                "deterministic": validation_cost_of(rt, cap, det, 1),
                "qwen": validation_cost_of(rt, cap, qwen, 30),
            }
            out["validation_costs"] = validation_costs
            out["table"] = table
            out["setup"] = build_setup(out, table, members, validation_costs,
                                       validation_attempts_of(rt.store, cap, det),
                                       validation_attempts_of(rt.store, cap, qwen))
            status["phase"] = "metering"
            out["meters"] = {}
            for arm, tids in tasks_by_arm.items():
                if not tids:
                    continue
                try:
                    out["meters"][arm] = emergence.measure(rt.store, cap, tids,
                                                           external_adapters=adapters)
                except Refused as exc:
                    out.setdefault("meter_failures", {})[arm] = str(exc)
            out["sum_meters"] = {}
            for arm, tids in sum_tasks_by_arm.items():
                if not tids:
                    continue
                try:
                    out["sum_meters"][arm] = emergence.measure(rt.store, sum_cap, tids)
                except Refused as exc:
                    out.setdefault("meter_failures", {})[f"sum-{arm}"] = str(exc)
            out["nonattainment"] = build_nonattainment(out)
            status["phase"] = "verdict"
            try:
                # The preregistration declares the organizational-assessment
                # budget (100 case evaluations); the verdict enforces it.
                out["verdict"] = emergence.organizational_verdict(
                    rt.store, cap, external_adapters=adapters,
                    development_budget=VERDICT_BUDGET)
            except Refused as exc:
                out["verdict"] = dict(verdict="no-members", error=str(exc)[:200])
            out["nov"] = nov_by_arm(out)
            out["oracle"] = oracle_result(out)
            out["hypotheses"] = check_hypotheses(out)
            out["head"] = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                         capture_output=True, text=True).stdout.strip()
        finally:
            rt.close()
    out["preregistration"] = PREREG_SHA256
    path.write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    return out


def build_setup(out, table, members, validation_costs, det_attempts, qwen_attempts):
    """Explicit economic boundary for admission, calibration and execution (B34).

    Calibration demands are the selection evidence: the fixed and neural
    arms pay their own calibration through their metered tasks, while the
    coordinated arm pays the full calibration table of both members (its
    selection requires the complete evidence). Shared initialization
    (capability definition, budget creation) carries no per-demand cost
    and is not amortized to any arm.
    """
    calibration = {}
    for row in table:
        for label in members:
            slot = calibration.setdefault(label, dict(demands=0, compute_ns=0,
                                                      overhead_ns=0))
            if label in row.get("costs", {}):
                slot["demands"] += 1
                slot["compute_ns"] += row["costs"][label]
            if label in row.get("overhead", {}):
                slot["overhead_ns"] += row["overhead"][label]
    return dict(
        boundary=("admission, calibration, held-out execution and assessment are "
                  "charged to the arm(s) requiring the evidence; coordinated pays "
                  "the full calibration table of both members; shared initialization "
                  "is not amortized; the oracle uses held-out demands only with zero "
                  "validation/assessment cost"),
        calibration=calibration,
        validation_attempts=dict(deterministic=det_attempts, qwen=qwen_attempts),
        validation_costs=dict(validation_costs))


def build_nonattainment(out):
    """Explicit nonattainment outcomes for arms without meters (B32).

    An unavailable provider or empty organization produces a recorded
    outcome with its reason -- it never silently disappears. Arms missing
    from both meters and nonattainment are left unexplained so H1 fails.
    """
    nonattained = {}
    skipped = {}
    for skip in out.get("skipped", []):
        skipped.setdefault(skip["arm"], []).append(skip["idx"])
    for arm in EXPECTED_ARMS:
        if arm in out.get("meters", {}) or arm in out.get("meter_failures", {}):
            continue
        reasons = []
        if arm == "neural" and not out.get("qwen_admitted"):
            reasons.append(out.get("qwen_admission_error") or "qwen not admitted")
        if arm == "fixed" and not out.get("deterministic_admitted"):
            reasons.append(out.get("deterministic_admission_error")
                           or "deterministic provider not admitted")
        if arm == "coordinated" and not out.get("selection"):
            reasons.append("empty selection: no member chosen for any held-out demand")
        n_skip = len(skipped.get(arm, []))
        if n_skip:
            reasons.append(f"{n_skip} demands skipped without execution")
        if reasons:
            nonattained[arm] = dict(reason="; ".join(reasons), skipped=n_skip)
    return nonattained


def arm_nov(out, arm):
    report = out["meters"][arm]
    native = report["R"]
    compute = native["compute_ns"] / UNIT_NS
    overhead = native["overhead_ns"] / UNIT_NS
    extra = out.get("sum_meters", {}).get(arm)
    if extra is not None:
        compute += extra["R"]["compute_ns"] / UNIT_NS
        overhead += extra["R"]["overhead_ns"] / UNIT_NS
    if arm == "coordinated":
        # Coordinated selection requires the full calibration table of
        # both members, so it pays the complete calibration evidence cost
        # (B34). Fixed and neural pay their own calibration through their
        # metered calibration tasks.
        for slot in out.get("setup", {}).get("calibration", {}).values():
            compute += slot.get("compute_ns", 0) / UNIT_NS
            overhead += slot.get("overhead_ns", 0) / UNIT_NS
    validation = sum(out["validation_costs"].values()) if arm == "coordinated" else 0.0
    if arm == "fixed":
        validation += out["validation_costs"].get("deterministic", 0)
    if arm == "neural":
        validation += out["validation_costs"].get("qwen", 0)
    costs = dict(compute=compute, overhead=overhead, construction=0.0,
                 validation=float(validation), assessment=native["assessment_ns"] / UNIT_NS,
                 maintenance=float(native["maintenance_units"]))
    by_idx = {}
    for demand in out["stream"]:
        by_idx[demand["idx"]] = demand
    served, native_compute_ns, native_total_ns = [], 0, 0
    for entry in out.get("runs", []):
        # Outcomes are attributed by experimental arm, never by provider
        # name: coordinated executions serve the coordinated arm whichever
        # member served them (B31).
        if entry.get("arm") != arm:
            continue
        demand = by_idx[entry["idx"]]
        if demand["split"] != "held-out":
            continue
        native_compute_ns += entry.get("compute_ns", 0) or 0
        native_total_ns += entry.get("total_ns", 0) or 0
        if entry.get("served") and entry.get("correct"):
            served.append(dict(contract="nl-arith", late=bool(entry.get("late", False))))
    table = {"nl-arith": dict(per_request=VALUES["nl-arith"]["per_request"],
                              late_penalty=VALUES["nl-arith"]["late_penalty"])}
    result = emergence.net_value([dict(served=served, costs=costs)], table)
    return dict(value=result["total"] + sum(costs.values()), costs=costs,
                net=result["total"], served=len(served),
                native=dict(compute_ns=native_compute_ns, total_ns=native_total_ns,
                            runs=len([e for e in out.get("runs", []) if e.get("arm") == arm]),
                            skipped=len([s for s in out.get("skipped", [])
                                         if s.get("arm") == arm])))


def nov_by_arm(out):
    nov = {arm: arm_nov(out, arm) for arm in out.get("meters", {})}
    for arm, record in out.get("nonattainment", {}).items():
        if arm not in nov:
            nov[arm] = dict(value=0.0, costs={name: 0.0 for name in emergence.NOV_COSTS},
                            net=0.0, served=0, nonattained=True,
                            reason=record.get("reason", ""),
                            native=dict(compute_ns=0, total_ns=0, runs=0,
                                        skipped=record.get("skipped", 0)))
    return nov


def oracle_result(out):
    by_idx = {}
    for demand in out["stream"]:
        by_idx[demand["idx"]] = demand
    best, total_value, windows = {}, 0.0, []
    for demand in out["stream"]:
        # The oracle uses the declared evaluation horizon: held-out
        # demands only. Calibration is setup evidence, never service (B34).
        if demand["split"] != "held-out":
            continue
        candidates = [e for e in out.get("runs", [])
                      if e["idx"] == demand["idx"] and e.get("correct")]
        if not candidates:
            continue
        winner = min(candidates, key=lambda e: e["compute_ns"])
        best[demand["idx"]] = winner
        total_value += VALUES["nl-arith"]["per_request"]
    compute = sum(e["compute_ns"] for e in best.values()) / UNIT_NS
    overhead = sum(max(0, e["total_ns"] - e["compute_ns"]) for e in best.values()) / UNIT_NS
    costs = dict(compute=compute, overhead=overhead, construction=0.0, validation=0.0,
                 assessment=0.0, maintenance=0.0)
    return dict(windows=[dict(value=total_value, costs=costs)], total=total_value - sum(costs.values()),
                demands_covered=len(best))


def check_hypotheses(out):
    checks = {}
    # B32: the complete expected arm set is required. An arm with a meter
    # or an explicit nonattainment record is accounted; a silently missing
    # arm fails completeness.
    metered = [a for a in EXPECTED_ARMS if a in out.get("meters", {})]
    explained = [a for a in EXPECTED_ARMS if a in out.get("nonattainment", {})]
    missing = [a for a in EXPECTED_ARMS if a not in out.get("meters", {})
               and a not in out.get("nonattainment", {})]
    checks["H1"] = dict(passed=not out.get("meter_failures") and not missing,
                        meter_failures=out.get("meter_failures", {}), arms=metered,
                        nonattained=explained, missing=missing)
    try:
        for arm, data in out.get("meters", {}).items():
            assert set(data["R"]) >= {"compute_ns", "overhead_ns"}
        # H2 requires the complete expected NOV arm set, including
        # explicit nonattainment accounting: a nonattained arm carries
        # zero costs and its recorded reason, never a silent omission.
        assert set(out.get("nov", {})) >= set(EXPECTED_ARMS), "incomplete NOV arm set"
        for arm in EXPECTED_ARMS:
            entry = out["nov"][arm]
            assert set(entry["costs"]) == set(emergence.NOV_COSTS)
            if arm in out.get("nonattainment", {}):
                assert entry.get("nonattained"), f"{arm} nonattained without marking"
        assert out["nov"]
        # Every expected demand-arm pair needs an explicit terminal outcome:
        # a runs entry or a skip record (integrity requirement).
        held_ids = [d["idx"] for d in out.get("stream", []) if d["split"] == "held-out"]
        have = {(e.get("idx"), e.get("arm")) for e in out.get("runs", [])}
        have |= {(s.get("idx"), s.get("arm")) for s in out.get("skipped", [])}
        uncovered = [(i, a) for i in held_ids for a in EXPECTED_ARMS
                     if (i, a) not in have]
        assert not uncovered, f"{len(uncovered)} demand-arm pairs without outcome"
        checks["H2"] = dict(passed=True)
    except (AssertionError, KeyError) as exc:
        checks["H2"] = dict(passed=False, error=str(exc)[:200])
    verdict = out.get("verdict", {})
    checks["H3"] = dict(passed=verdict.get("verdict") in
                        ("organizational", "compositional-but-fragile", "redundant",
                         "neither", "inconclusive-budget")
                        and verdict.get("checks_spent", -1) >= 0,
                        verdict=verdict.get("verdict"))
    held_ids = {d["idx"] for d in out["stream"] if d["split"] == "held-out"}
    fixed_ok = sum(1 for e in out.get("runs", [])
                   if e.get("arm") == "fixed" and e["idx"] in held_ids and e.get("correct"))
    coord_ok = sum(1 for e in out.get("runs", [])
                   if e.get("arm") == "coordinated" and e["idx"] in held_ids and e.get("correct"))
    checks["H4"] = dict(passed=coord_ok > fixed_ok, coordinated_correct=coord_ok,
                        fixed_correct=fixed_ok)
    qwen_costs, det_costs = [], []
    for entry in out.get("runs", []):
        if entry.get("served") and entry.get("correct"):
            (qwen_costs if entry.get("member") == "qwen" else det_costs).append(
                entry["compute_ns"])
    qwen_mean = sum(qwen_costs) / len(qwen_costs) if qwen_costs else 0
    det_mean = sum(det_costs) / len(det_costs) if det_costs else 0
    # B36: the comparative ratio needs valid observations from both
    # provider families and a meaningful denominator. Missing evidence is
    # reported as insufficient -- never counted as a pass.
    if det_mean <= 0 or qwen_mean <= 0:
        checks["H5"] = dict(passed=False, qwen_mean_ns=qwen_mean, det_mean_ns=det_mean,
                            reason="insufficient-comparative-evidence")
    else:
        checks["H5"] = dict(passed=bool(qwen_mean / det_mean >= 10),
                            qwen_mean_ns=qwen_mean, det_mean_ns=det_mean,
                            ratio=qwen_mean / det_mean)
    return checks


def run_seeds(outdir, seeds):
    """Run each seed; returns (completed, aborted).

    A completed result or an abort record for a seed refuses execution
    outright (SystemExit): an authorized rerun needs an explicit
    amendment and a separate output location. Infrastructure aborts are
    recorded and counted so the process status reflects them.
    """
    completed, aborted = [], []
    for seed in seeds:
        if seed not in SEEDS:
            raise SystemExit(f"seed {seed} is not preregistered")
        started = time.perf_counter()
        status = {}
        try:
            seed_out = _run_seed(seed, outdir, status=status)
        except (SystemExit, KeyboardInterrupt):
            raise
        except Exception as exc:
            # Infrastructure failures abort the seed with an explicit
            # record -- never a silent replacement, never an overwrite.
            abort_path = outdir / f"seed-{seed}.aborted.json"
            if abort_path.exists():
                raise SystemExit(f"{abort_path.name} already exists; abort records "
                                 "are never overwritten")
            abort = dict(seed=seed, phase=status.get("phase", "unknown"),
                         error=f"{type(exc).__name__}: {exc}"[:500],
                         head=subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                             capture_output=True, text=True).stdout.strip(),
                         preregistration=PREREG_SHA256)
            abort_path.write_text(json.dumps(abort, indent=1), encoding="utf-8")
            print(f"seed {seed} ABORTED in phase {abort['phase']}: "
                  f"{abort['error']}", flush=True)
            aborted.append(seed)
            continue
        print(f"seed {seed}: {time.perf_counter() - started:.1f}s "
              f"hypotheses={[k for k, v in seed_out['hypotheses'].items() if v['passed']]} "
              f"verdict={seed_out['verdict'].get('verdict')} "
              f"nov={ {k: round(v['net'], 1) for k, v in seed_out['nov'].items()} } "
              f"oracle={round(seed_out['oracle']['total'], 1)}", flush=True)
        completed.append(seed)
    return completed, aborted


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] == "--verify-only":
        verify_frozen()
        print(f"frozen: preregistration {PREREG_SHA256[:12]} manifest {FROZEN.name} ok",
              flush=True)
        return 0
    outdir = Path(args[0]) if args else RESULTS
    seeds = [int(a) for a in args[1:]] or list(SEEDS)
    verify_frozen()
    outdir.mkdir(parents=True, exist_ok=True)
    _, aborted = run_seeds(outdir, seeds)
    # Aborted seeds are preserved records, and the process status says so.
    return 1 if aborted else 0


if __name__ == "__main__":
    raise SystemExit(main())
