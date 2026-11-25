"""Replaceable developmental coordination policy (ADR-3) over an
evidence-grounded organizational observation (ADR-2) with declared
viability bands (ADR-5).

This module coordinates mechanisms; it invents none. A policy observes
organizational state through the restricted development context and
returns one decision per step. The policy proposes; it never executes:
every mutating action runs through its existing kernel gate, which
re-verifies everything at execution time. `defer` and `noop` are
first-class outcomes with recorded reasons, never failures.

Epistemic discipline (Doc 33 section 33.6): every observed quantity
cites the kernel records it derives from; aggregates computed from
records are labeled estimated; anything the restricted context cannot
see is labeled unknown, never guessed.
"""
from .contracts import Refused

DECISIONS = ("continue", "recruit", "investigate", "construct",
             "evaluate-candidate", "reorganize", "assimilate",
             "suspend", "retire", "regenerate", "defer", "noop")


def default_bands():
    """Declared viability bands (Doc 33 section 33.4, R-25-08).

    Data, not code paths: thresholds are reviewable per deployment and
    re-estimated from meter history, never tuned against confirmatory
    results. Entering and leaving a band use different thresholds
    (hysteresis); transitions start cooldowns measured in coordination
    steps.
    """
    return dict(
        coverage=dict(floor=1.0, enter=1.0, exit=0.99,
                      response="investigate, then construct or recruit"),
        retention=dict(floor=1.0, enter=1.0, exit=0.99,
                       response="wake, re-assess, regenerate"),
        budget_runway=dict(floor_periods=5, enter=5, exit=8,
                           response="defer development; never mint"),
        maintenance_share=dict(ceiling=0.2, enter=0.2, exit=0.15,
                               response="retire or dormant per verified verdicts"),
        development_spend=dict(band=(0.0, 0.1), enter=0.1, exit=0.07,
                               cooldown_steps=50,
                               response="cool down probing; never forced"),
        population=dict(soft_max=64, enter=64, exit=56,
                        response="tighten nomination"),
        churn=dict(ceiling_per_100_steps=10, enter=10, exit=6,
                   cooldown_steps=25,
                   response="lengthen cooldowns; review nomination"),
        recovery=dict(evidence_max_age_steps=500,
                      response="probe recovery paths by assessment only"),
    )


def _member_states(ctx, capability):
    try:
        rows = [m for m in ctx.find("member") if m.get("capability") == capability]
    except Refused:
        rows = []
    counts = {"ACTIVE": 0, "DORMANT": 0, "ARCHIVED": 0}
    for row in rows:
        if row.get("state") in counts:
            counts[row["state"]] += 1
    return counts, [row.get("id") for row in rows]


def build_observation(ctx, capabilities, budgets=(), demands=()):
    """Evidence-grounded observation of organizational state (ADR-2).

    capabilities: ids to report on. budgets: (budget, principal) pairs
    for runway. demands: capability ids with unserved demand behind them.
    Only restricted-context reads are used; anything unreachable is
    reported unknown with its reason, never synthesized.
    """
    caps = {}
    for capability in capabilities:
        counts, ids = _member_states(ctx, capability)
        try:
            assessments = [a for a in ctx.find("retention-assessment")
                           if a.get("capability") == capability]
        except Refused:
            assessments = None
        caps[capability] = dict(
            members=dict(counts, status="observed",
                         source="member rows", records=ids),
            retention=dict(status="observed" if assessments is not None else "unknown",
                           source="retention-assessment rows",
                           count=None if assessments is None else len(assessments)),
            demanded=dict(status="observed", value=capability in set(demands)),
        )
    runway = {}
    for budget, principal in budgets:
        try:
            view = ctx.budget(budget, principal)
            available = view.get("available", {}).get("attempts", 0)
            spent = view.get("spent", {}).get("attempts", 0)
            runway[budget] = dict(status="observed", available=available,
                                  spent=spent, source="budget view")
        except Refused as exc:
            runway[budget] = dict(status="unknown", reason=str(exc)[:120])
    try:
        trials = ctx.find("construction-run")
        decisions = ctx.find("ecology-decision")
        churn = dict(status="estimated", construction_runs=len(trials),
                     recorded_decisions=len(decisions),
                     source="construction-run and ecology-decision rows")
    except Refused as exc:
        churn = dict(status="unknown", reason=str(exc)[:120])
    return dict(capabilities=caps, runway=runway, churn=churn,
                recovery=dict(status="unknown",
                              reason="member history is not visible to the "
                                     "restricted context"))


def decide(action, target=None, reason="", evidence=None, est_cost=0,
           budget=None, principal=None):
    """Build one decision record. Unknown actions are refused, not guessed."""
    if action not in DECISIONS:
        raise Refused(f"unknown developmental action {action!r}")
    return dict(action=action, target=target, reason=reason,
                evidence=dict(evidence or {}), est_cost=est_cost,
                budget=budget, principal=principal)


class DevelopmentalPolicy:
    """Replaceable policy interface (ADR-3, R-07-13).

    Subclasses implement propose(); the base implementation always
    abstains. Policies run inside the restricted development context:
    they may read whitelisted records and cite them as evidence, spend
    nothing themselves, and mutate nothing. Version identity is carried
    so replacement is an explicit, recorded operator act.
    """
    version = "base/noop-v1"

    def propose(self, observation, ctx):
        return decide("noop", reason="base policy abstains",
                      evidence={"policy": self.version})


class NoopPolicy(DevelopmentalPolicy):
    """Legitimate inactivity: always suspend with a recorded reason."""

    version = "noop/suspend-v1"

    def propose(self, observation, ctx):
        return decide("defer", reason="no developmental proposal; stable conditions",
                      evidence={"policy": self.version})


def _runway_periods(runway):
    periods = []
    for entry in runway.values():
        if entry.get("status") != "observed":
            continue
        burn = entry.get("spent", 0)
        periods.append(float("inf") if burn <= 0 else
                       entry.get("available", 0) / burn)
    return min(periods) if periods else None


class ViabilityPolicy(DevelopmentalPolicy):
    """Evidence-driven developmental proposals from viability bands.

    Priority: investigate unserved demanded capabilities, recruit where
    dormant competence exists and its evidence is fresh, construct where
    investigation found no existing member and the budget allows, defer
    when the runway is short, noop when the organization is within
    bounds. Every proposal cites its records; nothing here executes.
    """

    version = "viability/bands-v1"

    def __init__(self, bands=None):
        self.bands = bands if bands is not None else default_bands()

    def propose(self, observation, ctx):
        caps = observation.get("capabilities", {})
        for capability, report in caps.items():
            members = report.get("members", {})
            if not report.get("demanded", {}).get("value"):
                continue
            if members.get("ACTIVE", 0) > 0:
                continue
            if members.get("DORMANT", 0) > 0:
                return decide("recruit", target=capability,
                              reason="demanded capability has dormant members",
                              evidence={"member_rows": members.get("records", [])})
            return decide("investigate", target=capability,
                          reason="demanded capability has no serving member",
                          evidence={"member_rows": members.get("records", [])})
        runway = observation.get("runway", {})
        floor = self.bands["budget_runway"]["floor_periods"]
        periods = _runway_periods(runway)
        if periods is not None and periods < floor:
            return decide("defer", reason="budget runway below floor; never mint",
                          evidence={"runway_periods": periods, "floor": floor})
        return decide("noop", reason="organization within viability bounds",
                      evidence={"policy": self.version})


def record_decision(ctx, decision, key):
    """Journal one policy decision through the restricted context.

    The decision record carries the action, its cited evidence, the
    estimated cost and the applicable budget constraint. Recording is
    the only write a policy performs; execution stays with the kernel.
    """
    if decision.get("action") not in DECISIONS:
        raise Refused(f"cannot record unknown action {decision.get('action')!r}")
    value = dict(decision, policy=decision.get("evidence", {}).get("policy"))
    ctx.write("ecology-decision", key, value, "eco-decision",
              action=decision["action"], target=str(decision.get("target")),
              reason=str(decision.get("reason"))[:200])
    return key
