"""Opaque scoped permits; authority does not execute provider payloads."""
from .contracts import Refused, PermitScope, positive_time, uid, require_owner


class Authority:
    def __init__(self, store, control, evidence, clock):
        self.store = store
        self.control = control
        self.evidence = evidence
        self.clock = clock

    def issue_tx(self, scope: PermitScope, refs, ttl):
        positive_time(ttl)
        if ttl > 3600:
            raise Refused("permit lifetime exceeds profile limit")
        if not isinstance(scope, PermitScope) or scope.kind not in ("task", "effect"):
            raise Refused("typed permit scope required")
        self.evidence.check_support(refs, consequential=scope.kind == "effect")
        state = self.control.read()
        token = uid()
        self.store.put("permit", token, dict(id=token, kind=scope.kind, target=scope.target,
            principal=scope.principal, provider=scope.provider, context=scope.context,
            operation=scope.operation, epoch=state["epoch"], revision=state["revision"],
            payload_digest=scope.content_digest, evidence=list(refs), expires=self.clock() + ttl, revoked=False))
        self.store.event("authorized", permit=token, target=scope.target, permit_kind=scope.kind)
        return token

    def check_permit(self, token, principal, kind, target, *, fresh=True):
        if not isinstance(token, str):
            raise Refused("opaque permit reference required")
        permit = self.store.get("permit", token)
        require_owner(permit, principal)
        if permit["kind"] != kind or permit["target"] != target:
            raise Refused("permit scope mismatch")
        if fresh:
            state = self.control.read()
            if permit["revoked"] or permit["expires"] <= self.clock():
                raise Refused("permit revoked or expired")
            if (permit["epoch"], permit["revision"]) != (state["epoch"], state["revision"]):
                raise Refused("stale authority epoch or manifest")
            self.evidence.check_support(permit["evidence"], consequential=kind == "effect")
        return permit

    def revoke(self, token):
        with self.store.transaction():
            record = self.store.get("permit", token)
            record["revoked"] = True
            self.store.put("permit", token, record)
            self.store.event("revoked", permit=token)

    def cut_epoch(self):
        with self.store.transaction():
            state = self.control.read()
            state["epoch"] += 1
            self.store.put("control", "current", state)
            self.store.event("epoch-cut", epoch=state["epoch"])
