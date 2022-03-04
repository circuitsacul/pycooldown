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

# NOTE: 95% of this code is originally from discord.py
# (discord/ext/commands/cooldowns.py).

from __future__ import annotations

import asyncio
import time
from collections import deque
from typing import Any, Deque, Dict, Generic, Optional, TypeVar

from .exceptions import MaxConcurrencyReached

__all__ = ("Cooldown", "CooldownMapping", "MaxConcurrency")

_KEY = TypeVar("_KEY")


class Cooldown:
    """Represents a cooldown.
    Attributes
    -----------
    rate: :class:`int`
        The total number of tokens available per :attr:`per` seconds.
    per: :class:`float`
        The length of the cooldown period in seconds.
    """

    __slots__ = ("rate", "per", "_window", "_tokens", "_last")

    def __init__(self, rate: float, per: float) -> None:
        self.rate: int = int(rate)
        self.per: float = float(per)
        self._window: float = 0.0
        self._tokens: int = self.rate
        self._last: float = 0.0

    def get_tokens(self, current: Optional[float] = None) -> int:
        """Returns the number of available tokens before rate limiting is
        applied.

        Parameters
        ------------
        current: Optional[:class:`float`]
            The time in seconds since Unix epoch to calculate tokens at.
            If not supplied then :func:`time.time()` is used.
        Returns
        --------
        :class:`int`
            The number of tokens available before the cooldown is to be
            applied.
        """

        if not current:
            current = time.time()

        tokens = self._tokens

        if current > self._window + self.per:
            tokens = self.rate
        return tokens

    def get_retry_after(self, current: Optional[float] = None) -> float:
        """Returns the time in seconds until the cooldown will be reset.
        Parameters
        -------------
        current: Optional[:class:`float`]
            The current time in seconds since Unix epoch.
            If not supplied, then :func:`time.time()` is used.
        Returns
        -------
        :class:`float`
            The number of seconds to wait before this cooldown will be reset.
        """

        current = current or time.time()
        tokens = self.get_tokens(current)

        if tokens == 0:
            return self.per - (current - self._window)

        return 0.0

    def update_rate_limit(
        self, current: Optional[float] = None
    ) -> Optional[float]:
        """Updates the cooldown rate limit.
        Parameters
        -------------
        current: Optional[:class:`float`]
            The time in seconds since Unix epoch to update the rate limit at.
            If not supplied, then :func:`time.time()` is used.
        Returns
        -------
        Optional[:class:`float`]
            The retry-after time in seconds if rate limited.
        """

        current = current or time.time()
        self._last = current

        self._tokens = self.get_tokens(current)

        # first token used means that we start a new rate limit window
        if self._tokens == self.rate:
            self._window = current

        # check if we are rate limited
        if self._tokens == 0:
            return self.per - (current - self._window)

        # we're not so decrement our tokens
        self._tokens -= 1

        return None

    def reset(self) -> None:
        """Reset the cooldown to its initial state."""

        self._tokens = self.rate
        self._last = 0.0

    def copy(self) -> Cooldown:
        """Creates a copy of this cooldown.
        Returns
        --------
        :class:`Cooldown`
            A new instance of this cooldown.
        """

        return Cooldown(self.rate, self.per)

    def __repr__(self) -> str:
        return (
            f"<Cooldown rate: {self.rate} per: {self.per} window: "
            f"{self._window} tokens: {self._tokens}>"
        )


class CooldownMapping(Generic[_KEY]):
    def __init__(self, rate: float | None, per: float | None) -> None:
        self.rate = rate
        self.per = per
        self._cooldowns: dict[_KEY, Cooldown] = {}

    def copy(self) -> CooldownMapping[_KEY]:
        ret: CooldownMapping[_KEY] = CooldownMapping(self.rate, self.per)
        ret._cooldowns = self._cooldowns.copy()
        return ret

    def _remove_expired_cooldowns(
        self, current: Optional[float] = None
    ) -> None:
        # we want to delete all cooldown objects that haven't been used
        # in a cooldown window. e.g. if we have a cooldown of 60s and it has
        # not been used in 60s then that key should be deleted
        current = current if current is not None else time.time()
        dead_keys = [
            k for k, v in self._cooldowns.items() if current > v._last + v.per
        ]
        for k in dead_keys:
            del self._cooldowns[k]

    def create_bucket(
        self, rate: float | None = None, per: float | None = None
    ) -> Cooldown:
        rate = rate or self.rate
        per = per or self.per

        if rate is None:
            raise TypeError(
                "You must specify a rate, either in __init__ or in the call."
            )
        if per is None:
            raise TypeError(
                "You must specify a per, either in __init__ or in the call."
            )

        return Cooldown(rate, per)

    def get_bucket(
        self,
        key: _KEY,
        current: Optional[float] = None,
        rate: float | None = None,
        per: float | None = None,
    ) -> Cooldown:
        self._remove_expired_cooldowns(current)
        if key not in self._cooldowns:
            bucket = self.create_bucket(rate, per)
            self._cooldowns[key] = bucket
        else:
            bucket = self._cooldowns[key]

        return bucket

    def update_rate_limit(
        self,
        key: _KEY,
        current: Optional[float] = None,
        rate: float | None = None,
        per: float | None = None,
    ) -> Optional[float]:
        bucket = self.get_bucket(key, current, rate, per)
        return bucket.update_rate_limit(current)


class _Semaphore:
    """This class is a version of a semaphore.
    If you're wondering why asyncio.Semaphore isn't being used,
    it's because it doesn't expose the internal value. This internal
    value is necessary because I need to support both `wait=True` and
    `wait=False`.
    An asyncio.Queue could have been used to do this as well -- but it is
    not as inefficient since internally that uses two queues and is a bit
    overkill for what is basically a counter.
    """

    __slots__ = ("value", "loop", "_waiters")

    def __init__(self, number: int) -> None:
        self.value: int = number
        self.loop: asyncio.AbstractEventLoop = asyncio.get_event_loop()
        self._waiters: Deque[asyncio.Future[None]] = deque()

    def __repr__(self) -> str:
        return f"<_Semaphore value={self.value} waiters={len(self._waiters)}>"

    def locked(self) -> bool:
        return self.value == 0

    def is_active(self) -> bool:
        return len(self._waiters) > 0

    def wake_up(self) -> None:
        while self._waiters:
            future = self._waiters.popleft()
            if not future.done():
                future.set_result(None)
                return

    async def acquire(self, *, wait: bool = False) -> bool:
        if not wait and self.value <= 0:
            # signal that we're not acquiring
            return False

        while self.value <= 0:
            future = self.loop.create_future()
            self._waiters.append(future)
            try:
                await future
            except Exception:
                future.cancel()
                if self.value > 0 and not future.cancelled():
                    self.wake_up()
                raise

        self.value -= 1
        return True

    def release(self) -> None:
        self.value += 1
        self.wake_up()


class MaxConcurrency(Generic[_KEY]):
    __slots__ = ("number", "per", "wait", "_mapping")

    def __init__(self, number: int, *, wait: bool) -> None:
        self._mapping: Dict[Any, _Semaphore] = {}
        self.number: int = number
        self.wait: bool = wait

        if number <= 0:
            raise ValueError("max_concurrency 'number' cannot be less than 1")

    def __repr__(self) -> str:
        return f"<MaxConcurrency number={self.number} wait={self.wait}>"

    async def acquire(self, key: _KEY) -> None:
        try:
            sem = self._mapping[key]
        except KeyError:
            self._mapping[key] = sem = _Semaphore(self.number)

        acquired = await sem.acquire(wait=self.wait)
        if not acquired:
            raise MaxConcurrencyReached(self)

    async def release(self, key: _KEY) -> None:
        # Technically there's no reason for this function to be async
        # But it might be more useful in the future
        try:
            sem = self._mapping[key]
        except KeyError:
            # ...? peculiar
            return
        else:
            sem.release()

        if sem.value >= self.number and not sem.is_active():
            del self._mapping[key]
