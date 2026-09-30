from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
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
from qore.infrastructure.cibo_integrated_capital_forward_binding import (
    bind_forward_population_to_integrated_capital_truth,
    manifest_trader_lineages,
)
from qore.infrastructure.cibo_integrated_capital_truth import (
    RealizedProfitEquivalenceBinding,
)
from qore.infrastructure.market_test_environment import MarketRuntimeEnvironment

T0 = datetime(2026, 9, 30, 21, 0, tzinfo=UTC)


def _identity() -> CiboAccountCapitalIdentity:
    return CiboAccountCapitalIdentity(
        provider_key="ctrader-demo",
        account_ref="forward-integrated",
        environment=MarketRuntimeEnvironment.DEMO,
    )


def _settlement() -> CmaSettlementState:
    return apply_settlement(
        CmaSettlementState(
            signal_fingerprint="signal-forward",
            position_id=901,
        ),
        CmaSettlementRecord(
            event="CTRADER_DEMO_EXIT_SETTLEMENT",
            deal_id=902,
            signal_fingerprint="signal-forward",
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
            concentration_limit_by_group=(
                ("EQUITY_BETA", Decimal("10")),
            ),
        ),
    )
    return ingest_base_settlement(
        state,
        event_id="forward-profit",
        occurred_at=T0 + timedelta(minutes=10),
        trader_id=TraderLineage.VT31_NAS100,
        settlement=_settlement(),
    )


def _source_ledger(*, realized_profit: str = "20") -> CapitalSourceLedger:
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
            proven_amount_usd=Decimal(realized_profit),
        )
    )


def _manifest() -> ArchBForwardEconomicManifest:
    frozen = FROZEN_PHASE20_POLICY_CANDIDATE
    plan = FROZEN_PHASE20D_QUALIFICATION_PLAN
    row = ArchBForwardEconomicManifestRow(
        decision_epoch_id="epoch-forward",
        decision_evidence_sha256="sha256:" + "1" * 64,
        decision_at=T0,
        fold_id="WF1",
        signal_fingerprint="signal-forward",
        trader_id=TraderLineage.VT31_NAS100.value,
        candidate_id=frozen.candidate_id,
        code_sha=frozen.code_sha,
        parameter_sha256=frozen.parameter_sha256(),
        collector_git_sha="a" * 40,
        provider_key=_identity().provider_key,
        account_ref=_identity().account_ref,
        environment=_identity().environment.value,
        provider_evidence_id="provider-forward",
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
        execution_risk_evidence_id="risk-forward",
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
        admission_lot_ids=("profit:gen1",),
    ),
)


def test_exact_forward_population_reconciles_truth_but_stays_scientifically_blocked() -> None:
    report = bind_forward_population_to_integrated_capital_truth(
        manifest=_manifest(),
        account_identity=_identity(),
        source_ledger=_source_ledger(),
        compound_state=_compound_state(),
        realized_profit_bindings=_BINDINGS,
    )

    assert report.account_scope_match is True
    assert report.settlement_population_exact is True
    assert report.positive_profit_reconciliation_match is True
    assert report.integrated_capital_truth_pass is True
    assert report.manifest_positive_profit_usd == Decimal("20")
    assert report.compound_positive_profit_usd == Decimal("20")
    assert report.source_ledger_sha256 is not None
    assert report.compound_cycle_state_sha256 is not None
    assert report.ready_for_scientific_consumption is False
    assert report.blockers == ("FORWARD_MANIFEST_NOT_SCIENTIFICALLY_READY",)
    assert report.runtime_authority is False
    assert report.sizing_authority is False
    assert report.risk_authority is False
    assert report.execution_authority is False


def test_settlement_population_mismatch_blocks_cross_ledger_truth() -> None:
    manifest = _manifest()
    bad_row = replace(
        manifest.rows[0],
        settlement_sha256="sha256:" + "9" * 64,
    )
    bad_manifest = replace(manifest, rows=(bad_row,))

    report = bind_forward_population_to_integrated_capital_truth(
        manifest=bad_manifest,
        account_identity=_identity(),
        source_ledger=_source_ledger(),
        compound_state=_compound_state(),
        realized_profit_bindings=_BINDINGS,
    )

    assert report.settlement_population_exact is False
    assert report.integrated_capital_truth_pass is False
    assert report.source_ledger_sha256 is None
    assert (
        "FORWARD_COMPOUND_SETTLEMENT_POPULATION_MISMATCH"
        in report.blockers
    )
    assert "INTEGRATED_CAPITAL_TRUTH_POPULATION_GATE_BLOCKED" in report.blockers


def test_source_ledger_amount_drift_remains_fail_closed() -> None:
    report = bind_forward_population_to_integrated_capital_truth(
        manifest=_manifest(),
        account_identity=_identity(),
        source_ledger=_source_ledger(realized_profit="19"),
        compound_state=_compound_state(),
        realized_profit_bindings=_BINDINGS,
    )

    assert report.settlement_population_exact is True
    assert report.positive_profit_reconciliation_match is True
    assert report.integrated_capital_truth_pass is False
    assert "INTEGRATED_CAPITAL_TRUTH_NOT_RECONCILED" in report.blockers


def test_manifest_lineages_are_canonical() -> None:
    assert manifest_trader_lineages(_manifest()) == (
        TraderLineage.VT31_NAS100,
    )
