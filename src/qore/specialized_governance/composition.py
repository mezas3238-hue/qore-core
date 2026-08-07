from __future__ import annotations

from dataclasses import dataclass

from qore.core.application import CoreApplication
from qore.core.bootstrap import bootstrap
from qore.core.configuration import Configuration
from qore.core.lifecycle import Clock
from qore.core.runtime import RuntimeContext
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
        """Return the official deterministic module registration order."""
        return (
            self.trader,
            self.validation,
            self.statistics,
            self.knowledge,
            self.optimization,
        )


@dataclass(frozen=True, slots=True)
class SpecializedGovernanceApplication:
    """Specialized-services root object built above the official Core."""

    core: CoreApplication
    modules: SpecializedServiceModules
    decision_flow: SpecializedServicesDecisionFlow


def compose_specialized_governance(
    configuration: Configuration,
    *,
    runtime_context: RuntimeContext | None = None,
    clock: Clock | None = None,
) -> Result[SpecializedGovernanceApplication, KernelError]:
    """Compose all PHASE-05 specialized services through Core bootstrap()."""
    if (runtime_context is None) != (clock is None):
        return Failure(
            ValidationError("runtime_context and clock must be provided together")
        )

    modules = SpecializedServiceModules.create()
    domain_modules = modules.domain_modules()
    if runtime_context is None:
        boot = bootstrap(configuration, domain_modules=domain_modules)
    else:
        assert clock is not None
        boot = bootstrap(
            configuration,
            runtime_context=runtime_context,
            clock=clock,
            domain_modules=domain_modules,
        )
    if isinstance(boot, Failure):
        return Failure(boot.error)

    core = boot.value
    return Success(
        SpecializedGovernanceApplication(
            core=core,
            modules=modules,
            decision_flow=SpecializedServicesDecisionFlow(
                message_bus=core.domain.message_bus,
            ),
        )
    )
