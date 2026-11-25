"""Admitted task execution owns task and invocation lifecycles."""
from .contracts import Cancelled, Refused, PermitScope, ProviderRunner, digest, positive_time, quantities, uid, require_owner
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
        self.population = None  # wired by the runtime after construction

    def create_task(self, principal, role, value, budget, amount=None, *, context="default", timeout=5):
        return self._create(principal, value, budget, amount, context, timeout, role=role)

    def create_member_task(self, principal, capability, provider, value, budget, amount=None, *,
                           context="default", timeout=5):
        """Capability-routed work: the caller names the contract and the selected member."""
        return self._create(principal, value, budget, amount, context, timeout,
                            capability=capability, member=provider)

    def _create(self, principal, value, budget, amount, context, timeout, *, role=None, capability=None, member=None):
        timeout = positive_time(timeout)
        if timeout > 60 or not principal or not context:
            raise Refused("invalid identity/context or worker timeout above 60 seconds")
        key = uid()
        with self.store.transaction():
            state = self.control.read()
            if capability is not None:
                spec = self.population.member(capability, member)
            else:
                if role not in state["bindings"]:
                    raise Refused("role is not active")
                spec = self.registry.resolve(state["bindings"][role])
            providers.check(spec["input"], value)
            required = spec["cost"]
            grant = required if amount is None else quantities(amount)
            if set(grant) != set(required) or any(grant[k] < v for k, v in required.items()):
                raise Refused("execution grant is below trusted operation requirements")
            holding = self.resources.reserve_tx(budget, principal, grant, key)
            self.store.put("task", key, dict(id=key, principal=principal, role=role, capability=capability,
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
            if record.get("capability"):
                self.population.member(record["capability"], record["provider"])
            elif state["bindings"].get(record["role"]) != record["provider"]:
                raise Refused("task provider binding changed")
            holding = self.store.get("holding", record["holding"])
            if holding["state"] == "HELD":
                self.resources.allocate_tx(record["holding"], principal)
            elif holding["state"] != "ALLOCATED":
                raise Refused("task has no live allocation")
            record["state"] = "READY"
            self.store.put("task", task, record)
            scope = PermitScope("task", task, principal, digest(record), record["provider"],
                                record["context"], record.get("capability") or record["role"])
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
            spec = (self.population.member(task["capability"], task["provider"]) if task.get("capability")
                    else self.registry.resolve(task["provider"]))
            self.resources.spend_tx(task["holding"], {"attempts": 1})
            task.update(state="RUNNING", invocation=invocation, epoch=permit["epoch"], revision=permit["revision"])
            self.store.put("task", key, task)
            self.store.put("invocation", invocation, dict(id=invocation, task=key, permit=token, state="RUNNING"))
            self.store.event("invocation-started", task=key, invocation=invocation)
        self.failpoint("after_invocation_start")
        started = time.monotonic()
        node_index = [0]
        def cancelled():
            return self.task(key, principal).get("cancel_requested", False)
        def on_start(node_spec):
            if cancelled():
                raise Cancelled("cancelled at a pure node boundary")
            # One admission attempt was charged durably above; later nodes pay here.
            charge = node_spec["cost"]["attempts"] - (1 if node_index[0] == 0 else 0)
            node_index[0] += 1
            if charge:
                with self.store.transaction():
                    self.resources.spend_tx(task["holding"], {"attempts": charge})
        produced = []
        def on_result(record):
            with self.store.transaction():
                result_id = uid()
                result = dict(record, id=result_id, task=key, invocation=invocation, sequence=len(produced),
                              principal=principal, context=task["context"], manifest_revision=task["revision"])
                self.store.put("result", result_id, result)
                produced.append(result_id)
                self.store.event("intermediate-result", result=result_id, task=key, node=record["node"])
        timings = []
        try:
            output = self.runner.compute(spec, task["value"], task["timeout"], on_start=on_start,
                                         on_result=on_result, cancelled=cancelled, on_timing=timings.append)
            if cancelled():
                raise Cancelled("cancelled at the final pure boundary")
        except Exception as exc:
            self._finish(task, invocation, error=str(exc), elapsed=time.monotonic() - started,
                         cancelled=isinstance(exc, Cancelled), timings=timings)
            raise
        self._finish(task, invocation, output=output, elapsed=time.monotonic() - started, timings=timings)
        return output

    def invocation(self, key, principal):
        with self.store.mutex:
            record = self.store.get("invocation", key)
            require_owner(self.store.get("task", record["task"]), principal)
            return record

    def _finish(self, task, invocation, *, output=None, error=None, elapsed=0, cancelled=False, timings=()):
        with self.store.transaction():
            current = self.store.get("invocation", invocation)
            if current["state"] != "RUNNING":
                raise Refused("invocation already terminated")
            current["state"] = "STOPPED" if cancelled else "FAILED" if error else "COMPLETED"
            current.update(error=error, timings=list(timings), profile=getattr(self.runner, "profile", None),
                           compute_ns=sum(t["compute_ns"] for t in timings),
                           total_ns=sum(t["total_ns"] for t in timings))
            self.store.put("invocation", invocation, current)
            task.update(state="CANCELLED" if cancelled else "FAILED" if error else "SUCCEEDED", result=output,
                        error=error, elapsed_seconds=elapsed)
            self.resources.release_tx(task["holding"], task["principal"])
            self.store.put("task", task["id"], task)
            self.store.event("invocation-finished", invocation=invocation, state=task["state"])

    def cancel_task(self, key, principal):
        with self.store.transaction():
            task = self.store.get("task", key)
            require_owner(task, principal)
            if task["state"] == "RUNNING":
                task["cancel_requested"] = True
                invocation = self.store.get("invocation", task["invocation"])
                self.authority.revoke_tx(invocation["permit"])
                self.store.put("task", key, task)
                self.store.event("task-cancel-requested", task=key)
                return "STOP_REQUESTED"
            if task["state"] in ("SUCCEEDED", "FAILED", "CANCELLED"):
                return task["state"]
            task["state"] = "CANCELLED"
            self.resources.release_tx(task["holding"], principal)
            self.store.put("task", key, task)
            self.store.event("task-cancelled", task=key)
            return "CANCELLED"
