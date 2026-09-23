from decimal import Decimal

from qore.infrastructure.trader_lab.vt08_cognitive_cibo_stop_protection_v1 import (
    _stop_price,
)
from qore.infrastructure.trader_lab.vt08_index_c2_r1_cibo_stop_protection import (
    STOP_POLICIES,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide


def test_transfer_uses_exact_preexisting_vt08_cibo_policy_names() -> None:
    assert tuple(policy.name for policy in STOP_POLICIES) == (
        "off",
        "soft",
        "be050-lock050-at100",
        "aggressive",
    )


def test_stop_price_can_only_move_toward_favorable_direction() -> None:
    entry = Decimal("100")
    risk = Decimal("10")
    assert _stop_price(
        side=DemoTradingSetupSide.LONG,
        entry=entry,
        risk=risk,
        stop_r=Decimal("-1"),
    ) == Decimal("90")
    assert _stop_price(
        side=DemoTradingSetupSide.LONG,
        entry=entry,
        risk=risk,
        stop_r=Decimal("0.5"),
    ) == Decimal("105")
    assert _stop_price(
        side=DemoTradingSetupSide.SHORT,
        entry=entry,
        risk=risk,
        stop_r=Decimal("-1"),
    ) == Decimal("110")
    assert _stop_price(
        side=DemoTradingSetupSide.SHORT,
        entry=entry,
        risk=risk,
        stop_r=Decimal("0.5"),
    ) == Decimal("95")


def test_policy_ratchets_are_monotonic() -> None:
    for policy in STOP_POLICIES:
        triggers = tuple(trigger for trigger, _ in policy.ratchets)
        locks = tuple(lock for _, lock in policy.ratchets)
        assert triggers == tuple(sorted(triggers))
        assert locks == tuple(sorted(locks))
