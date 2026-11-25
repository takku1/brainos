"""Bounded unary DAG contracts and execution; no authority or publication policy."""
import time
from .contracts import Cancelled, Refused, digest
from .providers import check


def unit(schema):
    return "utf8" if schema == "text" else "dimensionless"


def compatible(source, source_unit, target, target_unit, adapter="identity"):
    if adapter != "identity" or source != target or source_unit != target_unit:
        raise Refused("connection needs exact semantic schema/units; unsupported adapter")


def specification(definition, capability, resolve):
    nodes = definition.get("nodes", [])
    if not isinstance(nodes, list) or not 1 <= len(nodes) <= 16:
        raise Refused("graph requires 1..16 bounded nodes")
    inp, out = definition["input"], definition["output"]
    input_unit = definition.get("input_unit", unit(inp))
    output_unit = definition.get("output_unit", unit(out))
    values = {"$input": (inp, input_unit)}
    normalized, dependencies = [], []
    resources, domains, cost = set(), set(), 0
    for node in nodes:
        name, ref, source = node["id"], node["provider"], node["input"]
        if not isinstance(name, str) or not name or name in values or source not in values:
            raise Refused("duplicate node or forward/cyclic/wrong-kind input reference")
        spec = resolve(ref)
        if spec["kind"] != "primitive":
            raise Refused("nested graphs require an explicit lowering; first profile accepts primitive nodes")
        compatible(*values[source], spec["input"], spec["input_unit"], node.get("adapter", "identity"))
        normalized.append(dict(id=name, provider=ref, input=source, adapter="identity"))
        values[name] = (spec["output"], spec["output_unit"])
        dependencies.append(ref)
        cost += spec["cost"]["attempts"]
        resources.update(spec["footprint"]["resources"])
        domains.update(spec["footprint"]["failure_domains"])
    output = definition["output_node"]
    if output not in values or output == "$input":
        raise Refused("output must resolve to a graph result")
    compatible(*values[output], out, output_unit)
    core = dict(kind="graph", implementation="typed-dag", version="1", input=inp,
                output=out, input_unit=input_unit, output_unit=output_unit,
                capability=capability, nodes=normalized, output_node=output,
                dependencies=sorted(set(dependencies)), cost={"attempts": cost},
                footprint={"resources": sorted(resources), "failure_domains": sorted(domains)},
                engine_abi="trusted-unary/v1")
    artifact = digest(core)
    return dict(core, id="graph:" + artifact, artifact=artifact)


def execute(spec, value, resolve, compute, timeout, *, on_result=None, cancelled=None):
    deadline = time.monotonic() + timeout
    check(spec["input"], value)
    values = {"$input": value}
    for node in spec["nodes"]:
        if cancelled and cancelled():
            raise Cancelled("cancelled at graph node boundary")
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise Refused("graph exceeded its shared wall-clock bound")
        provider = resolve(node["provider"])
        result = compute(provider, values[node["input"]], remaining)
        values[node["id"]] = result
        if on_result:
            on_result(dict(node=node["id"], provider=provider["id"], source=node["input"],
                           schema=provider["output"], unit=provider["output_unit"],
                           value=result, value_digest=digest(result), dependencies=[provider["id"]]))
    result = values[spec["output_node"]]
    check(spec["output"], result)
    return result
