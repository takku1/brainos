"""Runtime dependency closure (Doc 29 section 29.4, Doc 32 section 32.9).

Same semantics as the reference model in tools/dep_closure.py, which is the
conformance oracle (tests/test_cumulative.py ClosureConformance): directional
dependency edges plus symmetric footprint-tag intersections, iterated to a
fixed point; unknown footprints intersect everything; verified isolation
removes only its own tags. Failing to converge is a fault, never "no impact".
"""
from .contracts import Refused


def compute_closure(seed, edges, footprints, isolation=None, unknown="intersect-all", cap=None):
    seed = set(seed)
    if not seed:
        return frozenset(), 0
    edges = list(edges)
    footprints = {n: set(f) for n, f in footprints.items()}
    isolation = {n: set(v) for n, v in (isolation or {}).items()}
    nodes = set(footprints) | {n for e in edges for n in e} | seed
    cap = max(len(nodes), 1) if cap is None else cap
    if not isinstance(cap, int) or cap < 0:
        raise Refused("closure iteration cap must be a nonnegative integer")

    def tags(n):
        if n not in footprints:
            if unknown == "intersect-all":
                return None
            raise Refused(f"unknown footprint: {n}")
        return footprints[n] - isolation.get(n, set())

    affected = set(seed)
    for iteration in range(cap + 1):
        grown = set(affected)
        grown.update(dependent for dependent, dependency in edges if dependency in affected)
        member_tags = [tags(m) for m in affected]
        if any(t is None for t in member_tags):
            grown |= nodes
        else:
            union = set().union(*member_tags)
            for n in nodes - grown:
                t = tags(n)
                if t is None or t & union:
                    grown.add(n)
        if grown == affected:
            return frozenset(affected), iteration
        affected = grown
    raise Refused("dependency closure did not converge within its cap; fail closed")


IMPACT_CLASSES = {
    # class: (footprint key or None for dependency-only, default action)
    "support": (None, "block"),
    "contract": (None, "block"),
    "unknown": ("*", "block"),
    "resources": ("resources", "reevaluate"),
    "failure_domains": ("failure_domains", "reevaluate"),
}


def population_closure(providers, changed, kind):
    """Closure over a pinned provider population for one impact class."""
    if kind not in IMPACT_CLASSES:
        raise Refused("unknown impact class")
    key, action = IMPACT_CLASSES[kind]
    edges = [(row["id"], dep) for row in providers.values() if row["kind"] == "graph"
             for dep in row["transitive_dependencies"]]
    if key is None:
        footprints = {pid: set() for pid in providers}
    elif key == "*":
        footprints = {pid: set() for pid in providers if pid not in changed}
    else:
        footprints = {pid: {f"{key}:{tag}" for tag in row["footprint"][key]} for pid, row in providers.items()}
    affected, _ = compute_closure(changed, edges, footprints)
    return sorted(affected), action
