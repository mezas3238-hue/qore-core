"""Composite Portfolio capability sensor for CIBO Maximum Capability."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_full_economic_digital_twin import (
    CiboObservedEconomicTwin,
)
from qore.infrastructure.cibo_portfolio_shadow_efficiency_sensor import (
    CiboPortfolioShadowEfficiencyReport,
    measure_portfolio_shadow_efficiency,
)
from qore.infrastructure.cibo_position_continuation_coverage_sensor import (
    CiboPositionContinuationCoverage,
    measure_position_continuation_coverage,
)
from qore.infrastructure.cibo_position_release_readiness_sensor import (
    CiboPositionReleaseReadinessReport,
    measure_position_release_readiness,
)
from qore.infrastructure.cibo_reused_holdout_compound_portfolio_lane import (
    CompoundPortfolioShadowDecision,
)


@dataclass(frozen=True, slots=True)
class CiboPortfolioEngineCapabilityReport:
    twin_id: str
    continuation: CiboPositionContinuationCoverage
    release_readiness: CiboPositionReleaseReadinessReport
    shadow: CiboPortfolioShadowEfficiencyReport
    continuation_efficiency: Decimal
    release_execution_efficiency: Decimal
    shadow_actuation_efficiency: Decimal
    portfolio_capability_efficiency: Decimal
    primary_blocker: str
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if not self.twin_id or not self.primary_blocker:
            raise CiboCapitalManagementError(
                "Portfolio capability identity/blocker required"
            )
        for name in (
            "continuation_efficiency",
            "release_execution_efficiency",
            "shadow_actuation_efficiency",
            "portfolio_capability_efficiency",
        ):
            value = getattr(self, name)
            if value < 0 or value > 1:
                raise CiboCapitalManagementError(
                    f"Portfolio capability {name} outside [0,1]"
                )
        if self.productive_authority:
            raise CiboCapitalManagementError(
                "Portfolio capability sensor cannot acquire authority"
            )


def measure_portfolio_engine_capability(
    *,
    twin: CiboObservedEconomicTwin,
    shadow_decisions: tuple[CompoundPortfolioShadowDecision, ...],
) -> CiboPortfolioEngineCapabilityReport:
    continuation = measure_position_continuation_coverage(twin)
    readiness = measure_position_release_readiness(twin)
    shadow = measure_portfolio_shadow_efficiency(shadow_decisions)

    if continuation.open_position_count == 0:
        continuation_efficiency = Decimal(1)
        release_efficiency = Decimal(1)
    else:
        continuation_efficiency = continuation.continuation_coverage
        release_efficiency = readiness.executable_release_rate

    if shadow.open_position_competition_count == 0:
        shadow_efficiency = Decimal(1)
    elif shadow.release_proposal_count == 0:
        # A valid KEEP decision is complete without a mutation path.
        shadow_efficiency = Decimal(1)
    else:
        # RELEASE is still shadow-only. Proposal frequency must never be
        # misreported as real economic actuation.
        shadow_efficiency = Decimal(0)

    capability = min(
        continuation_efficiency,
        release_efficiency,
        shadow_efficiency,
    )

    if continuation.primary_blocker not in {
        "NONE",
        "NO_OPEN_POSITION_COMPETITION",
    }:
        blocker = continuation.primary_blocker
    elif readiness.primary_blocker not in {
        "NONE",
        "NO_OPEN_POSITIONS",
    }:
        blocker = readiness.primary_blocker
    elif shadow.primary_blocker == (
        "SHADOW_RELEASE_REQUIRES_EXECUTABLE_SETTLEMENT_EVIDENCE"
    ):
        blocker = shadow.primary_blocker
    else:
        blocker = "NONE"

    return CiboPortfolioEngineCapabilityReport(
        twin_id=twin.twin_id,
        continuation=continuation,
        release_readiness=readiness,
        shadow=shadow,
        continuation_efficiency=continuation_efficiency,
        release_execution_efficiency=release_efficiency,
        shadow_actuation_efficiency=shadow_efficiency,
        portfolio_capability_efficiency=capability,
        primary_blocker=blocker,
        productive_authority=False,
    )
