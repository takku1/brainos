"""Execution profiles for the trusted catalogue, behind one adapter.

Profiles differ only in how a verified request reaches `worker.answer`:
  subprocess  fresh interpreter per primitive (isolation/crash testing)
  persistent  one long-lived trusted worker, restarted on timeout or error
  inprocess   direct call; the deadline is checked after completion (no preemption)
Schema checks, protocol bounds, artifact verification, graph lowering,
cancellation and timing are shared, so no profile can skip a check.
"""
import json
import queue
import subprocess
import sys
import threading
import time

from .contracts import PROTOCOL_LIMIT, Cancelled, Refused, encode
from . import graphs, providers, worker

PROFILES = ("subprocess", "persistent", "inprocess")


class _Adapter:
    profile = None

    def __init__(self, registry=None, on_event=None):
        self.registry = registry
        self.on_event = on_event or (lambda kind, **fields: None)

    def compute(self, spec, value, timeout, *, on_start=None, on_result=None, cancelled=None, on_timing=None):
        if cancelled and cancelled():
            raise Cancelled("cancelled before primitive execution")
        if spec.get("kind") == "graph":
            if self.registry is None:
                raise Refused("graph execution requires reference resolution")
            return graphs.execute(spec, value, self.registry.resolve,
                lambda primitive, data, remaining: self.compute(primitive, data, remaining,
                    on_start=on_start, cancelled=cancelled, on_timing=on_timing), timeout,
                on_result=on_result, cancelled=cancelled)
        if on_start:
            on_start(spec)
        providers.check(spec["input"], value)
        started = time.perf_counter_ns()
        request = encode(dict(implementation=spec["implementation"], artifact=spec["artifact"], value=value))
        encoded = time.perf_counter_ns()
        if len(request.encode()) > PROTOCOL_LIMIT:
            raise Refused("worker input exceeds protocol limit")
        raw, timing = self._invoke(request, timeout)
        received = time.perf_counter_ns()
        if len(raw.encode()) > PROTOCOL_LIMIT:
            raise Refused("provider worker failed or exceeded protocol limit")
        message = json.loads(raw)
        if not message.get("ok"):
            raise Refused(message.get("error", "provider failed"))
        providers.check(spec["output"], message["result"])
        finished = time.perf_counter_ns()
        compute_ns = message.get("compute_ns", 0)
        timing = dict(profile=self.profile, provider=spec["id"], compute_ns=compute_ns,
                      serialize_ns=(encoded - started) + (finished - received),
                      transport_ns=max(0, timing["round_trip_ns"] - compute_ns - timing.get("startup_ns", 0)),
                      startup_ns=timing.get("startup_ns", 0), total_ns=finished - started)
        if on_timing:
            on_timing(timing)
        return message["result"]

    def _invoke(self, request, timeout):
        """Deliver a verified request; return (raw reply, {round_trip_ns, startup_ns})."""
        raise NotImplementedError

    def close(self):
        pass


class ProcessRunner(_Adapter):
    """Fresh subprocess per primitive. Interpreter start-up and transport are
    not separable here, so both are reported together as `startup_ns`."""
    profile = "subprocess"

    def _invoke(self, request, timeout):
        started = time.perf_counter_ns()
        try:
            result = subprocess.run([sys.executable, "-m", "brainos.worker"], input=request,
                text=True, encoding="utf-8", capture_output=True, timeout=timeout, check=False)
        except subprocess.TimeoutExpired as exc:
            raise Refused("provider exceeded wall-clock bound") from exc
        round_trip = time.perf_counter_ns() - started
        if result.returncode:
            raise Refused("provider worker failed or exceeded protocol limit")
        compute_ns = json.loads(result.stdout).get("compute_ns", 0) if result.stdout.startswith("{") else 0
        return result.stdout, dict(round_trip_ns=round_trip, startup_ns=max(0, round_trip - compute_ns))


class PersistentRunner(_Adapter):
    """One long-lived trusted worker. Timeout, death or a malformed reply kills
    it; the next call starts a fresh worker. No request is retried silently."""
    profile = "persistent"

    def __init__(self, registry=None, on_event=None):
        super().__init__(registry, on_event)
        self.lock = threading.Lock()
        self.process = None
        self.replies = None
        self.starts = 0

    def _spawn(self):
        started = time.perf_counter_ns()
        process = subprocess.Popen([sys.executable, "-m", "brainos.worker", "--serve"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, encoding="utf-8", bufsize=1)
        replies = queue.Queue()
        def pump(stream=process.stdout):
            for line in stream:
                replies.put(line)
            replies.put(None)
        threading.Thread(target=pump, daemon=True).start()
        try:
            ready = replies.get(timeout=30)
        except queue.Empty:
            ready = None
        if not ready or not json.loads(ready).get("ready"):
            process.kill()
            raise Refused("persistent worker failed to start")
        self.process, self.replies = process, replies
        self.starts += 1
        self.on_event("worker-started", profile=self.profile, pid=process.pid, starts=self.starts)
        return time.perf_counter_ns() - started

    def _kill(self, reason):
        if self.process is not None:
            pid = self.process.pid
            self.process.kill()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pass
            self.process = self.replies = None
            self.on_event("worker-stopped", profile=self.profile, pid=pid, reason=reason)

    def _invoke(self, request, timeout):
        with self.lock:
            startup = 0
            if self.process is None or self.process.poll() is not None:
                if self.process is not None:
                    self._kill("worker exited")
                startup = self._spawn()
            started = time.perf_counter_ns()
            try:
                self.process.stdin.write(request + "\n")
                self.process.stdin.flush()
            except OSError as exc:
                self._kill("request write failed")
                raise Refused("persistent worker failed") from exc
            try:
                reply = self.replies.get(timeout=timeout)
            except queue.Empty as exc:
                self._kill("timeout")
                raise Refused("provider exceeded wall-clock bound") from exc
            if reply is None:
                self._kill("worker exited during request")
                raise Refused("persistent worker failed")
            return reply.rstrip("\n"), dict(round_trip_ns=time.perf_counter_ns() - started + startup,
                                            startup_ns=startup)

    def close(self):
        with self.lock:
            if self.process is not None:
                try:
                    self.process.stdin.close()
                    self.process.wait(timeout=5)
                except (OSError, subprocess.TimeoutExpired):
                    self.process.kill()
                self.process = self.replies = None


class InProcessRunner(_Adapter):
    """Trusted direct call for benchmarking deterministic primitives. It cannot
    preempt: a call that overruns its deadline is refused after it returns."""
    profile = "inprocess"

    def _invoke(self, request, timeout):
        started = time.perf_counter_ns()
        reply = encode(worker.answer(request.encode()))
        round_trip = time.perf_counter_ns() - started
        if round_trip > timeout * 1e9:
            raise Refused("provider exceeded wall-clock bound")
        return reply, dict(round_trip_ns=round_trip, startup_ns=0)


def make_runner(profile, registry=None, on_event=None):
    if profile not in PROFILES:
        raise Refused("unknown execution profile")
    return {"subprocess": ProcessRunner, "persistent": PersistentRunner,
            "inprocess": InProcessRunner}[profile](registry, on_event)
