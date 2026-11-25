"""Registry identity checks against the independently trusted catalogue."""
from .contracts import Refused
from . import providers


class ProviderRegistry:
    def __init__(self, store):
        self.store = store

    def register(self, implementation):
        spec = providers.specification(implementation)
        with self.store.transaction():
            self.store.put("provider", spec["id"], spec)
            self.store.event("provider-registered", provider=spec["id"])
        return spec["id"]

    def resolve(self, key):
        spec = self.store.get("provider", key)
        if spec != providers.specification(spec["implementation"]):
            raise Refused("registry artifact does not match trusted catalogue")
        return spec
