"""Bounded assimilation by structural factoring and duplicate selection (Doc 24 ASSIMILATE).

Assimilation is not composition: a composite needs its parents, whereas an
assimilation replaces them. The candidate must preserve every parent's
competence, and parents may be made dormant only after the union gate passes.

Developmental side only. This module holds the restricted development context
and never the runtime; publication and recovery are kernel operations that
verify everything they are given.

    nominate  every admissible consolidation from the declared trusted catalogue
    evaluate  isolated execution of parents and candidates (explicit invocation,
              never the ecology wake policy): exact output equality on union,
              held-out and rare sets; declared latency tolerance; downstream
              equality; full-cost break-even within a horizon
    publish   stage and validate replacement memberships and bindings, then the
              kernel's single-transaction commit
    recover   validated bindings (and memberships for stale parents) back to
              parents; the kernel advances the epoch
"""
from dataclasses import dataclass, field
from itertools import product
import math
from statistics import median
from types import SimpleNamespace
import time

from .contracts import Refused, digest, uid
from .devcontext import development_context


@dataclass
class Gate:
    """Declared union-gate parameters (by the capability owners and operator)."""
    tolerance: dict                      # capability -> max candidate/parent answer-latency ratio
    horizon_epochs: float = 50.0         # break-even must occur within this many data epochs
    maintenance_ns_per_byte_epoch: float = 1.0   # declared upkeep of a maintained structure
    min_savings_ns: float = 0.0          # per-epoch savings must exceed this
    resolution_ns: float = 20_000.0      # latency ratios below this median are not measurable
    upkeep_ns_per_provider_epoch: float = 0.0    # declared upkeep of each maintained provider
    confidence_z: float = 1.96           # tolerance applies to the upper bound of the paired ratio
    min_log_sd: float = 0.10             # floor on log-ratio spread (no false certainty from few inputs)
    early_stop_factor: float = 20.0      # abort a candidate pass once its cost exceeds this x parents'
    early_stop_min_inputs: int = 2       # ... after at least this many inputs per capability


@dataclass
class EvaluationSet:
    """Inputs grouped into data epochs; every input carries its capability and set name."""
    epochs: list                         # [[(capability, value, set_name), ...], ...] sharing one dataset
    dependents: dict = field(default_factory=dict)   # role -> [inputs] for downstream checks


class _EarlyStop(Exception):
    pass


def structure_kind(spec):
    """Maintained-structure identity: declared prepare, or an opaque internal structure."""
    if spec.get("prepare"):
        return spec["prepare"]
    return f"internal:{spec['implementation']}" if spec.get("internal_state") else None


class AssimilationSearch:
    def __init__(self, runtime):
        self.ctx = runtime if isinstance(runtime, SimpleNamespace) else development_context(runtime)
        self.session = dict(construction_ns=0, evaluations=0, parent_cache={})

    def _record(self, kind, **body):
        key = uid()
        self.ctx.write("assimilation-trial", key, dict(id=key, kind=kind, **body), "assimilation-trial",
                       trial=key, trial_kind=kind)
        return key

    # --- nomination ---------------------------------------------------------------
    def nominate(self, parents):
        """parents: [{capability, provider}]. Returns (candidates, controls)."""
        ctx = self.ctx
        caps = sorted({p["capability"] for p in parents})
        contracts = {c: ctx.get("capability", c) for c in caps}
        parent_specs = {p["provider"]: ctx.resolve(p["provider"]) for p in parents}
        labels = {c: {parent_specs[p["provider"]]["capability"] for p in parents if p["capability"] == c}
                  for c in caps}
        if any(len(v) != 1 for v in labels.values()):
            raise Refused("parents of one capability must share one semantic label")
        eligible = {c: [s for s in ctx.catalogue()
                        if all(s[k] == contracts[c][k] for k in ("input", "output", "input_unit", "output_unit"))
                        and s["capability"] in labels[c]] for c in caps}
        self.session = dict(construction_ns=0, evaluations=0, parent_cache={})   # one nomination = one session
        parent_kinds = {structure_kind(parent_specs[p["provider"]]) for p in parents} - {None}
        nominated, rejected = [], []
        for kind in sorted({structure_kind(s) for c in caps for s in eligible[c]}, key=lambda k: (k is None, k or "")):
            options = [[s for s in eligible[c] if structure_kind(s) == kind] for c in caps]
            if not all(options):
                rejected.append(dict(prepare=kind, reason="no admissible primitive for every parent contract"))
                continue
            for combo in product(*options):
                assignment = {c: s["id"] for c, s in zip(caps, combo)}
                structures = {kind} - {None}
                reduces = len(structures) < len(parent_kinds) or len(set(assignment.values())) < len(parents)
                if set(assignment.values()) <= set(parent_specs):
                    method = "duplicate-selection"
                elif not structures:
                    method = "structure-elimination"
                else:
                    method = "structural-factoring"
                entry = dict(assignment=assignment, implementations={c: s["implementation"] for c, s in zip(caps, combo)},
                             prepare=kind, structures=len(structures), parent_structures=len(parent_kinds),
                             method=method)
                if reduces:
                    nominated.append(entry)
                else:
                    rejected.append(dict(entry, reason="does not reduce providers or maintained structures"))
        controls = [dict(kind="originals", assignment={p["capability"]: p["provider"] for p in parents}),
                    dict(kind="wrapper", note="routing wrapper over parents: same providers and structures")]
        self._record("nomination", parents=parents, nominated=nominated, rejected=rejected, controls=controls,
                     catalogue_size=len(ctx.catalogue()))
        return nominated, controls

    # --- isolated evaluation --------------------------------------------------------
    def _run(self, spec, value, budget, principal, timings):
        self.ctx.charge(budget, principal, spec["cost"], "assimilation-evaluation")
        seen = []
        out = self.ctx.compute(spec, value, 30, on_timing=seen.append)
        timings.extend(seen)
        return out, seen[-1]

    def measure(self, providers_by_cap, epochs, budget, principal, *, reference=None, gate=None):
        """Run providers over each epoch from a cold cache; per-input outputs and stage costs.

        With `reference` (parent records, same order) and `gate`, the pass stops early once a
        capability's cumulative cost exceeds gate.early_stop_factor x the parents' cost.
        Returns (records, compute_ns, stopped_reason or None).
        """
        ctx, records, spent = self.ctx, [], []
        totals = {}
        try:
            for e, epoch in enumerate(epochs):
                ctx.clear_prepared()
                for cap, value, set_name in epoch:
                    runs = {}
                    for key in providers_by_cap[cap]:
                        out, timing = self._run(ctx.resolve(key), value, budget, principal, spent)
                        runs[key] = dict(output=out, prepare_ns=timing["prepare_ns"], answer_ns=timing["answer_ns"],
                                         state_bytes=timing["state_bytes"], prepare=ctx.resolve(key)["prepare"])
                    records.append(dict(epoch=e, capability=cap, set=set_name, runs=runs))
                    if reference is not None and gate is not None:
                        ref = reference[len(records) - 1]
                        mine = sum(r["prepare_ns"] + r["answer_ns"] for r in runs.values())
                        theirs = min(r["prepare_ns"] + r["answer_ns"] for r in ref["runs"].values())
                        count, a, b = totals.get(cap, (0, 0, 0))
                        totals[cap] = (count + 1, a + mine, b + max(theirs, gate.resolution_ns))
                        count, a, b = totals[cap]
                        if count >= gate.early_stop_min_inputs and a > gate.early_stop_factor * b:
                            raise _EarlyStop(f"early stop: {cap} cost {a / b:.1f}x parents after {count} inputs")
        except _EarlyStop as stop:
            return records, sum(t["compute_ns"] for t in spent), str(stop)
        return records, sum(t["compute_ns"] for t in spent), None

    @staticmethod
    def epoch_costs(records, choice, gate):
        """Per-epoch cost when each capability is served by `choice[cap]` (one provider)."""
        costs = {}
        for e in sorted({r["epoch"] for r in records}):
            rows = [r for r in records if r["epoch"] == e]
            answer = sum(r["runs"][choice[r["capability"]]]["answer_ns"] for r in rows)
            built = {}
            for r in rows:
                run = r["runs"][choice[r["capability"]]]
                if run["prepare"] is not None:
                    built[run["prepare"]] = max(built.get(run["prepare"], 0), run["prepare_ns"])
                    built.setdefault(("bytes", run["prepare"]), run["state_bytes"])
            prepare = sum(v for k, v in built.items() if not isinstance(k, tuple))
            state = sum(v for k, v in built.items() if isinstance(k, tuple))
            costs[e] = dict(answer_ns=answer, prepare_ns=prepare, state_bytes=state,
                            maintenance_ns=state * gate.maintenance_ns_per_byte_epoch,
                            total_ns=answer + prepare + state * gate.maintenance_ns_per_byte_epoch)
        return costs

    def evaluate(self, candidate, parents, evaluation, gate, *, budget, principal):
        """Union gate: correctness, tolerance, downstream equality, full-cost break-even."""
        started = time.perf_counter_ns()
        ctx = self.ctx
        caps = sorted(candidate["assignment"])
        for implementation in set(candidate["implementations"].values()):
            ctx.register(implementation)             # identity record only; no membership or authority
        parent_by_cap = {c: [p["provider"] for p in parents if p["capability"] == c] for c in caps}
        # Parents are measured once per nomination; candidates run in separate cold passes.
        cache_key = (digest(sorted(p["provider"] for p in parents)), id(evaluation))
        if cache_key in self.session["parent_cache"]:
            parent_records, parent_ns = self.session["parent_cache"][cache_key], 0
        else:
            parent_records, parent_ns, _ = self.measure(parent_by_cap, evaluation.epochs, budget, principal)
            self.session["parent_cache"][cache_key] = parent_records
        cand_records, cand_ns, stopped = self.measure({c: [candidate["assignment"][c]] for c in caps},
                                                      evaluation.epochs, budget, principal,
                                                      reference=parent_records, gate=gate)
        if stopped:
            self.session["construction_ns"] += parent_ns + cand_ns
            self.session["evaluations"] += 1
            verdict = dict(accepted=False, competent=False, reasons=[stopped], assignment=candidate["assignment"],
                           implementations=candidate["implementations"], method=candidate["method"],
                           latency_ratio={}, mismatches=None, rebuilt={}, mean_savings_ns=None, upkeep_saving_ns=0,
                           construction_ns=parent_ns + cand_ns, session_construction_ns=self.session["construction_ns"],
                           break_even_epochs=None, state_bytes_before=None, state_bytes_after=None,
                           per_epoch_before={}, per_epoch_after={}, early_stop=True,
                           evaluation_wall_ns=time.perf_counter_ns() - started)
            verdict["trial"] = self._record("evaluation", parents=parents, **{k: v for k, v in verdict.items()
                                                                              if k not in ("per_epoch_before", "per_epoch_after")})
            return verdict
        parent_records = parent_records[:len(cand_records)]
        reasons, per_cap = [], {}
        mismatches = 0
        for pr, cr in zip(parent_records, cand_records):
            reference = {json_key(run["output"]) for run in pr["runs"].values()}
            got = json_key(cr["runs"][candidate["assignment"][pr["capability"]]]["output"])
            if len(reference) != 1 or got not in reference:
                mismatches += 1
        if mismatches:
            reasons.append(f"output mismatch on {mismatches} evaluated inputs")
        sets = sorted({r["set"] for r in parent_records})
        for c in caps:
            if candidate["assignment"][c] in parent_by_cap[c]:
                per_cap[c] = "same-artifact"         # competence identical by identity
                continue
            for s in sets:
                p = [min(run["answer_ns"] for run in r["runs"].values()) for r in parent_records
                     if r["capability"] == c and r["set"] == s]
                q = [r["runs"][candidate["assignment"][c]]["answer_ns"] for r in cand_records
                     if r["capability"] == c and r["set"] == s]
                if not p:
                    continue
                ratio = median(q) / max(1, median(p))
                if max(median(p), median(q)) < gate.resolution_ns:
                    per_cap.setdefault(c, {})[s] = f"below-resolution ({ratio:.2f})"
                    continue
                per_cap.setdefault(c, {})[s] = round(ratio, 3)
                if ratio > gate.tolerance[c]:
                    reasons.append(f"{c} answer latency {ratio:.2f}x parents on {s} exceeds tolerance {gate.tolerance[c]}x")
            # Confidence margin over all measurable inputs: upper bound of the paired log ratio.
            logs = []
            for pr, cr in zip(parent_records, cand_records):
                if pr["capability"] != c:
                    continue
                p1 = min(run["answer_ns"] for run in pr["runs"].values())
                q1 = cr["runs"][candidate["assignment"][c]]["answer_ns"]
                if max(p1, q1) >= gate.resolution_ns:
                    logs.append(math.log(max(q1, 1) / max(p1, 1)))
            if logs:
                mean = sum(logs) / len(logs)
                sd = max(gate.min_log_sd, math.sqrt(sum((x - mean) ** 2 for x in logs) / max(1, len(logs) - 1)))
                upper = math.exp(mean + gate.confidence_z * sd / math.sqrt(len(logs)))
                per_cap.setdefault(c, {})["upper_bound"] = round(upper, 3)
                if upper > gate.tolerance[c]:
                    reasons.append(f"{c} answer-latency upper bound {upper:.2f}x exceeds tolerance {gate.tolerance[c]}x")
        # Downstream dependents: rebuild with the candidate and require equal outputs.
        kept = set(candidate["assignment"].values())
        superseded = [p for p in parents if p["provider"] not in kept]
        rebuilt, deps = {}, ctx.dependents([p["provider"] for p in superseded])
        if deps["members"]:
            reasons.append(f"active members depend on parents and are out of scope: {deps['members']}")
        for role, key in deps["roles"].items():
            spec = ctx.resolve(key)
            if spec["kind"] == "primitive":
                cap = next(c for c in caps if key in parent_by_cap[c])
                rebuilt[role] = dict(provider=candidate["assignment"][cap], direct=True)
                continue
            replace = {p["provider"]: candidate["assignment"][p["capability"]] for p in superseded}
            nodes = [dict(n, provider=replace.get(n["provider"], n["provider"])) for n in spec["source_nodes"]]
            definition = dict(input=spec["input"], output=spec["output"], output_node=spec["output_node"], nodes=nodes)
            new_key = ctx.register_graph(definition, spec["capability"])
            inputs = evaluation.dependents.get(role, [])
            if not inputs:
                reasons.append(f"downstream role {role!r} has no evaluation inputs")
            spent = []
            for value in inputs:
                old = ctx.compute(spec, value, 30, on_timing=spent.append)
                new = ctx.compute(ctx.resolve(new_key), value, 30, on_timing=spent.append)
                if json_key(old) != json_key(new):
                    reasons.append(f"downstream role {role!r} output changed")
                    break
            cand_ns += sum(t["compute_ns"] for t in spent)
            rebuilt[role] = dict(provider=new_key, direct=False)
        # Economics: per-epoch savings against the full construction cost of this evaluation.
        parent_choice = {}
        for c in caps:
            parent_choice[c] = min(parent_by_cap[c], key=lambda k: sum(
                r["runs"][k]["answer_ns"] for r in parent_records if r["capability"] == c))
        before = self.epoch_costs(parent_records, parent_choice, gate)
        after = self.epoch_costs(cand_records, candidate["assignment"], gate)
        upkeep = gate.upkeep_ns_per_provider_epoch * (
            len({p["provider"] for p in parents}) - len(set(candidate["assignment"].values())))
        savings = [before[e]["total_ns"] - after[e]["total_ns"] + upkeep for e in before]
        mean_savings = sum(savings) / len(savings)
        construction_ns = parent_ns + cand_ns
        self.session["construction_ns"] += construction_ns
        self.session["evaluations"] += 1
        # Break-even uses everything this nomination has spent so far, not this candidate alone.
        horizon = self.session["construction_ns"] / mean_savings if mean_savings > 0 else float("inf")
        if mean_savings <= gate.min_savings_ns:
            reasons.append(f"no per-epoch saving ({mean_savings / 1e3:.1f} us)")
        elif horizon > gate.horizon_epochs:
            reasons.append(f"break-even {horizon:.1f} epochs exceeds horizon {gate.horizon_epochs}")
        state_before = sum(v["state_bytes"] for v in before.values()) / len(before)
        state_after = sum(v["state_bytes"] for v in after.values()) / len(after)
        competent = not [r for r in reasons if "saving" not in r and "break-even" not in r]
        verdict = dict(accepted=not reasons, competent=competent, reasons=reasons, assignment=candidate["assignment"],
                       implementations=candidate["implementations"], method=candidate["method"],
                       latency_ratio=per_cap, mismatches=mismatches, rebuilt=rebuilt,
                       mean_savings_ns=round(mean_savings), upkeep_saving_ns=upkeep, construction_ns=construction_ns,
                       session_construction_ns=self.session["construction_ns"], early_stop=False,
                       break_even_epochs=None if horizon == float("inf") else round(horizon, 2),
                       state_bytes_before=round(state_before), state_bytes_after=round(state_after),
                       per_epoch_before=before, per_epoch_after=after,
                       evaluation_wall_ns=time.perf_counter_ns() - started)
        verdict["trial"] = self._record("evaluation", parents=parents, **{k: v for k, v in verdict.items()
                                                                          if k not in ("per_epoch_before", "per_epoch_after")})
        return verdict

    def select(self, verdicts, gate):
        """Final decision over a nomination: charge ALL evaluations to the chosen candidate.

        A candidate is selectable only if competent and if the nomination's total construction
        cost breaks even within the horizon at its per-epoch saving. Returns the best verdict
        (largest saving) or None; every verdict gets `selectable` and `final_reasons`.
        """
        total = sum(v["construction_ns"] for v in verdicts)
        best = None
        for v in verdicts:
            reasons = [] if v.get("competent") else ["not competent: " + "; ".join(v["reasons"])]
            saving = v.get("mean_savings_ns")
            if v.get("competent"):
                if saving is None or saving <= gate.min_savings_ns:
                    reasons.append("no per-epoch saving")
                elif total / saving > gate.horizon_epochs:
                    reasons.append(f"nomination break-even {total / saving:.1f} epochs exceeds horizon {gate.horizon_epochs}")
            v.update(selectable=not reasons, final_reasons=reasons, nomination_construction_ns=total,
                     nomination_break_even_epochs=None if not saving or saving <= 0 else round(total / saving, 2))
            if not reasons and (best is None or saving > best["mean_savings_ns"]):
                best = v
        self._record("selection", total_construction_ns=total, chosen=best and best["trial"],
                     candidates=[dict(trial=v["trial"], selectable=v["selectable"], reasons=v["final_reasons"])
                                 for v in verdicts])
        return best

    # --- publication and recovery -------------------------------------------------------
    def publish(self, verdict, parents, role_cases, *, budget, principal):
        if not verdict["accepted"]:
            raise Refused("only an accepted candidate can be published")
        ctx = self.ctx
        parent_keys = {p["provider"] for p in parents}
        kept = [dict(capability=c, provider=k) for c, k in sorted(verdict["assignment"].items()) if k in parent_keys]
        superseded = [p for p in parents if p["provider"] not in {k["provider"] for k in kept}]
        members = [ctx.prepare_membership(c, k, budget, principal)
                   for c, k in sorted(verdict["assignment"].items()) if k not in parent_keys]
        bindings = [ctx.prepare_binding(role, item["provider"], role_cases[role], budget, principal)
                    for role, item in sorted(verdict["rebuilt"].items())]
        plan = dict(id=f"assimilation:{uid()}", parents=superseded, kept=kept, members=members, bindings=bindings,
                    lineage=dict(trial=verdict["trial"], method=verdict["method"], assignment=verdict["assignment"],
                                 all_parents=parents))
        revision = ctx.commit_assimilation(plan)
        self._record("publication", plan=plan, revision=revision)
        return plan["id"]

    def recover(self, assimilation, role_cases, *, budget, principal, reason):
        ctx = self.ctx
        record = ctx.get("assimilation", assimilation)
        bindings = [ctx.prepare_binding(role, provider, role_cases[role], budget, principal)
                    for role, provider in sorted(record["previous"].items())]
        # Parent competence is re-proven, never assumed: every parent revalidates.
        members = [ctx.prepare_membership(p["capability"], p["provider"], budget, principal)
                   for p in record["parents"]]
        revision = ctx.revert_assimilation(assimilation, members=members, bindings=bindings, reason=reason)
        self._record("recovery", assimilation=assimilation, revision=revision, revalidated=len(members), reason=reason)
        return revision


def json_key(value):
    return digest(value)
