"""Registry identity checks and enforced impact records.

Every staging, validation, commit, task admission, execution and membership
path resolves providers here, so a `block` impact recorded against a provider
is refused at all of those boundaries (Doc 29 section 29.2).
"""
import hashlib
import math
import re

from .contracts import Refused, encode, quantities, uid
from . import closure, graphs, providers

EXTERNAL_COST_CATEGORIES = ("initialization", "inference", "transport", "memory",
                            "accelerator", "overhead")
EXTERNAL_MEASURED_BY = ("kernel", "adapter")
ARTIFACT_ALGORITHMS = {"sha256": re.compile(r"^[0-9a-f]{64}$")}


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
                          cost_schedule, cost_units, measured_by, artifact,
                          artifact_algorithm="sha256", identities, sampling=None,
                          nondeterministic, admission=None, issued_by="operator"):
        """Operator-only registration of an external provider (R-02-14).

        The trusted catalogue stays closed to external code: this path pins
        the artifact digest and declared identities instead of verifying
        against catalogue sources. Developmental code is never an operator,
        so it cannot reach this path (it is not exposed through the
        development context). The recorded provider takes the identical
        resolution, blocking, task, ledger and lifecycle paths as any
        member; `kind` stays `"external"` so checks can tell substrates
        apart without granting privilege.

        Identity (B26) is the canonical digest of the complete immutable
        specification — same weights with a different tokenizer, prompt,
        sampling, runtime or cost schedule are different providers that
        share the artifact but never each other's competence evidence or
        authority. Re-registration with different semantics is refused
        (B27); identical re-registration is idempotent.
        """
        if issued_by not in self.operators:
            raise Refused("only an operator principal may register external providers")
        if not implementation or not input or not output or not capability:
            raise Refused("external provider needs implementation, schemas and capability")
        cost = quantities(cost)
        core = dict(kind="external", implementation=implementation, input=input, output=output,
                    input_unit=graphs.unit(input), output_unit=graphs.unit(output),
                    capability=capability, cost=cost)
        core["cost_schedule"] = self._cost_schedule(cost_schedule)
        core["cost_units"], core["measured_by"] = self._cost_metadata(cost_units, measured_by)
        core["artifact"], core["artifact_algorithm"] = self._artifact(artifact, artifact_algorithm)
        core["identities"] = self._identities(identities)
        core["sampling"] = self._sampling(sampling, nondeterministic)
        core["nondeterministic"] = nondeterministic
        core["admission"] = self._admission(admission, nondeterministic)
        core["transitive_dependencies"] = []
        core["footprint"] = {"resources": ["external"], "failure_domains": ["external-process"]}
        digest = hashlib.sha256(encode(core).encode()).hexdigest()
        key = f"{implementation}@ext-{digest[:16]}"
        spec = dict(core, provider_digest=digest, id=key)
        with self.store.transaction():
            try:
                existing = self.store.get("provider", key)
            except Refused:
                existing = None
            if existing is not None and existing != spec:
                raise Refused("provider identity is pinned: re-registration with "
                              "different semantics is refused")
            self.store.put("provider", key, spec)
            self.store.event("provider-registered", provider=key, provider_kind="external")
        return key

    @staticmethod
    def _cost_schedule(schedule):
        if not isinstance(schedule, dict) or set(schedule) != set(EXTERNAL_COST_CATEGORIES):
            raise Refused(f"cost schedule needs exactly {EXTERNAL_COST_CATEGORIES}")
        for name, value in schedule.items():
            if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
                raise Refused(f"cost schedule {name!r} must be a finite nonnegative number")
        return dict(schedule)

    @staticmethod
    def _cost_metadata(units, measured_by):
        """Units and measurement sources per category (B30): categories are
        never summed across incompatible quantities; conversion is declared
        per experiment at the net-value mapping, not in the registry."""
        if not isinstance(units, dict) or set(units) != set(EXTERNAL_COST_CATEGORIES):
            raise Refused(f"cost units needed for exactly {EXTERNAL_COST_CATEGORIES}")
        if any(not isinstance(u, str) or not u for u in units.values()):
            raise Refused("cost units must be nonempty unit names")
        if not isinstance(measured_by, dict) or set(measured_by) != set(EXTERNAL_COST_CATEGORIES):
            raise Refused(f"measurement sources needed for exactly {EXTERNAL_COST_CATEGORIES}")
        if any(m not in EXTERNAL_MEASURED_BY for m in measured_by.values()):
            raise Refused(f"measurement sources must be {EXTERNAL_MEASURED_BY}")
        return dict(units), dict(measured_by)

    @staticmethod
    def _artifact(artifact, algorithm):
        if algorithm not in ARTIFACT_ALGORITHMS:
            raise Refused(f"unknown artifact algorithm {algorithm!r}")
        if not isinstance(artifact, str) or not ARTIFACT_ALGORITHMS[algorithm].match(artifact):
            raise Refused("artifact digest must match its declared algorithm format")
        return artifact, algorithm

    @staticmethod
    def _identities(identities):
        if not isinstance(identities, dict):
            raise Refused("external provider needs declared identities")
        for name in ("model", "runtime"):
            if not identities.get(name) or not isinstance(identities[name], str):
                raise Refused(f"external provider needs a {name} identity")
        for name in ("tokenizer", "prompt_template", "adapter"):
            if name in identities and (not identities[name] or not isinstance(identities[name], str)):
                raise Refused(f"declared {name} identity must be a nonempty string")
        return dict(identities)

    @staticmethod
    def _sampling(sampling, nondeterministic):
        if not isinstance(nondeterministic, bool):
            raise Refused("external provider must declare determinism explicitly")
        if nondeterministic:
            if not isinstance(sampling, dict) or not sampling:
                raise Refused("a nondeterministic provider must declare its sampling configuration")
            return dict(sampling)
        if sampling:
            raise Refused("a deterministic provider must not declare sampling configuration")
        return {}

    @staticmethod
    def _admission(admission, nondeterministic):
        """k-of-n admission policy (R-02-15): per-provider declared evidence bar.
        Nondeterministic providers require it; deterministic providers must not
        declare it. The policy is part of the provider identity: changing what
        'admitted' means is a new provider, and old evidence never transfers."""
        if nondeterministic:
            if not isinstance(admission, dict):
                raise Refused("a nondeterministic provider must declare its admission policy")
            try:
                n, k = admission["n"], admission["k"]
            except (KeyError, TypeError):
                raise Refused("admission policy needs integer n and k")
            if type(n) is not int or type(k) is not int or not 1 <= k <= n:
                raise Refused("admission policy needs 1 <= k <= n as integers")
            if set(admission) != {"n", "k"}:
                raise Refused("admission policy carries only n and k")
            return dict(n=n, k=k)
        if admission:
            raise Refused("a deterministic provider must not declare an admission policy")
        return {}

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

    @classmethod
    def _external_record(cls, spec):
        """Re-derive the canonical external record: tampered pins fail closed."""
        try:
            cost = quantities(spec["cost"])
            schedule = cls._cost_schedule(spec["cost_schedule"])
            units, measured = cls._cost_metadata(spec["cost_units"], spec["measured_by"])
            artifact, algorithm = cls._artifact(spec["artifact"], spec["artifact_algorithm"])
            identities = cls._identities(spec["identities"])
            sampling = cls._sampling(spec.get("sampling", {}), spec["nondeterministic"])
            admission = cls._admission(spec.get("admission", {}), spec["nondeterministic"])
            core = dict(kind="external", implementation=spec["implementation"], input=spec["input"],
                        output=spec["output"], input_unit=graphs.unit(spec["input"]),
                        output_unit=graphs.unit(spec["output"]),
                        capability=spec["capability"], cost=cost, admission=admission,
                        cost_schedule=schedule, cost_units=units, measured_by=measured,
                        artifact=artifact, artifact_algorithm=algorithm, identities=identities,
                        sampling=sampling, nondeterministic=spec["nondeterministic"],
                        transitive_dependencies=[], footprint={
                            "resources": ["external"], "failure_domains": ["external-process"]})
        except (KeyError, TypeError, AttributeError) as exc:
            raise Refused(f"external provider record is malformed: {exc}")
        if (not core["implementation"] or not core["input"] or not core["output"]
                or not core["capability"]):
            raise Refused("external provider record is malformed")
        digest = hashlib.sha256(encode(core).encode()).hexdigest()
        if spec.get("provider_digest") != digest:
            raise Refused("external provider identity does not match its specification")
        return dict(core, provider_digest=digest,
                    id=f"{core['implementation']}@ext-{digest[:16]}")

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
