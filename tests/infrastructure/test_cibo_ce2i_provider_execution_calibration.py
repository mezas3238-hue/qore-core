from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.cibo_arch_b_forward_economic_manifest import (
    ARCH_B_FORWARD_ECONOMIC_MANIFEST_ID,
    ArchBForwardEconomicManifest,
    ArchBForwardEconomicManifestRow,
)
from qore.infrastructure.cibo_ce2i_phase20_execution_risk_store import (
    VersionedPhase20ExecutedRiskBook,
)
from qore.infrastructure.cibo_ce2i_phase20_outcome_reconciliation import (
    Phase20ExecutedRiskEvidence,
)
from qore.infrastructure.cibo_ce2i_phase20_policy_candidate import (
    FROZEN_PHASE20_POLICY_CANDIDATE,
)
from qore.infrastructure.cibo_ce2i_phase20_qualification_plan import (
    FROZEN_PHASE20D_QUALIFICATION_PLAN,
    phase20d_qualification_plan_sha256,
)
from qore.infrastructure.cibo_ce2i_provider_execution_calibration import (
    calibrate_ctrader_demo_forward_execution,
    provider_execution_risk_sha256,
)

T0 = datetime(2026, 9, 30, 20, 30, tzinfo=UTC)

_LINEAGES = (
    "R34_XAUUSD",
    "R38_EURUSD",
    "R43_GBPUSD",
    "R38_GBPJPY",
    "R42_AUDJPY",
    "VT08_FOREX",
    "VT31_NAS100",
)

_SYMBOLS = (
    ("XAUUSD", "XAUUSD"),
    ("EURUSD", "EURUSD"),
    ("GBPUSD", "GBPUSD"),
    ("GBPJPY", "GBPJPY"),
    ("AUDJPY", "AUDJPY"),
    ("EURUSD", "EURUSD"),
    ("NAS100", "US100"),
)


def _population() -> tuple[
    ArchBForwardEconomicManifest,
    VersionedPhase20ExecutedRiskBook,
]:
    frozen = FROZEN_PHASE20_POLICY_CANDIDATE
    plan = FROZEN_PHASE20D_QUALIFICATION_PLAN
    rows = []
    risks = []
    for index in range(plan.minimum_candidate_outcomes):
        lineage = _LINEAGES[index % len(_LINEAGES)]
        qore_symbol, provider_symbol = _SYMBOLS[index % len(_SYMBOLS)]
        decision_at = T0 + timedelta(minutes=index)
        risk_id = f"risk-{index}"
        executed_risk = Decimal("1.005")
        rows.append(
            ArchBForwardEconomicManifestRow(
                decision_epoch_id=f"epoch-{index}",
                decision_evidence_sha256=(
                    "sha256:" + f"{index + 1:064x}"
                ),
                decision_at=decision_at,
                fold_id=f"WF{(index % plan.fold_count) + 1}",
                signal_fingerprint=f"signal-{index}",
                trader_id=lineage,
                candidate_id=frozen.candidate_id,
                code_sha=frozen.code_sha,
                parameter_sha256=frozen.parameter_sha256(),
                collector_git_sha="a" * 40,
                provider_key="ctrader-demo",
                account_ref="12345",
                environment="demo",
                provider_evidence_id=f"provider-{index}",
                qore_symbol=qore_symbol,
                provider_symbol=provider_symbol,
                provider_economics_sha256="sha256:" + "2" * 64,
                provider_contract_size=Decimal("1"),
                provider_tick_size=Decimal("0.01"),
                provider_tick_value=Decimal("1"),
                provider_observed_at=(
                    decision_at - timedelta(milliseconds=100)
                ).isoformat(),
                provider_minimum_volume=Decimal("0.01"),
                provider_volume_step=Decimal("0.01"),
                provider_margin_per_volume_usd=Decimal("1"),
                provider_commission_per_volume_usd=Decimal("0"),
                provider_slippage_reserve_per_volume_usd=Decimal("0"),
                provider_bid=Decimal("100"),
                provider_ask=Decimal("101"),
                policy_record_sha256="sha256:" + "3" * 64,
                policy_selected=index < plan.minimum_selected_outcomes,
                baseline_policy_id=plan.baseline_policy_id,
                baseline_selected=True,
                execution_risk_evidence_id=risk_id,
                executed_risk_sha256="sha256:" + "4" * 64,
                executed_source_volume=Decimal("0.01"),
                executed_initial_stop_risk_usd=executed_risk,
                settlement_sha256="sha256:" + "5" * 64,
                settlement_deal_ids=(index + 1,),
                realized_net_pnl_usd=Decimal("2"),
                outcome_observed_at=decision_at + timedelta(minutes=10),
                release_evidence_sha256="sha256:" + "6" * 64,
                release_chain_sha256="sha256:" + "7" * 64,
                released_stop_risk_capacity_usd=executed_risk,
                released_margin_capacity_usd=Decimal("1"),
                terminal_release_at=decision_at + timedelta(minutes=9),
                capital_minutes=Decimal("9"),
            )
        )
        risks.append(
            Phase20ExecutedRiskEvidence(
                evidence_id=risk_id,
                decision_evidence_sha256=rows[-1].decision_evidence_sha256,
                signal_fingerprint=rows[-1].signal_fingerprint,
                qore_symbol=qore_symbol,
                provider_order_ref=f"order-{index}",
                side="long",
                position_id=index + 1,
                authorized_source_volume=Decimal("0.01"),
                filled_source_volume=Decimal("0.01"),
                weighted_fill_price=Decimal("101.01"),
                intended_entry_price=Decimal("101"),
                structural_stop_price=Decimal("99"),
                stop_risk_per_volume_at_intended_entry_usd=Decimal("100"),
                executed_initial_stop_risk_usd=executed_risk,
                observed_at=decision_at + timedelta(milliseconds=1500),
                fill_evidence_refs=(f"fill-{index}",),
                fill_reconciled=True,
                mutation_outcome_known=True,
                capital_deployed_at=(
                    decision_at + timedelta(milliseconds=1000)
                ),
            )
        )
        rows[-1] = replace(
            rows[-1],
            executed_risk_sha256=provider_execution_risk_sha256(
                risks[-1]
            ),
        )
    manifest = ArchBForwardEconomicManifest(
        manifest_id=ARCH_B_FORWARD_ECONOMIC_MANIFEST_ID,
        frozen_candidate_id=frozen.candidate_id,
        frozen_code_sha=frozen.code_sha,
        frozen_parameter_sha256=frozen.parameter_sha256(),
        qualification_plan_id=plan.plan_id,
        qualification_plan_sha256=phase20d_qualification_plan_sha256(),
        baseline_policy_id=plan.baseline_policy_id,
        qualification_status="PASS",
        decision_epochs=plan.minimum_decision_epochs,
        candidate_rows=len(rows),
        complete_lineage_rows=len(rows),
        rows=tuple(rows),
        gaps=(),
        ready_for_scientific_consumption=True,
    )
    return manifest, VersionedPhase20ExecutedRiskBook(
        generation=len(risks),
        evidences=tuple(risks),
    )


def _empty_manifest() -> ArchBForwardEconomicManifest:
    frozen = FROZEN_PHASE20_POLICY_CANDIDATE
    plan = FROZEN_PHASE20D_QUALIFICATION_PLAN
    return ArchBForwardEconomicManifest(
        manifest_id=ARCH_B_FORWARD_ECONOMIC_MANIFEST_ID,
        frozen_candidate_id=frozen.candidate_id,
        frozen_code_sha=frozen.code_sha,
        frozen_parameter_sha256=frozen.parameter_sha256(),
        qualification_plan_id=plan.plan_id,
        qualification_plan_sha256=phase20d_qualification_plan_sha256(),
        baseline_policy_id=plan.baseline_policy_id,
        qualification_status="NOT_READY",
        decision_epochs=0,
        candidate_rows=0,
        complete_lineage_rows=0,
        rows=(),
        gaps=(),
        ready_for_scientific_consumption=False,
    )


def test_calibration_mechanics_use_provider_quote_to_weighted_fill() -> None:
    manifest, risks = _population()

    report = calibrate_ctrader_demo_forward_execution(
        manifest=manifest,
        executed_risk_book=risks,
        frozen_at=T0 + timedelta(hours=4),
    )

    assert report.total_observations == 200
    assert report.manifest_scientifically_ready is True
    assert report.all_complete_rows_reconciled is True
    assert report.required_symbol_coverage_met is True
    assert report.minimum_symbol_observations_met is True
    assert report.empirical_slippage_calibrated is True
    assert report.execution_model_ready is True
    assert report.blockers == ()
    assert len(report.symbol_summaries) == 6
    assert all(
        item.p95_adverse_slippage_bps > 0
        for item in report.symbol_summaries
    )
    first = report.observations[0]
    assert first.provider_quote_price == Decimal("101")
    assert first.weighted_fill_price == Decimal("101.01")
    assert first.signed_slippage_price == Decimal("0.01")
    assert first.signed_slippage_cost_per_volume_usd == Decimal("1")
    assert first.adverse_slippage_cost_per_volume_usd == Decimal("1")
    assert first.provider_quote_age_ms == Decimal("100")
    assert first.decision_to_fill_ms == Decimal("1000")
    assert first.fill_to_risk_reconciliation_ms == Decimal("500")
    assert report.historical_2017_exact_claimed is False
    assert report.holdout_outcomes_used is False
    assert report.target_aware is False
    assert report.productive_authority is False
    assert report.fingerprint().startswith("sha256:")


def test_calibration_fails_closed_without_real_forward_population() -> None:
    report = calibrate_ctrader_demo_forward_execution(
        manifest=_empty_manifest(),
        executed_risk_book=VersionedPhase20ExecutedRiskBook(generation=0),
        frozen_at=T0,
    )

    assert report.empirical_slippage_calibrated is False
    assert report.execution_model_ready is False
    assert report.total_observations == 0
    assert "FORWARD_MANIFEST_NOT_SCIENTIFICALLY_READY" in report.blockers
    assert "REQUIRED_PROVIDER_SYMBOL_COVERAGE_INCOMPLETE" in report.blockers


def test_favorable_fill_is_preserved_as_negative_signed_slippage() -> None:
    manifest, risks = _population()
    first = risks.evidences[0]
    favorable = Phase20ExecutedRiskEvidence(
        evidence_id=first.evidence_id,
        decision_evidence_sha256=first.decision_evidence_sha256,
        signal_fingerprint=first.signal_fingerprint,
        qore_symbol=first.qore_symbol,
        provider_order_ref=first.provider_order_ref,
        side=first.side,
        position_id=first.position_id,
        authorized_source_volume=first.authorized_source_volume,
        filled_source_volume=first.filled_source_volume,
        weighted_fill_price=Decimal("100.99"),
        intended_entry_price=first.intended_entry_price,
        structural_stop_price=first.structural_stop_price,
        stop_risk_per_volume_at_intended_entry_usd=(
            first.stop_risk_per_volume_at_intended_entry_usd
        ),
        executed_initial_stop_risk_usd=Decimal("0.995"),
        observed_at=first.observed_at,
        fill_evidence_refs=first.fill_evidence_refs,
        fill_reconciled=True,
        mutation_outcome_known=True,
        capital_deployed_at=first.capital_deployed_at,
    )
    first_row = manifest.rows[0]
    adjusted_row = replace(
        first_row,
        executed_risk_sha256=provider_execution_risk_sha256(favorable),
        executed_initial_stop_risk_usd=Decimal("0.995"),
        released_stop_risk_capacity_usd=Decimal("0.995"),
    )
    adjusted_manifest = replace(
        manifest,
        rows=(adjusted_row,) + manifest.rows[1:],
    )
    adjusted_risks = VersionedPhase20ExecutedRiskBook(
        generation=risks.generation,
        evidences=(favorable,) + risks.evidences[1:],
    )

    report = calibrate_ctrader_demo_forward_execution(
        manifest=adjusted_manifest,
        executed_risk_book=adjusted_risks,
        frozen_at=T0 + timedelta(hours=4),
    )

    assert report.observations[0].signed_slippage_price == Decimal("-0.01")
    assert report.observations[0].signed_slippage_bps < 0
    assert report.observations[0].adverse_slippage_bps == 0
    assert (
        report.observations[0].signed_slippage_cost_per_volume_usd
        == Decimal("-1")
    )
    assert report.observations[0].adverse_slippage_cost_per_volume_usd == 0
