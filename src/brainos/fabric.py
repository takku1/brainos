"""Typed graph admission and scoped impact views, using existing Core services."""
from .contracts import Refused, require_owner


class ComputationalFabric:
    def __init__(self, store, control, registry, transactor, tasks):
        self.store = store
        self.control = control
        self.registry = registry
        self.transactor = transactor
        self.tasks = tasks

    def stage(self, definition, capability):
        with self.store.mutex:
            active = set(self.control.read()["bindings"].values())
            if any(node["provider"] not in active for node in definition.get("nodes", [])):
                raise Refused("composition parents must be independently active/validated")
            provider = self.registry.register_graph(definition, capability)
            candidate = self.transactor.stage({capability: provider})
            return dict(provider=provider, candidate=candidate, role=capability)

    def results(self, task, principal):
        self.tasks.task(task, principal)
        with self.store.mutex:
            rows = sorted((row for row in self.store.find("result") if row["task"] == task),
                          key=lambda row: (row["invocation"], row["sequence"]))
            for row in rows:
                require_owner(row, principal)
            return rows

    def impact(self, provider, kind="support"):
        records = {row["id"]: row for row in self.store.find("provider")}
        if provider not in records or kind not in ("support", "resources", "failure_domains"):
            raise Refused("unknown provider or impact class")
        affected = {provider}
        if kind != "support":
            footprint = set(records[provider]["footprint"][kind])
            affected.update(key for key, row in records.items() if footprint.intersection(row["footprint"][kind]))
        while True:
            enlarged = affected | {key for key, row in records.items() if row["kind"] == "graph"
                                   and affected.intersection(row["dependencies"])}
            if enlarged == affected:
                break
            affected = enlarged
        return dict(kind=kind, affected=sorted(affected),
                    action="block-dependent-use" if kind == "support" else "reevaluate-affected-guarantees")
