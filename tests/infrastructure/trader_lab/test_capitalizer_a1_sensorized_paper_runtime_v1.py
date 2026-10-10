"""Full sensor → actual nine-market Master Frame → PAPER execution regression.

The world/regime evidence here is a documented synthetic FIXTURE. These
tests prove end-to-end call graph only, not historical financial performance.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from test_capitalizer_master_cognitive_frame import (
    _a1_multi_hypothesis_fixture,
    _paper_source,
)

from qore.infrastructure.trader_lab.capitalizer_a1_master_frame_paper_trader_integration_v1 import (
    A1PaperSource,
)
from qore.infrastructure.trader_lab.capitalizer_a1_sensorized_paper_runtime_v1 import (
    run_sensorized_master_frame_paper,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_entry_timing_sensors_shadow_v1 import (
    EntrySensorInput,
)

T = datetime(2026, 1, 5, 1, tzinfo=UTC)


def _bars(symbol: str) -> tuple[CapitalizerM1Bar, ...]:
    candles = (
        ("100", "101", "99.5", "100.5"),
        ("100.5", "100.8", "99", "99.5"),
        ("99.5", "100.2", "99.3", "100"),
        ("100", "100.1", "98.5", "99"),
        ("99", "99.4", "98.8", "99.1"),
        ("99.1", "100.6", "99", "100.4"),
    )
    return tuple(
        CapitalizerM1Bar(
            symbol=symbol,
            opened_at=T-timedelta(minutes=6-i),
            closed_at=T-timedelta(minutes=5-i),
            open=Decimal(o), high=Decimal(hi),
            low=Decimal(low), close=Decimal(close),
            volume=100, digits=3,
        )
        for i, (o, hi, low, close) in enumerate(candles)
    )


def _inputs() -> tuple[
    tuple[A1PaperSource, ...],
    dict[str, EntrySensorInput],
]:
    ids = ("SRC:AUDJPY:A", "SRC:AUDJPY:B", "SRC:USDJPY:C")
    originals = tuple(
        A1PaperSource(
            source_opportunity_id=sid,
            trade=replace(
                _paper_source(sid, T, symbol=market, realized_r=pnl).trade,
                entry_price="100.4",
            ),
        )
        for sid, market, pnl in (
            (ids[0], "AUDJPY", "-1"),
            (ids[1], "AUDJPY", "0.5"),
            (ids[2], "USDJPY", "0.4"),
        )
    )
    inputs = {
        row.source_opportunity_id: EntrySensorInput(
            symbol=row.trade.symbol, session="ASIA",
            decision_at=T, h1_direction="BULLISH",
            h1_basis="SOURCE_CAUSAL_C2", h1_confirmed_at=T-timedelta(hours=1),
            m15_confirmed_at=T-timedelta(minutes=15),
            m15_protected_stop=Decimal("98"),
            m1_bars=_bars(row.trade.symbol),
        )
        for row in originals
    }
    return originals, inputs


def test_native_candles_flow_to_full_master_to_actual_paper_source_decisions() -> None:
    originals, snapshots = _inputs()
    ids = tuple(row.source_opportunity_id for row in originals)
    barrier = _a1_multi_hypothesis_fixture(T, source_ids=ids)
    result = run_sensorized_master_frame_paper(
        barriers=(barrier,), source_evidence=snapshots,
        source_originals=originals, baseline_selected_source_ids=ids,
    )
    assert result.full_master_frame_invoked
    assert result.sensors_reached_full_master_frame
    assert result.observed_sensor_frames == 3
    assert result.source_cisd_identity_conflicts == 0
    assert result.report.cognitively_passed == 3
    assert result.report.paper_selected == 3
    assert result.report.master_frame_paper_metrics["trades"] == 3
    assert all(row.sensor_evidence_present for row in result.report.source_ledger)
    assert any("SCALPER_SENSOR:" in token for token in
               result.report.source_ledger[0].why_tokens) is False
    # HOW: observation tokens enter the real full frame; final WHY remains
    # gate-oriented rather than falsely claiming that missing data are known.
    assert not result.report.full_historical_native_nine_market_run
    assert not result.live_authorized


def test_source_cisd_family_conflict_is_evidence_not_an_automatic_entry_veto() -> None:
    originals, snapshots = _inputs()
    ids = tuple(row.source_opportunity_id for row in originals)
    changed = replace(
        originals[0],
        trade=replace(originals[0].trade, trigger_family="FVG_RETRACE_CISD"),
    )
    result = run_sensorized_master_frame_paper(
        barriers=(_a1_multi_hypothesis_fixture(T, source_ids=ids),),
        source_evidence=snapshots,
        source_originals=(changed, *originals[1:]),
        baseline_selected_source_ids=ids,
    )
    assert result.source_cisd_identity_conflicts == 1
    assert result.report.paper_selected == 3


def test_future_m1_or_missing_original_sensor_fails_before_cognition() -> None:
    originals, snapshots = _inputs()
    ids = tuple(row.source_opportunity_id for row in originals)
    barrier = _a1_multi_hypothesis_fixture(T, source_ids=ids)
    with pytest.raises(ValueError, match="original source IDs"):
        run_sensorized_master_frame_paper(
            barriers=(barrier,), source_evidence={
                key: value for key, value in snapshots.items() if key != ids[0]
            }, source_originals=originals, baseline_selected_source_ids=ids,
        )
    future = replace(_bars("AUDJPY")[-1], closed_at=T+timedelta(minutes=1))
    with pytest.raises(ValueError, match="future/inflight"):
        run_sensorized_master_frame_paper(
            barriers=(barrier,), source_evidence={
                **snapshots, ids[0]: replace(
                    snapshots[ids[0]], m1_bars=(*_bars("AUDJPY")[:-1], future),
                ),
            }, source_originals=originals, baseline_selected_source_ids=ids,
        )
