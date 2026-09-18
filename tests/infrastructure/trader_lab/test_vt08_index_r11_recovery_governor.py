from decimal import Decimal

from qore.infrastructure.trader_lab import vt08_index_r11_recovery_governor as mod


def test_r11_contract() -> None:
    assert mod.MIN_TRADES == 1500
    assert mod.MAX_TRADES == 1600
    assert mod.PRIMARY_PF_GOAL == Decimal("1.50")
    assert mod.PRIMARY_DD_GOAL == Decimal("6")
    assert mod.SECONDARY_PF_GOAL == Decimal("1.30")
    assert mod.SECONDARY_DD_GOAL == Decimal("8")


def test_r11_scheme_space_is_bounded_and_nonzero() -> None:
    schemes = mod._schemes()
    assert schemes
    assert len(schemes) <= 256
    for scheme in schemes:
        assert scheme.aligned_weight > 0
        assert scheme.c2_cap > 0
        assert scheme.short_cap > 0
        assert scheme.defensive_multiplier > 0
        assert scheme.hard_multiplier > 0
        assert scheme.hard_trigger > scheme.loss_trigger


def test_r11_strong_context_can_bypass_defense() -> None:
    assert any(scheme.strong_context_bypass for scheme in mod._schemes())
    assert any(not scheme.strong_context_bypass for scheme in mod._schemes())
