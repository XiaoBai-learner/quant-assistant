"""Serial rate limiter for fragile data sources."""
from __future__ import annotations

import random
import time
from typing import Callable, Optional, Tuple, Union


Jitter = Union[float, Tuple[float, float]]


class SerialRateLimiter:
    """Ensure calls are spaced by at least min_interval plus jitter."""

    def __init__(
        self,
        min_interval: float = 1.0,
        jitter: Jitter = 0.0,
        monotonic: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.min_interval = min_interval
        self.jitter = jitter
        self.monotonic = monotonic
        self.sleep = sleep
        self._last_call: Optional[float] = None

    def wait(self) -> None:
        """Sleep until the next request is allowed."""
        now = self.monotonic()
        if self._last_call is not None:
            delay = self.min_interval - (now - self._last_call)
            if delay > 0:
                self.sleep(delay + self._jitter())
        self._last_call = self.monotonic()

    def _jitter(self) -> float:
        if isinstance(self.jitter, tuple):
            return random.uniform(self.jitter[0], self.jitter[1])
        return float(self.jitter)
