from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    Phase20ForwardDecisionSeal,
    VersionedPhase20ForwardEvidenceBook,
)
from qore.infrastructure.cibo_ce2i_phase20_t14_intervention_population import (
    assess_phase20_t14_natural_intervention_population,
)
from qore.infrastructure.ctrader_demo_live_behavior_lab import (
    BehaviorStage,
    LiveBehaviorEvent,
)

BASE = datetime(2026, 9, 28, 5, 0, tzinfo=UTC)


def _decision() -> Phase20ForwardDecisionSeal:
    payload = {"evidence_kind": "FORWARD_OBSERVED", "candidates": []}
    return Phase20ForwardDecisionSeal(
        evidence_id="decision",
        decision_epoch_id="epoch",
        evidence_sha256="sha256:" + ("a" * 64),
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
    stage: BehaviorStage,
    payload: dict[str, object],
    trader: str = "R38_EURUSD",
) -> LiveBehaviorEvent:
    return LiveBehaviorEvent(
        case_id="signal:signal-1",
        observed_at=BASE + timedelta(minutes=minute),
        source="test",
        stage=stage,
        event=name,
        trader=trader,
        symbol="EURUSD",
        signal_fingerprint="signal-1",
        position_id=101,
        payload=payload,
    )


def _book() -> VersionedPhase20ForwardEvidenceBook:
    return VersionedPhase20ForwardEvidenceBook(
        generation=1,
        decisions=(_decision(),),
    )


def test_t14_natural_intervention_requires_physical_before_after_change() -> None:
    events = (
        _event(
            minute=1,
            name="CTRADER_DEMO_POSITION_PATH_SAMPLE",
            stage=BehaviorStage.POSITION,
            payload={"stop_loss": "0.95", "volume": "0.10"},
        ),
        _event(
            minute=2,
            name="CTRADER_DEMO_STOP_ADVANCED",
            stage=BehaviorStage.MANAGEMENT,
            payload={},
        ),
        _event(
            minute=3,
            name="CTRADER_DEMO_POSITION_PATH_SAMPLE",
            stage=BehaviorStage.POSITION,
            payload={"stop_loss": "1.01", "volume": "0.10"},
        ),
        _event(
            minute=4,
            name="CTRADER_DEMO_EXIT_SETTLEMENT",
            stage=BehaviorStage.EXIT,
            payload={"net_profit": "7.5"},
        ),
    )

    audit = assess_phase20_t14_natural_intervention_population(
        evidence_book=_book(),
        events=events,
    )

    assert audit.forward_bound_positions == 1
    assert audit.physical_management_positions == 1
    assert audit.management_events == 1
    assert audit.qualifying_interventions == 1
    assert audit.pre_post_path_positions == 1
    assert audit.protection_transition_positions == 1
    assert audit.volume_transition_positions == 0
    assert audit.terminally_settled_after_intervention_positions == 1
    assert audit.eligible_natural_intervention_positions == 1
    assert audit.represented_lineages == ("R38_EURUSD",)
    assert audit.trader_owned_management_preserved is True
    assert audit.cibo_derisk_policy_identified is False
    assert audit.fresh_oos_utility_demonstrated is False
    assert audit.blockers == (
        "NATURAL_TRADER_INTERVENTIONS_DO_NOT_IDENTIFY_CIBO_DERISK_POLICY",
        "FRESH_OOS_DERISK_UTILITY_ANALYSIS_REQUIRED",
    )


def test_t14_passive_management_observation_is_not_intervention() -> None:
    events = (
        _event(
            minute=1,
            name="CTRADER_DEMO_POSITION_PATH_SAMPLE",
            stage=BehaviorStage.POSITION,
            payload={"stop_loss": "0.95", "volume": "0.10"},
        ),
        _event(
            minute=2,
            name="CTRADER_DEMO_MANAGEMENT_OBSERVATION",
            stage=BehaviorStage.MANAGEMENT,
            payload={},
        ),
        _event(
            minute=3,
            name="CTRADER_DEMO_POSITION_PATH_SAMPLE",
            stage=BehaviorStage.POSITION,
            payload={"stop_loss": "1.01", "volume": "0.10"},
        ),
        _event(
            minute=4,
            name="CTRADER_DEMO_EXIT_SETTLEMENT",
            stage=BehaviorStage.EXIT,
            payload={},
        ),
    )

    audit = assess_phase20_t14_natural_intervention_population(
        evidence_book=_book(),
        events=events,
    )

    assert audit.physical_management_positions == 0
    assert audit.eligible_natural_intervention_positions == 0
    assert "NO_TRADER_OWNED_PHYSICAL_MANAGEMENT_EVENTS" in audit.blockers


def test_t14_partial_requires_later_terminal_settlement() -> None:
    events = (
        _event(
            minute=1,
            name="CTRADER_DEMO_POSITION_PATH_SAMPLE",
            stage=BehaviorStage.POSITION,
            payload={"stop_loss": "0.95", "volume": "0.10"},
            trader="VT31_NAS100",
        ),
        _event(
            minute=2,
            name="CTRADER_DEMO_DOL1_PARTIAL_BANKED",
            stage=BehaviorStage.MANAGEMENT,
            payload={},
            trader="VT31_NAS100",
        ),
        _event(
            minute=3,
            name="CTRADER_DEMO_POSITION_PATH_SAMPLE",
            stage=BehaviorStage.POSITION,
            payload={"stop_loss": "0.95", "volume": "0.05"},
            trader="VT31_NAS100",
        ),
        _event(
            minute=4,
            name="CTRADER_DEMO_PARTIAL_SETTLEMENT",
            stage=BehaviorStage.MANAGEMENT,
            payload={"net_profit": "3"},
            trader="VT31_NAS100",
        ),
    )

    audit = assess_phase20_t14_natural_intervention_population(
        evidence_book=_book(),
        events=events,
    )

    assert audit.qualifying_interventions == 1
    assert audit.volume_transition_positions == 1
    assert audit.terminally_settled_after_intervention_positions == 0
    assert audit.eligible_natural_intervention_positions == 0
    assert "NO_TERMINAL_SETTLEMENT_AFTER_T14_INTERVENTION" in audit.blockers


def test_t14_ignores_unbound_signal() -> None:
    event = LiveBehaviorEvent(
        case_id="other",
        observed_at=BASE + timedelta(minutes=1),
        source="test",
        stage=BehaviorStage.MANAGEMENT,
        event="CTRADER_DEMO_STOP_ADVANCED",
        trader="R38_EURUSD",
        symbol="EURUSD",
        signal_fingerprint="not-forward",
        position_id=202,
        payload={},
    )

    audit = assess_phase20_t14_natural_intervention_population(
        evidence_book=_book(),
        events=(event,),
    )

    assert audit.forward_bound_positions == 0
    assert "NO_FORWARD_BOUND_T14_POSITION_EVENTS" in audit.blockers
