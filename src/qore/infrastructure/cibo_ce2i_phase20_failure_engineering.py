"""Phase 20J-A adversarial failure engineering for CIBO capital state.

This harness composes already-implemented provider, capital-ledger, portfolio
reservation and settlement primitives under explicit faults. It is intended to
prove fail-closed behavior and restart-safe state preservation, not to estimate
market probabilities or qualify an allocator.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from pathlib import Path

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    CapitalSource,
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_capital_source_ledger import (
    CapitalReservationRequest,
    CapitalSourceLedger,
)
from qore.infrastructure.cibo_capital_source_ledger_store import (
    DurableCapitalLedgerError,
    DurableCapitalSourceLedgerStore,
)
from qore.infrastructure.cibo_ce2i_causal_expectation import (
    CausalExpectationBasis,
    CausalOpportunityExpectation,
)
from qore.infrastructure.cibo_ce2i_chronological_replay import (
    CiboReplayCausalTrade,
    ReplayEconomicsStatus,
    ReplaySignalFingerprintOrigin,
)
from qore.infrastructure.cibo_ce2i_opportunity_competition import (
    CapitalOpportunityCandidate,
    OpportunityAllocationBudget,
    allocate_competing_opportunities,
)
from qore.infrastructure.cibo_ce2i_phase20_provider_stress import (
    Phase20ProviderStressStatus,
    phase20c_synthetic_predeclared_stress_scenarios,
    run_phase20c_counterfactual_stress_matrix,
)
from qore.infrastructure.cibo_ce2i_portfolio_allocation_ledger import (
    PortfolioAllocationLedger,
)
from qore.infrastructure.cibo_ce2i_portfolio_allocation_store import (
    DurablePortfolioAllocationError,
    DurablePortfolioAllocationStore,
)
from qore.infrastructure.cibo_cma_settlement_ledger import (
    CmaSettlementLedgerError,
    CmaSettlementRecord,
)
from qore.infrastructure.cibo_cma_settlement_store import (
    DurableCmaSettlementStore,
)
from qore.infrastructure.cibo_provider_economic_normalization import (
    ProviderEconomicObservation,
)


class Phase20FailureDisposition(StrEnum):
    FAIL_CLOSED = "FAIL_CLOSED"
    STATE_PRESERVED = "STATE_PRESERVED"
    IDEMPOTENT = "IDEMPOTENT"


@dataclass(frozen=True, slots=True)
class Phase20FailureProbe:
    probe_id: str
    disposition: Phase20FailureDisposition
    passed: bool
    detail: str

    def __post_init__(self) -> None:
        if not self.probe_id or not self.detail:
            raise CiboCapitalManagementError(
                "Phase20J failure probe identity/detail is required"
            )
        if type(self.disposition) is not Phase20FailureDisposition:
            raise CiboCapitalManagementError(
                "Phase20J failure probe disposition is invalid"
            )
        if type(self.passed) is not bool:
            raise CiboCapitalManagementError(
                "Phase20J failure probe passed must be bool"
            )


@dataclass(frozen=True, slots=True)
class Phase20FailureEngineeringReport:
    identity: str
    probes: tuple[Phase20FailureProbe, ...]
    synthetic_contract_evidence_only: bool = True
    market_probability_claimed: bool = False
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
        if not self.identity or not self.probes:
            raise CiboCapitalManagementError(
                "Phase20J report identity/probes are required"
            )
        probe_ids = tuple(item.probe_id for item in self.probes)
        if len(probe_ids) != len(set(probe_ids)):
            raise CiboCapitalManagementError(
                "Phase20J report contains duplicate probe id"
            )
        if not self.synthetic_contract_evidence_only:
            raise CiboCapitalManagementError(
                "Phase20J-A must remain synthetic contract evidence"
            )
        if (
            self.market_probability_claimed
            or self.historical_provider_economics_claimed
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
                "Phase20J failure-engineering governance drift"
            )


def _probe(
    probe_id: str,
    disposition: Phase20FailureDisposition,
    passed: bool,
    detail: str,
) -> Phase20FailureProbe:
    return Phase20FailureProbe(
        probe_id=probe_id,
        disposition=disposition,
        passed=passed,
        detail=detail,
    )


def _raises(
    operation: Callable[[], object],
    expected: type[BaseException] | tuple[type[BaseException], ...],
) -> bool:
    try:
        operation()
    except expected:
        return True
    return False


def _provider_causal() -> CiboReplayCausalTrade:
    return CiboReplayCausalTrade(
        trader_id=TraderLineage.R38_EURUSD,
        signal_fingerprint="phase20j-provider",
        signal_fingerprint_origin=(
            ReplaySignalFingerprintOrigin.PHASE18_RECONSTRUCTED
        ),
        qore_symbol="EURUSD",
        side="long",
        signal_at=datetime(2021, 10, 1, 12, 0, tzinfo=UTC),
        entry_at=datetime(2021, 10, 1, 12, 1, tzinfo=UTC),
        entry_price=Decimal("100"),
        structural_stop=Decimal("99"),
        technical_target=Decimal("102"),
        legacy_risk_scale=Decimal("1"),
        minimum_execution_steps=1,
        pre_trade_state=(),
        source_evidence_ids=("synthetic:phase20j-provider",),
        economics_status=ReplayEconomicsStatus.R_DENOMINATED_ONLY,
    )


def _provider_observation() -> ProviderEconomicObservation:
    return ProviderEconomicObservation(
        provider_key="synthetic-phase20j-provider",
        qore_symbol="EURUSD",
        provider_symbol="EURUSD",
        bid=Decimal("99.9"),
        ask=Decimal("100.1"),
        contract_size=Decimal("100"),
        tick_size=Decimal("0.1"),
        tick_value=Decimal("1"),
        minimum_volume=Decimal("0.01"),
        maximum_volume=Decimal("100"),
        volume_step=Decimal("0.01"),
        margin_per_volume=Decimal("20"),
        commission_per_volume_usd=Decimal("2"),
        slippage_reserve_per_volume_usd=Decimal("1"),
        observed_at=datetime(2026, 9, 27, 2, 15, tzinfo=UTC),
    )


def _provider_failure_probes() -> tuple[Phase20FailureProbe, ...]:
    evaluations = run_phase20c_counterfactual_stress_matrix(
        causal=_provider_causal(),
        observation=_provider_observation(),
        scenarios=phase20c_synthetic_predeclared_stress_scenarios(),
    )
    by_id = {item.scenario_id: item for item in evaluations}
    liquidity = by_id["CF_LIQUIDITY_UNAVAILABLE"]
    minimum = by_id["CF_MINIMUM_VOLUME_CLIFF"]
    combined = by_id["CF_COMBINED_ADVERSE"]
    baseline = by_id["CF_BASELINE_CURRENT_SNAPSHOT"]

    combined_non_improving = (
        combined.result is not None
        and baseline.result is not None
        and (
            combined.result.economics.stressed_execution_cost_per_volume_usd
            >= baseline.result.economics.stressed_execution_cost_per_volume_usd
        )
        and (
            combined.result.economics.stressed_margin_per_volume_usd
            >= baseline.result.economics.stressed_margin_per_volume_usd
        )
    )
    return (
        _probe(
            "J01_PROVIDER_LIQUIDITY_UNAVAILABLE",
            Phase20FailureDisposition.FAIL_CLOSED,
            (
                liquidity.status
                is Phase20ProviderStressStatus.FAIL_CLOSED_PROVIDER_CONSTRAINT
                and liquidity.result is None
            ),
            "Unavailable liquidity remains an explicit provider constraint failure.",
        ),
        _probe(
            "J02_PROVIDER_MINIMUM_VOLUME_CLIFF",
            Phase20FailureDisposition.FAIL_CLOSED,
            (
                minimum.status
                is Phase20ProviderStressStatus.FAIL_CLOSED_PROVIDER_CONSTRAINT
                and minimum.result is None
            ),
            "A minimum-volume/maximum-volume cliff cannot fabricate executability.",
        ),
        _probe(
            "J03_PROVIDER_COMBINED_ADVERSE_NON_IMPROVING",
            Phase20FailureDisposition.STATE_PRESERVED,
            combined_non_improving,
            "Combined provider stress cannot improve execution or margin economics.",
        ),
    )


def _capital_ledger_failure_probes(root: Path) -> tuple[Phase20FailureProbe, ...]:
    path = root / "phase20j-capital-ledger.json"
    store = DurableCapitalSourceLedgerStore(path)
    base = CapitalSourceLedger().add_source(
        source_id="phase20j-profit",
        source=CapitalSource.REALIZED_PROFIT,
        proven_amount_usd=Decimal("20"),
    )
    deployed = (
        base.reserve(
            reservation_id="phase20j-r1",
            source_id="phase20j-profit",
            amount_usd=Decimal("8"),
        )
        .deploy("phase20j-r1")
    )
    first = store.store(deployed, expected_generation=0)

    restarted_before = DurableCapitalSourceLedgerStore(path).load()
    before_account = restarted_before.ledger.accounts[0]
    restart_preserves_unsettled = (
        restarted_before.generation == first.generation
        and before_account.deployed_usd == Decimal("8")
        and before_account.available_usd == Decimal("12")
        and before_account.consumed_usd == 0
        and before_account.cumulative_released_usd == 0
    )

    settled = restarted_before.ledger.settle_deployment(
        "phase20j-r1",
        returned_capacity_usd=Decimal("3"),
    )
    second = store.store(
        settled,
        expected_generation=restarted_before.generation,
    )
    restarted_after = DurableCapitalSourceLedgerStore(path).load()
    after_account = restarted_after.ledger.accounts[0]
    delayed_settlement_preserved = (
        restarted_after.generation == second.generation
        and after_account.deployed_usd == 0
        and after_account.available_usd == Decimal("15")
        and after_account.consumed_usd == Decimal("5")
        and after_account.cumulative_released_usd == Decimal("3")
    )

    stale_rejected = _raises(
        lambda: store.store(base, expected_generation=first.generation),
        DurableCapitalLedgerError,
    )

    lock_path = path.with_name(f".{path.name}.writer-lock")
    lock_path.mkdir()
    try:
        writer_lock_rejected = _raises(
            lambda: store.store(
                restarted_after.ledger,
                expected_generation=restarted_after.generation,
            ),
            DurableCapitalLedgerError,
        )
    finally:
        lock_path.rmdir()

    corrupt_path = root / "phase20j-corrupt-capital.json"
    corrupt_path.write_text("{bad-json", encoding="utf-8")
    corrupt_rejected = _raises(
        lambda: DurableCapitalSourceLedgerStore(corrupt_path).load(),
        DurableCapitalLedgerError,
    )

    return (
        _probe(
            "J04_RESTART_PRESERVES_UNSETTLED_DEPLOYMENT",
            Phase20FailureDisposition.STATE_PRESERVED,
            restart_preserves_unsettled,
            "Restart cannot convert deployed unsettled capital into available capacity.",
        ),
        _probe(
            "J05_DELAYED_SETTLEMENT_RELEASES_ONLY_RECONCILED_RETURN",
            Phase20FailureDisposition.STATE_PRESERVED,
            delayed_settlement_preserved,
            "Delayed settlement returns only reconciled capacity and preserves consumed capital.",
        ),
        _probe(
            "J06_STALE_CAPITAL_LEDGER_GENERATION",
            Phase20FailureDisposition.FAIL_CLOSED,
            stale_rejected,
            "A stale capital-ledger writer cannot overwrite the reconciled generation.",
        ),
        _probe(
            "J07_CAPITAL_LEDGER_WRITER_LOCK",
            Phase20FailureDisposition.FAIL_CLOSED,
            writer_lock_rejected,
            "An existing durable writer lock blocks a second capital-ledger writer.",
        ),
        _probe(
            "J08_CORRUPT_CAPITAL_LEDGER_SNAPSHOT",
            Phase20FailureDisposition.FAIL_CLOSED,
            corrupt_rejected,
            "An unreadable durable capital snapshot cannot be treated as empty/fresh state.",
        ),
    )


def _portfolio_failure_probes(root: Path) -> tuple[Phase20FailureProbe, ...]:
    path = root / "phase20j-portfolio.json"
    store = DurablePortfolioAllocationStore(path)
    ledger = PortfolioAllocationLedger(
        total_stop_risk_capacity_usd=Decimal("10"),
        total_margin_capacity_usd=Decimal("20"),
        concentration_limit_by_group=(("USD", Decimal("7")),),
    )
    initialized = store.initialize(ledger)
    second = store.store(
        initialized.ledger,
        expected_generation=initialized.generation,
    )
    stale_rejected = _raises(
        lambda: store.store(
            initialized.ledger,
            expected_generation=initialized.generation,
        ),
        DurablePortfolioAllocationError,
    )

    lock_path = path.with_name(f".{path.name}.writer-lock")
    lock_path.mkdir()
    try:
        writer_lock_rejected = _raises(
            lambda: store.store(
                second.ledger,
                expected_generation=second.generation,
            ),
            DurablePortfolioAllocationError,
        )
    finally:
        lock_path.rmdir()

    restarted = DurablePortfolioAllocationStore(path).load()
    restart_preserved = (
        restarted is not None
        and restarted.generation == second.generation
        and restarted.ledger == second.ledger
    )

    return (
        _probe(
            "J09_STALE_PORTFOLIO_RESERVATION_GENERATION",
            Phase20FailureDisposition.FAIL_CLOSED,
            stale_rejected,
            "A stale portfolio allocator cannot overwrite current reservation state.",
        ),
        _probe(
            "J10_PORTFOLIO_WRITER_LOCK",
            Phase20FailureDisposition.FAIL_CLOSED,
            writer_lock_rejected,
            "A second portfolio-allocation writer is blocked while the lock is held.",
        ),
        _probe(
            "J11_PORTFOLIO_STATE_SURVIVES_RESTART",
            Phase20FailureDisposition.STATE_PRESERVED,
            restart_preserved,
            "Portfolio reservation capacity and generation survive restart.",
        ),
    )


def _settlement_failure_probes(root: Path) -> tuple[Phase20FailureProbe, ...]:
    path = root / "phase20j-settlements.json"
    store = DurableCmaSettlementStore(path)
    partial = CmaSettlementRecord(
        event="CTRADER_DEMO_PARTIAL_SETTLEMENT",
        deal_id=1,
        signal_fingerprint="phase20j-signal",
        position_id=101,
        net_profit_usd=Decimal("5"),
        position_open_after=True,
    )
    first = store.apply(partial, expected_generation=0)
    duplicate = store.apply(
        partial,
        expected_generation=first.generation,
    )
    exact_duplicate_idempotent = (
        duplicate.generation == first.generation
        and len(duplicate.states) == 1
        and len(duplicate.states[0].records) == 1
        and duplicate.states[0].realized_net_pnl_usd == Decimal("5")
    )

    conflicting = CmaSettlementRecord(
        event="CTRADER_DEMO_PARTIAL_SETTLEMENT",
        deal_id=1,
        signal_fingerprint="phase20j-signal",
        position_id=101,
        net_profit_usd=Decimal("7"),
        position_open_after=True,
    )
    conflicting_rejected = _raises(
        lambda: store.apply(
            conflicting,
            expected_generation=duplicate.generation,
        ),
        CmaSettlementLedgerError,
    )

    terminal = CmaSettlementRecord(
        event="CTRADER_DEMO_EXIT_SETTLEMENT",
        deal_id=2,
        signal_fingerprint="phase20j-signal",
        position_id=101,
        net_profit_usd=Decimal("3"),
        position_open_after=False,
    )
    closed = store.apply(
        terminal,
        expected_generation=duplicate.generation,
    )
    restarted = DurableCmaSettlementStore(path).load()
    closed_state_preserved = (
        restarted.generation == closed.generation
        and restarted.states[0].position_closed
        and restarted.states[0].realized_net_pnl_usd == Decimal("8")
    )

    post_terminal = CmaSettlementRecord(
        event="CTRADER_DEMO_PARTIAL_SETTLEMENT",
        deal_id=3,
        signal_fingerprint="phase20j-signal",
        position_id=101,
        net_profit_usd=Decimal("1"),
        position_open_after=True,
    )
    post_terminal_rejected = _raises(
        lambda: store.apply(
            post_terminal,
            expected_generation=restarted.generation,
        ),
        CmaSettlementLedgerError,
    )

    return (
        _probe(
            "J12_EXACT_DUPLICATE_SETTLEMENT_IDEMPOTENT",
            Phase20FailureDisposition.IDEMPOTENT,
            exact_duplicate_idempotent,
            "An exact repeated broker deal neither duplicates PnL nor advances generation.",
        ),
        _probe(
            "J13_CONFLICTING_DUPLICATE_SETTLEMENT",
            Phase20FailureDisposition.FAIL_CLOSED,
            conflicting_rejected,
            "The same deal id with conflicting economics is rejected.",
        ),
        _probe(
            "J14_TERMINAL_SETTLEMENT_SURVIVES_RESTART",
            Phase20FailureDisposition.STATE_PRESERVED,
            closed_state_preserved,
            "Terminal close state and realized PnL survive restart.",
        ),
        _probe(
            "J15_SETTLEMENT_AFTER_TERMINAL_EXIT",
            Phase20FailureDisposition.FAIL_CLOSED,
            post_terminal_rejected,
            "A new settlement after terminal exit is rejected.",
        ),
    )



def _provider_stress_detail_probes() -> tuple[Phase20FailureProbe, ...]:
    evaluations = run_phase20c_counterfactual_stress_matrix(
        causal=_provider_causal(),
        observation=_provider_observation(),
        scenarios=phase20c_synthetic_predeclared_stress_scenarios(),
    )
    by_id = {item.scenario_id: item for item in evaluations}
    baseline = by_id["CF_BASELINE_CURRENT_SNAPSHOT"].result
    spread = by_id["CF_SPREAD_X2"].result
    slippage = by_id["CF_SLIPPAGE_FLOOR_4"].result
    margin = by_id["CF_MARGIN_X2"].result
    delay = by_id["CF_EXECUTION_DELAY_2000MS"].result

    if baseline is None or spread is None or slippage is None or margin is None:
        raise CiboCapitalManagementError(
            "Phase20J-B executable provider stress fixture unexpectedly failed"
        )
    if delay is None:
        raise CiboCapitalManagementError(
            "Phase20J-B delay stress fixture unexpectedly failed"
        )

    return (
        _probe(
            "J16_SPREAD_EXPANSION_NON_IMPROVING",
            Phase20FailureDisposition.STATE_PRESERVED,
            (
                spread.economics.stressed_spread_cost_per_volume_usd
                > baseline.economics.stressed_spread_cost_per_volume_usd
                and spread.opportunity.intended_entry
                == baseline.opportunity.intended_entry
                and spread.opportunity.stop_loss
                == baseline.opportunity.stop_loss
            ),
            "Spread expansion worsens execution economics without changing Trader geometry.",
        ),
        _probe(
            "J17_SLIPPAGE_RESERVE_NON_IMPROVING",
            Phase20FailureDisposition.STATE_PRESERVED,
            (
                slippage.economics.stressed_slippage_reserve_per_volume_usd
                > baseline.economics.stressed_slippage_reserve_per_volume_usd
                and slippage.economics.stressed_execution_cost_per_volume_usd
                > baseline.economics.stressed_execution_cost_per_volume_usd
            ),
            "Higher slippage reserve raises execution cost and cannot improve the opportunity.",
        ),
        _probe(
            "J18_MARGIN_EXPANSION_NON_IMPROVING",
            Phase20FailureDisposition.STATE_PRESERVED,
            (
                margin.economics.stressed_margin_per_volume_usd
                > baseline.economics.stressed_margin_per_volume_usd
                and margin.opportunity.margin_per_volume
                > baseline.opportunity.margin_per_volume
            ),
            "Margin expansion increases capital consumption without changing Trader geometry.",
        ),
        _probe(
            "J19_EXECUTION_DELAY_FLOOR_PRESERVED",
            Phase20FailureDisposition.STATE_PRESERVED,
            (
                delay.economics.stressed_execution_delay_ms
                == Decimal("2000")
                and delay.opportunity.intended_entry
                == baseline.opportunity.intended_entry
            ),
            "Delayed-fill stress is retained explicitly instead of being erased from evidence.",
        ),
    )


def _cluster_candidate(
    fingerprint: str,
    trader: TraderLineage,
    *,
    group: str = "USD",
) -> CapitalOpportunityCandidate:
    now = datetime(2026, 9, 27, 5, 0, tzinfo=UTC)
    return CapitalOpportunityCandidate(
        signal_fingerprint=fingerprint,
        trader_id=trader,
        qore_symbol=fingerprint.upper(),
        provider_symbol=fingerprint.upper(),
        decision_as_of=now,
        expectation=CausalOpportunityExpectation(
            evidence_id=f"phase20j-b:{fingerprint}",
            as_of=now,
            basis=CausalExpectationBasis.FROZEN_HISTORICAL_PRIOR,
            expected_net_value_usd=Decimal("10"),
            expected_capital_minutes=Decimal("10"),
        ),
        stop_risk_usd=Decimal("5"),
        margin_usd=Decimal("10"),
        concentration_group=group,
        concentration_risk_usd=Decimal("5"),
    )


def _portfolio_cluster_failure_probes() -> tuple[Phase20FailureProbe, ...]:
    correlated = allocate_competing_opportunities(
        (
            _cluster_candidate("corr-a", TraderLineage.R38_EURUSD),
            _cluster_candidate("corr-b", TraderLineage.R43_GBPUSD),
        ),
        OpportunityAllocationBudget(
            stop_risk_headroom_usd=Decimal("20"),
            margin_headroom_usd=Decimal("100"),
            concentration_limit_by_group=(("USD", Decimal("7")),),
        ),
    )
    clustered = allocate_competing_opportunities(
        (
            _cluster_candidate("cluster-a", TraderLineage.R38_EURUSD, group="A"),
            _cluster_candidate("cluster-b", TraderLineage.R43_GBPUSD, group="B"),
            _cluster_candidate("cluster-c", TraderLineage.VT31_NAS100, group="C"),
        ),
        OpportunityAllocationBudget(
            stop_risk_headroom_usd=Decimal("10"),
            margin_headroom_usd=Decimal("100"),
            concentration_limit_by_group=(
                ("A", Decimal("10")),
                ("B", Decimal("10")),
                ("C", Decimal("10")),
            ),
        ),
    )
    return (
        _probe(
            "J20_CORRELATION_CONCENTRATION_BLOCKS_SECOND_USE",
            Phase20FailureDisposition.FAIL_CLOSED,
            (
                len(correlated.selected_signal_fingerprints) == 1
                and correlated.used_stop_risk_usd == Decimal("5")
                and "concentration" in correlated.rows[1].reason
            ),
            "A correlation/concentration group cannot silently consume excess shared risk.",
        ),
        _probe(
            "J21_SIMULTANEOUS_CLUSTER_RESPECTS_STOP_RISK_CAPACITY",
            Phase20FailureDisposition.STATE_PRESERVED,
            (
                len(clustered.selected_signal_fingerprints) == 2
                and clustered.used_stop_risk_usd == Decimal("10")
                and any(
                    row.reason == "shared stop-risk headroom exhausted"
                    for row in clustered.rows
                    if not row.selected
                )
            ),
            "A same-time opportunity cluster cannot reserve beyond shared stop-risk capacity.",
        ),
    )


def _simultaneous_loss_conservation_probe() -> Phase20FailureProbe:
    ledger = CapitalSourceLedger().add_source(
        source_id="phase20j-b-loss-capital",
        source=CapitalSource.ORIGINAL_BASE_CAPITAL,
        proven_amount_usd=Decimal("10"),
    )
    reserved = ledger.reserve_many(
        (
            CapitalReservationRequest(
                reservation_id="phase20j-b-loss-a",
                source_id="phase20j-b-loss-capital",
                amount_usd=Decimal("5"),
            ),
            CapitalReservationRequest(
                reservation_id="phase20j-b-loss-b",
                source_id="phase20j-b-loss-capital",
                amount_usd=Decimal("5"),
            ),
        )
    )
    deployed = (
        reserved.deploy("phase20j-b-loss-a")
        .deploy("phase20j-b-loss-b")
    )
    settled = (
        deployed.settle_deployment(
            "phase20j-b-loss-a",
            returned_capacity_usd=Decimal("0"),
        )
        .settle_deployment(
            "phase20j-b-loss-b",
            returned_capacity_usd=Decimal("0"),
        )
    )
    account = settled.accounts[0]
    conserved = (
        account.proven_amount_usd == Decimal("10")
        and account.available_usd == 0
        and account.reserved_usd == 0
        and account.deployed_usd == 0
        and account.consumed_usd == Decimal("10")
        and (
            account.available_usd
            + account.reserved_usd
            + account.deployed_usd
            + account.consumed_usd
        )
        == account.proven_amount_usd
    )
    return _probe(
        "J22_SIMULTANEOUS_FULL_LOSSES_PRESERVE_CAPITAL_CONSERVATION",
        Phase20FailureDisposition.STATE_PRESERVED,
        conserved,
        (
            "Two simultaneous full losses consume proven capital without "
            "negative or fictitious capacity."
        ),
    )


def run_phase20j_provider_cluster_failure_engineering(
) -> Phase20FailureEngineeringReport:
    """Run Phase20J-B provider-shock and clustered-capital failure probes."""

    probes = (
        *_provider_stress_detail_probes(),
        *_portfolio_cluster_failure_probes(),
        _simultaneous_loss_conservation_probe(),
    )
    return Phase20FailureEngineeringReport(
        identity="CIBO_PHASE20J_B_PROVIDER_CLUSTER_FAILURE_V1",
        probes=probes,
    )


def run_phase20j_failure_engineering(
    *,
    root: Path,
) -> Phase20FailureEngineeringReport:
    """Run the synthetic Phase20J-A cross-surface failure matrix."""

    if not isinstance(root, Path):
        raise CiboCapitalManagementError("Phase20J root must be pathlib.Path")
    root.mkdir(parents=True, exist_ok=True)
    probes = (
        *_provider_failure_probes(),
        *_capital_ledger_failure_probes(root),
        *_portfolio_failure_probes(root),
        *_settlement_failure_probes(root),
    )
    return Phase20FailureEngineeringReport(
        identity="CIBO_PHASE20J_A_FAILURE_ENGINEERING_V1",
        probes=probes,
    )
