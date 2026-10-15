"""Original VT31 G3 MSS + explicit TTrades 09h-source cognitive proposal, no PnL."""
from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import (
    G3_MSS_FRAMEWORK_POLICY,
    SessionId,
    Side,
)
from scripts.vt31_cog_evidence_v2_20261014 import TTRADES_AM
from scripts.vt31_ttrades_source_first_g3_cognitive_proposal_20261015 import (
    MIN10_CONFLICT,
    NEW_RESEARCH_VERSION,
    SUCCESS,
    cognitive_profile_court,
    ttrades_fixture,
    ttrades_source_first_g3_cognitive_proposal,
)


@pytest.mark.parametrize("month", [1, 7])
@pytest.mark.parametrize("side", [Side.LONG, Side.SHORT])
def test_source_bound_ttrades_dol_can_be_versioned_when_g3_min10_compatible(
    month, side,
):
    rows, at = ttrades_fixture(side=side, month=month, min10_valid=True)
    response = ttrades_source_first_g3_cognitive_proposal(
        profile=TTRADES_AM, session=SessionId.NY_AM,
        as_of=at, closed_m1=rows,
    )
    assert response.status == SUCCESS, response.record()
    assert response.original_cog_dol == Decimal(
        "150" if side is Side.LONG else "60"
    )
    assert response.source_opposite_h1_dol == Decimal(
        "120" if side is Side.LONG else "80"
    )
    assert response.projected_index_points == Decimal(
        "15" if side is Side.LONG else "14"
    )
    dto = response.proposed
    assert dto is not None
    assert dto.cognitive_version == NEW_RESEARCH_VERSION
    assert dto.side == side
    assert dto.draw_target == response.source_opposite_h1_dol
    assert dto.structure_break_confirmed_at == at
    assert dto.mss_anchor_close == rows[-1].close
    assert dto.framework_policy == G3_MSS_FRAMEWORK_POLICY
    assert dto.draw_level_observed_at < at
    assert response.independent_v2_state == "CONFIRMED"
    assert not response.operations_authorized
    assert not response.method_certified
    assert not response.cognition_certified


@pytest.mark.parametrize("side,expect_gap", [
    (Side.LONG, Decimal("5")),
    (Side.SHORT, Decimal("4")),
])
@pytest.mark.parametrize("month", [1, 7])
def test_ttrades_source_valid_but_g3_10point_method_conflict_wait(
    side, expect_gap, month,
):
    rows, at = ttrades_fixture(side=side, month=month, min10_valid=False)
    response = ttrades_source_first_g3_cognitive_proposal(
        profile=TTRADES_AM, session=SessionId.NY_AM,
        as_of=at, closed_m1=rows,
    )
    assert response.status == MIN10_CONFLICT, response.record()
    assert response.projected_index_points == expect_gap
    assert response.proposed is None
    assert response.source_opposite_h1_dol == Decimal(
        "110" if side is Side.LONG else "90"
    )
    assert not response.operations_authorized


def test_nosweep_does_not_mint_profile_cognitive_dto():
    rows, at = ttrades_fixture(
        side=Side.LONG, month=1, min10_valid=True,
    )
    edited = list(rows)
    edited[390+601] = replace(
        edited[390+601], low=Decimal("93"), open=Decimal("96"),
        high=Decimal("99"), close=Decimal("95"),
    )
    got = ttrades_source_first_g3_cognitive_proposal(
        profile=TTRADES_AM, session=SessionId.NY_AM,
        as_of=at, closed_m1=tuple(edited),
    )
    assert got.status == "TTRADES_SOURCE_NOT_CONFIRMED_WAIT"
    assert got.proposed is None


def test_single_bar_double_raid_intrabar_order_unknown_not_cognitive_permission():
    rows, at = ttrades_fixture(side=Side.LONG, month=1, min10_valid=True)
    changed = list(rows)
    changed[390+601] = replace(changed[390+601], high=Decimal("121"))
    got = ttrades_source_first_g3_cognitive_proposal(
        profile=TTRADES_AM, session=SessionId.NY_AM,
        as_of=at, closed_m1=tuple(changed),
    )
    assert got.status == "TTRADES_SOURCE_NOT_CONFIRMED_WAIT"
    assert got.proposed is None


def test_missing_nine_am_m1_unknown_no_imputation():
    rows, at = ttrades_fixture(side=Side.SHORT, month=1, min10_valid=True)
    omitted = rows[:390+560] + rows[390+561:]
    got = ttrades_source_first_g3_cognitive_proposal(
        profile=TTRADES_AM, session=SessionId.NY_AM,
        as_of=at, closed_m1=omitted,
    )
    assert got.status == "TTRADES_SOURCE_NOT_CONFIRMED_WAIT"
    assert got.proposed is None


def test_weak_mss_with_ttrades_sweep_is_wait_not_fake_dol():
    rows, at = ttrades_fixture(side=Side.LONG, month=7, min10_valid=True)
    revised = list(rows)
    revised[-1] = replace(
        revised[-1], open=Decimal("94"), close=Decimal("104"),
    )
    got = ttrades_source_first_g3_cognitive_proposal(
        profile=TTRADES_AM, session=SessionId.NY_AM,
        as_of=at, closed_m1=tuple(revised),
    )
    assert got.status == "ORIGINAL_COG_MSS_NOT_CONFIRMED_WAIT"
    assert got.proposed is None


def test_unrecognized_method_identity_london_and_future_are_never_rebound():
    rows, at = ttrades_fixture(side=Side.LONG, month=1, min10_valid=True)
    with pytest.raises(ValueError, match="TTRADES_EXPLICIT_METHOD_PROFILE_REQUIRED"):
        ttrades_source_first_g3_cognitive_proposal(
            profile="ICT_GENERAL_2023", session=SessionId.NY_AM,
            as_of=at, closed_m1=rows,
        )
    outside = ttrades_source_first_g3_cognitive_proposal(
        profile=TTRADES_AM, session=SessionId.LONDON,
        as_of=at, closed_m1=rows,
    )
    assert outside.status == "PROFILE_SESSION_REJECTED"
    future = ttrades_source_first_g3_cognitive_proposal(
        profile=TTRADES_AM, session=SessionId.NY_AM,
        as_of=at-timedelta(minutes=1), closed_m1=rows,
    )
    assert future.status == "INPUT_INVALID_REJECTED"
    assert future.proposed is None


def test_court_never_claims_certification_or_authority():
    data = cognitive_profile_court()
    assert len(data["cases"]) == 8
    assert data["original_frozen_g3_code_sha"]["git_blob_sha1"] == (
        "d0ab4c15d6e9d24e53224d27bdb2cd96af914fb9"
    )
    assert sum(x["status"] == SUCCESS for x in data["cases"]) == 4
    assert sum(x["status"] == MIN10_CONFLICT for x in data["cases"]) == 4
    assert data["input_historical_3y_data_used"] is False
    assert data["trader_method_certified"] is False
    assert data["trader_cognitive_certified"] is False
    assert data["independent_human_method_source_review"] is False
    assert data["independent_human_cog_ops_dual_signatures"] is False
    assert data["economic_backtest_run"] is False
    assert data["orders_filled"] == data["lots_selected"] == 0
    assert data["live_authorized"] is False
    for x in data["cases"]:
        assert x["method_certified"] is False
        assert x["cognition_certified"] is False
        assert x["human_signed"] is False
        assert x["operations_authorized"] is False
