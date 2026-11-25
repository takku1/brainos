"""Independently identified, explicitly versioned trusted primitive artifacts."""
from bisect import bisect_left, bisect_right
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
import inspect
import time
from .contracts import Refused, digest

MAX_WIDTH = 2**20


def int_list(value):
    if (not isinstance(value, list) or len(value) > 4096
            or any(type(x) is not int or abs(x) > 2**63 - 1 for x in value)):
        raise Refused("expected at most 4096 signed 63-bit integers")
    return value


def range_batch(value):
    if (not isinstance(value, dict) or set(value) != {"data", "queries"}
            or not isinstance(value["data"], list) or len(value["data"]) > 20000
            or any(type(x) is not int or abs(x) > 2**63 - 1 for x in value["data"])
            or not isinstance(value["queries"], list) or len(value["queries"]) > 2000
            or any(not isinstance(q, list) or len(q) != 2 or any(type(b) is not int for b in q)
                   or not 0 <= q[1] - q[0] <= MAX_WIDTH for q in value["queries"])):
        raise Refused("expected <=20000 integers and <=2000 [lo, hi] queries of width <= 2^20")
    return value


def check(kind, value):
    if kind == "text":
        if not isinstance(value, str) or len(value.encode()) > 32768:
            raise Refused("expected bounded UTF-8 text")
    elif kind == "integers":
        int_list(value)
    elif kind == "range-batch":
        range_batch(value)
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


def double(value):
    return 2 * value


def range_scan(value):
    data = value["data"]
    return [sum(1 for x in data if lo <= x <= hi) for lo, hi in value["queries"]]


def range_scan_list(value):
    data = list(value["data"])
    result = []
    for lo, hi in value["queries"]:
        result.append(len([x for x in data if lo <= x <= hi]))
    return result


def range_bisect(value):
    ordered = sorted(value["data"])
    return [bisect_right(ordered, hi) - bisect_left(ordered, lo) for lo, hi in value["queries"]]


def range_hash(value):
    counts = Counter(value["data"])
    return [sum(counts.get(v, 0) for v in range(lo, hi + 1)) for lo, hi in value["queries"]]


@dataclass(frozen=True)
class Primitive:
    function: object
    input: str
    output: str
    capability: str
    version: str = "1"
    attempts: int = 1
    resources: tuple = ("cpu",)


PRIMITIVES = {
    "parse_csv": Primitive(parse_csv, "text", "integers", "parse-integers"),
    "sum": Primitive(sum_builtin, "integers", "integer", "sum-integers"),
    "sum_loop": Primitive(sum_loop, "integers", "integer", "sum-integers"),
    "count": Primitive(count_items, "integers", "integer", "count-integers"),
    "text_length": Primitive(text_length, "text", "integer", "text-length"),
    "negate": Primitive(negate, "integer", "integer", "negate-integer"),
    "double": Primitive(double, "integer", "integer", "double-integer"),
    "range_scan": Primitive(range_scan, "range-batch", "integers", "range-count"),
    "range_scan_list": Primitive(range_scan_list, "range-batch", "integers", "range-count",
                                   resources=("cpu", "list-buffer")),
    "range_bisect": Primitive(range_bisect, "range-batch", "integers", "range-count",
                              resources=("cpu", "sort-buffer")),
    "range_hash": Primitive(range_hash, "range-batch", "integers", "range-count",
                            resources=("cpu", "hash-table")),
}
CATALOG = {name: (entry.input, entry.output, entry.capability) for name, entry in PRIMITIVES.items()}


@lru_cache(maxsize=512)
def code_identity(function):
    """Digest of a function's source; cached per function object (a patched or
    edited function is a different object and is hashed afresh)."""
    return digest(inspect.getsource(function).replace("\r\n", "\n"))


def specification(name):
    if name not in PRIMITIVES:
        raise Refused("implementation is not in the trusted catalogue")
    entry = PRIMITIVES[name]
    if type(entry.attempts) is not int or entry.attempts < 1:
        raise Refused("trusted primitive execution cost must be positive")
    dependencies = {"schema-check/v1": code_identity(check), "int-list/v1": code_identity(int_list)}
    if "range-batch" in (entry.input, entry.output):
        dependencies["range-batch/v1"] = code_identity(range_batch)
    core = dict(kind="primitive", implementation=name, version=entry.version,
                code=code_identity(entry.function), dependencies=dependencies,
                input=entry.input, output=entry.output, capability=entry.capability,
                input_unit="utf8" if entry.input == "text" else "dimensionless",
                output_unit="utf8" if entry.output == "text" else "dimensionless",
                cost={"attempts": entry.attempts}, engine_abi="trusted-unary/v1",
                footprint={"resources": sorted(entry.resources), "failure_domains": ["trusted-python"]})
    artifact = digest(core)
    return dict(core, artifact=artifact, id=f"{name}@{entry.version}:{artifact}")


def compute(name, value):
    return timed_compute(specification(name), value)[0]


def timed_compute(spec, value):
    """Run a verified primitive; the timed region is the provider function only."""
    check(spec["input"], value)
    function = PRIMITIVES[spec["implementation"]].function
    started = time.perf_counter_ns()
    result = function(value)
    elapsed = time.perf_counter_ns() - started
    check(spec["output"], result)
    return result, elapsed
