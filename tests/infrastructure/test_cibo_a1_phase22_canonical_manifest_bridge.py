from __future__ import annotations

import hashlib
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.cibo_a1_phase22_canonical_manifest_bridge import (
    bridge_a1_to_canonical_phase22_intake,
)
from qore.infrastructure.cibo_a1_phase22_scientific_consumption import (
    MANIFEST_ID,
    A1Phase22PopulationFold,
    A1Phase22ScientificConsumptionManifest,
)
from qore.infrastructure.cibo_arch_a_internal_readiness import (
    PHASE22_V2_CANDIDATE_ID,
    PHASE22_V2_INTAKE_SCHEMA,
    PHASE22_V2_REQUIRED_FOLDS,
    PHASE22_V2_REQUIRED_RECEIPTS,
    PHASE22_V2_REQUIRED_TRADERS,
    ArchitectAPhase22V2ScientificIntakeReport,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)

BASE = datetime(2015, 10, 20, tzinfo=UTC)


def _sha(label: str) -> str:
    return "sha256:" + hashlib.sha256(label.encode()).hexdigest()


def _manifest() -> A1Phase22ScientificConsumptionManifest:
    folds = tuple(
        A1Phase22PopulationFold(
            fold_id=fold_id,
            decision_count=20,
            first_decision_at=BASE + timedelta(days=index * 20),
            last_decision_at=BASE + timedelta(days=(index + 1) * 20 - 1),
            population_sha256=_sha(f"fold-{fold_id}"),
        )
        for index, fold_id in enumerate(PHASE22_V2_REQUIRED_FOLDS)
    )
    return A1Phase22ScientificConsumptionManifest(
        manifest_id=MANIFEST_ID,
        candidate_id=PHASE22_V2_CANDIDATE_ID,
        code_sha="a" * 40,
        parameter_sha256=_sha("parameters"),
        amendment_sha256=_sha("amendment"),
        source_population_sha256=_sha("source-population"),
        policy_population_sha256=_sha("policy-population"),
        decision_count=80,
        policy_count=80,
        outcome_count=160,
        trader_ids=PHASE22_V2_REQUIRED_TRADERS,
        folds=folds,
        exact_policy_coverage=True,
        historical_replay_only=True,
        folds_defined_without_outcomes=True,
    )


def _intake() -> ArchitectAPhase22V2ScientificIntakeReport:
    return ArchitectAPhase22V2ScientificIntakeReport(
        schema=PHASE22_V2_INTAKE_SCHEMA,
        manifest_sha256=_sha("canonical-phase22-scientific-manifest"),
        candidate_id=PHASE22_V2_CANDIDATE_ID,
        qualification_status="PASS",
        trader_ids=PHASE22_V2_REQUIRED_TRADERS,
        fold_ids=PHASE22_V2_REQUIRED_FOLDS,
        decision_epochs=80,
        candidate_outcomes=160,
        selected_outcomes=80,
        calendar_span_days=182,
        distinct_trading_days=120,
        minimum_fold_candidate_outcomes=20,
        minimum_fold_lineages=7,
        minimum_outcomes_any_lineage=10,
        candidate_outcome_coverage="1",
        selected_outcome_coverage="1",
        baseline_selected_outcome_coverage="1",
        receipt_refs=tuple(
            (name, _sha(name))
            for name in PHASE22_V2_REQUIRED_RECEIPTS
        ),
        ready_for_scientific_reentry=True,
        blockers=(),
    )


def test_a1_bridge_uses_same_canonical_phase22_identity_as_a2() -> None:
    bridge = bridge_a1_to_canonical_phase22_intake(
        manifest=_manifest(),
        intake=_intake(),
    )

    assert bridge.canonical_phase22_manifest_sha256 == _intake().manifest_sha256
    assert bridge.a1_consumption_manifest_sha256 == _manifest().fingerprint()
    assert bridge.a2_compatible_manifest_identity is True
    assert bridge.trader_ids == PHASE22_V2_REQUIRED_TRADERS
    assert bridge.fold_ids == PHASE22_V2_REQUIRED_FOLDS
    assert bridge.certification_ready is False


def test_a1_bridge_accepts_terminal_fail_as_scientifically_consumable() -> None:
    bridge = bridge_a1_to_canonical_phase22_intake(
        manifest=_manifest(),
        intake=replace(_intake(), qualification_status="FAIL"),
    )

    assert bridge.qualification_status == "FAIL"
    assert bridge.ready_for_scientific_reentry is True


def test_a1_bridge_rejects_decision_population_count_drift() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="decision-population count drift",
    ):
        bridge_a1_to_canonical_phase22_intake(
            manifest=_manifest(),
            intake=replace(_intake(), decision_epochs=81),
        )


def test_a1_bridge_rejects_trader_lineage_drift() -> None:
    manifest = replace(
        _manifest(),
        trader_ids=PHASE22_V2_REQUIRED_TRADERS[:-1],
    )

    with pytest.raises(
        CiboCapitalManagementError,
        match="Trader lineage drift",
    ):
        bridge_a1_to_canonical_phase22_intake(
            manifest=manifest,
            intake=_intake(),
        )


def test_a1_bridge_rejects_nonadmissible_intake() -> None:
    intake = replace(
        _intake(),
        ready_for_scientific_reentry=False,
        blockers=("PHASE22_NOT_ADMISSIBLE",),
    )

    with pytest.raises(
        CiboCapitalManagementError,
        match="requires admissible terminal intake",
    ):
        bridge_a1_to_canonical_phase22_intake(
            manifest=_manifest(),
            intake=intake,
        )
