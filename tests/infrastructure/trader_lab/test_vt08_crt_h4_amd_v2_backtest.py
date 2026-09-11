from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab.vt08_crt_h4_amd_v2_backtest import (
    _FOREX_H4_ANCHOR_HOURS,
    _FUTURES_H4_ANCHOR_HOURS,
    Vt08CrtH4AmdV2SourceAudit,
    _Bar,
    _candidate_from_protected,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_crt_h4_amd_v2 import (
    METHODOLOGY_VERSION,
    Vt08CrtH4AmdV2Scenario,
    Vt08CrtH4AmdV2TimingFamily,
)


def _bar(
    start: datetime,
    open_price: str,
    high: str,
    low: str,
    close: str,
) -> _Bar:
    return _Bar(
        opened_at=start,
        closed_at=start + timedelta(minutes=15),
        open=Decimal(open_price),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
    )


def test_historical_audit_uses_only_owner_three_by_three_windows() -> None:
    assert _FOREX_H4_ANCHOR_HOURS == (1, 5, 9)
    assert _FUTURES_H4_ANCHOR_HOURS == (2, 6, 10)


def test_mechanical_cisd_candidate_is_not_relabelled_as_trade_or_win() -> None:
    start = datetime(2026, 1, 1, 5, tzinfo=UTC)
    current = (
        _bar(start, "100", "100.5", "94", "96"),
        _bar(start + timedelta(minutes=15), "96", "101", "95", "100.5"),
        _bar(start + timedelta(minutes=30), "100.5", "104", "99", "103"),
    )
    candidate = _candidate_from_protected(
        scenario=Vt08CrtH4AmdV2Scenario.REVERSAL_EXPANSION_C2,
        anchor=start,
        closes_at=start + timedelta(hours=4),
        current=current,
        side=DemoTradingSetupSide.LONG,
        required_run_level=Decimal("95"),
        bias_status="requires-source-context-confirmation",
        prior_wick_status=None,
    )
    assert candidate is not None
    payload = candidate.payload()
    assert payload["automatic_setup"] is False
    assert payload["source_point_of_interest_status"] == "requires-source-poi-confirmation"
    assert payload["source_wick_status"] == "qualitative-unresolved-by-video"
    assert payload["post_signal_path_is_not_trade_result"] is True
    assert "win" not in payload
    assert "loss" not in payload


def test_source_audit_reports_reconciled_empty_economic_replay() -> None:
    audit = Vt08CrtH4AmdV2SourceAudit(
        software_sha="a" * 40,
        symbol="EURUSD",
        provider_symbol_name="EURUSD",
        account_fingerprint="b" * 64,
        evidence_fingerprint="c" * 64,
        checked_at=datetime(2026, 1, 1, tzinfo=UTC),
        timing_family=Vt08CrtH4AmdV2TimingFamily.FOREX,
        eligible_anchor_windows=0,
        missing_anchor_windows=0,
        candidates=(),
    )
    payload = audit.payload()
    assert payload["methodology_version"] == METHODOLOGY_VERSION
    assert payload["human_owner_operating_scope"] is True
    assert payload["operating_timezone"] == "America/New_York"
    assert payload["forex_operating_h4_anchors"] == [1, 5, 9]
    assert payload["futures_operating_h4_anchors"] == [2, 6, 10]
    assert payload["automatic_setup_count"] == 0
    assert payload["filled_count"] == 0
    assert payload["win_count"] == 0
    assert payload["loss_count"] == 0
    assert payload["economic_backtest_authorized"] is True
    assert payload["prior_13468_campaign_valid_for_economics"] is False
    assert payload["prior_16351_candidate_count_final_source_fidelity"] is False


def test_c3_fvg_cisd_setup_fills_only_after_signal_and_hits_target() -> None:
    start = datetime(2026, 1, 1, 5, tzinfo=UTC)
    current = (
        _bar(start, "99", "100", "98", "99.5"),
        _bar(start + timedelta(minutes=15), "99.5", "104", "99.5", "103"),
        _bar(start + timedelta(minutes=30), "103", "104", "103", "103.5"),
        _bar(start + timedelta(minutes=45), "102", "102.2", "101", "101.5"),
        _bar(start + timedelta(minutes=60), "101.5", "103", "101.2", "102.5"),
        _bar(start + timedelta(minutes=75), "102.5", "106", "102", "105"),
    )
    candidate = _candidate_from_protected(
        scenario=Vt08CrtH4AmdV2Scenario.CONTINUATION_EXPANSION_C3,
        anchor=start,
        closes_at=start + timedelta(hours=4),
        current=current,
        side=DemoTradingSetupSide.LONG,
        required_run_level=None,
        bias_status="completed-candle2-reversal-direction",
        prior_wick_status="source-formalized-boundary-sweep",
        executable_c3_profile=True,
    )
    assert candidate is not None
    assert candidate.automatic_setup is True
    assert candidate.entry_price == Decimal("102.5")
    assert candidate.stop_price == Decimal("101")
    assert candidate.target_price == Decimal("105.5")
    assert candidate.filled_at == start + timedelta(minutes=75)
    assert candidate.outcome == "target"
    assert candidate.result_r == Decimal("2")
