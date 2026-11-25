"""Bounded competitive ecology over one capability population (Doc 25).

Selection is contextual: a trusted featurizer assigns each workload a context,
and the policy keeps per-(context, member) cost evidence. Exploration is
funded: it happens only while the exploration budget can pay for it.

Retention rule (Doc 25 sections 25.3/25.12): a member may be retired only with
redundancy evidence. In every context the population has observed, the member
must have enough samples and some other active member must be at least as good
within `margin`. A specialist that is best anywhere, or has not been measured in
some observed context, is retained, however poor its aggregate cost. Lower
aggregate fitness alone is never grounds for retirement.

This module never issues funding and never mutates the manifest; BrainOS-side
effects go through the population (retire/restore) and task APIs.
"""
from dataclasses import dataclass, field
import random
from statistics import median


def featurize(workload):
    """Trusted context assignment from declared workload features (not from providers)."""
    queries = workload["queries"]
    widths = sorted(hi - lo for lo, hi in queries) or [0]
    q = len(queries)
    qband = "single" if q <= 2 else "few" if q <= 32 else "many"
    wband = "narrow" if widths[len(widths) // 2] <= 16 else "wide"
    return f"{qband}-{wband}"


@dataclass
class EcologyPolicy:
    members: list
    min_samples: int = 3
    margin: float = 0.10
    epsilon: float = 0.05
    seed: int = 0
    evidence: dict = field(default_factory=dict)   # (context, member) -> [(cost, revision)]
    contexts: list = field(default_factory=list)
    current: object = None                          # (member, revision) -> bool, from fabric
    prune_factor: float = None                      # v2: stop forced exploration of hopeless members
    archived: list = field(default_factory=list)

    def __post_init__(self):
        self.rng = random.Random(self.seed)
        self.members = list(self.members)

    def samples(self, context, member):
        rows = self.evidence.get((context, member), [])
        if self.current is not None:
            rows = [r for r in rows if self.current(member, r[1])]
        return [cost for cost, _ in rows]

    def estimate(self, context, member):
        values = self.samples(context, member)
        return median(values) if values else None

    def select(self, context, can_explore):
        """Return (member, exploring)."""
        if context not in self.contexts:
            self.contexts.append(context)
        if can_explore:
            known = [self.estimate(context, m) for m in self.members if self.samples(context, m)]
            order = self.members
            if self.prune_factor:   # v2: breadth-first, so pruning compares against measured rivals
                order = sorted(self.members, key=lambda m: len(self.samples(context, m)))
            for member in order:
                n = len(self.samples(context, member))
                if n >= self.min_samples:
                    continue
                if self.prune_factor and n and self.estimate(context, member) > self.prune_factor * min(known):
                    continue    # hopeless here; its insufficient evidence still blocks its retirement
                return member, True
        known = [(self.estimate(context, m), m) for m in self.members if self.samples(context, m)]
        if not known:
            return self.members[0], False
        best = min(known)[1]
        if can_explore and len(self.members) > 1 and self.rng.random() < self.epsilon:
            return self.rng.choice([m for m in self.members if m != best]), True
        return best, False

    def observe(self, context, member, cost, revision=0):
        self.evidence.setdefault((context, member), []).append((cost, revision))

    def best(self, context):
        known = [(self.estimate(context, m), m) for m in self.members if self.samples(context, m)]
        return min(known)[1] if known else None

    def contribution(self):
        return {m: [c for c in self.contexts if self.best(c) == m] for m in self.members}

    def retirement_evidence(self, member):
        per_context, justified = {}, bool(self.contexts) and member in self.members and len(self.members) > 1
        for context in self.contexts:
            mine = self.samples(context, member)
            if len(mine) < self.min_samples:
                per_context[context] = dict(verdict="insufficient-evidence", samples=len(mine))
                justified = False
                continue
            own = median(mine)
            rivals = {m: median(self.samples(context, m)) for m in self.members
                      if m != member and len(self.samples(context, m)) >= self.min_samples}
            covering = {m: v for m, v in rivals.items() if v <= own * (1 + self.margin)}
            per_context[context] = dict(own_median=own, covered_by=sorted(covering), rivals=rivals)
            if not covering:
                per_context[context]["verdict"] = "specialist"
                justified = False
            else:
                per_context[context]["verdict"] = "redundant"
        return dict(member=member, justified=justified, margin=self.margin,
                    min_samples=self.min_samples, contexts=per_context,
                    rule="redundant-within-margin-in-every-observed-context")

    def retirement_candidate(self):
        """The single most redundant member (worst aggregate among justified), or None."""
        justified = [self.retirement_evidence(m) for m in self.members]
        justified = [e for e in justified if e["justified"]]
        if not justified:
            return None
        def aggregate(e):
            return sum(v["own_median"] for v in e["contexts"].values())
        return max(justified, key=aggregate)

    def retire(self, member):
        self.members.remove(member)
        self.archived.append(member)

    def is_new(self, context):
        return context not in self.contexts

    def restore(self, member):
        """Regeneration: the caller has re-validated the member through the population."""
        self.archived.remove(member)
        self.members.append(member)


# --- controls (replayed over the same measured cost table) -----------------

def static_choice(calibration):
    """Best mean cost over a calibration set covering all contexts; then fixed."""
    members = calibration[0]["costs"].keys()
    return min(members, key=lambda m: sum(row["costs"][m] for row in calibration))


def offline_selection(calibration):
    """Conventional algorithm selection: per-context argmin on calibration, then fixed."""
    table = {}
    for row in calibration:
        table.setdefault(row["context"], []).append(row["costs"])
    return {c: min(rows[0], key=lambda m: median(r[m] for r in rows)) for c, rows in table.items()}


def aggregate_retirement(policy, keep):
    """Naive control: keep only the `keep` members with the best mean cost over observed contexts."""
    def mean_cost(member):
        values = [policy.estimate(c, member) for c in policy.contexts if policy.estimate(c, member) is not None]
        return sum(values) / len(values) if values else float("inf")
    ranked = sorted(policy.members, key=mean_cost)
    return ranked[:keep], ranked[keep:]
