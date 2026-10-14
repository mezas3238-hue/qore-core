"""M0-M3 source-certified *context*, never trader or economic certification."""
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
from scripts.vt31_ttrades_am_cognitive_fidelity_witness_20261014 import (
    assess_ttrades_am_context,
    ict_2023_profile_scope,
)

NY = ZoneInfo("America/New_York")
DAY = datetime(2025, 7, 1, tzinfo=NY)
START9 = DAY.replace(hour=9)
START10 = DAY.replace(hour=10)


def candle(
    minute: int, *, hour: int,
    o: str = "100", h: str = "102", lo: str = "98", c: str = "100",
) -> M1Bar:
    stamp = (START9 if hour == 9 else START10).astimezone(UTC)
    stamp += timedelta(minutes=minute)
    return M1Bar(
        stamp, stamp+timedelta(minutes=1),
        Decimal(o), Decimal(h), Decimal(lo), Decimal(c),
    )


def fixtures() -> tuple[tuple[M1Bar, ...], tuple[M1Bar, ...], CognitiveDecision]:
    hour9 = [candle(i, hour=9) for i in range(60)]
    hour9[10] = candle(10, hour=9, h="110")
    hour9[20] = candle(20, hour=9, lo="90")
    ten = [
        candle(0, hour=10),
        candle(1, hour=10, o="96", h="99", lo="89", c="95"),
        candle(2, hour=10, o="94", h="100", lo="93", c="98"),
        candle(3, hour=10, o="98", h="101", lo="97", c="99"),
    ]
    mss = ten[2].closed_at
    dto = CognitiveDecision(
        session=SessionId.NY_AM, side=Side.LONG,
        observed_at=ten[-1].closed_at,
        draw_target=Decimal("110"),
        draw_family="TTRADES_NY_AM_9AM_H1_OPPOSITE",
        draw_level_observed_at=hour9[-1].closed_at,
        structure_level=Decimal("97"),
        structure_level_confirmed_at=hour9[55].closed_at,
        structure_break_confirmed_at=mss,
        source_provenance="SYNTHETIC_ASOF_CONTEXT_NO_TRADES",
        cognitive_version="METHOD_SOURCE_CERT_V0",
        mss_anchor_close=ten[2].close,
        framework_policy=G3_MSS_FRAMEWORK_POLICY,
    )
    return tuple(hour9), tuple(ten), dto


def check(
    h9: tuple[M1Bar, ...], ten: tuple[M1Bar, ...], dto: CognitiveDecision,
):
    return assess_ttrades_am_context(
        cognition=dto, previous_ny_9am=h9, current_ny_10am=ten,
    )


def test_am_happy_context_but_never_certified_as_trader() -> None:
    h9, ten, dto = fixtures()
    result = check(h9, ten, dto)
    assert result.status == "CONTEXT_CONFORMANT_ONLY", result.reason_codes
    assert not result.reason_codes
    assert result.first_sweep_closed_at == ten[1].closed_at
    assert result.mss_closed_at == ten[2].closed_at
    assert result.reference_high == Decimal("110")
    assert result.reference_low == Decimal("90")
    assert result.target_expected == Decimal("110")
    assert not result.methodology_certified
    assert not result.cognitive_certified
    assert not result.execution_authorized
    d = result.to_public_record()
    assert d["first_sweep_closed_at"].endswith("+00:00")


def test_missing_9am_h1_can_never_be_invented() -> None:
    h9, ten, dto = fixtures()
    r = check(h9[1:], ten, dto)
    assert "H1_09_10_NOT_COMPLETE" in r.reason_codes
    assert r.status == "REJECTED"


def test_missing_10am_prefix_or_stale_cog_rejected() -> None:
    h9, ten, dto = fixtures()
    r = check(h9, ten[:-1], dto)
    assert "COG_AS_OF_NOT_LAST_CLOSED_M1" in r.reason_codes
    ten_bad = ten[:2] + (replace(ten[2],
        opened_at=ten[2].opened_at + timedelta(minutes=1),
        closed_at=ten[2].closed_at + timedelta(minutes=1)),) + ten[3:]
    assert "M1_10AM_PREFIX_GAPPED_OR_MISSING" in check(
        h9, ten_bad, dto,
    ).reason_codes


def test_absent_raid_veto() -> None:
    h9, ten, dto = fixtures()
    fixed = ten[:1] + (candle(1, hour=10),) + ten[2:]
    r = check(h9, fixed, dto)
    assert "NO_PRE_SIGNAL_9AM_H1_SWEEP" in r.reason_codes


def test_high_raid_cannot_authorize_long_and_high_low_same_candle_unknown() -> None:
    h9, ten, dto = fixtures()
    wrong = ten[:1] + (candle(
        1, hour=10, o="101", h="111", lo="99", c="105",
    ),) + ten[2:]
    assert "SWEEP_DIRECTION_CONTRADICTS_COG" in check(
        h9, wrong, dto,
    ).reason_codes
    both = ten[:1] + (candle(
        1, hour=10, o="100", h="111", lo="89", c="100",
    ),) + ten[2:]
    assert "BOTH_H1_SIDES_SWEPT_UNKNOWN_INTRABAR_ORDER" in check(
        h9, both, dto,
    ).reason_codes


def test_opposite_raid_after_first_sweep_revokes_approval() -> None:
    h9, ten, dto = fixtures()
    later = ten[:-1] + (candle(
        3, hour=10, o="99", h="111", lo="98", c="100",
    ),)
    r = check(h9, later, dto)
    assert "OPPOSITE_H1_RAID_AFTER_FIRST_SWEEP" in r.reason_codes


def test_mss_before_raid_or_not_observed_never_passes() -> None:
    h9, ten, dto = fixtures()
    early = replace(dto, structure_break_confirmed_at=ten[0].closed_at)
    assert "MSS_NOT_AFTER_SWEEP" in check(h9, ten, early).reason_codes
    backdated = replace(
        dto, structure_break_confirmed_at=h9[58].closed_at,
    )
    assert "MSS_NOT_OBSERVED_IN_CURRENT_NY_AM_M1" in check(
        h9, ten, backdated,
    ).reason_codes


def test_mss_not_displaced_back_inside_hour_is_vetoed() -> None:
    h9, ten, dto = fixtures()
    outside = ten[:2] + (candle(
        2, hour=10, o="94", h="100", lo="88", c="89",
    ),) + ten[3:]
    assert "MSS_DISPLACEMENT_NOT_BACK_INSIDE_9AM_H1" in check(
        h9, outside, dto,
    ).reason_codes


def test_closest_previous_session_dol_is_not_ttrades_9am_opposite() -> None:
    h9, ten, dto = fixtures()
    # Characterization of the real cleanroom producer's prior-NY pool family:
    old = replace(
        dto, draw_family="PRIOR_NY_CASH_SESSION_HIGH",
        draw_target=Decimal("150"),
    )
    r = check(h9, ten, old)
    assert "DOL_NOT_OPPOSITE_9AM_H1_EXTREME" in r.reason_codes
    assert r.target_expected == Decimal("110")


def test_incorrect_clock_profile_and_9am_not_universal_ict_rule() -> None:
    h9, ten, dto = fixtures()
    london = replace(dto, session=SessionId.LONDON)
    assert "WRONG_METHOD_PROFILE_SESSION" in check(
        h9, ten, london,
    ).reason_codes
    result = ict_2023_profile_scope(SessionId.LONDON)
    assert result["allowed_session"]
    assert result["9am_H1_raid_universal_required"] is False
    assert result["methodology_certified"] is False
    assert result["order_authority"] is False


def test_fail_closed_no_future_quote_not_even_if_dto_claims_it() -> None:
    h9, ten, dto = fixtures()
    future = ten + (candle(4, hour=10),)
    assert "COG_AS_OF_NOT_LAST_CLOSED_M1" in check(
        h9, future, dto,
    ).reason_codes
    assert "FUTURE_M1_IN_SOURCE" in check(h9, future, dto).reason_codes


@pytest.mark.parametrize("side", [Side.LONG, Side.SHORT])
def test_all_context_certificates_only_research_no_live(side: Side) -> None:
    h9, ten, dto = fixtures()
    r = check(h9, ten, replace(dto, side=side))
    assert not r.execution_authorized
    assert not r.methodology_certified
    assert not r.cognitive_certified
