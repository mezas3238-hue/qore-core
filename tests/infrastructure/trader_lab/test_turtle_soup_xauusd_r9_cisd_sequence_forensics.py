from decimal import Decimal
from types import SimpleNamespace

from qore.infrastructure.trader_lab import turtle_soup_xauusd_r9_cisd_sequence_forensics as r9s
from qore.infrastructure.trader_lab.ict_turtle_soup_r4_source_exact import Side


def _bar(open_: str, high: str, low: str, close: str):
    return SimpleNamespace(
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
    )


def test_path_efficiency_is_one_for_monotonic_path() -> None:
    bars = [_bar('1','2','1','1'), _bar('1','3','1','2'), _bar('2','4','2','3')]
    assert r9s._path_efficiency(bars) == Decimal('1')


def test_favorable_step_share_respects_side() -> None:
    bars = [_bar('1','2','1','1'), _bar('1','3','1','2'), _bar('2','3','1','1')]
    assert r9s._favorable_step_share(bars, Side.LONG) == Decimal('0.5')
    assert r9s._favorable_step_share(bars, Side.SHORT) == Decimal('0.5')


def test_favorable_close_location() -> None:
    bar = _bar('2','4','1','3')
    assert r9s._favorable_close_location(bar, Side.LONG) == Decimal('2') / Decimal('3')
    assert r9s._favorable_close_location(bar, Side.SHORT) == Decimal('1') / Decimal('3')


def test_feature_contract_contains_expansion_quality() -> None:
    required = {
        'raid_to_cisd_path_efficiency',
        'reclaim_to_cisd_path_efficiency',
        'confirm_bar_favorable_close_location',
        'confirm_bar_overlap_previous_fraction',
        'post_reclaim_max_reviolation_raid_fraction',
    }
    assert required <= set(r9s.FEATURES)
