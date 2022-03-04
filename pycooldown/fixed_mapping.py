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


class FixedCooldown(Generic[_K]):
    """A cooldown mapping where each key has an identical rate and period.

    Args:
        period (float): The timespan of the cooldown.
        capacity (float): The maximum number of units per timespan.
    """

    def __init__(self, period: float, capacity: float) -> None:
        self.period = period
        self.capacity = capacity

        self._old: dict[_K, SlidingWindow] = {}
        self._cur: dict[_K, SlidingWindow] = {}

        self.last_cycle = time()

    def __getitem__(self, key: _K) -> SlidingWindow:
        if v := self._old.pop(key, None):
            self._cur[key] = v
        return self._cur[key]

    def __setitem__(self, key: _K, value: SlidingWindow) -> None:
        self._cur[key] = value

    def get_bucket(self, key: _K) -> SlidingWindow:
        """Get or create a cooldown window, whilst removing expired ones.

        Args:
            key (Any): The key for the cooldown.

        Returns:
            SlidingWindow: The sliding window for the cooldown.
        """

        now = time()
        if now > self.last_cycle + self.period:
            self.last_cycle = now

            self._old.clear()
            cur = self._cur
            self._cur = self._old
            self._old = cur

        try:
            return self[key]
        except KeyError:
            b = SlidingWindow(self.period, self.capacity)
            self._cur[key] = b
            return b

    def get_retry_after(self, key: _K) -> float:
        """Get the current retry-after, without triggering the cooldown.

        Args:
            key (Any): The key for the cooldown.

        Returns:
            float: How many seconds before the cooldown can be triggered again.
        """

        return self.get_bucket(key).get_retry_after()

    def update_rate_limit(self, key: _K) -> float | None:
        """Trigger the cooldown. If the cooldown cannot be triggered, return
        the retry-after.

        Args:
            key (Any): The key for the cooldown.

        Returns:
            float | None: The retry-after in seconds, if any, else None.
        """

        return self.get_bucket(key).update_rate_limit()
