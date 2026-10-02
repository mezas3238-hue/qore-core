from datetime import UTC, datetime
from decimal import Decimal

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
    CiboCapitalMissionPolicy,
    derive_cibo_capital_mission,
    fundednext_stellar_instant_identity,
)
from qore.infrastructure.cibo_ce2i_causal_expectation import (
    CausalExpectationBasis,
    CausalOpportunityExpectation,
)
from qore.infrastructure.cibo_ce2i_opportunity_competition import (
    CapitalOpportunityCandidate,
)
from qore.infrastructure.cibo_ce2i_optionality import KnownCapitalOption
from qore.infrastructure.cibo_ce2i_phase20_robust_allocator import (
    Phase20AllocatorDisposition,
    propose_phase20h_robust_allocation,
)
from qore.infrastructure.cibo_ce2i_regime_selector import (
    CiboCapitalRegimeState,
    CiboRegimePosture,
    CiboRegimeToolSelection,
    CorrelationState,
    LiquidityState,
    ProviderCondition,
    VolatilityState,
    select_ce2i_tools_for_regime,
)
from qore.infrastructure.market_test_environment import MarketRuntimeEnvironment

NOW = datetime(2026, 9, 27, 5, 30, tzinfo=UTC)


def _demo_mission() -> CiboCapitalMissionPolicy:
    return derive_cibo_capital_mission(
        CiboAccountCapitalIdentity(
            provider_key="ctrader-demo",
            account_ref="phase20h-demo",
            environment=MarketRuntimeEnvironment.DEMO,
        )
    )


def _regime(
    mission: CiboCapitalMissionPolicy,
    *,
    drawdown: str = "0.20",
    adverse: bool = False,
    stale: bool = False,
    opportunity_count: int = 2,
) -> CiboRegimeToolSelection:
    return select_ce2i_tools_for_regime(
        mission=mission,
        state=CiboCapitalRegimeState(
            liquidity=LiquidityState.NORMAL,
            volatility=VolatilityState.NORMAL,
            correlation=CorrelationState.NORMAL,
            provider_condition=ProviderCondition.HEALTHY,
            risk_utilization=Decimal("0.20"),
            margin_utilization=Decimal("0.20"),
            drawdown_utilization=Decimal(drawdown),
            opportunity_count=opportunity_count,
            position_path_adverse=adverse,
            evidence_stale=stale,
        ),
    )


def _candidate(
    fingerprint: str,
    trader: TraderLineage,
    *,
    net: str,
    minutes: str,
    group: str = "USD",
) -> CapitalOpportunityCandidate:
    return CapitalOpportunityCandidate(
        signal_fingerprint=fingerprint,
        trader_id=trader,
        qore_symbol=fingerprint.upper(),
        provider_symbol=fingerprint.upper(),
        decision_as_of=NOW,
        expectation=CausalOpportunityExpectation(
            evidence_id=f"phase20h:{fingerprint}",
            as_of=NOW,
            basis=CausalExpectationBasis.FROZEN_HISTORICAL_PRIOR,
            expected_net_value_usd=Decimal(net),
            expected_capital_minutes=Decimal(minutes),
        ),
        stop_risk_usd=Decimal("5"),
        margin_usd=Decimal("10"),
        concentration_group=group,
        concentration_risk_usd=Decimal("5"),
    )


def _options() -> tuple[KnownCapitalOption, ...]:
    return (
        KnownCapitalOption(
            opportunity_id="future-small",
            minimum_stop_risk_usd=Decimal("4"),
            minimum_margin_usd=Decimal("20"),
        ),
        KnownCapitalOption(
            opportunity_id="future-large",
            minimum_stop_risk_usd=Decimal("10"),
            minimum_margin_usd=Decimal("40"),
        ),
    )


def test_phase20h_stable_demo_allocates_inside_shared_headroom() -> None:
    mission = _demo_mission()
    fast = _candidate(
        "fast",
        TraderLineage.R43_GBPUSD,
        net="8",
        minutes="5",
    )
    slow = _candidate(
        "slow",
        TraderLineage.R38_EURUSD,
        net="10",
        minutes="20",
    )

    decision = propose_phase20h_robust_allocation(
        mission=mission,
        regime=_regime(mission),
        hard_risk_headroom_usd=Decimal("5"),
        margin_headroom_usd=Decimal("100"),
        concentration_limit_by_group=(("USD", Decimal("100")),),
        candidates=(slow, fast),
    )

    assert decision.disposition is Phase20AllocatorDisposition.ALLOCATE
    assert decision.reserve_stop_risk_usd == 0
    assert decision.deployable_stop_risk_usd == Decimal("5")
    assert decision.allocation is not None
    assert decision.allocation.selected_signal_fingerprints == ("fast",)
    assert decision.allocation.used_stop_risk_usd == Decimal("5")
    assert decision.applied_tools == ("T15", "T09", "T18")


def test_phase20h_single_stable_candidate_does_not_require_competition() -> None:
    mission = _demo_mission()
    decision = propose_phase20h_robust_allocation(
        mission=mission,
        regime=_regime(mission, opportunity_count=1),
        hard_risk_headroom_usd=Decimal("5"),
        margin_headroom_usd=Decimal("100"),
        concentration_limit_by_group=(("USD", Decimal("100")),),
        candidates=(
            _candidate(
                "solo",
                TraderLineage.R43_GBPUSD,
                net="8",
                minutes="5",
            ),
        ),
    )

    assert decision.disposition is Phase20AllocatorDisposition.ALLOCATE
    assert decision.allocation is not None
    assert decision.allocation.selected_signal_fingerprints == ("solo",)
    assert decision.applied_tools == ("T15",)
    assert decision.reason == (
        "single causal candidate evaluated directly against T01 capacity "
        "gates without T09/T18 competition"
    )




def test_phase20h_single_candidate_negative_rank_prior_cannot_veto_t01() -> None:
    mission = _demo_mission()
    decision = propose_phase20h_robust_allocation(
        mission=mission,
        regime=_regime(mission, opportunity_count=1),
        hard_risk_headroom_usd=Decimal("5"),
        margin_headroom_usd=Decimal("100"),
        concentration_limit_by_group=(("USD", Decimal("100")),),
        candidates=(
            _candidate(
                "solo-negative-prior",
                TraderLineage.VT08_FOREX,
                net="-1",
                minutes="105",
            ),
        ),
    )

    assert decision.disposition is Phase20AllocatorDisposition.ALLOCATE
    assert decision.allocation is not None
    assert decision.allocation.selected_signal_fingerprints == (
        "solo-negative-prior",
    )
    assert decision.allocation.rows[0].reason == (
        "single valid opportunity fits T01 capacity gates"
    )
    assert decision.applied_tools == ("T15",)


def test_phase20h_single_candidate_still_fails_closed_on_margin() -> None:
    mission = _demo_mission()
    decision = propose_phase20h_robust_allocation(
        mission=mission,
        regime=_regime(mission, opportunity_count=1),
        hard_risk_headroom_usd=Decimal("5"),
        margin_headroom_usd=Decimal("9"),
        concentration_limit_by_group=(("USD", Decimal("100")),),
        candidates=(
            _candidate(
                "solo-margin",
                TraderLineage.R43_GBPUSD,
                net="8",
                minutes="5",
            ),
        ),
    )

    assert decision.disposition is Phase20AllocatorDisposition.NO_ELIGIBLE_ALLOCATION
    assert decision.allocation is not None
    assert decision.allocation.selected_signal_fingerprints == ()
    assert decision.allocation.rows[0].reason == "shared margin headroom exhausted"


def test_phase20h_recovery_preserves_all_new_capital() -> None:
    mission = _demo_mission()
    decision = propose_phase20h_robust_allocation(
        mission=mission,
        regime=_regime(mission, drawdown="0.80"),
        hard_risk_headroom_usd=Decimal("60"),
        margin_headroom_usd=Decimal("500"),
        concentration_limit_by_group=(("USD", Decimal("100")),),
        candidates=(
            _candidate(
                "fast",
                TraderLineage.R43_GBPUSD,
                net="8",
                minutes="5",
            ),
        ),
        known_options=_options(),
    )

    assert decision.regime_posture is CiboRegimePosture.RECOVERY
    assert decision.disposition is Phase20AllocatorDisposition.PRESERVE_CAPACITY
    assert decision.reserve_stop_risk_usd == Decimal("60")
    assert decision.reserve_margin_usd == Decimal("500")
    assert decision.deployable_stop_risk_usd == 0
    assert decision.allocation is None
    assert decision.applied_tools == ("T15", "T13")


def test_phase20h_stale_regime_halts_without_invoking_blocked_tools() -> None:
    mission = _demo_mission()
    decision = propose_phase20h_robust_allocation(
        mission=mission,
        regime=_regime(mission, stale=True),
        hard_risk_headroom_usd=Decimal("60"),
        margin_headroom_usd=Decimal("500"),
        concentration_limit_by_group=(("USD", Decimal("100")),),
        candidates=(),
        known_options=_options(),
    )

    assert decision.regime_posture is CiboRegimePosture.HALT_NEW_CAPITAL
    assert decision.disposition is Phase20AllocatorDisposition.PRESERVE_CAPACITY
    assert decision.applied_tools == ()
    assert decision.reserve_stop_risk_usd == Decimal("60")
    assert decision.deployable_stop_risk_usd == 0
    assert decision.allocation is None


def test_phase20h_defensive_reserves_option_and_blocks_competition() -> None:
    mission = _demo_mission()
    decision = propose_phase20h_robust_allocation(
        mission=mission,
        regime=_regime(mission, adverse=True),
        hard_risk_headroom_usd=Decimal("60"),
        margin_headroom_usd=Decimal("500"),
        concentration_limit_by_group=(("USD", Decimal("100")),),
        candidates=(
            _candidate(
                "fast",
                TraderLineage.R43_GBPUSD,
                net="8",
                minutes="5",
            ),
        ),
        known_options=_options(),
    )

    assert decision.regime_posture is CiboRegimePosture.DEFENSIVE
    assert decision.disposition is Phase20AllocatorDisposition.NO_ELIGIBLE_ALLOCATION
    assert decision.reserve_stop_risk_usd == Decimal("4")
    assert decision.reserve_margin_usd == Decimal("20")
    assert decision.reserved_for_opportunity_ids == ("future-small",)
    assert decision.applied_tools == ("T15",)
    assert decision.allocation is None


def test_phase20h_external_capital_fails_conservative_without_t15() -> None:
    mission = derive_cibo_capital_mission(
        fundednext_stellar_instant_identity(account_ref="phase20h-funded")
    )
    decision = propose_phase20h_robust_allocation(
        mission=mission,
        regime=_regime(mission),
        hard_risk_headroom_usd=Decimal("60"),
        margin_headroom_usd=Decimal("500"),
        concentration_limit_by_group=(("USD", Decimal("100")),),
        candidates=(
            _candidate(
                "fast",
                TraderLineage.R43_GBPUSD,
                net="8",
                minutes="5",
            ),
        ),
        known_options=_options(),
    )

    assert decision.disposition is Phase20AllocatorDisposition.PRESERVE_CAPACITY
    assert decision.reserve_stop_risk_usd == Decimal("60")
    assert decision.reserve_margin_usd == Decimal("500")
    assert decision.deployable_stop_risk_usd == 0
    assert decision.applied_tools == ()
    assert decision.allocation is None


def test_phase20h_candidate_order_does_not_change_selection() -> None:
    mission = _demo_mission()
    fast = _candidate(
        "fast",
        TraderLineage.R43_GBPUSD,
        net="8",
        minutes="5",
    )
    slow = _candidate(
        "slow",
        TraderLineage.R38_EURUSD,
        net="10",
        minutes="20",
    )
    regime = _regime(mission)
    left = propose_phase20h_robust_allocation(
        mission=mission,
        regime=regime,
        hard_risk_headroom_usd=Decimal("5"),
        margin_headroom_usd=Decimal("100"),
        concentration_limit_by_group=(("USD", Decimal("100")),),
        candidates=(slow, fast),
    )
    right = propose_phase20h_robust_allocation(
        mission=mission,
        regime=regime,
        hard_risk_headroom_usd=Decimal("5"),
        margin_headroom_usd=Decimal("100"),
        concentration_limit_by_group=(("USD", Decimal("100")),),
        candidates=(fast, slow),
    )

    assert left.allocation is not None
    assert right.allocation is not None
    assert left.allocation == right.allocation
    assert left.allocation.selected_signal_fingerprints == ("fast",)


def test_phase20h_candidate_grants_no_policy_or_runtime_authority() -> None:
    mission = _demo_mission()
    decision = propose_phase20h_robust_allocation(
        mission=mission,
        regime=_regime(mission),
        hard_risk_headroom_usd=Decimal("5"),
        margin_headroom_usd=Decimal("100"),
        concentration_limit_by_group=(("USD", Decimal("100")),),
        candidates=(),
    )

    assert decision.outcome_aware is False
    assert decision.validation_tuned is False
    assert decision.phase19j_burned_validation_reused is False
    assert decision.policy_certified is False
    assert decision.allocation_authority is False
    assert decision.risk_authority is False
    assert decision.execution_authority is False
    assert decision.demo_execution_authorized is False
    assert decision.live_authorized is False
    assert decision.real_capital_authorized is False
    assert decision.merge_authorized is False
