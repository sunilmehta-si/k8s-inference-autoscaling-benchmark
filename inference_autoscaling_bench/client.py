"""Replay a trace against an OpenAI-compatible endpoint, open loop, and time every streamed response.

Open loop means each request is sent at its arrival time whatever happened to the earlier ones, the way real users
arrive: a closed loop that waits for answers would hide exactly the queueing an autoscaler that is too slow causes.
Each request streams, so time to first token (TTFT) is measured where the user feels it: from sending the request to
the first content chunk arriving.

Standard library only. A dispatcher sleeps until each arrival and starts a thread for that request alone, so the
threads alive are the requests in flight, not the requests still to come: a queue of a thousand waiting requests is a
thousand threads, not a pool that runs dry and starts everything late. How late each request actually started is
recorded, so a run whose client fell behind says so instead of passing off its own delay as the cluster's.
"""
from __future__ import annotations

import http.client
import json
import socket
import threading
import time
from dataclasses import asdict, dataclass
from urllib.parse import urlsplit

from .workload import Request

CHAT_PATH = "/v1/chat/completions"
THREAD_STACK_BYTES = 512 * 1024


@dataclass
class Result:
    index: int
    scheduled_s: float            # when the trace says it arrives, after the start
    lateness_s: float             # how much later than that the client actually sent it
    requested_prompt_tokens: int
    requested_output_tokens: int
    status: int                   # HTTP status; 0 means no answer at all (connection error or timeout)
    ttft_s: float | None          # send to first content chunk
    e2e_s: float | None           # send to the end of the stream
    output_chunks: int
    prompt_tokens: int | None = None       # what the server counted, from usage
    completion_tokens: int | None = None
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.status == 200 and self.error is None and self.ttft_s is not None

    def to_dict(self) -> dict:
        return asdict(self)


def prompt_for(tokens: int) -> str:
    """A prompt of `tokens` one-token words: the server counts it back in usage, and the client records both."""
    return " ".join(["a"] * tokens)


def body(request: Request, model: str) -> bytes:
    # min_tokens equal to max_tokens pins the response length: without it the simulator samples a length from a
    # histogram, and the simulation's fixed output size would not be what the cluster serves.
    return json.dumps({
        "model": model, "messages": [{"role": "user", "content": prompt_for(request.prompt_tokens)}],
        "max_tokens": request.output_tokens, "min_tokens": request.output_tokens, "temperature": 0,
        "stream": True, "stream_options": {"include_usage": True},
    }).encode()


def _send(host: str, port: int, base: str, request: Request, model: str, start: float, results: list, timeout: float):
    scheduled = request.arrival
    sent = time.monotonic()
    result = Result(request.index, round(scheduled, 3), round(max(0.0, sent - start - scheduled), 3), request.prompt_tokens,
                    request.output_tokens, 0, None, None, 0)
    results[request.index] = result
    conn = http.client.HTTPConnection(host, port, timeout=timeout)   # a new connection each time: kube-proxy balances per connection
    try:
        conn.request("POST", base + CHAT_PATH, body=body(request, model),
                     headers={"Content-Type": "application/json", "Accept": "text/event-stream"})
        resp = conn.getresponse()
        result.status = resp.status
        if resp.status != 200:
            result.error = resp.read(300).decode(errors="replace").strip() or resp.reason
            result.e2e_s = round(time.monotonic() - sent, 4)
            return
        for raw in resp:
            line = raw.strip()
            if not line.startswith(b"data:"):
                continue
            data = line[5:].strip()
            if data == b"[DONE]":
                break
            chunk = json.loads(data)
            for choice in chunk.get("choices") or []:
                if (choice.get("delta") or {}).get("content"):
                    if result.ttft_s is None:
                        result.ttft_s = round(time.monotonic() - sent, 4)
                    result.output_chunks += 1
            usage = chunk.get("usage")
            if usage:
                result.prompt_tokens = usage.get("prompt_tokens")
                result.completion_tokens = usage.get("completion_tokens")
        result.e2e_s = round(time.monotonic() - sent, 4)
        if result.ttft_s is None:
            result.error = "the stream ended without a content chunk"
    except (OSError, http.client.HTTPException, ValueError, socket.timeout) as exc:
        result.status = 0 if result.status in (0, 200) else result.status
        result.error = f"{type(exc).__name__}: {exc}"[:300]
        result.e2e_s = round(time.monotonic() - sent, 4)
    finally:
        conn.close()


def run(url: str, model: str, trace: list[Request], timeout: float = 600.0, lead_s: float = 1.0) -> list[Result]:
    """Send every request at its arrival time and return the results in trace order."""
    parts = urlsplit(url)
    if parts.scheme != "http" or not parts.hostname:
        raise ValueError(f"endpoint must be an http URL, got {url!r}")
    host, port, base = parts.hostname, parts.port or 80, parts.path.rstrip("/")
    results: list[Result | None] = [None] * len(trace)
    start = time.monotonic() + lead_s
    old_stack = threading.stack_size()
    threading.stack_size(THREAD_STACK_BYTES)
    threads: list[threading.Thread] = []
    try:
        for request in trace:
            delay = start + request.arrival - time.monotonic()
            if delay > 0:
                time.sleep(delay)
            thread = threading.Thread(target=_send, args=(host, port, base, request, model, start, results, timeout), daemon=True)
            thread.start()
            threads.append(thread)
        for thread in threads:
            thread.join()
    finally:
        threading.stack_size(old_stack)
    missing = [i for i, r in enumerate(results) if r is None]
    if missing:
        raise RuntimeError(f"{len(missing)} requests never started a send, the first is {missing[0]}")
    return results  # type: ignore[return-value]
