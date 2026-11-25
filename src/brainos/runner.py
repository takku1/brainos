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


class ExternalDispatcher:
    """Spawn and supervise external adapter processes (Doc 02 section 2.12).

    One long-lived process per provider id, restarted on timeout, death or
    malformed reply — the same supervision as a persistent worker, with no
    model dependencies in the kernel: commands are operator configuration,
    and every reply is verified against the pinned provider record before
    its output is trusted.
    """

    def __init__(self, commands, on_event=None):
        self.commands = dict(commands)
        self.on_event = on_event or (lambda kind, **fields: None)
        self.lock = threading.Lock()
        self.processes = {}
        self.replies = {}

    def _spawn(self, provider, implementation):
        if implementation not in self.commands:
            raise Refused(f"no external adapter configured for {implementation!r}")
        started = time.perf_counter_ns()
        try:
            process = subprocess.Popen(self.commands[implementation], stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                        text=True, encoding="utf-8", bufsize=1)
        except OSError as exc:
            raise Refused(f"external adapter failed to start: {exc}")
        replies = queue.Queue()
        def pump(stream=process.stdout):
            for line in stream:
                replies.put(line)
            replies.put(None)
        threading.Thread(target=pump, daemon=True).start()
        try:
            ready = replies.get(timeout=30)
            ready = json.loads(ready) if ready else None
        except (queue.Empty, ValueError):
            ready = None
        if not ready or not ready.get("ready"):
            process.kill()
            raise Refused("external adapter failed to start")
        self.on_event("worker-started", profile="external", provider=provider,
                      pid=process.pid, starts=1)
        self.processes[provider] = process
        self.replies[provider] = replies
        return time.perf_counter_ns() - started

    def _kill(self, provider, reason):
        process = self.processes.pop(provider, None)
        self.replies.pop(provider, None)
        if process is not None:
            if process.poll() is None:
                process.kill()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pass
            self.on_event("worker-stopped", profile="external", provider=provider, reason=reason)

    def invoke(self, spec, request, timeout):
        provider = spec["id"]
        with self.lock:
            process, replies = self.processes.get(provider), self.replies.get(provider)
            if process is None or process.poll() is not None:
                if process is not None:
                    self._kill(provider, "adapter exited")
                startup = self._spawn(provider, spec["implementation"])
                process, replies = self.processes[provider], self.replies[provider]
            else:
                startup = 0
            started = time.perf_counter_ns()
            try:
                process.stdin.write(request + "\n")
                process.stdin.flush()
            except OSError as exc:
                self._kill(provider, "request write failed")
                raise Refused(f"external adapter failed: {exc}")
            try:
                reply = replies.get(timeout=timeout)
            except queue.Empty:
                self._kill(provider, "timeout")
                raise Refused("external provider exceeded wall-clock bound")
            if reply is None:
                self._kill(provider, "adapter exited during request")
                raise Refused("external adapter failed")
            return reply.rstrip("\n"), dict(round_trip_ns=time.perf_counter_ns() - started + startup,
                                            startup_ns=startup)

    def close(self):
        with self.lock:
            for provider in list(self.processes):
                self._kill(provider, "close")


class _Adapter:
    profile = None

    def __init__(self, registry=None, on_event=None, external=None):
        self.registry = registry
        self.on_event = on_event or (lambda kind, **fields: None)
        self.external = external

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
        if spec.get("kind") == "external":
            return self._compute_external(spec, value, timeout, on_start=on_start,
                                          cancelled=cancelled, on_timing=on_timing)
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
                      startup_ns=timing.get("startup_ns", 0), total_ns=finished - started,
                      prepare_ns=message.get("prepare_ns", 0), answer_ns=message.get("answer_ns", compute_ns),
                      cache_hit=message.get("cache_hit"), state_bytes=message.get("state_bytes", 0))
        if on_timing:
            on_timing(timing)
        return message["result"]

    def _compute_external(self, spec, value, timeout, *, on_start=None, cancelled=None,
                          on_timing=None):
        """One external provider call: verified request, verified reply, both timings kept."""
        if self.external is None:
            raise Refused("no external adapter launcher configured")
        if cancelled and cancelled():
            raise Cancelled("cancelled before external execution")
        if on_start:
            on_start(spec)
        providers.check(spec["input"], value)
        started = time.perf_counter_ns()
        request = encode(dict(implementation=spec["implementation"], artifact=spec["artifact"],
                              value=value, sampling=spec.get("sampling", {})))
        encoded = time.perf_counter_ns()
        if len(request.encode()) > PROTOCOL_LIMIT:
            raise Refused("external request exceeds protocol limit")
        raw, timing = self.external.invoke(spec, request, timeout)
        received = time.perf_counter_ns()
        if len(raw.encode()) > PROTOCOL_LIMIT:
            raise Refused("external adapter failed or exceeded protocol limit")
        try:
            message = json.loads(raw)
        except ValueError:
            self.external._kill(spec["id"], "malformed reply")
            raise Refused("external adapter returned malformed reply")
        if not message.get("ok"):
            raise Refused(message.get("error", "external provider failed"))
        if message.get("artifact") != spec["artifact"]:
            raise Refused("external adapter reply carries an unexpected artifact digest")
        providers.check(spec["output"], message["result"])
        finished = time.perf_counter_ns()
        compute_ns = message.get("compute_ns", 0)
        if type(compute_ns) is not int or compute_ns < 0:
            raise Refused("external adapter reported unusable timing")
        timing = dict(profile="external", provider=spec["id"], compute_ns=compute_ns,
                      serialize_ns=(encoded - started) + (finished - received),
                      transport_ns=max(0, timing["round_trip_ns"] - compute_ns - timing.get("startup_ns", 0)),
                      startup_ns=timing.get("startup_ns", 0), total_ns=finished - started,
                      adapter_compute_ns=compute_ns)
        if on_timing:
            on_timing(timing)
        return message["result"]

    def _invoke(self, request, timeout):
        """Deliver a verified request; return (raw reply, {round_trip_ns, startup_ns})."""
        raise NotImplementedError

    def clear_prepared(self):
        """Drop cached prepared structures (measurement control; never changes results)."""
        spec = providers.specification("sum")
        request = encode(dict(implementation="sum", artifact=spec["artifact"], value=[], control="clear-prepared"))
        self._invoke(request, 10)

    def close(self):
        if self.external is not None:
            self.external.close()


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

    def __init__(self, registry=None, on_event=None, external=None):
        super().__init__(registry, on_event, external)
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
        super().close()


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


def make_runner(profile, registry=None, on_event=None, external=None):
    if profile not in PROFILES:
        raise Refused("unknown execution profile")
    return {"subprocess": ProcessRunner, "persistent": PersistentRunner,
            "inprocess": InProcessRunner}[profile](registry, on_event, external)
