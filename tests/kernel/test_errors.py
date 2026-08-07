import pytest

from qore.kernel.errors import DomainError, InfrastructureError, KernelError, ValidationError


def test_error_hierarchy() -> None:
    assert issubclass(KernelError, Exception)
    assert issubclass(DomainError, KernelError)
    assert issubclass(ValidationError, DomainError)
    assert issubclass(InfrastructureError, KernelError)


def test_error_hierarchy_can_be_raised_and_caught() -> None:
    with pytest.raises(DomainError):
        raise ValidationError("bad value")
    with pytest.raises(KernelError):
        raise InfrastructureError("timeout")
