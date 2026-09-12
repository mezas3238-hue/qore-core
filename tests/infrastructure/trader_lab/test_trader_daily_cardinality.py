from datetime import UTC, date, datetime

import pytest

from qore.infrastructure.trader_lab.trader_daily_cardinality import (
    DailyCardinalityValidationError,
    DailyTradeBudget,
    MarketDayId,
    MarketDayLedger,
    market_day_id_from_timestamp,
    stable_candidate_id,
    summarize_market_days,
)

_SHA = "a" * 40
_EVIDENCE = "b" * 64


def _ledger(
    *,
    family: str = "vt08-forex",
    market: str = "EURUSD",
    local_date: date = date(2026, 7, 6),
    windows: tuple[int, ...] = (1, 5, 9),
    eligible: bool = True,
    complete: bool = True,
) -> MarketDayLedger:
    return MarketDayLedger(
        market_day_id=MarketDayId(family, market, local_date),
        eligible_day=eligible,
        data_complete=complete,
        authorized_windows=windows,
        source_rule_version="v2.5-owner-operational-scope",
        software_sha=_SHA,
        evidence_fingerprint=_EVIDENCE,
    )


def test_three_valid_forex_windows_may_create_many_setups_but_only_one_selection() -> None:
    ledger = _ledger()
    for hour in (1, 5, 9):
        ledger = ledger.observe_window(hour)
        ledger = ledger.add_candidate(f"candidate:c2-{hour}")
        ledger = ledger.add_qualified_setup(f"setup:window-{hour}")
    assert ledger.candidate_count == 3
    assert ledger.qualified_setup_count == 3
    selected = ledger.select_setup("setup:window-5")
    assert selected.selected_setup_count == 1
    assert selected.daily_trade_budget is DailyTradeBudget.CONSUMED
    with pytest.raises(DailyCardinalityValidationError):
        selected.select_setup("setup:window-9")


def test_three_valid_futures_windows_may_create_many_setups_but_only_one_fill() -> None:
    ledger = _ledger(
        family="vt08-futures",
        market="NAS100",
        windows=(2, 6, 10),
    )
    for hour in (2, 6, 10):
        ledger = ledger.observe_window(hour)
        ledger = ledger.add_qualified_setup(f"setup:window-{hour}")
    ledger = ledger.select_setup("setup:window-2")
    ledger = ledger.record_pending_order("order:daily-selected")
    ledger = ledger.record_fill("fill:one")
    assert ledger.filled_trade_count == 1
    with pytest.raises(DailyCardinalityValidationError):
        ledger.record_fill("fill:two")


def test_c2_and_c3_candidates_same_day_remain_diagnostic_until_one_setup_is_selected() -> None:
    ledger = _ledger().observe_window(1)
    ledger = ledger.add_candidate("candidate:c2-long")
    ledger = ledger.add_candidate("candidate:c3-long")
    ledger = ledger.add_qualified_setup("setup:c2")
    ledger = ledger.add_qualified_setup("setup:c3")
    assert ledger.candidate_count == 2
    assert ledger.qualified_setup_count == 2
    assert ledger.selected_setup_count == 0
    ledger = ledger.select_setup("setup:c3")
    assert ledger.selected_setup_count == 1


def test_multiple_pois_confirmations_and_entry_families_do_not_expand_daily_budget() -> None:
    ledger = _ledger().observe_window(5)
    for setup_id in (
        "setup:fvg-confirmation-close",
        "setup:positional-h4-open",
        "setup:protected-swing-continuation",
    ):
        ledger = ledger.add_qualified_setup(setup_id)
    ledger = ledger.select_setup("setup:fvg-confirmation-close")
    with pytest.raises(DailyCardinalityValidationError):
        ledger.select_setup("setup:positional-h4-open")


def test_duplicate_candidate_identity_is_rejected() -> None:
    ledger = _ledger().add_candidate("candidate:same-evidence")
    with pytest.raises(DailyCardinalityValidationError):
        ledger.add_candidate("candidate:same-evidence")


def test_candidate_identity_is_stable_for_same_market_day_and_evidence() -> None:
    market_day = MarketDayId("vt08-forex", "EURUSD", date(2026, 7, 6))
    first = stable_candidate_id(
        market_day_id=market_day,
        anchor_hour_new_york=5,
        scenario="candle3",
        side="long",
        signal_at=datetime(2026, 7, 6, 14, 15, tzinfo=UTC),
        evidence_fingerprint=_EVIDENCE,
    )
    second = stable_candidate_id(
        market_day_id=market_day,
        anchor_hour_new_york=5,
        scenario="candle3",
        side="long",
        signal_at=datetime(2026, 7, 6, 14, 15, tzinfo=UTC),
        evidence_fingerprint=_EVIDENCE,
    )
    assert first == second


def test_dst_transition_uses_new_york_local_date_not_utc_date() -> None:
    before_fall_back = market_day_id_from_timestamp(
        trader_family="vt08-forex",
        canonical_market="EURUSD",
        observed_at=datetime(2026, 11, 1, 3, 30, tzinfo=UTC),
    )
    after_fall_back = market_day_id_from_timestamp(
        trader_family="vt08-forex",
        canonical_market="EURUSD",
        observed_at=datetime(2026, 11, 1, 7, 30, tzinfo=UTC),
    )
    assert before_fall_back.local_date == date(2026, 10, 31)
    assert after_fall_back.local_date == date(2026, 11, 1)


def test_weekend_or_data_gap_day_can_be_observed_but_cannot_select_setup() -> None:
    weekend = _ledger(
        local_date=date(2026, 7, 4),
        eligible=False,
        complete=False,
    ).observe_window(1)
    weekend = weekend.add_candidate("candidate:diagnostic-only")
    assert weekend.candidate_count == 1
    with pytest.raises(DailyCardinalityValidationError):
        weekend.add_qualified_setup("setup:not-authorized")


def test_exact_midnight_transition_creates_distinct_market_day_authorities() -> None:
    first = market_day_id_from_timestamp(
        trader_family="vt08-forex",
        canonical_market="EURUSD",
        observed_at=datetime(2026, 7, 6, 3, 59, 59, tzinfo=UTC),
    )
    second = market_day_id_from_timestamp(
        trader_family="vt08-forex",
        canonical_market="EURUSD",
        observed_at=datetime(2026, 7, 6, 4, 0, 0, tzinfo=UTC),
    )
    assert first.local_date == date(2026, 7, 5)
    assert second.local_date == date(2026, 7, 6)
    assert first != second


def test_aggregate_fills_cannot_exceed_eligible_market_days() -> None:
    first = _ledger(local_date=date(2026, 7, 6)).add_qualified_setup("setup:a")
    first = first.select_setup("setup:a").record_pending_order("order:a").record_fill("fill:a")
    second = _ledger(local_date=date(2026, 7, 7))
    summary = summarize_market_days((first, second))
    assert summary.eligible_market_days == 2
    assert summary.filled_trade_count == 1
    assert summary.filled_trade_count <= summary.eligible_market_days
    assert summary.daily_cardinality_violations == 0


def test_duplicate_market_day_in_aggregate_fails_closed() -> None:
    ledger = _ledger()
    with pytest.raises(DailyCardinalityValidationError):
        summarize_market_days((ledger, ledger))


def test_terminal_trade_count_never_exceeds_one() -> None:
    ledger = _ledger().add_qualified_setup("setup:a")
    ledger = ledger.select_setup("setup:a")
    ledger = ledger.record_pending_order("order:a")
    ledger = ledger.record_fill("fill:a")
    ledger = ledger.record_terminal_trade("trade:a")
    assert ledger.terminal_trade_count == 1
    with pytest.raises(DailyCardinalityValidationError):
        ledger.record_terminal_trade("trade:b")
