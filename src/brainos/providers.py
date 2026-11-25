"""Trusted deterministic provider catalogue for the first profile.

No dynamic imports, eval, pickles, model framework, or arbitrary user code.
Catalogue entries use an artifact digest independent of provider self-report.
"""
import hashlib
from pathlib import Path

from .contracts import Refused, digest


def int_list(value):
    if (not isinstance(value, list) or len(value) > 4096
            or any(type(x) is not int or abs(x) > 2**63 - 1 for x in value)):
        raise Refused("expected at most 4096 signed 63-bit integers")
    return value


def check(kind, value):
    if kind == "text":
        if not isinstance(value, str) or len(value.encode()) > 32768:
            raise Refused("expected bounded UTF-8 text")
    elif kind == "integers":
        int_list(value)
    elif kind == "integer":
        if type(value) is not int:
            raise Refused("expected an integer")
    else:
        raise Refused("unsupported schema")


CATALOG = {
    "parse_csv": ("text", "integers", "parse-integers"),
    "sum": ("integers", "integer", "sum-integers"),
    "sum_loop": ("integers", "integer", "sum-integers"),
    "count": ("integers", "integer", "count-integers"),
}


def specification(name):
    if name not in CATALOG:
        raise Refused("implementation is not in the trusted catalogue")
    inp, out, capability = CATALOG[name]
    source = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    artifact = digest([name, source, inp, out, capability])
    return dict(id=f"{name}:{artifact}", implementation=name, artifact=artifact,
                input=inp, output=out, capability=capability)


def compute(name, value):
    spec = specification(name)
    check(spec["input"], value)
    if name == "parse_csv":
        result = [] if not value.strip() else [int(x.strip()) for x in value.split(",")]
    elif name == "sum":
        result = sum(value)
    elif name == "sum_loop":
        result = 0
        for item in value:
            result += item
    else:
        result = len(value)
    check(spec["output"], result)
    return result
