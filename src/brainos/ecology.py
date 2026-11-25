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
import math
import random
from statistics import median

from .contracts import digest, uid


from .population import featurize  # noqa: E402  (one trusted featurizer)


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
    mode: str = "median"                            # "lcb": uncertainty-aware selection/pruning (B19)
    draws: str = "random"                           # "digest": per-decision draws, restart-reproducible (B16)
    prior_sd: float = 1.0                           # log-cost spread assumed before data (lcb)
    prior_weight: float = 2.0
    z: float = 1.96

    def __post_init__(self):
        self.rng = random.Random(self.seed)
        self.members = list(self.members)
        self.decisions = 0

    def _uniform(self):
        if self.draws == "digest":
            return int(digest([self.seed, self.decisions, "u"])[:13], 16) / 16 ** 13
        return self.rng.random()

    def _pick(self, options):
        if self.draws == "digest":
            return options[int(digest([self.seed, self.decisions, "pick"])[:13], 16) % len(options)]
        return self.rng.choice(options)

    def bounds(self, context, member):
        """(lower, upper) confidence bounds on cost from log-cost samples with a prior spread."""
        values = [math.log(max(v, 1)) for v in self.samples(context, member)]
        if not values:
            return 0.0, math.inf
        n, mean = len(values), sum(values) / len(values)
        ss = sum((v - mean) ** 2 for v in values)
        sd = math.sqrt((self.prior_sd ** 2 * self.prior_weight + ss) / (self.prior_weight + n - 1))
        half = self.z * sd / math.sqrt(n)
        return math.exp(mean - half), math.exp(mean + half)

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
        try:
            return self._select(context, can_explore)
        finally:
            self.decisions += 1

    def _select_lcb(self, context, can_explore):
        known = [(self.estimate(context, m), m) for m in self.members if self.samples(context, m)]
        greedy = min(known)[1] if known else self.members[0]
        if not can_explore:
            return greedy, False
        best_upper = min((self.bounds(context, m)[1] for m in self.members), default=math.inf)
        # Optimism under uncertainty, excluding members whose lower bound exceeds the best upper bound.
        plausible = [m for m in self.members if self.bounds(context, m)[0] <= best_upper]
        unsampled = [m for m in plausible if not self.samples(context, m)]
        if unsampled:
            return unsampled[0], True
        thin = [m for m in plausible if len(self.samples(context, m)) < self.min_samples]
        if thin:
            choice = min(thin, key=lambda m: self.bounds(context, m)[0])
            return choice, choice != greedy
        choice = min(plausible, key=lambda m: self.bounds(context, m)[0])
        return choice, choice != greedy

    def _select(self, context, can_explore):
        if context not in self.contexts:
            self.contexts.append(context)
        if self.mode == "lcb":
            return self._select_lcb(context, can_explore)
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
        if can_explore and len(self.members) > 1 and self._uniform() < self.epsilon:
            return self._pick([m for m in self.members if m != best]), True
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


class EcologyService:
    """Durable ecology over one capability population (B16).

    The configuration and every decision (selection or lifecycle operation) are
    records written through the development context. Observed costs are read
    from the kernel's invocation records, never supplied by the caller.
    Restarting replays the records in sequence and reproduces the policy state;
    with digest draws, later decisions are identical to an uninterrupted run.
    Lifecycle requests go to the population, which verifies them independently.
    """

    def __init__(self, ctx, ecology_id):
        self.ctx = ctx
        self.config = ctx.get("ecology", ecology_id)
        self.id = ecology_id
        self.capability = self.config["capability"]
        self.providers = dict(self.config["providers"])          # name -> provider id
        self.policy = EcologyPolicy(list(self.providers), current=self._current, draws="digest",
                                    **self.config["policy"])
        self.policy.dormant = []
        self.seq = 0
        self.cited = []
        for row in sorted((r for r in ctx.find("ecology-decision") if r["ecology"] == ecology_id),
                          key=lambda r: r["seq"]):
            self._apply(row)

    @classmethod
    def create(cls, ctx, capability, providers, **policy):
        key = uid()
        ctx.write("ecology", key, dict(id=key, capability=capability, providers=dict(providers), policy=policy),
                  "ecology-created", ecology=key, capability=capability)
        return cls(ctx, key)

    def _current(self, member, revision):
        return self.ctx.evidence_current(self.providers[member], revision)

    def _apply(self, row):
        self.seq = row["seq"] + 1
        policy = self.policy
        if row["type"] == "select":
            if row["context"] not in policy.contexts:
                policy.contexts.append(row["context"])
            policy.decisions += 1
            invocation = self.ctx.get("invocation", row["invocation"])
            policy.observe(row["context"], row["member"], invocation["compute_ns"], invocation["evidence_revision"])
            self.cited.append(row["invocation"])
        elif row["op"] in ("retire", "dormant"):
            # A member may be retired from ACTIVE or (dormancy-first) from DORMANT.
            holder = policy.members if row["member"] in policy.members else policy.dormant
            holder.remove(row["member"])
            (policy.archived if row["op"] == "retire" else policy.dormant).append(row["member"])
        elif row["op"] == "wake":
            policy.dormant.remove(row["member"])
            policy.members.append(row["member"])
        elif row["op"] == "regenerate":
            policy.archived.remove(row["member"])
            policy.members.append(row["member"])

    def _write(self, row):
        row = dict(row, id=f"{self.id}:{self.seq}", ecology=self.id, seq=self.seq)
        self.ctx.write("ecology-decision", row["id"], row, "ecology-decision", ecology=self.id, seq=self.seq)
        self._apply(row)

    # --- selection ------------------------------------------------------------
    def choose(self, context, can_explore):
        """Pure choice; nothing is recorded until `observe` cites the resulting invocation."""
        snapshot = self.policy.decisions
        known = list(self.policy.contexts)
        member, exploring = self.policy.select(context, can_explore)
        self.policy.decisions = snapshot              # the durable record advances the counter
        self.policy.contexts[:] = known               # ... and records the context
        return member, exploring

    def observe(self, context, member, exploring, invocation):
        invocation_record = self.ctx.get("invocation", invocation)
        task = self.ctx.get("task", invocation_record["task"])
        if task["provider"] != self.providers[member] or task.get("capability") != self.capability:
            raise ValueError("observation must cite an invocation of that member under this capability")
        self._write(dict(type="select", context=context, member=member, exploring=bool(exploring),
                         invocation=invocation))

    # --- lifecycle (population verifies every request) ------------------------
    def assess(self, member):
        return self.ctx.assess(self.capability, self.providers[member], self.cited)

    def make_dormant(self, member):
        assessment = self.assess(member)
        self.ctx.make_dormant(self.capability, self.providers[member], assessment=assessment["id"])
        self._write(dict(type="lifecycle", op="dormant", member=member, assessment=assessment["id"]))
        return assessment

    def retire(self, member, reason):
        assessment = self.assess(member)
        self.ctx.retire(self.capability, self.providers[member], assessment=assessment["id"], reason=reason)
        self._write(dict(type="lifecycle", op="retire", member=member, assessment=assessment["id"]))
        return assessment

    def wake(self, member, *, budget, principal):
        outcome = self.ctx.wake(self.capability, self.providers[member], budget=budget, principal=principal)
        self._write(dict(type="lifecycle", op="wake", member=member, **outcome))
        return outcome

    def regenerate(self, member, *, budget, principal):
        self.ctx.regenerate(self.capability, self.providers[member], budget=budget, principal=principal)
        self._write(dict(type="lifecycle", op="regenerate", member=member))
