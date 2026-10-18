"""Research-only M2 pre-OPS guard, original G3 first M1 DTO event fixtures."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import (
    NEW_YORK,
    SessionId,
)
from scripts.vt31_m2c_preops_source_admission_20261018 import (
    M2PreOpsResearchGate,
)


def make(
    month: int, session: SessionId, state: str,
    *, miss: int | None = None,
    wrong_level: bool = False,
) -> tuple[M2PreOpsResearchGate, dict]:
    hour = {
        SessionId.LONDON: 3,
        SessionId.NY_AM: 10,
        SessionId.NY_PM: 14,
    }[session]
    d = f"2025-{month:02d}-15"
    asof = datetime(
        2025, month, 15, hour, 1, tzinfo=NEW_YORK,
    ).astimezone(UTC)
    first = asof - timedelta(minutes=4)
    opened_list = [first + timedelta(minutes=i) for i in range(4)]
    tape = M2PreOpsResearchGate()
    for i, opened in enumerate(opened_list):
        if miss == i:
            continue
        tape.observe_closed_m1(
            opened_at=opened.isoformat(),
            closed_at=(opened + timedelta(minutes=1)).isoformat(),
        )
    pool = {
        "family": "ASIA_NY_CLOCK_HIGH",
        "level": "102.00" if not wrong_level else "102.50",
        "source_end": first.isoformat(),
        "state": "UNKNOWN" if miss is not None else "UNCONSUMED",
        "reason": (
            "POST_SOURCE_M1_COVERAGE_GAPPED" if miss is not None else None
        ),
    }
    if state == "REJECTED":
        pool["family"] = "PRIOR_NY_CASH_SESSION_HIGH"
    case = {
        "original_G3_QORE_DTO_present_not_trade": True,
        "ny_day": d,
        "session": session.value,
        "first_closed_M1_utc": asof.isoformat(),
        "native_M0_source_wait": None,
        "nyam_h1_09_completed_at_10_if_applicable": (
            True if session is SessionId.NY_AM else None
        ),
        "M2_QORE_independent_attestation_state": state,
        "original_g3_draw_family": (
            "PRIOR_NY_CASH_SESSION_HIGH" if state == "REJECTED"
            else "ASIA_NY_CLOCK_HIGH"
        ),
        "original_G3_draw_price": "102.00",
        "source_pool_six_independent_M1_witnesses": [pool],
        "M2_QORE_independent_attestation_reasons": (
            ["COG_DOL_ANNOUNCED_BEFORE_SOURCE_CLOSE"]
            if state == "REJECTED" else []
        ),
    }
    return tape, case


@pytest.mark.parametrize("month", [1, 7])
@pytest.mark.parametrize("session", list(SessionId))
def test_complete_context_is_research_only_not_ops_or_author(month, session):
    tape, case = make(month, session, "CONFIRMED")
    out = tape.admit_committed_cog_event(case)
    assert out.source_m2_status == "SOURCE_CONTEXT_COMPLETE_UNCERTIFIED"
    assert out.independent_missing_m1 == 0
    assert out.ops_cognition is None
    assert out.ops_authorized is False
    assert out.author_method_certified is False
    assert out.method_owner_signed is False
    assert out.broker_orders == out.sizing == 0
    assert out.ny_day == case["ny_day"]


@pytest.mark.parametrize("month", [1, 7])
@pytest.mark.parametrize("session", list(SessionId))
def test_exact_one_closed_m1_missing_forces_preops_wait(month, session):
    tape, case = make(month, session, "UNKNOWN", miss=1)
    out = tape.admit_committed_cog_event(case)
    assert out.source_m2_status == "WAIT_SOURCE_M1_GAP"
    assert out.independent_missing_m1 == 1
    assert out.ops_cognition is None
    assert not out.ops_authorized


@pytest.mark.parametrize("session", list(SessionId))
def test_preexisting_cash_method_mismatch_remains_wait(session):
    tape, case = make(7, session, "REJECTED")
    out = tape.admit_committed_cog_event(case)
    assert out.source_m2_status == "WAIT_CASH_CALENDAR_POLICY_UNSIGNED"
    assert out.independent_missing_m1 is None
    assert out.ops_cognition is None
    assert not out.ops_authorized


def test_unknown_without_m1_gap_falsifies_original_source_label():
    tape, case = make(7, SessionId.LONDON, "UNKNOWN")
    case["source_pool_six_independent_M1_witnesses"][0]["state"] = "UNKNOWN"
    case["source_pool_six_independent_M1_witnesses"][0]["reason"] = (
        "POST_SOURCE_M1_COVERAGE_GAPPED"
    )
    with pytest.raises(AssertionError, match="GAP_NOT_REPRODUCED"):
        tape.admit_committed_cog_event(case)


def test_claim_confirmed_but_m1_missing_rejected_not_promoted():
    tape, case = make(7, SessionId.NY_PM, "CONFIRMED", miss=2)
    case["source_pool_six_independent_M1_witnesses"][0]["state"] = "UNCONSUMED"
    with pytest.raises(AssertionError, match="REAL_M1_GAP_CONTRADICTION"):
        tape.admit_committed_cog_event(case)


def test_g3_claimed_price_mismatch_refused_before_any_ops():
    tape, case = make(7, SessionId.NY_PM, "CONFIRMED", wrong_level=True)
    with pytest.raises(ValueError, match="PRICE_CONTRADICTION"):
        tape.admit_committed_cog_event(case)


def test_not_the_latest_close_cannot_be_accepted():
    tape, case = make(7, SessionId.LONDON, "CONFIRMED")
    case["first_closed_M1_utc"] = (
        datetime.fromisoformat(case["first_closed_M1_utc"])
        + timedelta(minutes=1)
    ).isoformat()
    with pytest.raises(ValueError, match="LATEST_CLOSE"):
        tape.admit_committed_cog_event(case)


def test_future_source_end_failsclosed():
    tape, case = make(7, SessionId.LONDON, "CONFIRMED")
    case["source_pool_six_independent_M1_witnesses"][0]["source_end"] = (
        datetime.fromisoformat(case["first_closed_M1_utc"])
        + timedelta(minutes=1)
    ).isoformat()
    with pytest.raises(ValueError, match="SOURCE_END_NOT_BEFORE_ASOF"):
        tape.admit_committed_cog_event(case)


def test_explicit_native_m0_wait_cannot_be_bypassed():
    tape, case = make(7, SessionId.NY_AM, "CONFIRMED")
    case["native_M0_source_wait"] = "SOURCE_09H_INCOMPLETE_WAIT"
    with pytest.raises(ValueError, match="BYPASSED_NATIVE_SOURCE_WAIT"):
        tape.admit_committed_cog_event(case)


def test_ttrades_h1_not_required_for_ict_general():
    for session in (SessionId.LONDON, SessionId.NY_PM):
        tape, case = make(7, session, "CONFIRMED")
        assert case["nyam_h1_09_completed_at_10_if_applicable"] is None
        assert tape.admit_committed_cog_event(case).ops_cognition is None


def test_nyam_ttrades_h1_source_required():
    tape, case = make(7, SessionId.NY_AM, "CONFIRMED")
    case["nyam_h1_09_completed_at_10_if_applicable"] = False
    with pytest.raises(ValueError, match="H1_M0_GATE_CONTRADICTION"):
        tape.admit_committed_cog_event(case)


def test_rejected_not_cash_policy_must_fail():
    tape, case = make(7, SessionId.LONDON, "REJECTED")
    case["M2_QORE_independent_attestation_reasons"] = ["OTHER_FAKE_REASON"]
    with pytest.raises(ValueError, match="NOT_A_CASH_POLICY_FIXTURE"):
        tape.admit_committed_cog_event(case)


def test_replayed_dto_not_allowed_twice():
    tape, case = make(7, SessionId.LONDON, "CONFIRMED")
    tape.admit_committed_cog_event(case)
    with pytest.raises(ValueError, match="DUPLICATE_SESSION"):
        tape.admit_committed_cog_event(case)


@pytest.mark.parametrize("kind", ["duplicate", "backwards", "naive", "unclosed"])
def test_source_ingress_is_strictly_m1_closed_monotonic(kind):
    tape = M2PreOpsResearchGate()
    opened = datetime(2025, 7, 15, 7, tzinfo=UTC)
    tape.observe_closed_m1(
        opened_at=opened.isoformat(),
        closed_at=(opened + timedelta(minutes=1)).isoformat(),
    )
    next_open = {
        "duplicate": opened,
        "backwards": opened - timedelta(minutes=1),
        "naive": opened.replace(tzinfo=None),
        "unclosed": opened + timedelta(minutes=1),
    }[kind]
    closing = next_open + (
        timedelta(minutes=2) if kind == "unclosed" else timedelta(minutes=1)
    )
    with pytest.raises(ValueError):
        tape.observe_closed_m1(
            opened_at=next_open.isoformat(),
            closed_at=closing.isoformat(),
        )


def test_unsigned_cash_policy_never_activates_ops_even_with_390_source():
    tape, case = make(7, SessionId.LONDON, "REJECTED")
    obs = tape.admit_committed_cog_event(case)
    assert obs.source_m2_status == "WAIT_CASH_CALENDAR_POLICY_UNSIGNED"
    assert obs.ops_cognition is None
    assert not obs.ops_authorized


def test_preops_gate_does_not_import_or_call_native_original_ops():
    import inspect

    source = inspect.getsource(M2PreOpsResearchGate)
    assert "IctSilverBulletOperations" not in source
    assert "broker" not in source.lower() or "broker_orders" in source
