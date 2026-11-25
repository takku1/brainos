"""Composition root for the local single-authority Core profile."""
import time

from .authority import Authority
from .evidence import EvidenceLedger
from .execution import TaskExecutor
from .gateways import EffectGateway
from .recovery import RecoveryCoordinator
from .registry import ProviderRegistry
from .resources import ResourceLedger
from .population import CapabilityPopulation
from .runner import ExternalDispatcher, make_runner
from .storage import Store
from .transactor import Transactor
from .fabric import ComputationalFabric


class ControlState:
    """Shared manifest/epoch record; only kernel services write this record."""
    def __init__(self, store):
        self.store = store

    def read(self):
        return self.store.get("control", "current")


class Runtime:
    """Wire explicit service dependencies; no model framework in the kernel.

    Local operator APIs are trusted. Catalogue processes are not a sandbox for
    arbitrary code. Budgets account declared work grants, not CPU/VRAM limits.
    """
    VALIDATION_FUNDING = dict(period_seconds=3600, grant={"attempts": 128}, ceiling={"attempts": 256})

    def __init__(self, path, *, clock=time.time, failpoint=None, profile="subprocess",
                 operators=frozenset({"operator"}), external_adapters=None):
        self.store = Store(path)
        failpoint = failpoint or (lambda name: None)
        self.control = ControlState(self.store)
        self.resources = ResourceLedger(self.store, clock, operators)
        self.evidence = EvidenceLedger(self.store, self.control, clock)
        self.registry = ProviderRegistry(self.store, operators)
        self.authority = Authority(self.store, self.control, self.evidence, clock)
        external = (ExternalDispatcher(external_adapters, self._runner_event)
                    if external_adapters else None)
        self.runner = make_runner(profile, self.registry, self._runner_event, external=external)
        self.tasks = TaskExecutor(self.store, self.control, self.registry, self.runner,
                                  self.resources, self.authority, failpoint)
        self.effects = EffectGateway(self.store, self.control, self.resources,
                                     self.evidence, self.authority, failpoint)
        try:
            RecoveryCoordinator(self.store, self.resources).recover()
            with self.store.transaction():
                grants = self.store.find("system")
                if not any(g.get("kind") == "validation-budget" for g in grants):
                    budget = self.resources.create_budget_tx("_kernel_validation", {"attempts": 128},
                                                             issued_by="_kernel")
                    self.resources.attach_policy_tx(budget, issued_by="_kernel", **self.VALIDATION_FUNDING)
                    self.store.put("system", "validation-budget", dict(kind="validation-budget", id=budget))
                budget = self.store.get("system", "validation-budget")["id"]
            self.transactor: Transactor = Transactor(self.store, self.control, self.registry, self.runner,
                                         failpoint, self.resources, budget)
            self.fabric = ComputationalFabric(self.store, self.control, self.registry, self.transactor, self.tasks)
            self.population = CapabilityPopulation(self.store, self.registry, self.transactor, self.control)
            self.tasks.population = self.population
        except BaseException:
            self.runner.close()
            self.store.close()
            raise

    def _runner_event(self, kind, **fields):
        """Worker lifecycle (start, stop on timeout/death) is journaled."""
        with self.store.mutex:  # in_transaction is connection-wide; only our thread may extend it
            if self.store.closed:
                return
            if self.store.db.in_transaction:
                self.store.event(kind, **fields)
            else:
                with self.store.transaction():
                    self.store.event(kind, **fields)

    def manifest(self):
        with self.store.mutex:
            return self.control.read()

    def close(self):
        self.runner.close()
        self.store.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
