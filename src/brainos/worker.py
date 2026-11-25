"""Bounded subprocess protocol for catalogue providers; not a hostile-code sandbox."""
import json
import sys

from .contracts import encode
from .providers import compute, specification


def main():
    try:
        raw = sys.stdin.buffer.read(65537)
        if len(raw) > 65536:
            raise ValueError("input exceeds protocol limit")
        request = json.loads(raw)
        spec = specification(request["implementation"])
        if request["artifact"] != spec["artifact"]:
            raise ValueError("artifact digest mismatch")
        result = {"ok": True, "result": compute(spec["implementation"], request["value"])}
    except Exception as exc:
        result = {"ok": False, "error": str(exc)}
    sys.stdout.write(encode(result))


if __name__ == "__main__":
    main()
