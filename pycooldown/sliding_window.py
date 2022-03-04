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


class SlidingWindow:
    """A sliding window implementation, based on discord.py's Cooldown class.

    Args:
        period (float): The period for the sliding window.
        capacity (float): The capacity for the sliding window.
    """

    # NOTE: This sliding window implementation was copied from the Cooldown
    # class in discord.py.

    __slots__ = ("capacity", "period", "_window", "_tokens", "_last")

    def __init__(self, period: float, capacity: float) -> None:
        self.capacity: int = int(capacity)
        self.period: float = float(period)
        self._window: float = 0.0
        self._tokens: int = self.capacity
        self._last: float = 0.0

    def get_tokens(self, current: float | None = None) -> int:
        if not current:
            current = time()

        tokens = self._tokens

        if current > self._window + self.period:
            tokens = self.capacity
        return tokens

    def get_retry_after(self) -> float:
        """Get the retry-after without triggering the cooldown.

        Args:
            current (float | None, optional): The current time. Defaults to
            None.

        Returns:
            float: The retry-after, in seconds.
        """

        current = time()
        tokens = self.get_tokens(current)

        if tokens == 0:
            return self.period - (current - self._window)

        return 0.0

    def update_rate_limit(self) -> float | None:
        """Trigger the cooldown if possible, otherwise return the retry-after.

        Args:
            current (float | None, optional): The current time. Defaults to
            None.

        Returns:
            float | None: The retry-after, if any, else None.
        """

        current = time()
        self._last = current

        self._tokens = self.get_tokens(current)

        # first token used means that we start a new rate limit window
        if self._tokens == self.capacity:
            self._window = current

        # check if we are rate limited
        if self._tokens == 0:
            return self.period - (current - self._window)

        # we're not so decrement our tokens
        self._tokens -= 1
        return None

    def reset(self) -> None:
        """Reset the cooldown."""

        self._tokens = self.capacity
        self._last = 0.0
