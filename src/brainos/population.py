"""Capability contracts and provider populations (Doc 26 section 26.3).

Capability: what can be accomplished (contract: name, schemas, units and its
independent admission cases). Provider: one implementation artifact.
Membership: a validated assertion that a provider implements a contract.
Role: a manifest binding (owned by the transactor), separate from all three.
"""
from .contracts import Refused, digest, encode
from . import graphs
import json


class CapabilityPopulation:
    def __init__(self, store, registry, transactor):
        self.store = store
        self.registry = registry
        self.transactor = transactor

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
                                                   cases_digest=digest(cases)))
            self.store.event("capability-defined", capability=key)
        return key

    def contract(self, capability):
        with self.store.mutex:
            return self.store.get("capability", capability)

    def admit(self, capability, provider, *, budget, principal):
        """Validate the provider on the contract's own admission cases, then admit."""
        cases = self.contract(capability)["admission_cases"]
        candidate = self.transactor.stage_membership(capability, provider)
        self.transactor.validate(candidate, {capability: cases}, budget=budget, principal=principal)
        return self.transactor.commit_membership(candidate)

    def members(self, capability, *, include_archived=False):
        with self.store.mutex:
            rows = [m for m in self.store.find("member") if m["capability"] == capability
                    and (include_archived or m["state"] == "ACTIVE")]
        usable = []
        for row in rows:
            if self.registry.blocking_impact(row["provider"]) is None:
                usable.append(row)
        return usable

    def member(self, capability, provider):
        """An ACTIVE, unblocked member's provider spec, or Refused."""
        with self.store.mutex:
            row = next((m for m in self.store.find("member") if m["id"] == f"{capability}|{provider}"), None)
        if row is None or row["state"] != "ACTIVE":
            raise Refused("provider is not an active member of this capability")
        return self.registry.resolve(provider)

    def retire(self, capability, provider, *, reason, evidence):
        """Archive a member. Evidence must justify retirement (see ecology.retirement_evidence)."""
        if not reason or not isinstance(evidence, dict) or not evidence.get("justified"):
            raise Refused("retirement requires recorded redundancy or zero-contribution evidence")
        with self.store.transaction():
            key = f"{capability}|{provider}"
            row = self.store.get("member", key)
            if row["state"] != "ACTIVE":
                raise Refused("only an active member can be retired")
            others = [m for m in self.store.find("member") if m["capability"] == capability
                      and m["state"] == "ACTIVE" and m["id"] != key]
            if not others:
                raise Refused("cannot retire the last active member of a capability")
            row["state"] = "ARCHIVED"
            row["history"].append(dict(event="retired", reason=reason, evidence_digest=digest(evidence)))
            self.store.put("member", key, row)
            self.store.put("retirement", digest([key, len(row["history"])]),
                           dict(id=digest([key, len(row["history"])]), member=key, reason=reason, evidence=evidence))
            self.store.event("member-retired", capability=capability, provider=provider, reason=reason)

    def restore(self, capability, provider, *, budget, principal):
        """Regeneration: an archived member returns only through fresh validation."""
        return self.admit(capability, provider, budget=budget, principal=principal)
