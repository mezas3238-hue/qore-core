from decimal import Decimal

from qore.infrastructure.trader_lab import vt08_index_r13_rolling_drawdown_governor as mod


def test_r13_contract() -> None:
    assert mod.MIN_TRADES == 1500
    assert mod.MAX_TRADES == 1600
    assert mod.PRIMARY_PF_GOAL == Decimal("1.50")
    assert mod.PRIMARY_DD_GOAL == Decimal("6")
    assert mod.SECONDARY_PF_GOAL == Decimal("1.30")
    assert mod.SECONDARY_DD_GOAL == Decimal("8")


def test_r13_scheme_space_is_bounded_and_nonzero() -> None:
    schemes = mod._schemes()
    assert schemes
    assert len(schemes) <= 500
    for scheme in schemes:
        assert scheme.aligned_weight > 0
        assert scheme.c2_cap > 0
        assert scheme.short_cap > 0
        assert scheme.warn_multiplier > 0
        assert scheme.hard_multiplier > 0
        assert scheme.hard_dd_r > scheme.warn_dd_r
        if scheme.loss_multiplier is not None:
            assert scheme.loss_multiplier > 0


def test_r13_does_not_use_all_time_peak_contract() -> None:
    assert "rolling" in mod.IDENTITY.lower()
