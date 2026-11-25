"""Admitted task execution owns task and invocation lifecycles."""
from .contracts import Refused, PermitScope, ProviderRunner, digest, positive_time, uid, require_owner
import time
from . import providers


class TaskExecutor:
    def __init__(self, store, control, registry, runner: ProviderRunner, resources, authority, failpoint):
        self.store = store
        self.control = control
        self.registry = registry
        self.runner = runner
        self.resources = resources
        self.authority = authority
        self.failpoint = failpoint

    def create_task(self, principal, role, value, budget, amount=None, *, context="default", timeout=5):
        timeout = positive_time(timeout)
        if timeout > 60 or not principal or not context:
            raise Refused("invalid identity/context or worker timeout above 60 seconds")
        key = uid()
        with self.store.transaction():
            state = self.control.read()
            if role not in state["bindings"]:
                raise Refused("role is not active")
            spec = self.registry.resolve(state["bindings"][role])
            providers.check(spec["input"], value)
            holding = self.resources.reserve_tx(budget, principal, {"attempts": 1} if amount is None else amount, key)
            self.store.put("task", key, dict(id=key, principal=principal, role=role,
                provider=spec["id"], value=value, input_digest=digest(value), context=context,
                timeout=timeout, holding=holding, state="CREATED"))
            self.store.event("task-created", task=key)
        return key

    def authorize(self, task, principal, evidence=(), ttl=60):
        with self.store.transaction():
            record = self.store.get("task", task)
            require_owner(record, principal)
            if record["state"] not in ("CREATED", "READY"):
                raise Refused("task cannot be authorized in its current state")
            state = self.control.read()
            if state["bindings"].get(record["role"]) != record["provider"]:
                raise Refused("task provider binding changed")
            holding = self.store.get("holding", record["holding"])
            if holding["state"] == "HELD":
                self.resources.allocate_tx(record["holding"], principal)
            elif holding["state"] != "ALLOCATED":
                raise Refused("task has no live allocation")
            record["state"] = "READY"
            self.store.put("task", task, record)
            scope = PermitScope("task", task, principal, digest(record), record["provider"],
                                record["context"], record["role"])
            return self.authority.issue_tx(scope, evidence, ttl)

    def task(self, key, principal):
        with self.store.mutex:
            task = self.store.get("task", key)
            require_owner(task, principal)
            return task

    def run_task(self, key, token, principal):
        invocation = uid()
        with self.store.transaction():
            task = self.store.get("task", key)
            require_owner(task, principal)
            permit = self.authority.check_permit(token, principal, "task", key)
            if task["state"] != "READY" or permit["payload_digest"] != digest(task):
                raise Refused("task is not ready or its authorized content changed")
            if self.store.get("holding", task["holding"])["state"] != "ALLOCATED":
                raise Refused("allocation is not live")
            spec = self.registry.resolve(task["provider"])
            task.update(state="RUNNING", invocation=invocation, epoch=permit["epoch"], revision=permit["revision"])
            self.store.put("task", key, task)
            self.store.put("invocation", invocation, dict(id=invocation, task=key, permit=token, state="RUNNING"))
            self.store.event("invocation-started", task=key, invocation=invocation)
        self.failpoint("after_invocation_start")
        started = time.monotonic()
        try:
            output = self.runner.compute(spec, task["value"], task["timeout"])
        except Exception as exc:
            self._finish(task, invocation, error=str(exc), elapsed=time.monotonic() - started)
            raise
        self._finish(task, invocation, output=output, elapsed=time.monotonic() - started)
        return output

    def _finish(self, task, invocation, *, output=None, error=None, elapsed=0):
        with self.store.transaction():
            current = self.store.get("invocation", invocation)
            if current["state"] != "RUNNING":
                raise Refused("invocation already terminated")
            current["state"] = "FAILED" if error else "COMPLETED"
            self.store.put("invocation", invocation, current)
            task.update(state="FAILED" if error else "SUCCEEDED", result=output,
                        error=error, elapsed_seconds=elapsed)
            self.resources.charge_tx(task["holding"])
            self.store.put("task", task["id"], task)
            self.store.event("invocation-finished", invocation=invocation, state=task["state"])

    def cancel_task(self, key, principal):
        with self.store.transaction():
            task = self.store.get("task", key)
            require_owner(task, principal)
            if task["state"] == "RUNNING":
                raise Refused("synchronous worker drains within its admitted timeout; revoke its permit")
            if task["state"] in ("SUCCEEDED", "FAILED", "CANCELLED"):
                return task["state"]
            task["state"] = "CANCELLED"
            self.resources.release_tx(task["holding"], principal)
            self.store.put("task", key, task)
            self.store.event("task-cancelled", task=key)
            return "CANCELLED"
