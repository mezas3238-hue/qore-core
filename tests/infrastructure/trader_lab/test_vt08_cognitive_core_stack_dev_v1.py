from decimal import Decimal

from qore.infrastructure.trader_lab.vt08_cognitive_core_stack_dev_v1 import (
    EQ_BANK_FRACTION,
    aggressive_policy,
)


def test_core_stack_uses_exact_preexisting_aggressive_policy() -> None:
    policy = aggressive_policy()
    assert policy.name == "aggressive"
    assert policy.ratchets == (
        (Decimal("0.50"), Decimal("0.00")),
        (Decimal("1.00"), Decimal("0.50")),
        (Decimal("1.50"), Decimal("1.00")),
    )


def test_core_stack_eq_bank_is_half() -> None:
    assert EQ_BANK_FRACTION == Decimal("0.50")
