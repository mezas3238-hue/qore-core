from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.cibo_a1_phase22_scientific_consumption import (
    MANIFEST_ID,
    A1Phase22PopulationFold,
    A1Phase22ScientificConsumptionManifest,
)
from qore.infrastructure.cibo_a1_t08_phase22_oos_binding import (
    A1T08Phase22EpochBinding,
    bind_t08_oos_to_phase22,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    Phase20ForwardDecisionSeal,
)
from qore.infrastructure.cibo_ce2i_phase20_t08_oos_ablation import (
    T08NettingShadowEpoch,
)
from qore.infrastructure.cibo_phase22_historical_replay_economics_amendment import (
    EXECUTION_ECONOMICS_KIND,
)
from qore.infrastructure.cibo_phase22_historical_replay_settlement import (
    Phase22HistoricalReplayOutcomeSeal,
    VersionedPhase22HistoricalReplayEvidenceBook,
)
from qore.infrastructure.cibo_phase22_holdout_v2_source_receipt import (
    V2_SOURCE_BINDINGS,
    phase22_v2_holdout_source_receipt_sha256,
)

BASE = datetime(2015, 10, 20, 12, 0, tzinfo=UTC)
CANDIDATE_ID = "CIBO_USD60_6M_HOLDOUT_2015-10-19_2016-04-19_V2"
FOLDS = ("WF1", "WF2", "WF3", "WF4")

SOURCE_COLLECTOR_GIT_SHAS = tuple(
    sorted({item.collector_git_sha for item in V2_SOURCE_BINDINGS})
)


def _sha(label: str) -> str:
    return "sha256:" + hashlib.sha256(label.encode()).hexdigest()


def _decision(index: int) -> Phase20ForwardDecisionSeal:
    signal = f"signal-{index:02d}"
    decision_at = BASE + timedelta(hours=index)
    payload = {
        "evidence_kind": "HISTORICAL_REPLAY_OBSERVED",
        "candidates": [
            {
                "candidate": {
                    "signal_fingerprint": signal,
                    "trader_id": "VT31_NAS100",
                }
            }
        ],
    }
    return Phase20ForwardDecisionSeal(
        evidence_id=f"decision-{index:02d}",
        decision_epoch_id=f"epoch-{index:02d}",
        evidence_sha256=_sha(f"decision-{index:02d}"),
        decision_at=decision_at,
        candidate_id=CANDIDATE_ID,
        code_sha="a" * 40,
        parameter_sha256=_sha("parameters"),
        signal_fingerprints=(signal,),
        canonical_payload_json=json.dumps(payload, sort_keys=True),
        sealed_at=datetime(2026, 10, 1, 20, 0, tzinfo=UTC)
        + timedelta(seconds=index),
        seal_deadline_at=datetime(2026, 10, 1, 20, 5, tzinfo=UTC)
        + timedelta(seconds=index),
    )


def _outcome(
    decision: Phase20ForwardDecisionSeal,
    index: int,
) -> Phase22HistoricalReplayOutcomeSeal:
    deployed = decision.decision_at + timedelta(minutes=2)
    released = decision.decision_at + timedelta(minutes=20)
    observed = decision.decision_at + timedelta(minutes=30)
    evidence_id = (
        "phase22-replay-outcome:"
        + hashlib.sha256(f"outcome-{index:02d}".encode()).hexdigest()
    )
    return Phase22HistoricalReplayOutcomeSeal(
        evidence_id=evidence_id,
        decision_evidence_sha256=decision.evidence_sha256,
        signal_fingerprint=decision.signal_fingerprints[0],
        trader_id="VT31_NAS100",
        qore_symbol="NAS100",
        observed_at=observed,
        gross_structural_outcome_r=Decimal("1"),
        provider_execution_adjustment_usd=Decimal("0"),
        decision_provider_cost_proxy_usd=Decimal("0"),
        realized_net_pnl_usd=Decimal("5"),
        executed_initial_stop_risk_usd=Decimal("5"),
        realized_structural_outcome_r=Decimal("1"),
        capital_deployed_at=deployed,
        capital_released_at=released,
        capital_minutes=Decimal("18"),
        provider_calibration_sha256=_sha("calibration"),
        amendment_sha256=_sha("amendment"),
        execution_economics_kind=EXECUTION_ECONOMICS_KIND,
        counterfactual_historical_replay=True,
        historical_broker_fills_claimed=False,
        fabricated_execution_evidence_used=False,
        outcome_reconciled=True,
    )


def _shadow_epoch(
    decision: Phase20ForwardDecisionSeal,
    outcome: Phase22HistoricalReplayOutcomeSeal,
    index: int,
) -> T08NettingShadowEpoch:
    return T08NettingShadowEpoch(
        epoch_id=f"t08-shadow-{index:02d}",
        decision_at=decision.decision_at,
        shadow_sealed_at=decision.decision_at + timedelta(minutes=1),
        outcome_observed_at=outcome.observed_at,
        baseline_selected_count=1,
        treatment_selected_count=2,
        baseline_realized_net_pnl_usd=Decimal("1"),
        treatment_realized_net_pnl_usd=Decimal("2"),
        baseline_peak_loss_usd=Decimal("1"),
        treatment_peak_loss_usd=Decimal("1"),
        treatment_gross_stop_risk_usd=Decimal("10"),
        treatment_netted_risk_usd=Decimal("8"),
        netting_credit_usd=Decimal("2"),
        risk_mapping_evidence_id=f"mapping-{index:02d}",
        correlation_evidence_id=f"correlation-{index:02d}",
        outcome_evidence_ids=(outcome.evidence_id,),
    )


def _fold_digest(decisions: tuple[Phase20ForwardDecisionSeal, ...]) -> str:
    raw = json.dumps(
        [item.evidence_sha256 for item in decisions],
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _fixture() -> tuple[
    A1Phase22ScientificConsumptionManifest,
    VersionedPhase22HistoricalReplayEvidenceBook,
    tuple[A1T08Phase22EpochBinding, ...],
]:
    decisions = tuple(_decision(index) for index in range(32))
    outcomes = tuple(
        _outcome(decision, index)
        for index, decision in enumerate(decisions)
    )
    fold_objects: list[A1Phase22PopulationFold] = []
    bindings: list[A1T08Phase22EpochBinding] = []
    for fold_index, fold_id in enumerate(FOLDS):
        start = fold_index * 8
        subset = decisions[start : start + 8]
        fold_objects.append(
            A1Phase22PopulationFold(
                fold_id=fold_id,
                decision_count=len(subset),
                first_decision_at=subset[0].decision_at,
                last_decision_at=subset[-1].decision_at,
                population_sha256=_fold_digest(subset),
            )
        )
        for index in range(start, start + 8):
            bindings.append(
                A1T08Phase22EpochBinding(
                    fold_id=fold_id,
                    phase22_decision_sha256=decisions[index].evidence_sha256,
                    shadow_epoch=_shadow_epoch(
                        decisions[index],
                        outcomes[index],
                        index,
                    ),
                )
            )

    manifest = A1Phase22ScientificConsumptionManifest(
        manifest_id=MANIFEST_ID,
        candidate_id=CANDIDATE_ID,
        code_sha="a" * 40,
        parameter_sha256=_sha("parameters"),
        amendment_sha256=_sha("amendment"),
        source_population_sha256=_sha("source-population"),
        policy_population_sha256=_sha("policy-population"),
        decision_count=32,
        policy_count=32,
        outcome_count=32,
        trader_ids=("VT31_NAS100",),
        folds=tuple(fold_objects),
        exact_policy_coverage=True,
        historical_replay_only=True,
        folds_defined_without_outcomes=True,
    )
    evidence_book = VersionedPhase22HistoricalReplayEvidenceBook(
        source_receipt_sha256=phase22_v2_holdout_source_receipt_sha256(),
        source_collector_git_shas=SOURCE_COLLECTOR_GIT_SHAS,
        generation=1,
        amendment_sha256=_sha("amendment"),
        decisions=decisions,
        outcomes=outcomes,
    )
    return manifest, evidence_book, tuple(bindings)


def test_t08_oos_is_bound_to_exact_phase22_decisions_outcomes_and_folds() -> None:
    manifest, evidence_book, bindings = _fixture()

    report = bind_t08_oos_to_phase22(
        manifest=manifest,
        evidence_book=evidence_book,
        bindings=bindings,
    )

    assert report.bound_decision_count == 32
    assert report.exact_phase22_population_bound is True
    assert report.replay_outcome_lineage_bound is True
    assert report.oos_report.fresh_oos_utility_demonstrated is True
    assert report.oos_report.required_folds == 4
    assert report.factor_map_certified_here is False
    assert report.correlation_state_certified_here is False
    assert report.netting_credit_authorized is False


def test_t08_oos_rejects_missing_phase22_decision_coverage() -> None:
    manifest, evidence_book, bindings = _fixture()

    with pytest.raises(
        CiboCapitalManagementError,
        match="exact replay decision population",
    ):
        bind_t08_oos_to_phase22(
            manifest=manifest,
            evidence_book=evidence_book,
            bindings=bindings[:-1],
        )


def test_t08_oos_rejects_outcome_from_different_decision() -> None:
    manifest, evidence_book, bindings = _fixture()
    bad_epoch = replace(
        bindings[0].shadow_epoch,
        outcome_evidence_ids=(
            bindings[1].shadow_epoch.outcome_evidence_ids[0],
        ),
    )
    bad_binding = replace(bindings[0], shadow_epoch=bad_epoch)

    with pytest.raises(
        CiboCapitalManagementError,
        match="outcome lineage is not replay-bound",
    ):
        bind_t08_oos_to_phase22(
            manifest=manifest,
            evidence_book=evidence_book,
            bindings=(bad_binding,) + bindings[1:],
        )


def test_t08_oos_rejects_wrong_fold_assignment() -> None:
    manifest, evidence_book, bindings = _fixture()
    wrong = replace(bindings[0], fold_id="WF2")

    with pytest.raises(
        CiboCapitalManagementError,
        match="fold population differs from A1 manifest",
    ):
        bind_t08_oos_to_phase22(
            manifest=manifest,
            evidence_book=evidence_book,
            bindings=(wrong,) + bindings[1:],
        )


def test_t08_oos_rejects_decision_timestamp_drift() -> None:
    manifest, evidence_book, bindings = _fixture()
    bad_epoch = replace(
        bindings[0].shadow_epoch,
        decision_at=bindings[0].shadow_epoch.decision_at
        + timedelta(seconds=1),
    )
    bad_binding = replace(bindings[0], shadow_epoch=bad_epoch)

    with pytest.raises(
        CiboCapitalManagementError,
        match="chronology drift",
    ):
        bind_t08_oos_to_phase22(
            manifest=manifest,
            evidence_book=evidence_book,
            bindings=(bad_binding,) + bindings[1:],
        )
