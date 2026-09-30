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
    build_arch_a_capital_state_delivery,
)
from qore.infrastructure.cibo_arch_a_path_evidence_delivery import (
    build_arch_a_path_evidence_delivery,
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
from qore.infrastructure.cibo_compound_cycle_replay import BaseSettlementEvent
from qore.infrastructure.cibo_compound_cycle_state import (
    initialize_compound_cycle,
    settlement_sha256,
)
from qore.infrastructure.cibo_compound_path_history import (
    materialize_compound_path_history,
)
from qore.infrastructure.cibo_integrated_capital_truth import (
    RealizedProfitEquivalenceBinding,
)
from qore.infrastructure.market_test_environment import MarketRuntimeEnvironment

T0 = datetime(2026, 9, 30, 23, 0, tzinfo=UTC)


def _identity() -> CiboAccountCapitalIdentity:
    return CiboAccountCapitalIdentity(
        provider_key="ctrader-demo",
        account_ref="a-path-delivery",
        environment=MarketRuntimeEnvironment.DEMO,
    )


def _initial():
    return initialize_compound_cycle(
        account_identity=_identity(),
        opening_original_base_usd=Decimal("100"),
        t19_ledger=PortfolioAllocationLedger(
            total_stop_risk_capacity_usd=Decimal("10"),
            total_margin_capacity_usd=Decimal("100"),
            concentration_limit_by_group=(("EQUITY_BETA", Decimal("10")),),
        ),
    )


def _settlement():
    return apply_settlement(
        CmaSettlementState(
            signal_fingerprint="path-signal",
            position_id=901,
        ),
        CmaSettlementRecord(
            event="CTRADER_DEMO_EXIT_SETTLEMENT",
            deal_id=902,
            signal_fingerprint="path-signal",
            position_id=901,
            net_profit_usd=Decimal("20"),
            position_open_after=False,
        ),
    )


def _manifest() -> ArchBForwardEconomicManifest:
    frozen = FROZEN_PHASE20_POLICY_CANDIDATE
    plan = FROZEN_PHASE20D_QUALIFICATION_PLAN
    settlement = _settlement()
    row = ArchBForwardEconomicManifestRow(
        decision_epoch_id="epoch-path",
        decision_evidence_sha256="sha256:" + "1" * 64,
        decision_at=T0,
        fold_id="WF1",
        signal_fingerprint="path-signal",
        trader_id=TraderLineage.VT31_NAS100.value,
        candidate_id=frozen.candidate_id,
        code_sha=frozen.code_sha,
        parameter_sha256=frozen.parameter_sha256(),
        collector_git_sha="a" * 40,
        provider_key=_identity().provider_key,
        account_ref=_identity().account_ref,
        environment=_identity().environment.value,
        provider_evidence_id="provider-path",
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
        execution_risk_evidence_id="risk-path",
        executed_risk_sha256="sha256:" + "4" * 64,
        executed_source_volume=Decimal("0.01"),
        executed_initial_stop_risk_usd=Decimal("1"),
        settlement_sha256=settlement_sha256(settlement),
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


def _source_ledger():
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


_BINDINGS = (
    RealizedProfitEquivalenceBinding(
        source_id="profit-source",
        admission_lot_ids=("base-win:gen1",),
    ),
)


def _path_and_capital():
    initial = _initial()
    event = BaseSettlementEvent(
        event_id="base-win",
        occurred_at=T0 + timedelta(minutes=10),
        trader_id=TraderLineage.VT31_NAS100,
        settlement=_settlement(),
    )
    path = materialize_compound_path_history(
        initial_state=initial,
        initial_observed_at=T0 - timedelta(minutes=1),
        events=(event,),
    )
    final_state = replace(
        initial,
    )
    from qore.infrastructure.cibo_compound_cycle_replay import replay_compound_cycle

    final_state = replay_compound_cycle(
        initial_state=initial,
        events=(event,),
    ).final_state
    capital = build_arch_a_capital_state_delivery(
        manifest=_manifest(),
        account_identity=_identity(),
        source_ledger=_source_ledger(),
        compound_state=final_state,
        realized_profit_bindings=_BINDINGS,
    )
    return path, capital


def test_path_delivery_binds_exact_terminal_compound_state() -> None:
    path, capital = _path_and_capital()

    delivery = build_arch_a_path_evidence_delivery(
        capital_delivery=capital,
        path_history=path,
    )

    assert delivery.compound_path_history_sha256 == path.fingerprint()
    assert delivery.source_manifest_sha256 == capital.source_manifest_sha256
    assert delivery.minimum_original_base_usd == Decimal("100")
    assert delivery.minimum_compound_economic_value_usd == Decimal("0")
    assert delivery.peak_closing_realized_capital_usd == Decimal("120")
    assert delivery.terminal_closing_realized_capital_usd == Decimal("120")
    assert delivery.maximum_realized_capital_giveback_usd == Decimal("0")
    assert delivery.descriptive_path_ready is True
    assert delivery.causal_effect_identified is False
    assert delivery.economic_utility_ready is False
    assert delivery.certification_ready is False
    assert delivery.productive_authority is False
    assert delivery.fingerprint().startswith("sha256:")


def test_path_delivery_rejects_cross_state_history() -> None:
    path, capital = _path_and_capital()
    bad_terminal = replace(
        path.snapshots[-1],
        state_sha256="sha256:" + "f" * 64,
    )
    bad_path = replace(
        path,
        snapshots=path.snapshots[:-1] + (bad_terminal,),
    )

    with pytest.raises(
        ValueError,
        match="terminal state does not match capital truth",
    ):
        build_arch_a_path_evidence_delivery(
            capital_delivery=capital,
            path_history=bad_path,
        )
