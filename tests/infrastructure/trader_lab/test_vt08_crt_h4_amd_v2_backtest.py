from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab.vt08_crt_h4_amd_v2_backtest import (
    Vt08CrtH4AmdV2SourceAudit,
    _Bar,
    _candidate_from_protected,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_crt_h4_amd_v2 import (
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
    assert payload["source_wick_status"] == "qualitative-unresolved-by-video"
    assert payload["post_signal_path_is_not_trade_result"] is True
    assert "win" not in payload
    assert "loss" not in payload


def test_source_audit_refuses_economic_backtest_without_video_judgments() -> None:
    audit = Vt08CrtH4AmdV2SourceAudit(
        software_sha="a" * 40,
        symbol="XAUUSD",
        provider_symbol_name="XAUUSD",
        account_fingerprint="b" * 64,
        evidence_fingerprint="c" * 64,
        checked_at=datetime(2026, 1, 1, tzinfo=UTC),
        timing_family=Vt08CrtH4AmdV2TimingFamily.SOURCE_UNRESOLVED,
        eligible_anchor_windows=0,
        missing_anchor_windows=0,
        candidates=(),
    )
    payload = audit.payload()
    assert payload["automatic_setup_count"] == 0
    assert payload["filled_count"] == 0
    assert payload["win_count"] is None
    assert payload["loss_count"] is None
    assert payload["economic_backtest_authorized"] is False
    assert payload["prior_13468_campaign_valid_for_economics"] is False
