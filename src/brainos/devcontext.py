"""The capability surface handed to developmental code (search, ecology).

Developmental code never receives the Runtime, the resource ledger, the raw
store or the transactor. It gets closures for exactly the operations it needs:
spending from budgets it was given (never creating or funding one), resolving
and registering providers, admitting members, running pure computation,
lifecycle requests that the population independently verifies, and writing
only whitelisted record kinds.

This is in-process capability discipline in a trusted-code profile, not a
sandbox. Python introspection of closure cells can still reach the services;
the fitness tests check that developmental modules do not do so.
"""
from types import SimpleNamespace

from .contracts import Refused

WRITABLE = frozenset({"construction", "construction-run", "ecology", "ecology-decision", "assimilation-trial"})
READABLE = WRITABLE | {"provider", "capability", "member", "retention-assessment", "invocation", "task",
                       "assimilation", "candidate"}


def development_context(runtime):
    store, ledger, registry = runtime.store, runtime.resources, runtime.registry
    population, fabric, transactor = runtime.population, runtime.fabric, runtime.transactor

    def write(kind, key, value, event, **fields):
        if kind not in WRITABLE:
            raise Refused("developmental code may not write this record kind")
        with store.transaction():
            store.put(kind, key, value)
            store.event(event, **fields)

    def get(kind, key):
        if kind not in READABLE:
            raise Refused("developmental code may not read this record kind")
        with store.mutex:
            return store.get(kind, key)

    def find(kind):
        if kind not in READABLE:
            raise Refused("developmental code may not read this record kind")
        with store.mutex:
            return store.find(kind)

    def bind_role(role, provider, cases, budget, principal):
        candidate = transactor.stage({role: provider})
        transactor.validate(candidate, {role: cases}, budget=budget, principal=principal)
        transactor.commit(candidate)
        return role

    def prepare_membership(capability, provider, budget, principal):
        """Stage and validate (not commit) a membership candidate on the contract's own cases."""
        cases = population.contract(capability)["admission_cases"]
        candidate = transactor.stage_membership(capability, provider)
        transactor.validate(candidate, {capability: cases}, budget=budget, principal=principal)
        return candidate

    def prepare_binding(role, provider, cases, budget, principal):
        candidate = transactor.stage({role: provider})
        transactor.validate(candidate, {role: cases}, budget=budget, principal=principal)
        return candidate

    def catalogue():
        from . import providers
        return [providers.specification(name) for name in sorted(providers.PRIMITIVES)]

    def dependents(parents):
        """Roles and active members whose providers depend (transitively) on any parent."""
        parents = set(parents)
        with store.mutex:
            specs = {row["id"]: row for row in store.find("provider")}
            rows = store.find("member")
        def depends(key):
            return key in parents or bool(set(specs[key].get("transitive_dependencies", [])) & parents)
        roles = {role: key for role, key in runtime.manifest()["bindings"].items() if depends(key)}
        members = [m["id"] for m in rows if m["state"] == "ACTIVE" and m["provider"] not in parents
                   and depends(m["provider"])]
        return dict(roles=roles, members=members)

    def budget_view(budget, principal):
        record = ledger.budget(budget, principal)
        return dict(available=dict(record["available"]), spent=dict(record["spent"]))

    return SimpleNamespace(
        manifest=runtime.manifest, write=write, get=get, find=find,
        active_providers=fabric.active_providers, resolve=registry.resolve,
        register_composite=fabric.register, evidence_current=fabric.evidence_current,
        define_capability=population.define, admit=population.admit, members=population.members,
        assess=population.assess, make_dormant=population.make_dormant, wake=population.wake,
        retire=population.retire, regenerate=population.restore, member_state=population.state,
        bind_role=bind_role, charge=ledger.charge, budget=budget_view,
        spent=lambda budget, principal: budget_view(budget, principal)["spent"],
        compute=lambda *args, **kwargs: runtime.runner.compute(*args, **kwargs),  # late-bound profile
        clear_prepared=lambda: runtime.runner.clear_prepared(),
        catalogue=catalogue, register=registry.register, register_graph=registry.register_graph,
        dependents=dependents, prepare_membership=prepare_membership, prepare_binding=prepare_binding,
        commit_assimilation=transactor.commit_assimilation, revert_assimilation=transactor.revert_assimilation)
