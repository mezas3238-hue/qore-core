from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest

from qore.core.bootstrap import bootstrap
from qore.core.configuration import Configuration
from qore.domain.commands import CommandId
from qore.domain.events import CausationId, CorrelationId
from qore.domain.message_bus import CommandHandlerNotFoundError
from qore.functional.decisions import (
    DecisionId,
    DecisionOutcome,
    DecisionPriority,
    DecisionReason,
    DecisionReasonCode,
    DecisionType,
)
from qore.governance.decision_flow import (
    CrossModuleDecisionFlow,
    CrossModuleDecisionFlowPlan,
    GovernanceValidationError,
)
from qore.kernel.result import Failure, Success
from qore.modules.cibo.module import CiboModule
from qore.modules.cio.module import CioModule
from qore.modules.portfolio.contracts import AllocationIntentId, PortfolioTarget
from qore.modules.portfolio.module import PortfolioModule
from qore.modules.risk.contracts import RiskPolicy, RiskPolicyId
from qore.modules.risk.module import RiskModule

_TIMESTAMP = datetime(2026, 8, 7, 23, 0, tzinfo=UTC)
_CORRELATION_ID = CorrelationId(UUID("50000000-0000-0000-0000-000000000001"))
_CIO_COMMAND_ID = CommandId(UUID("50000000-0000-0000-0000-000000000002"))
_CIO_DECISION_ID = DecisionId(UUID("50000000-0000-0000-0000-000000000003"))
_CIBO_COMMAND_ID = CommandId(UUID("50000000-0000-0000-0000-000000000004"))
_CIBO_DECISION_ID = DecisionId(UUID("50000000-0000-0000-0000-000000000005"))
_PORTFOLIO_COMMAND_ID = CommandId(UUID("50000000-0000-0000-0000-000000000006"))
_INTENT_ID = AllocationIntentId(UUID("50000000-0000-0000-0000-000000000007"))
_RISK_COMMAND_ID = CommandId(UUID("50000000-0000-0000-0000-000000000008"))
_RISK_DECISION_ID = DecisionId(UUID("50000000-0000-0000-0000-000000000009"))
_POLICY_ID = RiskPolicyId(UUID("50000000-0000-0000-0000-000000000010"))


def _reason(code: str, summary: str) -> DecisionReason:
    return DecisionReason(code=DecisionReasonCode(code), summary=summary)


def _plan(peak_weight_bps: int) -> CrossModuleDecisionFlowPlan:
    return CrossModuleDecisionFlowPlan(
        correlation_id=_CORRELATION_ID,
        timestamp=_TIMESTAMP,
        cio_command_id=_CIO_COMMAND_ID,
        cio_decision_id=_CIO_DECISION_ID,
        cio_decision_type=DecisionType("cio.strategic-direction"),
        cio_priority=DecisionPriority.HIGH,
        cio_reasons=(
            _reason("cio.strategy-approved", "Strategic direction approved"),
        ),
        cio_outcome=DecisionOutcome.APPROVED,
        cibo_command_id=_CIBO_COMMAND_ID,
        cibo_decision_id=_CIBO_DECISION_ID,
        cibo_priority=DecisionPriority.NORMAL,
        cibo_reasons=(
            _reason("cibo.business-approved", "Business review approved"),
        ),
        cibo_outcome=DecisionOutcome.APPROVED,
        portfolio_command_id=_PORTFOLIO_COMMAND_ID,
        allocation_intent_id=_INTENT_ID,
        portfolio_targets=(
            PortfolioTarget(name="core", weight_bps=peak_weight_bps),
            PortfolioTarget(name="reserve", weight_bps=10_000 - peak_weight_bps),
        ),
        risk_command_id=_RISK_COMMAND_ID,
        risk_decision_id=_RISK_DECISION_ID,
        risk_policy=RiskPolicy(
            policy_id=_POLICY_ID,
            soft_single_target_limit_bps=7_000,
            hard_single_target_limit_bps=8_000,
        ),
    )


def _boot_full():
    return bootstrap(
        Configuration(application_name="qore-governance-flow-test"),
        domain_modules=(CioModule(), CiboModule(), PortfolioModule(), RiskModule()),
    )


@pytest.mark.parametrize(
    ("peak_weight_bps", "expected"),
    [
        (7_000, DecisionOutcome.APPROVED),
        (7_500, DecisionOutcome.DEGRADED),
        (8_001, DecisionOutcome.BLOCKED),
    ],
)
def test_cross_module_flow_reaches_risk_outcome(
    peak_weight_bps: int,
    expected: DecisionOutcome,
) -> None:
    boot = _boot_full()
    assert isinstance(boot, Success)

    result = CrossModuleDecisionFlow(
        message_bus=boot.value.domain.message_bus
    ).execute(_plan(peak_weight_bps))

    assert isinstance(result, Success)
    snapshot = result.value
    assert snapshot.risk_decision.outcome is expected
    assert snapshot.cio_decision.metadata.correlation_id == _CORRELATION_ID
    assert snapshot.cibo_decision.metadata.correlation_id == _CORRELATION_ID
    assert snapshot.allocation_intent.correlation_id == _CORRELATION_ID
    assert snapshot.risk_decision.metadata.correlation_id == _CORRELATION_ID
    assert snapshot.cibo_decision.metadata.causation_id == CausationId(
        _CIO_DECISION_ID.value
    )
    assert snapshot.allocation_intent.source_decision_id == _CIBO_DECISION_ID
    assert snapshot.risk_decision.metadata.causation_id == CausationId(_INTENT_ID.value)


def test_cross_module_flow_is_deterministic() -> None:
    boot = _boot_full()
    assert isinstance(boot, Success)
    flow = CrossModuleDecisionFlow(message_bus=boot.value.domain.message_bus)
    plan = _plan(7_500)

    first = flow.execute(plan)
    second = flow.execute(plan)

    assert isinstance(first, Success)
    assert isinstance(second, Success)
    assert first.value.logical_values() == second.value.logical_values()


def test_plan_rejects_non_approved_intermediate_governance() -> None:
    plan = _plan(7_000)

    with pytest.raises(GovernanceValidationError, match="approved CIBO"):
        CrossModuleDecisionFlowPlan(
            correlation_id=plan.correlation_id,
            timestamp=plan.timestamp,
            cio_command_id=plan.cio_command_id,
            cio_decision_id=plan.cio_decision_id,
            cio_decision_type=plan.cio_decision_type,
            cio_priority=plan.cio_priority,
            cio_reasons=plan.cio_reasons,
            cio_outcome=plan.cio_outcome,
            cibo_command_id=plan.cibo_command_id,
            cibo_decision_id=plan.cibo_decision_id,
            cibo_priority=plan.cibo_priority,
            cibo_reasons=plan.cibo_reasons,
            cibo_outcome=DecisionOutcome.BLOCKED,
            portfolio_command_id=plan.portfolio_command_id,
            allocation_intent_id=plan.allocation_intent_id,
            portfolio_targets=plan.portfolio_targets,
            risk_command_id=plan.risk_command_id,
            risk_decision_id=plan.risk_decision_id,
            risk_policy=plan.risk_policy,
        )


def test_plan_rejects_duplicate_causal_object_identity() -> None:
    plan = _plan(7_000)

    with pytest.raises(GovernanceValidationError, match="identities must be unique"):
        CrossModuleDecisionFlowPlan(
            correlation_id=plan.correlation_id,
            timestamp=plan.timestamp,
            cio_command_id=plan.cio_command_id,
            cio_decision_id=plan.cio_decision_id,
            cio_decision_type=plan.cio_decision_type,
            cio_priority=plan.cio_priority,
            cio_reasons=plan.cio_reasons,
            cio_outcome=plan.cio_outcome,
            cibo_command_id=plan.cibo_command_id,
            cibo_decision_id=DecisionId(plan.cio_decision_id.value),
            cibo_priority=plan.cibo_priority,
            cibo_reasons=plan.cibo_reasons,
            cibo_outcome=plan.cibo_outcome,
            portfolio_command_id=plan.portfolio_command_id,
            allocation_intent_id=plan.allocation_intent_id,
            portfolio_targets=plan.portfolio_targets,
            risk_command_id=plan.risk_command_id,
            risk_decision_id=plan.risk_decision_id,
            risk_policy=plan.risk_policy,
        )


def test_flow_propagates_missing_stage_handler_failure() -> None:
    boot = bootstrap(
        Configuration(application_name="qore-governance-flow-test"),
        domain_modules=(CioModule(), CiboModule(), PortfolioModule()),
    )
    assert isinstance(boot, Success)

    result = CrossModuleDecisionFlow(
        message_bus=boot.value.domain.message_bus
    ).execute(_plan(7_000))

    assert isinstance(result, Failure)
    assert isinstance(result.error, CommandHandlerNotFoundError)


def test_governance_flow_does_not_change_runtime_plan() -> None:
    boot = _boot_full()
    assert isinstance(boot, Success)

    assert len(boot.value.runtime_plan.components) == 1
    assert boot.value.runtime_plan.components[0].component is boot.value.engine
