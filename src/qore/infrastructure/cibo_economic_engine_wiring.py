"""CIBO economic-engine wiring.

This module contains cabling only.  It does not duplicate decision logic and it
does not translate one engine into another.  Canonical engine contracts are
passed directly between native CIBO engines:

Full Economic Twin
    -> GEN-C11 native multi-world MPC
    -> native account-wide Portfolio/Adaptive Leverage
    -> optional universal Position Lifecycle evaluations
    -> optional T14/T20 release -> capital-velocity redeployment proposal

CMA, QORE Risk and Execution remain downstream authorities.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from qore.infrastructure.cibo_capital_velocity_redeployment import (
    CiboCapitalReleaseEvent,
    CiboCapitalVelocityLedger,
    CiboRedeploymentProposal,
    consume_release_once,
    propose_redeployment,
)
from qore.infrastructure.cibo_full_economic_digital_twin import (
    CiboObservedEconomicTwin,
)
from qore.infrastructure.cibo_multi_period_capital_mpc import (
    Genc11KnownOptionSchedule,
    Genc11MultiPeriodPlan,
    Genc11WorldPath,
    plan_genc11_multi_period_capital,
)
from qore.infrastructure.cibo_portfolio_allocation_engine import (
    CiboPortfolioAllocationPlan,
    plan_account_wide_capital_allocation,
)
from qore.infrastructure.cibo_position_lifecycle import (
    CiboLifecycleFeature,
    CiboPositionLifecycleInput,
    CiboPositionLifecycleResult,
    FULL_CIBO_LIFECYCLE_FEATURES,
    run_cibo_position_lifecycle,
)
from qore.infrastructure.trader_lab.ict_turtle_soup_r4_source_exact import Bar


@dataclass(frozen=True, slots=True)
class CiboLifecycleWireRequest:
    position: CiboPositionLifecycleInput
    bars: tuple[Bar, ...]
    features: frozenset[
        CiboLifecycleFeature
    ] = FULL_CIBO_LIFECYCLE_FEATURES


@dataclass(frozen=True, slots=True)
class CiboEconomicEngineRun:
    twin_id: str
    genc11_plan: Genc11MultiPeriodPlan
    portfolio_plan: CiboPortfolioAllocationPlan
    lifecycle_results: tuple[CiboPositionLifecycleResult, ...]
    release_ledger: CiboCapitalVelocityLedger | None
    redeployment_proposals: tuple[CiboRedeploymentProposal, ...]
    allocation_authority: bool = False
    risk_authority: bool = False
    execution_authority: bool = False


def run_cibo_economic_engine_chain(
    *,
    twin: CiboObservedEconomicTwin,
    world_paths: tuple[Genc11WorldPath, ...],
    option_schedules: tuple[Genc11KnownOptionSchedule, ...],
    lifecycle_requests: Sequence[CiboLifecycleWireRequest] = (),
    release_events: Sequence[CiboCapitalReleaseEvent] = (),
) -> CiboEconomicEngineRun:
    """Run canonical CIBO engines through explicit direct wiring."""

    genc11 = plan_genc11_multi_period_capital(
        plan_id=f"genc11:{twin.twin_id}",
        twin=twin,
        world_paths=world_paths,
        option_schedules=option_schedules,
    )
    portfolio = plan_account_wide_capital_allocation(twin)

    lifecycle_results = tuple(
        run_cibo_position_lifecycle(
            request.position,
            request.bars,
            features=request.features,
        )
        for request in lifecycle_requests
    )

    ledger: CiboCapitalVelocityLedger | None = None
    proposals: list[CiboRedeploymentProposal] = []
    if release_events:
        ledger = CiboCapitalVelocityLedger()
        for release in release_events:
            ledger = consume_release_once(ledger, release)
            proposals.append(
                propose_redeployment(
                    twin=twin,
                    release=release,
                )
            )

    return CiboEconomicEngineRun(
        twin_id=twin.twin_id,
        genc11_plan=genc11,
        portfolio_plan=portfolio,
        lifecycle_results=lifecycle_results,
        release_ledger=ledger,
        redeployment_proposals=tuple(proposals),
        allocation_authority=False,
        risk_authority=False,
        execution_authority=False,
    )
