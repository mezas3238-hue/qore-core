from decimal import Decimal

from qore.infrastructure.trader_lab import vt08_index_r14_rolling_refinement as mod


def test_r14_contract() -> None:
    assert mod.MIN_TRADES == 1500
    assert mod.MAX_TRADES == 1600
    assert mod.MIN_EFFECTIVE_WEIGHT == Decimal("0.005")
    assert mod.PRIMARY_PF_GOAL == Decimal("1.50")
    assert mod.PRIMARY_DD_GOAL == Decimal("6")
    assert mod.SECONDARY_PF_GOAL == Decimal("1.30")
    assert mod.SECONDARY_DD_GOAL == Decimal("8")


def test_r14_local_search_is_bounded() -> None:
    schemes = mod._schemes()
    assert len(schemes) == 324
    assert len({scheme.scheme_id for scheme in schemes}) == 324


def test_r14_never_allows_zero_effective_weight() -> None:
    assert mod.MIN_EFFECTIVE_WEIGHT > 0
    for scheme in mod._schemes():
        parent = scheme.as_r13()
        assert parent.aligned_weight > 0
        assert parent.warn_multiplier > 0
        assert parent.hard_multiplier > 0
        assert parent.loss_multiplier is not None
        assert parent.loss_multiplier > 0
