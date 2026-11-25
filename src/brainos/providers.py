"""Independently identified, explicitly versioned trusted primitive artifacts."""
from dataclasses import dataclass
import inspect
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


def parse_csv(value):
    return [] if not value.strip() else [int(x.strip()) for x in value.split(",")]


def sum_builtin(value):
    return sum(value)


def sum_loop(value):
    result = 0
    for item in value:
        result += item
    return result


def count_items(value):
    return len(value)


def text_length(value):
    return len(value)


def negate(value):
    return -value


@dataclass(frozen=True)
class Primitive:
    function: object
    input: str
    output: str
    capability: str
    version: str = "1"
    attempts: int = 1


PRIMITIVES = {
    "parse_csv": Primitive(parse_csv, "text", "integers", "parse-integers"),
    "sum": Primitive(sum_builtin, "integers", "integer", "sum-integers"),
    "sum_loop": Primitive(sum_loop, "integers", "integer", "sum-integers"),
    "count": Primitive(count_items, "integers", "integer", "count-integers"),
    "text_length": Primitive(text_length, "text", "integer", "text-length"),
    "negate": Primitive(negate, "integer", "integer", "negate-integer"),
}
CATALOG = {name: (entry.input, entry.output, entry.capability) for name, entry in PRIMITIVES.items()}


def code_identity(function):
    return digest(inspect.getsource(function).replace("\r\n", "\n"))


def specification(name):
    if name not in PRIMITIVES:
        raise Refused("implementation is not in the trusted catalogue")
    entry = PRIMITIVES[name]
    if type(entry.attempts) is not int or entry.attempts < 1:
        raise Refused("trusted primitive execution cost must be positive")
    dependencies = {"schema-check/v1": code_identity(check), "int-list/v1": code_identity(int_list)}
    core = dict(kind="primitive", implementation=name, version=entry.version,
                code=code_identity(entry.function), dependencies=dependencies,
                input=entry.input, output=entry.output, capability=entry.capability,
                input_unit="utf8" if entry.input == "text" else "dimensionless",
                output_unit="utf8" if entry.output == "text" else "dimensionless",
                cost={"attempts": entry.attempts}, engine_abi="trusted-unary/v1",
                footprint={"resources": ["cpu"], "failure_domains": ["trusted-python"]})
    artifact = digest(core)
    return dict(core, artifact=artifact, id=f"{name}@{entry.version}:{artifact}")


def compute(name, value):
    spec = specification(name)
    check(spec["input"], value)
    result = PRIMITIVES[name].function(value)
    check(spec["output"], result)
    return result
