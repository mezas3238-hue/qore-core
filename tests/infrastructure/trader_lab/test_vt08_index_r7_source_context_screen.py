from decimal import Decimal

from qore.infrastructure.trader_lab import vt08_index_r7_source_context_screen as mod


def test_r7_screen_contract() -> None:
    assert mod.MIN_TRADES == 1500
    assert mod.MAX_TRADES == 1600
    assert mod.RAW_PF_MIN == Decimal("1.10")
    assert mod.GOVERNED_PF_MIN == Decimal("1.50")
    assert mod.GOVERNED_DD_MAX == Decimal("6")


def test_r7_screen_space_is_bounded() -> None:
    screens = mod._screens()
    assert len(screens) == 31
    assert len({screen.screen_id for screen in screens}) == 31


def test_r7_screen_has_no_post_entry_feature() -> None:
    assert set(mod.Feature.__annotations__) == {
        "previous_source_day_body_opposed"
    }
