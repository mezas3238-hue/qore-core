"""Adversarial frozen cross-version comparison; NO trader or ICT certification."""
from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import (
    NEW_YORK,
    CognitiveDecision,
    M1Bar,
    SessionId,
    Side,
)
from scripts.vt31_ict_dol_source_v1_20261014 import attest_ict_dol_source
from scripts.vt31_mc_p3_ict_independent_dol_20261014 import verify_ict_dol_from_m1
from scripts.vt31_m2_dol_reconciliation_20261014 import (
    DATES,
    audit_days,
    compare_one,
)


def instant(y: int, m: int, d: int, h: int, minute: int = 0) -> datetime:
    return datetime(
        y, m, d, h, minute, tzinfo=NEW_YORK,
    ).astimezone(UTC)


def bar(t: datetime, *, hi: str = "102", lo: str = "98") -> M1Bar:
    return M1Bar(
        t, t + timedelta(minutes=1),
        Decimal("100"), Decimal(hi), Decimal(lo), Decimal("100"),
    )


def strip(
    start: datetime, end: datetime, *, high: str = "102",
) -> tuple[M1Bar, ...]:
    return tuple(
        bar(start + timedelta(minutes=i), hi=high)
        for i in range(int((end - start).total_seconds() // 60))
    )


def probe(
    *, at: datetime, family: str, target: str, confirmed: datetime,
    session: SessionId = SessionId.NY_AM,
) -> CognitiveDecision:
    return CognitiveDecision(
        session=session, side=Side.LONG, observed_at=at,
        draw_family=family + "_HIGH", draw_target=Decimal(target),
        draw_level_observed_at=confirmed,
        structure_level=Decimal("100"),
        structure_level_confirmed_at=at - timedelta(minutes=2),
        structure_break_confirmed_at=at,
        source_provenance="SYNTHETIC_CONTRACT_PROBE",
        cognitive_version="NOT_NATIVE_COG",
    )


def asia() -> tuple[tuple[M1Bar, ...], CognitiveDecision]:
    begin, at = instant(2025, 7, 1, 0), instant(2025, 7, 1, 10, 6)
    rows = list(strip(begin, at))
    rows[65] = bar(rows[65].opened_at, hi="110")
    return tuple(rows), probe(
        at=at, family="ASIA_NY_CLOCK", target="110",
        confirmed=instant(2025, 7, 1, 3),
    )


def test_unmodified_verifiers_agree_on_complete_asia_source():
    rows, cog = asia()
    p3 = verify_ict_dol_from_m1(
        as_of=cog.observed_at, session=cog.session,
        history=rows, cognition=cog,
    )
    v1 = attest_ict_dol_source(
        as_of=cog.observed_at, session=cog.session,
        history=rows, cognition=cog,
    )
    assert p3.state == "VERIFIED_QORE_DOL_PRICE_LINEAGE"
    assert v1.state == "CONFIRMED"
    assert p3.observed_level == cog.draw_target
    assert not p3.method_certified and not v1.method_certified


def test_timestamp_conflict_p3_rejects_while_v1_confirms():
    rows, cog = asia()
    late = replace(
        cog, draw_level_observed_at=instant(2025, 7, 1, 3, 1),
    )
    p3 = verify_ict_dol_from_m1(
        as_of=late.observed_at, session=late.session,
        history=rows, cognition=late,
    )
    v1 = attest_ict_dol_source(
        as_of=late.observed_at, session=late.session,
        history=rows, cognition=late,
    )
    assert p3.state == "REJECTED"
    assert "COG_DOL_CONFIRMATION_TIMESTAMP_MISMATCH" in p3.reasons
    assert v1.state == "CONFIRMED"
    assert not v1.cognition_certified and not v1.execution_authorized


def test_old_complete_cash_fallback_and_consumption_contradiction():
    friday = list(strip(
        instant(2025, 6, 27, 9, 30), instant(2025, 6, 27, 16),
    ))
    friday[4] = bar(friday[4].opened_at, hi="150")
    monday = list(strip(
        instant(2025, 6, 30, 9, 30), instant(2025, 6, 30, 16),
    ))
    monday[24] = bar(monday[24].opened_at, hi="160")
    monday.pop(10)  # prior weekday is incomplete; NEVER invent 390th M1.
    tuesday = strip(
        instant(2025, 7, 1, 0), instant(2025, 7, 1, 10, 6),
    )
    rows = tuple(friday + monday) + tuesday
    cog = probe(
        at=tuesday[-1].closed_at, family="PRIOR_NY_CASH_SESSION",
        target="150", confirmed=friday[-1].closed_at,
    )
    p3 = verify_ict_dol_from_m1(
        as_of=cog.observed_at, session=cog.session,
        history=rows, cognition=cog,
    )
    v1 = attest_ict_dol_source(
        as_of=cog.observed_at, session=cog.session,
        history=rows, cognition=cog,
    )
    assert p3.state == "REJECTED"
    assert "DOL_ALREADY_CONSUMED_AFTER_CONFIRMATION" in p3.reasons
    assert p3.source_start == friday[0].opened_at
    assert v1.state == "UNKNOWN", v1.record()
    assert "SOURCE_POOL_NOT_CAUSALLY_ATTESTABLE" in v1.reasons


def test_gap_after_asia_remains_unknown_for_both_not_confirmed():
    rows, cog = asia()
    rows = rows[:210] + rows[211:]
    p3 = verify_ict_dol_from_m1(
        as_of=cog.observed_at, session=cog.session,
        history=rows, cognition=cog,
    )
    v1 = attest_ict_dol_source(
        as_of=cog.observed_at, session=cog.session,
        history=rows, cognition=cog,
    )
    assert p3.state == "UNKNOWN"
    assert v1.state == "UNKNOWN"


def test_probe_adapter_does_not_claim_native_cognition_or_method():
    rows, cog = asia()
    out = compare_one(
        rows, as_of=cog.observed_at, session=cog.session,
        family="ASIA_NY_CLOCK", side=Side.LONG,
    )
    assert out["same_normalized_state"] is True
    assert out["p3_state"] == out["v1_state"] == "SUPPORTED"
    assert out["probe_not_authentic_cognition"] is True
    assert not out["method_certified"]
    assert not out["cognition_certified"]
    assert not out["execution_authorized"]


def test_frozen_grid_never_silently_omits_missing_market_days():
    report = audit_days({d: () for d in DATES})
    assert report["scheduled_probes"] == 216
    assert report["unavailable_source_probes"] == 216
    assert len(report["records"]) == 216
    assert report["broker_ack_or_fills"] == 0
    assert report["profit_factor"] is None
    assert report["native_cog_evaluated"] is False
    assert not report["trader_certified"]
