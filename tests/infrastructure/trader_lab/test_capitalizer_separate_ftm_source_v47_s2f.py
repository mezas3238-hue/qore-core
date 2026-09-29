from __future__ import annotations

from qore.infrastructure.trader_lab import (
    capitalizer_ftm_raw_population_v47_s1r_c as raw,
)
from qore.infrastructure.trader_lab import (
    capitalizer_separate_ftm_source_v47_s2f as s2f,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerSourceDirection,
)


def test_ftm_taken_side_maps_to_continuation_not_reversal() -> None:
    assert s2f._continuation_side(raw.FTMTakenSide.HIGH) is CapitalizerSide.LONG
    assert s2f._continuation_side(raw.FTMTakenSide.LOW) is CapitalizerSide.SHORT
    assert (
        s2f._expected_reversal_direction(raw.FTMTakenSide.HIGH)
        is CapitalizerSourceDirection.BEARISH
    )
    assert (
        s2f._expected_reversal_direction(raw.FTMTakenSide.LOW)
        is CapitalizerSourceDirection.BULLISH
    )


def test_s2f_report_requires_monotone_full_prefill_funnel() -> None:
    try:
        s2f.S2FPeriodMarketReport(
            identity=s2f.IDENTITY,
            period="development",
            symbol="EURUSD",
            session="LONDON",
            operating_days_scanned=1,
            raw_sweeps=1,
            htf_continuation_aligned=2,
            continuation_m3_mss=0,
            continuation_m15=0,
            continuation_m1=0,
            ftm_confirmed=0,
            target_bound=0,
            armed_ftm_candidates=0,
            forensic_rejections={},
        )
    except ValueError as exc:
        assert "funnel monotonicity" in str(exc)
    else:
        raise AssertionError("non-monotone S2F funnel must fail closed")


def test_s2f_identity_is_separate_from_reversal_stream() -> None:
    assert s2f.IDENTITY == "QORE_CAPITALIZER_SEPARATE_FTM_SOURCE_STREAM_V47_S2F"
    assert s2f.PREDECLARATION_COMMENT_ID == 5900576271
