"""Child process deliberately exits without cleanup at durable boundaries."""
import json
import os
from pathlib import Path
import sys

from brainos import Runtime
from brainos.__main__ import install, execute
from brainos.effects import LocalReceiptSink


def main():
    root, point = Path(sys.argv[1]), sys.argv[2]
    armed = False

    def crash(name):
        if armed and name == point:
            os._exit(73)

    with LocalReceiptSink(root / "sink.sqlite3") as sink:
        with Runtime(root / "core.sqlite3", failpoint=crash) as runtime:
            install(runtime, {"total": "sum"}, {"total": [([1, 2], 3)]})
            budget = runtime.resources.create_budget("demo", {"attempts": 4})
            old = runtime.manifest()
            witness = dict(budget=budget, old_revision=old["revision"], old_provider=old["bindings"]["total"])
            if "manifest" in point:
                provider = runtime.registry.register("sum_loop")
                candidate = runtime.transactor.stage({"total": provider})
                runtime.transactor.validate(candidate, {"total": [([1, 2], 3)]})
                witness.update(candidate=candidate, new_provider=provider)
                (root / "witness.json").write_text(json.dumps(witness), encoding="utf-8")
                armed = True
                runtime.transactor.commit(candidate)
            elif point == "after_invocation_start":
                task = runtime.tasks.create_task("demo", "total", [1, 2], budget)
                token = runtime.tasks.authorize(task, "demo")
                witness.update(task=task, token=token)
                (root / "witness.json").write_text(json.dumps(witness), encoding="utf-8")
                armed = True
                runtime.tasks.run_task(task, token, "demo")
            else:
                task, _, _ = execute(runtime, budget, "total", [1, 2])
                support = runtime.evidence.record_evidence("checker", {}, "Certified")
                effect, token = runtime.effects.prepare_effect(task, "demo", sink.name,
                    {"total": 3}, budget, [support])
                witness.update(effect=effect, token=token)
                (root / "witness.json").write_text(json.dumps(witness), encoding="utf-8")
                armed = True
                runtime.effects.dispatch_effect(effect, token, "demo", sink)
    raise RuntimeError("the requested crash point was never reached")


if __name__ == "__main__":
    main()
