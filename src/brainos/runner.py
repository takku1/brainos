"""Time-bounded subprocess adapter for the fixed provider catalogue."""
import json
import subprocess
import sys
from .contracts import Cancelled, Refused, encode
from . import providers
from . import graphs


class ProcessRunner:
    def __init__(self, registry=None):
        self.registry = registry

    def compute(self, spec, value, timeout, *, on_start=None, on_result=None, cancelled=None):
        if cancelled and cancelled():
            raise Cancelled("cancelled before primitive execution")
        if spec.get("kind") == "graph":
            if self.registry is None:
                raise Refused("graph execution requires reference resolution")
            return graphs.execute(spec, value, self.registry.resolve,
                lambda primitive, data, remaining: self.compute(primitive, data, remaining,
                    on_start=on_start, cancelled=cancelled), timeout,
                on_result=on_result, cancelled=cancelled)
        if on_start:
            on_start(spec)
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
