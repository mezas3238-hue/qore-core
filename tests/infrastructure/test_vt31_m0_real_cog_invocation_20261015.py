"""Audit actual original COG calls, not optimistic route labels in M0."""
from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import (
    NEW_YORK,
    SessionId,
    Side,
)
from scripts.vt31_cog_evidence_v2_20261014 import TTRADES_AM
from scripts.vt31_m0_predecision_method_router_20261015 import (
    PREDECLARED,
    route_preselected_method,
    source_identity_court,
)
from scripts.vt31_ttrades_source_first_g3_cognitive_proposal_20261015 import (
    MIN10_CONFLICT,
    SUCCESS,
    ttrades_fixture,
    ttrades_source_first_g3_cognitive_proposal,
)


@pytest.mark.parametrize("month", [1, 7])
def test_partial_nine_hour_wait_did_not_invoke_cog(month):
    bars, at = ttrades_fixture(
        side=Side.LONG, month=month, min10_valid=True,
    )
    day = at.astimezone(NEW_YORK).date()
    missing = tuple(
        b for b in bars
        if not (
            b.opened_at.astimezone(NEW_YORK).date() == day
            and b.opened_at.astimezone(NEW_YORK).hour == 9
            and b.opened_at.astimezone(NEW_YORK).minute == 17
        )
    )
    source = ttrades_source_first_g3_cognitive_proposal(
        profile=TTRADES_AM, session=SessionId.NY_AM,
        closed_m1=missing, as_of=at,
    )
    assert source.status == "TTRADES_SOURCE_NOT_CONFIRMED_WAIT"
    assert "H1_09_10_INCOMPLETE" in source.reason_codes
    assert not source.original_cog_invoked
    assert source.record()["original_cog_invoked"] is False
    route = route_preselected_method(
        policy=PREDECLARED, session=SessionId.NY_AM,
        closed_m1=missing, as_of=at,
    )
    assert route.state == source.status
    assert not route.original_cog_invoked
    assert route.original_cog_side is None
    assert not route.research_proposal_dto_only


@pytest.mark.parametrize("month", [1, 7])
def test_no_first_sweep_wait_did_not_invoke_original_cog(month):
    bars, at = ttrades_fixture(
        side=Side.SHORT, month=month, min10_valid=False,
    )
    # Neutralize the 10:01 sweep, preserve completed 09 H1 and 10:02.
    no_sweep = bars[:-2] + (
        replace(
            bars[-2], open=Decimal("100"), high=Decimal("102"),
            low=Decimal("98"), close=Decimal("100"),
        ),
        bars[-1],
    )
    source = ttrades_source_first_g3_cognitive_proposal(
        profile=TTRADES_AM, session=SessionId.NY_AM,
        closed_m1=no_sweep, as_of=at,
    )
    assert source.status == "TTRADES_SOURCE_NOT_CONFIRMED_WAIT"
    assert "NO_PRIOR_9AM_H1_RAID_YET" in source.reason_codes
    assert not source.original_cog_invoked
    route = route_preselected_method(
        policy=PREDECLARED, session=SessionId.NY_AM,
        closed_m1=no_sweep, as_of=at,
    )
    assert route.state == source.status
    assert not route.original_cog_invoked


@pytest.mark.parametrize("month", [1, 7])
def test_no_mss_can_still_have_real_original_cog_assessment(month):
    bars, at = ttrades_fixture(
        side=Side.SHORT, month=month, min10_valid=False,
    )
    # H1 sweep-return remains; alter only MSS confirmation close.
    no_mss = bars[:-1] + (replace(bars[-1], close=Decimal("98")),)
    source = ttrades_source_first_g3_cognitive_proposal(
        profile=TTRADES_AM, session=SessionId.NY_AM,
        closed_m1=no_mss, as_of=at,
    )
    assert source.status == "ORIGINAL_COG_MSS_NOT_CONFIRMED_WAIT"
    assert source.original_cog_invoked
    assert source.proposed is None
    route = route_preselected_method(
        policy=PREDECLARED, session=SessionId.NY_AM,
        closed_m1=no_mss, as_of=at,
    )
    assert route.original_cog_invoked
    assert route.original_cog_side is None


def test_original_16_cases_preserve_real_calls_and_source_statuses():
    cases = source_identity_court()["cases"]
    assert len(cases) == 16
    assert all(x["original_cog_invoked"] for x in cases)
    assert sum(x["state"] == SUCCESS for x in cases) == 4
    assert sum(x["state"] == MIN10_CONFLICT for x in cases) == 4
    assert sum(
        x["state"] == "ICT_CONTEXT_WITNESS_UNDERDETERMINED"
        for x in cases
    ) == 8
