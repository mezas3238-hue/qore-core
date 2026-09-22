"""Evidence-only readiness gate for QORE's first cTrader DEMO execution phase.

The gate declares the *software/qualification phase* ready only when:
- all 31 catalog Traders have entered governed Trader Lab intake;
- the five first-cohort Traders have all been assessed and at least one is
  authentically DEMO_ELIGIBLE/selectable;
- cTrader configuration is DEMO-only; and
- a fresh authenticated cTrader DEMO preflight reports AVAILABLE.

A READY result is not an order and does not manufacture Risk authority.  A
current Trader SETUP and the downstream Risk->ExecutionSubmission path are still
required for the actual provider mutation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

from qore.infrastructure.ctrader_demo_execution_configuration import (
    CTraderDemoRuntimeConfiguration,
)
from qore.infrastructure.market_test_environment import MarketRuntimeEnvironment
from qore.infrastructure.ports import ExternalHealth, PortAvailability
from qore.infrastructure.trader_lab.catalog import TraderLabCatalogEnrollmentSet
from qore.infrastructure.trader_lab.cohort import (
    FirstCohortDemoSelection,
    FirstCohortLabStatus,
)
from qore.infrastructure.trader_lab.lifecycle import TraderLabState
from qore.kernel.errors import InfrastructureError


class FirstDemoExecutionPhaseError(InfrastructureError):
    """Phase-readiness input violates exact invariants."""

    __slots__ = ()


class FirstDemoExecutionPhaseStatus(StrEnum):
    BLOCKED = "blocked"
    READY_FOR_FIRST_EXECUTION = "ready_for_first_execution"


@dataclass(frozen=True, slots=True)
class FirstDemoExecutionPhasePolicy:
    """Explicit freshness policy for the authenticated broker preflight."""

    max_preflight_age: timedelta

    def __post_init__(self) -> None:
        if type(self.max_preflight_age) is not timedelta:
            raise FirstDemoExecutionPhaseError(
                "max_preflight_age must be timedelta"
            )
        if self.max_preflight_age <= timedelta(0):
            raise FirstDemoExecutionPhaseError(
                "max_preflight_age must be positive"
            )


@dataclass(frozen=True, slots=True)
class FirstDemoExecutionPhaseReadiness:
    """Immutable phase verdict; READY has no execution authority by itself."""

    status: FirstDemoExecutionPhaseStatus
    blockers: tuple[str, ...]
    catalog: TraderLabCatalogEnrollmentSet
    selection: FirstCohortDemoSelection
    provider_health: ExternalHealth
    configuration: CTraderDemoRuntimeConfiguration
    evaluated_at: datetime

    def __post_init__(self) -> None:
        if type(self.status) is not FirstDemoExecutionPhaseStatus:
            raise FirstDemoExecutionPhaseError(
                "phase status must be FirstDemoExecutionPhaseStatus"
            )
        if type(self.blockers) is not tuple or any(
            type(item) is not str or not item for item in self.blockers
        ):
            raise FirstDemoExecutionPhaseError(
                "phase blockers must be an immutable non-empty-string tuple"
            )
        if len(set(self.blockers)) != len(self.blockers):
            raise FirstDemoExecutionPhaseError(
                "phase blockers must not contain duplicates"
            )
        if self.status is FirstDemoExecutionPhaseStatus.READY_FOR_FIRST_EXECUTION:
            if self.blockers:
                raise FirstDemoExecutionPhaseError(
                    "ready phase must not carry blockers"
                )
        elif not self.blockers:
            raise FirstDemoExecutionPhaseError(
                "blocked phase must carry at least one blocker"
            )
        if not isinstance(self.catalog, TraderLabCatalogEnrollmentSet):
            raise FirstDemoExecutionPhaseError(
                "phase catalog must be TraderLabCatalogEnrollmentSet"
            )
        self.catalog.__post_init__()
        if not isinstance(self.selection, FirstCohortDemoSelection):
            raise FirstDemoExecutionPhaseError(
                "phase selection must be FirstCohortDemoSelection"
            )
        self.selection.__post_init__()
        if not isinstance(self.provider_health, ExternalHealth):
            raise FirstDemoExecutionPhaseError(
                "phase provider_health must be ExternalHealth"
            )
        self.provider_health.__post_init__()
        if not isinstance(self.configuration, CTraderDemoRuntimeConfiguration):
            raise FirstDemoExecutionPhaseError(
                "phase configuration must be CTraderDemoRuntimeConfiguration"
            )
        if (
            type(self.evaluated_at) is not datetime
            or self.evaluated_at.tzinfo is None
            or self.evaluated_at.utcoffset() is None
        ):
            raise FirstDemoExecutionPhaseError(
                "phase evaluated_at must be timezone-aware"
            )

    @property
    def phase_complete(self) -> bool:
        return self.status is FirstDemoExecutionPhaseStatus.READY_FOR_FIRST_EXECUTION


def evaluate_first_demo_execution_phase(
    *,
    catalog: TraderLabCatalogEnrollmentSet,
    selection: FirstCohortDemoSelection,
    provider_health: ExternalHealth,
    configuration: CTraderDemoRuntimeConfiguration,
    policy: FirstDemoExecutionPhasePolicy,
    evaluated_at: datetime,
) -> FirstDemoExecutionPhaseReadiness:
    """Return the fail-closed readiness verdict for first DEMO execution."""

    if not isinstance(catalog, TraderLabCatalogEnrollmentSet):
        raise FirstDemoExecutionPhaseError(
            "catalog must be TraderLabCatalogEnrollmentSet"
        )
    catalog.__post_init__()
    if not isinstance(selection, FirstCohortDemoSelection):
        raise FirstDemoExecutionPhaseError(
            "selection must be FirstCohortDemoSelection"
        )
    selection.__post_init__()
    if not isinstance(provider_health, ExternalHealth):
        raise FirstDemoExecutionPhaseError(
            "provider_health must be ExternalHealth"
        )
    provider_health.__post_init__()
    if not isinstance(configuration, CTraderDemoRuntimeConfiguration):
        raise FirstDemoExecutionPhaseError(
            "configuration must be CTraderDemoRuntimeConfiguration"
        )
    if not isinstance(policy, FirstDemoExecutionPhasePolicy):
        raise FirstDemoExecutionPhaseError(
            "policy must be FirstDemoExecutionPhasePolicy"
        )
    policy.__post_init__()
    if (
        type(evaluated_at) is not datetime
        or evaluated_at.tzinfo is None
        or evaluated_at.utcoffset() is None
    ):
        raise FirstDemoExecutionPhaseError(
            "evaluated_at must be timezone-aware"
        )

    blockers: list[str] = []
    if not catalog.all_traders_enrolled:
        blockers.append("not_all_31_traders_enrolled")
    if len(catalog.first_demo_cohort) != 5:
        blockers.append("first_demo_cohort_not_enrolled")

    selected = selection.selected
    selectable = tuple(
        assessment
        for assessment in selection.assessments
        if assessment.status is FirstCohortLabStatus.SELECTABLE
    )
    if selected is None or not selectable:
        blockers.append("no_demo_eligible_trader_selected")
    elif selected.lifecycle.state is not TraderLabState.DEMO_ELIGIBLE:
        blockers.append("selected_trader_not_demo_eligible")

    if configuration.environment is not MarketRuntimeEnvironment.DEMO:
        blockers.append("ctrader_configuration_not_demo")
    if provider_health.availability is not PortAvailability.AVAILABLE:
        blockers.append("ctrader_demo_preflight_unavailable")
    if provider_health.checked_at > evaluated_at:
        blockers.append("ctrader_demo_preflight_from_future")
    elif evaluated_at - provider_health.checked_at > policy.max_preflight_age:
        blockers.append("ctrader_demo_preflight_stale")

    status = (
        FirstDemoExecutionPhaseStatus.READY_FOR_FIRST_EXECUTION
        if not blockers
        else FirstDemoExecutionPhaseStatus.BLOCKED
    )
    return FirstDemoExecutionPhaseReadiness(
        status=status,
        blockers=tuple(blockers),
        catalog=catalog,
        selection=selection,
        provider_health=provider_health,
        configuration=configuration,
        evaluated_at=evaluated_at,
    )
