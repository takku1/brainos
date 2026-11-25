"""Time-bounded subprocess adapter for the fixed provider catalogue."""
import json
import subprocess
import sys
from .contracts import Refused, encode
from . import providers


class ProcessRunner:
    def compute(self, spec, value, timeout):
        providers.check(spec["input"], value)
        request = encode(dict(implementation=spec["implementation"], artifact=spec["artifact"], value=value))
        if len(request.encode()) > 65536:
            raise Refused("worker input exceeds protocol limit")
        try:
            result = subprocess.run([sys.executable, "-m", "brainos.worker"], input=request,
                text=True, encoding="utf-8", capture_output=True, timeout=timeout, check=False)
        except subprocess.TimeoutExpired as exc:
            raise Refused("provider exceeded wall-clock bound") from exc
        if result.returncode or len(result.stdout.encode()) > 65536:
            raise Refused("provider worker failed or exceeded protocol limit")
        message = json.loads(result.stdout)
        if not message.get("ok"):
            raise Refused(message.get("error", "provider failed"))
        providers.check(spec["output"], message["result"])
        return message["result"]
