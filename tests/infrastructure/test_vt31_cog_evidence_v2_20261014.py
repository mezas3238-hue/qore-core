"""Adversarial source-proof attestations for VT31 COG_EVIDENCE_V2."""
from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import (
    G3_MSS_FRAMEWORK_POLICY,
    CognitiveDecision,
    M1Bar,
    SessionId,
    Side,
)
from scripts.vt31_cog_evidence_v2_20261014 import (
    ICT_GENERAL,
    TTRADES_AM,
    inspect_cog_evidence,
)

NY = ZoneInfo("America/New_York")
START9 = datetime(2025, 7, 1, 9, tzinfo=NY).astimezone(UTC)
START10 = datetime(2025, 7, 1, 10, tzinfo=NY).astimezone(UTC)


def bar(
    at: datetime, *, o="100", h="102", lo="98", c="101",
) -> M1Bar:
    return M1Bar(
        at, at + timedelta(minutes=1),
        Decimal(o), Decimal(h), Decimal(lo), Decimal(c),
    )


def data(
    side: Side = Side.LONG,
) -> tuple[tuple[M1Bar, ...], CognitiveDecision]:
    nine = [bar(START9+timedelta(minutes=i)) for i in range(60)]
    nine[10] = bar(START9+timedelta(minutes=10), h="110")
    nine[20] = bar(START9+timedelta(minutes=20), lo="90")
    if side is Side.LONG:
        nine[57] = bar(START9+timedelta(minutes=57), h="104")
        ten = [
            bar(START10, o="100", c="100"),
            bar(START10+timedelta(minutes=1), o="96", h="99", lo="89", c="95"),
            bar(START10+timedelta(minutes=2), o="94", h="106", lo="93", c="105"),
            bar(START10+timedelta(minutes=3), o="105", h="107", lo="104", c="106"),
        ]
        level, target = "104", "110"
    else:
        nine[57] = bar(START9+timedelta(minutes=57), lo="96")
        ten = [
            bar(START10, o="100", c="100"),
            bar(START10+timedelta(minutes=1), o="104", h="111", lo="103", c="105"),
            bar(START10+timedelta(minutes=2), o="106", h="107", lo="94", c="95"),
            bar(START10+timedelta(minutes=3), o="95", h="96", lo="93", c="94"),
        ]
        level, target = "96", "90"
    bars = tuple(nine + ten)
    dto = CognitiveDecision(
        session=SessionId.NY_AM,
        side=side,
        observed_at=ten[-1].closed_at,
        draw_target=Decimal(target),
        draw_family="TTRADES_09H_OPPOSITE_EXTREME_QORE_PROFILE",
        draw_level_observed_at=nine[-1].closed_at,
        structure_level=Decimal(level),
        structure_level_confirmed_at=nine[58].closed_at,
        structure_break_confirmed_at=ten[2].closed_at,
        source_provenance="M1_SYNTHETIC_VALIDATION_NOT_ORDER",
        cognitive_version="COG_EVIDENCE_V2_TEST_ONLY",
        mss_anchor_close=ten[2].close,
        framework_policy=G3_MSS_FRAMEWORK_POLICY,
    )
    return bars, dto


def inspect(
    bars: tuple[M1Bar, ...], dto: CognitiveDecision | None,
    profile: str = TTRADES_AM,
):
    return inspect_cog_evidence(
        profile=profile, session=SessionId.NY_AM,
        as_of=bars[-1].closed_at, history=bars, cognition=dto,
    )


@pytest.mark.parametrize("side", [Side.LONG, Side.SHORT])
def test_attests_independent_original_mss_pivot_and_target_no_trade(side):
    bars, dto = data(side)
    out = inspect(bars, dto)
    assert out.state == "CONFIRMED", out.record()
    assert out.observed_mss_close == dto.mss_anchor_close
    assert out.observed_pivot_level == dto.structure_level
    assert out.observed_mss_at == dto.structure_break_confirmed_at
    assert out.observed_pivot_confirmed_at == dto.structure_level_confirmed_at
    assert out.context["status"] == "CONTEXT_CONFORMANT_ONLY"
    assert not out.rejected and not out.unknown
    assert not out.method_certified and not out.cognition_certified
    assert not out.live_authorized
    assert out.record()["observed_mss_close"] == str(dto.mss_anchor_close)


def test_false_mss_close_assertion_is_rejected_against_actual_m1():
    bars, dto = data()
    false = replace(dto, mss_anchor_close=Decimal("103"))
    out = inspect(bars, false)
    assert out.state == "REJECTED"
    assert "MSS_ANCHOR_CLOSE_MISMATCH_WITH_M1" in out.rejected


def test_later_revalidation_checks_original_mss_not_last_m1():
    bars, dto = data()
    assert bars[-1].close != dto.mss_anchor_close
    assert inspect(bars, dto).state == "CONFIRMED"


def test_tampered_pivot_price_rejected_even_when_mss_close_matches():
    bars, dto = data()
    out = inspect(bars, replace(dto, structure_level=Decimal("103")))
    assert out.state == "REJECTED"
    assert "PIVOT_LEVEL_OR_CONFIRMATION_INCONSISTENT" in out.rejected


def test_pivot_timestamp_tampered_fails_closed_with_unknown():
    bars, dto = data()
    wrong = replace(dto, structure_level_confirmed_at=bars[56].closed_at)
    out = inspect(bars, wrong)
    assert out.state in ("REJECTED", "UNKNOWN")
    assert "PIVOT_LEVEL_OR_CONFIRMATION_INCONSISTENT" in out.rejected or (
        "PIVOT_CONFIRMATION_M1_NOT_IN_MSS_LOOKBACK" in out.unknown
    )


def test_mss_did_not_cross_claimed_level_rejected():
    bars, dto = data()
    altered = list(bars)
    altered[-2] = bar(START10+timedelta(minutes=2),
                      o="94", h="106", lo="93", c="104")
    out = inspect(tuple(altered), dto)
    assert "MSS_LEVEL_CROSSING_INCONSISTENT_WITH_M1" in out.rejected


def test_mss_body_below_qore_reference_rejected():
    bars, dto = data()
    altered = list(bars)
    altered[-2] = bar(START10+timedelta(minutes=2),
                      o="104.5", h="106", lo="93", c="105")
    out = inspect(tuple(altered), dto)
    assert "MSS_IMPULSE_UNDER_QORE_1P25_MEDIAN5" in out.rejected


def test_h1_missing_unknown_not_automatically_no_raid():
    bars, dto = data()
    out = inspect(bars[1:], dto)
    assert out.state == "UNKNOWN"
    assert "H1_09_10_NOT_COMPLETE" in out.unknown


def test_double_extreme_sweep_in_one_m1_unknown_not_false_pass():
    bars, dto = data()
    altered = list(bars)
    altered[61] = bar(START10+timedelta(minutes=1),
                      o="99", h="111", lo="89", c="99")
    out = inspect(tuple(altered), dto)
    assert out.state == "UNKNOWN"
    assert "BOTH_H1_SIDES_SWEPT_UNKNOWN_INTRABAR_ORDER" in out.unknown


def test_nonmatching_target_rejected_only_for_ttrades_profile():
    bars, dto = data()
    strange = replace(dto, draw_target=Decimal("150"))
    assert "DOL_NOT_OPPOSITE_9AM_H1_EXTREME" in inspect(
        bars, strange,
    ).rejected
    general = inspect(bars, strange, ICT_GENERAL)
    assert general.state == "UNKNOWN"
    assert "ICT_EXTERNAL_DOL_PROVENANCE_UNVERIFIED" in general.unknown
    assert "DOL_NOT_OPPOSITE_9AM_H1_EXTREME" not in general.rejected


def test_no_cognitive_decision_is_unknown_not_rejected_or_confirmed():
    bars, _ = data()
    out = inspect(bars, None)
    assert out.state == "UNKNOWN"
    assert "NO_COG_DECISION_AT_AS_OF" in out.unknown


def test_external_as_of_differs_from_cognition_timestamp_rejected():
    bars, dto = data()
    out = inspect_cog_evidence(
        profile=TTRADES_AM, session=SessionId.NY_AM,
        as_of=bars[-2].closed_at, history=bars, cognition=dto,
    )
    assert out.state == "REJECTED"
    assert "COG_OBSERVED_AT_CONFLICT" in out.rejected
    assert "FUTURE_BAR_IN_COG_EVIDENCE_INPUT" in out.rejected


def test_nonmonotonic_duplicate_inputs_rejected():
    bars, dto = data()
    out = inspect(bars[:-1] + (bars[-2], bars[-1]), dto)
    assert out.state == "REJECTED"
    assert "NONMONOTONIC_M1_HISTORY" in out.rejected


def test_no_mss_bar_is_unknown_not_invented():
    bars, dto = data()
    trimmed = tuple(x for x in bars if x.closed_at != dto.structure_break_confirmed_at)
    out = inspect(trimmed, dto)
    assert out.state == "UNKNOWN"
    assert "MSS_BAR_NOT_OBSERVED_IN_HISTORY" in out.unknown


def test_general_london_never_requires_9am_range():
    start = datetime(2025, 7, 1, 3, tzinfo=NY).astimezone(UTC)
    history = tuple(bar(start+timedelta(minutes=i)) for i in range(4))
    out = inspect_cog_evidence(
        profile=ICT_GENERAL, session=SessionId.LONDON,
        as_of=history[-1].closed_at, history=history, cognition=None,
    )
    assert out.state == "UNKNOWN"
    assert "ICT_EXTERNAL_DOL_PROVENANCE_UNVERIFIED" in out.unknown
    assert "H1_09_10_NOT_COMPLETE" not in out.unknown
    assert "OUTSIDE_SELECTED_ICT_CLOSED_M1_WINDOW" not in out.rejected


def test_wrong_profile_and_bad_session_never_assumed():
    bars, dto = data()
    with pytest.raises(ValueError, match="explicit supported"):
        inspect(bars, dto, profile="PROFIT_OPTIMIZED")
    out = inspect_cog_evidence(
        profile=TTRADES_AM, session=SessionId.LONDON,
        as_of=bars[-1].closed_at, history=bars, cognition=dto,
    )
    assert out.state == "REJECTED"
    assert "TTRADES_AM_ONLY_NY_AM" in out.rejected
