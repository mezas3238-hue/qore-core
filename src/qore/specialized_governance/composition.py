from __future__ import annotations

from dataclasses import dataclass

from qore.core.application import CoreApplication
from qore.core.bootstrap import bootstrap
from qore.core.configuration import Configuration
from qore.core.lifecycle import Clock, EventIdSource
from qore.core.runtime import RuntimeContext
from qore.domain.composition import ComposableDomainModule
from qore.governance.composition import FunctionalModules
from qore.governance.decision_flow import CrossModuleDecisionFlow
from qore.kernel.errors import KernelError, ValidationError
from qore.kernel.result import Failure, Result, Success
from qore.modules.knowledge.module import KnowledgeServiceModule
from qore.modules.optimization.module import OptimizationServiceModule
from qore.modules.statistics.module import StatisticsServiceModule
from qore.modules.trader.module import VirtualTraderModule
from qore.modules.validation.module import ValidationLabModule
from qore.specialized_governance.decision_flow import SpecializedServicesDecisionFlow


@dataclass(frozen=True, slots=True)
class SpecializedServiceModules:
    """Official immutable PHASE-05 specialized-service module set."""

    trader: VirtualTraderModule
    validation: ValidationLabModule
    statistics: StatisticsServiceModule
    knowledge: KnowledgeServiceModule
    optimization: OptimizationServiceModule

    @classmethod
    def create(cls) -> SpecializedServiceModules:
        """Build one new isolated specialized-service module set."""
        return cls(
            trader=VirtualTraderModule(),
            validation=ValidationLabModule(),
            statistics=StatisticsServiceModule(),
            knowledge=KnowledgeServiceModule(),
            optimization=OptimizationServiceModule(),
        )

    def domain_modules(self) -> tuple[
        VirtualTraderModule,
        ValidationLabModule,
        StatisticsServiceModule,
        KnowledgeServiceModule,
        OptimizationServiceModule,
    ]:
        """Return the official deterministic specialized-module order."""
        return (
            self.trader,
            self.validation,
            self.statistics,
            self.knowledge,
            self.optimization,
        )


@dataclass(frozen=True, slots=True)
class SpecializedGovernanceApplication:
    """PHASE-05 root object above Functional Governance and the official Core."""

    core: CoreApplication
    functional_modules: FunctionalModules
    modules: SpecializedServiceModules
    functional_decision_flow: CrossModuleDecisionFlow
    decision_flow: SpecializedServicesDecisionFlow


def compose_specialized_governance(
    configuration: Configuration,
    *,
    runtime_context: RuntimeContext | None = None,
    clock: Clock | None = None,
    event_id_source: EventIdSource | None = None,
) -> Result[SpecializedGovernanceApplication, KernelError]:
    """Compose PHASE-04 and PHASE-05 modules through one official Core bootstrap."""
    if (
        (runtime_context is None)
        != (clock is None)
        or (runtime_context is None)
        != (event_id_source is None)
    ):
        return Failure(
            ValidationError(
                "runtime_context, clock and event_id_source must be provided together"
            )
        )
    if event_id_source is not None and not callable(event_id_source):
        return Failure(ValidationError("event id source must be callable"))

    functional_modules = FunctionalModules.create()
    modules = SpecializedServiceModules.create()
    domain_modules: tuple[ComposableDomainModule, ...] = (
        functional_modules.cio,
        functional_modules.cibo,
        functional_modules.portfolio,
        functional_modules.risk,
        *modules.domain_modules(),
    )
    if runtime_context is None:
        boot = bootstrap(configuration, domain_modules=domain_modules)
    else:
        assert clock is not None
        assert event_id_source is not None
        boot = bootstrap(
            configuration,
            runtime_context=runtime_context,
            clock=clock,
            event_id_source=event_id_source,
            domain_modules=domain_modules,
        )
    if isinstance(boot, Failure):
        return Failure(boot.error)

    core = boot.value
    return Success(
        SpecializedGovernanceApplication(
            core=core,
            functional_modules=functional_modules,
            modules=modules,
            functional_decision_flow=CrossModuleDecisionFlow(
                message_bus=core.domain.message_bus,
            ),
            decision_flow=SpecializedServicesDecisionFlow(
                message_bus=core.domain.message_bus,
            ),
        )
    )
