from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

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
from qore.infrastructure.cibo_ce2i_phase20_t15_reservation_counterfactual import (
    assess_t15_reservation_counterfactual_lineage,
)
from qore.infrastructure.cibo_phase22_historical_replay_economics_amendment import (
    EXECUTION_ECONOMICS_KIND,
)
from qore.infrastructure.cibo_phase22_historical_replay_settlement import (
    Phase22HistoricalReplayOutcomeSeal,
    VersionedPhase22HistoricalReplayEvidenceBook,
)

BASE = datetime(2015, 10, 20, 12, 0, tzinfo=UTC)
OPTION_ID = "known-option:VT31_NAS100:future-signal"


def _sha(label: str) -> str:
    return "sha256:" + hashlib.sha256(label.encode()).hexdigest()


def _decision(
    *,
    evidence_id: str,
    evidence_sha256: str,
    step: int,
    at: datetime,
    signals: tuple[str, ...],
    known_options: list[dict[str, object]],
) -> Phase20ForwardDecisionSeal:
    payload = {
        "evidence_kind": "HISTORICAL_REPLAY_OBSERVED",
        "current_step": step,
        "horizon_steps": 2,
        "known_options": known_options,
    }
    return Phase20ForwardDecisionSeal(
        evidence_id=evidence_id,
        decision_epoch_id=evidence_id,
        evidence_sha256=evidence_sha256,
        decision_at=at,
        candidate_id="CIBO_USD60_6M_HOLDOUT_2015-10-19_2016-04-19_V2",
        code_sha="a" * 40,
        parameter_sha256=_sha("params"),
        signal_fingerprints=signals,
        canonical_payload_json=json.dumps(payload, sort_keys=True),
        sealed_at=datetime(2026, 10, 1, 20, 0, tzinfo=UTC),
        seal_deadline_at=datetime(2026, 10, 1, 20, 0, 2, tzinfo=UTC),
    )


def _known_option(*, known_as_of: datetime = BASE) -> dict[str, object]:
    return {
        "option": {
            "opportunity_id": OPTION_ID,
            "decision_step": 11,
        },
        "known_as_of": known_as_of.isoformat(),
        "active_at_decision": True,
        "expires_at": (BASE + timedelta(hours=2)).isoformat(),
        "cancelled_at": None,
    }


def _origin() -> Phase20ForwardDecisionSeal:
    return _decision(
        evidence_id="origin",
        evidence_sha256=_sha("origin"),
        step=10,
        at=BASE,
        signals=(),
        known_options=[_known_option()],
    )


def _future() -> Phase20ForwardDecisionSeal:
    return _decision(
        evidence_id="future",
        evidence_sha256=_sha("future"),
        step=11,
        at=BASE + timedelta(hours=1),
        signals=("future-signal",),
        known_options=[],
    )


def _outcome() -> Phase22HistoricalReplayOutcomeSeal:
    return Phase22HistoricalReplayOutcomeSeal(
        evidence_id="phase22-replay-outcome:fixture",
        decision_evidence_sha256=_sha("future"),
        signal_fingerprint="future-signal",
        trader_id="VT31_NAS100",
        qore_symbol="NAS100",
        observed_at=BASE + timedelta(hours=2),
        gross_structural_outcome_r=Decimal("1"),
        provider_execution_adjustment_usd=Decimal("1"),
        decision_provider_cost_proxy_usd=Decimal("0.5"),
        realized_net_pnl_usd=Decimal("9"),
        executed_initial_stop_risk_usd=Decimal("10"),
        realized_structural_outcome_r=Decimal("1"),
        capital_deployed_at=BASE + timedelta(hours=1, minutes=5),
        capital_released_at=BASE + timedelta(hours=1, minutes=35),
        capital_minutes=Decimal("30"),
        provider_calibration_sha256=_sha("calibration"),
        amendment_sha256=_sha("amendment"),
        execution_economics_kind=EXECUTION_ECONOMICS_KIND,
        counterfactual_historical_replay=True,
        historical_broker_fills_claimed=False,
        fabricated_execution_evidence_used=False,
        outcome_reconciled=True,
    )


def _book(
    *,
    origin: Phase20ForwardDecisionSeal | None = None,
    outcomes: tuple[Phase22HistoricalReplayOutcomeSeal, ...] | None = None,
) -> VersionedPhase22HistoricalReplayEvidenceBook:
    return VersionedPhase22HistoricalReplayEvidenceBook(
        generation=1,
        amendment_sha256=_sha("amendment"),
        decisions=(origin or _origin(), _future()),
        outcomes=(_outcome(),) if outcomes is None else outcomes,
    )


def _policy(
    *,
    considered: tuple[str, ...] = (OPTION_ID,),
    reserve_risk: str = "5",
    reserve_margin: str = "10",
) -> Phase20ForwardPolicyDecisionSeal:
    record = {
        "evidence_sha256": _sha("origin"),
        "mpc_plan": {
            "considered_option_ids": list(considered),
            "reserve_stop_risk_usd": reserve_risk,
            "reserve_margin_usd": reserve_margin,
        },
    }
    canonical = json.dumps(
        record,
        sort_keys=True,
        separators=(",", ":"),
    )
    return Phase20ForwardPolicyDecisionSeal(
        evidence_sha256=_sha("origin"),
        policy_record_sha256="sha256:" + hashlib.sha256(
            canonical.encode()
        ).hexdigest(),
        allocator_disposition="PRESERVE_CAPACITY",
        selected_signal_fingerprints=(),
        canonical_record_json=canonical,
    )


def _policies(
    policy: Phase20ForwardPolicyDecisionSeal | None = None,
) -> VersionedPhase20ForwardPolicyBook:
    return VersionedPhase20ForwardPolicyBook(
        generation=1,
        decisions=(policy or _policy(),),
    )


def test_t15_phase22_lineage_binds_reservation_to_later_replay_outcome() -> None:
    report = assess_t15_reservation_counterfactual_lineage(
        evidence_book=_book(),
        policy_book=_policies(),
    )

    assert report.lineage_complete is True
    assert report.origin_epochs_with_known_options == 1
    assert report.policy_bound_origin_epochs == 1
    assert report.nonzero_reserve_origin_epochs == 1
    assert report.matured_option_instances == 1
    assert report.materialized_candidate_instances == 1
    assert report.reconciled_materialized_outcomes == 1
    assert report.counterfactual_effect_identified is False
    assert report.scientific_blockers == (
        "COUNTERFACTUAL_RESERVATION_CAUSAL_EFFECT_NOT_IDENTIFIED",
        "T15_CAUSAL_UTILITY_AND_WF1_WF4_REPLICATION_REQUIRED",
    )


def test_t15_phase22_lineage_rejects_future_known_option_at_origin() -> None:
    origin = _decision(
        evidence_id="origin",
        evidence_sha256=_sha("origin"),
        step=10,
        at=BASE,
        signals=(),
        known_options=[_known_option(known_as_of=BASE + timedelta(minutes=1))],
    )

    with pytest.raises(
        CiboCapitalManagementError,
        match="postdates reservation decision",
    ):
        assess_t15_reservation_counterfactual_lineage(
            evidence_book=_book(origin=origin),
            policy_book=_policies(),
        )


def test_t15_phase22_lineage_reports_considered_set_mismatch() -> None:
    report = assess_t15_reservation_counterfactual_lineage(
        evidence_book=_book(),
        policy_book=_policies(_policy(considered=())),
    )

    assert report.lineage_complete is False
    assert "T15_CONSIDERED_OPTION_SET_MISMATCH" in report.lineage_blockers


def test_t15_phase22_lineage_requires_reconciled_materialized_outcome() -> None:
    report = assess_t15_reservation_counterfactual_lineage(
        evidence_book=_book(outcomes=()),
        policy_book=_policies(),
    )

    assert report.materialized_candidate_instances == 1
    assert report.reconciled_materialized_outcomes == 0
    assert (
        "T15_MATERIALIZED_OPTION_OUTCOME_RECONCILIATION_INCOMPLETE"
        in report.lineage_blockers
    )


def test_t15_phase22_lineage_requires_nonzero_reservation() -> None:
    report = assess_t15_reservation_counterfactual_lineage(
        evidence_book=_book(),
        policy_book=_policies(
            _policy(reserve_risk="0", reserve_margin="0")
        ),
    )

    assert report.lineage_complete is False
    assert (
        "T15_NONZERO_RESERVATION_NOT_PROVEN_FOR_ALL_ORIGINS"
        in report.lineage_blockers
    )
