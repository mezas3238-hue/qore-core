"""V3 source freeze vs later price-only first-hit; never a trading outcome."""
from datetime import UTC, datetime, timedelta

from qore.infrastructure.trader_lab.vt08_crt_pure_2y_replay import ReplayBar
from qore.infrastructure.trader_lab.vt08_crt_three_source_v3_price_lifecycle import (
    evaluate_frozen_v3_price_lifecycle,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket

BASE = datetime(2025, 3, 3, 0, tzinfo=UTC)


def _fixture() -> tuple[ReplayBar, ...]:
    bars: list[ReplayBar] = []
    for i in range(48):
        bars.append(ReplayBar(BASE + timedelta(minutes=5 * i), 100, 110, 90, 105))
    for i in range(48, 96):
        bars.append(ReplayBar(BASE + timedelta(minutes=5 * i), 105, 108, 88, 95))
    for q in range(16):
        data = (
            (97, 99, 90, 94) if q == 1
            else (94, 99, 91, 98) if q == 2
            else (95, 99, 92, 95)
        )
        for i in range(3):
            idx = 96 + q * 3 + i
            bars.append(ReplayBar(BASE + timedelta(minutes=5 * idx), *data))
    return tuple(bars)


def test_frozen_v3_source_and_price_path_reconcile_one_qualified_source() -> None:
    sample = list(_fixture())
    # First M5 AFTER M15 confirmation closes at 08:45. No lookahead entry.
    sample[105] = ReplayBar(
        BASE + timedelta(minutes=525), 95, 101, 92, 99
    )
    manifest, rows = evaluate_frozen_v3_price_lifecycle(
        CrtPureMarket.AUDUSD, tuple(sample)
    )
    assert manifest["v3_source_candidates"] == 1
    assert manifest["v3_price_path_reconciled"] == 1
    assert manifest["outcomes"] == {"DESTINATION_FIRST": 1}
    assert rows[0]["source_m15_invalidating_extreme_relative"] == 90
    assert rows[0]["decision_clock_utc"] == "2025-03-03T08:45:00+00:00"
    assert manifest["no_PnL_or_sizing"] is True
    assert rows[0]["not_a_trade"] is True
    assert manifest["GLOBAL_CERTIFIED"] is False


def test_mutating_postdecision_m5_can_change_only_lifecycle_not_source_identity() -> None:
    src = list(_fixture())
    losing = list(src)
    winning = list(src)
    losing[105] = ReplayBar(BASE + timedelta(minutes=525), 95, 99, 89, 94)
    winning[105] = ReplayBar(BASE + timedelta(minutes=525), 95, 101, 92, 99)
    _, loss = evaluate_frozen_v3_price_lifecycle(CrtPureMarket.USDJPY, tuple(losing))
    _, win = evaluate_frozen_v3_price_lifecycle(CrtPureMarket.USDJPY, tuple(winning))
    assert loss[0]["source_event_id"] == win[0]["source_event_id"]
    assert loss[0]["decision_clock_utc"] == win[0]["decision_clock_utc"]
    assert loss[0]["price_path_outcome"] == "INVALIDATION_FIRST"
    assert win[0]["price_path_outcome"] == "DESTINATION_FIRST"
    assert loss[0]["not_a_trade"] and win[0]["not_a_trade"]


def test_missing_future_m5_records_unknown_instead_of_inventing_fill() -> None:
    truncated = tuple(
        row for row in _fixture()
        if row.opened_at < BASE + timedelta(minutes=525)
    )
    manifest, ledger = evaluate_frozen_v3_price_lifecycle(
        CrtPureMarket.AUDUSD, truncated
    )
    assert manifest["v3_source_candidates"] == 1
    assert ledger[0]["price_path_outcome"] == "UNKNOWN_MISSING_ENTRY_OPEN_PRICE"
    assert manifest["price_only_not_broker_fills"] is True
