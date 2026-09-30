from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_r0_acceptance_failure_forensics import (
    summarize_acceptance_failure,
)
from qore.infrastructure.trader_lab.capitalizer_r0_gross_characterization import (
    CapitalizerR0Trade,
)


def _m5_row(
    opened_at: datetime,
    *,
    low: int,
    open_: int,
    high: int,
    close: int,
) -> dict[str, object]:
    return {
        "schema": "qore.cibo_market_atlas.raw_m5.v1",
        "identity": "CIBO_MARKET_ATLAS_10Y_CONSUMPTION_V1",
        "canonical_symbol": "USDJPY",
        "opened_at": opened_at.isoformat(),
        "digits": 3,
        "volume": 100,
        "low_relative": low,
        "open_relative": open_,
        "high_relative": high,
        "close_relative": close,
    }


def _write_m5(root: Path) -> tuple[datetime, datetime]:
    ledger = root / "RAW_M5_LEDGER"
    ledger.mkdir(parents=True)
    start = datetime(2026, 1, 2, 1, 0, tzinfo=UTC)
    rows = (
        _m5_row(
            start,
            low=10_000_000,
            open_=10_002_000,
            high=10_006_000,
            close=10_004_000,
        ),
        _m5_row(
            start + timedelta(minutes=5),
            low=10_002_000,
            open_=10_004_000,
            high=10_010_000,
            close=10_009_000,
        ),
        _m5_row(
            start + timedelta(minutes=10),
            low=10_004_000,
            open_=10_008_000,
            high=10_012_000,
            close=10_005_000,
        ),
        _m5_row(
            start + timedelta(minutes=15),
            low=10_001_000,
            open_=10_005_000,
            high=10_007_000,
            close=10_002_000,
        ),
    )
    with (ledger / "2026.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")
    return start + timedelta(minutes=10), start + timedelta(minutes=20)


def _write_empty_target(root: Path) -> None:
    root.mkdir(parents=True)
    (root / "TARGET_DESTINATION_LEDGER_V2.jsonl").write_text(
        "",
        encoding="utf-8",
    )


def test_acceptance_failure_forensics_compare_causal_features_by_outcome(
    tmp_path: Path,
) -> None:
    m5_root = tmp_path / "m5"
    target_root = tmp_path / "target"
    first_signal, second_signal = _write_m5(m5_root)
    _write_empty_target(target_root)

    trades = (
        CapitalizerR0Trade(
            symbol="USDJPY",
            side=CapitalizerSide.LONG,
            signal_at=first_signal,
            entry_at=first_signal,
            exit_at=first_signal + timedelta(minutes=5),
            event_labels=("HIGH_ACCEPTANCE",),
            entry_price=Decimal("100.090"),
            stop_price=Decimal("100.020"),
            target_price=Decimal("100.200"),
            initial_risk_price=Decimal("0.070"),
            planned_reward_r=Decimal("1.5714285714"),
            realized_gross_r=Decimal("1.2"),
            exit_reason="TARGET",
            bars_held=1,
            same_bar_stop_target_ambiguity=False,
        ),
        CapitalizerR0Trade(
            symbol="USDJPY",
            side=CapitalizerSide.SHORT,
            signal_at=second_signal,
            entry_at=second_signal,
            exit_at=second_signal + timedelta(minutes=5),
            event_labels=("LOW_ACCEPTANCE",),
            entry_price=Decimal("100.020"),
            stop_price=Decimal("100.070"),
            target_price=Decimal("99.900"),
            initial_risk_price=Decimal("0.050"),
            planned_reward_r=Decimal("2.4"),
            realized_gross_r=Decimal("-1"),
            exit_reason="STOP",
            bars_held=1,
            same_bar_stop_target_ambiguity=False,
        ),
    )

    report = summarize_acceptance_failure(
        m5_root=m5_root,
        target_root=target_root,
        trades=trades,
    )
    assert report.acceptance_trades == 2
    assert report.causal_features_only is True
    assert report.outcome_used_as_label_only is True
    assert report.filter_selected is False
    assert report.candidate_revision_defined is False
    assert report.rule_promotion_allowed is False
    assert {(row.event_signature, row.outcome_label) for row in report.rows} == {
        ("HIGH_ACCEPTANCE", "WIN"),
        ("LOW_ACCEPTANCE", "LOSS"),
    }
