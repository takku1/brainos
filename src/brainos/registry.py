"""Registry identity checks and enforced impact records.

Every staging, validation, commit, task admission, execution and membership
path resolves providers here, so a `block` impact recorded against a provider
is refused at all of those boundaries (Doc 29 section 29.2).
"""
from .contracts import Refused, uid
from . import closure, graphs, providers


class ProviderRegistry:
    def __init__(self, store):
        self.store = store

    def register(self, implementation):
        spec = providers.specification(implementation)
        with self.store.transaction():
            self.store.put("provider", spec["id"], spec)
            self.store.event("provider-registered", provider=spec["id"])
        return spec["id"]

    def blocking_impact(self, key):
        for impact in self.store.find("impact"):
            if impact["action"] == "block" and key in impact["affected"]:
                return impact
        return None

    def resolve(self, key, _stack=()):
        if key in _stack or len(_stack) > 16:
            raise Refused("cyclic artifact dependency")
        impact = self.blocking_impact(key)
        if impact is not None:
            raise Refused(f"provider is blocked by {impact['kind']} impact {impact['id']}: {impact['reason']}")
        spec = self.store.get("provider", key)
        if spec.get("kind") == "graph":
            expected = graphs.specification(spec, spec["capability"],
                lambda ref: self.resolve(ref, (*_stack, key)))
        else:
            expected = providers.specification(spec["implementation"])
        if spec != expected:
            raise Refused("registry artifact does not match trusted catalogue")
        return spec

    def register_graph(self, definition, capability):
        spec = graphs.specification(definition, capability, self.resolve)
        with self.store.transaction():
            self.store.put("provider", spec["id"], spec)
            self.store.event("composite-registered", provider=spec["id"], dependencies=spec["dependencies"],
                             transitive=spec["transitive_dependencies"])
        return spec["id"]

    def population(self):
        return {row["id"]: row for row in self.store.find("provider")}

    def preview_impact(self, changed, kind):
        population = self.population()
        if any(key not in population for key in changed):
            raise Refused("impact names an unknown provider")
        return closure.population_closure(population, set(changed), kind)

    def record_impact(self, changed, kind, reason):
        """Compute closure over the population pinned by this transaction and enforce it."""
        if not reason:
            raise Refused("impact cause required")
        with self.store.transaction():
            affected, action = self.preview_impact(changed, kind)
            state = self.store.get("control", "current")
            state["evidence_revision"] += 1
            key = uid()
            self.store.put("impact", key, dict(id=key, kind=kind, cause=sorted(changed), reason=reason,
                affected=affected, action=action, evidence_revision=state["evidence_revision"],
                registry_size=len(self.store.find("provider"))))
            self.store.put("control", "current", state)
            self.store.event("impact-recorded", impact=key, impact_kind=kind, action=action, affected=affected)
        return key

    def exclude(self, key, reason):
        if not reason:
            raise Refused("exclusion cause required")
        return self.record_impact([key], "support", reason)
