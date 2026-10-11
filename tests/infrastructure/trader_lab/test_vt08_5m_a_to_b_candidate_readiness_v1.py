"""Cognitive Architect B never silently executes Architect A's unproven event."""
from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.trader_lab.vt08_5m_a_to_b_candidate_readiness_v1 import (
    Vt08CandidateBoundaryError,
    inspect_architect_a_candidate,
)
from qore.infrastructure.traders.vt08_cognitive_5m_research_scope import (
    CAUSAL_FIELDS,
)

T = datetime(2026, 1, 5, 6, tzinfo=UTC)


def _a_envelope(**overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "schema": "VT08_5M_CANDIDATE_EVENT_V1",
        "source_event_id": "vt08-5m-source:" + "a" * 64,
        "event_fingerprint": "b" * 64,
        "event_id": "vt08-5m:" + "b" * 64,
        "market": "EURJPY",
        "anchor_ny_hour": 1,
        "source_family": "positional-entry",
        "ltf_profile": "M15_STANDARD",
        "methodology_status": "SOURCE_COMPLETE_EXECUTABLE",
        "decision_at": T.isoformat(),
        "evidence_as_of": T.isoformat(),
        "pending_expiry_at": (T + timedelta(hours=4)).isoformat(),
        "bias_feature_cutoff": "UNATTESTED_IN_LEGACY_B01_CANDIDATE",
        "feature_close_cutoffs": {
            "source_h4": T.isoformat(),
            "cisd": (T - timedelta(minutes=15)).isoformat(),
            "protected_swing": (T - timedelta(minutes=15)).isoformat(),
        },
        "research_only": True,
        "execution_authorized": False,
        "live_authorized": False,
    }
    value.update(overrides)
    return value


def test_current_a_event_is_explicitly_blocked_not_falsely_cognitive_ready() -> None:
    report = inspect_architect_a_candidate(_a_envelope())
    assert not report.cognitive_ready
    assert report.research_only and not report.order_authorized
    assert report.blockers == (
        "A_B:DAILY_BIAS_SOURCE_TIME_UNATTESTED",
        "A_B:COGNITIVE_FEATURE_PROVENANCE_INCOMPLETE",
        "A_B:CONTRACT_NOT_JOINTLY_FROZEN",
    )
    assert report.source_event_id != report.snapshot_event_id


def test_all_mandatory_causal_fields_and_joint_approval_are_both_required() -> None:
    attrs = {name: T.isoformat() for name in CAUSAL_FIELDS}
    data = _a_envelope(
        bias_feature_cutoff=(T - timedelta(hours=2)).isoformat(),
        cognitive_feature_cutoffs=attrs,
    )
    not_signed = inspect_architect_a_candidate(data)
    assert not not_signed.cognitive_ready
    assert not_signed.blockers == ("A_B:CONTRACT_NOT_JOINTLY_FROZEN",)
    # A supplied approval string cannot promote an unreviewed contract.
    caller_claimed_signed = inspect_architect_a_candidate(
        data, joint_contract_manifest_sha256="a" * 64
    )
    assert not caller_claimed_signed.cognitive_ready
    assert caller_claimed_signed.blockers == ("A_B:CONTRACT_NOT_JOINTLY_FROZEN",)
    assert not caller_claimed_signed.order_authorized


@pytest.mark.parametrize(
    ("override", "expected"),
    (
        ({"research_only": False}, "research-only"),
        ({"execution_authorized": True}, "cannot grant execution"),
        ({"live_authorized": True}, "cannot grant execution"),
        ({"source_family": "continuation-entry"}, "unfrozen A source family"),
        ({"ltf_profile": "M3_FRACTAL"}, "unfrozen A LTF"),
        ({"methodology_status": "SHAPE_ONLY"}, "not executable"),
        ({"market": "GBPJPY"}, "outside research"),
        ({"anchor_ny_hour": 13}, "Owner 01/05/09"),
        ({"source_event_id": "unbound"}, "stable source_event_id"),
        ({"event_fingerprint": "invalid"}, "event_fingerprint"),
        ({"event_id": "bad"}, "snapshot fingerprint"),
    ),
)
def test_bad_a_event_never_reaches_cognitive_reasoner(
    override: dict[str, object], expected: str
) -> None:
    with pytest.raises(Vt08CandidateBoundaryError, match=expected):
        inspect_architect_a_candidate(_a_envelope(**override))


def test_future_confirmation_and_bias_are_fatal_not_missing_data_wait() -> None:
    later = (T + timedelta(minutes=1)).isoformat()
    cutoffs = _a_envelope()["feature_close_cutoffs"]
    assert isinstance(cutoffs, dict)
    future = dict(cutoffs, cisd=later)
    with pytest.raises(Vt08CandidateBoundaryError, match="future source confirmation"):
        inspect_architect_a_candidate(_a_envelope(feature_close_cutoffs=future))
    with pytest.raises(Vt08CandidateBoundaryError, match="future bias evidence"):
        inspect_architect_a_candidate(_a_envelope(bias_feature_cutoff=later))
    attrs = {name: T.isoformat() for name in CAUSAL_FIELDS}
    attrs["bias_state"] = later
    with pytest.raises(Vt08CandidateBoundaryError, match="future cognitive feature"):
        inspect_architect_a_candidate(
            _a_envelope(
                bias_feature_cutoff=T.isoformat(),
                cognitive_feature_cutoffs=attrs,
            )
        )


def test_invalid_source_window_and_unaware_timestamp_fail_closed() -> None:
    with pytest.raises(Vt08CandidateBoundaryError, match="invalid causal window"):
        inspect_architect_a_candidate(
            _a_envelope(evidence_as_of=(T + timedelta(minutes=1)).isoformat())
        )
    with pytest.raises(Vt08CandidateBoundaryError, match="timezone-aware"):
        inspect_architect_a_candidate(
            _a_envelope(decision_at="2026-01-05T06:00:00")
        )
