"""Adversarial source/Situation binding fixtures; NEVER real market evidence.

Only this synthetic test monkeypatches a pretend A/B manifest. The production
research module deliberately has APPROVED_A_B_MANIFEST_SHA256 = None.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from test_vt08_cognitive_5m_consumed_gate_v1 import _snapshot

import qore.infrastructure.trader_lab.vt08_5m_a_to_b_candidate_readiness_v1 as readiness
from qore.infrastructure.trader_lab.vt08_cognitive_5m_consumed_gate_v1 import (
    Vt08FiveMarketCognitiveGate,
)
from qore.infrastructure.traders.vt08_cognitive_5m_research_scope import (
    CAUSAL_FIELDS,
    Vt08FiveMarketResearchSituation,
)
from qore.infrastructure.traders.vt08_cognitive_v1_contracts import Vt08CognitiveAction

T0 = datetime(2026, 9, 23, 13, 15, tzinfo=UTC)
SOURCE = "vt08-5m-source:" + "a" * 64
TEST_MANIFEST = "d" * 64


def _matching_pair() -> tuple[dict[str, object], Vt08FiveMarketResearchSituation]:
    situation = _snapshot(source=SOURCE, when=T0, ltf_profile="M15_STANDARD")
    envelope: dict[str, object] = {
        "schema": "VT08_5M_CANDIDATE_EVENT_V1",
        "source_event_id": SOURCE,
        "event_fingerprint": "b" * 64,
        "event_id": "vt08-5m:" + "b" * 64,
        "market": situation.market,
        "side": situation.side,
        "anchor_ny_hour": situation.anchor_hour_ny,
        "source_family": "positional-entry",
        "entry_basis": "TTRADES_AUTHOR_SOURCE_REVIEWED_TEST_FIXTURE",
        "stop_basis": "TTRADES_AUTHOR_SOURCE_REVIEWED_TEST_FIXTURE",
        "target_basis": "TTRADES_AUTHOR_SOURCE_REVIEWED_TEST_FIXTURE",
        "filled_lifecycle": "TTRADES_AUTHOR_SOURCE_REVIEWED_TEST_FIXTURE",
        "ltf_profile": situation.ltf_profile,
        "ny_date": T0.astimezone(ZoneInfo("America/New_York")).date().isoformat(),
        "methodology_status": "SOURCE_COMPLETE_EXECUTABLE",
        "decision_at": T0.isoformat(),
        "evidence_as_of": T0.isoformat(),
        "latest_available_bar_close": T0.isoformat(),
        "pending_expiry_at": (T0 + timedelta(hours=4)).isoformat(),
        "feature_close_cutoffs": {
            "source_h4": T0.isoformat(),
            "cisd": T0.isoformat(),
            "protected_swing": T0.isoformat(),
        },
        "bias_feature_cutoff": T0.isoformat(),
        "cognitive_feature_cutoffs": {
            name: T0.isoformat() for name in CAUSAL_FIELDS
        },
        "research_only": True,
        "execution_authorized": False,
        "live_authorized": False,
    }
    return envelope, situation


def test_unsigned_complete_synthetic_fixture_is_refused_without_mutation() -> None:
    envelope, situation = _matching_pair()
    gate = Vt08FiveMarketCognitiveGate()
    with pytest.raises(ValueError, match="CONTRACT_NOT_JOINTLY_FROZEN"):
        gate.evaluate_provenanced(
            envelope, situation, joint_contract_manifest_sha256=TEST_MANIFEST
        )
    assert not gate.decisions
    assert not gate.fills


def test_consistent_synthetic_fixture_only_passes_with_test_only_manifest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Test-only injection is never a joint signature; no author/broker proof.
    monkeypatch.setattr(readiness, "APPROVED_A_B_MANIFEST_SHA256", TEST_MANIFEST)
    envelope, situation = _matching_pair()
    trace = Vt08FiveMarketCognitiveGate().evaluate_provenanced(
        envelope, situation, joint_contract_manifest_sha256=TEST_MANIFEST
    )
    assert trace.action is Vt08CognitiveAction.EXECUTE
    assert trace.research_only and not trace.broker_order_authorized


@pytest.mark.parametrize(
    ("field", "expected"),
    [
        ("side", "side drift"),
        ("anchor_ny_hour", "anchor_ny_hour drift"),
        ("ltf_profile", "ltf_profile drift"),
        ("ny_date", "ny_date drift"),
        ("pending_expiry_at", "pending_expiry_at drift"),
        ("latest_available_bar_close", "latest_available_bar_close drift"),
        ("cognitive_feature_cutoffs", "cognitive feature bias_state drift"),
    ],
)
def test_signed_but_mismatched_source_fields_cannot_reach_reasoning(
    monkeypatch: pytest.MonkeyPatch, field: str, expected: str
) -> None:
    # All alterations stay at or before decision time, so ONLY cross-binding
    # detects this deception (rather than a simple future-timestamp guard).
    monkeypatch.setattr(readiness, "APPROVED_A_B_MANIFEST_SHA256", TEST_MANIFEST)
    envelope, situation = _matching_pair()
    if field == "side":
        envelope[field] = "short"
    elif field == "anchor_ny_hour":
        envelope[field] = 5
    elif field == "ltf_profile":
        # Readiness must fail closed even before this independent binding.
        envelope[field] = "M3_FRACTAL"
    elif field == "ny_date":
        envelope[field] = "2026-09-22"
    elif field in {"pending_expiry_at", "latest_available_bar_close"}:
        envelope[field] = (T0 - timedelta(minutes=1)).isoformat()
        if field == "pending_expiry_at":
            envelope[field] = (T0 + timedelta(hours=3)).isoformat()
    elif field == "cognitive_feature_cutoffs":
        original = envelope[field]
        assert isinstance(original, dict)
        envelope[field] = dict(
            original, bias_state=(T0 - timedelta(minutes=1)).isoformat()
        )
    gate = Vt08FiveMarketCognitiveGate()
    with pytest.raises(ValueError, match=expected if field != "ltf_profile"
                       else "unfrozen A LTF profile"):
        gate.evaluate_provenanced(
            envelope, situation, joint_contract_manifest_sha256=TEST_MANIFEST
        )
    assert gate.decisions == ()
    assert gate.fills == ()
