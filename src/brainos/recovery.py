"""Single-owner restart advances authority and reconciles durable pending work."""


class RecoveryCoordinator:
    def __init__(self, store, resources):
        self.store = store
        self.resources = resources

    def recover(self):
        with self.store.transaction():
            states = self.store.find("control")
            state = states[0] if states else dict(epoch=0, revision=0, evidence_revision=0,
                                                  bindings={}, phase="PUBLISHED")
            state["epoch"] += 1
            state["phase"] = "PUBLISHED"
            self.store.put("control", "current", state)
            for candidate in self.store.find("candidate"):
                if candidate["state"] in ("PREPARED", "VALIDATING", "VALIDATED"):
                    candidate["state"] = "STALE"
                    self.store.put("candidate", candidate["id"], candidate)
                    self.store.event("candidate-stale-on-recovery", candidate=candidate["id"])
            for permit in self.store.find("permit"):
                permit["revoked"] = True
                self.store.put("permit", permit["id"], permit)
            for task in self.store.find("task"):
                if task["state"] == "RUNNING":
                    self.resources.charge_tx(task["holding"])
                    task.update(state="FAILED", error="interrupted execution; no result inferred")
                    self.store.put("task", task["id"], task)
                elif task["state"] in ("CREATED", "READY"):
                    self.resources.release_tx(task["holding"], task["principal"])
                    task.update(state="BLOCKED", error="restart requires a new task attempt")
                    self.store.put("task", task["id"], task)
            for invocation in self.store.find("invocation"):
                if invocation["state"] == "RUNNING":
                    invocation["state"] = "FAILED"
                    self.store.put("invocation", invocation["id"], invocation)
            for effect in self.store.find("effect"):
                if effect["state"] in ("DISPATCHED", "UNKNOWN"):
                    effect["state"] = "UNKNOWN"
                    self.store.put("effect", effect["id"], effect)
                elif effect["state"] == "INTENT":
                    effect["state"] = "CANCELLED"
                    self.resources.release_tx(effect["holding"], effect["principal"])
                    self.store.put("effect", effect["id"], effect)
            self.store.event("recovery", epoch=state["epoch"], revision=state["revision"])
