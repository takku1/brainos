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
            self.store.put("candidate", key, dict(id=key, bindings=bindings,
                revision=state["revision"], epoch=state["epoch"],
                evidence_revision=state["evidence_revision"], state="PREPARED"))
            self.store.event("prepared", candidate=key)
        return key

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
        attempts = 0
        try:
            for role, examples in cases.items():
                for value, expected in examples:
                    remaining = 10 - (time.monotonic() - started)
                    if remaining <= 0:
                        raise Refused("validation exceeded its ten-second grant")
                    attempts += 1
                    with self.store.transaction():
                        self.resources.spend_tx(holding, resolved[role]["cost"])
                    if self.runner.compute(resolved[role], value, min(5, remaining)) != expected:
                        raise Refused("candidate failed independent expected-output checks")
            with self.store.transaction():
                if self.control.read() != captured:
                    raise Refused("validation inputs changed")
                if self.store.get("candidate", candidate)["state"] != "VALIDATING":
                    raise Refused("candidate state changed during validation")
                record.update(state="VALIDATED", cases_digest=digest(cases))
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
            if record["state"] != "VALIDATED":
                raise Refused("candidate has no current validation")
            if any(record[k] != state[k] for k in ("revision", "epoch", "evidence_revision")):
                raise Refused("stale candidate or validation")
            for key in record["bindings"].values():
                self.registry.resolve(key)
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
