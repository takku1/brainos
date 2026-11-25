"""Owned resource reservations, conversions, charges, and tombstones."""
from .contracts import Refused, quantities, uid, require_owner


class ResourceLedger:
    def __init__(self, store):
        self.store = store

    def create_budget(self, principal, capacity):
        capacity = quantities(capacity)
        key = uid()
        with self.store.transaction():
            self.store.put("budget", key, dict(id=key, principal=principal, capacity=capacity,
                                               available=capacity, spent={k: 0 for k in capacity}))
            self.store.event("budget-created", budget=key)
        return key

    def budget(self, key, principal):
        with self.store.mutex:
            record = self.store.get("budget", key)
            require_owner(record, principal)
            return record

    def reserve_tx(self, budget, principal, amount, purpose):
        amount = quantities(amount)
        record = self.store.get("budget", budget)
        require_owner(record, principal)
        if set(amount) != set(record["available"]):
            raise Refused("resource dimensions differ")
        if any(v > record["available"][k] for k, v in amount.items()):
            raise Refused("budget overdraft")
        key = uid()
        for k, value in amount.items():
            record["available"][k] -= value
        self.store.put("budget", budget, record)
        self.store.put("holding", key, dict(id=key, principal=principal, budget=budget,
            purpose=purpose, amount=amount, remaining=amount, state="HELD"))
        self.store.event("reserved", holding=key, budget=budget, amount=amount)
        return key

    def reserve(self, budget, principal, amount, purpose="operator"):
        with self.store.transaction():
            return self.reserve_tx(budget, principal, amount, purpose)

    def allocate_tx(self, key, principal):
        holding = self.store.get("holding", key)
        require_owner(holding, principal)
        if holding["state"] != "HELD":
            raise Refused("reservation already converted or released")
        holding["state"] = "ALLOCATED"
        self.store.put("holding", key, holding)
        self.store.event("allocated", holding=key)

    def allocate(self, key, principal):
        with self.store.transaction():
            self.allocate_tx(key, principal)

    def release_tx(self, key, principal):
        holding = self.store.get("holding", key)
        require_owner(holding, principal)
        if holding["state"] == "RELEASED":
            return "ALREADY_RELEASED"
        budget = self.store.get("budget", holding["budget"])
        for k, value in holding["remaining"].items():
            budget["available"][k] += value
        holding.update(remaining={k: 0 for k in holding["remaining"]}, state="RELEASED")
        self.store.put("holding", key, holding)
        self.store.put("budget", budget["id"], budget)
        self.store.event("released", holding=key)
        return "RELEASED"

    def release(self, key, principal):
        with self.store.transaction():
            # Task/effect-owned live grants cannot be refunded by a caller.
            for kind in ("task", "effect"):
                for record in self.store.find(kind):
                    if record["holding"] == key and record["state"] in ("READY", "RUNNING", "INTENT", "DISPATCHED", "UNKNOWN"):
                        raise Refused("holding belongs to unresolved or active work")
            return self.release_tx(key, principal)

    def charge_tx(self, key):
        holding = self.store.get("holding", key)
        if holding["state"] == "RELEASED":
            return
        budget = self.store.get("budget", holding["budget"])
        for k, value in holding["remaining"].items():
            budget["spent"][k] += value
        holding["remaining"] = {k: 0 for k in holding["remaining"]}
        self.store.put("holding", key, holding)
        self.store.put("budget", budget["id"], budget)
        self.release_tx(key, holding["principal"])
