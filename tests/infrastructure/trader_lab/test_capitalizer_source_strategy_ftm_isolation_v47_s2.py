from __future__ import annotations

from datetime import UTC, datetime

import pytest

from qore.infrastructure.trader_lab import (
    capitalizer_ftm_raw_population_v47_s1r_c as raw_ftm,
)
from qore.infrastructure.trader_lab import (
    capitalizer_source_strategy_ftm_isolation_v47_s2 as ftm,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerSourceDirection,
)


def test_ftm_taken_side_maps_to_continuation_not_reversal() -> None:
    assert (
        ftm._continuation_direction(raw_ftm.FTMTakenSide.HIGH)
        is CapitalizerSourceDirection.BULLISH
    )
    assert (
        ftm._expected_direction(raw_ftm.FTMTakenSide.HIGH)
        is CapitalizerSourceDirection.BEARISH
    )
    assert (
        ftm._continuation_direction(raw_ftm.FTMTakenSide.LOW)
        is CapitalizerSourceDirection.BEARISH
    )
    assert (
        ftm._expected_direction(raw_ftm.FTMTakenSide.LOW)
        is CapitalizerSourceDirection.BULLISH
    )
    assert ftm._side(CapitalizerSourceDirection.BULLISH) is CapitalizerSide.LONG
    assert ftm._side(CapitalizerSourceDirection.BEARISH) is CapitalizerSide.SHORT


def test_ftm_report_enforces_monotone_pre_economic_funnel() -> None:
    with pytest.raises(ValueError, match="funnel monotonicity"):
        ftm.FTMPeriodMarketReport(
            identity=ftm.IDENTITY,
            period="development",
            symbol="EURUSD",
            session="LONDON",
            raw_sweeps=10,
            continuation_first=5,
            continuation_binding=6,
            continuation_m3=0,
            continuation_m3_fvg=0,
            independent_m1=0,
            unambiguous_target=0,
            routed_ftm=0,
            exact_fills=0,
            v46_rejected_after_fill=0,
            admitted_exact_fills=0,
            provider_tick_requests=0,
        )


def test_ftm_admitted_row_cannot_carry_fractal_route() -> None:
    with pytest.raises(ValueError, match="route drift"):
        ftm.FTMAdmittedFillRow(
            identity=ftm.IDENTITY,
            period="development",
            symbol="EURUSD",
            session="LONDON",
            operating_date="2026-01-02",
            side="LONG",
            route="FRACTAL_SCALP_CONTINUATION",
            sweep_at=datetime(2026, 1, 2, 8, 0, tzinfo=UTC).isoformat(),
            continuation_cisd_at=datetime(2026, 1, 2, 8, 5, tzinfo=UTC).isoformat(),
            continuation_m3_mss_at=datetime(2026, 1, 2, 8, 8, tzinfo=UTC).isoformat(),
            armed_at=datetime(2026, 1, 2, 8, 12, tzinfo=UTC).isoformat(),
            entry_at=datetime(2026, 1, 2, 8, 13, tzinfo=UTC).isoformat(),
            entry_price="1.1000",
            armed_level_used="1.1000",
            entry_mode="FVG_CE_50",
            stop_price="1.0990",
            target_price="1.1030",
            target_kind="HIGHER_TIMEFRAME_STRUCTURAL_OBJECTIVE",
            provider_tick_count=3,
            provider_request_count=1,
        )


def test_ftm_funnel_identity_constants_are_frozen() -> None:
    assert ftm.PREDECLARATION_COMMENT_ID == 5901844217
    assert ftm.SOURCE_M1_RUN_ID == 35548099334
    assert ftm.SOURCE_M1_SHA == "18c338aedd5013ce65a6cb6408ffbc2e904a6217"
    assert set(ftm.PERIODS) == {"reserved", "validation", "development"}
