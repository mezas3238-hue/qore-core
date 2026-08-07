from dataclasses import dataclass, replace

from qore.kernel.value_object import ValueObject


@dataclass(frozen=True, slots=True)
class Money(ValueObject):
    amount: int
    currency: str


def test_value_object_immutability_by_replacement() -> None:
    money = Money(100, "USD")
    altered = replace(money, amount=200)
    assert money.amount == 100
    assert altered.amount == 200
    assert altered is not money


def test_value_object_equality_and_hash_by_values() -> None:
    a = Money(100, "EUR")
    b = Money(100, "EUR")
    c = Money(200, "EUR")
    assert a == b
    assert a != c
    assert hash(a) == hash(b)


def test_value_object_not_equal_to_other_type() -> None:
    assert Money(100, "USD") != (100, "USD")


def test_value_object_inmutability_is_shallow() -> None:
    @dataclass(frozen=True, slots=True)
    class MutableField(ValueObject):
        items: list[int]

    value = MutableField([1, 2, 3])
    value.items.append(4)
    assert value.items == [1, 2, 3, 4]
