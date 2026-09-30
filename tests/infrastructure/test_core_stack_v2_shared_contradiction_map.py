from __future__ import annotations

from datetime import UTC, datetime

from qore.infrastructure.core_stack_v2.shared_contradiction_map import (
    ContradictionEvidence,
    build_contradiction_state,
)

NOW=datetime(2026,9,30,14,30,tzinfo=UTC)


def _evidence(
    evidence_id: str,
    group: str,
    *,
    support: int,
    contradiction: int,
    quality: int=10_000,
) -> ContradictionEvidence:
    return ContradictionEvidence(
        evidence_id=evidence_id,
        hypothesis_id="H1_CONTINUATION",
        as_of=NOW,
        support_bps=support,
        contradiction_bps=contradiction,
        data_quality_bps=quality,
        independent_group=group,
        evidence_refs=(f"source:{evidence_id}",),
    )


def test_high_contradiction_reduces_assertiveness() -> None:
    clean=build_contradiction_state(
        (
            _evidence("local","LOCAL",support=8_000,contradiction=1_000),
            _evidence("peer","PEER",support=8_000,contradiction=1_500),
        ),
        hypothesis_id="H1_CONTINUATION",
        required_groups=("LOCAL","PEER"),
    )
    conflicted=build_contradiction_state(
        (
            _evidence("local","LOCAL",support=8_000,contradiction=7_500),
            _evidence("peer","PEER",support=7_500,contradiction=8_000),
        ),
        hypothesis_id="H1_CONTINUATION",
        required_groups=("LOCAL","PEER"),
    )

    assert conflicted.contradiction_bps > clean.contradiction_bps
    assert conflicted.assertiveness_ceiling_bps < clean.assertiveness_ceiling_bps
    assert "CONTRADICTION_HIGH" in conflicted.reason_codes


def test_missing_required_evidence_is_explicit() -> None:
    state=build_contradiction_state(
        (_evidence("local","LOCAL",support=7_000,contradiction=2_000),),
        hypothesis_id="H1_CONTINUATION",
        required_groups=("LOCAL","PEER","MACRO"),
    )

    assert state.missing_evidence == ("MACRO","PEER")
    assert state.assertiveness_ceiling_bps <= 7_000
    assert "REQUIRED_EVIDENCE_MISSING" in state.reason_codes


def test_no_evidence_returns_unknown_not_fake_confidence() -> None:
    state=build_contradiction_state(
        (),
        hypothesis_id="H1_CONTINUATION",
        required_groups=("LOCAL","PEER"),
    )

    assert state.evidence_count == 0
    assert state.assertiveness_ceiling_bps == 0
    assert state.missing_evidence == ("LOCAL","PEER")
    assert state.reason_codes == ("NO_EVIDENCE_UNKNOWN",)


def test_contradiction_map_has_no_productive_authority() -> None:
    state=build_contradiction_state(
        (_evidence("local","LOCAL",support=5_000,contradiction=5_000),),
        hypothesis_id="H1_CONTINUATION",
        required_groups=("LOCAL",),
    )
    assert state.productive_authority is False
