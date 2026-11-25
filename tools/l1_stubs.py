"""Minimal stub providers and supervisors for the L1 conformance harness.

Stubs, not an implementation: deterministic, in-memory, single-threaded.
Each check in tools/l1_harness.py pairs a conforming stub (must pass)
with a defective twin (must be rejected) where applicable.
"""
from __future__ import annotations
from itertools import count


_INSTANCE_IDS = count(1)


ENVELOPE_KEYS = {"contract", "version", "schema", "freshness",
                 "tier", "cost", "quality", "support_refs"}


class Provider:
    def __init__(self, name, capabilities, version="v1", epoch=1,
                 quarantined=False):
        self.name = name
        self.instance_id = next(_INSTANCE_IDS)
        self.capabilities = list(capabilities)
        self.version = version
        self.epoch = epoch
        self.quarantined = quarantined
        self.state = {}

    def contract_id(self):
        return f"{self.capabilities[0]}:{self.version}"


class CalculatorV1(Provider):
    def __init__(self, **kw):
        super().__init__("calc-v1", ["arithmetic"], **kw)

    def compute(self, op, a, b):
        if op == "add":
            return a + b
        if op == "mul":
            return a * b
        raise ValueError(f"unsupported op {op}")


class CalculatorV2(Provider):
    """Independent implementation of the same contract (different code)."""

    def __init__(self, **kw):
        super().__init__("calc-v2", ["arithmetic"], **kw)

    def compute(self, op, a, b):
        table = {"add": lambda: a + b, "mul": lambda: a * b}
        if op not in table:
            raise ValueError(f"unsupported op {op}")
        return table[op]()


class StaleCalculator(CalculatorV1):
    """Defective twin: advertises v2 while executing v1 logic/epochs."""

    def __init__(self, **kw):
        super().__init__(**kw)
        self.name = "calc-stale"
        self.version = "v2"  # lies about version


class Supervisor:
    """Honest supervisor: reads only envelope fields. Audits accesses."""

    def __init__(self):
        self.accessed = []

    def _get(self, envelope, key):
        assert key in ENVELOPE_KEYS, f"non-envelope access: {key}"
        self.accessed.append(key)
        return envelope.get(key)

    def decide(self, action, envelope, manifest):
        tier = self._get(envelope, "tier")
        contract = self._get(envelope, "contract")
        version = self._get(envelope, "version")
        if contract not in manifest["contracts"]:
            return ("deny", "unknown-contract")
        if version not in manifest["contracts"][contract]:
            return ("deny", "unlisted-version")
        if action["irreversible"] and tier != "Certified":
            return ("deny", "tier-insufficient")
        return ("permit", manifest["epoch"])


class SnoopingSupervisor(Supervisor):
    """Defective twin: reaches into payload bytes to decide."""

    def decide(self, action, envelope, manifest):
        payload = envelope.get("payload_bytes", b"")  # noqa: F841 — the violation
        self.accessed.append("payload_bytes")
        return super().decide(action, envelope, manifest)


PERMITS = {}
INVOCATIONS = {}
_INVOCATION_IDS = count(1)


def make_permit(provider, epoch, tier, operation="compute", principal="test",
                context="default"):
    """Trusted test fixture for issuance; not a production AUTHORIZE API."""
    p = {"provider": provider.instance_id, "version": provider.version,
         "operation": operation, "principal": principal, "context": context,
         "epoch": epoch, "tier": tier,
         "revoked": False, "scope": "full"}
    PERMITS[id(p)] = (p, dict(p))
    return p


def revoke_permit(permit):
    record = PERMITS.get(id(permit))
    if record is None or record[0] is not permit or record[1] != permit:
        return ("refuse", "unissued-or-modified-permit")
    permit["revoked"] = True
    permit["scope"] = "drain-only"
    record[1].update(revoked=True, scope="drain-only")
    return ("ok", None)


def act(provider, permit, epoch, side_effect=False, reauthorized=False,
        operation="compute", principal="test", context="default",
        invocation=None):
    """Start or drain a simulated invocation. No real external effects.

    Authority is stored independently from caller-visible handles. A fresh
    side effect requires a separate, live permit handle as reauthorization;
    a caller-supplied boolean cannot authorize it. Drain never creates effects.
    """
    record = PERMITS.get(id(permit))
    if record is None or record[0] is not permit or record[1] != permit:
        return ("refuse", "unissued-or-modified-permit")
    expected = (provider.instance_id, provider.version, operation, principal, context)
    bound = tuple(permit[k] for k in
                  ("provider", "version", "operation", "principal", "context"))
    if bound != expected:
        return ("refuse", "scope-mismatch")
    if provider.quarantined:
        return ("refuse", "quarantined")
    if epoch != permit["epoch"]:
        return ("refuse", "stale-epoch")
    if invocation is not None:
        active = INVOCATIONS.get(invocation)
        if active != (id(permit), bound, epoch):
            return ("refuse", "unknown-or-completed-invocation")
        if side_effect:
            return ("refuse", "drain-cannot-create-effect")
        return ("ok", invocation)
    if permit["revoked"] or permit["scope"] != "full":
        return ("refuse", "revoked")
    if side_effect:
        fresh = PERMITS.get(id(reauthorized))
        if (fresh is None or fresh[0] is not reauthorized
                or fresh[1] != reauthorized or reauthorized is permit
                or reauthorized["revoked"] or reauthorized["scope"] != "full"
                or reauthorized["epoch"] != epoch
                or reauthorized["tier"] != "Certified"
                or tuple(reauthorized[k] for k in
                         ("provider", "version", "operation", "principal", "context")) != bound):
            return ("refuse", "reauth-required")
    invocation_id = next(_INVOCATION_IDS)
    INVOCATIONS[invocation_id] = (id(permit), bound, epoch)
    return ("ok", invocation_id)


def complete(invocation):
    return INVOCATIONS.pop(invocation, None) is not None


def admit_provider(provider, artifacts):
    """Compare instance identity against a trusted artifact registry fixture."""
    expected = artifacts.get(provider.instance_id)
    if expected != (type(provider), provider.version):
        return ("refuse", "artifact-version-mismatch")
    return ("ok", None)
