from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.cibo_open_position_mark_intelligence import (
    CiboPositionMarkEvidence,
)
from qore.infrastructure.cibo_reused_holdout_compound_portfolio_lane import (
    _Open,
    _open_economic_position_snapshot,
)


T0 = datetime(2026, 10, 4, 12, 0, tzinfo=UTC)


def _open() -> _Open:
    return _Open(
        signal_fingerprint="open-1",
        trader_id="R38_EURUSD",
        qore_symbol="EURUSD",
        side="long",
        entry_at=T0,
        exit_at=T0 + timedelta(minutes=60),
        entry_price=Decimal("100"),
        structural_stop=Decimal("99"),
        technical_target=Decimal("102"),
        authorization_id="auth-1",
        authorized_volume=Decimal("1"),
        authorized_stop_risk_usd=Decimal("1"),
        authorized_margin_usd=Decimal("2"),
        gross_structural_outcome_r=Decimal("1"),
        provider_cost_usd=Decimal("0.1"),
        entry_expected_net_value_usd=Decimal("2"),
        entry_expected_capital_minutes=Decimal("60"),
        expectation_evidence_sha256="sha256:" + "a" * 64,
        protected_loss_reserve_usd=Decimal("1"),
        source_traders_before_entry=("R38_EURUSD",),
    )


def _mark(observed_minutes: int, price: str, digest: str) -> CiboPositionMarkEvidence:
    observed = T0 + timedelta(minutes=observed_minutes)
    return CiboPositionMarkEvidence(
        signal_fingerprint="open-1",
        qore_symbol="EURUSD",
        observed_at=observed,
        source_bar_opened_at=observed - timedelta(minutes=5),
        source_bar_closed_at=observed,
        mark_price=Decimal(price),
        evidence_sha256="sha256:" + digest * 64,
    )


def test_open_position_snapshot_uses_latest_causal_mark_only() -> None:
    decision_at = T0 + timedelta(minutes=20)
    marks = {
        "open-1": (
            _mark(5, "100.2", "b"),
            _mark(15, "100.7", "c"),
            _mark(25, "101.5", "d"),
        )
    }

    snapshot = _open_economic_position_snapshot(
        _open(),
        decision_at=decision_at,
        marks_by_signal=marks,
    )

    assert snapshot.current_mark_price == Decimal("100.7")
    assert snapshot.market_state_observed_at == T0 + timedelta(minutes=15)
    assert snapshot.mark_to_market_identified is True
    assert snapshot.current_mark_price != Decimal("101.5")


def test_open_position_snapshot_remains_unmarked_without_causal_evidence() -> None:
    snapshot = _open_economic_position_snapshot(
        _open(),
        decision_at=T0 + timedelta(minutes=2),
        marks_by_signal={
            "open-1": (_mark(5, "100.2", "e"),)
        },
    )

    assert snapshot.current_mark_price is None
    assert snapshot.market_state_observed_at is None
    assert snapshot.mark_to_market_identified is False
