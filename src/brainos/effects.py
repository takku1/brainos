"""A durable simulated external endpoint, independently journaled from Core."""
from .contracts import Refused, digest, uid
from .storage import Store


class LocalReceiptSink:
    def __init__(self, path, name="local-receipts"):
        self.name = name
        self.store = Store(path)
        with self.store.transaction():
            identities = self.store.find("endpoint")
            if identities:
                self.identity = identities[0]["identity"]
            else:
                self.identity = "endpoint:" + uid()
                self.store.put("endpoint", "identity", {"identity": self.identity})
                self.store.event("endpoint-initialized", identity=self.identity)

    def applied_events(self):
        return [event for event in self.store.journal() if event["kind"] == "applied"]

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.store.close()

    def apply(self, operation_id, payload):
        with self.store.transaction():
            receipts = {r["operation_id"]: r for r in self.store.find("receipt")}
            if operation_id in receipts:
                record = receipts[operation_id]
                if record["payload_digest"] != digest(payload):
                    raise Refused("idempotency key reused for another payload")
                return record
            record = dict(operation_id=operation_id, endpoint=self.identity,
                          payload_digest=digest(payload), payload=payload)
            self.store.put("receipt", operation_id, record)
            self.store.event("applied", operation=operation_id, payload_digest=record["payload_digest"])
            return record

    def lookup(self, operation_id):
        with self.store.mutex:
            for record in self.store.find("receipt"):
                if record["operation_id"] == operation_id:
                    return record
            return None
