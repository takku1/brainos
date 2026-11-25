"""Test-only external adapter: line-delimited JSON over stdio.

Speaks the worker wire protocol with test-only behaviors. Normal requests
echo the input value back (identity function), so admission cases can pin
exact outputs; any input containing "?" abstains with "ABSTAIN". Faults
are driven by string values of the form "__mock__:<mode>[:<arg>]":

  crash          exit(1) immediately (supervision must restart us)
  timeout        sleep <seconds> (default 30; the kernel deadline must win)
  malformed      emit a non-JSON line
  wrong-artifact reply with artifact "0"*64 (kernel pin check must refuse)
  error          reply {"ok": false} with the given message
  alternate      even calls echo, odd calls reply "WRONG" (scripted flakiness)

Usage: python -m implementations.mock_adapter [--expect-artifact DIGEST]
The adapter checks each request's artifact against --expect-artifact when
given, simulating the adapter-side pin check; mismatches get an error
reply instead of execution.
"""
import argparse
import json
import sys
import time


def normalize_ws(value):
    return " ".join(value.split())


def answer(request, calls, expect_artifact, normalize):
    if expect_artifact is not None and request.get("artifact") != expect_artifact:
        return {"ok": False, "error": "adapter artifact pin mismatch",
                "artifact": request.get("artifact")}
    value = request.get("value")
    if normalize and isinstance(value, str):
        return {"ok": True, "result": normalize_ws(value), "artifact": request.get("artifact"),
                "compute_ns": 0}
    if isinstance(value, str) and "?" in value:
        return {"ok": True, "result": "ABSTAIN", "artifact": request.get("artifact"),
                "compute_ns": 0}
    if isinstance(value, str) and value.startswith("__mock__:"):
        parts = value.split(":", 2)
        mode = parts[1] if len(parts) > 1 else ""
        arg = parts[2] if len(parts) > 2 else ""
        if mode == "crash":
            sys.stdout.flush()
            sys.exit(1)
        if mode == "timeout":
            time.sleep(float(arg or 30))
            return {"ok": True, "result": value, "artifact": request.get("artifact"),
                    "compute_ns": 0}
        if mode == "malformed":
            sys.stdout.write("this is not json\n")
            sys.stdout.flush()
            return {"ok": True, "result": value, "artifact": request.get("artifact"),
                    "compute_ns": 0}
        if mode == "wrong-artifact":
            return {"ok": True, "result": value, "artifact": "0" * 64, "compute_ns": 0}
        if mode == "error":
            return {"ok": False, "error": arg or "mock error",
                    "artifact": request.get("artifact")}
        if mode == "alternate":
            calls[0] += 1
            if calls[0] % 2 == 0:
                return {"ok": True, "result": "WRONG", "artifact": request.get("artifact"),
                        "compute_ns": 0}
        if mode == "abstain-if-unknown":
            return {"ok": True, "result": "ABSTAIN", "artifact": request.get("artifact"),
                    "compute_ns": 0}
    started = time.perf_counter_ns()
    result = value
    return {"ok": True, "result": result, "artifact": request.get("artifact"),
            "compute_ns": time.perf_counter_ns() - started}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--expect-artifact", default=None)
    parser.add_argument("--normalize", action="store_true",
                        help="normalize whitespace instead of echoing (L1 parity double)")
    args = parser.parse_args(argv)
    sys.stdout.write(json.dumps({"ready": True}) + "\n")
    sys.stdout.flush()
    calls = [0]
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except ValueError:
            sys.stdout.write(json.dumps({"ok": False, "error": "bad request"}) + "\n")
            sys.stdout.flush()
            continue
        sys.stdout.write(json.dumps(answer(request, calls, args.expect_artifact,
                                           args.normalize)) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
