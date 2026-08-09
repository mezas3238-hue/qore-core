from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID

import pytest

from qore.domain.events import CorrelationId
from qore.governance.cibo_executive_dialogue import (
    CiboExecutiveAnswer,
    CiboExecutiveDialogueTurnId,
    CiboExecutiveDialogueValidationError,
    CiboExecutiveJudgmentState,
    CiboExecutivePromptRef,
    CiboExecutiveQuestion,
    build_cibo_executive_answer,
)
from qore.governance.executive_control import ExecutivePrincipalId, ExecutiveReadScope
from qore.governance.executive_ports import ExecutiveEvidenceRef
from qore.kernel.result import Failure, Success

_NOW = datetime(2026, 8, 9, 13, 0, tzinfo=UTC)
_PRINCIPAL = ExecutivePrincipalId("ceo.primary")
_CORRELATION = CorrelationId(UUID("56000000-0000-0000-0000-000000000001"))


def _question() -> CiboExecutiveQuestion:
    return CiboExecutiveQuestion(
        turn_id=CiboExecutiveDialogueTurnId(
            UUID("56000000-0000-0000-0000-000000000002")
        ),
        principal_id=_PRINCIPAL,
        prompt_ref=CiboExecutivePromptRef("prompt:risk-review"),
        requested_scope=ExecutiveReadScope.RISK,
        asked_at=_NOW,
        correlation_id=_CORRELATION,
    )


def test_answer_is_evidence_backed_structured_and_deterministic() -> None:
    result = build_cibo_executive_answer(
        _question(),
        judgment_state=CiboExecutiveJudgmentState.CONCERNED,
        summary_code="risk.restricted",
        reason_codes=("portfolio.correlation", "risk.limit"),
        evidence_refs=(
            ExecutiveEvidenceRef("audit:risk/002"),
            ExecutiveEvidenceRef("audit:risk/001"),
        ),
        answered_at=_NOW + timedelta(seconds=1),
        navigation_scope=ExecutiveReadScope.RISK,
    )

    assert isinstance(result, Success)
    answer = result.value
    assert answer.reason_codes == ("portfolio.correlation", "risk.limit")
    assert tuple(item.value for item in answer.evidence_refs) == (
        "audit:risk/001",
        "audit:risk/002",
    )
    assert answer.logical_values() == answer.logical_values()
    assert not hasattr(answer, "chain_of_thought")
    assert not hasattr(answer, "hidden_reasoning")
    with pytest.raises(FrozenInstanceError):
        answer.__setattr__("summary_code", "changed")


def test_answer_requires_nonempty_reasons_and_evidence() -> None:
    no_reasons = build_cibo_executive_answer(
        _question(),
        judgment_state=CiboExecutiveJudgmentState.CAUTIOUS,
        summary_code="market.uncertain",
        reason_codes=(),
        evidence_refs=(ExecutiveEvidenceRef("audit:market/001"),),
        answered_at=_NOW + timedelta(seconds=1),
    )
    no_evidence = build_cibo_executive_answer(
        _question(),
        judgment_state=CiboExecutiveJudgmentState.CAUTIOUS,
        summary_code="market.uncertain",
        reason_codes=("market.regime",),
        evidence_refs=(),
        answered_at=_NOW + timedelta(seconds=1),
    )

    assert isinstance(no_reasons, Failure)
    assert isinstance(no_evidence, Failure)


def test_raw_prompt_text_is_not_part_of_question_contract() -> None:
    question = _question()
    assert hasattr(question, "prompt_ref")
    assert not hasattr(question, "prompt")
    assert not hasattr(question, "text")
    assert not hasattr(question, "token")
    assert not hasattr(question, "credentials")


def test_dialogue_exposes_no_trade_or_command_authority() -> None:
    result = build_cibo_executive_answer(
        _question(),
        judgment_state=CiboExecutiveJudgmentState.CRITICAL,
        summary_code="risk.blocked",
        reason_codes=("risk.blocked",),
        evidence_refs=(ExecutiveEvidenceRef("audit:risk/003"),),
        answered_at=_NOW + timedelta(seconds=1),
    )
    assert isinstance(result, Success)
    for name in ("execute", "submit_order", "force_buy", "force_sell", "dispatch"):
        assert not hasattr(result.value, name)


def test_answer_cannot_predate_question() -> None:
    result = build_cibo_executive_answer(
        _question(),
        judgment_state=CiboExecutiveJudgmentState.UNCERTAIN,
        summary_code="evidence.insufficient",
        reason_codes=("evidence.insufficient",),
        evidence_refs=(ExecutiveEvidenceRef("audit:evidence/001"),),
        answered_at=_NOW - timedelta(microseconds=1),
    )
    assert isinstance(result, Failure)


def test_prompt_ref_and_types_fail_closed_without_coercion() -> None:
    with pytest.raises(CiboExecutiveDialogueValidationError):
        CiboExecutivePromptRef("Raw Prompt")
    with pytest.raises(CiboExecutiveDialogueValidationError):
        CiboExecutiveDialogueTurnId(cast(UUID, "turn"))
    result = build_cibo_executive_answer(
        cast(CiboExecutiveQuestion, object()),
        judgment_state=CiboExecutiveJudgmentState.CONFIDENT,
        summary_code="system.healthy",
        reason_codes=("system.healthy",),
        evidence_refs=(ExecutiveEvidenceRef("audit:system/001"),),
        answered_at=_NOW,
    )
    assert isinstance(result, Failure)


def test_direct_answer_rejects_invalid_navigation_scope() -> None:
    with pytest.raises(CiboExecutiveDialogueValidationError):
        CiboExecutiveAnswer(
            question=_question(),
            judgment_state=CiboExecutiveJudgmentState.CONFIDENT,
            summary_code="system.healthy",
            reason_codes=("system.healthy",),
            evidence_refs=(ExecutiveEvidenceRef("audit:system/002"),),
            answered_at=_NOW + timedelta(seconds=1),
            navigation_scope=cast(ExecutiveReadScope, "orders"),
        )
