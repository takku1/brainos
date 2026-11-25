"""Registry identity checks against the independently trusted catalogue."""
from .contracts import Refused
from . import providers
from . import graphs


class ProviderRegistry:
    def __init__(self, store):
        self.store = store

    def register(self, implementation):
        spec = providers.specification(implementation)
        with self.store.transaction():
            self.store.put("provider", spec["id"], spec)
            self.store.event("provider-registered", provider=spec["id"])
        return spec["id"]

    def resolve(self, key, _stack=()):
        if key in _stack or len(_stack) > 16:
            raise Refused("cyclic artifact dependency")
        if any(row["id"] == key for row in self.store.find("excluded")):
            raise Refused("provider is excluded by scoped impact")
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
            self.store.event("composite-registered", provider=spec["id"], dependencies=spec["dependencies"])
        return spec["id"]

    def exclude(self, key, reason):
        if not reason:
            raise Refused("exclusion cause required")
        with self.store.transaction():
            self.store.get("provider", key)
            self.store.put("excluded", key, dict(id=key, reason=reason))
            state = self.store.get("control", "current")
            state["evidence_revision"] += 1
            self.store.put("control", "current", state)
            self.store.event("provider-excluded", provider=key, reason=reason)
