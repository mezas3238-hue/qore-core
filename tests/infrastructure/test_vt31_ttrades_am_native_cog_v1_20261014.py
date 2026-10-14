"""Adversarial source-native TTrades proposal fixtures. No broker/PNL."""
from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import (
    M1Bar,
    SessionId,
    Side,
)
from scripts.vt31_cog_evidence_v2_20261014 import (
    TTRADES_AM,
    inspect_cog_evidence,
)
from scripts.vt31_mc_p2_ttrades_native_h1_evidence_20261014 import (
    native_ttrades_am_context,
)
from scripts.vt31_ttrades_am_native_cog_v1_20261014 import (
    COG_VERSION,
    TARGET_FAMILY,
    propose_ttrades_am_cognition,
)

NY = ZoneInfo("America/New_York")


def make_bar(
    at: datetime, *, o: str = "100", h: str = "102",
    lo: str = "98", c: str = "101",
) -> M1Bar:
    return M1Bar(
        at, at + timedelta(minutes=1),
        Decimal(o), Decimal(h), Decimal(lo), Decimal(c),
    )


def fixture(
    *, month: int = 7, side: Side = Side.LONG,
) -> tuple[tuple[M1Bar, ...], tuple[M1Bar, ...]]:
    day = 1 if month == 7 else 15
    start9 = datetime(2025, month, day, 9, tzinfo=NY).astimezone(UTC)
    start10 = datetime(2025, month, day, 10, tzinfo=NY).astimezone(UTC)
    nine = [make_bar(start9 + timedelta(minutes=i)) for i in range(60)]
    nine[10] = make_bar(start9 + timedelta(minutes=10), h="110")
    nine[20] = make_bar(start9 + timedelta(minutes=20), lo="90")
    if side is Side.LONG:
        nine[57] = make_bar(start9 + timedelta(minutes=57), h="104")
        ten = (
            make_bar(start10, o="100", c="100"),
            make_bar(start10 + timedelta(minutes=1), o="96", h="99",
                     lo="89", c="95"),
            make_bar(start10 + timedelta(minutes=2), o="94", h="106",
                     lo="93", c="105"),
            make_bar(start10 + timedelta(minutes=3), o="105", h="107",
                     lo="104", c="106"),
        )
    else:
        nine[57] = make_bar(start9 + timedelta(minutes=57), lo="96")
        ten = (
            make_bar(start10, o="100", c="100"),
            make_bar(start10 + timedelta(minutes=1), o="104", h="111",
                     lo="103", c="105"),
            make_bar(start10 + timedelta(minutes=2), o="106", h="107",
                     lo="94", c="95"),
            make_bar(start10 + timedelta(minutes=3), o="95", h="96",
                     lo="93", c="94"),
        )
    return tuple(nine), ten


def run(
    nine: tuple[M1Bar, ...], ten: tuple[M1Bar, ...],
    **kwargs: object,
):
    history = nine + ten
    return propose_ttrades_am_cognition(
        as_of=ten[-1].closed_at, history=history, **kwargs,
    )


@pytest.mark.parametrize("month,offset", [(1, -5), (7, -4)])
@pytest.mark.parametrize("side", [Side.LONG, Side.SHORT])
def test_new_producer_emits_native_source_validated_at_first_return(
    month, offset, side,
):
    nine, ten = fixture(month=month, side=side)
    result = run(nine, ten[:3])
    assert result.state == "CONTEXT_ATTESTED_NOT_CERTIFIED", result.record()
    assert result.native_state == "RETURN_INSIDE_OBSERVED"
    assert result.independent_v2_state == "CONFIRMED"
    dto = result.decision
    assert dto is not None
    assert dto.cognitive_version == COG_VERSION
    assert dto.draw_family == TARGET_FAMILY
    assert dto.side == side
    assert dto.draw_target == Decimal("110" if side is Side.LONG else "90")
    assert dto.structure_level == Decimal("104" if side is Side.LONG else "96")
    assert dto.structure_break_confirmed_at == ten[2].closed_at
    assert dto.mss_anchor_close == ten[2].close
    assert dto.draw_level_observed_at == nine[-1].closed_at
    assert int(dto.observed_at.astimezone(NY).utcoffset().total_seconds()/3600) == offset
    original = inspect_cog_evidence(
        profile=TTRADES_AM, session=SessionId.NY_AM,
        as_of=dto.observed_at, history=nine + ten[:3], cognition=dto,
    )
    assert original.state == "CONFIRMED"
    assert not result.method_certified and not result.cognition_certified
    assert not result.execution_authorized
    record = result.record()
    assert record["decision"]["draw_target"] == str(dto.draw_target)
    assert record["method_certified"] is False


def test_not_reissue_old_first_return_on_later_candle():
    nine, ten = fixture()
    result = run(nine, ten)
    assert result.state == "UNKNOWN"
    assert result.decision is None
    assert "RETURN_M1_NOT_FRESH_AT_ASOF" in result.reasons


def test_no_sweep_never_mints_dto():
    nine, ten = fixture()
    ten = ten[:1] + (make_bar(ten[1].opened_at),) + ten[2:3]
    result = run(nine, ten)
    assert result.state == "UNKNOWN"
    assert result.decision is None
    assert result.native_state == "AWAIT_SWEEP"


def test_single_candle_double_sweep_is_unknown_not_coinflip():
    nine, ten = fixture()
    both = make_bar(ten[1].opened_at, h="111", lo="89")
    result = run(nine, ten[:1] + (both,) + ten[2:3])
    assert result.state == "UNKNOWN"
    assert result.decision is None
    assert "BOTH_H1_SIDES_SWEPT_UNKNOWN_INTRABAR_ORDER" in result.reasons


def test_first_raid_candle_itself_not_accepted_as_closed_return():
    nine, ten = fixture()
    result = run(nine, ten[:2])
    assert result.state == "UNKNOWN"
    assert result.native_state == "AWAIT_RETURN"


def test_opposite_raid_after_first_cannot_be_relabeled():
    nine, ten = fixture()
    other = make_bar(
        ten[2].opened_at, o="94", h="111", lo="93", c="105",
    )
    result = run(nine, ten[:2] + (other,))
    assert result.state == "REJECTED"
    assert "OPPOSITE_H1_RAID_AFTER_FIRST_SWEEP" in result.reasons


def test_no_pivot_cross_at_return_means_no_proposal():
    nine, ten = fixture()
    not_broken = make_bar(
        ten[2].opened_at, o="94", h="103", lo="93", c="100",
    )
    result = run(nine, ten[:2] + (not_broken,))
    assert result.state == "UNKNOWN"
    assert "QORE_MSS_PROXY_NOT_CONFIRMED_ON_FIRST_RETURN" in result.reasons


def test_weak_displacement_does_not_generate_mss():
    nine, ten = fixture()
    weak = make_bar(
        ten[2].opened_at, o="104.5", h="106", lo="93", c="105",
    )
    result = run(nine, ten[:2] + (weak,))
    assert result.state == "UNKNOWN"
    assert result.decision is None
    assert "QORE_MSS_PROXY_NOT_CONFIRMED_ON_FIRST_RETURN" in result.reasons


def test_gapped_h1_unknown_no_imputation():
    nine, ten = fixture()
    result = run(nine[:22] + nine[23:], ten[:3])
    assert result.state == "UNKNOWN"
    assert result.decision is None
    assert result.native_state == "UNKNOWN"


def test_gapped_10am_m1_unknown_no_imputation():
    nine, ten = fixture()
    result = run(nine, ten[:1] + ten[2:3])
    assert result.state == "UNKNOWN"
    assert result.decision is None


def test_london_profile_cannot_inherit_ttrades_9am():
    nine, ten = fixture()
    result = run(nine, ten[:3], session=SessionId.LONDON)
    assert result.state == "REJECTED"
    assert result.decision is None


def test_future_duplicate_stale_or_nonmonotonic_input_cannot_mint_dto():
    nine, ten = fixture()
    source = nine + ten[:3]
    future = source + (make_bar(ten[3].opened_at),)
    assert propose_ttrades_am_cognition(
        as_of=ten[2].closed_at, history=future,
    ).state == "REJECTED"
    assert propose_ttrades_am_cognition(
        as_of=ten[2].closed_at, history=source[:10] + source[9:],
    ).state == "REJECTED"
    assert propose_ttrades_am_cognition(
        as_of=ten[2].closed_at, history=source[1:2] + source[:1] + source[2:],
    ).state == "REJECTED"
    assert propose_ttrades_am_cognition(
        as_of=ten[2].closed_at + timedelta(minutes=1), history=source,
    ).state == "UNKNOWN"


def test_wrong_dol_candidate_falsified_by_existing_independent_v2():
    nine, ten = fixture()
    result = run(nine, ten[:3])
    assert result.decision is not None
    forged = replace(result.decision, draw_target=Decimal("150"))
    v2 = inspect_cog_evidence(
        profile=TTRADES_AM, session=SessionId.NY_AM,
        as_of=forged.observed_at, history=nine + ten[:3], cognition=forged,
    )
    assert v2.state == "REJECTED"
    assert "DOL_NOT_OPPOSITE_9AM_H1_EXTREME" in v2.rejected


def test_source_native_witness_independent_of_new_producer():
    nine, ten = fixture()
    proof = native_ttrades_am_context(
        as_of=ten[2].closed_at, nine=nine, ten=ten[:3],
    )
    assert proof.state == "RETURN_INSIDE_OBSERVED"
    proposal = run(nine, ten[:3])
    assert proposal.decision is not None
    assert proposal.decision.draw_target == proof.opposite_h1_dol
    assert proposal.decision.side.value == proof.candidate_side
    assert proposal.state == "CONTEXT_ATTESTED_NOT_CERTIFIED"
