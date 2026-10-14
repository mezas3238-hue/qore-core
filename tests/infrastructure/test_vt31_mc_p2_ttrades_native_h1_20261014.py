"""Native M1 source facts vs COG_EVIDENCE_V2, not broker/trader authorization."""
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
from scripts.vt31_mc_p2_ttrades_native_h1_evidence_20261014 import (
    compare_native_with_existing_cog,
    native_ttrades_am_context,
)

NY = ZoneInfo("America/New_York")


def bar(
    stamp: datetime, *, o: str = "100", h: str = "102",
    lo: str = "98", c: str = "101",
) -> M1Bar:
    return M1Bar(
        stamp, stamp + timedelta(minutes=1),
        Decimal(o), Decimal(h), Decimal(lo), Decimal(c),
    )


def fixture(
    *, date: tuple[int, int, int] = (2025, 7, 1),
    side: Side = Side.LONG,
) -> tuple[tuple[M1Bar, ...], tuple[M1Bar, ...], CognitiveDecision]:
    y, m, d = date
    begin9 = datetime(y, m, d, 9, tzinfo=NY).astimezone(UTC)
    begin10 = datetime(y, m, d, 10, tzinfo=NY).astimezone(UTC)
    h9 = [bar(begin9+timedelta(minutes=i)) for i in range(60)]
    h9[10] = bar(begin9+timedelta(minutes=10), h="110")
    h9[20] = bar(begin9+timedelta(minutes=20), lo="90")
    if side is Side.LONG:
        h9[57] = bar(begin9+timedelta(minutes=57), h="104")
        h10 = [
            bar(begin10, o="100", c="100"),
            bar(begin10+timedelta(minutes=1), o="96", h="99", lo="89", c="95"),
            bar(begin10+timedelta(minutes=2), o="94", h="106", lo="93", c="105"),
            bar(begin10+timedelta(minutes=3), o="105", h="107", lo="104", c="106"),
        ]
        pivot, target = "104", "110"
    else:
        h9[57] = bar(begin9+timedelta(minutes=57), lo="96")
        h10 = [
            bar(begin10, o="100", c="100"),
            bar(begin10+timedelta(minutes=1), o="104", h="111", lo="103", c="105"),
            bar(begin10+timedelta(minutes=2), o="106", h="107", lo="94", c="95"),
            bar(begin10+timedelta(minutes=3), o="95", h="96", lo="93", c="94"),
        ]
        pivot, target = "96", "90"
    cog = CognitiveDecision(
        session=SessionId.NY_AM, side=side, observed_at=h10[-1].closed_at,
        draw_target=Decimal(target), draw_family="TTRADES_09H_OPPOSITE",
        draw_level_observed_at=h9[-1].closed_at,
        structure_level=Decimal(pivot),
        structure_level_confirmed_at=h9[58].closed_at,
        structure_break_confirmed_at=h10[2].closed_at,
        source_provenance="SYNTHETIC_POSITIVE_TEST_NOT_TRADER",
        cognitive_version="QORE_SOURCE_ONLY_SYNTHETIC",
        mss_anchor_close=h10[2].close,
        framework_policy=G3_MSS_FRAMEWORK_POLICY,
    )
    return tuple(h9), tuple(h10), cog


def check(
    nine: tuple[M1Bar, ...], ten: tuple[M1Bar, ...],
    *, at: datetime | None = None, session: SessionId = SessionId.NY_AM,
):
    return native_ttrades_am_context(
        as_of=at or ten[-1].closed_at,
        nine=nine, ten=ten, session=session,
    )


@pytest.mark.parametrize("side", [Side.LONG, Side.SHORT])
@pytest.mark.parametrize("date,offset", [
    ((2025, 7, 1), -4),
    ((2025, 1, 15), -5),
])
def test_native_9am_h1_raid_return_opposite_target_by_dst(date, offset, side):
    nine, ten, dto = fixture(date=date, side=side)
    evidence = check(nine, ten)
    assert evidence.state == "RETURN_INSIDE_OBSERVED"
    assert evidence.first_sweep_side == ("LOW" if side is Side.LONG else "HIGH")
    assert evidence.first_sweep_at == ten[1].closed_at
    assert evidence.return_inside_at == ten[2].closed_at
    assert evidence.opposite_h1_dol == Decimal(
        "110" if side is Side.LONG else "90"
    )
    assert evidence.candidate_side == side.value
    assert evidence.high_9am == Decimal("110")
    assert evidence.low_9am == Decimal("90")
    assert int(ten[-1].opened_at.astimezone(NY).utcoffset().total_seconds()/3600) == offset
    assert evidence.record()["method_certified"] is False
    assert not evidence.cognition_certified and not evidence.execution_authorized
    assert dto.structure_break_confirmed_at == evidence.return_inside_at


def test_first_sweep_same_candle_return_not_certified():
    nine, ten, _ = fixture()
    s = check(nine, ten[:2])
    assert s.state == "AWAIT_RETURN"
    assert s.first_sweep_at == ten[1].closed_at
    assert s.return_inside_at is None


def test_no_raid_means_await_not_generated_trade():
    nine, ten, _ = fixture()
    no_raid = (ten[0], bar(ten[1].opened_at), ten[2], ten[3])
    s = check(nine, no_raid)
    assert s.state == "AWAIT_SWEEP"
    assert s.candidate_side is None and s.opposite_h1_dol is None


def test_double_sweep_same_m1_unknown_order_cannot_choose_winner():
    nine, ten, _ = fixture()
    both = list(ten)
    both[1] = bar(ten[1].opened_at, o="100", h="111", lo="89", c="100")
    s = check(nine, tuple(both))
    assert s.state == "UNKNOWN"
    assert "BOTH_H1_SIDES_SWEPT_UNKNOWN_INTRABAR_ORDER" in s.reasons
    assert s.return_inside_at is None


def test_opposite_raid_later_never_relabels_first_sweep():
    nine, ten, _ = fixture()
    crossed = ten + (bar(
        ten[-1].closed_at, o="106", h="111", lo="100", c="107",
    ),)
    s = check(nine, crossed)
    assert s.state == "REJECTED"
    assert s.first_sweep_side == "LOW"
    assert s.candidate_side == "LONG"
    assert "OPPOSITE_H1_RAID_AFTER_FIRST_SWEEP" in s.reasons


def test_repeated_raid_same_side_does_not_restart_first_timestamp():
    nine, ten, _ = fixture()
    second = ten + (bar(
        ten[-1].closed_at, o="106", h="107", lo="89", c="106",
    ),)
    s = check(nine, second)
    assert s.state == "RETURN_INSIDE_OBSERVED"
    assert s.first_sweep_at == ten[1].closed_at


def test_incomplete_or_gapped_h1_is_unknown():
    nine, ten, _ = fixture()
    assert check(nine[1:], ten).state == "UNKNOWN"
    assert "H1_09_10_INCOMPLETE" in check(nine[1:], ten).reasons
    assert check(nine[:12] + nine[13:], ten).state == "UNKNOWN"


def test_gapped_10_m1_unknown_without_imputation():
    nine, ten, _ = fixture()
    s = check(nine, ten[:1] + ten[2:])
    assert s.state == "UNKNOWN"
    assert "TEN_AM_CLOSED_M1_GAP_OR_MISSING" in s.reasons


def test_future_or_backdated_asof_cannot_be_treated_as_observed():
    nine, ten, _ = fixture()
    s = check(nine, ten, at=ten[2].closed_at)
    assert s.state == "REJECTED"
    assert "FUTURE_OR_STALE_ASOF_M1" in s.reasons
    s2 = check(nine, ten, at=ten[-1].closed_at+timedelta(minutes=1))
    assert s2.state == "REJECTED"
    assert "FUTURE_OR_STALE_ASOF_M1" in s2.reasons


def test_out_of_window_and_london_profile_refused():
    nine, ten, _ = fixture()
    assert check(nine, ten, session=SessionId.LONDON).state == "REJECTED"
    assert check(
        nine, ten, at=ten[-1].closed_at+timedelta(hours=2),
    ).state == "REJECTED"


@pytest.mark.parametrize("side", [Side.LONG, Side.SHORT])
def test_native_context_plus_v2_synthetic_cog_contract_context_only(side):
    nine, ten, cog = fixture(side=side)
    native = check(nine, ten)
    full_history = nine + ten
    result = compare_native_with_existing_cog(
        native=native, cognition=cog, history=full_history,
    )
    assert result.state == "CONTEXT_ATTESTED_NOT_CERTIFIED", result
    assert result.v2_state == "CONFIRMED"
    assert result.reasons == ()
    assert not result.method_certified and not result.cognition_certified
    assert not result.execution_authorized


def test_native_context_without_cog_cannot_mint_cognition():
    nine, ten, _ = fixture()
    result = compare_native_with_existing_cog(
        native=check(nine, ten), cognition=None, history=nine+ten,
    )
    assert result.state == "COG_NOT_PRESENT"


def test_wrong_cog_dol_is_rejected_before_any_certification():
    nine, ten, cog = fixture()
    false = replace(cog, draw_target=Decimal("150"))
    result = compare_native_with_existing_cog(
        native=check(nine, ten), cognition=false, history=nine+ten,
    )
    assert result.state == "REJECTED"
    assert "COG_DOL_NOT_PRIOR_H1_OPPOSITE" in result.reasons


def test_wrong_cog_direction_or_time_never_forces_pass():
    nine, ten, cog = fixture()
    short = replace(cog, side=Side.SHORT)
    result = compare_native_with_existing_cog(
        native=check(nine, ten), cognition=short, history=nine+ten,
    )
    assert result.state == "REJECTED"
    assert "COG_DIRECTION_OPPOSES_FIRST_RAID" in result.reasons
    early = replace(cog, structure_break_confirmed_at=ten[1].closed_at)
    assert "COG_MSS_NOT_AFTER_SOURCE_RAID" in compare_native_with_existing_cog(
        native=check(nine, ten), cognition=early, history=nine+ten,
    ).reasons


def test_forced_context_does_not_match_tampered_source_market():
    nine, ten, cog = fixture()
    alter = list(nine)
    alter[10] = bar(nine[10].opened_at, h="120")
    outcome = compare_native_with_existing_cog(
        native=check(nine, ten), cognition=cog, history=tuple(alter)+ten,
    )
    assert outcome.state == "REJECTED"
    assert "NATIVE_AND_COG_M1_SOURCE_INCONSISTENT" in outcome.reasons


def test_no_9am_rule_applies_to_ict_london_or_nypm():
    from scripts.vt31_ttrades_am_cognitive_fidelity_witness_20261014 import (
        ict_2023_profile_scope,
    )

    for session in (SessionId.LONDON, SessionId.NY_PM):
        d = ict_2023_profile_scope(session)
        assert d["9am_H1_raid_universal_required"] is False


def test_native_ttrades_is_never_true_method_or_live_certificate_even_at_11():
    nine, ten, _ = fixture()
    expanded = ten + tuple(
        bar(ten[-1].closed_at+timedelta(minutes=i))
        for i in range(56)
    )
    s = check(nine, expanded)
    assert s.as_of.astimezone(NY).hour == 11
    assert s.state == "RETURN_INSIDE_OBSERVED"
    assert not s.method_certified and not s.execution_authorized
