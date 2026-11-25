"""Prepared and validated configurations publish with revision and epoch CAS."""
import json
import time
from .contracts import Refused, ProviderRunner, digest, encode, uid


class Transactor:
    def __init__(self, store, control, registry, runner: ProviderRunner, failpoint, resources, validation_budget):
        self.store = store
        self.control = control
        self.registry = registry
        self.runner = runner
        self.failpoint = failpoint
        self.resources = resources
        self.validation_budget = validation_budget

    def stage(self, bindings):
        if not isinstance(bindings, dict) or not bindings:
            raise Refused("nonempty role bindings required")
        key = uid()
        with self.store.transaction():
            state = self.control.read()
            for role, provider in bindings.items():
                spec = self.registry.resolve(provider)
                if not isinstance(role, str) or not role:
                    raise Refused("role must be a nonempty name")
                if role in state["bindings"]:
                    previous = self.store.get("provider", state["bindings"][role])
                    if any(previous[k] != spec[k] for k in ("capability", "input", "output")):
                        raise Refused("replacement violates the role capability or schemas")
            self.store.put("candidate", key, dict(id=key, kind="binding", bindings=bindings,
                revision=state["revision"], epoch=state["epoch"],
                evidence_revision=state["evidence_revision"], state="PREPARED"))
            self.store.event("prepared", candidate=key)
        return key

    def stage_membership(self, capability, provider):
        """A population admission: validated like a binding, never bound in the manifest."""
        key = uid()
        with self.store.transaction():
            contract = self.store.get("capability", capability)
            spec = self.registry.resolve(provider)
            if any(spec[k] != contract[k] for k in ("input", "output", "input_unit", "output_unit")):
                raise Refused("provider schemas/units do not match the capability contract")
            state = self.control.read()
            self.store.put("candidate", key, dict(id=key, kind="membership", bindings={capability: provider},
                revision=state["revision"], epoch=state["epoch"],
                evidence_revision=state["evidence_revision"], state="PREPARED"))
            self.store.event("prepared", candidate=key, membership=capability)
        return key

    def _pinned(self, record, state, kind):
        if record.get("kind", "binding") != kind:
            raise Refused(f"candidate is not a {kind} candidate")
        if record["state"] != "VALIDATED":
            raise Refused("candidate has no current validation")
        if any(record[k] != state[k] for k in ("revision", "epoch", "evidence_revision")):
            raise Refused("stale candidate or validation")
        for key in record["bindings"].values():
            self.registry.resolve(key)

    def commit_membership(self, candidate):
        with self.store.transaction():
            return self._commit_membership_tx(candidate, self.control.read())

    def _commit_membership_tx(self, candidate, state, *, event="admitted"):
        record = self.store.get("candidate", candidate)
        self._pinned(record, state, "membership")
        (capability, provider), = record["bindings"].items()
        key = f"{capability}|{provider}"
        previous = next((m for m in self.store.find("member") if m["id"] == key), None)
        if previous is not None and previous["state"] == "ACTIVE":
            raise Refused("provider is already an active member")
        history = previous["history"] if previous else []
        history.append(dict(event=event, candidate=candidate, revision=state["revision"]))
        row = dict(previous or {}, id=key, capability=capability, provider=provider, state="ACTIVE",
                   candidate=candidate, cases_digest=record["cases_digest"], history=history,
                   admitted_period=self.store.get("capability", capability)["period"])
        self.store.put("member", key, row)
        record["state"] = "COMMITTED"
        self.store.put("candidate", candidate, record)
        self.store.event("member-admitted", capability=capability, provider=provider, candidate=candidate)
        return key

    # --- ASSIMILATE (Doc 24): atomic publication and lineage-based recovery ------
    def _depends_on(self, provider, parents):
        spec = self.store.get("provider", provider)
        return provider in parents or bool(set(spec.get("transitive_dependencies", [])) & parents)

    def commit_assimilation(self, plan):
        """Publish an assimilation in ONE transaction, or not at all.

        plan: id, parents [{capability, provider}], members [VALIDATED membership
        candidates], bindings [VALIDATED binding candidates], lineage (dict).
        Every role or active member that depends on a parent must be rebound or
        superseded by the plan; parents become DORMANT (superseded), never ARCHIVED.
        """
        with self.store.transaction():
            state = self.control.read()
            lineage = plan.get("lineage", {})
            # B21: publication is bound to a recorded selection that chose this exact evaluation.
            selection = next((t for t in self.store.find("assimilation-trial")
                              if t["id"] == lineage.get("selection") and t["kind"] == "selection"), None)
            if selection is None or selection.get("chosen") is None or selection["chosen"] != lineage.get("trial"):
                raise Refused("assimilation plan is not bound to a selection that chose its evaluation")
            evaluation = next((t for t in self.store.find("assimilation-trial")
                               if t["id"] == lineage["trial"] and t["kind"] == "evaluation"), None)
            if evaluation is None or evaluation["assignment"] != lineage.get("assignment"):
                raise Refused("selected evaluation does not match the plan's assignment")
            parents = {p["provider"] for p in plan["parents"]}
            members = [self.store.get("candidate", c) for c in plan["members"]]
            bindings = [self.store.get("candidate", c) for c in plan["bindings"]]
            for record, kind in [(m, "membership") for m in members] + [(b, "binding") for b in bindings]:
                self._pinned(record, state, kind)
            covered = {cap for m in members for cap in m["bindings"]}
            for keep in plan.get("kept", []):
                row = next((r for r in self.store.find("member")
                            if r["id"] == f"{keep['capability']}|{keep['provider']}"), None)
                if row is None or row["state"] != "ACTIVE" or keep["provider"] in parents:
                    raise Refused("a kept provider must be an active member that is not superseded")
                covered.add(keep["capability"])
            for parent in plan["parents"]:
                if parent["capability"] not in covered:
                    raise Refused("missing parent coverage: a parent capability has no replacement member")
                row = next((r for r in self.store.find("member")
                            if r["id"] == f"{parent['capability']}|{parent['provider']}"), None)
                if row is None or row["state"] not in ("ACTIVE", "DORMANT"):
                    raise Refused("parent is not a current member")
            for record in members + bindings:
                for provider in record["bindings"].values():
                    if self._depends_on(provider, parents):
                        raise Refused("replacement still depends on a parent being superseded")
            rebound = {role: provider for b in bindings for role, provider in b["bindings"].items()}
            for role, provider in state["bindings"].items():
                if role not in rebound and self._depends_on(provider, parents):
                    raise Refused(f"hidden dependency: role {role!r} depends on a superseded parent")
            for row in self.store.find("member"):
                if (row["state"] == "ACTIVE" and row["provider"] not in parents
                        and self._depends_on(row["provider"], parents)):
                    raise Refused(f"hidden dependency: member {row['id']!r} depends on a superseded parent")
            admitted = [self._commit_membership_tx(m["id"], state, event="assimilated") for m in members]
            previous = {role: state["bindings"].get(role) for role in rebound}
            state["bindings"].update(rebound)
            self.failpoint("during_assimilation_commit")
            for parent in plan["parents"]:
                key = f"{parent['capability']}|{parent['provider']}"
                row = self.store.get("member", key)
                row.update(state="DORMANT", superseded_by=plan["id"], dormant_revision=state["evidence_revision"],
                           dormant_period=self.store.get("capability", parent["capability"])["period"])
                row["history"].append(dict(event="superseded", assimilation=plan["id"]))
                self.store.put("member", key, row)
            for b in bindings:
                b["state"] = "COMMITTED"
                self.store.put("candidate", b["id"], b)
            state.update(revision=state["revision"] + 1, epoch=state["epoch"] + 1, phase="PUBLISHED")
            self.store.put("control", "current", state)
            self.store.put("assimilation", plan["id"], dict(id=plan["id"], state="PUBLISHED",
                parents=plan["parents"], kept=plan.get("kept", []), members=admitted, rebound=rebound, previous=previous,
                lineage=plan.get("lineage", {}), revision=state["revision"], epoch=state["epoch"],
                evidence_revision=state["evidence_revision"]))
            self.store.event("assimilation-published", assimilation=plan["id"], revision=state["revision"])
        return state["revision"]

    def revert_assimilation(self, assimilation, *, members=(), bindings=(), reason):
        """Restore parent competence after post-publication loss, with fresh evidence.

        A parent touched by an impact since publication needs a VALIDATED membership
        candidate; every rebound role needs a VALIDATED binding candidate back to its
        previous provider. The epoch advances, so permits issued under the
        assimilation are refused and pre-assimilation permits are not revived.
        """
        if not reason:
            raise Refused("recovery requires a recorded cause")
        with self.store.transaction():
            state = self.control.read()
            record = self.store.get("assimilation", assimilation)
            if record["state"] != "PUBLISHED":
                raise Refused("only a published assimilation can be reverted")
            fresh = {}
            for c in members:
                cand = self.store.get("candidate", c)
                self._pinned(cand, state, "membership")
                fresh[next(iter(cand["bindings"].values()))] = c
            back = {}
            for c in bindings:
                cand = self.store.get("candidate", c)
                self._pinned(cand, state, "binding")
                back.update(cand["bindings"])
            for role, provider in record["previous"].items():
                if back.get(role) != provider:
                    raise Refused(f"role {role!r} needs a validated binding back to its previous provider")
            for parent in record["parents"]:
                key = f"{parent['capability']}|{parent['provider']}"
                row = self.store.get("member", key)
                stale = any(i["evidence_revision"] > record["evidence_revision"]
                            and parent["provider"] in i["affected"] for i in self.store.find("impact"))
                if stale and parent["provider"] not in fresh:
                    raise Refused("parent evidence is stale: fresh validation required before recovery")
                if parent["provider"] in fresh:
                    self._commit_membership_tx(fresh[parent["provider"]], state, event="recovered")
                else:
                    row["state"] = "ACTIVE"
                    row["history"].append(dict(event="recovered", assimilation=assimilation, validated=False))
                    self.store.put("member", key, row)
            for key in record["members"]:
                row = self.store.get("member", key)
                row.update(state="DORMANT", superseded_by=f"revert:{assimilation}",
                           dormant_revision=state["evidence_revision"],
                           dormant_period=self.store.get("capability", row["capability"])["period"])
                row["history"].append(dict(event="reverted", assimilation=assimilation, reason=reason))
                self.store.put("member", key, row)
            state["bindings"].update(back)
            for c in bindings:
                cand = self.store.get("candidate", c)
                cand["state"] = "COMMITTED"
                self.store.put("candidate", c, cand)
            state.update(revision=state["revision"] + 1, epoch=state["epoch"] + 1, phase="PUBLISHED")
            self.store.put("control", "current", state)
            record.update(state="REVERTED", reverted_revision=state["revision"], reason=reason)
            self.store.put("assimilation", assimilation, record)
            self.store.event("assimilation-reverted", assimilation=assimilation, reason=reason)
        return state["revision"]

    def validate(self, candidate, cases, *, budget=None, principal=None):
        budget = self.validation_budget if budget is None else budget
        principal = "_kernel_validation" if principal is None else principal
        # Prepare under a short transaction. Expensive signal work owns no DB lock.
        with self.store.transaction():
            record = self.store.get("candidate", candidate)
            if record["state"] != "PREPARED":
                raise Refused("validation requires a prepared candidate")
            expected_roles = set(record["bindings"])
            if set(cases) != expected_roles or any(not values for values in cases.values()):
                raise Refused("every changed role requires independent test cases")
            if sum(len(values) for values in cases.values()) > 64:
                raise Refused("validation exceeds the profile's 64-case bound")
            captured = self.control.read()
            if any(record[k] != captured[k] for k in ("revision", "epoch", "evidence_revision")):
                raise Refused("candidate base is stale")
            cases = json.loads(encode(cases))
            resolved = {role: self.registry.resolve(key) for role, key in record["bindings"].items()}
            amount = sum(len(cases[role]) * spec["cost"]["attempts"] for role, spec in resolved.items())
            holding = self.resources.reserve_tx(budget, principal, {"attempts": amount}, "validation:" + candidate)
            self.resources.allocate_tx(holding, principal)
            record.update(validation_holding=holding, validation_principal=principal)
            record["state"] = "VALIDATING"
            self.store.put("candidate", candidate, record)
            self.store.event("validation-started", candidate=candidate)
        started = time.monotonic()
        started_ns = time.perf_counter_ns()   # same clock as compute timings (monotonic is ~15 ms on Windows)
        attempts = 0
        timings = []
        try:
            for role, examples in cases.items():
                for value, expected in examples:
                    remaining = 10 - (time.monotonic() - started)
                    if remaining <= 0:
                        raise Refused("validation exceeded its ten-second grant")
                    attempts += 1
                    with self.store.transaction():
                        self.resources.spend_tx(holding, resolved[role]["cost"])
                    if self.runner.compute(resolved[role], value, min(5, remaining),
                                           on_timing=timings.append) != expected:
                        raise Refused("candidate failed independent expected-output checks")
            with self.store.transaction():
                if self.control.read() != captured:
                    raise Refused("validation inputs changed")
                if self.store.get("candidate", candidate)["state"] != "VALIDATING":
                    raise Refused("candidate state changed during validation")
                record.update(state="VALIDATED", cases_digest=digest(cases),
                              validation_compute_ns=sum(t["compute_ns"] for t in timings),
                              validation_total_ns=sum(t["total_ns"] for t in timings),
                              validation_wall_ns=time.perf_counter_ns() - started_ns, validation_attempts=attempts)
                self.resources.release_tx(holding, principal)
                self.store.put("candidate", candidate, record)
                self.store.event("validated", candidate=candidate, cases=record["cases_digest"],
                                 attempts=attempts, elapsed_seconds=time.monotonic() - started)
        except Exception as exc:
            with self.store.transaction():
                record["state"] = "REJECTED"
                self.resources.release_tx(holding, principal)
                self.store.put("candidate", candidate, record)
                self.store.event("validation-failed", candidate=candidate, attempts=attempts,
                                 elapsed_seconds=time.monotonic() - started, error=str(exc))
            raise

    def commit(self, candidate):
        with self.store.transaction():
            record = self.store.get("candidate", candidate)
            state = self.control.read()
            self._pinned(record, state, "binding")
            state["bindings"].update(record["bindings"])
            state.update(revision=state["revision"] + 1, epoch=state["epoch"] + 1, phase="COMMITTED")
            record["state"] = "COMMITTED"
            self.store.put("candidate", candidate, record)
            self.store.put("control", "current", state)
            self.store.event("manifest-committed", candidate=candidate, revision=state["revision"])
            self.failpoint("before_manifest_commit")
        self.failpoint("after_manifest_commit")
        with self.store.transaction():
            state = self.control.read()
            state["phase"] = "PUBLISHED"
            self.store.put("control", "current", state)
            self.store.event("manifest-published", revision=state["revision"])
        return state["revision"]
