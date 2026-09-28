from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    Phase20ForwardDecisionSeal,
    VersionedPhase20ForwardEvidenceBook,
)
from qore.infrastructure.cibo_ce2i_phase20_t14_path_readiness import (
    assess_phase20_t14_path_readiness,
)
from qore.infrastructure.ctrader_demo_live_behavior_lab import (
    BehaviorStage,
    LiveBehaviorEvent,
)

BASE = datetime(2026, 9, 28, 5, 0, tzinfo=UTC)


def _decision() -> Phase20ForwardDecisionSeal:
    payload = {
        "evidence_kind": "FORWARD_OBSERVED",
        "candidates": [],
    }
    return Phase20ForwardDecisionSeal(
        evidence_id="decision",
        decision_epoch_id="epoch",
        evidence_sha256="sha256:" + "a" * 64,
        decision_at=BASE,
        candidate_id="candidate",
        code_sha="code",
        parameter_sha256="params",
        signal_fingerprints=("signal-1",),
        canonical_payload_json=json.dumps(payload, sort_keys=True),
        sealed_at=BASE + timedelta(milliseconds=100),
        seal_deadline_at=BASE + timedelta(seconds=2),
    )


def _event(
    *,
    minute: int,
    name: str,
    payload: dict[str, object],
) -> LiveBehaviorEvent:
    return LiveBehaviorEvent(
        case_id="signal:signal-1",
        observed_at=BASE + timedelta(minutes=minute),
        source="test",
        stage=BehaviorStage.POSITION,
        event=name,
        trader="R38_EURUSD",
        symbol="EURUSD",
        signal_fingerprint="signal-1",
        position_id=101,
        payload=payload,
    )


def test_t14_binds_existing_longitudinal_path_and_settlement_cost() -> None:
    events = (
        _event(
            minute=1,
            name="CTRADER_DEMO_POSITION_PATH_SAMPLE",
            payload={"stop_loss": "0.95", "volume": "0.10"},
        ),
        _event(
            minute=2,
            name="CTRADER_DEMO_PARTIAL_SETTLEMENT",
            payload={"commission": "-0.50"},
        ),
        _event(
            minute=3,
            name="CTRADER_DEMO_POSITION_PATH_SAMPLE",
            payload={"stop_loss": "1.01", "volume": "0.05"},
        ),
    )
    report = assess_phase20_t14_path_readiness(
        evidence_book=VersionedPhase20ForwardEvidenceBook(
            generation=1,
            decisions=(_decision(),),
        ),
        events=events,
    )

    assert report.stream_bound is True
    assert report.observed_path_samples == 2
    assert report.path_positions == 1
    assert report.longitudinal_path_positions == 1
    assert report.reconciled_stop_positions == 1
    assert report.execution_cost_bound_positions == 1
    assert report.protection_change_positions == 1
    assert report.volume_change_positions == 1
    assert report.qualifying_intervention_positions == 1
    assert report.blockers == ()


def test_t14_ignores_unbound_behavior_signal() -> None:
    event = LiveBehaviorEvent(
        case_id="other",
        observed_at=BASE + timedelta(minutes=1),
        source="test",
        stage=BehaviorStage.POSITION,
        event="CTRADER_DEMO_POSITION_PATH_SAMPLE",
        trader="R38_EURUSD",
        symbol="EURUSD",
        signal_fingerprint="not-forward-bound",
        position_id=202,
        payload={"stop_loss": "0.95", "volume": "0.10"},
    )
    report = assess_phase20_t14_path_readiness(
        evidence_book=VersionedPhase20ForwardEvidenceBook(
            generation=1,
            decisions=(_decision(),),
        ),
        events=(event,),
    )

    assert report.stream_bound is False
    assert report.path_positions == 0
    assert "NO_FORWARD_BOUND_POSITION_PATH_SAMPLES" in report.blockers
