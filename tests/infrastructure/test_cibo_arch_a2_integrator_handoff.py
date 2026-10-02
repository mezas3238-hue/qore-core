from __future__ import annotations

from qore.infrastructure.cibo_arch_a2_integrator_handoff import (
    ARCH_A_BASE_SHA,
    A2_BRANCH,
    CAPITAL_SCIENCE_ENGINEERING_CLOSURE_SCHEMA,
    HISTORICAL_COMPOUND_ADAPTER_ID,
    HISTORICAL_COMPOUND_CONTRACT_ID,
    INTERNAL_CAPITAL_MARKET_DELIVERY_ID,
    SCHEMA,
    A2HistoricalCompoundLineageDelivery,
    A2InternalCapitalMarketDelivery,
    build_architect_a2_capital_science_engineering_closure,
    build_architect_a2_integrator_handoff,
)
from qore.infrastructure.cibo_arch_a2_internal_readiness import (
    evaluate_architect_a2_internal_readiness,
)
from qore.infrastructure.cibo_arch_a2_scientific_closure import (
    A2_WORKSTREAM_IDS,
    ArchitectA2ScientificClosurePacket,
)

MANIFEST = "sha256:" + "1" * 64
HEAD = "2" * 40


def _closure(
    *,
    falsified_ids: tuple[str, ...] = (),
    incomplete: bool = False,
) -> ArchitectA2ScientificClosurePacket:
    if incomplete:
        return ArchitectA2ScientificClosurePacket(
            phase22_manifest_sha256=MANIFEST,
            receipt_count=0,
            terminal_count=0,
            completed_ids=(),
            falsified_ids=(),
            external_ids=(),
            missing_ids=A2_WORKSTREAM_IDS,
            exact_a2_surface=True,
            ready_for_integrator=False,
        )
    falsified = set(falsified_ids)
    completed = tuple(
        item for item in A2_WORKSTREAM_IDS if item not in falsified
    )
    return ArchitectA2ScientificClosurePacket(
        phase22_manifest_sha256=MANIFEST,
        receipt_count=17,
        terminal_count=17,
        completed_ids=completed,
        falsified_ids=falsified_ids,
        external_ids=(),
        missing_ids=(),
        exact_a2_surface=True,
        ready_for_integrator=True,
    )


def test_a2_integrator_handoff_binds_exact_green_lane() -> None:
    receipt = build_architect_a2_integrator_handoff(
        a2_head_sha=HEAD,
        readiness=evaluate_architect_a2_internal_readiness(),
        closure=_closure(),
    )

    assert receipt.schema == SCHEMA
    assert receipt.branch == A2_BRANCH
    assert receipt.arch_a_base_sha == ARCH_A_BASE_SHA
    assert receipt.a2_head_sha == HEAD
    assert receipt.terminal_count == 17
    assert receipt.completed_ids == A2_WORKSTREAM_IDS
    assert receipt.falsified_ids == ()
    assert receipt.blockers == ()
    assert receipt.ready_for_integrator is True
    assert receipt.ledger_update_authority is False
    assert receipt.merge_authority is False
    assert receipt.certification_claimed is False
    assert receipt.productive_authority is False
    assert receipt.fingerprint().startswith("sha256:")


def test_a2_integrator_handoff_accepts_legitimate_falsification() -> None:
    receipt = build_architect_a2_integrator_handoff(
        a2_head_sha=HEAD,
        readiness=evaluate_architect_a2_internal_readiness(),
        closure=_closure(falsified_ids=("GEN-C12",)),
    )

    assert receipt.terminal_count == 17
    assert receipt.falsified_ids == ("GEN-C12",)
    assert receipt.ready_for_integrator is True
    assert receipt.blockers == ()


def test_a2_integrator_handoff_blocks_incomplete_science() -> None:
    receipt = build_architect_a2_integrator_handoff(
        a2_head_sha=HEAD,
        readiness=evaluate_architect_a2_internal_readiness(),
        closure=_closure(incomplete=True),
    )

    assert receipt.terminal_count == 0
    assert receipt.ready_for_integrator is False
    assert receipt.blockers == ("A2_SCIENTIFIC_CLOSURE_INCOMPLETE",)



def test_a2_historical_compound_crosslane_delivery_is_replay_safe() -> None:
    delivery = A2HistoricalCompoundLineageDelivery(
        contract_id=HISTORICAL_COMPOUND_CONTRACT_ID,
        source_workstream="COMPOUND_ENGINE",
        source_head=HEAD,
        artifact_sha256="sha256:" + "3" * 64,
        source_population_sha256="sha256:" + "4" * 64,
        a1_manifest_sha256="sha256:" + "5" * 64,
        adapter_identity=HISTORICAL_COMPOUND_ADAPTER_ID,
        historical_replay_supported=True,
        historical_broker_ids_required=False,
        historical_broker_ids_emitted=False,
        current_demo_ids_relabelled_as_historical=False,
        fabricated_execution_ids_used=False,
        realized_profit_only=True,
        floating_pnl_used_as_capital=False,
        capital_conservation_proven=True,
        double_spend_detected=False,
        decision_before_outcome_preserved=True,
        deterministic_replay=True,
    )

    assert delivery.source_workstream == "COMPOUND_ENGINE"
    assert delivery.historical_broker_ids_emitted is False
    assert delivery.floating_pnl_used_as_capital is False
    assert delivery.capital_conservation_proven is True
    assert delivery.fingerprint().startswith("sha256:")


def test_a2_internal_capital_market_crosslane_delivery_is_complete() -> None:
    delivery = A2InternalCapitalMarketDelivery(
        contract_id=INTERNAL_CAPITAL_MARKET_DELIVERY_ID,
        source_workstream="INTERNAL_CAPITAL_MARKET",
        source_head=HEAD,
        artifact_sha256="sha256:" + "6" * 64,
        source_population_sha256="sha256:" + "7" * 64,
        policy_identity=(
            "CIBO_GENC6_ROBUST_PARETO_MARGINAL_CAPITAL_MARKET_SHADOW_V1"
        ),
        true_scarcity_bound=True,
        capital_conservation_proven=True,
    )

    assert delivery.source_workstream == "INTERNAL_CAPITAL_MARKET"
    assert delivery.true_scarcity_bound is True
    assert delivery.capital_conservation_proven is True
    assert delivery.fingerprint().startswith("sha256:")


def test_a2_capital_science_engineering_closes_with_phase22_external() -> None:
    receipt = build_architect_a2_capital_science_engineering_closure(
        a2_head_sha=HEAD,
        readiness=evaluate_architect_a2_internal_readiness(),
        closure=_closure(incomplete=True),
    )

    assert receipt.schema == CAPITAL_SCIENCE_ENGINEERING_CLOSURE_SCHEMA
    assert receipt.owned_workstream_count == 17
    assert receipt.internal_readiness_passed is True
    assert receipt.crosslane_contracts_complete is True
    assert receipt.local_actionable_blocker_count == 0
    assert receipt.phase22_scientific_terminal_count == 0
    assert receipt.phase22_scientific_pending_count == 17
    assert receipt.phase22_scientific_evidence_external is True
    assert receipt.lane_engineering_closed is True
    assert receipt.ready_for_integrator_engineering_handoff is True
    assert receipt.certification_claimed is False
    assert receipt.productive_authority is False
