"""Original VT31CleanroomCognition differs from primary TTrades NY AM DOL."""
from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.traders.vt31_ict_cleanroom.cognition import (
    VT31CleanroomCognition,
)
from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import (
    SessionId,
    Side,
)
from scripts.vt31_mc_p2_ttrades_native_h1_evidence_20261014 import (
    native_ttrades_am_context,
)
from scripts.vt31_original_cog_nyam_ttrades_source_conflict_20261014 import (
    nyam_source_fixture,
    original_nyam_source_conflict,
)


def test_original_vt31_g3_nyam_cog_truly_emits_cash_dol_not_nine_h1():
    source, nine, ten = nyam_source_fixture()
    cog = VT31CleanroomCognition()
    for bar in source:
        cog.observe_closed_m1(bar)
    dto = cog.assess(session=SessionId.NY_AM, as_of=ten[-1].closed_at)
    assert dto.decision is not None
    assert dto.decision.side is Side.LONG
    assert dto.decision.draw_family == "PRIOR_NY_CASH_SESSION_HIGH"
    assert dto.decision.draw_target == Decimal("150")
    assert dto.decision.structure_level == Decimal("104")
    assert max(x.high for x in nine) == Decimal("110")
    assert min(x.low for x in nine) == Decimal("90")
    assert dto.trade_authorized is False


def test_independent_ttrades_source_witness_requires_opposite_9am_high():
    source, nine, ten = nyam_source_fixture()
    native = native_ttrades_am_context(
        as_of=ten[-1].closed_at, nine=nine, ten=ten,
    )
    assert native.state == "RETURN_INSIDE_OBSERVED"
    assert native.first_sweep_at == ten[1].closed_at
    assert native.return_inside_at == ten[2].closed_at
    assert native.candidate_side == "LONG"
    assert native.opposite_h1_dol == Decimal("110")


def test_mismatch_is_qualitative_methodological_not_quantitative():
    p = original_nyam_source_conflict()
    assert p["observed_actual_original_cog_dol"] == "150"
    assert p["ttrades_source_required_opposite_h1_dol"] == "110"
    assert p["methodology_profile_qualitative_verdict"] == (
        "TTRADES_NYAM_DOL_SOURCE_NONCONFORMANT"
    )
    assert p["observed_actual_original_cog_side"] == "LONG"
    assert p["independent_source_v2_state"] == "REJECTED"
    assert "DOL_NOT_OPPOSITE_9AM_H1_EXTREME" in (
        p["independent_source_v2_rejections"]
    )
    assert p["ict_general_dol_logic_independently_falsified"] is False
    assert p["original_engine_called_not_a_proxy"] is True
    assert p["cog_temporal_inference_functional_for_this_case"] is True
    assert p["cog_ttrades_author_fidelity_certified"] is False
    assert p["cog_overall_certified"] is False
    assert p["methodology_overall_certified"] is False
    assert p["financial_evidence"] is None
    assert p["market_replay_3y_used"] is False
    assert p["operator_orders"] == p["lot_sizing"] == 0
    assert p["live_authorized"] is False
