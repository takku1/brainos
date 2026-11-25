"""Trusted catalogue worker protocol; not a hostile-code sandbox.

`python -m brainos.worker` answers one request on stdin (fresh-subprocess
profile). `python -m brainos.worker --serve` answers line-delimited requests
until stdin closes (persistent profile). Both use `answer`, which the
in-process profile also calls, so every profile verifies the same artifact.
"""
import json
import os
import sys

from .contracts import PROTOCOL_LIMIT, encode
from .providers import clear_prepared, specification, timed_compute


def answer(raw):
    """Verify the request against the trusted catalogue and compute it."""
    try:
        if len(raw) > PROTOCOL_LIMIT:
            raise ValueError("input exceeds protocol limit")
        request = json.loads(raw)
        spec = specification(request["implementation"])
        if request["artifact"] != spec["artifact"]:
            raise ValueError("artifact digest mismatch")
        if request.get("control") == "clear-prepared":
            clear_prepared()
            return {"ok": True, "result": None, "compute_ns": 0}
        result, timing = timed_compute(spec, request["value"])
        return dict(timing, ok=True, result=result)
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def serve():
    out = sys.stdout
    out.write(encode({"ready": True, "pid": os.getpid()}) + "\n")
    out.flush()
    for line in sys.stdin.buffer:
        out.write(encode(answer(line.rstrip(b"\r\n"))) + "\n")
        out.flush()


def main():
    if "--serve" in sys.argv[1:]:
        serve()
        return
    raw = sys.stdin.buffer.read(PROTOCOL_LIMIT + 1)
    sys.stdout.write(encode(answer(raw)))


if __name__ == "__main__":
    main()
