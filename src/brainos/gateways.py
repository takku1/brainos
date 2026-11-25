"""Effect intent, fresh boundary admission, and uncertain-outcome reconciliation."""
from .contracts import Refused, Unresolved, PermitScope, ReceiptEndpoint, digest, uid, require_owner


class EffectGateway:
    def __init__(self, store, control, resources, evidence, authority, failpoint):
        self.store = store
        self.control = control
        self.resources = resources
        self.evidence = evidence
        self.authority = authority
        self.failpoint = failpoint

    def required_support(self, key, principal, target, payload):
        with self.store.mutex:
            task = self.store.get("task", key)
            require_owner(task, principal)
            return dict(task=key, target=target, operation="dispatch", context=task["context"], claim=digest(payload))

    def prepare_effect(self, key, principal, target, payload, budget, evidence, *, effect_id=None, ttl=60):
        effect_id = effect_id or uid()
        with self.store.transaction():
            task = self.store.get("task", key)
            require_owner(task, principal)
            if task["state"] != "SUCCEEDED" or task["revision"] != self.control.read()["revision"]:
                raise Refused("effect requires a successful result under the current manifest")
            if any(e["id"] == effect_id for e in self.store.find("effect")):
                raise Refused("effect ID exists; reconcile or reauthorize that exact intent")
            if not isinstance(target, str) or not target.startswith("endpoint:"):
                raise Refused("a stable endpoint identity is required, not its display name")
            required = self.required_support(key, principal, target, payload)
            self.evidence.check_support(evidence, consequential=True, required_scope=required)
            holding = self.resources.reserve_tx(budget, principal, {"attempts": 1}, effect_id)
            self.resources.allocate_tx(holding, principal)
            effect = dict(id=effect_id, task=key, principal=principal, target=target,
                          payload=payload, context=task["context"], holding=holding, state="INTENT", receipt=None)
            self.store.put("effect", effect_id, effect)
            scope = PermitScope("effect", effect_id, principal, digest(effect), target,
                                task["context"], "dispatch", subject=key, claim=digest(payload))
            token = self.authority.issue_tx(scope, evidence, ttl)
            self.store.event("effect-intent", effect=effect_id)
        return effect_id, token

    def dispatch_effect(self, key, token, principal, sink: ReceiptEndpoint):
        self.failpoint("before_effect_admission")
        with self.store.transaction():
            effect = self.store.get("effect", key)
            require_owner(effect, principal)
            if effect["target"] != sink.identity:
                raise Refused("wrong effect endpoint")
            permit = self.authority.check_permit(token, principal, "effect", key)
            if effect["state"] != "INTENT" or permit["payload_digest"] != digest(effect):
                raise Unresolved("effect must be reconciled or has changed")
            if self.store.get("holding", effect["holding"])["state"] != "ALLOCATED":
                raise Refused("effect has no live allocation")
            effect["state"] = "DISPATCHED"
            effect["dispatch_admission"] = dict(epoch=permit["epoch"], revision=permit["revision"],
                                                endpoint=sink.identity, linearization="durable-dispatch-commit")
            self.store.put("effect", key, effect)
            self.store.event("effect-dispatched", effect=key, admission=effect["dispatch_admission"])
        # This commit is dispatch admission, not completed external application.
        # Later revocation/challenge/publication cannot recall an admitted effect.
        self.failpoint("before_effect_apply")
        try:
            receipt = sink.apply(key, effect["payload"])
            self.failpoint("after_effect_applied")
        except Exception as exc:
            with self.store.transaction():
                effect.update(state="UNKNOWN", error=str(exc))
                self.store.put("effect", key, effect)
                self.store.event("effect-unknown", effect=key)
            raise Unresolved("effect outcome unknown; reconcile before retry") from exc
        self._confirm(effect, receipt)
        return receipt

    def _confirm(self, effect, receipt):
        if (receipt.get("payload_digest") != digest(effect["payload"])
                or receipt.get("operation_id") != effect["id"]
                or receipt.get("endpoint") != effect["target"]):
            raise Unresolved("receipt does not match the effect payload")
        with self.store.transaction():
            effect.update(state="CONFIRMED", receipt=receipt)
            self.resources.charge_tx(effect["holding"])
            self.store.put("effect", effect["id"], effect)
            self.store.event("effect-confirmed", effect=effect["id"])

    def reconcile_effect(self, key, principal, sink: ReceiptEndpoint):
        with self.store.mutex:
            effect = self.store.get("effect", key)
            require_owner(effect, principal)
            if effect["target"] != sink.identity:
                raise Refused("wrong effect endpoint")
            if effect["state"] == "CONFIRMED":
                return effect["receipt"]
            if effect["state"] not in ("UNKNOWN", "DISPATCHED"):
                raise Refused("effect is not awaiting reconciliation")
            receipt = sink.lookup(key)
            if receipt is None:
                raise Unresolved("no confirmed receipt; operator reconciliation required, no blind retry")
            self._confirm(effect, receipt)
            return receipt
