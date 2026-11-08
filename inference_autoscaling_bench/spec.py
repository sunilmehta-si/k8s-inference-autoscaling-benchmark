"""A policy spec is one line: `[label=]policy[:key=value,...]`.

    static-24                          a fixed pool of 24 pods
    hpa-concurrency                    the HPA on requests in the system per pod, every default
    hpa-queue:target=2,down=60         the HPA on waiting requests per pod, target 2, a 60 s scale-down window
    slow=hpa-rps:startup=120           a label, and pods that take 120 s to start

Keys: target, down (scale-down window, s), up_window (s), tolerance, up_pods, up_percent for an HPA; startup
(seconds before a new pod is ready), min (the fewest pods, the standing headroom) and sync (seconds between the
autoscaler's decisions) for any policy, route (`central`, the default: one shared queue; `pod`: each request is
sent to a random ready pod when it arrives and waits in that pod's own queue, as behind a Kubernetes Service), lag
(seconds: the autoscaler acts on the signal as it was that long ago, as when it reads it through Prometheus) and scrape
(seconds: each pod is scraped at that interval at its own offset, a rule evaluated at that interval at its own offset
sums the latest samples, and the autoscaler reads the latest evaluation; not combined with lag).
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Callable

from .policies import SIGNALS, Hpa, Policy, Static
from .sim import SYNC_PERIOD_S, Replica

HPA_KEYS = {"target": float, "down": float, "up_window": float, "tolerance": float, "up_pods": int, "up_percent": float}
HPA_ARGUMENT = {"down": "down_window_s", "up_window": "up_window_s"}


@dataclass(frozen=True)
class Spec:
    label: str
    text: str
    make: Callable[[], Policy]   # a fresh policy: an HPA remembers its recommendations
    replica: Replica
    min_replicas: int | None = None   # overrides the matrix's minimum for this policy
    sync_s: float = SYNC_PERIOD_S
    pod_queues: bool = False
    metrics_lag_s: float = 0.0
    scrape_s: float = 0.0


def parse(text: str, base: Replica = Replica()) -> Spec:
    label, _, body = text.partition("=") if "=" in text.split(":", 1)[0] else ("", "", text)
    kind, _, options = body.partition(":")
    params: dict[str, str] = {}
    for item in filter(None, options.split(",")):
        key, eq, value = item.partition("=")
        if not eq or not value:
            raise ValueError(f"{item!r} in {text!r} is not key=value")
        params[key.strip()] = value.strip()
    replica = base
    minimum = None
    if "min" in params:
        minimum = _number(int, "min", params.pop("min"))
        if minimum < 1:
            raise ValueError("min must be at least 1")
    sync = SYNC_PERIOD_S
    if "sync" in params:
        sync = _number(float, "sync", params.pop("sync"))
        if sync <= 0:
            raise ValueError("sync must be positive")
    pod_queues = False
    if "route" in params:
        route = params.pop("route")
        if route not in ("central", "pod"):
            raise ValueError(f"route must be central or pod, not {route!r}")
        pod_queues = route == "pod"
    lag = 0.0
    if "lag" in params:
        lag = _number(float, "lag", params.pop("lag"))
        if lag < 0:
            raise ValueError("lag cannot be negative")
    scrape = 0.0
    if "scrape" in params:
        scrape = _number(float, "scrape", params.pop("scrape"))
        if scrape <= 0:
            raise ValueError("scrape must be positive")
        if lag:
            raise ValueError("set lag or scrape, not both")
    if "startup" in params:
        replica = replace(base, startup_s=_number(float, "startup", params.pop("startup")))
    label = label or (body if options else kind)
    if kind.startswith("static-"):
        if params:
            raise ValueError(f"a static pool takes no options besides startup, min, sync, route, lag and scrape, not {', '.join(params)}")
        size = _number(int, "pool size", kind[len("static-"):])
        if size < 1:
            raise ValueError("a static pool needs at least one pod")
        return Spec(label, text, lambda: Static(size), replica, minimum, sync, pod_queues, lag, scrape)
    signal = kind[len("hpa-"):] if kind.startswith("hpa-") else ""
    if signal not in SIGNALS:
        raise ValueError(f"unknown policy {kind!r}: use static-N or hpa-<{'|'.join(SIGNALS)}>")
    arguments = {}
    for key, value in params.items():
        if key not in HPA_KEYS:
            raise ValueError(f"unknown option {key!r}; choose from {', '.join(sorted(HPA_KEYS))}, startup, min, sync, route, lag, scrape")
        arguments[HPA_ARGUMENT.get(key, key)] = _number(HPA_KEYS[key], key, value)
    return Spec(label, text, lambda: Hpa(signal, name=label, **arguments), replica, minimum, sync, pod_queues, lag, scrape)


def with_route(text: str, route: str) -> str:
    """The spec `text` with `route=<route>` added and its label unchanged, so a dataset re-run with another route is
    labelled exactly as the original is."""
    label, eq, body = text.partition("=") if "=" in text.split(":", 1)[0] else ("", "", text)
    kind, colon, options = body.partition(":")
    if "route=" in options:
        raise ValueError(f"{text!r} already sets a route")
    joined = f"{kind}:{options + ',' if options else ''}route={route}"
    if label:
        return f"{label}={joined}"
    # An unlabelled spec's label is its own text, which a label cannot hold (it has a colon): it gets the route in it.
    return joined if options else f"{kind}={joined}"


def _number(kind, what, value):
    try:
        return kind(value)
    except ValueError:
        raise ValueError(f"{what} must be a number, not {value!r}") from None
