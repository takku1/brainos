"""Reference dependency-closure algorithm for BrainOS (Doc 32 §32.9).

Conservative fixed-point computation over graph dependencies and
interference footprints. This is a reference model for conformance
testing, not production infrastructure.
"""
from __future__ import annotations


class ClosureFault(Exception):
    """Raised when closure cannot be bounded (fail closed, never publish)."""


def compute_closure(seed, edges, footprints, isolation=None, unknown="intersect-all", cap=None):
    """Fixed-point affected set.

    seed: iterable of initially affected node ids.
    edges: iterable of (dependent, dependency) — change in `dependency`
      invalidates `dependent` (one direction only).
    footprints: {node: set(str tags)} — shared tags mean symmetric interference.
    isolation: {node: set(tags)} — verified scope exclusions for that node.
    unknown: how to treat nodes with no footprint entry;
      "intersect-all" (default, conservative) or "raise".
    cap: iteration bound; default = number of known nodes.
    Returns (frozenset affected, iterations used).
    """
    seed = set(seed)
    if not seed:
        return frozenset(), 0
    edges = list(edges)
    footprints = {n: set(f) for n, f in footprints.items()}
    isolation = {n: set(v) for n, v in (isolation or {}).items()}
    nodes = set(footprints) | {n for e in edges for n in e} | set(seed)
    if cap is None:
        cap = max(len(nodes), 1)
    if not isinstance(cap, int) or cap < 0:
        raise ClosureFault("iteration cap must be a nonnegative integer")

    def tags(n):
        if n not in footprints:
            if unknown == "intersect-all":
                return None  # sentinel: intersects everything
            raise ClosureFault(f"unknown footprint: {n}")
        iso = isolation.get(n, set())
        return set(footprints[n]) - iso

    affected = set(seed)
    # seed members with unknown footprints are affected by definition; their
    # spread covers everything (conservative), which the loop below handles
    # by treating an unknown footprint as intersecting all tags.
    for _ in range(cap + 1):
        grown = set(affected)
        # directional propagation: dependency in set -> dependent joins
        for dependent, dependency in edges:
            if dependency in affected:
                grown.add(dependent)
        # symmetric propagation: shared tag with any affected member
        affected_tags = set()
        unknown_present = False
        for m in affected:
            t = tags(m)
            if t is None:
                unknown_present = True
            else:
                affected_tags |= t
        if unknown_present:
            grown |= set(nodes)
        else:
            for n in nodes:
                if n in grown:
                    continue
                t = tags(n)
                if t is None:
                    grown.add(n)  # unknown: assume affected
                elif t & affected_tags:
                    grown.add(n)
        if grown == affected:
            return frozenset(affected), _
        affected = grown
    raise ClosureFault("closure did not converge within cap")


def _check(name, cond, detail=""):
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))
    return bool(cond)


def self_test():
    ok = True
    # P1: direct + transitive dependency.
    s, _ = compute_closure({"B"}, [("A", "B"), ("C", "A")],
                           {"A": {"e"}, "B": {"e"}, "C": {"e"}})
    ok &= _check("P1 transitive", s == {"A", "B", "C"}, sorted(s))
    # P2: symmetric interference through a shared tag, no edge.
    s, _ = compute_closure({"X"}, [], {"X": {"gpu0"}, "Y": {"gpu0"}, "Z": {"cpu"}})
    ok &= _check("P2 symmetric", s == {"X", "Y"}, sorted(s))
    # P3: unknown footprint is conservative — an unknown member of the
    # affected set pulls in every known node (intersects everything).
    s, _ = compute_closure({"ghost"}, [], {"X": {"gpu0"}, "Y": {"cpu"}})
    ok &= _check("P3 unknown-conservative", s == {"ghost", "X", "Y"}, sorted(s))
    # N1: directional — change at dependent does not pull dependency.
    s, _ = compute_closure({"A"}, [("A", "B")],
                           {"A": {"ta"}, "B": {"tb"}})
    ok &= _check("N1 directional", s == {"A"}, sorted(s))
    # N2: scoped isolation excludes verified scope.
    s, _ = compute_closure({"X"}, [],
                           {"X": {"gpu0"}, "Y": {"gpu0"}},
                           isolation={"Y": {"gpu0"}})
    ok &= _check("N2 isolation", s == {"X"}, sorted(s))
    # N3: empty seed, disjoint footprints -> empty closure (no over-claim).
    s, _ = compute_closure(set(), [], {"A": {"a"}, "B": {"b"}})
    ok &= _check("N3 empty-seed", s == set(), sorted(s))
    # P4: cycle terminates at fixed point, no infinite loop.
    s, n = compute_closure({"A"}, [("A", "B"), ("B", "A")],
                           {"A": {"a"}, "B": {"b"}})
    ok &= _check("P4 cycle-terminates", s == {"A", "B"}, f"iters={n}")
    # N4: unknown node with strict policy raises instead of guessing.
    try:
        compute_closure({"ghost"}, [], {"known": {"t"}}, unknown="raise")
        ok &= _check("N4 unknown-strict", False, "no error raised")
    except ClosureFault:
        ok &= _check("N4 unknown-strict", True, "ClosureFault raised")
    print(f"\n{'ALL PASS' if ok else 'FAILURES PRESENT'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(self_test())
