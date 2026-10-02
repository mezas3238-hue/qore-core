from dataclasses import replace
from datetime import timedelta
from decimal import Decimal

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_arch2_t11_gross_edge_manifest_intake import (
    intake_t11_gross_edge_from_arch_b_manifest,
)
from qore.infrastructure.cibo_arch2_t11_nonlinear_input_freeze import (
    FROZEN_AT,
)
from qore.infrastructure.cibo_arch_b_forward_economic_manifest import (
    ARCH_B_FORWARD_ECONOMIC_MANIFEST_ID,
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

_LINEAGES = (
    TraderLineage.R38_GBPJPY,
    TraderLineage.R43_GBPUSD,
    TraderLineage.R42_AUDJPY,
    TraderLineage.R38_EURUSD,
    TraderLineage.R34_XAUUSD,
    TraderLineage.VT08_FOREX,
    TraderLineage.VT31_NAS100,
)
_SYMBOLS = (
    "GBPJPY",
    "GBPUSD",
    "AUDJPY",
    "EURUSD",
    "XAUUSD",
    "EURUSD",
    "NAS100",
)
_SHA = "sha256:" + "a" * 64


def _row(index: int) -> ArchBForwardEconomicManifestRow:
    lineage_index = index % len(_LINEAGES)
    trader = _LINEAGES[lineage_index]
    symbol = _SYMBOLS[lineage_index]
    observed = FROZEN_AT + timedelta(minutes=index + 10)
    return ArchBForwardEconomicManifestRow(
        decision_epoch_id=f"epoch-{index}",
        decision_evidence_sha256="sha256:" + f"{index + 1:064x}",
        decision_at=observed - timedelta(minutes=2),
        fold_id=f"WF{(index % 4) + 1}",
        signal_fingerprint=f"sig-{index}",
        trader_id=trader.value,
        candidate_id=FROZEN_PHASE20_POLICY_CANDIDATE.candidate_id,
        code_sha=FROZEN_PHASE20_POLICY_CANDIDATE.code_sha,
        parameter_sha256=FROZEN_PHASE20_POLICY_CANDIDATE.parameter_sha256(),
        collector_git_sha="b" * 40,
        provider_key="ctrader-demo",
        account_ref="forward-account",
        environment="demo",
        provider_evidence_id=f"provider-{index}",
        qore_symbol=symbol,
        provider_symbol=symbol,
        provider_economics_sha256=_SHA,
        provider_observed_at=observed.isoformat(),
        provider_contract_size=Decimal("100000"),
        provider_tick_size=Decimal("0.00001"),
        provider_tick_value=Decimal("1"),
        provider_minimum_volume=Decimal("0.01"),
        provider_volume_step=Decimal("0.01"),
        provider_margin_per_volume_usd=Decimal("1"),
        provider_commission_per_volume_usd=Decimal("0"),
        provider_slippage_reserve_per_volume_usd=Decimal("0"),
        provider_bid=Decimal("100"),
        provider_ask=Decimal("100.01"),
        policy_record_sha256=_SHA,
        policy_selected=True,
        baseline_policy_id=FROZEN_PHASE20D_QUALIFICATION_PLAN.baseline_policy_id,
        baseline_selected=False,
        execution_risk_evidence_id=f"risk-{index}",
        executed_risk_sha256=_SHA,
        executed_source_volume=Decimal("0.01"),
        executed_initial_stop_risk_usd=Decimal("0.50"),
        settlement_sha256=_SHA,
        settlement_deal_ids=(index + 1,),
        realized_net_pnl_usd=Decimal("1.00"),
        outcome_observed_at=observed,
        release_evidence_sha256=_SHA,
        release_chain_sha256=_SHA,
        released_stop_risk_capacity_usd=Decimal("0.50"),
        released_margin_capacity_usd=Decimal("1"),
        terminal_release_at=observed - timedelta(seconds=1),
        capital_minutes=Decimal("1"),
    )


def _manifest() -> ArchBForwardEconomicManifest:
    rows = tuple(_row(index) for index in range(210))
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
        qualification_status="PASS",
        decision_epochs=80,
        candidate_rows=len(rows),
        complete_lineage_rows=len(rows),
        rows=rows,
        gaps=(),
        ready_for_scientific_consumption=True,
    )


def test_manifest_intake_derives_gross_edge_without_refit() -> None:
    intake = intake_t11_gross_edge_from_arch_b_manifest(_manifest())

    assert intake.source_row_count == 210
    assert intake.selected_row_count == 210
    assert intake.admitted_post_freeze_count == 210
    assert intake.excluded_pre_freeze_selected_count == 0
    assert intake.excluded_unselected_count == 0
    assert intake.outcome_aware_filtering_used is False
    assert intake.model_refit_performed is False
    assert intake.phase22_v2_consumed is False

    first = intake.observations[0]
    assert first.structural_outcome_r == Decimal("2")
    assert first.stop_risk_per_volume_usd == Decimal("50")
    assert first.fresh_oos_source_authorized is True


def test_manifest_intake_filters_pre_freeze_only_by_time() -> None:
    manifest = _manifest()
    first = manifest.rows[0]
    old_time = FROZEN_AT - timedelta(minutes=1)
    old = replace(
        first,
        decision_at=old_time - timedelta(minutes=1),
        outcome_observed_at=old_time,
        terminal_release_at=old_time - timedelta(seconds=1),
        realized_net_pnl_usd=Decimal("-999"),
    )
    manifest = replace(
        manifest,
        rows=(old,) + manifest.rows[1:],
    )

    intake = intake_t11_gross_edge_from_arch_b_manifest(manifest)

    assert intake.admitted_post_freeze_count == 209
    assert intake.excluded_pre_freeze_selected_count == 1
    assert "sig-0" not in {
        item.signal_fingerprint for item in intake.observations
    }
