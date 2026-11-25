"""Registry identity checks and enforced impact records.

Every staging, validation, commit, task admission, execution and membership
path resolves providers here, so a `block` impact recorded against a provider
is refused at all of those boundaries (Doc 29 section 29.2).
"""
import math

from .contracts import Refused, quantities, uid
from . import closure, graphs, providers

EXTERNAL_COST_CATEGORIES = ("initialization", "inference", "transport", "memory",
                            "accelerator", "overhead")


class ProviderRegistry:
    def __init__(self, store, operators=frozenset({"operator"})):
        self.store = store
        self.operators = frozenset(operators)

    def register(self, implementation):
        spec = providers.specification(implementation)
        with self.store.transaction():
            self.store.put("provider", spec["id"], spec)
            self.store.event("provider-registered", provider=spec["id"])
        return spec["id"]

    def register_external(self, *, implementation, input, output, capability, cost,
                          cost_schedule, artifact, identities, nondeterministic,
                          issued_by="operator"):
        """Operator-only registration of an external provider (R-02-14).

        The trusted catalogue stays closed to external code: this path pins
        the artifact digest and declared identities instead of verifying
        against catalogue sources. Developmental code is never an operator,
        so it cannot reach this path (it is not exposed through the
        development context). The recorded provider takes the identical
        resolution, blocking, task, ledger and lifecycle paths as any
        member; `kind` stays `"external"` so checks can tell substrates
        apart without granting privilege.
        """
        if issued_by not in self.operators:
            raise Refused("only an operator principal may register external providers")
        if not implementation or not input or not output or not capability:
            raise Refused("external provider needs implementation, schemas and capability")
        cost = quantities(cost)
        if not isinstance(cost_schedule, dict) or set(cost_schedule) != set(EXTERNAL_COST_CATEGORIES):
            raise Refused(f"cost schedule needs exactly {EXTERNAL_COST_CATEGORIES}")
        for name, value in cost_schedule.items():
            if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
                raise Refused(f"cost schedule {name!r} must be a finite nonnegative number")
        if not artifact or not isinstance(artifact, str):
            raise Refused("external provider needs a pinned artifact digest")
        if (not isinstance(identities, dict) or not identities.get("model")
                or not identities.get("runtime")):
            raise Refused("external provider needs model and runtime identities")
        if not isinstance(nondeterministic, bool):
            raise Refused("external provider must declare determinism explicitly")
        core = dict(kind="external", implementation=implementation, input=input, output=output,
                    capability=capability, cost=cost, cost_schedule=dict(cost_schedule),
                    artifact=artifact, identities=dict(identities),
                    nondeterministic=nondeterministic, transitive_dependencies=[],
                    footprint={"resources": ["external"], "failure_domains": ["external-process"]})
        key = f"{implementation}@ext-{core['artifact'][:16]}"
        spec = dict(core, id=key)
        with self.store.transaction():
            self.store.put("provider", key, spec)
            self.store.event("provider-registered", provider=key, provider_kind="external")
        return key

    def blocking_impact(self, key):
        for impact in self.store.find("impact"):
            if impact["action"] == "block" and key in impact["affected"]:
                return impact
        return None

    def resolve(self, key, _stack=()):
        if key in _stack or len(_stack) > 16:
            raise Refused("cyclic artifact dependency")
        impact = self.blocking_impact(key)
        if impact is not None:
            raise Refused(f"provider is blocked by {impact['kind']} impact {impact['id']}: {impact['reason']}")
        spec = self.store.get("provider", key)
        if spec.get("kind") == "graph":
            expected = graphs.specification(spec, spec["capability"],
                lambda ref: self.resolve(ref, (*_stack, key)))
        elif spec.get("kind") == "external":
            expected = self._external_record(spec)
        else:
            expected = providers.specification(spec["implementation"])
        if spec != expected:
            raise Refused("registry artifact does not match trusted catalogue")
        return spec

    @staticmethod
    def _external_record(spec):
        """Re-derive the canonical external record: tampered pins fail closed."""
        try:
            cost = quantities(spec["cost"])
            schedule = spec["cost_schedule"]
            if set(schedule) != set(EXTERNAL_COST_CATEGORIES):
                raise Refused("cost schedule drifted")
            for value in schedule.values():
                if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
                    raise Refused("cost schedule drifted")
            core = dict(kind="external", implementation=spec["implementation"], input=spec["input"],
                        output=spec["output"], capability=spec["capability"], cost=cost,
                        cost_schedule=dict(schedule), artifact=spec["artifact"],
                        identities=dict(spec["identities"]),
                        nondeterministic=spec["nondeterministic"],
                        transitive_dependencies=[], footprint={
                            "resources": ["external"], "failure_domains": ["external-process"]})
        except (KeyError, TypeError, AttributeError) as exc:
            raise Refused(f"external provider record is malformed: {exc}")
        if (not core["implementation"] or not core["input"] or not core["output"]
                or not core["capability"] or not core["artifact"]
                or not core["identities"].get("model") or not core["identities"].get("runtime")
                or not isinstance(core["nondeterministic"], bool)):
            raise Refused("external provider record is malformed")
        return dict(core, id=f"{core['implementation']}@ext-{core['artifact'][:16]}")

    def register_graph(self, definition, capability):
        spec = graphs.specification(definition, capability, self.resolve)
        with self.store.transaction():
            self.store.put("provider", spec["id"], spec)
            self.store.event("composite-registered", provider=spec["id"], dependencies=spec["dependencies"],
                             transitive=spec["transitive_dependencies"])
        return spec["id"]

    def population(self):
        return {row["id"]: row for row in self.store.find("provider")}

    def preview_impact(self, changed, kind):
        population = self.population()
        if any(key not in population for key in changed):
            raise Refused("impact names an unknown provider")
        return closure.population_closure(population, set(changed), kind)

    def record_impact(self, changed, kind, reason):
        """Compute closure over the population pinned by this transaction and enforce it."""
        if not reason:
            raise Refused("impact cause required")
        with self.store.transaction():
            affected, action = self.preview_impact(changed, kind)
            state = self.store.get("control", "current")
            state["evidence_revision"] += 1
            key = uid()
            self.store.put("impact", key, dict(id=key, kind=kind, cause=sorted(changed), reason=reason,
                affected=affected, action=action, evidence_revision=state["evidence_revision"],
                registry_size=len(self.store.find("provider"))))
            self.store.put("control", "current", state)
            self.store.event("impact-recorded", impact=key, impact_kind=kind, action=action, affected=affected)
        return key

    def exclude(self, key, reason):
        if not reason:
            raise Refused("exclusion cause required")
        return self.record_impact([key], "support", reason)
