"""A forecast of the arrival rate a little ahead, for a policy that scales before the load arrives.

`Holt` is Holt's linear trend method, the simplest forecaster that can see a ramp coming: it keeps a smoothed level of
the series and a smoothed trend (change per second), and forecasts `level + trend * h` for `h` seconds ahead, never below 0. `alpha`
weighs each new observation against the level's own projection; `beta` weighs each new change of level against the
trend so far. Both are between 0 and 1: near 1 follows the latest observation, near 0 holds on to the past.
"""
from __future__ import annotations


class Holt:
    def __init__(self, alpha: float = 0.5, beta: float = 0.3):
        if not 0 < alpha <= 1:
            raise ValueError(f"alpha must be above 0 and at most 1, not {alpha:g}")
        if not 0 <= beta <= 1:
            raise ValueError(f"beta must be between 0 and 1, not {beta:g}")
        self.alpha, self.beta = alpha, beta
        self.level: float | None = None
        self.trend = 0.0   # change of the level per second
        self.at: float | None = None

    def update(self, t: float, value: float) -> None:
        """Take the observation `value` made at second `t`."""
        if self.level is None:
            self.level, self.at = value, t
            return
        dt = t - self.at
        if dt <= 0:
            raise ValueError(f"observations must move forward in time: {t:g} s after {self.at:g} s")
        previous = self.level
        self.level = self.alpha * value + (1 - self.alpha) * (previous + self.trend * dt)
        self.trend = self.beta * (self.level - previous) / dt + (1 - self.beta) * self.trend
        self.at = t

    def forecast(self, h: float) -> float:
        """The value forecast `h` seconds after the latest observation (0 before any)."""
        if h < 0:
            raise ValueError("a forecast looks ahead: h cannot be negative")
        if self.level is None:
            return 0.0
        return max(0.0, self.level + self.trend * h)   # a falling series ends at nothing, never below
