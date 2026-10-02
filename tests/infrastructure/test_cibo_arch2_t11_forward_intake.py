from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.cibo_arch2_t11_forward_intake import (
    build_t11_gross_edge_forward_intake,
)
from qore.infrastructure.cibo_arch_b_forward_economic_manifest import (
    ARCH_B_FORWARD_ECONOMIC_MANIFEST_ID,
    ArchBForwardEconomicManifest,
    ArchBForwardEconomicManifestRow,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase20_policy_candidate import (
    FROZEN_PHASE20_POLICY_CANDIDATE,
)
from qore.infrastructure.cibo_ce2i_phase20_qualification_plan import (
    FROZEN_PHASE20D_QUALIFICATION_PLAN,
    phase20d_qualification_plan_sha256,
)

T0 = datetime(2026, 10, 2, 0, 0, tzinfo=UTC)
TRADERS = (
    "VT08_FOREX",
    "R34_XAUUSD",
    "R38_EURUSD",
    "R43_GBPUSD",
    "R38_GBPJPY",
    "R42_AUDJPY",
    "VT31_NAS100",
)
SYMBOLS = (
    "EURUSD",
    "XAUUSD",
    "EURUSD",
    "GBPUSD",
    "GBPJPY",
    "AUDJPY",
    "NAS100",
)


def _sha(char: str) -> str:
    return "sha256:" + char * 64


def _row(index: int) -> ArchBForwardEconomicManifestRow:
    decision_at = T0 + timedelta(minutes=index)
    observed_at = decision_at + timedelta(minutes=10)
    trader = TRADERS[index % len(TRADERS)]
    symbol = SYMBOLS[index % len(SYMBOLS)]
    return ArchBForwardEconomicManifestRow(
        decision_epoch_id=f"epoch-{index}",
        decision_evidence_sha256=_sha(str(index % 10)),
        decision_at=decision_at,
        fold_id=f"WF{index % 4 + 1}",
        signal_fingerprint=f"signal-{index}",
        trader_id=trader,
        candidate_id=FROZEN_PHASE20_POLICY_CANDIDATE.candidate_id,
        code_sha=FROZEN_PHASE20_POLICY_CANDIDATE.code_sha,
        parameter_sha256=FROZEN_PHASE20_POLICY_CANDIDATE.parameter_sha256(),
        collector_git_sha="1" * 40,
        provider_key="ctrader-demo",
        account_ref="demo-account",
        environment="demo",
        provider_evidence_id=f"provider-{index}",
        qore_symbol=symbol,
        provider_symbol="USTEC" if symbol == "NAS100" else symbol,
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
        provider_bid=Decimal("1.1"),
        provider_ask=Decimal("1.10001"),
        policy_record_sha256=_sha("b"),
        policy_selected=True,
        baseline_policy_id=FROZEN_PHASE20D_QUALIFICATION_PLAN.baseline_policy_id,
        baseline_selected=True,
        execution_risk_evidence_id=f"risk-{index}",
        executed_risk_sha256=_sha("c"),
        executed_source_volume=Decimal("0.01"),
        executed_initial_stop_risk_usd=Decimal("2"),
        settlement_sha256=_sha("d"),
        settlement_deal_ids=(100000 + index,),
        realized_net_pnl_usd=Decimal("1"),
        outcome_observed_at=observed_at,
        release_evidence_sha256=_sha("e"),
        release_chain_sha256=_sha("f"),
        released_stop_risk_capacity_usd=Decimal("2"),
        released_margin_capacity_usd=Decimal("1"),
        terminal_release_at=observed_at - timedelta(minutes=1),
        capital_minutes=Decimal("9"),
    )


def _manifest(*, ready: bool) -> ArchBForwardEconomicManifest:
    rows = tuple(_row(index) for index in range(210))
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
        ready_for_scientific_consumption=ready,
    )


def test_t11_forward_intake_derives_structural_r_without_refit_or_v2() -> None:
    intake = build_t11_gross_edge_forward_intake(
        manifest=_manifest(ready=True),
        fresh_population_authorization_id="fresh-phase20-forward-001",
        fresh_population_authorized=True,
    )

    assert intake.selected_row_count == 210
    assert len(intake.observations) == 210
    first = intake.observations[0]
    assert first.structural_outcome_r == Decimal("0.5")
    assert first.stop_risk_per_volume_usd == Decimal("200")
    assert first.outcome_reconciled is True
    assert first.provider_bound is True
    assert first.fresh_oos_source_authorized is True
    assert first.model_refit_performed is False
    assert intake.phase22_v2_consumed is False
    assert intake.canonical_ledger_modified is False
    assert intake.productive_authority is False


def test_t11_forward_intake_refuses_implicit_authorization() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="not explicitly authorized",
    ):
        build_t11_gross_edge_forward_intake(
            manifest=_manifest(ready=True),
            fresh_population_authorization_id="fresh-phase20-forward-001",
            fresh_population_authorized=False,
        )


def test_t11_forward_intake_refuses_non_scientific_manifest() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="not ready for scientific consumption",
    ):
        build_t11_gross_edge_forward_intake(
            manifest=_manifest(ready=False),
            fresh_population_authorization_id="fresh-phase20-forward-001",
            fresh_population_authorized=True,
        )
