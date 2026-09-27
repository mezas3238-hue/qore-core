"""Phase 20F independent CE2I accounting-core mechanism certification.

This harness exercises real CE2I implementation surfaces rather than promoting
tools from registry metadata alone. Phase20F-A covers T05/T19/T20 accounting
mechanics. Phase20F-B covers T11/T12/T14/T15 execution/regime/de-risking/
optionality mechanics. Both tranches avoid historical provider economics and
burned Phase-19J validation.

The certification is contract-level only. It grants no allocator, QORE Risk,
execution, DEMO, LIVE, real-capital or merge authority.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import StrEnum
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
from qore.infrastructure.cibo_capital_source_ledger import (
    CapitalReservationRequest,
    CapitalSourceLedger,
    ReservationState,
)
from qore.infrastructure.cibo_capital_source_ledger_store import (
    DurableCapitalLedgerError,
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
from qore.infrastructure.cibo_ce2i_recycling import (
    RecyclePurpose,
    ReleasedCapacityEvidence,
    deploy_recycled_capacity,
    register_released_capacity,
    reserve_recycled_capacity,
    settle_recycled_capacity,
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
from qore.infrastructure.cibo_ce2i_tool_registry import ToolMaturity, tool_by_code
from qore.infrastructure.cibo_cma_capital_observation import CmaCapitalObservation
from qore.infrastructure.cibo_cma_initial_seed import build_initial_seed_request
from qore.infrastructure.market_test_environment import MarketRuntimeEnvironment


class Phase20MechanismCertificationStatus(StrEnum):
    CONTRACT_CERTIFIED = "CONTRACT_CERTIFIED"
    CONTRACT_FAILED = "CONTRACT_FAILED"


@dataclass(frozen=True, slots=True)
class Phase20MechanismProof:
    tool_code: str
    invariant_id: str
    passed: bool
    detail: str

    def __post_init__(self) -> None:
        if not self.tool_code or not self.invariant_id or not self.detail:
            raise CiboCapitalManagementError(
                "Phase20F proof identity/detail is required"
            )
        if type(self.passed) is not bool:
            raise CiboCapitalManagementError("Phase20F proof passed must be bool")


@dataclass(frozen=True, slots=True)
class Phase20MechanismCertification:
    tool_code: str
    tool_name: str
    status: Phase20MechanismCertificationStatus
    proof_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.tool_code or not self.tool_name or not self.proof_ids:
            raise CiboCapitalManagementError(
                "Phase20F certification identity/proofs are required"
            )
        if type(self.status) is not Phase20MechanismCertificationStatus:
            raise CiboCapitalManagementError(
                "Phase20F certification status must use canonical enum"
            )


@dataclass(frozen=True, slots=True)
class Phase20MechanismCertificationReport:
    identity: str
    certifications: tuple[Phase20MechanismCertification, ...]
    proofs: tuple[Phase20MechanismProof, ...]
    synthetic_contract_evidence_only: bool = True
    historical_provider_economics_claimed: bool = False
    phase19j_burned_validation_reused: bool = False
    policy_certified: bool = False
    allocation_authority: bool = False
    risk_authority: bool = False
    execution_authority: bool = False
    demo_execution_authorized: bool = False
    live_authorized: bool = False
    real_capital_authorized: bool = False
    merge_authorized: bool = False

    def __post_init__(self) -> None:
        if not self.identity or not self.certifications or not self.proofs:
            raise CiboCapitalManagementError(
                "Phase20F report identity/certifications/proofs are required"
            )
        codes = tuple(item.tool_code for item in self.certifications)
        if len(codes) != len(set(codes)):
            raise CiboCapitalManagementError(
                "Phase20F report contains duplicate tool certification"
            )
        proof_ids = tuple(item.invariant_id for item in self.proofs)
        if len(proof_ids) != len(set(proof_ids)):
            raise CiboCapitalManagementError(
                "Phase20F report contains duplicate proof id"
            )
        if not self.synthetic_contract_evidence_only:
            raise CiboCapitalManagementError(
                "Phase20F tranche must remain synthetic contract evidence"
            )
        if (
            self.historical_provider_economics_claimed
            or self.phase19j_burned_validation_reused
            or self.policy_certified
            or self.allocation_authority
            or self.risk_authority
            or self.execution_authority
            or self.demo_execution_authorized
            or self.live_authorized
            or self.real_capital_authorized
            or self.merge_authorized
        ):
            raise CiboCapitalManagementError(
                "Phase20F accounting-core governance drift"
            )


def _proof(
    tool_code: str,
    invariant_id: str,
    passed: bool,
    detail: str,
) -> Phase20MechanismProof:
    return Phase20MechanismProof(
        tool_code=tool_code,
        invariant_id=invariant_id,
        passed=passed,
        detail=detail,
    )


def _certification_for(
    tool_code: str,
    proofs: tuple[Phase20MechanismProof, ...],
) -> Phase20MechanismCertification:
    tool = tool_by_code(tool_code)
    if tool.maturity is not ToolMaturity.CONTRACT_IMPLEMENTED:
        raise CiboCapitalManagementError(
            f"{tool_code} is not contract-implemented"
        )
    selected = tuple(item for item in proofs if item.tool_code == tool_code)
    if not selected:
        raise CiboCapitalManagementError(
            f"{tool_code} has no independent Phase20F proofs"
        )
    status = (
        Phase20MechanismCertificationStatus.CONTRACT_CERTIFIED
        if all(item.passed for item in selected)
        else Phase20MechanismCertificationStatus.CONTRACT_FAILED
    )
    return Phase20MechanismCertification(
        tool_code=tool.code,
        tool_name=tool.name,
        status=status,
        proof_ids=tuple(item.invariant_id for item in selected),
    )


def _expect_capital_error(operation: Callable[[], object]) -> bool:
    try:
        operation()
    except CiboCapitalManagementError:
        return True
    return False


def _t19_reservation_proofs(root: Path) -> tuple[Phase20MechanismProof, ...]:
    base = CapitalSourceLedger().add_source(
        source_id="t19-profit",
        source=CapitalSource.REALIZED_PROFIT,
        proven_amount_usd=Decimal("20"),
    )
    reserved = base.reserve(
        reservation_id="t19-r1",
        source_id="t19-profit",
        amount_usd=Decimal("15"),
    )
    no_double_spend = _expect_capital_error(
        lambda: reserved.reserve(
            reservation_id="t19-r2",
            source_id="t19-profit",
            amount_usd=Decimal("10"),
        )
    )

    atomic_base = (
        CapitalSourceLedger()
        .add_source(
            source_id="t19-a",
            source=CapitalSource.REALIZED_PROFIT,
            proven_amount_usd=Decimal("5"),
        )
        .add_source(
            source_id="t19-b",
            source=CapitalSource.PROTECTED_ECONOMIC_FLOOR,
            proven_amount_usd=Decimal("2"),
        )
    )
    atomic_rejected = _expect_capital_error(
        lambda: atomic_base.reserve_many(
            (
                CapitalReservationRequest(
                    reservation_id="t19-a-r",
                    source_id="t19-a",
                    amount_usd=Decimal("5"),
                ),
                CapitalReservationRequest(
                    reservation_id="t19-b-r",
                    source_id="t19-b",
                    amount_usd=Decimal("3"),
                ),
            )
        )
    )
    atomic_unchanged = (
        atomic_base.reservations == ()
        and all(item.reserved_usd == 0 for item in atomic_base.accounts)
    )

    store = DurableCapitalSourceLedgerStore(root / "t19-cas-ledger.json")
    store.store(base, expected_generation=0)
    stale_generation_rejected = False
    try:
        store.store(base, expected_generation=0)
    except DurableCapitalLedgerError:
        stale_generation_rejected = True

    return (
        _proof(
            "T19",
            "T19_NO_DOUBLE_SPEND",
            no_double_spend,
            "A second reservation cannot consume already-reserved capacity.",
        ),
        _proof(
            "T19",
            "T19_MULTI_SOURCE_ATOMICITY",
            atomic_rejected and atomic_unchanged,
            "A failing multi-source reservation leaves every source unchanged.",
        ),
        _proof(
            "T19",
            "T19_DURABLE_CAS_STALE_WRITER_REJECTED",
            stale_generation_rejected,
            "A stale durable-ledger generation cannot overwrite newer state.",
        ),
    )


def _t20_release_proofs() -> tuple[Phase20MechanismProof, ...]:
    base = CapitalSourceLedger().add_source(
        source_id="t20-profit",
        source=CapitalSource.REALIZED_PROFIT,
        proven_amount_usd=Decimal("20"),
    )
    reserved = base.reserve(
        reservation_id="t20-r1",
        source_id="t20-profit",
        amount_usd=Decimal("8"),
    )
    released = reserved.release_unused("t20-r1")
    account = released.accounts[0]
    reserved_only_release = (
        account.available_usd == Decimal("20")
        and account.reserved_usd == 0
        and account.cumulative_released_usd == Decimal("8")
        and released.reservations[0].state is ReservationState.RELEASED
    )

    deployed = reserved.deploy("t20-r1")
    deployed_release_rejected = _expect_capital_error(
        lambda: deployed.release_unused("t20-r1")
    )
    settled = deployed.settle_deployment(
        "t20-r1",
        returned_capacity_usd=Decimal("3"),
    )
    settled_account = settled.accounts[0]
    settlement_separated = (
        settled_account.available_usd == Decimal("15")
        and settled_account.deployed_usd == 0
        and settled_account.consumed_usd == Decimal("5")
        and settled_account.cumulative_released_usd == Decimal("3")
        and settled.reservations[0].state is ReservationState.SETTLED
    )

    return (
        _proof(
            "T20",
            "T20_RESERVED_ONLY_UNUSED_RELEASE",
            reserved_only_release,
            "Unused reserved capacity returns in full and release is recorded as flow.",
        ),
        _proof(
            "T20",
            "T20_DEPLOYED_RELEASE_PATH_REJECTED",
            deployed_release_rejected,
            "Economically deployed capacity cannot impersonate an unused reservation.",
        ),
        _proof(
            "T20",
            "T20_RETURNED_VS_CONSUMED_ACCOUNTING",
            settlement_separated,
            "Settlement separates returned capacity from economically consumed capacity.",
        ),
    )


def _t05_recycling_proofs(root: Path) -> tuple[Phase20MechanismProof, ...]:
    now = datetime(2026, 9, 27, 2, 0, tzinfo=UTC)

    unreconciled_store = DurableCapitalSourceLedgerStore(
        root / "t05-unreconciled.json"
    )
    unreconciled = ReleasedCapacityEvidence(
        evidence_id="t05-unreconciled",
        source=CapitalSource.RELEASED_RISK_CAPACITY,
        amount_usd=Decimal("20"),
        reconciled_at=now,
        upstream_reference="synthetic:settlement",
        reconciled=False,
    )
    unreconciled_rejected = _expect_capital_error(
        lambda: register_released_capacity(
            unreconciled,
            ledger_store=unreconciled_store,
        )
    )

    margin_store = DurableCapitalSourceLedgerStore(root / "t05-margin.json")
    margin = register_released_capacity(
        ReleasedCapacityEvidence(
            evidence_id="t05-margin",
            source=CapitalSource.RELEASED_MARGIN_CAPACITY,
            amount_usd=Decimal("20"),
            reconciled_at=now,
            upstream_reference="synthetic:margin-release",
        ),
        ledger_store=margin_store,
    )
    margin_to_risk_rejected = _expect_capital_error(
        lambda: reserve_recycled_capacity(
            reservation_id="t05-margin-as-risk",
            source_id=margin.source_id,
            purpose=RecyclePurpose.STOP_RISK,
            amount_usd=Decimal("5"),
            ledger_store=margin_store,
        )
    )

    risk_store_path = root / "t05-risk.json"
    risk_store = DurableCapitalSourceLedgerStore(risk_store_path)
    risk = register_released_capacity(
        ReleasedCapacityEvidence(
            evidence_id="t05-risk",
            source=CapitalSource.RELEASED_RISK_CAPACITY,
            amount_usd=Decimal("20"),
            reconciled_at=now,
            upstream_reference="synthetic:risk-release",
        ),
        ledger_store=risk_store,
    )
    risk_to_margin_rejected = _expect_capital_error(
        lambda: reserve_recycled_capacity(
            reservation_id="t05-risk-as-margin",
            source_id=risk.source_id,
            purpose=RecyclePurpose.MARGIN,
            amount_usd=Decimal("5"),
            ledger_store=risk_store,
        )
    )
    reservation = reserve_recycled_capacity(
        reservation_id="t05-risk-r1",
        source_id=risk.source_id,
        purpose=RecyclePurpose.STOP_RISK,
        amount_usd=Decimal("8"),
        ledger_store=risk_store,
    )
    deploy_recycled_capacity(reservation, ledger_store=risk_store)
    settle_recycled_capacity(
        reservation,
        returned_capacity_usd=Decimal("3"),
        ledger_store=risk_store,
    )
    restarted = DurableCapitalSourceLedgerStore(risk_store_path).load()
    restarted_account = restarted.ledger.accounts[0]
    settlement_persisted = (
        restarted_account.available_usd == Decimal("15")
        and restarted_account.consumed_usd == Decimal("5")
        and restarted_account.cumulative_released_usd == Decimal("3")
    )

    return (
        _proof(
            "T05",
            "T05_RECONCILIATION_REQUIRED",
            unreconciled_rejected,
            "Unreconciled released capacity cannot enter the reusable ledger.",
        ),
        _proof(
            "T05",
            "T05_DIMENSIONAL_NON_FUNGIBILITY",
            margin_to_risk_rejected and risk_to_margin_rejected,
            "Released margin and released stop-risk capacity cannot impersonate each other.",
        ),
        _proof(
            "T05",
            "T05_SETTLEMENT_PERSISTS_AFTER_RESTART",
            settlement_persisted,
            "Returned and consumed recycled risk survive durable-store restart.",
        ),
    )



def _demo_mission() -> CiboCapitalMissionPolicy:
    return derive_cibo_capital_mission(
        CiboAccountCapitalIdentity(
            provider_key="ctrader-demo",
            account_ref="phase20f-demo",
            environment=MarketRuntimeEnvironment.DEMO,
        )
    )


def _regime_state(
    *,
    drawdown: str = "0.20",
    adverse: bool = False,
    stale: bool = False,
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


def _t11_execution_efficiency_proofs() -> tuple[Phase20MechanismProof, ...]:
    blocked = execution_efficient_volume_cap(
        ExecutionCostCurveInput(
            evidence_id="phase20f:t11:block",
            volume_step=Decimal("1"),
            maximum_volume=Decimal("10"),
            gross_edge_per_volume_usd=Decimal("2"),
            spread_cost_per_volume_usd=Decimal("2"),
            commission_cost_per_volume_usd=Decimal("1"),
            slippage_cost_per_volume_usd=Decimal("0"),
            impact_cost_per_volume_squared_usd=Decimal("0"),
        )
    )
    nonlinear = execution_efficient_volume_cap(
        ExecutionCostCurveInput(
            evidence_id="phase20f:t11:impact",
            volume_step=Decimal("1"),
            maximum_volume=Decimal("10"),
            gross_edge_per_volume_usd=Decimal("10"),
            spread_cost_per_volume_usd=Decimal("1"),
            commission_cost_per_volume_usd=Decimal("1"),
            slippage_cost_per_volume_usd=Decimal("0"),
            impact_cost_per_volume_squared_usd=Decimal("1"),
        )
    )
    return (
        _proof(
            "T11",
            "T11_NON_POSITIVE_LINEAR_EDGE_BLOCKS_EXPANSION",
            blocked.volume_cap == 0
            and blocked.net_expectancy_usd == 0
            and blocked.marginal_next_step_net_usd is not None
            and blocked.marginal_next_step_net_usd < 0,
            "Execution cost that consumes gross edge yields zero expansion capacity.",
        ),
        _proof(
            "T11",
            "T11_NEGATIVE_MARGINAL_STEP_CAPS_VOLUME",
            nonlinear.volume_cap == Decimal("4")
            and nonlinear.net_expectancy_usd == Decimal("16")
            and nonlinear.marginal_next_step_net_usd == Decimal("-1"),
            "Nonlinear impact stops sizing before the next negative marginal step.",
        ),
    )


def _t12_regime_selector_proofs() -> tuple[Phase20MechanismProof, ...]:
    mission = _demo_mission()
    stale = select_ce2i_tools_for_regime(
        mission=mission,
        state=_regime_state(stale=True),
    )
    recovery = select_ce2i_tools_for_regime(
        mission=mission,
        state=_regime_state(drawdown="0.80"),
    )
    recovery_blocks = all(
        code not in recovery.enabled_tools
        for code in ("T06", "T07", "T09", "T18")
    )
    return (
        _proof(
            "T12",
            "T12_STALE_EVIDENCE_FAILS_CLOSED_TO_RELEASE",
            stale.posture is CiboRegimePosture.HALT_NEW_CAPITAL
            and stale.enabled_tools == ("T20",),
            "Stale regime evidence cannot authorize new capital deployment.",
        ),
        _proof(
            "T12",
            "T12_RECOVERY_POSTURE_BLOCKS_EXPANSION",
            recovery.posture is CiboRegimePosture.RECOVERY
            and recovery_blocks
            and "T11" in recovery.enabled_tools
            and "T20" in recovery.enabled_tools,
            "Recovery posture retains defensive/release tools while blocking expansion.",
        ),
    )


def _t14_dynamic_derisking_proofs() -> tuple[Phase20MechanismProof, ...]:
    reduced = plan_dynamic_derisking(
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
    invalidated = plan_dynamic_derisking(
        CiboDeRiskingInput(
            current_volume=Decimal("1.00"),
            minimum_retained_volume=Decimal("0.10"),
            volume_step=Decimal("0.10"),
            stop_risk_per_volume_usd=Decimal("100"),
            margin_per_volume_usd=Decimal("200"),
            maximum_retained_stop_risk_usd=Decimal("100"),
            maximum_retained_margin_usd=Decimal("200"),
            methodology_position_valid=False,
        )
    )
    return (
        _proof(
            "T14",
            "T14_MINIMUM_STEP_ALIGNED_REDUCTION",
            reduced.action is CiboDeRiskAction.REDUCE
            and reduced.retained_volume == Decimal("0.50")
            and reduced.reduction_volume == Decimal("0.50")
            and reduced.retained_stop_risk_usd == Decimal("50.00")
            and reduced.released_stop_risk_usd == Decimal("50.00"),
            "De-risking uses the least step-aligned reduction that restores ceilings.",
        ),
        _proof(
            "T14",
            "T14_TRADER_INVALIDATION_RELEASES_ALL",
            invalidated.action is CiboDeRiskAction.RELEASE_ALL
            and invalidated.retained_volume == 0
            and invalidated.released_stop_risk_usd == Decimal("100.00"),
            "Trader methodology invalidation cannot be overridden by CIBO capital logic.",
        ),
    )


def _t15_optionality_proofs() -> tuple[Phase20MechanismProof, ...]:
    mission = _demo_mission()
    options = (
        KnownCapitalOption(
            opportunity_id="phase20f-small",
            minimum_stop_risk_usd=Decimal("4"),
            minimum_margin_usd=Decimal("20"),
        ),
        KnownCapitalOption(
            opportunity_id="phase20f-large",
            minimum_stop_risk_usd=Decimal("10"),
            minimum_margin_usd=Decimal("40"),
        ),
    )
    defensive_regime = select_ce2i_tools_for_regime(
        mission=mission,
        state=_regime_state(adverse=True),
    )
    defensive = plan_capital_optionality(
        mission=mission,
        regime=defensive_regime,
        hard_risk_headroom_usd=Decimal("60"),
        margin_headroom_usd=Decimal("500"),
        known_options=options,
    )
    recovery_regime = select_ce2i_tools_for_regime(
        mission=mission,
        state=_regime_state(drawdown="0.80"),
    )
    recovery = plan_capital_optionality(
        mission=mission,
        regime=recovery_regime,
        hard_risk_headroom_usd=Decimal("60"),
        margin_headroom_usd=Decimal("500"),
        known_options=options,
    )
    return (
        _proof(
            "T15",
            "T15_DEFENSIVE_PRESERVES_CHEAPEST_KNOWN_OPTION",
            defensive.reserve_stop_risk_usd == Decimal("4")
            and defensive.reserve_margin_usd == Decimal("20")
            and defensive.reserved_for_opportunity_ids == ("phase20f-small",),
            "Defensive capability-discovery preserves the cheapest known executable option.",
        ),
        _proof(
            "T15",
            "T15_RECOVERY_PRESERVES_ALL_REMAINING_CAPACITY",
            recovery.reserve_stop_risk_usd == Decimal("60")
            and recovery.reserve_margin_usd == Decimal("500")
            and recovery.deployable_stop_risk_usd == 0
            and recovery.deployable_margin_usd == 0,
            "Recovery posture preserves all remaining new-capital capacity.",
        ),
    )


def run_phase20f_operational_mechanism_certification(
) -> Phase20MechanismCertificationReport:
    """Execute independent contract proofs for T11, T12, T14 and T15."""

    proofs = (
        *_t11_execution_efficiency_proofs(),
        *_t12_regime_selector_proofs(),
        *_t14_dynamic_derisking_proofs(),
        *_t15_optionality_proofs(),
    )
    certifications = tuple(
        _certification_for(code, proofs)
        for code in ("T11", "T12", "T14", "T15")
    )
    return Phase20MechanismCertificationReport(
        identity="CIBO_PHASE20F_OPERATIONAL_MECHANISM_CERTIFICATION_V1",
        certifications=certifications,
        proofs=proofs,
    )



def _phase20f_opportunity() -> TraderOpportunityEnvelope:
    return TraderOpportunityEnvelope(
        trader_id=TraderLineage.R38_EURUSD,
        signal_fingerprint="phase20f-signal",
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
        maximum_volume=Decimal("10"),
    )


def _t01_minimal_seed_proofs() -> tuple[Phase20MechanismProof, ...]:
    now = datetime(2026, 9, 27, 3, 0, tzinfo=UTC)
    seed = build_initial_seed_request(
        request_id="phase20f-seed",
        opportunity=_phase20f_opportunity(),
        assigned_capital_usd=Decimal("2000"),
        hard_risk_headroom_usd=Decimal("60"),
        margin_headroom_usd=Decimal("1000"),
        requested_at=now,
        expires_at=now + timedelta(seconds=30),
    )
    insufficient_margin_rejected = _expect_capital_error(
        lambda: build_initial_seed_request(
            request_id="phase20f-seed-blocked",
            opportunity=_phase20f_opportunity(),
            assigned_capital_usd=Decimal("2000"),
            hard_risk_headroom_usd=Decimal("60"),
            margin_headroom_usd=Decimal("0.50"),
            requested_at=now,
            expires_at=now + timedelta(seconds=30),
        )
    )
    return (
        _proof(
            "T01",
            "T01_USES_PROVIDER_MINIMUM_EXECUTABLE_SEED",
            seed.plan.volume == Decimal("0.01")
            and seed.plan.stop_risk_usd == Decimal("1.00")
            and seed.request.requested_volume == Decimal("0.01")
            and seed.request.strategy_requested_risk_usd is None,
            "Minimal seed uses executable provider granularity, not legacy Trader sizing.",
        ),
        _proof(
            "T01",
            "T01_FAILS_CLOSED_BELOW_MINIMUM_MARGIN",
            insufficient_margin_rejected,
            "CIBO cannot fabricate a minimal seed when observed margin headroom is insufficient.",
        ),
    )


def _expansion_observation(
    *,
    realized: str,
    protected: str,
    capacity: str,
) -> CmaCapitalObservation:
    return CmaCapitalObservation(
        event="CIBO_CMA_CAPITAL_OBSERVATION",
        trader=TraderLineage.R38_EURUSD.value,
        symbol="EURUSD",
        signal_fingerprint="phase20f-signal",
        position_id=101,
        stage=CapitalStage.CAPITALIZE,
        evidence_sufficient=True,
        expansion_eligible=True,
        realized_net_pnl_usd=Decimal(realized),
        remaining_stop_worst_case_pnl_usd=Decimal("0"),
        net_economic_floor_usd=Decimal(capacity),
        base_capital_at_risk_usd=Decimal("0"),
        protected_open_floor_usd=Decimal(protected),
        self_financing_capacity_usd=Decimal(capacity),
        reason="phase20f synthetic expansion evidence",
    )


def _expansion_store(
    *,
    path: Path,
    source: CapitalSource,
    amount: Decimal,
) -> DurableCapitalSourceLedgerStore:
    store = DurableCapitalSourceLedgerStore(path)
    ledger = CapitalSourceLedger().add_source(
        source_id="phase20f-expansion-source",
        source=source,
        proven_amount_usd=amount,
    )
    store.store(ledger, expected_generation=0)
    return store


def _t06_t07_expansion_proofs(root: Path) -> tuple[Phase20MechanismProof, ...]:
    now = datetime(2026, 9, 27, 3, 0, tzinfo=UTC)

    profit_store = _expansion_store(
        path=root / "t06-profit.json",
        source=CapitalSource.REALIZED_PROFIT,
        amount=Decimal("20"),
    )
    profit = reserve_expansion_proposal(
        reservation_id="t06-r1",
        source_id="phase20f-expansion-source",
        opportunity=_phase20f_opportunity(),
        observation=_expansion_observation(
            realized="10",
            protected="0",
            capacity="10",
        ),
        hard_risk_headroom_usd=Decimal("50"),
        margin_headroom_usd=Decimal("1000"),
        assigned_capital_usd=Decimal("10000"),
        requested_at=now,
        expires_at=now + timedelta(seconds=30),
        request_id="t06-risk",
        ledger_store=profit_store,
    )

    floor_store = _expansion_store(
        path=root / "t07-floor.json",
        source=CapitalSource.PROTECTED_ECONOMIC_FLOOR,
        amount=Decimal("20"),
    )
    protected = reserve_expansion_proposal(
        reservation_id="t07-r1",
        source_id="phase20f-expansion-source",
        opportunity=_phase20f_opportunity(),
        observation=_expansion_observation(
            realized="0",
            protected="8",
            capacity="8",
        ),
        hard_risk_headroom_usd=Decimal("50"),
        margin_headroom_usd=Decimal("1000"),
        assigned_capital_usd=Decimal("10000"),
        requested_at=now,
        expires_at=now + timedelta(seconds=30),
        request_id="t07-risk",
        ledger_store=floor_store,
    )

    base_store = _expansion_store(
        path=root / "t06-base-forbidden.json",
        source=CapitalSource.ORIGINAL_BASE_CAPITAL,
        amount=Decimal("20"),
    )
    base_rejected = _expect_capital_error(
        lambda: reserve_expansion_proposal(
            reservation_id="t06-base",
            source_id="phase20f-expansion-source",
            opportunity=_phase20f_opportunity(),
            observation=_expansion_observation(
                realized="10",
                protected="0",
                capacity="10",
            ),
            hard_risk_headroom_usd=Decimal("50"),
            margin_headroom_usd=Decimal("1000"),
            assigned_capital_usd=Decimal("10000"),
            requested_at=now,
            expires_at=now + timedelta(seconds=30),
            request_id="t06-base-risk",
            ledger_store=base_store,
        )
    )

    return (
        _proof(
            "T06",
            "T06_REALIZED_PROFIT_BOUNDS_EXPANSION",
            profit.source is CapitalSource.REALIZED_PROFIT
            and profit.plan.stop_risk_usd == Decimal("10")
            and profit_store.load().ledger.accounts[0].reserved_usd
            == Decimal("10"),
            "Profit-funded expansion cannot reserve more than reconciled realized-profit capacity.",
        ),
        _proof(
            "T06",
            "T06_ORIGINAL_BASE_CAPITAL_NOT_EXPANSION_SOURCE",
            base_rejected,
            "Original base capital cannot masquerade as self-financing expansion capacity.",
        ),
        _proof(
            "T07",
            "T07_PROTECTED_FLOOR_BOUNDS_EXPANSION",
            protected.source is CapitalSource.PROTECTED_ECONOMIC_FLOOR
            and protected.plan.stop_risk_usd == Decimal("8")
            and floor_store.load().ledger.accounts[0].reserved_usd
            == Decimal("8"),
            "Protected-floor expansion is capped by reconciled protected capacity.",
        ),
    )


def _competition_candidate(
    *,
    fingerprint: str,
    trader: TraderLineage,
    net: str,
    minutes: str,
    group: str = "USD",
) -> CapitalOpportunityCandidate:
    now = datetime(2026, 9, 27, 3, 0, tzinfo=UTC)
    return CapitalOpportunityCandidate(
        signal_fingerprint=fingerprint,
        trader_id=trader,
        qore_symbol=fingerprint.upper(),
        provider_symbol=fingerprint.upper(),
        decision_as_of=now,
        expectation=CausalOpportunityExpectation(
            evidence_id=f"phase20f:{fingerprint}",
            as_of=now,
            basis=CausalExpectationBasis.FROZEN_HISTORICAL_PRIOR,
            expected_net_value_usd=Decimal(net),
            expected_capital_minutes=Decimal(minutes),
        ),
        stop_risk_usd=Decimal("5"),
        margin_usd=Decimal("10"),
        concentration_group=group,
        concentration_risk_usd=Decimal("5"),
    )


def _t09_t18_competition_proofs() -> tuple[Phase20MechanismProof, ...]:
    fast = _competition_candidate(
        fingerprint="fast",
        trader=TraderLineage.R43_GBPUSD,
        net="8",
        minutes="5",
    )
    slow = _competition_candidate(
        fingerprint="slow",
        trader=TraderLineage.R38_EURUSD,
        net="10",
        minutes="20",
    )
    scarce = allocate_competing_opportunities(
        (slow, fast),
        OpportunityAllocationBudget(
            stop_risk_headroom_usd=Decimal("5"),
            margin_headroom_usd=Decimal("100"),
            concentration_limit_by_group=(("USD", Decimal("100")),),
        ),
    )

    left = _competition_candidate(
        fingerprint="a",
        trader=TraderLineage.R38_EURUSD,
        net="10",
        minutes="10",
    )
    right = _competition_candidate(
        fingerprint="b",
        trader=TraderLineage.VT31_NAS100,
        net="10",
        minutes="10",
    )
    identity_neutral = allocate_competing_opportunities(
        (right, left),
        OpportunityAllocationBudget(
            stop_risk_headroom_usd=Decimal("5"),
            margin_headroom_usd=Decimal("100"),
            concentration_limit_by_group=(("USD", Decimal("100")),),
        ),
    )

    return (
        _proof(
            "T09",
            "T09_SCARCE_CAPITAL_COMPETES_BY_CAUSAL_EFFICIENCY",
            scarce.selected_signal_fingerprints == ("fast",)
            and scarce.rows[1].reason == "shared stop-risk headroom exhausted",
            (
                "Scarce stop-risk capacity selects the stronger causal "
                "value-per-risk-minute candidate."
            ),
        ),
        _proof(
            "T18",
            "T18_TRADER_IDENTITY_DOES_NOT_CREATE_PRIORITY",
            left.net_value_per_risk_minute == right.net_value_per_risk_minute
            and identity_neutral.selected_signal_fingerprints == ("a",),
            "Cross-Trader allocation is economics-driven; Trader identity alone adds no score.",
        ),
    )


def _t13_drawdown_reserve_proofs() -> tuple[Phase20MechanismProof, ...]:
    mission = _demo_mission()
    recovery_regime = select_ce2i_tools_for_regime(
        mission=mission,
        state=_regime_state(drawdown="0.80"),
    )
    reserve = plan_capital_optionality(
        mission=mission,
        regime=recovery_regime,
        hard_risk_headroom_usd=Decimal("60"),
        margin_headroom_usd=Decimal("500"),
        known_options=(),
    )
    return (
        _proof(
            "T13",
            "T13_DRAWDOWN_RECOVERY_RESERVES_ALL_CAPACITY",
            recovery_regime.posture is CiboRegimePosture.RECOVERY
            and reserve.reserve_stop_risk_usd == Decimal("60")
            and reserve.reserve_margin_usd == Decimal("500")
            and reserve.deployable_stop_risk_usd == 0
            and reserve.deployable_margin_usd == 0,
            "Drawdown recovery posture can reserve all remaining new-capital capacity.",
        ),
    )


def run_phase20f_capital_action_certification(
    *,
    root: Path,
) -> Phase20MechanismCertificationReport:
    """Execute independent contract proofs for T01/T06/T07/T09/T13/T18."""

    if not isinstance(root, Path):
        raise CiboCapitalManagementError("Phase20F-C root must be pathlib.Path")
    root.mkdir(parents=True, exist_ok=True)
    proofs = (
        *_t01_minimal_seed_proofs(),
        *_t06_t07_expansion_proofs(root),
        *_t09_t18_competition_proofs(),
        *_t13_drawdown_reserve_proofs(),
    )
    certifications = tuple(
        _certification_for(code, proofs)
        for code in ("T01", "T06", "T07", "T09", "T13", "T18")
    )
    return Phase20MechanismCertificationReport(
        identity="CIBO_PHASE20F_CAPITAL_ACTION_CERTIFICATION_V1",
        certifications=certifications,
        proofs=proofs,
    )


def run_phase20f_accounting_core_certification(
    *,
    root: Path,
) -> Phase20MechanismCertificationReport:
    """Execute independent contract proofs for T05, T19 and T20."""

    if not isinstance(root, Path):
        raise CiboCapitalManagementError("Phase20F root must be pathlib.Path")
    root.mkdir(parents=True, exist_ok=True)

    proofs = (
        *_t05_recycling_proofs(root),
        *_t19_reservation_proofs(root),
        *_t20_release_proofs(),
    )
    certifications = tuple(
        _certification_for(code, proofs) for code in ("T05", "T19", "T20")
    )
    return Phase20MechanismCertificationReport(
        identity="CIBO_PHASE20F_ACCOUNTING_CORE_CERTIFICATION_V1",
        certifications=certifications,
        proofs=proofs,
    )
