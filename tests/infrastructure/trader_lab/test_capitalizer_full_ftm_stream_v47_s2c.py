from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.trader_lab import (
    capitalizer_full_ftm_stream_v47_s2c as s2c,
)
from qore.infrastructure.trader_lab import (
    capitalizer_source_strategy_isolation_v47_s2 as s2,
)
from qore.infrastructure.trader_lab.capitalizer_contract import CapitalizerSession
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_ftm_raw_population_v47_s1r_c import (
    FTMTakenSide,
)


def _row(at: str, symbol: str) -> s2c.S2CAdmittedFillRow:
    return s2c.S2CAdmittedFillRow(
        identity=s2c.IDENTITY,
        period="development",
        symbol=symbol,
        session="LONDON",
        operating_date="2026-01-05",
        side="LONG",
        route="FAILURE_TO_MANIPULATE_CONTINUATION",
        sweep_at="2026-01-05T07:00:00+00:00",
        continuation_confirmed_at="2026-01-05T07:10:00+00:00",
        armed_at="2026-01-05T07:15:00+00:00",
        entry_at=at,
        entry_price="100",
        armed_level_used="100",
        entry_mode="FVG_CE_50",
        stop_price="99",
        target_price="103",
        target_kind="HIGHER_TIMEFRAME_STRUCTURAL_OBJECTIVE",
        provider_tick_count=1,
        provider_request_count=1,
    )


def test_taken_side_maps_to_continuation_not_expected_reversal() -> None:
    assert s2c._continuation_side(FTMTakenSide.HIGH) is CapitalizerSide.LONG
    assert s2c._continuation_side(FTMTakenSide.LOW) is CapitalizerSide.SHORT


def test_s2c_max3_is_chronological_ceiling() -> None:
    rows = (
        _row("2026-01-05T08:03:00+00:00", "GBPUSD"),
        _row("2026-01-05T08:01:00+00:00", "EURUSD"),
        _row("2026-01-05T08:02:00+00:00", "EURUSD"),
        _row("2026-01-05T08:04:00+00:00", "GBPUSD"),
    )
    selected = s2c.select_max3(rows)
    assert len(selected) == 3
    assert [row.entry_at for row in selected] == [
        "2026-01-05T08:01:00+00:00",
        "2026-01-05T08:02:00+00:00",
        "2026-01-05T08:03:00+00:00",
    ]


def test_s2c_admitted_row_rejects_fractal_route() -> None:
    with pytest.raises(ValueError, match="route drift"):
        s2c.S2CAdmittedFillRow(
            identity=s2c.IDENTITY,
            period="development",
            symbol="EURUSD",
            session="LONDON",
            operating_date="2026-01-05",
            side="LONG",
            route="FRACTAL_SCALP_CONTINUATION",
            sweep_at="2026-01-05T07:00:00+00:00",
            continuation_confirmed_at="2026-01-05T07:10:00+00:00",
            armed_at="2026-01-05T07:15:00+00:00",
            entry_at="2026-01-05T07:20:00+00:00",
            entry_price="100",
            armed_level_used="100",
            entry_mode="FVG_CE_50",
            stop_price="99",
            target_price="103",
            target_kind="HIGHER_TIMEFRAME_STRUCTURAL_OBJECTIVE",
            provider_tick_count=1,
            provider_request_count=1,
        )


def test_report_requires_monotone_pre_economic_funnel() -> None:
    with pytest.raises(ValueError, match="funnel monotonicity drift"):
        s2c.S2CPeriodMarketReport(
            identity=s2c.IDENTITY,
            period="development",
            symbol="EURUSD",
            session="LONDON",
            raw_sweeps=1,
            htf_continuation_aligned=2,
            continuation_first=0,
            continuation_binding=0,
            ict_continuation_mss_fvg=0,
            independent_m1_bound=0,
            deterministic_target_bound=0,
            exact_fills=0,
            v46_rejected_after_fill=0,
            admitted_exact_fills=0,
            provider_tick_requests=0,
        )


def test_frozen_source_ids_are_not_economic_outputs() -> None:
    assert s2c.SOURCE_M1_RUN_ID == 35548099334
    assert s2c.PREDECLARATION_COMMENT_ID == 5901846384
    assert s2.IDENTITY == "QORE_CAPITALIZER_SOURCE_STRATEGY_ISOLATION_V47_S2"
