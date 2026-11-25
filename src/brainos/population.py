"""Capability contracts, provider populations and the provider lifecycle.

Capability: what can be accomplished (contract: name, schemas, units and its
independent admission cases). Provider: one implementation artifact.
Membership: a validated assertion that a provider implements a contract.
Role: a manifest binding (owned by the transactor), separate from all three.

Lifecycle (Doc 21 section 21.12): ACTIVE -> DORMANT -> ARCHIVED, with wake and
regeneration back to ACTIVE. Every transition that removes execution or
maintenance is justified by a retention *assessment* that this service
computes itself. It uses kernel records only: real invocations of that exact
provider (cost read from the invocation, context recomputed from the task
input). Caller-supplied verdicts are never trusted.
"""
import json
import time
from statistics import median

from .contracts import Refused, digest, encode, uid
from . import graphs

DEFAULT_RETENTION = dict(min_samples=3, margin=0.10, min_age=0, min_coverage=1, min_dormant_age=0,
                         dormancy_first=False)


def featurize(workload):
    """Trusted context assignment for range-batch workloads (declared features only)."""
    queries = workload["queries"]
    widths = sorted(hi - lo for lo, hi in queries) or [0]
    q = len(queries)
    qband = "single" if q <= 2 else "few" if q <= 32 else "many"
    wband = "narrow" if widths[len(widths) // 2] <= 16 else "wide"
    return f"{qband}-{wband}"


FEATURIZERS = {"range-batch": featurize}


def verdict(samples, member, active, params, contexts):
    """Pure retention rule over {(context, member): [costs]} (shared by assess and tests).

    redundant: in every observed context the member has >= min_samples and some
               other ACTIVE member with >= min_samples is within `margin`.
    not-best:  the member is the best median in no observed context.
    retain:    otherwise (including insufficient evidence anywhere).
    """
    per, redundant, best_somewhere = {}, bool(contexts), False
    for c in contexts:
        mine = samples.get((c, member), [])
        rivals = {m: median(samples[(c, m)]) for m in active
                  if m != member and len(samples.get((c, m), [])) >= params["min_samples"]}
        own = median(mine) if mine else None
        if own is not None and all(own < v for v in rivals.values()):
            best_somewhere = True
        if len(mine) < params["min_samples"]:
            per[c] = dict(verdict="insufficient-evidence", samples=len(mine))
            redundant = False
            continue
        covering = sorted(m for m, v in rivals.items() if v <= own * (1 + params["margin"]))
        per[c] = dict(own_median=own, covered_by=covering, rivals=rivals,
                      verdict="redundant" if covering else "specialist")
        redundant &= bool(covering)
    if len(contexts) < params["min_coverage"]:
        return "retain", per, "insufficient context coverage"
    if redundant:
        return "redundant", per, "covered within margin in every observed context"
    if not best_somewhere and all(v["verdict"] != "specialist" for v in per.values()):
        return "not-best", per, "best in no observed context"
    return "retain", per, "specialist or insufficient evidence somewhere"


class CapabilityPopulation:
    def __init__(self, store, registry, transactor, control):
        self.store = store
        self.registry = registry
        self.transactor = transactor
        self.control = control

    # --- contracts and operator configuration ---------------------------------
    def define(self, name, input, output, admission_cases, *, input_unit=None, output_unit=None):
        if not name or not admission_cases or len(admission_cases) > 64:
            raise Refused("a capability needs a name and 1..64 admission cases")
        contract = dict(name=name, input=input, output=output,
                        input_unit=input_unit or graphs.unit(input), output_unit=output_unit or graphs.unit(output))
        key = f"capability:{name}@{digest(contract)[:16]}"
        cases = json.loads(encode(admission_cases))
        with self.store.transaction():
            existing = next((c for c in self.store.find("capability") if c["id"] == key), None)
            if existing is not None:
                if existing["cases_digest"] != digest(cases):
                    raise Refused("capability contract already defined with other admission cases")
                return key
            self.store.put("capability", key, dict(contract, id=key, admission_cases=cases,
                cases_digest=digest(cases), retention=dict(DEFAULT_RETENTION), period=0, maintenance={}))
            self.store.event("capability-defined", capability=key)
        return key

    def contract(self, capability):
        with self.store.mutex:
            return self.store.get("capability", capability)

    def set_retention_policy(self, capability, **params):
        """Operator API: retention rule parameters for this capability."""
        unknown = set(params) - set(DEFAULT_RETENTION)
        if unknown:
            raise Refused(f"unknown retention parameters: {sorted(unknown)}")
        with self.store.transaction():
            record = self.store.get("capability", capability)
            record["retention"] = dict(record["retention"], **params)
            self.store.put("capability", capability, record)
            self.store.event("retention-policy", capability=capability, params=record["retention"])

    def set_maintenance(self, capability, provider, *, active, dormant):
        """Operator API: declared maintenance units per period for one member."""
        if type(active) is not int or type(dormant) is not int or not 0 <= dormant <= active:
            raise Refused("maintenance must be integers with 0 <= dormant <= active")
        with self.store.transaction():
            record = self.store.get("capability", capability)
            record["maintenance"][provider] = dict(active=active, dormant=dormant)
            self.store.put("capability", capability, record)

    # --- membership -----------------------------------------------------------
    def _row(self, capability, provider):
        return next((m for m in self.store.find("member") if m["id"] == f"{capability}|{provider}"), None)

    def state(self, capability, provider):
        with self.store.mutex:
            row = self._row(capability, provider)
            return row["state"] if row else None

    def admit(self, capability, provider, *, budget, principal):
        """Validate the provider on the contract's own admission cases, then admit (ACTIVE)."""
        cases = self.contract(capability)["admission_cases"]
        candidate = self.transactor.stage_membership(capability, provider)
        self.transactor.validate(candidate, {capability: cases}, budget=budget, principal=principal)
        return self.transactor.commit_membership(candidate)

    def members(self, capability, *, include_archived=False, states=("ACTIVE",)):
        with self.store.mutex:
            rows = [m for m in self.store.find("member") if m["capability"] == capability
                    and (include_archived or m["state"] in states)]
        return [row for row in rows if self.registry.blocking_impact(row["provider"]) is None]

    def member(self, capability, provider):
        """An ACTIVE, unblocked member's provider spec, or Refused. Only ACTIVE members execute."""
        with self.store.mutex:
            row = self._row(capability, provider)
        if row is None or row["state"] != "ACTIVE":
            raise Refused("provider is not an active member of this capability")
        return self.registry.resolve(provider)

    # --- grounded retention assessment ---------------------------------------
    def _observations(self, capability, invocations):
        """Verify cited invocations; return {(context, provider): [compute_ns]} and a digest."""
        contract = self.store.get("capability", capability)
        featurizer = FEATURIZERS.get(contract["input"])
        if featurizer is None:
            raise Refused("no trusted featurizer for this capability's input schema")
        samples, cited = {}, []
        for key in sorted(set(invocations)):
            invocation = self.store.get("invocation", key)
            task = self.store.get("task", invocation["task"])
            if invocation["state"] != "COMPLETED" or task.get("capability") is None:
                raise Refused("cited invocation is not a completed capability-routed task")
            other = self.store.get("capability", task["capability"])
            if any(other[k] != contract[k] for k in ("input", "output", "input_unit", "output_unit")):
                raise Refused("cited invocation served a different contract")
            context = featurizer(task["value"])
            samples.setdefault((context, task["provider"]), []).append(invocation["compute_ns"])
            cited.append([key, task["provider"], context, invocation["compute_ns"]])
        return samples, digest(cited)

    def assess(self, capability, provider, invocations):
        """Compute and record a retention assessment from cited real invocations."""
        started = time.perf_counter_ns()
        with self.store.transaction():
            record = self.store.get("capability", capability)
            row = self._row(capability, provider)
            if row is None or row["state"] == "ARCHIVED":
                raise Refused("assessment requires a current member")
            samples, observed = self._observations(capability, invocations)
            contexts = sorted({c for c, _ in samples})
            active = [m["provider"] for m in self.store.find("member")
                      if m["capability"] == capability and m["state"] == "ACTIVE"]
            params = record["retention"]
            result, per, why = verdict(samples, provider, active, params, contexts)
            age = record["period"] - row.get("admitted_period", 0)
            if result != "retain" and age < params["min_age"]:
                result, why = "retain", f"admission age {age} < {params['min_age']}"
            key = uid()
            assessment = dict(id=key, capability=capability, provider=provider, verdict=result, reason=why,
                contexts=per, coverage=contexts, params=params, observations=observed,
                invocations=sorted(set(invocations)), member_state=row["state"], age=age,
                period=record["period"], evidence_revision=self.control.read()["evidence_revision"],
                active=sorted(active), wall_ns=time.perf_counter_ns() - started)
            self.store.put("retention-assessment", key, assessment)
            self.store.event("retention-assessed", assessment=key, provider=provider, verdict=result)
        return assessment

    def _verified(self, capability, provider, assessment, allowed):
        record = self.store.get("retention-assessment", assessment)
        if record["capability"] != capability or record["provider"] != provider:
            raise Refused("assessment is bound to a different capability or provider")
        if record["evidence_revision"] != self.control.read()["evidence_revision"]:
            raise Refused("assessment is stale: evidence changed since it was computed")
        if record["period"] != self.store.get("capability", capability)["period"]:
            raise Refused("assessment is stale: a maintenance period has passed")
        row = self._row(capability, provider)
        if row is None or row["state"] != record["member_state"]:
            raise Refused("assessment is stale: member state changed")
        # Re-derive from the same cited invocations and the current population.
        samples, observed = self._observations(capability, record["invocations"])
        if observed != record["observations"]:
            raise Refused("cited observations changed")
        active = sorted(m["provider"] for m in self.store.find("member")
                        if m["capability"] == capability and m["state"] == "ACTIVE")
        if active != record["active"]:
            raise Refused("assessment is stale: the active population changed")
        if record["verdict"] not in allowed:
            raise Refused(f"assessment verdict {record['verdict']!r} does not justify this transition")
        return record, row

    # --- lifecycle transitions ------------------------------------------------
    def make_dormant(self, capability, provider, *, assessment):
        with self.store.transaction():
            record, row = self._verified(capability, provider, assessment, ("not-best", "redundant"))
            if row["state"] != "ACTIVE":
                raise Refused("only an active member can become dormant")
            if sum(1 for m in self.store.find("member") if m["capability"] == capability
                   and m["state"] == "ACTIVE") <= 1:
                raise Refused("cannot make the last active member dormant")
            row.update(state="DORMANT", dormant_period=record["period"],
                       dormant_revision=record["evidence_revision"])
            row["history"].append(dict(event="dormant", assessment=assessment))
            self.store.put("member", row["id"], row)
            self.store.event("member-dormant", capability=capability, provider=provider, assessment=assessment)

    def wake(self, capability, provider, *, budget, principal):
        """DORMANT -> ACTIVE. Free if nothing touched it since dormancy; else fresh validation."""
        with self.store.transaction():
            row = self._row(capability, provider)
            if row is None or row["state"] != "DORMANT":
                raise Refused("only a dormant member can wake")
            stale = any(i["evidence_revision"] > row["dormant_revision"] and provider in i["affected"]
                        for i in self.store.find("impact"))
            if not stale:
                row["state"] = "ACTIVE"
                row["history"].append(dict(event="woke", validated=False))
                self.store.put("member", row["id"], row)
                self.store.event("member-woke", capability=capability, provider=provider, validated=False)
                return dict(validated=False)
        self.admit(capability, provider, budget=budget, principal=principal)
        return dict(validated=True)

    def retire(self, capability, provider, *, assessment, reason):
        """ACTIVE/DORMANT -> ARCHIVED, only with a verified `redundant` assessment."""
        if not reason:
            raise Refused("retirement requires a reason")
        with self.store.transaction():
            record, row = self._verified(capability, provider, assessment, ("redundant",))
            params = record["params"]
            if params["dormancy_first"]:
                if row["state"] != "DORMANT":
                    raise Refused("this capability retires only from dormancy")
                if record["period"] - row["dormant_period"] < params["min_dormant_age"]:
                    raise Refused("member has not been dormant long enough")
            if row["state"] == "ACTIVE" and sum(1 for m in self.store.find("member")
                    if m["capability"] == capability and m["state"] == "ACTIVE") <= 1:
                raise Refused("cannot retire the last active member of a capability")
            row["state"] = "ARCHIVED"
            row["history"].append(dict(event="retired", reason=reason, assessment=assessment))
            self.store.put("member", row["id"], row)
            self.store.put("retirement", uid(), dict(member=row["id"], reason=reason, assessment=assessment))
            self.store.event("member-retired", capability=capability, provider=provider, assessment=assessment)

    def restore(self, capability, provider, *, budget, principal):
        """Regeneration: an archived member returns only through fresh validation."""
        if self.state(capability, provider) != "ARCHIVED":
            raise Refused("only an archived member can be regenerated")
        return self.admit(capability, provider, budget=budget, principal=principal)

    def maintain(self, capability, budget, principal, *, charge):
        """Advance one maintenance period; charge declared upkeep for ACTIVE and DORMANT members.

        `charge` is the ledger's charge function (operator wiring); returns units charged.
        """
        with self.store.transaction():
            record = self.store.get("capability", capability)
            units = 0
            for row in self.store.find("member"):
                if row["capability"] != capability or row["state"] not in ("ACTIVE", "DORMANT"):
                    continue
                rate = record["maintenance"].get(row["provider"], dict(active=0, dormant=0))
                units += rate["active" if row["state"] == "ACTIVE" else "dormant"]
            record["period"] += 1
            self.store.put("capability", capability, record)
            self.store.event("maintenance-period", capability=capability, period=record["period"], units=units)
        if units:
            charge(budget, principal, {"maintenance": units}, f"maintenance:{capability}")
        return units
