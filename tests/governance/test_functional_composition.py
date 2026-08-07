from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from qore.core.configuration import Configuration
from qore.domain.commands import CommandId
from qore.domain.events import CorrelationId
from qore.domain.modules import ModuleName
from qore.functional.decisions import (
    DecisionId,
    DecisionOutcome,
    DecisionPriority,
    DecisionReason,
    DecisionReasonCode,
    DecisionType,
)
from qore.governance.composition import compose_functional_governance
from qore.governance.decision_flow import CrossModuleDecisionFlowPlan
from qore.kernel.result import Success
from qore.modules.portfolio.contracts import AllocationIntentId, PortfolioTarget
from qore.modules.risk.contracts import RiskPolicy, RiskPolicyId

_TIMESTAMP = datetime(2026, 8, 7, 23, 30, tzinfo=UTC)
_CORRELATION_ID = CorrelationId(UUID("60000000-0000-0000-0000-000000000001"))


def _reason(code: str) -> DecisionReason:
    return DecisionReason(
        code=DecisionReasonCode(code),
        summary=code,
    )


def _plan() -> CrossModuleDecisionFlowPlan:
    return CrossModuleDecisionFlowPlan(
        correlation_id=_CORRELATION_ID,
        timestamp=_TIMESTAMP,
        cio_command_id=CommandId(UUID("60000000-0000-0000-0000-000000000002")),
        cio_decision_id=DecisionId(UUID("60000000-0000-0000-0000-000000000003")),
        cio_decision_type=DecisionType("cio.strategic-direction"),
        cio_priority=DecisionPriority.HIGH,
        cio_reasons=(_reason("cio.approved"),),
        cio_outcome=DecisionOutcome.APPROVED,
        cibo_command_id=CommandId(UUID("60000000-0000-0000-0000-000000000004")),
        cibo_decision_id=DecisionId(UUID("60000000-0000-0000-0000-000000000005")),
        cibo_priority=DecisionPriority.NORMAL,
        cibo_reasons=(_reason("cibo.approved"),),
        cibo_outcome=DecisionOutcome.APPROVED,
        portfolio_command_id=CommandId(
            UUID("60000000-0000-0000-0000-000000000006")
        ),
        allocation_intent_id=AllocationIntentId(
            UUID("60000000-0000-0000-0000-000000000007")
        ),
        portfolio_targets=(
            PortfolioTarget(name="core", weight_bps=7_500),
            PortfolioTarget(name="reserve", weight_bps=2_500),
        ),
        risk_command_id=CommandId(UUID("60000000-0000-0000-0000-000000000008")),
        risk_decision_id=DecisionId(UUID("60000000-0000-0000-0000-000000000009")),
        risk_policy=RiskPolicy(
            policy_id=RiskPolicyId(
                UUID("60000000-0000-0000-0000-000000000010")
            ),
            soft_single_target_limit_bps=7_000,
            hard_single_target_limit_bps=8_000,
        ),
    )


def test_functional_composition_exposes_official_modules_and_flow() -> None:
    composed = compose_functional_governance(
        Configuration(application_name="qore-functional-governance-test")
    )

    assert isinstance(composed, Success)
    application = composed.value
    catalog = application.core.domain.module_catalog

    assert catalog.get(ModuleName("cio")) is application.modules.cio
    assert catalog.get(ModuleName("cibo")) is application.modules.cibo
    assert catalog.get(ModuleName("portfolio")) is application.modules.portfolio
    assert catalog.get(ModuleName("risk")) is application.modules.risk


def test_functional_composition_executes_end_to_end_flow() -> None:
    composed = compose_functional_governance(
        Configuration(application_name="qore-functional-governance-test")
    )
    assert isinstance(composed, Success)

    result = composed.value.decision_flow.execute(_plan())

    assert isinstance(result, Success)
    assert result.value.risk_decision.outcome is DecisionOutcome.DEGRADED
    assert result.value.correlation_id == _CORRELATION_ID


def test_functional_flow_does_not_mutate_runtime_state_or_health() -> None:
    composed = compose_functional_governance(
        Configuration(application_name="qore-functional-governance-test")
    )
    assert isinstance(composed, Success)
    core = composed.value.core
    before_snapshot = core.runtime_snapshot()
    before_health = core.runtime_health()

    result = composed.value.decision_flow.execute(_plan())

    assert isinstance(result, Success)
    assert core.runtime_snapshot() == before_snapshot
    assert core.runtime_health() == before_health
    assert len(core.runtime_plan.components) == 1
    assert core.runtime_plan.components[0].component is core.engine


def test_functional_compositions_do_not_share_module_instances() -> None:
    first = compose_functional_governance(
        Configuration(application_name="qore-functional-governance-a")
    )
    second = compose_functional_governance(
        Configuration(application_name="qore-functional-governance-b")
    )

    assert isinstance(first, Success)
    assert isinstance(second, Success)
    assert first.value.modules.cio is not second.value.modules.cio
    assert first.value.modules.cibo is not second.value.modules.cibo
    assert first.value.modules.portfolio is not second.value.modules.portfolio
    assert first.value.modules.risk is not second.value.modules.risk
    assert first.value.core.domain.handler_registry is not second.value.core.domain.handler_registry
