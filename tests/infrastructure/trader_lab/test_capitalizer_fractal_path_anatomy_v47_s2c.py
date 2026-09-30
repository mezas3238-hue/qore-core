from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from qore.infrastructure.trader_lab import (
    capitalizer_fractal_path_anatomy_v47_s2c as path_audit,
)
from qore.infrastructure.trader_lab import (
    capitalizer_source_strategy_gross_economics_v47_s2b as s2b,
)


def _trade(value: str, *, reason: str = "STOP") -> s2b.S2BGrossTrade:
    return s2b.S2BGrossTrade(
        identity=s2b.IDENTITY,
        source_identity=s2b.SOURCE_S2A_IDENTITY,
        period="development",
        symbol="EURUSD",
        session="LONDON",
        operating_date="2026-01-01",
        side="LONG",
        route="FRACTAL_SCALP_CONTINUATION",
        entry_at="2026-01-01T10:00:15+00:00",
        entry_price="100",
        stop_price="99",
        target_price="103",
        initial_risk_price="1",
        target_r="3",
        exit_at="2026-01-01T10:30:00+00:00",
        exit_price=str(Decimal("100") + Decimal(value)),
        exit_reason=reason,
        realized_gross_r=value,
        m1_bars_held=30,
        exact_exit_ticks_required=False,
        stop_first_fallback_used=False,
    )


def _audit_row(
    *,
    realized: str,
    label: str,
    exit_reason: str,
    mae: str,
    mfe: str,
) -> path_audit.FractalPathAuditRow:
    return path_audit.FractalPathAuditRow(
        identity=path_audit.IDENTITY,
        period="development",
        symbol="EURUSD",
        session="LONDON",
        side="LONG",
        entry_at="2026-01-01T10:00:15+00:00",
        exit_at="2026-01-01T10:30:00+00:00",
        exit_reason=exit_reason,
        realized_gross_r=realized,
        outcome_label=label,
        mae_r=mae,
        mfe_r=mfe,
        mae_at=datetime(2026, 1, 1, 10, 5, tzinfo=UTC).isoformat(),
        mfe_at=datetime(2026, 1, 1, 10, 10, tzinfo=UTC).isoformat(),
        time_to_mae_minutes=4,
        time_to_mfe_minutes=9,
        path_order="MAE_BEFORE_MFE",
        exact_partial_interval_ticks_used=True,
    )


def test_path_summary_separates_winners_losers_and_full_stops() -> None:
    rows = (
        _audit_row(
            realized="2",
            label="WINNER",
            exit_reason="TARGET",
            mae="0.2",
            mfe="2.2",
        ),
        _audit_row(
            realized="-1",
            label="LOSER",
            exit_reason="STOP",
            mae="1",
            mfe="0.3",
        ),
    )
    summary = path_audit.summarize(rows)
    assert summary["trades"] == 2
    assert summary["winners"] == 1
    assert summary["losers"] == 1
    assert summary["full_stop_losers"] == 1
    assert summary["median_mae_r_winners"] == "0.2"
    assert summary["median_mfe_r_full_stop_losers"] == "0.3"


def test_path_row_keeps_outcome_labels_research_only() -> None:
    row = _audit_row(
        realized="-1",
        label="LOSER",
        exit_reason="STOP",
        mae="1",
        mfe="0.4",
    )
    assert row.terminal_outcome_research_label_only is True
    assert row.mae_mfe_productive_feature_allowed is False
    assert row.fresh_holdout_opened is False
    assert row.trader_certified is False


def test_s2c_sources_are_frozen() -> None:
    assert path_audit.PREDECLARATION_COMMENT_ID == 5901892907
    assert path_audit.SOURCE_S2B_RUN_ID == 36651366703
    assert path_audit.SOURCE_S2B_SHA == "59d826f3b24031e52e6c0f32e8cca1ecfb4d0524"
