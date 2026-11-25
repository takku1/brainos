"""Owned resource reservations, conversions, charges, tombstones and funding.

Capacity enters the ledger only through `create_budget` or a funding policy,
both issued by an operator principal (Doc 20 section 20.2). Developmental code
is never an operator, so it cannot mint its own funding.
"""
import math
import time

from .contracts import Refused, positive_time, quantities, uid, require_owner

KERNEL = "_kernel"


class ResourceLedger:
    def __init__(self, store, clock=time.time, operators=frozenset({"operator"})):
        self.store = store
        self.clock = clock
        self.operators = frozenset(operators) | {KERNEL}

    def _issuer(self, issued_by):
        if issued_by not in self.operators:
            raise Refused("only an operator principal may issue funding")

    def create_budget(self, principal, capacity, *, issued_by="operator"):
        with self.store.transaction():
            return self.create_budget_tx(principal, capacity, issued_by=issued_by)

    def create_budget_tx(self, principal, capacity, *, issued_by="operator"):
        self._issuer(issued_by)
        capacity = quantities(capacity)
        key = uid()
        self.store.put("budget", key, dict(id=key, principal=principal, capacity=capacity,
                                           available=capacity, spent={k: 0 for k in capacity},
                                           issued_by=issued_by, policy=None))
        self.store.event("budget-created", budget=key, issued_by=issued_by)
        return key

    def attach_policy(self, budget, *, issued_by, period_seconds, grant, ceiling):
        with self.store.transaction():
            return self.attach_policy_tx(budget, issued_by=issued_by, period_seconds=period_seconds,
                                         grant=grant, ceiling=ceiling)

    def attach_policy_tx(self, budget, *, issued_by, period_seconds, grant, ceiling):
        """Periodic replenishment: once per elapsed period, never above `ceiling`."""
        self._issuer(issued_by)
        period_seconds = positive_time(period_seconds)
        grant, ceiling = quantities(grant), quantities(ceiling)
        record = self.store.get("budget", budget)
        if issued_by == record["principal"] and issued_by != KERNEL:
            raise Refused("a principal cannot fund its own budget")
        if set(grant) != set(record["available"]) or set(ceiling) != set(grant):
            raise Refused("funding dimensions differ from the budget")
        if any(grant[k] < 1 or ceiling[k] < grant[k] for k in grant):
            raise Refused("funding grant must be positive and within its ceiling")
        record["policy"] = dict(issued_by=issued_by, period_seconds=period_seconds, grant=grant,
                                ceiling=ceiling, anchor=self.clock(), periods_funded=0)
        self.store.put("budget", budget, record)
        self.store.event("funding-policy", budget=budget, issued_by=issued_by,
                         period_seconds=period_seconds, grant=grant, ceiling=ceiling)

    def _accrue_tx(self, record):
        policy = record.get("policy")
        if not policy:
            return record
        due = math.floor((self.clock() - policy["anchor"]) / policy["period_seconds"])
        periods = due - policy["periods_funded"]
        if periods <= 0:
            return record
        added = {}
        for k, grant in policy["grant"].items():
            room = max(0, policy["ceiling"][k] - record["available"][k])
            added[k] = min(grant * periods, room)
            record["available"][k] += added[k]
            record["capacity"][k] += added[k]
        policy["periods_funded"] = due
        self.store.put("budget", record["id"], record)
        self.store.event("funded", budget=record["id"], period=due, periods=periods, added=added)
        return record

    def budget(self, key, principal):
        with self.store.mutex:
            record = self.store.get("budget", key)
            require_owner(record, principal)
            if record.get("policy") and self.store.db.in_transaction:
                record = self._accrue_tx(record)
            elif record.get("policy"):
                with self.store.transaction():
                    record = self._accrue_tx(self.store.get("budget", key))
            return record

    def reserve_tx(self, budget, principal, amount, purpose):
        amount = quantities(amount)
        record = self._accrue_tx(self.store.get("budget", budget))
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
            if any(row.get("validation_holding") == key and row["state"] == "VALIDATING"
                   for row in self.store.find("candidate")):
                raise Refused("holding belongs to active validation")
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

    def spend_tx(self, key, amount):
        amount = quantities(amount)
        holding = self.store.get("holding", key)
        if holding["state"] != "ALLOCATED" or set(amount) != set(holding["remaining"]):
            raise Refused("spending requires a live compatible allocation")
        if any(v > holding["remaining"][k] for k, v in amount.items()):
            raise Refused("allocation exhausted")
        budget = self.store.get("budget", holding["budget"])
        for k, value in amount.items():
            holding["remaining"][k] -= value
            budget["spent"][k] += value
        self.store.put("holding", key, holding)
        self.store.put("budget", budget["id"], budget)
        self.store.event("spent", holding=key, amount=amount)

    def charge(self, budget, principal, amount, purpose):
        with self.store.transaction():
            holding = self.reserve_tx(budget, principal, amount, purpose)
            self.allocate_tx(holding, principal)
            self.charge_tx(holding)
