from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.cibo.contracts import (
    CiboEvidenceStatus,
    CiboFunctionalEvidence,
    CiboFunctionalValidationError,
)
from qore.infrastructure.trader_lab.candidate import TraderLabCandidateBinding
from qore.infrastructure.trader_lab.cibo_functional_receipt import (
    CiboTraderLabExecutionStatus,
    CiboTraderLabFunctionGate,
    TraderLabCiboFunctionPassReceipt,
    build_cibo_function_execution,
    issue_trader_lab_cibo_function_pass,
)
from qore.infrastructure.trader_lab.lifecycle import (
    TraderLabLifecycle,
    TraderLabPromotionRequest,
    apply_trader_lab_promotion,
    start_trader_lab_lifecycle,
)
from qore.infrastructure.trader_lab.stage_evidence import (
    TraderLabStage,
    TraderLabStageEvidenceRecord,
)
from qore.kernel.result import Failure, Success

_NOW = datetime(2026, 8, 9, 12, 0, tzinfo=UTC)

_CandidateFactory = Callable[..., TraderLabCandidateBinding]
_EvidenceFactory = Callable[..., TraderLabStageEvidenceRecord]


def _research_ready(
    candidate: TraderLabCandidateBinding,
    stage_evidence_factory: _EvidenceFactory,
) -> TraderLabLifecycle:
    lifecycle = start_trader_lab_lifecycle(candidate)
    evidence = stage_evidence_factory(
        stage=TraderLabStage.RESEARCH,
        candidate=candidate,
        evidence_suffix=910,
        produced_at=_NOW,
    )
    promoted = apply_trader_lab_promotion(
        lifecycle,
        TraderLabPromotionRequest(
            stage=TraderLabStage.RESEARCH,
            evidence=evidence,
        ),
    )
    assert isinstance(promoted, Success)
    return promoted.value


def _execution(
    candidate: TraderLabCandidateBinding,
    function: CiboTraderLabFunctionGate,
    *,
    status: CiboTraderLabExecutionStatus = CiboTraderLabExecutionStatus.PASS,
    minute: int = 1,
):
    built = build_cibo_function_execution(
        candidate=candidate,
        function=function,
        input_sha256="1" * 64,
        output_sha256="2" * 64,
        executed_at=_NOW + timedelta(minutes=minute),
        status=status,
    )
    assert isinstance(built, Success)
    return built.value


def test_plain_sufficient_still_cannot_be_manufactured() -> None:
    with pytest.raises(CiboFunctionalValidationError):
        CiboFunctionalEvidence(
            status=CiboEvidenceStatus.SUFFICIENT,
            evidence_refs=(),
            as_of=_NOW,
        )


def test_draft_candidate_cannot_receive_cibo_function_pass(
    candidate_factory: _CandidateFactory,
) -> None:
    candidate = candidate_factory()
    lifecycle = start_trader_lab_lifecycle(candidate)
    result = issue_trader_lab_cibo_function_pass(
        lifecycle,
        _execution(
            candidate,
            CiboTraderLabFunctionGate.CF01_FINANCIAL_WORLD_MONITORING,
        ),
        previous_receipt=None,
    )
    assert isinstance(result, Failure)
    assert "RESEARCH PASS" in str(result.error)


def test_failed_execution_cannot_receive_pass(
    candidate_factory: _CandidateFactory,
    stage_evidence_factory: _EvidenceFactory,
) -> None:
    candidate = candidate_factory()
    lifecycle = _research_ready(candidate, stage_evidence_factory)
    result = issue_trader_lab_cibo_function_pass(
        lifecycle,
        _execution(
            candidate,
            CiboTraderLabFunctionGate.CF01_FINANCIAL_WORLD_MONITORING,
            status=CiboTraderLabExecutionStatus.FAIL,
        ),
        previous_receipt=None,
    )
    assert isinstance(result, Failure)
    assert "failed CIBO function execution" in str(result.error)


def test_cf01_pass_is_valid_external_sufficient_evidence(
    candidate_factory: _CandidateFactory,
    stage_evidence_factory: _EvidenceFactory,
) -> None:
    candidate = candidate_factory()
    lifecycle = _research_ready(candidate, stage_evidence_factory)
    issued = issue_trader_lab_cibo_function_pass(
        lifecycle,
        _execution(
            candidate,
            CiboTraderLabFunctionGate.CF01_FINANCIAL_WORLD_MONITORING,
        ),
        previous_receipt=None,
    )
    assert isinstance(issued, Success)
    receipt = issued.value
    evidence = CiboFunctionalEvidence(
        status=CiboEvidenceStatus.SUFFICIENT,
        evidence_refs=(receipt.evidence_ref,),
        as_of=receipt.approved_at,
        trader_lab_pass_receipts=(receipt,),
    )
    assert evidence.status is CiboEvidenceStatus.SUFFICIENT
    assert evidence.trader_lab_pass_receipts == (receipt,)


def test_function_gate_cannot_skip_previous_pass(
    candidate_factory: _CandidateFactory,
    stage_evidence_factory: _EvidenceFactory,
) -> None:
    candidate = candidate_factory()
    lifecycle = _research_ready(candidate, stage_evidence_factory)
    skipped = issue_trader_lab_cibo_function_pass(
        lifecycle,
        _execution(
            candidate,
            CiboTraderLabFunctionGate.CF02_MARKET_INTELLIGENCE_MESH,
        ),
        previous_receipt=None,
    )
    assert isinstance(skipped, Failure)
    assert "previous Trader Lab PASS" in str(skipped.error)


def test_exact_previous_pass_unlocks_next_function(
    candidate_factory: _CandidateFactory,
    stage_evidence_factory: _EvidenceFactory,
) -> None:
    candidate = candidate_factory()
    lifecycle = _research_ready(candidate, stage_evidence_factory)
    first = issue_trader_lab_cibo_function_pass(
        lifecycle,
        _execution(
            candidate,
            CiboTraderLabFunctionGate.CF01_FINANCIAL_WORLD_MONITORING,
        ),
        previous_receipt=None,
    )
    assert isinstance(first, Success)
    second = issue_trader_lab_cibo_function_pass(
        lifecycle,
        _execution(
            candidate,
            CiboTraderLabFunctionGate.CF02_MARKET_INTELLIGENCE_MESH,
            minute=2,
        ),
        previous_receipt=first.value,
    )
    assert isinstance(second, Success)
    assert second.value.previous_receipt is first.value


def test_previous_pass_from_other_candidate_is_rejected(
    candidate_factory: _CandidateFactory,
    stage_evidence_factory: _EvidenceFactory,
) -> None:
    candidate_a = candidate_factory(candidate_suffix=1)
    candidate_b = candidate_factory(candidate_suffix=2)
    lifecycle_a = _research_ready(candidate_a, stage_evidence_factory)
    lifecycle_b = _research_ready(candidate_b, stage_evidence_factory)
    first_a = issue_trader_lab_cibo_function_pass(
        lifecycle_a,
        _execution(
            candidate_a,
            CiboTraderLabFunctionGate.CF01_FINANCIAL_WORLD_MONITORING,
        ),
        previous_receipt=None,
    )
    assert isinstance(first_a, Success)
    second_b = issue_trader_lab_cibo_function_pass(
        lifecycle_b,
        _execution(
            candidate_b,
            CiboTraderLabFunctionGate.CF02_MARKET_INTELLIGENCE_MESH,
            minute=2,
        ),
        previous_receipt=first_a.value,
    )
    assert isinstance(second_b, Failure)
    assert "same candidate" in str(second_b.error)


def test_receipt_cannot_be_directly_constructed(
    candidate_factory: _CandidateFactory,
    stage_evidence_factory: _EvidenceFactory,
) -> None:
    candidate = candidate_factory()
    lifecycle = _research_ready(candidate, stage_evidence_factory)
    execution = _execution(
        candidate,
        CiboTraderLabFunctionGate.CF01_FINANCIAL_WORLD_MONITORING,
    )
    tail = lifecycle.qualifications[-1]
    with pytest.raises(Exception):
        TraderLabCiboFunctionPassReceipt(
            candidate=candidate,
            function=execution.function,
            execution_sha256=execution.execution_sha256,
            lifecycle_state=lifecycle.state,
            lifecycle_tail_evidence_sha256=tail.evidence.fingerprint.value,
            previous_receipt=None,
            approved_at=execution.executed_at,
            receipt_sha256="3" * 64,
            evidence_ref=pytest.importorskip(
                "qore.infrastructure.cibo_trader_capability_profile"
            ).CiboEvidenceRef("trader-lab:forged"),
        )
