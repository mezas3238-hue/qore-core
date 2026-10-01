from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.cibo_a1_phase22_scientific_consumption import (
    build_a1_phase22_scientific_consumption_manifest,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_policy_store import (
    Phase20ForwardPolicyDecisionSeal,
    VersionedPhase20ForwardPolicyBook,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    Phase20ForwardDecisionSeal,
)
from qore.infrastructure.cibo_phase22_historical_replay_settlement import (
    VersionedPhase22HistoricalReplayEvidenceBook,
)

BASE = datetime(2015, 10, 20, 12, 0, tzinfo=UTC)
CANDIDATE_ID = "CIBO_USD60_6M_HOLDOUT_2015-10-19_2016-04-19_V2"


def _sha(label: str) -> str:
    return "sha256:" + hashlib.sha256(label.encode()).hexdigest()


def _decision(index: int) -> Phase20ForwardDecisionSeal:
    signal = f"signal-{index}"
    payload = {
        "evidence_kind": "HISTORICAL_REPLAY_OBSERVED",
        "candidates": [
            {
                "candidate": {
                    "signal_fingerprint": signal,
                    "trader_id": (
                        "VT31_NAS100" if index % 2 == 0 else "R38_EURUSD"
                    ),
                }
            }
        ],
    }
    at = BASE + timedelta(hours=index)
    return Phase20ForwardDecisionSeal(
        evidence_id=f"decision-{index}",
        decision_epoch_id=f"epoch-{index}",
        evidence_sha256=_sha(f"decision-{index}"),
        decision_at=at,
        candidate_id=CANDIDATE_ID,
        code_sha="a" * 40,
        parameter_sha256=_sha("params"),
        signal_fingerprints=(signal,),
        canonical_payload_json=json.dumps(payload, sort_keys=True),
        sealed_at=datetime(2026, 10, 1, 20, 0, tzinfo=UTC)
        + timedelta(seconds=index),
        seal_deadline_at=datetime(2026, 10, 1, 20, 5, tzinfo=UTC)
        + timedelta(seconds=index),
    )


def _policy(decision: Phase20ForwardDecisionSeal) -> Phase20ForwardPolicyDecisionSeal:
    record = {
        "evidence_sha256": decision.evidence_sha256,
        "selected_signal_fingerprints": list(decision.signal_fingerprints),
    }
    canonical = json.dumps(
        record,
        sort_keys=True,
        separators=(",", ":"),
    )
    return Phase20ForwardPolicyDecisionSeal(
        evidence_sha256=decision.evidence_sha256,
        policy_record_sha256="sha256:" + hashlib.sha256(
            canonical.encode()
        ).hexdigest(),
        allocator_disposition="ALLOCATE",
        selected_signal_fingerprints=decision.signal_fingerprints,
        canonical_record_json=canonical,
    )


def _books() -> tuple[
    VersionedPhase22HistoricalReplayEvidenceBook,
    VersionedPhase20ForwardPolicyBook,
]:
    decisions = tuple(_decision(index) for index in range(8))
    policies = tuple(_policy(item) for item in decisions)
    return (
        VersionedPhase22HistoricalReplayEvidenceBook(
            generation=1,
            amendment_sha256=_sha("amendment"),
            decisions=decisions,
            outcomes=(),
        ),
        VersionedPhase20ForwardPolicyBook(
            generation=1,
            decisions=policies,
        ),
    )


def test_a1_phase22_manifest_binds_one_exact_four_fold_population() -> None:
    evidence, policies = _books()

    manifest = build_a1_phase22_scientific_consumption_manifest(
        evidence_book=evidence,
        policy_book=policies,
    )

    assert manifest.decision_count == 8
    assert manifest.policy_count == 8
    assert manifest.outcome_count == 0
    assert manifest.exact_policy_coverage is True
    assert manifest.historical_replay_only is True
    assert manifest.folds_defined_without_outcomes is True
    assert tuple(item.fold_id for item in manifest.folds) == (
        "WF1",
        "WF2",
        "WF3",
        "WF4",
    )
    assert tuple(item.decision_count for item in manifest.folds) == (2, 2, 2, 2)
    assert manifest.trader_ids == ("R38_EURUSD", "VT31_NAS100")


def test_a1_phase22_manifest_rejects_code_drift() -> None:
    evidence, policies = _books()
    modified = replace(evidence.decisions[-1], code_sha="b" * 40)

    with pytest.raises(
        CiboCapitalManagementError,
        match="candidate/code/parameter drift",
    ):
        build_a1_phase22_scientific_consumption_manifest(
            evidence_book=VersionedPhase22HistoricalReplayEvidenceBook(
                generation=1,
                amendment_sha256=evidence.amendment_sha256,
                decisions=evidence.decisions[:-1] + (modified,),
                outcomes=(),
            ),
            policy_book=policies,
        )


def test_a1_phase22_manifest_rejects_incomplete_policy_surface() -> None:
    evidence, policies = _books()

    with pytest.raises(
        CiboCapitalManagementError,
        match="exactly match decisions",
    ):
        build_a1_phase22_scientific_consumption_manifest(
            evidence_book=evidence,
            policy_book=VersionedPhase20ForwardPolicyBook(
                generation=1,
                decisions=policies.decisions[:-1],
            ),
        )


def test_a1_phase22_manifest_rejects_non_historical_evidence_kind() -> None:
    evidence, policies = _books()
    first = evidence.decisions[0]
    payload = json.loads(first.canonical_payload_json)
    payload["evidence_kind"] = "FORWARD_OBSERVED"
    modified = replace(
        first,
        canonical_payload_json=json.dumps(payload, sort_keys=True),
    )

    with pytest.raises(
        CiboCapitalManagementError,
        match="requires historical replay evidence",
    ):
        build_a1_phase22_scientific_consumption_manifest(
            evidence_book=VersionedPhase22HistoricalReplayEvidenceBook(
                generation=1,
                amendment_sha256=evidence.amendment_sha256,
                decisions=(modified,) + evidence.decisions[1:],
                outcomes=(),
            ),
            policy_book=policies,
        )


def test_a1_phase22_manifest_rejects_policy_digest_drift() -> None:
    evidence, policies = _books()
    first = policies.decisions[0]
    corrupted = Phase20ForwardPolicyDecisionSeal(
        evidence_sha256=first.evidence_sha256,
        policy_record_sha256=_sha("wrong"),
        allocator_disposition=first.allocator_disposition,
        selected_signal_fingerprints=first.selected_signal_fingerprints,
        canonical_record_json=first.canonical_record_json,
    )

    with pytest.raises(CiboCapitalManagementError, match="policy digest drift"):
        build_a1_phase22_scientific_consumption_manifest(
            evidence_book=evidence,
            policy_book=VersionedPhase20ForwardPolicyBook(
                generation=1,
                decisions=(corrupted,) + policies.decisions[1:],
            ),
        )
