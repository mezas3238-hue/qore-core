"""Hermetic causal/golden-fixture checks for Architect A -> B proposal."""
from dataclasses import replace
from datetime import datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from qore.infrastructure.trader_lab.vt08_5m_candidate_event_v1 import (
    CandidateEventContractError,
    Vt08CandidateEventV1,
)

NY = ZoneInfo("America/New_York")


def golden(*, july: bool = False) -> Vt08CandidateEventV1:
    anchor = datetime(2026, 7 if july else 1, 5, 1, tzinfo=NY)
    return Vt08CandidateEventV1(
        market="EURJPY",
        source_family="positional-entry",
        ltf_profile="M15_STANDARD",
        side="long",
        scenario="C2_COMPLETED",
        h4_anchor_at=anchor,
        decision_at=anchor,
        evidence_as_of=anchor,
        candle2_closed_at=anchor,
        opposing_series_opened_at=anchor - timedelta(hours=2),
        cisd_confirmed_at=anchor - timedelta(minutes=15),
        ps_confirmed_at=anchor - timedelta(minutes=15),
        entry_price=Decimal("160.00"),
        stop_price=Decimal("159.50"),
        target_price=Decimal("161.00"),
        pending_expiry_at=anchor + timedelta(hours=4),
        source_methodology_sha256="a" * 64,
        evidence_sha256="b" * 64,
    )


def test_golden_envelope_deterministic_and_outcome_free() -> None:
    event = golden()
    assert event.envelope() == golden().envelope()
    payload = event.envelope()
    assert payload["ny_date"] == "2026-01-05"
    assert payload["anchor_ny_hour"] == 1
    assert payload["execution_authorized"] is False
    assert payload["live_authorized"] is False
    assert "pnl" not in str(payload).lower()
    assert "profit" not in str(payload).lower()
    assert len(payload["event_fingerprint"]) == 64


def test_dst_preserves_new_york_anchor_not_utc_hour() -> None:
    winter, summer = golden(), golden(july=True)
    assert winter.envelope()["h4_anchor_at"].endswith("+00:00")
    assert summer.envelope()["h4_anchor_at"].endswith("+00:00")
    assert winter.h4_anchor_at.utcoffset() != summer.h4_anchor_at.utcoffset()
    assert summer.envelope()["anchor_ny_hour"] == 1


@pytest.mark.parametrize("family", [
    "reversal-entry", "continuation-entry", "confident-entry",
    "open-entry", "poi-continuation-entry",
])
def test_no_unproven_nonpositional_fills(family: str) -> None:
    with pytest.raises(CandidateEventContractError, match="not an executable bundle"):
        replace(golden(), source_family=family)


@pytest.mark.parametrize("profile", ["M3_FRACTAL", "M5_FRACTAL"])
def test_no_cross_profile_synthetic_fills(profile: str) -> None:
    with pytest.raises(CandidateEventContractError, match="M15 only"):
        replace(golden(), ltf_profile=profile)


def test_banned_thirteen_ny_even_if_present_in_official_source_timing() -> None:
    event = golden()
    shifted = event.h4_anchor_at + timedelta(hours=12)
    with pytest.raises(CandidateEventContractError, match="01/05/09"):
        replace(
            event,
            h4_anchor_at=shifted,
            decision_at=shifted,
            evidence_as_of=shifted,
            candle2_closed_at=shifted,
            pending_expiry_at=shifted + timedelta(hours=4),
            opposing_series_opened_at=shifted - timedelta(hours=2),
            cisd_confirmed_at=shifted - timedelta(minutes=15),
            ps_confirmed_at=shifted - timedelta(minutes=15),
        )


def test_future_protected_swing_cannot_license_past_h4_open() -> None:
    event = golden()
    with pytest.raises(CandidateEventContractError, match="not confirmed as-of"):
        replace(event, ps_confirmed_at=event.decision_at + timedelta(minutes=15),
                cisd_confirmed_at=event.decision_at + timedelta(minutes=15))


def test_no_retroactive_evidence_asof() -> None:
    event = golden()
    with pytest.raises(CandidateEventContractError, match="causal at H4 open"):
        replace(event, evidence_as_of=event.decision_at + timedelta(minutes=15))


def test_invalid_long_risk_or_non2r_target_rejected() -> None:
    with pytest.raises(CandidateEventContractError, match="geometry invalid"):
        replace(golden(), stop_price=Decimal("161"))
    with pytest.raises(CandidateEventContractError, match="fixed-2R"):
        replace(golden(), target_price=Decimal("160.75"))


def test_no_live_or_unapproved_market() -> None:
    with pytest.raises(CandidateEventContractError, match="research-only"):
        replace(golden(), research_only=False)
    with pytest.raises(CandidateEventContractError, match="market outside"):
        replace(golden(), market="NAS100")


def test_fingerprint_changes_with_source_known_information() -> None:
    event = golden()
    assert event.fingerprint() != replace(
        event, evidence_sha256="c" * 64
    ).fingerprint()


def test_naive_or_bad_provenance_is_rejected() -> None:
    with pytest.raises(CandidateEventContractError, match="timezone-aware"):
        replace(golden(), decision_at=datetime(2026, 1, 5, 1))
    with pytest.raises(CandidateEventContractError, match="lowercase sha256"):
        replace(golden(), evidence_sha256="some-unbound-evidence")
