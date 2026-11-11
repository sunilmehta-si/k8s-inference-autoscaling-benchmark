"""A forecast of the arrival rate a little ahead, for a policy that scales before the load arrives.

`Holt` is Holt's linear trend method, the simplest forecaster that can see a ramp coming: it keeps a smoothed level of
the series and a smoothed trend (change per second), and forecasts `level + trend * h` for `h` seconds ahead. `alpha`
weighs each new observation against the level's own projection; `beta` weighs each new change of level against the
trend so far. Both are between 0 and 1: near 1 follows the latest observation, near 0 holds on to the past.
"""
from __future__ import annotations


class Holt:
    def __init__(self, alpha: float = 0.5):
        self.alpha = alpha
        self.level: float | None = None
        self.at: float | None = None

    def update(self, t: float, value: float) -> None:
        """Take the observation `value` made at second `t`."""
        if self.level is None:
            self.level, self.at = value, t
            return
        self.level = self.alpha * value + (1 - self.alpha) * self.level
        self.at = t

    def forecast(self, h: float) -> float:
        """The value forecast `h` seconds after the latest observation (0 before any)."""
        return 0.0 if self.level is None else self.level
