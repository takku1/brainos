"""Bounded unary DAG contracts, explicit lowering and execution.

No authority or publication policy lives here. A node may reference a
primitive or an active composite; composites are lowered (inlined) into
primitive nodes so execution never recurses into nested graphs. The authored
nodes are kept as `source_nodes` so the registry can recompute and verify the
lowering from its inputs.
"""
import time
from .contracts import Cancelled, Refused, digest
from .providers import check

MAX_LOWERED_NODES = 16


def unit(schema):
    return "utf8" if schema == "text" else "dimensionless"


def compatible(source, source_unit, target, target_unit, adapter="identity"):
    if adapter != "identity" or source != target or source_unit != target_unit:
        raise Refused("connection needs exact semantic schema/units; unsupported adapter")


def _reachable(nodes, output):
    """Node ids that contribute to `output` (backward reachability)."""
    sources = {node["id"]: node["input"] for node in nodes}
    needed, frontier = set(), output
    while frontier in sources and frontier not in needed:
        needed.add(frontier)
        frontier = sources[frontier]
    return needed


def specification(definition, capability, resolve):
    authored = definition.get("source_nodes", definition.get("nodes", []))
    if not isinstance(authored, list) or not 1 <= len(authored) <= MAX_LOWERED_NODES:
        raise Refused("graph requires 1..16 bounded nodes")
    inp, out = definition["input"], definition["output"]
    input_unit = definition.get("input_unit", unit(inp))
    output_unit = definition.get("output_unit", unit(out))
    values = {"$input": (inp, input_unit)}
    source_nodes, lowered, direct, transitive = [], [], [], set()
    resources, domains, cost = set(), set(), 0
    for node in authored:
        name, ref, source = node["id"], node["provider"], node["input"]
        if (not isinstance(name, str) or not name or "/" in name or name in values
                or source not in values):
            raise Refused("duplicate node or forward/cyclic/wrong-kind input reference")
        spec = resolve(ref)
        compatible(*values[source], spec["input"], spec["input_unit"], node.get("adapter", "identity"))
        source_nodes.append(dict(id=name, provider=ref, input=source, adapter="identity"))
        direct.append(ref)
        if spec["kind"] == "primitive":
            lowered.append(dict(id=name, provider=ref, input=source, adapter="identity"))
            transitive.add(ref)
        elif spec["kind"] == "graph":
            # Inline the nested lowering under a prefixed namespace.
            rename = {"$input": source}
            for inner in spec["nodes"]:
                rename[inner["id"]] = f"{name}/{inner['id']}"
                lowered.append(dict(id=rename[inner["id"]], provider=inner["provider"],
                                    input=rename[inner["input"]], adapter="identity"))
            # The composite's result is its output node's value, published as `name`.
            # Unary nodes that all reach the output form a chain, so it is last.
            if rename[spec["output_node"]] != lowered[-1]["id"]:
                raise Refused("nested composite output must be its final lowered node")
            lowered[-1]["id"] = name
            transitive.update(spec["transitive_dependencies"])
            transitive.add(ref)
        else:
            raise Refused("unknown provider kind")
        if len(lowered) > MAX_LOWERED_NODES:
            raise Refused("lowered graph exceeds 16 primitive nodes")
        values[name] = (spec["output"], spec["output_unit"])
        cost += spec["cost"]["attempts"]
        resources.update(spec["footprint"]["resources"])
        domains.update(spec["footprint"]["failure_domains"])
    output = definition["output_node"]
    if output not in values or output == "$input":
        raise Refused("output must resolve to a graph result")
    if _reachable(source_nodes, output) != {node["id"] for node in source_nodes}:
        raise Refused("every node must contribute to the output node")
    compatible(*values[output], out, output_unit)
    core = dict(kind="graph", implementation="typed-dag", version="2", input=inp,
                output=out, input_unit=input_unit, output_unit=output_unit,
                capability=capability, source_nodes=source_nodes, nodes=lowered,
                output_node=output, dependencies=sorted(set(direct)),
                transitive_dependencies=sorted(transitive), cost={"attempts": cost},
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
        if provider["kind"] != "primitive":
            raise Refused("lowered graphs execute primitive nodes only")
        result = compute(provider, values[node["input"]], remaining)
        values[node["id"]] = result
        if on_result:
            on_result(dict(node=node["id"], provider=provider["id"], source=node["input"],
                           schema=provider["output"], unit=provider["output_unit"],
                           value=result, value_digest=digest(result), dependencies=[provider["id"]]))
    result = values[spec["output_node"]]
    check(spec["output"], result)
    return result
