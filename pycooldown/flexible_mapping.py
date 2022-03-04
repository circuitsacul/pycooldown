# MIT License
#
# Copyright (c) 2022 TrigonDev
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from __future__ import annotations

from time import time
from typing import Generic, TypeVar

from .sliding_window import SlidingWindow

_K = TypeVar("_K")


class FlexibleCooldown(Generic[_K]):
    """A cooldown mapping where each key can have a different rate and capacity.

    Args:
        max_period (float): The maximum value for a cooldown. The smaller this
        is, the less memory the mapping will use.
    """

    def __init__(self, max_period: float) -> None:
        self.max_period = max_period

        self._old: dict[_K, SlidingWindow] = {}
        self._cur: dict[_K, SlidingWindow] = {}

        self.last_cycle = time()

    def __getitem__(self, key: _K) -> SlidingWindow:
        if v := self._old.pop(key, None):
            self._cur[key] = v
        return self._cur[key]

    def __setitem__(self, key: _K, value: SlidingWindow) -> None:
        self._cur[key] = value

    def get_bucket(
        self, key: _K, period: float, capacity: float
    ) -> SlidingWindow:
        """Get or create a cooldown for a key.

        Args:
            key (Any): The key for the cooldown.
            period (float): The timespan to use for the cooldown.
            capacity (float): The capacity to use for the cooldown.

        Raises:
            RuntimeError: You specified a period greater than max_period.
            RuntimeError: You specified a period or capcity that didn't match
            the existing cooldown's period or capacity.

        Returns:
            SlidingWindow: The cooldown for this key.
        """

        if period > self.max_period:
            raise RuntimeError("The period must be less than max_period.")

        now = time()
        if now > self.last_cycle + self.max_period:
            self.last_cycle = now

            self._old.clear()
            cur = self._cur
            self._cur = self._old
            self._old = cur

        try:
            b = self[key]
            if b.capacity != capacity or b.period != period:
                raise RuntimeError(
                    "Mismatch capacity or period. Each key can only have one "
                    "capacity value."
                )
        except KeyError:
            b = SlidingWindow(period, capacity)
            self._cur[key] = b

        return b

    def get_retry_after(
        self, key: _K, period: float, capacity: float
    ) -> float:
        """Get the current retry-after without triggering the cooldown.

        Args:
            key (Any): The key for the cooldown.
            period (float): The period for the cooldown.
            capacity (float): The capacity for the cooldown.

        Returns:
            float: The current retry-after in seconds.
        """

        return self.get_bucket(key, period, capacity).get_retry_after()

    def update_rate_limit(
        self, key: _K, period: float, capacity: float
    ) -> float | None:
        """Trigger the cooldown if possible, otherwise return the retry-after.

        Args:
            key (Any): The key for the cooldown.
            period (float): The period for the cooldown.
            capacity (float): The capacity for the cooldown.

        Returns:
            float | None: The retry-after in seconds, if any, else None.
        """

        return self.get_bucket(key, period, capacity).update_rate_limit()
