from __future__ import annotations

from dataclasses import dataclass

from qore.core.application import CoreApplication
from qore.core.bootstrap import bootstrap
from qore.core.configuration import Configuration
from qore.core.lifecycle import Clock
from qore.core.runtime import RuntimeContext
from qore.governance.decision_flow import CrossModuleDecisionFlow
from qore.kernel.errors import KernelError, ValidationError
from qore.kernel.result import Failure, Result, Success
from qore.modules.cibo.module import CiboModule
from qore.modules.cio.module import CioModule
from qore.modules.portfolio.module import PortfolioModule
from qore.modules.risk.module import RiskModule


@dataclass(frozen=True, slots=True)
class FunctionalModules:
    """Conjunto oficial e inmutable de módulos funcionales PHASE-04."""

    cio: CioModule
    cibo: CiboModule
    portfolio: PortfolioModule
    risk: RiskModule

    @classmethod
    def create(cls) -> FunctionalModules:
        """Construir una composición funcional nueva y aislada."""
        return cls(
            cio=CioModule(),
            cibo=CiboModule(),
            portfolio=PortfolioModule(),
            risk=RiskModule(),
        )


@dataclass(frozen=True, slots=True)
class FunctionalGovernanceApplication:
    """Root Object funcional construido sobre el Core oficial."""

    core: CoreApplication
    modules: FunctionalModules
    decision_flow: CrossModuleDecisionFlow


def compose_functional_governance(
    configuration: Configuration,
    *,
    runtime_context: RuntimeContext | None = None,
    clock: Clock | None = None,
) -> Result[FunctionalGovernanceApplication, KernelError]:
    """Componer CIO+CIBO+Portfolio+Risk sobre el bootstrap oficial del Core."""
    if (runtime_context is None) != (clock is None):
        return Failure(
            ValidationError("runtime_context and clock must be provided together")
        )

    modules = FunctionalModules.create()
    domain_modules = (
        modules.cio,
        modules.cibo,
        modules.portfolio,
        modules.risk,
    )
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
        FunctionalGovernanceApplication(
            core=core,
            modules=modules,
            decision_flow=CrossModuleDecisionFlow(
                message_bus=core.domain.message_bus,
            ),
        )
    )
