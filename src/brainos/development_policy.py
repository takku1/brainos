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
see is labeled unknown, never guessed. An unconditional
within-bounds verdict requires every assessed variable to be known
and inside its band (B43): unknowns yield investigation or deferral,
and a `noop` always names the variables it does not cover.

State (B38): hysteresis bands, cooldowns, burn rates, churn windows
and assessment ages need memory across steps. The loop owns one
PolicyState, passes it to every observation and proposal, and persists
it through the restricted context so restarts resume conservatively.
Without state, history-dependent quantities report unknown and the
policy fails closed toward deferral.
"""
from .contracts import Refused

DECISIONS = ("continue", "recruit", "investigate", "construct",
             "evaluate-candidate", "reorganize", "assimilate",
             "suspend", "retire", "regenerate", "defer", "noop")

STATE_KEY = "policy-state-v1"


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
        retention=dict(floor=1.0, enter=1.0, exit=0.99, max_age_steps=50,
                       response="wake, re-assess, regenerate"),
        competence=dict(min_samples=3, floor=1.0, enter=1.0, exit=0.99,
                        cooldown_steps=25,
                        response="investigate unconfirmed or poorly serving members"),
        budget_runway=dict(floor_periods=5, enter=5, exit=8,
                           response="defer development; never mint"),
        maintenance_share=dict(ceiling=0.2, enter=0.2, exit=0.15,
                               response="retire or dormant per verified verdicts"),
        development_spend=dict(band=(0.0, 0.1), enter=0.1, exit=0.07,
                               cooldown_steps=50, est_cost_attempts=64,
                               response="cool down probing; never forced"),
        population=dict(soft_max=64, enter=64, exit=56,
                        response="tighten nomination"),
        churn=dict(ceiling_per_100_steps=10, enter=10, exit=6,
                   window_steps=100, cooldown_steps=25,
                   response="lengthen cooldowns; review nomination"),
        recovery=dict(evidence_max_age_steps=500,
                      response="probe recovery paths by assessment only"),
    )


class PolicyState:
    """Step-aware memory for hysteresis, cooldowns, burn and churn (B38).

    Owned by the coordination loop and passed to every observation and
    proposal. Persisted through the restricted context (`save`/`load`)
    so a restart resumes from recorded history instead of assuming it.
    A fresh state reports no history: history-dependent quantities are
    unknown until observed, and the policy fails closed toward
    deferral rather than assuming viability.
    """

    def __init__(self):
        self.step = None
        self.spend = {}
        self.members = {}
        self.member_step = None
        self.transitions = []
        self.seen_assessments = {}
        self.actions = []
        self.flags = {}
        self.cited = {}
        self.probe = {}
        self.snapshots = {}

    def note_step(self, step):
        self.step = step

    # -- resource burn (B39) -------------------------------------------
    def note_spend(self, budget, available, spent, step):
        self.spend.setdefault(budget, []).append((step, available, spent))
        self.step = step

    def burn_per_step(self, budget):
        """Measured expenditure per step over the last two distinct
        samples, or None when no rate has been observed yet."""
        samples = self.spend.get(budget, [])
        for i in range(len(samples) - 1, 0, -1):
            step1, _, spent1 = samples[i]
            step0, _, spent0 = samples[i - 1]
            if step1 != step0:
                return (spent1 - spent0) / (step1 - step0)
        return None

    # -- membership churn (B42) ----------------------------------------
    def note_members(self, snapshot, step):
        """Record {member_id: state}; returns transitions since the
        prior snapshot, each (kind, member_id, state)."""
        transitions = []
        if self.member_step is not None:
            for mid, state in snapshot.items():
                if mid not in self.members:
                    transitions.append(("added", mid, state))
                elif self.members[mid] != state:
                    transitions.append(("%s-to-%s" % (self.members[mid].lower(),
                                                      state.lower()), mid, state))
            for mid in self.members:
                if mid not in snapshot:
                    transitions.append(("removed", mid, None))
            for kind, mid, state in transitions:
                self.transitions.append((step, kind, mid))
        self.members = dict(snapshot)
        self.member_step = step
        self.step = step
        return transitions

    def transitions_in_window(self, step, window):
        return sum(1 for (s, _, _) in self.transitions if s > step - window)

    # -- assessment freshness (B41) ------------------------------------
    def note_assessments(self, ids, step):
        for aid in ids:
            self.seen_assessments.setdefault(aid, step)
        self.step = step

    def assessment_age(self, aid):
        if aid not in self.seen_assessments or self.step is None:
            return None
        return self.step - self.seen_assessments[aid]

    # -- action cooldowns and hysteresis flags (B38) -------------------
    def log_action(self, action, target, step):
        self.actions.append((step, action, target))
        self.step = step

    def recent_action(self, action, target, step, cooldown):
        return any(s > step - cooldown and a == action and t == target
                   for (s, a, t) in self.actions)

    def flag(self, key):
        return self.flags.get(key, False)

    def set_flag(self, key, violated):
        self.flags[key] = bool(violated)

    # -- persistence ----------------------------------------------------
    def save(self, ctx):
        # JSON-safe: tuple flags become "kind|budget" strings, tuples lists.
        value = dict(step=self.step, spend=self.spend, members=self.members,
                     member_step=self.member_step,
                     transitions=[list(t) for t in self.transitions[-200:]],
                     seen_assessments=self.seen_assessments,
                     actions=[list(a) for a in self.actions[-200:]],
                     cited={k: list(v) for k, v in self.cited.items()},
                     probe={k: [v[0], list(v[1])] for k, v in self.probe.items()},
                     snapshots={f"{a}|{t}": list(v)
                                for (a, t), v in self.snapshots.items()},
                     flags={"%s|%s" % key: value
                            for key, value in self.flags.items()})
        ctx.write("ecology", STATE_KEY, value, "policy-state-saved", step=self.step)
        return STATE_KEY

    @classmethod
    def load(cls, ctx):
        state = cls()
        try:
            saved = ctx.get("ecology", STATE_KEY)
        except Refused:
            return state
        if not isinstance(saved, dict):
            return state
        for key in ("spend", "members", "seen_assessments", "cited"):
            if isinstance(saved.get(key), dict):
                setattr(state, key, saved[key])
        for key in ("transitions", "actions"):
            if isinstance(saved.get(key), list):
                setattr(state, key, [tuple(item) for item in saved[key]])
        for key, value in (saved.get("flags") or {}).items():
            kind, _, budget = key.partition("|")
            state.flags[(kind, budget)] = bool(value)
        for key, value in (saved.get("snapshots") or {}).items():
            action, _, target = key.partition("|")
            if isinstance(value, list):
                state.snapshots[(action, target)] = list(value)
        if isinstance(saved.get("probe"), dict):
            state.probe = {k: [v[0], list(v[1])] for k, v in saved["probe"].items()
                           if isinstance(v, (list, tuple)) and len(v) == 2}
        state.step = saved.get("step")
        state.member_step = saved.get("member_step")
        return state


def _member_states(ctx, capability):
    """Membership picture distinguishing servable from blocked members.

    Blocked providers (kernel impact closure) are reported separately:
    a blocked ACTIVE row is not serving capacity, and mistaking it for
    competence is exactly the B40 failure. Returns
    (counts, {member_id: state}, [member_ids]) over servable members.
    """
    try:
        rows = [m for m in ctx.find("member") if m.get("capability") == capability]
    except Refused:
        rows = []
    try:
        servable = {m["id"] for m in ctx.members(
            capability, include_archived=True,
            states=("ACTIVE", "DORMANT", "ARCHIVED"))}
    except Refused:
        servable = {row.get("id") for row in rows}
    counts = {"ACTIVE": 0, "DORMANT": 0, "ARCHIVED": 0, "BLOCKED": 0}
    states, blocked = {}, []
    for row in rows:
        if row.get("id") not in servable:
            counts["BLOCKED"] += 1
            blocked.append(row.get("id"))
            continue
        if row.get("state") in counts:
            counts[row["state"]] += 1
            states[row.get("id")] = row.get("state")
    return counts, states, sorted(states), sorted(blocked)


def _competence(ctx, capability, recent_entries, min_samples):
    """Grounded serving competence from recent task outcomes (B40).

    recent_entries: [(task_id, correct_or_None, context), ...] supplied
    by the loop that observed the executions. Kernel task states are
    cross-checked (SUCCEEDED vs FAILED/CANCELLED is observed);
    correctness is loop-attested and labeled estimated. An active
    member with no, thin or unattested recent evidence is
    *unconfirmed*: membership alone never establishes competence.
    """
    checked = []
    for entry in recent_entries or []:
        tid, correct, context = entry[0], entry[1], entry[2] if len(entry) > 2 else None
        try:
            task = ctx.get("task", tid)
        except Refused:
            continue
        if task.get("state") not in ("SUCCEEDED", "FAILED", "CANCELLED"):
            continue
        if task.get("capability") not in (None, capability):
            continue
        checked.append((tid, task.get("state") == "SUCCEEDED",
                        bool(correct) if correct is not None else None, context))
    if not checked:
        return dict(status="unknown", reason="no recent task outcomes")
    n = len(checked)
    kernel_rate = sum(1 for (_, ok, _, _) in checked if ok) / n
    attested = [(ok, c) for (_, ok, c, _) in checked if c is not None]
    correct_rate = (sum(1 for (_, c) in attested if c) / len(attested)
                    if attested else None)
    per_context = {}
    for (_, ok, correct, context) in checked:
        slot = per_context.setdefault(context, {"n": 0, "ok": 0, "attested": 0,
                                                "correct": 0})
        slot["n"] += 1
        slot["ok"] += 1 if ok else 0
        if correct is not None:
            slot["attested"] += 1
            slot["correct"] += 1 if correct else 0
    for context, slot in per_context.items():
        slot["kernel_rate"] = slot["ok"] / slot["n"]
        slot["correct_rate"] = (slot["correct"] / slot["attested"]
                                if slot["attested"] else None)
        slot["thin"] = slot["n"] < min_samples
    return dict(status="observed", n=n, kernel_success_rate=kernel_rate,
                correct_rate=correct_rate,
                attested=sum(1 for (_, _, c, _) in checked if c is not None),
                per_context=per_context, thin=n < min_samples,
                evidence=[tid for (tid, _, _, _) in checked])


def _retention(ctx, capability, member_states, state, max_age_steps):
    """Retained competence from assessment outcomes and freshness (B41).

    Fresh means the assessment's period matches the capability period
    and its age (first-seen step) is within max_age_steps. Young
    members under min_age carry youth-implied retention (estimated).
    Counts alone establish nothing.
    """
    try:
        assessments = [a for a in ctx.find("retention-assessment")
                       if a.get("capability") == capability]
    except Refused:
        return dict(status="unknown", reason="retention-assessment rows unreadable")
    try:
        record = ctx.get("capability", capability)
        period, params = record.get("period", 0), record.get("retention", {})
    except Refused:
        return dict(status="unknown", reason="capability row unreadable")
    min_age = params.get("min_age", 0)
    by_provider = {}
    for aid, provider in ((a.get("id"), a.get("provider")) for a in assessments):
        by_provider.setdefault(provider, []).append(aid)
    member_ids = {a.get("id") for a in assessments}
    if state is not None and member_ids:
        state.note_assessments(sorted(member_ids),
                               state.step if state.step is not None else 0)
    providers = {}
    for mid, mstate in member_states.items():
        provider = mid.rsplit("|", 1)[-1]
        cands = [a for a in assessments if a.get("provider") == provider]
        verdict, freshness, age, aid = None, "unknown", None, None
        if cands:
            aid = max(cands, key=lambda a: (a.get("period", -1),
                                            state.seen_assessments.get(a.get("id"), -1)
                                            if state else -1)).get("id")
            best = next(a for a in cands if a.get("id") == aid)
            verdict = best.get("verdict")
            if best.get("period") != period:
                freshness = "stale"
            elif state is not None:
                age = state.assessment_age(aid)
                freshness = ("fresh" if age is not None and age <= max_age_steps
                             else "unknown")
            else:
                freshness = "unknown"
        try:
            member_age = period - next(
                m.get("admitted_period", 0) for m in ctx.find("member")
                if m.get("id") == mid)
        except (Refused, StopIteration):
            member_age = None
        if freshness == "unknown" and min_age > 0 and member_age is not None \
                and member_age < min_age:
            freshness, verdict = "implied-youth", None
        providers[provider] = dict(state=mstate, verdict=verdict,
                                   freshness=freshness, age_steps=age,
                                   assessment=aid)
    return dict(status="observed", count=len(assessments), providers=providers)


def full_snapshot(report):
    """Membership snapshot for cooldown comparison, including blocked
    members: a blocked provider is a changed world (B38)."""
    members = report.get("members", {})
    return sorted(members.get("snapshot", members.get("records", [])))


def build_observation(ctx, capabilities, budgets=(), demands=(), recent=None,
                      state=None, step=None, names=None):
    """Evidence-grounded observation of organizational state (ADR-2).

    capabilities: ids to report on. names: {id: display name} for
    readable decisions (targets stay ids). budgets: (budget, principal)
    pairs for runway. demands: capability ids (or {id: [contexts]})
    with unserved demand behind them. recent: {capability: [(task_id,
    correct_or_None, context)]} loop-observed outcomes for competence.
    With state and step, spend/member/assessment history is recorded
    (documented side effect) so burn rates, churn and ages are
    measured; without them those quantities report unknown.
    """
    recent = recent or {}
    names = names or {}
    demands_map = demands if isinstance(demands, dict) else {c: None for c in demands}
    if state is not None and step is not None:
        state.note_step(step)
    min_samples = default_bands()["competence"]["min_samples"]
    max_age = default_bands()["retention"]["max_age_steps"]
    window = default_bands()["churn"]["window_steps"]
    caps, snapshot = {}, {}
    for capability in capabilities:
        counts, states, ids, blocked = _member_states(ctx, capability)
        snapshot.update(states)
        comp = _competence(ctx, capability, recent.get(capability, []), min_samples)
        ret = _retention(ctx, capability, states, state, max_age)
        caps[capability] = dict(
            name=names.get(capability, capability),
            members=dict(counts, status="observed",
                         source="member rows", records=ids,
                         snapshot=sorted(ids + blocked)),
            competence=comp,
            retention=ret,
            demanded=dict(status="observed",
                          value=capability in demands_map,
                          contexts=demands_map.get(capability)))
    runway = {}
    for budget, principal in budgets:
        try:
            view = ctx.budget(budget, principal)
            available = view.get("available", {}).get("attempts", 0)
            spent = view.get("spent", {}).get("attempts", 0)
            if state is not None and step is not None:
                state.note_spend(budget, available, spent, step)
            burn = state.burn_per_step(budget) if state is not None else None
            if burn is None:
                runway[budget] = dict(status="unknown", available=available,
                                      spent=spent, source="budget view",
                                      reason="no measured burn rate yet")
            elif burn <= 0:
                runway[budget] = dict(status="observed", available=available,
                                      spent=spent, burn_per_step=0,
                                      periods=float("inf"), source="budget view")
            else:
                runway[budget] = dict(status="observed", available=available,
                                      spent=spent, burn_per_step=burn,
                                      periods=available / burn, source="budget view")
        except Refused as exc:
            runway[budget] = dict(status="unknown", reason=str(exc)[:120])
    if state is not None and step is not None:
        state.note_step(step)
        transitions = state.note_members(snapshot, step)
        churn = dict(status="estimated",
                     transitions_last_window=state.transitions_in_window(step, window),
                     window_steps=window,
                     recent=[(s, k, m) for (s, k, m) in state.transitions[-5:]],
                     source="member snapshot deltas")
    else:
        transitions, churn = [], dict(status="unknown",
                                      reason="no member history yet")
    return dict(capabilities=caps, runway=runway, churn=churn,
                transitions=transitions, step=step,
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


class ViabilityPolicy(DevelopmentalPolicy):
    """Evidence-driven developmental proposals from viability bands.

    Priority: investigate unserved or unconfirmed capabilities, recruit
    where dormant competence exists, construct where investigation
    found nothing and the budget allows, defer when the runway is
    short or variables are unassessed, noop only when every assessed
    variable is known and inside its band. Every proposal cites its
    records; nothing here executes. Hysteresis flags and cooldowns
    (B38) apply when a PolicyState is passed.
    """

    version = "viability/bands-v2"

    def __init__(self, bands=None):
        self.bands = bands if bands is not None else default_bands()

    def _competence_gate(self, comp, demanded_contexts):
        """(verdict, detail): ok, poor, or unconfirmed (B40)."""
        floor = self.bands["competence"]["floor"]
        if comp.get("status") != "observed":
            return "unconfirmed", "no recent task outcomes"
        if comp.get("thin"):
            return "unconfirmed", "fewer than %d recent outcomes" % self.bands[
                "competence"]["min_samples"]
        if comp.get("correct_rate") is None:
            return "unconfirmed", "correctness unattested"
        if comp["correct_rate"] < floor or comp["kernel_success_rate"] < floor:
            return "poor", "recent success below floor"
        if demanded_contexts:
            for context in demanded_contexts:
                slot = comp.get("per_context", {}).get(context)
                if slot is None or slot.get("thin"):
                    return "unconfirmed", "context %r unconfirmed" % (context,)
                if (slot.get("correct_rate") is None
                        or slot["correct_rate"] < floor):
                    return "poor", "context %r below floor" % (context,)
        return "ok", "recent outcomes within band"

    def propose(self, observation, ctx, state=None):
        caps = observation.get("capabilities", {})
        step = observation.get("step")
        for capability, report in caps.items():
            if not report.get("demanded", {}).get("value"):
                continue
            members = report.get("members", {})
            if members.get("ACTIVE", 0) <= 0:
                if members.get("DORMANT", 0) > 0:
                    if self._cool(state, step, "recruit", capability,
                                  full_snapshot(report)):
                        return self._defer_cool(capability, "recruit")
                    return decide("recruit", target=capability,
                                  reason="demanded capability has dormant members",
                                  evidence={"member_rows": members.get("records", [])})
                if state is not None and step is not None and self._settled(
                        state, step, "investigate", capability, members):
                    return self._construct(report, capability, observation, state,
                                           step)
                return decide("investigate", target=capability,
                              reason="demanded capability has no serving member",
                              evidence={"member_rows": members.get("records", [])})
            comp = report.get("competence", {})
            verdict, detail = self._competence_gate(
                comp, report.get("demanded", {}).get("contexts"))
            if verdict != "ok":
                sig = [verdict, sorted(
                    report.get("members", {}).get("records", []))]
                cooled = self._probe_cooled(state, step, capability, sig)
                if cooled is not None:
                    return cooled
                return decide("investigate", target=capability,
                              reason="active members %s: %s" % (
                                  "serve poorly" if verdict == "poor"
                                  else "unconfirmed", detail),
                              evidence={"competence": comp, "probe_sig": sig})
            adverse = {p: r for p, r in report.get("retention", {}).get(
                "providers", {}).items()
                if r.get("state") == "ACTIVE"
                and r.get("freshness") == "fresh"
                and r.get("verdict") in ("redundant", "not-best")}
            if adverse:
                serving = [p for p, r in report.get("retention", {}).get(
                    "providers", {}).items()
                    if r.get("state") == "ACTIVE"]
                others = [p for p in serving if p not in adverse]
                if others:
                    provider = sorted(adverse)[0]
                    return decide("suspend", target=capability,
                                  reason="verified %s with %s serving: suspend %s" % (
                                      adverse[provider]["verdict"],
                                      ", ".join(sorted(others)),
                                      provider),
                                  evidence={"providers": sorted(adverse),
                                            "assessment": adverse[provider][
                                                "assessment"],
                                            "suspended": provider})
                return decide("investigate", target=capability,
                              reason="adverse retention evidence with no "
                                     "alternative serving member",
                              evidence={"providers": sorted(adverse)})
        runway = observation.get("runway", {})
        floor = self.bands["budget_runway"]["enter"]
        for budget, entry in runway.items():
            if entry.get("status") != "observed":
                if (entry.get("spent", 0) or 0) > 0 or not state:
                    return decide("defer", reason="budget runway unassessed",
                                  evidence={"budget": budget,
                                            "detail": entry.get("reason")})
                continue
            key = ("runway", budget)
            periods = entry.get("periods", float("inf"))
            if state is not None:
                if periods < self.bands["budget_runway"]["enter"]:
                    state.set_flag(key, True)
                elif periods > self.bands["budget_runway"]["exit"]:
                    state.set_flag(key, False)
                if state.flag(key):
                    return decide("defer", reason="budget runway below floor",
                                  evidence={"budget": budget, "periods": periods})
            elif periods < floor:
                return decide("defer", reason="budget runway below floor",
                              evidence={"budget": budget, "periods": periods})
        return decide("noop", reason="organization within bounds on assessed "
                                     "variables; uncovered: %s" % ", ".join(
                                         self._advisory(observation)),
                      evidence={"policy": self.version})

    def _cool(self, state, step, action, target, records):
        """Cooldown applies only while the membership snapshot is
        unchanged since the last such proposal: a changed world
        re-triggers immediately (B38)."""
        if state is None or step is None:
            return False
        if not state.recent_action(
                action, target, step,
                self.bands["development_spend"]["cooldown_steps"]):
            return False
        return state.snapshots.get((action, target)) == sorted(records)

    def _probe_cooled(self, state, step, capability, sig):
        """Defer when an investigation with the same verdict and member
        set ran within the competence cooldown: re-probing identical
        evidence is spam, while any change re-triggers immediately."""
        if state is None or step is None:
            return None
        if not state.recent_action("investigate", capability, step,
                                   self.bands["competence"]["cooldown_steps"]):
            return None
        last = state.probe.get(capability)
        if last is not None and list(last[1]) == list(sig[1]) and last[0] == sig[0]:
            return decide("defer", target=capability,
                          reason="investigation cooling down; no change "
                                 "since last probe",
                          evidence={"policy": self.version})
        return None

    def _defer_cool(self, target, action):
        return decide("defer", target=target,
                      reason="%s cooling down after recent proposal" % action,
                      evidence={"policy": self.version})

    def _settled(self, state, step, action, target, members):
        """A prior investigation with no membership change since: the
        deficiency is confirmed, so propose construction, not another
        investigation."""
        prior = [s for (s, a, t) in state.actions
                 if a == action and t == target and s < step]
        return bool(prior)

    def _construct(self, report, capability, observation, state, step):
        band = self.bands["development_spend"]
        if self._cool(state, step, "construct", capability,
                      full_snapshot(report)):
            return self._defer_cool(capability, "construct")
        funded = [b for b, e in observation.get("runway", {}).items()
                  if e.get("status") == "observed"
                  and e.get("periods", 0) > self.bands["budget_runway"]["enter"]]
        if not funded:
            return decide("defer", target=capability,
                          reason="construction unjustified without a funded budget",
                          evidence={"policy": self.version})
        return decide("construct", target=capability,
                      reason="investigation confirmed no serving member",
                      evidence={"member_rows": report.get("members", {}).get(
                          "records", [])},
                      est_cost=band["est_cost_attempts"],
                      budget=funded[0], principal="dev")

    def _advisory(self, observation):
        uncovered = []
        if observation.get("recovery", {}).get("status") == "unknown":
            uncovered.append("recovery readiness")
        if observation.get("churn", {}).get("status") == "unknown":
            uncovered.append("churn history")
        for cap, report in observation.get("capabilities", {}).items():
            for provider, entry in report.get("retention", {}).get(
                    "providers", {}).items():
                if entry.get("freshness") in ("unknown", "stale",
                                              "implied-youth"):
                    uncovered.append("retention %s/%s" % (cap, provider))
        return uncovered or ["none"]


def classify_quiescence(observation, state, bands, recovering=False):
    """Distinguish healthy quiescence from look-alikes (B43, F).

    Labels: healthy-quiescence, unresolved-pressure, blocked-adaptation,
    exhausted-search, resource-deferral, recovery, unknown. A high noop
    rate alone never establishes health: every unknown or adverse
    variable is named in the reasons.
    """
    caps = observation.get("capabilities", {})
    demanded = [c for c, r in caps.items() if r.get("demanded", {}).get("value")]
    step = observation.get("step")
    cooldown = bands["competence"]["cooldown_steps"]
    if recovering:
        return ("recovery", ["explicit recovery flag set"])
    blocked = [c for c in demanded
               if observation["capabilities"][c]["members"].get("BLOCKED", 0) > 0]
    if blocked:
        return ("blocked-adaptation",
                ["blocked members on %s" % caps[c].get("name", c) for c in blocked])
    for cap in demanded:
        members = caps[cap]["members"]
        if members.get("ACTIVE", 0) <= 0 and members.get("DORMANT", 0) <= 0:
            if (state is not None and step is not None
                    and state.recent_action("construct", cap, step, cooldown)):
                return ("exhausted-search",
                        ["construction attempted for %s without result"
                         % caps[cap].get("name", cap)])
            return ("unresolved-pressure",
                    ["no serving member for %s" % caps[cap].get("name", cap)])
    for cap in demanded:
        comp = caps[cap].get("competence", {})
        if comp.get("status") != "observed" or comp.get("thin") \
                or comp.get("correct_rate") is None:
            return ("unresolved-pressure",
                    ["competence unconfirmed for %s" % caps[cap].get("name", cap)])
        if comp["correct_rate"] < bands["competence"]["floor"] \
                or comp["kernel_success_rate"] < bands["competence"]["floor"]:
            return ("unresolved-pressure",
                    ["poor serving competence on %s" % caps[cap].get("name", cap)])
    for budget, entry in observation.get("runway", {}).items():
        if entry.get("status") == "observed" \
                and entry.get("periods", float("inf")) < bands["budget_runway"]["enter"]:
            return ("resource-deferral", ["runway below floor"])
    unknowns = []
    for cap in demanded:
        ret = caps[cap].get("retention", {})
        if ret.get("status") != "observed":
            unknowns.append("retention unreadable on %s" % caps[cap].get("name", cap))
            continue
        for provider, entry in ret.get("providers", {}).items():
            if entry.get("freshness") in ("unknown", "stale", "implied-youth"):
                unknowns.append("retention %s on %s" % (
                    entry.get("freshness"), caps[cap].get("name", cap)))
                break
    for budget, entry in observation.get("runway", {}).items():
        if entry.get("status") != "observed":
            unknowns.append("runway unassessed")
            break
    if unknowns:
        return ("unknown", unknowns)
    return ("healthy-quiescence", ["all assessed variables within bounds"])


def construction_lineage(ctx, provider, _seen=None):
    """Lineage of a constructed provider from kernel records: a chain of
    (provider_id, depth) from the provider down through constructed
    ancestors. Primitives terminate the chain. Cycles are cut, never
    followed twice."""
    _seen = _seen if _seen is not None else set()
    if provider in _seen:
        return []
    _seen.add(provider)
    try:
        spec = ctx.resolve(provider)
    except Refused:
        return [(provider, 0)]
    chain = [(provider, 0)]
    deps = [d for d in spec.get("transitive_dependencies", []) if d != provider]
    best = 0
    for dep in deps:
        try:
            kind = ctx.resolve(dep).get("kind")
        except Refused:
            continue
        if kind != "graph":
            continue
        sub = construction_lineage(ctx, dep, _seen)
        if sub:
            best = max(best, sub[0][1] + 1)
            chain.extend(sub)
    chain[0] = (provider, best)
    return chain


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
