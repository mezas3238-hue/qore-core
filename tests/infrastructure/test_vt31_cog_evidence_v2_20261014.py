"""COG_EVIDENCE_V2: authentic assessment DTO + as-of high/low and source vetoes."""
from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from qore.infrastructure.traders.vt31_ict_cleanroom.cognition import (
    CognitiveAssessment,
)
from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import (
    G3_MSS_FRAMEWORK_POLICY,
    CognitiveDecision,
    M1Bar,
    SessionId,
    Side,
)
from scripts.vt31_cog_evidence_v2_20261014 import (
    ICT,
    TTRADES,
    Status,
    record,
)

NY = ZoneInfo("America/New_York")
DAY = datetime(2025, 7, 1, tzinfo=NY)
NINE = DAY.replace(hour=9).astimezone(UTC)
TEN = DAY.replace(hour=10).astimezone(UTC)


def candle(
    minute: int, *, start: datetime,
    o: str = "100", hi: str = "102", lo: str = "98", close: str = "100",
) -> M1Bar:
    t = start + timedelta(minutes=minute)
    return M1Bar(
        t, t + timedelta(minutes=1), Decimal(o),
        Decimal(hi), Decimal(lo), Decimal(close),
    )


def genuine_contract_fixture():
    nine = [candle(i, start=NINE) for i in range(60)]
    nine[10] = candle(10, start=NINE, hi="110")
    nine[20] = candle(20, start=NINE, lo="90")
    ten = [
        candle(0, start=TEN),
        candle(1, start=TEN, o="96", hi="99", lo="89", close="95"),
        candle(2, start=TEN, o="94", hi="100", lo="93", close="98"),
        candle(3, start=TEN, o="98", hi="101", lo="97", close="99"),
    ]
    dto = CognitiveDecision(
        session=SessionId.NY_AM, side=Side.LONG,
        observed_at=ten[-1].closed_at,
        draw_target=Decimal("110"),
        draw_family="TTRADES_NY_AM_H1_OPPOSITE",
        draw_level_observed_at=nine[-1].closed_at,
        structure_level=Decimal("97"),
        structure_level_confirmed_at=nine[55].closed_at,
        structure_break_confirmed_at=ten[2].closed_at,
        source_provenance="TEST_SYNTHETIC_CLOSED_M1",
        cognitive_version="METHOD_CERT_SHADOW",
        framework_policy=G3_MSS_FRAMEWORK_POLICY,
        mss_anchor_close=Decimal("98"),
    )
    assessment = CognitiveAssessment(
        as_of=ten[-1].closed_at,
        session=SessionId.NY_AM,
        decision=dto,
        state="CAUSAL_DRAW_AND_SHIFT_PROVEN",
        causal_closed_m1_count=100,
        verified_htf=("M15", "H1"),
        source_pool_count=1,
        structure_shift_detected=True,
        missing=(),
    )
    return tuple(nine), tuple(ten), assessment


def evaluate(nine, ten, assessment, profile=TTRADES):
    return record(
        profile=profile, assessment=assessment,
        previous_ny_9am=nine, current_ny_10am=ten,
    )


def test_confirmed_context_has_no_trader_certification_or_order_authority():
    nine, ten, a = genuine_contract_fixture()
    r = evaluate(nine, ten, a)
    assert r.schema == "qore.vt31.cog_evidence.v2.research_only"
    assert r.status is Status.CONFIRMED
    assert r.context_confirmed_only
    assert not r.reasons
    assert r.draw_target == r.expected_source_target == "110"
    assert r.first_sweep_closed_at == ten[1].closed_at.isoformat()
    assert r.mss_closed_at == ten[2].closed_at.isoformat()
    assert r.verified_htf == ("M15", "H1")
    assert r.source_pool_count == 1
    assert r.input_m1_closed_asof == 64
    assert not any((
        r.methodology_certified, r.cognition_certified,
        r.execution_authorized, r.economic_edge_proven,
    ))


def test_same_evidence_has_reproducible_json_and_hash():
    nine, ten, a = genuine_contract_fixture()
    x = evaluate(nine, ten, a)
    y = evaluate(nine, ten, a)
    assert x.evidence_sha256 == y.evidence_sha256
    assert len(x.evidence_sha256) == 64
    assert len(x.verified_closed_m1_sha256) == 64
    assert x.to_json() == y.to_json()


def test_missing_source_hour_is_unknown_never_confirmed():
    nine, ten, a = genuine_contract_fixture()
    r = evaluate(nine[:-1], ten, a)
    assert r.status is Status.UNKNOWN
    assert "H1_09_10_NOT_COMPLETE" in r.reasons
    assert not r.context_confirmed_only


def test_gapped_ten_prefix_is_unknown_not_a_valid_raid():
    nine, ten, a = genuine_contract_fixture()
    corrupt = ten[:2] + (candle(
        5, start=TEN, o="94", hi="100", lo="93", close="98",
    ),) + ten[3:]
    r = evaluate(nine, corrupt, a)
    assert r.status is Status.UNKNOWN
    assert "M1_10AM_PREFIX_GAPPED_OR_MISSING" in r.reasons


def test_no_cog_decision_exposes_reasons_as_unknown():
    nine, ten, a = genuine_contract_fixture()
    none = replace(
        a, decision=None, state="NO_VALID_CAUSAL_COGNITION",
        missing=("H1_CLOSED_CONTEXT", "LIQUIDITY_POOL"),
        verified_htf=(),
    )
    r = evaluate(nine, ten, none)
    assert r.status is Status.UNKNOWN
    assert "COG_DECISION_NOT_PRESENT" in r.reasons
    assert "COG_MISSING_LIQUIDITY_POOL" in r.reasons
    assert not r.cog_decision_present


def test_cog_state_claiming_decision_but_none_is_rejected():
    nine, ten, a = genuine_contract_fixture()
    absent = replace(a, decision=None)
    r = evaluate(nine, ten, absent)
    assert r.status is Status.REJECTED
    assert "COG_STATE_CLAIMS_ABSENT_DECISION" in r.reasons


def test_wrong_dol_cannot_confirm():
    nine, ten, a = genuine_contract_fixture()
    r = evaluate(nine, ten, replace(
        a, decision=replace(a.decision, draw_target=Decimal("150")),
    ))
    assert r.status is Status.REJECTED
    assert "DOL_NOT_OPPOSITE_9AM_H1_EXTREME" in r.reasons


def test_g3_mss_anchor_forgery_is_rejected():
    nine, ten, a = genuine_contract_fixture()
    wrong = replace(a.decision, mss_anchor_close=Decimal("99"))
    r = evaluate(nine, ten, replace(a, decision=wrong))
    assert r.status is Status.REJECTED
    assert "MSS_ANCHOR_CLOSE_NOT_EQUAL_WITNESS_M1" in r.reasons


def test_mss_break_must_actually_cross_structure():
    nine, ten, a = genuine_contract_fixture()
    wrong = replace(a.decision, structure_level=Decimal("105"))
    r = evaluate(nine, ten, replace(a, decision=wrong))
    assert r.status is Status.REJECTED
    assert "MSS_BREAK_LEVEL_NOT_CROSSED_BY_CLOSE" in r.reasons


def test_double_side_raid_fails_closed_and_cannot_claim_direction():
    nine, ten, a = genuine_contract_fixture()
    wrong = ten[:1] + (candle(
        1, start=TEN, o="100", hi="111", lo="89", close="100",
    ),) + ten[2:]
    r = evaluate(nine, wrong, a)
    assert r.status is Status.REJECTED
    assert "BOTH_H1_SIDES_SWEPT_UNKNOWN_INTRABAR_ORDER" in r.reasons


def test_no_sweep_is_rejected_but_missing_hour_is_unknown():
    nine, ten, a = genuine_contract_fixture()
    wrong = ten[:1] + (candle(1, start=TEN),) + ten[2:]
    r = evaluate(nine, wrong, a)
    assert r.status is Status.REJECTED
    assert "NO_PRE_SIGNAL_9AM_H1_SWEEP" in r.reasons


def test_source_future_bar_never_enters_closed_asof_digest():
    nine, ten, a = genuine_contract_fixture()
    ordinary = evaluate(nine, ten, a)
    future = ten + (candle(4, start=TEN),)
    r = evaluate(nine, future, a)
    assert r.status is Status.REJECTED
    assert "FUTURE_M1_IN_SOURCE" in r.reasons
    assert r.verified_closed_m1_sha256 == ordinary.verified_closed_m1_sha256
    assert r.input_m1_closed_asof == ordinary.input_m1_closed_asof


def test_assessment_asof_and_session_mutations_rejected():
    nine, ten, a = genuine_contract_fixture()
    stale = replace(a, as_of=ten[2].closed_at)
    r = evaluate(nine, ten, stale)
    assert r.status is Status.REJECTED
    assert "COG_DECISION_AS_OF_MISMATCH" in r.reasons
    wrong_session = replace(a, session=SessionId.LONDON)
    r2 = evaluate(nine, ten, wrong_session)
    assert r2.status is Status.REJECTED
    assert "COG_DECISION_SESSION_MISMATCH" in r2.reasons


def test_genuine_cog_htf_missing_and_order_authorization_forgery_rejected():
    nine, ten, a = genuine_contract_fixture()
    r = evaluate(nine, ten, replace(a, verified_htf=("M15",)))
    assert r.status is Status.REJECTED
    assert "COG_HTF_EVIDENCE_CONTRADICTS_PROVEN_DECISION" in r.reasons
    r2 = evaluate(nine, ten, replace(a, trade_authorized=True))
    assert "RESEARCH_ONLY_ASSESSMENT_INVARIANT_VIOLATED" in r2.reasons
    assert r2.status is Status.REJECTED
    assert not r2.execution_authorized


@pytest.mark.parametrize("session", [
    SessionId.LONDON, SessionId.NY_AM, SessionId.NY_PM,
])
def test_ict_general_is_unknown_not_falsely_vetoed_by_ttrades_9am(session):
    nine, ten, a = genuine_contract_fixture()
    a = replace(a, session=session, decision=None,
                state="NO_VALID_CAUSAL_COGNITION", missing=("LIQUIDITY_POOL",))
    r = evaluate((), (), a, profile=ICT)
    assert r.status is Status.UNKNOWN
    assert "ICT_SOURCE_DOCTRINE_NOT_YET_FORMALIZED" in r.reasons
    assert "H1_09_10_NOT_COMPLETE" not in r.reasons


def test_non_registered_methodology_profile_is_rejected_at_boundary():
    _, _, a = genuine_contract_fixture()
    with pytest.raises(ValueError, match="unrecognized source"):
        record(profile="TTRADES_UNIVERSAL_2023", assessment=a)
