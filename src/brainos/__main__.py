"""Run the first real execution/restart/replacement demonstration."""
import argparse
import json
from pathlib import Path

from . import Refused, Runtime, Unresolved
from .effects import LocalReceiptSink


def install(runtime, bindings, cases):
    ids = {role: runtime.registry.register(name) for role, name in bindings.items()}
    candidate = runtime.transactor.stage(ids)
    runtime.transactor.validate(candidate, cases)
    runtime.transactor.commit(candidate)
    return ids


def execute(runtime, budget, role, value):
    task = runtime.tasks.create_task("demo", role, value, budget)
    permit = runtime.tasks.authorize(task, "demo")
    return task, permit, runtime.tasks.run_task(task, permit, "demo")


def demo(directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    interrupted = False

    def lose_ack(point):
        nonlocal interrupted
        if point == "after_effect_applied" and not interrupted:
            interrupted = True
            raise OSError("injected lost acknowledgment")

    with LocalReceiptSink(directory / "receipts.sqlite3") as sink:
        with Runtime(directory / "core.sqlite3", failpoint=lose_ack) as runtime:
            install(runtime, {"parse": "parse_csv", "total": "sum"},
                    {"parse": [("1, 2, 3", [1, 2, 3])], "total": [([1, 2, 3], 6), ([], 0)]})
            budget = runtime.resources.create_budget("demo", {"attempts": 8})
            _, _, values = execute(runtime, budget, "parse", "10,20,30")
            task, old_permit, total = execute(runtime, budget, "total", values)
            payload = {"checked_total": total}
            support = runtime.evidence.record_evidence("demo-policy-check", {"approved": True}, "Certified",
                support=runtime.effects.required_support(task, "demo", sink.identity, payload))
            effect, permit = runtime.effects.prepare_effect(task, "demo", sink.identity,
                payload, budget, [support])
            try:
                runtime.effects.dispatch_effect(effect, permit, "demo", sink)
            except Unresolved:
                pass
            old_epoch = runtime.manifest()["epoch"]
        with Runtime(directory / "core.sqlite3") as runtime:
            receipt = runtime.effects.reconcile_effect(effect, "demo", sink)
            try:
                runtime.authority.check_permit(old_permit, "demo", "task", task)
            except Refused:
                old_authority_rejected = True
            else:
                raise RuntimeError("restart incorrectly preserved authority")
            install(runtime, {"total": "sum_loop"}, {"total": [([10, 20, 30], 60), ([], 0)]})
            _, _, replacement = execute(runtime, budget, "total", [10, 20, 30])
            return dict(total=total, recovered_receipt=receipt, replacement_result=replacement,
                        epoch_advanced=runtime.manifest()["epoch"] > old_epoch,
                        old_authority_rejected=old_authority_rejected,
                        effect_applications=sum(e["kind"] == "applied" and e.get("operation") == effect
                                                for e in sink.store.journal()),
                        budget=runtime.resources.budget(budget, "demo"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dir", default=".brainos/demo", help="local durable demonstration state")
    args = parser.parse_args()
    print(json.dumps(demo(args.state_dir), indent=2))


if __name__ == "__main__":
    main()
