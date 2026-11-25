"""Typed graph admission and scoped impact views, using existing Core services."""
from .contracts import Refused, require_owner


class ComputationalFabric:
    def __init__(self, store, control, registry, transactor, tasks):
        self.store = store
        self.control = control
        self.registry = registry
        self.transactor = transactor
        self.tasks = tasks

    def active_providers(self):
        """Providers that may parent a composition: manifest-bound or active members."""
        with self.store.mutex:
            bound = set(self.control.read()["bindings"].values())
            members = {m["provider"] for m in self.store.find("member") if m["state"] == "ACTIVE"}
        return bound | members

    def register(self, definition, capability):
        with self.store.mutex:
            active = self.active_providers()
            nodes = definition.get("source_nodes", definition.get("nodes", []))
            if any(node["provider"] not in active for node in nodes):
                raise Refused("composition parents must be independently active/validated")
            return self.registry.register_graph(definition, capability)

    def stage(self, definition, capability, role=None):
        provider = self.register(definition, capability)
        role = role or capability
        candidate = self.transactor.stage({role: provider})
        return dict(provider=provider, candidate=candidate, role=role)

    def results(self, task, principal):
        self.tasks.task(task, principal)
        with self.store.mutex:
            rows = sorted((row for row in self.store.find("result") if row["task"] == task),
                          key=lambda row: (row["invocation"], row["sequence"]))
            for row in rows:
                require_owner(row, principal)
            return rows

    def impact(self, provider, kind="support"):
        """Preview: conservative closure over the current population (no enforcement)."""
        affected, action = self.registry.preview_impact([provider], kind)
        return dict(kind=kind, affected=affected, action=action)

    def apply_impact(self, changed, kind, reason):
        """Record and enforce: `block` is refused at every resolution boundary."""
        return self.registry.record_impact(changed, kind, reason)

    def evidence_current(self, provider, evidence_revision):
        """False if a `reevaluate` impact on `provider` postdates the evidence."""
        with self.store.mutex:
            return not any(i["action"] == "reevaluate" and provider in i["affected"]
                           and i["evidence_revision"] > evidence_revision for i in self.store.find("impact"))
