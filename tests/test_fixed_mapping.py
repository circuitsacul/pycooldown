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

import pytest
from mock import Mock
from pytest_mock import MockerFixture

from pycooldown.fixed_mapping import FixedCooldown


@pytest.mark.parametrize(["period", "capacity"], [(1, 1), (1, 2), (2, 1)])
def test_init(period: float, capacity: int) -> None:
    mapping = FixedCooldown(capacity, period)
    assert mapping.period == period
    assert mapping.capacity == capacity
    assert len(mapping._old) == 0
    assert len(mapping._cur) == 0


def test_get_bucket() -> None:
    mapping: FixedCooldown[str] = FixedCooldown(1, 1)
    bucket = mapping.get_bucket("test")
    assert bucket.period == 1
    assert bucket.capacity == 1


def test_getitem() -> None:
    mapping: FixedCooldown[str] = FixedCooldown(1, 1)

    # test that a KeyError is raised if the bucket does not exist
    with pytest.raises(KeyError):
        mapping["test"]

    # create a bucket
    bucket = mapping.get_bucket("test")

    # test that the bucket is returned when the key is passed
    assert mapping["test"] is bucket


def test_getitem_moves_bucket() -> None:
    mapping: FixedCooldown[str] = FixedCooldown(1, 1)

    bucket_mock = Mock()
    mapping._old["test"] = bucket_mock
    bucket = mapping.get_bucket("test")

    assert bucket is bucket_mock
    assert "test" not in mapping._old
    assert "test" in mapping._cur


def test_setitem() -> None:
    mapping: FixedCooldown[str] = FixedCooldown(1, 1)

    bucket_mock = Mock()
    mapping["test"] = bucket_mock

    assert "test" in mapping._cur
    assert mapping._cur["test"] is bucket_mock
    assert "test" not in mapping._old


def test_cycle() -> None:
    mapping: FixedCooldown[str] = FixedCooldown(1, 1)

    # create buckets and add them to the mapping
    bucket1 = Mock()
    bucket2 = Mock()
    mapping._old["test1"] = bucket1
    mapping._cur["test2"] = bucket2

    # cycle the mapping
    mapping.last_cycle = 0
    bucket3 = mapping.get_bucket("test3")

    # test that the buckets were moved correctly
    assert mapping._old == {"test2": bucket2}
    assert mapping._cur == {"test3": bucket3}


def test_get_retry_after(mocker: MockerFixture) -> None:
    mapping: FixedCooldown[str] = FixedCooldown(1, 1)

    # test that "get_bucket" is called
    gb_spy = mocker.spy(mapping, "get_bucket")
    mapping.get_retry_after("test")
    gb_spy.assert_called_once_with("test")

    # patch get_bucket, test that retry_after is called and returned
    gb_mock = mocker.patch.object(mapping, "get_bucket")
    bucket_mock = Mock()
    gb_mock.return_value = bucket_mock

    ret = mapping.get_retry_after("test")
    bucket_mock.get_retry_after.assert_called_once_with()
    assert ret is bucket_mock.get_retry_after()


def test_update_ratelimit(mocker: MockerFixture) -> None:
    mapping: FixedCooldown[str] = FixedCooldown(1, 1)

    # test that "get_bucket" is called
    gb_spy = mocker.spy(mapping, "get_bucket")
    mapping.update_ratelimit("test")
    gb_spy.assert_called_once_with("test")

    # patch get_bucket, test that update_ratelimit is called and returned
    gb_mock = mocker.patch.object(mapping, "get_bucket")
    bucket_mock = Mock()
    gb_mock.return_value = bucket_mock

    ret = mapping.update_ratelimit("test")
    bucket_mock.update_ratelimit.assert_called_once_with()
    assert ret is bucket_mock.update_ratelimit()
