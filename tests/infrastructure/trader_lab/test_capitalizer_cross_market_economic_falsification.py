from qore.infrastructure.trader_lab.capitalizer_cross_market_economic_falsification import (
    _remove_noreclaim_cisd_cross_h1,
)


def test_timing_ablation_is_scoped_only_to_noreclaim_cross_h1() -> None:
    assert _remove_noreclaim_cisd_cross_h1(
        state_family="NO_RECLAIM_FRESH",
        timing_state="ANY_CROSS_H1",
    )
    assert not _remove_noreclaim_cisd_cross_h1(
        state_family="RECLAIM_ALL_FRESH",
        timing_state="ANY_CROSS_H1",
    )
    assert not _remove_noreclaim_cisd_cross_h1(
        state_family="NO_RECLAIM_FRESH",
        timing_state="ALL_WITHIN_H1",
    )
