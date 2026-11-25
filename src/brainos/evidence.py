"""Evidence validity, verdict-only checks, and explicit adjudication."""
from .contracts import Refused, positive_time, uid


class EvidenceLedger:
    def __init__(self, store, control, clock):
        self.store = store
        self.control = control
        self.clock = clock

    def record_evidence(self, source, payload, tier="Observed", ttl=3600, *, support=None):
        """Trusted operator ingestion; a provider cannot assign itself a tier."""
        if not source or tier not in ("Observed", "Believed", "Certified"):
            raise Refused("invalid source or tier")
        positive_time(ttl)
        key = uid()
        with self.store.transaction():
            self.store.put("evidence", key, dict(id=key, source=source, payload=payload,
                tier=tier, state="ACTIVE", suspend_epoch=None, expires=self.clock() + ttl,
                support=support))
            self._bump_evidence()
            self.store.event("evidence-recorded", evidence=key, tier=tier)
        return key

    def _bump_evidence(self):
        state = self.control.read()
        state["evidence_revision"] += 1
        self.store.put("control", "current", state)

    def challenge(self, key, grounds):
        if not grounds:
            raise Refused("challenge grounds required")
        with self.store.transaction():
            record = self.store.get("evidence", key)
            if record["state"] not in ("ACTIVE", "RESTORED"):
                raise Refused("claim is not challengeable")
            record.update(state="CHALLENGED", suspend_epoch=self.control.read()["epoch"] + 1)
            self.store.put("evidence", key, record)
            self._bump_evidence()
            self.store.event("challenged", evidence=key, grounds=grounds)

    def verify(self, key, verdict, procedure):
        if verdict not in ("PASS", "FAIL", "INCONCLUSIVE") or not procedure:
            raise Refused("verification needs a declared result and procedure")
        proof = uid()
        with self.store.transaction():
            self.store.get("evidence", key)
            self.store.put("proof", proof, dict(target=key, verdict=verdict, procedure=procedure,
                evidence_revision=self.control.read()["evidence_revision"]))
            self.store.event("verified", evidence=key, verdict=verdict, proof=proof)
        return proof

    def restore(self, key, proof):
        with self.store.transaction():
            claim = self.store.get("evidence", key)
            result = self.store.get("proof", proof)
            if (claim["state"] != "CHALLENGED" or result["target"] != key
                    or result["verdict"] != "PASS"
                    or claim["expires"] <= self.clock()
                    or result["evidence_revision"] != self.control.read()["evidence_revision"]):
                raise Refused("restoration proof is stale, mismatched or insufficient")
            claim.update(state="RESTORED", suspend_epoch=None)
            self.store.put("evidence", key, claim)
            self._bump_evidence()
            self.store.event("restored", evidence=key, proof=proof)

    def check_support(self, refs, *, consequential=False, required_scope=None):
        if not isinstance(refs, (list, tuple)):
            raise Refused("evidence references must be an explicit list or tuple")
        if consequential and not refs:
            raise Refused("consequential effects require certified evidence")
        for key in refs:
            claim = self.store.get("evidence", key)
            if claim["expires"] <= self.clock():
                raise Refused("support has expired")
            if consequential and claim["tier"] != "Certified":
                raise Refused("Certified evidence required")
            if consequential and (required_scope is None or claim.get("support") != required_scope):
                raise Refused("evidence does not support this claim, task, target, operation and context")
            if claim["state"] == "CHALLENGED":
                if consequential or self.control.read()["epoch"] >= claim["suspend_epoch"]:
                    raise Refused("support is challenged")
            elif claim["state"] not in ("ACTIVE", "RESTORED"):
                raise Refused("support is inactive")
