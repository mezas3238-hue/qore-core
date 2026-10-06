from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
)
from qore.infrastructure.cibo_arch_a_capital_state_delivery import (
    ArchACapitalStateDeliveryRow,
    build_arch_a_capital_state_delivery,
)
from qore.infrastructure.cibo_arch_b_forward_economic_manifest import (
    ARCH_B_FORWARD_ECONOMIC_MANIFEST_ID,
    ArchBForwardEconomicManifest,
    ArchBForwardEconomicManifestRow,
)
from qore.infrastructure.cibo_capital_management_authority import CapitalSource
from qore.infrastructure.cibo_capital_source_ledger import CapitalSourceLedger
from qore.infrastructure.cibo_ce2i_phase20_policy_candidate import (
    FROZEN_PHASE20_POLICY_CANDIDATE,
)
from qore.infrastructure.cibo_ce2i_phase20_qualification_plan import (
    FROZEN_PHASE20D_QUALIFICATION_PLAN,
    phase20d_qualification_plan_sha256,
)
from qore.infrastructure.cibo_ce2i_portfolio_allocation_ledger import (
    PortfolioAllocationLedger,
)
from qore.infrastructure.cibo_cma_settlement_ledger import (
    CmaSettlementRecord,
    CmaSettlementState,
    apply_settlement,
)
from qore.infrastructure.cibo_compound_cycle_state import (
    ingest_base_settlement,
    initialize_compound_cycle,
    settlement_sha256,
)
from qore.infrastructure.cibo_integrated_capital_truth import (
    RealizedProfitEquivalenceBinding,
)
from qore.infrastructure.market_test_environment import MarketRuntimeEnvironment

T0 = datetime(2026, 9, 30, 21, 45, tzinfo=UTC)


def _identity() -> CiboAccountCapitalIdentity:
    return CiboAccountCapitalIdentity(
        provider_key="ctrader-demo",
        account_ref="a-delivery",
        environment=MarketRuntimeEnvironment.DEMO,
    )


def _settlement() -> CmaSettlementState:
    return apply_settlement(
        CmaSettlementState(
            signal_fingerprint="signal-a",
            position_id=901,
        ),
        CmaSettlementRecord(
            event="CTRADER_DEMO_EXIT_SETTLEMENT",
            deal_id=902,
            signal_fingerprint="signal-a",
            position_id=901,
            net_profit_usd=Decimal("20"),
            position_open_after=False,
        ),
    )


def _compound_state():
    state = initialize_compound_cycle(
        account_identity=_identity(),
        opening_original_base_usd=Decimal("100"),
        t19_ledger=PortfolioAllocationLedger(
            total_stop_risk_capacity_usd=Decimal("10"),
            total_margin_capacity_usd=Decimal("100"),
            concentration_limit_by_group=(("EQUITY_BETA", Decimal("10")),),
        ),
    )
    return ingest_base_settlement(
        state,
        event_id="base-win",
        occurred_at=T0 + timedelta(minutes=10),
        trader_id=TraderLineage.VT31_NAS100,
        settlement=_settlement(),
    )


def _source_ledger() -> CapitalSourceLedger:
    return (
        CapitalSourceLedger()
        .add_source(
            source_id="gen0",
            source=CapitalSource.ORIGINAL_BASE_CAPITAL,
            proven_amount_usd=Decimal("100"),
        )
        .add_source(
            source_id="profit-source",
            source=CapitalSource.REALIZED_PROFIT,
            proven_amount_usd=Decimal("20"),
        )
    )


def _manifest() -> ArchBForwardEconomicManifest:
    frozen = FROZEN_PHASE20_POLICY_CANDIDATE
    plan = FROZEN_PHASE20D_QUALIFICATION_PLAN
    row = ArchBForwardEconomicManifestRow(
        decision_epoch_id="epoch-a",
        decision_evidence_sha256="sha256:" + "1" * 64,
        decision_at=T0,
        fold_id="WF1",
        signal_fingerprint="signal-a",
        trader_id=TraderLineage.VT31_NAS100.value,
        candidate_id=frozen.candidate_id,
        code_sha=frozen.code_sha,
        parameter_sha256=frozen.parameter_sha256(),
        collector_git_sha="a" * 40,
        provider_key=_identity().provider_key,
        account_ref=_identity().account_ref,
        environment=_identity().environment.value,
        provider_evidence_id="provider-a",
        qore_symbol="NAS100",
        provider_symbol="US100",
        provider_economics_sha256="sha256:" + "2" * 64,
        provider_observed_at=(T0 - timedelta(seconds=1)).isoformat(),
        provider_contract_size=Decimal("1"),
        provider_tick_size=Decimal("1"),
        provider_tick_value=Decimal("1"),
        provider_minimum_volume=Decimal("0.01"),
        provider_volume_step=Decimal("0.01"),
        provider_margin_per_volume_usd=Decimal("1"),
        provider_commission_per_volume_usd=Decimal("0"),
        provider_slippage_reserve_per_volume_usd=Decimal("0"),
        provider_bid=Decimal("20000"),
        provider_ask=Decimal("20001"),
        policy_record_sha256="sha256:" + "3" * 64,
        policy_selected=True,
        baseline_policy_id=plan.baseline_policy_id,
        baseline_selected=True,
        execution_risk_evidence_id="risk-a",
        executed_risk_sha256="sha256:" + "4" * 64,
        executed_source_volume=Decimal("0.01"),
        executed_initial_stop_risk_usd=Decimal("1"),
        settlement_sha256=settlement_sha256(_settlement()),
        settlement_deal_ids=(902,),
        realized_net_pnl_usd=Decimal("20"),
        outcome_observed_at=T0 + timedelta(minutes=10),
        release_evidence_sha256="sha256:" + "5" * 64,
        release_chain_sha256="sha256:" + "6" * 64,
        released_stop_risk_capacity_usd=Decimal("1"),
        released_margin_capacity_usd=Decimal("1"),
        terminal_release_at=T0 + timedelta(minutes=9),
        capital_minutes=Decimal("9"),
    )
    return ArchBForwardEconomicManifest(
        manifest_id=ARCH_B_FORWARD_ECONOMIC_MANIFEST_ID,
        frozen_candidate_id=frozen.candidate_id,
        frozen_code_sha=frozen.code_sha,
        frozen_parameter_sha256=frozen.parameter_sha256(),
        qualification_plan_id=plan.plan_id,
        qualification_plan_sha256=phase20d_qualification_plan_sha256(),
        baseline_policy_id=plan.baseline_policy_id,
        qualification_status="NOT_READY",
        decision_epochs=1,
        candidate_rows=1,
        complete_lineage_rows=1,
        rows=(row,),
        gaps=(),
        ready_for_scientific_consumption=False,
    )


_BINDINGS = (
    RealizedProfitEquivalenceBinding(
        source_id="profit-source",
        admission_lot_ids=("base-win:gen1",),
    ),
)


def test_base_forward_settlement_is_delivered_without_fabricated_deployment() -> None:
    manifest = _manifest()
    delivery = build_arch_a_capital_state_delivery(
        manifest=manifest,
        account_identity=_identity(),
        source_ledger=_source_ledger(),
        compound_state=_compound_state(),
        realized_profit_bindings=_BINDINGS,
    )

    assert delivery.source_manifest_sha256 == manifest.fingerprint()
    assert delivery.source_ledger_sha256 is not None
    assert delivery.compound_cycle_state_sha256 is not None
    assert delivery.exact_settlement_population_bound is True
    assert delivery.integrated_capital_truth_pass is True
    assert delivery.settlement_delivery_ready is True
    assert delivery.forward_manifest_scientifically_ready is False
    assert delivery.full_a001_capital_path_ready is False
    assert "FORWARD_MANIFEST_NOT_SCIENTIFICALLY_READY" in delivery.gaps
    assert "PROFIT_GIVEBACK_PATH_NOT_MATERIALIZED" in delivery.gaps

    row = delivery.rows[0]
    assert row.source_kind == "BASE_CAPITAL"
    assert row.source_manifest_sha256 == manifest.fingerprint()
    assert row.deployment_id is None
    assert row.source_lot_id is None
    assert row.source_capital_generation is None
    assert row.deployed_capital_usd is None
    assert row.capital_lock_minutes is None
    assert delivery.fingerprint().startswith("sha256:")


def test_forward_settlement_identity_drift_fails_closed() -> None:
    manifest = _manifest()
    bad = replace(
        manifest.rows[0],
        signal_fingerprint="different-signal",
    )

    with pytest.raises(ValueError):
        build_arch_a_capital_state_delivery(
            manifest=replace(manifest, rows=(bad,)),
            account_identity=_identity(),
            source_ledger=_source_ledger(),
            compound_state=_compound_state(),
            realized_profit_bindings=_BINDINGS,
        )


def test_compound_row_cannot_omit_deployment_lineage() -> None:
    with pytest.raises(
        ValueError,
        match="requires complete deployment lineage",
    ):
        ArchACapitalStateDeliveryRow(
            source_manifest_sha256="sha256:" + "1" * 64,
            decision_evidence_sha256="sha256:" + "2" * 64,
            signal_fingerprint="signal",
            trader_id=TraderLineage.VT31_NAS100.value,
            settlement_sha256="sha256:" + "3" * 64,
            settlement_occurred_at=T0,
            source_kind="COMPOUND_CAPITAL",
            realized_net_pnl_usd=Decimal("1"),
            provider_economics_sha256="sha256:" + "4" * 64,
            deployment_id=None,
            market_event_id=None,
            decision_id=None,
            deployed_at=None,
            source_lot_id=None,
            source_capital_generation=None,
            deployed_capital_usd=None,
            stop_risk_usd=None,
            margin_usd=None,
            capital_lock_minutes=None,
        )
