"""Phase 20G structural ablation and mechanism-interaction contract.

This module uses synthetic, contemporaneous fixtures only. It measures whether
independently certified CE2I mechanisms have distinct and safely composable
effects. It does not estimate market value, optimize a policy, reuse Phase-19J
validation, or claim historical provider economics.

The purpose is to falsify unsafe coupling such as:
- execution economics creating funding authority;
- a positive execution cap bypassing a stale/recovery regime gate;
- optionality reserve changing Trader geometry;
- de-risking inventing new capital;
- input order deciding cross-Trader allocation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
    CiboCapitalMissionPolicy,
    derive_cibo_capital_mission,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CapitalSource,
    CapitalStage,
    CiboCapitalManagementError,
    TraderOpportunityEnvelope,
)
from qore.infrastructure.cibo_capital_source_ledger import CapitalSourceLedger
from qore.infrastructure.cibo_capital_source_ledger_store import (
    DurableCapitalSourceLedgerStore,
)
from qore.infrastructure.cibo_ce2i_causal_expectation import (
    CausalExpectationBasis,
    CausalOpportunityExpectation,
)
from qore.infrastructure.cibo_ce2i_dynamic_derisking import (
    CiboDeRiskAction,
    CiboDeRiskingInput,
    plan_dynamic_derisking,
)
from qore.infrastructure.cibo_ce2i_execution_efficiency import (
    ExecutionCostCurveInput,
    execution_efficient_volume_cap,
)
from qore.infrastructure.cibo_ce2i_expansion_proposal import reserve_expansion_proposal
from qore.infrastructure.cibo_ce2i_opportunity_competition import (
    CapitalOpportunityCandidate,
    OpportunityAllocationBudget,
    allocate_competing_opportunities,
)
from qore.infrastructure.cibo_ce2i_optionality import (
    KnownCapitalOption,
    plan_capital_optionality,
)
from qore.infrastructure.cibo_ce2i_regime_selector import (
    CiboCapitalRegimeState,
    CiboRegimePosture,
    CorrelationState,
    LiquidityState,
    ProviderCondition,
    VolatilityState,
    select_ce2i_tools_for_regime,
)
from qore.infrastructure.cibo_cma_capital_observation import CmaCapitalObservation
from qore.infrastructure.market_test_environment import MarketRuntimeEnvironment


@dataclass(frozen=True, slots=True)
class Phase20InteractionCase:
    case_id: str
    mechanisms: tuple[str, ...]
    passed: bool
    detail: str

    def __post_init__(self) -> None:
        if not self.case_id or not self.mechanisms or not self.detail:
            raise CiboCapitalManagementError(
                "Phase20G case identity/mechanisms/detail are required"
            )
        if type(self.passed) is not bool:
            raise CiboCapitalManagementError("Phase20G passed must be bool")


@dataclass(frozen=True, slots=True)
class Phase20InteractionAblationReport:
    identity: str
    cases: tuple[Phase20InteractionCase, ...]
    synthetic_contract_evidence_only: bool = True
    empirical_value_claimed: bool = False
    historical_provider_economics_claimed: bool = False
    phase19j_burned_validation_reused: bool = False
    policy_selected: bool = False
    allocation_authority: bool = False
    risk_authority: bool = False
    execution_authority: bool = False
    live_authorized: bool = False
    real_capital_authorized: bool = False

    def __post_init__(self) -> None:
        if not self.identity or not self.cases:
            raise CiboCapitalManagementError(
                "Phase20G report identity/cases are required"
            )
        ids = tuple(item.case_id for item in self.cases)
        if len(ids) != len(set(ids)):
            raise CiboCapitalManagementError(
                "Phase20G case ids must be unique"
            )
        if not self.synthetic_contract_evidence_only:
            raise CiboCapitalManagementError(
                "Phase20G V1 must remain synthetic contract evidence"
            )
        if (
            self.empirical_value_claimed
            or self.historical_provider_economics_claimed
            or self.phase19j_burned_validation_reused
            or self.policy_selected
            or self.allocation_authority
            or self.risk_authority
            or self.execution_authority
            or self.live_authorized
            or self.real_capital_authorized
        ):
            raise CiboCapitalManagementError(
                "Phase20G contract governance drift"
            )


def _case(
    case_id: str,
    mechanisms: tuple[str, ...],
    passed: bool,
    detail: str,
) -> Phase20InteractionCase:
    return Phase20InteractionCase(
        case_id=case_id,
        mechanisms=mechanisms,
        passed=passed,
        detail=detail,
    )


def _demo_mission() -> CiboCapitalMissionPolicy:
    return derive_cibo_capital_mission(
        CiboAccountCapitalIdentity(
            provider_key="ctrader-demo",
            account_ref="phase20g-demo",
            environment=MarketRuntimeEnvironment.DEMO,
        )
    )


def _state(
    *,
    drawdown: str = "0.20",
    stale: bool = False,
    adverse: bool = False,
) -> CiboCapitalRegimeState:
    return CiboCapitalRegimeState(
        liquidity=LiquidityState.NORMAL,
        volatility=VolatilityState.NORMAL,
        correlation=CorrelationState.NORMAL,
        provider_condition=ProviderCondition.HEALTHY,
        risk_utilization=Decimal("0.20"),
        margin_utilization=Decimal("0.20"),
        drawdown_utilization=Decimal(drawdown),
        opportunity_count=3,
        position_path_adverse=adverse,
        evidence_stale=stale,
    )


def _execution_curve() -> ExecutionCostCurveInput:
    return ExecutionCostCurveInput(
        evidence_id="phase20g:execution",
        volume_step=Decimal("0.01"),
        maximum_volume=Decimal("0.10"),
        gross_edge_per_volume_usd=Decimal("10"),
        spread_cost_per_volume_usd=Decimal("1"),
        commission_cost_per_volume_usd=Decimal("1"),
        slippage_cost_per_volume_usd=Decimal("0"),
        impact_cost_per_volume_squared_usd=Decimal("100"),
    )


def _opportunity() -> TraderOpportunityEnvelope:
    return TraderOpportunityEnvelope(
        trader_id=TraderLineage.R38_EURUSD,
        signal_fingerprint="phase20g-signal",
        qore_symbol="EURUSD",
        provider_symbol="EURUSD",
        side="long",
        entry_type="MARKET",
        intended_entry=Decimal("1.1000"),
        stop_loss=Decimal("1.0950"),
        take_profit=Decimal("1.1100"),
        stop_loss_per_volume=Decimal("100"),
        margin_per_volume=Decimal("200"),
        volume_step=Decimal("0.01"),
        minimum_volume=Decimal("0.01"),
        maximum_volume=Decimal("0.10"),
    )


def _observation() -> CmaCapitalObservation:
    return CmaCapitalObservation(
        event="CIBO_CMA_CAPITAL_OBSERVATION",
        trader=TraderLineage.R38_EURUSD.value,
        symbol="EURUSD",
        signal_fingerprint="phase20g-signal",
        position_id=101,
        stage=CapitalStage.CAPITALIZE,
        evidence_sufficient=True,
        expansion_eligible=True,
        realized_net_pnl_usd=Decimal("10"),
        remaining_stop_worst_case_pnl_usd=Decimal("0"),
        net_economic_floor_usd=Decimal("10"),
        base_capital_at_risk_usd=Decimal("0"),
        protected_open_floor_usd=Decimal("0"),
        self_financing_capacity_usd=Decimal("10"),
        reason="phase20g synthetic observation",
    )


def _candidate(
    *,
    fingerprint: str,
    trader: TraderLineage,
    net: str,
    minutes: str,
) -> CapitalOpportunityCandidate:
    now = datetime(2026, 9, 27, 4, 0, tzinfo=UTC)
    return CapitalOpportunityCandidate(
        signal_fingerprint=fingerprint,
        trader_id=trader,
        qore_symbol=fingerprint.upper(),
        provider_symbol=fingerprint.upper(),
        decision_as_of=now,
        expectation=CausalOpportunityExpectation(
            evidence_id=f"phase20g:{fingerprint}",
            as_of=now,
            basis=CausalExpectationBasis.FROZEN_HISTORICAL_PRIOR,
            expected_net_value_usd=Decimal(net),
            expected_capital_minutes=Decimal(minutes),
        ),
        stop_risk_usd=Decimal("5"),
        margin_usd=Decimal("10"),
        concentration_group="USD",
        concentration_risk_usd=Decimal("5"),
    )


def run_phase20g_structural_ablation(
    *,
    root: Path,
) -> Phase20InteractionAblationReport:
    """Run synthetic ablations and safe-composition laws for certified mechanisms."""

    if not isinstance(root, Path):
        raise CiboCapitalManagementError("Phase20G root must be pathlib.Path")
    root.mkdir(parents=True, exist_ok=True)
    mission = _demo_mission()

    execution_cap = execution_efficient_volume_cap(_execution_curve())
    g01 = (
        execution_cap.volume_cap == Decimal("0.04")
        and execution_cap.volume_cap < _execution_curve().maximum_volume
        and execution_cap.marginal_next_step_net_usd == Decimal("-0.01")
    )

    stale_regime = select_ce2i_tools_for_regime(
        mission=mission,
        state=_state(stale=True),
    )
    g02 = (
        execution_cap.volume_cap > 0
        and stale_regime.posture is CiboRegimePosture.HALT_NEW_CAPITAL
        and stale_regime.enabled_tools == ("T20",)
    )

    store = DurableCapitalSourceLedgerStore(root / "g03-expansion.json")
    store.store(
        CapitalSourceLedger().add_source(
            source_id="g03-profit",
            source=CapitalSource.REALIZED_PROFIT,
            proven_amount_usd=Decimal("10"),
        ),
        expected_generation=0,
    )
    now = datetime(2026, 9, 27, 4, 0, tzinfo=UTC)
    bounded = reserve_expansion_proposal(
        reservation_id="g03-r1",
        source_id="g03-profit",
        opportunity=_opportunity(),
        observation=_observation(),
        hard_risk_headroom_usd=Decimal("50"),
        margin_headroom_usd=Decimal("1000"),
        assigned_capital_usd=Decimal("10000"),
        requested_at=now,
        expires_at=now + timedelta(seconds=30),
        request_id="g03-risk",
        ledger_store=store,
        maximum_expansion_volume=execution_cap.volume_cap,
    )
    g03 = (
        bounded.plan.volume == Decimal("0.04")
        and bounded.plan.stop_risk_usd == Decimal("4.00")
        and store.load().ledger.accounts[0].reserved_usd == Decimal("4.00")
    )

    defensive_regime = select_ce2i_tools_for_regime(
        mission=mission,
        state=_state(adverse=True),
    )
    options = (
        KnownCapitalOption(
            opportunity_id="g04-small",
            minimum_stop_risk_usd=Decimal("4"),
            minimum_margin_usd=Decimal("20"),
        ),
        KnownCapitalOption(
            opportunity_id="g04-large",
            minimum_stop_risk_usd=Decimal("10"),
            minimum_margin_usd=Decimal("40"),
        ),
    )
    optionality = plan_capital_optionality(
        mission=mission,
        regime=defensive_regime,
        hard_risk_headroom_usd=Decimal("60"),
        margin_headroom_usd=Decimal("500"),
        known_options=options,
    )
    g04 = (
        optionality.reserve_stop_risk_usd == Decimal("4")
        and optionality.reserve_margin_usd == Decimal("20")
        and optionality.deployable_stop_risk_usd == Decimal("56")
        and optionality.reserved_for_opportunity_ids == ("g04-small",)
    )

    derisk = plan_dynamic_derisking(
        CiboDeRiskingInput(
            current_volume=Decimal("1.00"),
            minimum_retained_volume=Decimal("0.10"),
            volume_step=Decimal("0.10"),
            stop_risk_per_volume_usd=Decimal("100"),
            margin_per_volume_usd=Decimal("200"),
            maximum_retained_stop_risk_usd=Decimal("55"),
            maximum_retained_margin_usd=Decimal("500"),
            methodology_position_valid=True,
        )
    )
    g05 = (
        derisk.action is CiboDeRiskAction.REDUCE
        and derisk.retained_volume == Decimal("0.50")
        and derisk.released_stop_risk_usd == Decimal("50.00")
    )

    recovery_regime = select_ce2i_tools_for_regime(
        mission=mission,
        state=_state(drawdown="0.80"),
    )
    recovery_reserve = plan_capital_optionality(
        mission=mission,
        regime=recovery_regime,
        hard_risk_headroom_usd=Decimal("60"),
        margin_headroom_usd=Decimal("500"),
    )
    g06 = (
        recovery_regime.posture is CiboRegimePosture.RECOVERY
        and "T06" not in recovery_regime.enabled_tools
        and "T09" not in recovery_regime.enabled_tools
        and recovery_reserve.deployable_stop_risk_usd == 0
        and recovery_reserve.deployable_margin_usd == 0
        and derisk.released_stop_risk_usd > 0
    )

    fast = _candidate(
        fingerprint="fast",
        trader=TraderLineage.R43_GBPUSD,
        net="8",
        minutes="5",
    )
    slow = _candidate(
        fingerprint="slow",
        trader=TraderLineage.R38_EURUSD,
        net="10",
        minutes="20",
    )
    budget = OpportunityAllocationBudget(
        stop_risk_headroom_usd=Decimal("5"),
        margin_headroom_usd=Decimal("100"),
        concentration_limit_by_group=(("USD", Decimal("100")),),
    )
    left = allocate_competing_opportunities((slow, fast), budget)
    right = allocate_competing_opportunities((fast, slow), budget)
    g07 = (
        left.selected_signal_fingerprints == ("fast",)
        and right.selected_signal_fingerprints == ("fast",)
        and left.rows == right.rows
    )

    cases = (
        _case(
            "G01_T11_EXECUTION_CAP_ABLATION",
            ("T11",),
            g01,
            (
                "Removing execution impact would expose 0.10 volume; T11 "
                "caps the same synthetic opportunity at 0.04."
            ),
        ),
        _case(
            "G02_T12_STALE_REGIME_DOMINATES_POSITIVE_EXECUTION_CAP",
            ("T11", "T12"),
            g02,
            (
                "A positive execution cap cannot bypass stale regime evidence; "
                "only T20 remains enabled."
            ),
        ),
        _case(
            "G03_T06_T11_FUNDING_AND_EXECUTION_ARE_ORTHOGONAL",
            ("T06", "T11", "T19"),
            g03,
            (
                "Execution efficiency can reduce a profit-funded expansion "
                "reservation but cannot create funding."
            ),
        ),
        _case(
            "G04_T15_OPTIONALITY_RESERVES_DISTINCT_FUTURE_CAPACITY",
            ("T12", "T15"),
            g04,
            (
                "Defensive optionality reserves known future capacity while "
                "leaving current Trader geometry untouched."
            ),
        ),
        _case(
            "G05_T14_DERISKING_REDUCES_EXISTING_EXPOSURE",
            ("T14",),
            g05,
            (
                "T14 acts on existing exposure and releases current stop-risk "
                "capacity without authorizing new capital."
            ),
        ),
        _case(
            "G06_RECOVERY_COMPOSES_RESERVE_AND_DERISKING",
            ("T12", "T13", "T14", "T15"),
            g06,
            (
                "Recovery blocks expansion, preserves all new-capital headroom, "
                "and can simultaneously reduce existing exposure."
            ),
        ),
        _case(
            "G07_T09_T18_COMPETITION_IS_INPUT_ORDER_INVARIANT",
            ("T09", "T18"),
            g07,
            (
                "Cross-Trader competition produces the same allocation "
                "regardless of candidate input order."
            ),
        ),
    )
    return Phase20InteractionAblationReport(
        identity="CIBO_PHASE20G_STRUCTURAL_ABLATION_V1",
        cases=cases,
    )
