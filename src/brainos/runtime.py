"""Composition root for the local single-authority Core profile."""
import time

from .authority import Authority
from .evidence import EvidenceLedger
from .execution import TaskExecutor
from .gateways import EffectGateway
from .recovery import RecoveryCoordinator
from .registry import ProviderRegistry
from .resources import ResourceLedger
from .runner import ProcessRunner
from .storage import Store
from .transactor import Transactor


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
    def __init__(self, path, *, clock=time.time, failpoint=None):
        self.store = Store(path)
        failpoint = failpoint or (lambda name: None)
        self.control = ControlState(self.store)
        self.resources = ResourceLedger(self.store)
        self.evidence = EvidenceLedger(self.store, self.control, clock)
        self.registry = ProviderRegistry(self.store)
        self.authority = Authority(self.store, self.control, self.evidence, clock)
        self.runner = ProcessRunner()
        self.transactor = Transactor(self.store, self.control, self.registry, self.runner, failpoint)
        self.tasks = TaskExecutor(self.store, self.control, self.registry, self.runner,
                                  self.resources, self.authority, failpoint)
        self.effects = EffectGateway(self.store, self.control, self.resources,
                                     self.evidence, self.authority, failpoint)
        try:
            RecoveryCoordinator(self.store, self.resources).recover()
        except BaseException:
            self.store.close()
            raise

    def manifest(self):
        with self.store.mutex:
            return self.control.read()

    def close(self):
        self.store.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
