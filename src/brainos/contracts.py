"""Serialization and errors shared by the runtime and worker boundary."""
import hashlib
import json
import math
from dataclasses import dataclass
from uuid import uuid4
from typing import Protocol, TypedDict


class Refused(ValueError):
    """A request failed an explicit admission or execution constraint."""


class Unresolved(Refused):
    """An outcome is uncertain; it is unsafe to infer failure or retry."""


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(encode(value).encode("utf-8")).hexdigest()


def uid():
    return uuid4().hex


def positive_time(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        raise Refused("time bound must be finite and positive")
    return value


def quantities(value):
    if not isinstance(value, dict) or not value:
        raise Refused("a nonempty resource vector is required")
    if any(not isinstance(k, str) or not k or type(v) is not int or v < 0
           for k, v in value.items()):
        raise Refused("resource quantities must be nonnegative integers")
    return dict(value)


def require_owner(record, principal):
    if record["principal"] != principal:
        raise Refused("principal mismatch")


class ProviderSpec(TypedDict):
    id: str
    implementation: str
    artifact: str
    input: str
    output: str
    capability: str


class EffectReceipt(TypedDict):
    operation_id: str
    payload_digest: str
    payload: object


class ProviderRunner(Protocol):
    def compute(self, spec: ProviderSpec, value: object, timeout: float) -> object: ...


class ReceiptEndpoint(Protocol):
    name: str

    def apply(self, operation_id: str, payload: object) -> EffectReceipt: ...

    def lookup(self, operation_id: str) -> EffectReceipt | None: ...


@dataclass(frozen=True)
class PermitScope:
    """Control-plane projection: signal bytes never enter the authority service."""
    kind: str
    target: str
    principal: str
    content_digest: str
    provider: str
    context: str
    operation: str
