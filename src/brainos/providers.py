"""Independently identified, explicitly versioned trusted primitive artifacts."""
from bisect import bisect_left, bisect_right
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
import inspect
import json
import re
import time
from .contracts import Refused, digest, encode

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


def exact_batch(value):
    if (not isinstance(value, dict) or set(value) != {"data", "queries"}
            or not isinstance(value["data"], list) or len(value["data"]) > 20000
            or any(type(x) is not int or abs(x) > 2**63 - 1 for x in value["data"])
            or not isinstance(value["queries"], list) or len(value["queries"]) > 4000
            or any(type(k) is not int for k in value["queries"])):
        raise Refused("expected <=20000 integers and <=4000 integer keys")
    return value


def check(kind, value):
    if kind == "text":
        if not isinstance(value, str) or len(value.encode()) > 32768:
            raise Refused("expected bounded UTF-8 text")
    elif kind == "integers":
        int_list(value)
    elif kind == "range-batch":
        range_batch(value)
    elif kind == "exact-batch":
        exact_batch(value)
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


def normalize_ws(value):
    return " ".join(value.split())


def parse_nl_sum(value):
    """Canonical natural-language sums to a typed intermediate representation."""
    match = re.match(r"^\s*add\s+up\s+(-?\d+)\s*(?:,|\band\b)\s*(-?\d+)\s*\.?\s*$",
                     value, re.IGNORECASE)
    if not match:
        raise Refused("not a canonical sum request")
    return json.dumps({"operation": "sum", "values": [int(match.group(1)), int(match.group(2))]})


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


# --- staged primitives: a declared `prepare` stage builds a structure from the
# data alone; `answer` uses it. Identical prepare stages may share structures.
def prepare_hash(data):
    return Counter(data)


def prepare_sorted(data):
    return sorted(data)


def exact_on_hash(index, queries):
    return [index.get(k, 0) for k in queries]


def exact_on_dict(index, queries):
    return [index[k] if k in index else 0 for k in queries]


def prepare_dict(data):
    counts = {}
    for x in data:
        counts[x] = counts.get(x, 0) + 1
    return counts


def exact_on_sorted(index, queries):
    return [bisect_right(index, k) - bisect_left(index, k) for k in queries]


def exact_on_scan(data, queries):
    return [data.count(k) for k in queries]


def range_on_sorted(index, queries):
    return [bisect_right(index, hi) - bisect_left(index, lo) for lo, hi in queries]


def range_on_hash(index, queries):
    return [sum(index.get(v, 0) for v in range(lo, hi + 1)) for lo, hi in queries]


def range_on_scan(data, queries):
    return [sum(1 for x in data if lo <= x <= hi) for lo, hi in queries]


@dataclass(frozen=True)
class Primitive:
    function: object
    input: str
    output: str
    capability: str
    version: str = "1"
    attempts: int = 1
    resources: tuple = ("cpu",)
    prepare: object = None          # staged primitives: data -> structure (shared by identity)
    split: bool = False             # answer signature is (data, queries) with no prepare stage
    internal_state: bool = False    # builds a structure inside the answer stage (undeclared prepare)


PRIMITIVES = {
    "parse_csv": Primitive(parse_csv, "text", "integers", "parse-integers"),
    "sum": Primitive(sum_builtin, "integers", "integer", "sum-integers"),
    "sum_loop": Primitive(sum_loop, "integers", "integer", "sum-integers"),
    "count": Primitive(count_items, "integers", "integer", "count-integers"),
    "text_length": Primitive(text_length, "text", "integer", "text-length"),
    "normalize_ws": Primitive(normalize_ws, "text", "text", "text-normalize"),
    "parse_nl_sum": Primitive(parse_nl_sum, "text", "text", "nl-arith"),
    "negate": Primitive(negate, "integer", "integer", "negate-integer"),
    "double": Primitive(double, "integer", "integer", "double-integer"),
    "range_scan": Primitive(range_scan, "range-batch", "integers", "range-count"),
    "range_scan_list": Primitive(range_scan_list, "range-batch", "integers", "range-count",
                                   resources=("cpu", "list-buffer")),
    "range_bisect": Primitive(range_bisect, "range-batch", "integers", "range-count",
                              resources=("cpu", "sort-buffer"), internal_state=True),
    "range_hash": Primitive(range_hash, "range-batch", "integers", "range-count",
                            resources=("cpu", "hash-table"), internal_state=True),
    # Staged lookup family (assimilation experiments): `function` is the answer stage.
    "exact_hash": Primitive(exact_on_hash, "exact-batch", "integers", "exact-count",
                            resources=("cpu", "hash-table"), prepare=prepare_hash),
    "exact_dict": Primitive(exact_on_dict, "exact-batch", "integers", "exact-count",
                            resources=("cpu", "dict-table"), prepare=prepare_dict),
    "exact_sorted": Primitive(exact_on_sorted, "exact-batch", "integers", "exact-count",
                              resources=("cpu", "sort-buffer"), prepare=prepare_sorted),
    "exact_scan": Primitive(exact_on_scan, "exact-batch", "integers", "exact-count", split=True),
    "range_sorted": Primitive(range_on_sorted, "range-batch", "integers", "range-count",
                              resources=("cpu", "sort-buffer"), prepare=prepare_sorted),
    "range_hash_index": Primitive(range_on_hash, "range-batch", "integers", "range-count",
                                  resources=("cpu", "hash-table"), prepare=prepare_hash),
    "range_scan_staged": Primitive(range_on_scan, "range-batch", "integers", "range-count", split=True),
}
CATALOG = {name: (entry.input, entry.output, entry.capability) for name, entry in PRIMITIVES.items()}


@lru_cache(maxsize=512)
def code_identity(function):
    """Digest of a function's source; cached per function object (a patched or
    edited function is a different object and is hashed afresh)."""
    return digest(inspect.getsource(function).replace("\r\n", "\n"))


def prepare_identity(entry):
    """Shared-structure identity: same prepare code means interchangeable structures."""
    return None if entry.prepare is None else f"{entry.prepare.__name__}:{code_identity(entry.prepare)[:16]}"


def specification(name):
    if name not in PRIMITIVES:
        raise Refused("implementation is not in the trusted catalogue")
    entry = PRIMITIVES[name]
    if type(entry.attempts) is not int or entry.attempts < 1:
        raise Refused("trusted primitive execution cost must be positive")
    dependencies = {"schema-check/v1": code_identity(check), "int-list/v1": code_identity(int_list)}
    if "range-batch" in (entry.input, entry.output):
        dependencies["range-batch/v1"] = code_identity(range_batch)
    if "exact-batch" in (entry.input, entry.output):
        dependencies["exact-batch/v1"] = code_identity(exact_batch)
    if entry.prepare is not None:
        dependencies["prepare/" + entry.prepare.__name__] = code_identity(entry.prepare)
    core = dict(kind="primitive", implementation=name, version=entry.version,
                code=code_identity(entry.function), dependencies=dependencies,
                input=entry.input, output=entry.output, capability=entry.capability,
                input_unit="utf8" if entry.input == "text" else "dimensionless",
                output_unit="utf8" if entry.output == "text" else "dimensionless",
                cost={"attempts": entry.attempts}, engine_abi="trusted-unary/v1",
                prepare=prepare_identity(entry),
                footprint={"resources": sorted(entry.resources), "failure_domains": ["trusted-python"]})
    if entry.internal_state:
        core["internal_state"] = True   # added only when true, so other identities are unchanged
    artifact = digest(core)
    return dict(core, artifact=artifact, id=f"{name}@{entry.version}:{artifact}")


def compute(name, value):
    return timed_compute(specification(name), value)[0]


_PREPARED = {}            # (prepare identity, data identity) -> (structure, encoded bytes)
_PREPARED_LIMIT = 8


def clear_prepared():
    _PREPARED.clear()


def structure_bytes(structure):
    if isinstance(structure, dict):
        return len(encode(sorted(structure.items())))
    return len(encode(structure))


def timed_compute(spec, value):
    """Run a verified primitive; the timed regions are the provider stages only.

    Returns (result, timing) where timing has compute_ns and, for staged
    primitives, prepare_ns (0 on a cache hit), answer_ns, cache_hit and
    state_bytes (encoded size of the structure used).
    """
    check(spec["input"], value)
    entry = PRIMITIVES[spec["implementation"]]
    if entry.prepare is None:
        started = time.perf_counter_ns()
        if entry.split:
            result = entry.function(value["data"], value["queries"])
        else:
            result = entry.function(value)
        elapsed = time.perf_counter_ns() - started
        check(spec["output"], result)
        return result, dict(compute_ns=elapsed, prepare_ns=0, answer_ns=elapsed, cache_hit=None, state_bytes=0)
    data = value["data"]
    lookup_started = time.perf_counter_ns()
    key = (spec["prepare"], len(data), hash(tuple(data)))
    hit = key in _PREPARED
    lookup_ns = time.perf_counter_ns() - lookup_started
    prepare_ns = 0
    if hit:
        structure, size = _PREPARED[key]
    else:
        started = time.perf_counter_ns()
        structure = entry.prepare(data)
        prepare_ns = time.perf_counter_ns() - started
        size = structure_bytes(structure)
        if len(_PREPARED) >= _PREPARED_LIMIT:
            _PREPARED.pop(next(iter(_PREPARED)))
        _PREPARED[key] = (structure, size)
    started = time.perf_counter_ns()
    result = entry.function(structure, value["queries"])
    answer_ns = time.perf_counter_ns() - started
    check(spec["output"], result)
    return result, dict(compute_ns=prepare_ns + answer_ns, prepare_ns=prepare_ns, answer_ns=answer_ns,
                        lookup_ns=lookup_ns, cache_hit=hit, state_bytes=size)
