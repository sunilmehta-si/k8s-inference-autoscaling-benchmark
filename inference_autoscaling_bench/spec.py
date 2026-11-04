"""A policy spec is one line: `[label=]policy[:key=value,...]`.

    static-24                          a fixed pool of 24 pods
    hpa-concurrency                    the HPA on requests in the system per pod, every default
    hpa-queue:target=2,down=60         the HPA on waiting requests per pod, target 2, a 60 s scale-down window
    slow=hpa-rps:startup=120           a label, and pods that take 120 s to start

Keys: target, down (scale-down window, s), up_window (s), tolerance, up_pods, up_percent for an HPA; startup
(seconds before a new pod is ready) and min (the fewest pods, the standing headroom) for any policy.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Callable

from .policies import SIGNALS, Hpa, Policy, Static
from .sim import Replica

HPA_KEYS = {"target": float, "down": float, "up_window": float, "tolerance": float, "up_pods": int, "up_percent": float}
HPA_ARGUMENT = {"down": "down_window_s", "up_window": "up_window_s"}


@dataclass(frozen=True)
class Spec:
    label: str
    text: str
    make: Callable[[], Policy]   # a fresh policy: an HPA remembers its recommendations
    replica: Replica
    min_replicas: int | None = None   # overrides the matrix's minimum for this policy


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
    if "startup" in params:
        replica = replace(base, startup_s=_number(float, "startup", params.pop("startup")))
    label = label or (body if options else kind)
    if kind.startswith("static-"):
        if params:
            raise ValueError(f"a static pool takes no options besides startup and min, not {', '.join(params)}")
        size = _number(int, "pool size", kind[len("static-"):])
        if size < 1:
            raise ValueError("a static pool needs at least one pod")
        return Spec(label, text, lambda: Static(size), replica, minimum)
    signal = kind[len("hpa-"):] if kind.startswith("hpa-") else ""
    if signal not in SIGNALS:
        raise ValueError(f"unknown policy {kind!r}: use static-N or hpa-<{'|'.join(SIGNALS)}>")
    arguments = {}
    for key, value in params.items():
        if key not in HPA_KEYS:
            raise ValueError(f"unknown option {key!r}; choose from {', '.join(sorted(HPA_KEYS))}, startup, min")
        arguments[HPA_ARGUMENT.get(key, key)] = _number(HPA_KEYS[key], key, value)
    return Spec(label, text, lambda: Hpa(signal, name=label, **arguments), replica, minimum)


def _number(kind, what, value):
    try:
        return kind(value)
    except ValueError:
        raise ValueError(f"{what} must be a number, not {value!r}") from None
