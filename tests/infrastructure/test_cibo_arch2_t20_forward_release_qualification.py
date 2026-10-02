from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.cibo_arch2_t20_forward_release_qualification import (
    TERMINAL_RECOMMENDATION,
    WAITING_RECOMMENDATION,
    qualify_t20_forward_release_population,
)
from qore.infrastructure.cibo_arch_b_forward_economic_manifest import (
    ARCH_B_FORWARD_ECONOMIC_MANIFEST_ID,
    ArchBForwardEconomicEvidenceGap,
    ArchBForwardEconomicManifest,
    ArchBForwardEconomicManifestRow,
)
from qore.infrastructure.cibo_ce2i_phase20_policy_candidate import (
    FROZEN_PHASE20_POLICY_CANDIDATE,
)
from qore.infrastructure.cibo_ce2i_phase20_qualification_plan import (
    FROZEN_PHASE20D_QUALIFICATION_PLAN,
    phase20d_qualification_plan_sha256,
)

T0 = datetime(2026, 10, 2, 0, 0, tzinfo=UTC)


def _sha(char: str) -> str:
    return "sha256:" + char * 64


def _row(index: int, *, fold_id: str, trader_id: str) -> ArchBForwardEconomicManifestRow:
    decision_at = T0 + timedelta(minutes=index)
    release_at = decision_at + timedelta(minutes=5)
    observed_at = release_at + timedelta(minutes=1)
    return ArchBForwardEconomicManifestRow(
        decision_epoch_id=f"epoch-{index}",
        decision_evidence_sha256=_sha(f"{index % 10}"),
        decision_at=decision_at,
        fold_id=fold_id,
        signal_fingerprint=f"signal-{index}",
        trader_id=trader_id,
        candidate_id=FROZEN_PHASE20_POLICY_CANDIDATE.candidate_id,
        code_sha=FROZEN_PHASE20_POLICY_CANDIDATE.code_sha,
        parameter_sha256=FROZEN_PHASE20_POLICY_CANDIDATE.parameter_sha256(),
        collector_git_sha="1" * 40,
        provider_key="ctrader-demo",
        account_ref="demo-account",
        environment="demo",
        provider_evidence_id=f"provider-{index}",
        qore_symbol="EURUSD",
        provider_symbol="EURUSD",
        provider_economics_sha256=_sha("a"),
        provider_observed_at=decision_at.isoformat(),
        provider_contract_size=Decimal("100000"),
        provider_tick_size=Decimal("0.00001"),
        provider_tick_value=Decimal("1"),
        provider_minimum_volume=Decimal("0.01"),
        provider_volume_step=Decimal("0.01"),
        provider_margin_per_volume_usd=Decimal("100"),
        provider_commission_per_volume_usd=Decimal("3"),
        provider_slippage_reserve_per_volume_usd=Decimal("0"),
        provider_bid=Decimal("1.10000"),
        provider_ask=Decimal("1.10001"),
        policy_record_sha256=_sha("b"),
        policy_selected=True,
        baseline_policy_id=FROZEN_PHASE20D_QUALIFICATION_PLAN.baseline_policy_id,
        baseline_selected=True,
        execution_risk_evidence_id=f"risk-{index}",
        executed_risk_sha256=_sha("c"),
        executed_source_volume=Decimal("0.01"),
        executed_initial_stop_risk_usd=Decimal("1"),
        settlement_sha256=_sha("d"),
        settlement_deal_ids=(100000 + index,),
        realized_net_pnl_usd=Decimal("0.25"),
        outcome_observed_at=observed_at,
        release_evidence_sha256=_sha("e"),
        release_chain_sha256=_sha("f"),
        released_stop_risk_capacity_usd=Decimal("1"),
        released_margin_capacity_usd=Decimal("1"),
        terminal_release_at=release_at,
        capital_minutes=Decimal("5"),
    )


def _ready_manifest() -> ArchBForwardEconomicManifest:
    traders = (
        "R38_GBPJPY",
        "R43_GBPUSD",
        "R42_AUDJPY",
        "R38_EURUSD",
        "R34_XAUUSD",
        "VT08_FOREX",
        "VT31_NAS100",
    )
    folds = ("WF1", "WF2", "WF3", "WF4")
    rows = tuple(
        _row(
            index,
            fold_id=folds[index % 4],
            trader_id=traders[index % 7],
        )
        for index in range(210)
    )
    return ArchBForwardEconomicManifest(
        manifest_id=ARCH_B_FORWARD_ECONOMIC_MANIFEST_ID,
        frozen_candidate_id=FROZEN_PHASE20_POLICY_CANDIDATE.candidate_id,
        frozen_code_sha=FROZEN_PHASE20_POLICY_CANDIDATE.code_sha,
        frozen_parameter_sha256=FROZEN_PHASE20_POLICY_CANDIDATE.parameter_sha256(),
        qualification_plan_id=FROZEN_PHASE20D_QUALIFICATION_PLAN.plan_id,
        qualification_plan_sha256=phase20d_qualification_plan_sha256(),
        baseline_policy_id=FROZEN_PHASE20D_QUALIFICATION_PLAN.baseline_policy_id,
        qualification_status="PASS",
        decision_epochs=100,
        candidate_rows=210,
        complete_lineage_rows=210,
        rows=rows,
        gaps=(),
        ready_for_scientific_consumption=True,
    )


def test_t20_uses_frozen_phase20d_population_gates_without_new_thresholds() -> None:
    result = qualify_t20_forward_release_population(_ready_manifest())

    assert result.minimum_candidate_outcomes == (
        FROZEN_PHASE20D_QUALIFICATION_PLAN.minimum_candidate_outcomes
    )
    assert result.required_candidate_coverage == (
        FROZEN_PHASE20D_QUALIFICATION_PLAN.minimum_candidate_outcome_coverage
    )
    assert result.complete_release_lifecycles == 210
    assert result.release_coverage == Decimal("1")
    assert result.source_manifest_scientific_ready is True
    assert result.empirical_t20_ready is True
    assert result.recommendation == TERMINAL_RECOMMENDATION
    assert result.canonical_ledger_modified is False
    assert result.phase22_v2_consumed is False
    assert result.productive_authority is False


def test_t20_waits_when_authoritative_release_lineage_is_missing() -> None:
    manifest = _ready_manifest()
    gap = ArchBForwardEconomicEvidenceGap(
        decision_evidence_sha256=_sha("9"),
        signal_fingerprint="missing-release",
        blocking=True,
        reasons=("T20_RELEASE_EVIDENCE_MISSING",),
    )
    incomplete = replace(
        manifest,
        candidate_rows=211,
        complete_lineage_rows=210,
        gaps=(gap,),
        ready_for_scientific_consumption=False,
    )

    result = qualify_t20_forward_release_population(incomplete)

    assert result.empirical_t20_ready is False
    assert result.t20_release_gap_count == 1
    assert result.blocking_gap_count == 1
    assert result.recommendation == WAITING_RECOMMENDATION


def test_t20_waits_when_manifest_is_not_scientifically_ready() -> None:
    manifest = replace(
        _ready_manifest(),
        ready_for_scientific_consumption=False,
    )

    result = qualify_t20_forward_release_population(manifest)

    assert result.source_manifest_scientific_ready is False
    assert result.empirical_t20_ready is False
    assert result.recommendation == WAITING_RECOMMENDATION


def test_t20_rejects_fold_with_too_few_release_lifecycles() -> None:
    manifest = _ready_manifest()
    rows = tuple(
        replace(
            row,
            fold_id=(
                "WF4"
                if index == 0
                else f"WF{1 + ((index - 1) % 3)}"
            ),
        )
        for index, row in enumerate(manifest.rows)
    )
    incomplete = replace(manifest, rows=rows)

    result = qualify_t20_forward_release_population(incomplete)

    assert result.four_fold_coverage_complete is False
    assert result.empirical_t20_ready is False
    assert result.recommendation == WAITING_RECOMMENDATION


def test_t20_rejects_fold_with_too_few_lineages() -> None:
    manifest = _ready_manifest()
    rows = tuple(
        replace(row, trader_id="R38_EURUSD")
        if row.fold_id == "WF4"
        else row
        for row in manifest.rows
    )
    incomplete = replace(manifest, rows=rows)

    result = qualify_t20_forward_release_population(incomplete)

    assert result.four_fold_coverage_complete is False
    assert result.empirical_t20_ready is False
    assert result.recommendation == WAITING_RECOMMENDATION


def test_t20_requires_exact_canonical_seven_lineages() -> None:
    manifest = _ready_manifest()
    rows = tuple(
        replace(row, trader_id="NON_CANONICAL_LINEAGE")
        if row.trader_id == "VT31_NAS100"
        else row
        for row in manifest.rows
    )
    incomplete = replace(manifest, rows=rows)

    result = qualify_t20_forward_release_population(incomplete)

    assert result.seven_lineage_coverage_complete is False
    assert result.empirical_t20_ready is False
    assert result.recommendation == WAITING_RECOMMENDATION
