from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_r0_gross_characterization import (
    CapitalizerR0Trade,
)
from qore.infrastructure.trader_lab.capitalizer_r0_loss_forensics import (
    summarize_r0_forensics,
)


def _trade(
    *,
    index: int,
    side: CapitalizerSide,
    result: str,
    event: str,
) -> CapitalizerR0Trade:
    entry = datetime(2026, 1, 1, 1, 0, tzinfo=UTC) + timedelta(hours=index)
    return CapitalizerR0Trade(
        symbol="USDJPY",
        side=side,
        signal_at=entry,
        entry_at=entry,
        exit_at=entry + timedelta(minutes=5),
        event_labels=(event,),
        entry_price=Decimal("100"),
        stop_price=Decimal("99") if side is CapitalizerSide.LONG else Decimal("101"),
        target_price=Decimal("102") if side is CapitalizerSide.LONG else Decimal("98"),
        initial_risk_price=Decimal("1"),
        planned_reward_r=Decimal("2"),
        realized_gross_r=Decimal(result),
        exit_reason="STOP" if Decimal(result) < 0 else "TARGET",
        bars_held=1,
        same_bar_stop_target_ambiguity=False,
    )


def test_r0_forensics_decomposes_and_preserves_diagnostic_governance() -> None:
    trades = (
        _trade(index=0, side=CapitalizerSide.LONG, result="-1", event="LOW_ACCEPTANCE"),
        _trade(index=1, side=CapitalizerSide.LONG, result="-1", event="LOW_ACCEPTANCE"),
        _trade(index=2, side=CapitalizerSide.SHORT, result="2", event="HIGH_ACCEPTANCE"),
        _trade(index=3, side=CapitalizerSide.SHORT, result="-1", event="HIGH_ACCEPTANCE"),
    )
    report = summarize_r0_forensics(trades)

    assert report.overall.trades == 4
    assert len(report.by_side) == 2
    assert len(report.by_event_signature) == 2
    assert report.longest_loss_streaks[0].length == 2
    assert report.longest_loss_streaks[0].dominant_side == "LONG"
    assert report.diagnostic_only is True
    assert report.filter_selected is False
    assert report.candidate_revision_defined is False
    assert report.execution_costs_applied is False
    assert report.fresh_holdout_claimed is False
    assert report.rule_promotion_allowed is False
