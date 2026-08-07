from dataclasses import replace

import pytest

from qore.kernel.errors import KernelError
from qore.kernel.result import Failure, Result, Success


def test_success_creation_and_access() -> None:
    success = Success(value=42)
    assert success.value == 42


def test_failure_creation() -> None:
    failure = Failure(error=KernelError("boom"))
    assert isinstance(failure.error, KernelError)


def test_result_immutability_by_replacement() -> None:
    success = Success(value=1)
    altered = replace(success, value=3)
    assert success.value == 1
    assert altered.value == 3
    assert altered is not success


def test_result_equality() -> None:
    assert Success(value=[1, 2]) == Success(value=[1, 2])
    error = KernelError("err")
    assert Failure(error=error) == Failure(error=error)


def test_result_type_alias_works_with_match() -> None:
    result: Result[int, KernelError] = Success(100)
    match result:
        case Success(value=value):
            assert value == 100
        case Failure():
            pytest.fail("Should be success")


def test_success_and_failure_support_isinstance() -> None:
    assert isinstance(Success(value="ok"), Success)
    assert isinstance(Failure(error=KernelError()), Failure)
