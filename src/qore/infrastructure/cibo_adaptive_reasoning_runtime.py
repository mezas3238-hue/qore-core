from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from re import fullmatch
from typing import Protocol
from uuid import UUID

from qore.infrastructure.cibo_executive_brain import CiboExecutiveBrain
from qore.infrastructure.cibo_reasoning_policy import CiboReasoningRoute
from qore.infrastructure.cibo_reasoning_runtime import (
    CiboReasoningProposal,
    CiboReasoningRequest,
    CiboReasoningRuntime,
    CiboReasoningRuntimeError,
    CiboReasoningRuntimeResult,
    CiboReasoningRuntimeValidationError,
)
from qore.kernel.result import Failure, Result, Success

_DIGEST_RE = r"sha256:[0-9a-f]{64}"
_CODE_RE = r"[a-z][a-z0-9._-]*"


def _digest_json(value: object) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return f"sha256:{sha256(encoded).hexdigest()}"


def cibo_reasoning_request_digest(request: CiboReasoningRequest) -> str:
    """Canonical digest of the exact admitted CIBO reasoning request."""
    if type(request) is not CiboReasoningRequest:
        raise CiboReasoningRuntimeValidationError(
            "request digest requires exact CiboReasoningRequest"
        )
    CiboReasoningRequest.__post_init__(request)
    return _digest_json(
        {
            "request_id": str(request.request_id),
            "subject_code": request.subject_code,
            "asked_at": request.asked_at.isoformat(),
            "prompt": request.prompt,
            "evidence_refs": [item.value for item in request.evidence_refs],
            "observations": list(request.observations),
            "memory_refs": [str(item) for item in request.memory_refs],
        }
    )


def cibo_reasoning_proposal_digest(proposal: CiboReasoningProposal) -> str:
    """Canonical digest of the exact authority-free proposal admitted by QORE."""
    if type(proposal) is not CiboReasoningProposal:
        raise CiboReasoningRuntimeValidationError(
            "proposal digest requires exact CiboReasoningProposal"
        )
    CiboReasoningProposal.__post_init__(proposal)
    return _digest_json(proposal.logical_values())


def _validate_digest(value: str, *, field_name: str) -> None:
    if type(value) is not str or fullmatch(_DIGEST_RE, value) is None:
        raise CiboReasoningRuntimeValidationError(
            f"{field_name} must be a canonical sha256 digest"
        )


def _validate_code(value: str, *, field_name: str) -> None:
    if type(value) is not str or fullmatch(_CODE_RE, value) is None:
        raise CiboReasoningRuntimeValidationError(
            f"{field_name} must use canonical lowercase code syntax"
        )


def _validate_aware_datetime(value: datetime, *, field_name: str) -> None:
    if type(value) is not datetime:
        raise CiboReasoningRuntimeValidationError(f"{field_name} must be datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise CiboReasoningRuntimeValidationError(
            f"{field_name} must be timezone-aware"
        )


@dataclass(frozen=True, slots=True)
class CiboReasoningProviderEvidence:
    """Provider-call evidence before the runtime binds completion timestamps."""

    route: CiboReasoningRoute
    provider_code: str
    engine_code: str
    request_digest: str
    request_payload_digest: str
    response_digest: str
    configuration_fingerprint: str
    schema_fingerprint: str
    provider_response_ref: str
    admitted_proposal_digest: str

    def __post_init__(self) -> None:
        if type(self.route) is not CiboReasoningRoute:
            raise CiboReasoningRuntimeValidationError(
                "provider evidence route must be exact CiboReasoningRoute"
            )
        self.route.__post_init__()
        _validate_code(self.provider_code, field_name="provider_code")
        _validate_code(self.engine_code, field_name="engine_code")
        for field_name in (
            "request_digest",
            "request_payload_digest",
            "response_digest",
            "configuration_fingerprint",
            "schema_fingerprint",
            "admitted_proposal_digest",
        ):
            _validate_digest(getattr(self, field_name), field_name=field_name)
        if type(self.provider_response_ref) is not str or not self.provider_response_ref:
            raise CiboReasoningRuntimeValidationError(
                "provider_response_ref must be non-empty exact str"
            )
        if any(ch in self.provider_response_ref for ch in "\x00\n\r\t"):
            raise CiboReasoningRuntimeValidationError(
                "provider_response_ref must not contain control characters"
            )


@dataclass(frozen=True, slots=True)
class CiboReasoningEngineAdmission:
    """One provider proposal paired with immutable provenance evidence."""

    proposal: CiboReasoningProposal
    provider_evidence: CiboReasoningProviderEvidence

    def __post_init__(self) -> None:
        if type(self.proposal) is not CiboReasoningProposal:
            raise CiboReasoningRuntimeValidationError(
                "engine admission proposal must be exact CiboReasoningProposal"
            )
        CiboReasoningProposal.__post_init__(self.proposal)
        if type(self.provider_evidence) is not CiboReasoningProviderEvidence:
            raise CiboReasoningRuntimeValidationError(
                "engine admission provider_evidence must be exact"
            )
        self.provider_evidence.__post_init__()
        if (
            self.provider_evidence.admitted_proposal_digest
            != cibo_reasoning_proposal_digest(self.proposal)
        ):
            raise CiboReasoningRuntimeValidationError(
                "provider evidence proposal digest did not bind admitted proposal"
            )


class CiboRoutedReasoningEngine(Protocol):
    """External engine that returns proposal plus auditable provider evidence."""

    def reason_with_evidence(
        self,
        request: CiboReasoningRequest,
    ) -> Result[CiboReasoningEngineAdmission, CiboReasoningRuntimeError]:
        """Produce one governed admission without formal Risk/execution authority."""
        ...


@dataclass(frozen=True, slots=True)
class CiboReasoningEngineReceipt:
    """Immutable receipt proving the exact external reasoning call admitted by QORE."""

    route: CiboReasoningRoute
    provider_code: str
    engine_code: str
    request_digest: str
    request_payload_digest: str
    response_digest: str
    configuration_fingerprint: str
    schema_fingerprint: str
    provider_response_ref: str
    admitted_proposal_digest: str
    started_at: datetime
    completed_at: datetime

    def __post_init__(self) -> None:
        CiboReasoningProviderEvidence(
            route=self.route,
            provider_code=self.provider_code,
            engine_code=self.engine_code,
            request_digest=self.request_digest,
            request_payload_digest=self.request_payload_digest,
            response_digest=self.response_digest,
            configuration_fingerprint=self.configuration_fingerprint,
            schema_fingerprint=self.schema_fingerprint,
            provider_response_ref=self.provider_response_ref,
            admitted_proposal_digest=self.admitted_proposal_digest,
        )
        _validate_aware_datetime(self.started_at, field_name="started_at")
        _validate_aware_datetime(self.completed_at, field_name="completed_at")
        if self.completed_at < self.started_at:
            raise CiboReasoningRuntimeValidationError(
                "reasoning receipt completed_at must not predate started_at"
            )


@dataclass(frozen=True, slots=True)
class CiboReasoningReplayRecord:
    """Retained admitted proposal + receipt used for provider-free historical replay."""

    request_id: UUID
    proposal: CiboReasoningProposal
    receipt: CiboReasoningEngineReceipt

    def __post_init__(self) -> None:
        if type(self.request_id) is not UUID:
            raise CiboReasoningRuntimeValidationError("replay request_id must be UUID")
        if type(self.proposal) is not CiboReasoningProposal:
            raise CiboReasoningRuntimeValidationError(
                "replay proposal must be exact CiboReasoningProposal"
            )
        CiboReasoningProposal.__post_init__(self.proposal)
        if type(self.receipt) is not CiboReasoningEngineReceipt:
            raise CiboReasoningRuntimeValidationError(
                "replay receipt must be exact CiboReasoningEngineReceipt"
            )
        self.receipt.__post_init__()
        if self.receipt.admitted_proposal_digest != cibo_reasoning_proposal_digest(
            self.proposal
        ):
            raise CiboReasoningRuntimeValidationError(
                "replay receipt does not bind retained admitted proposal"
            )


@dataclass(frozen=True, slots=True)
class CiboAdaptiveReasoningRuntimeResult:
    """Validated CIBO synthesis plus immutable route/receipt/replay provenance."""

    runtime_result: CiboReasoningRuntimeResult
    route: CiboReasoningRoute
    receipt: CiboReasoningEngineReceipt
    replay_record: CiboReasoningReplayRecord

    def __post_init__(self) -> None:
        if type(self.runtime_result) is not CiboReasoningRuntimeResult:
            raise CiboReasoningRuntimeValidationError(
                "adaptive runtime_result must be exact CiboReasoningRuntimeResult"
            )
        CiboReasoningRuntimeResult.__post_init__(self.runtime_result)
        if type(self.route) is not CiboReasoningRoute:
            raise CiboReasoningRuntimeValidationError(
                "adaptive route must be exact CiboReasoningRoute"
            )
        self.route.__post_init__()
        if type(self.receipt) is not CiboReasoningEngineReceipt:
            raise CiboReasoningRuntimeValidationError(
                "adaptive receipt must be exact CiboReasoningEngineReceipt"
            )
        self.receipt.__post_init__()
        if type(self.replay_record) is not CiboReasoningReplayRecord:
            raise CiboReasoningRuntimeValidationError(
                "adaptive replay_record must be exact CiboReasoningReplayRecord"
            )
        self.replay_record.__post_init__()
        if self.receipt.route != self.route:
            raise CiboReasoningRuntimeValidationError(
                "adaptive receipt route must match selected route"
            )


@dataclass(frozen=True, slots=True)
class _AdmittedProposalEngine:
    proposal: CiboReasoningProposal

    def reason(
        self,
        request: CiboReasoningRequest,
    ) -> Result[CiboReasoningProposal, CiboReasoningRuntimeError]:
        if type(request) is not CiboReasoningRequest:
            return Failure(
                CiboReasoningRuntimeValidationError(
                    "replay engine requires exact CiboReasoningRequest"
                )
            )
        return Success(self.proposal)


@dataclass(frozen=True, slots=True)
class CiboAdaptiveReasoningRuntime:
    """Governed route-aware runtime with immutable provider provenance and replay."""

    engine: CiboRoutedReasoningEngine
    route: CiboReasoningRoute
    brain: CiboExecutiveBrain = CiboExecutiveBrain()

    def run(
        self,
        request: CiboReasoningRequest,
        *,
        synthesized_at: datetime,
    ) -> Result[CiboAdaptiveReasoningRuntimeResult, CiboReasoningRuntimeError]:
        if type(request) is not CiboReasoningRequest:
            return Failure(
                CiboReasoningRuntimeValidationError(
                    "adaptive runtime requires exact CiboReasoningRequest"
                )
            )
        try:
            CiboReasoningRequest.__post_init__(request)
            if type(self.route) is not CiboReasoningRoute:
                raise CiboReasoningRuntimeValidationError(
                    "adaptive runtime route must be exact CiboReasoningRoute"
                )
            self.route.__post_init__()
            _validate_aware_datetime(synthesized_at, field_name="synthesized_at")
            if synthesized_at < request.asked_at:
                raise CiboReasoningRuntimeValidationError(
                    "synthesized_at must not predate request asked_at"
                )
        except CiboReasoningRuntimeError as error:
            return Failure(error)

        admitted = self.engine.reason_with_evidence(request)
        if isinstance(admitted, Failure):
            return admitted
        admission = admitted.value
        if type(admission) is not CiboReasoningEngineAdmission:
            return Failure(
                CiboReasoningRuntimeValidationError(
                    "routed engine returned invalid admission type"
                )
            )
        try:
            admission.__post_init__()
            evidence = admission.provider_evidence
            if evidence.route != self.route:
                raise CiboReasoningRuntimeValidationError(
                    "provider evidence route did not match governed selected route"
                )
            request_digest = cibo_reasoning_request_digest(request)
            if evidence.request_digest != request_digest:
                raise CiboReasoningRuntimeValidationError(
                    "provider evidence request digest did not bind exact request"
                )
            receipt = CiboReasoningEngineReceipt(
                route=self.route,
                provider_code=evidence.provider_code,
                engine_code=evidence.engine_code,
                request_digest=evidence.request_digest,
                request_payload_digest=evidence.request_payload_digest,
                response_digest=evidence.response_digest,
                configuration_fingerprint=evidence.configuration_fingerprint,
                schema_fingerprint=evidence.schema_fingerprint,
                provider_response_ref=evidence.provider_response_ref,
                admitted_proposal_digest=evidence.admitted_proposal_digest,
                started_at=request.asked_at,
                completed_at=synthesized_at,
            )
        except CiboReasoningRuntimeError as error:
            return Failure(error)

        translated = CiboReasoningRuntime(
            engine=_AdmittedProposalEngine(admission.proposal),
            brain=self.brain,
        ).run(request, synthesized_at=synthesized_at)
        if isinstance(translated, Failure):
            return translated

        try:
            replay_record = CiboReasoningReplayRecord(
                request_id=request.request_id,
                proposal=admission.proposal,
                receipt=receipt,
            )
            return Success(
                CiboAdaptiveReasoningRuntimeResult(
                    runtime_result=translated.value,
                    route=self.route,
                    receipt=receipt,
                    replay_record=replay_record,
                )
            )
        except CiboReasoningRuntimeError as error:
            return Failure(error)

    @staticmethod
    def replay(
        request: CiboReasoningRequest,
        replay_record: CiboReasoningReplayRecord,
        *,
        brain: CiboExecutiveBrain = CiboExecutiveBrain(),
    ) -> Result[CiboReasoningRuntimeResult, CiboReasoningRuntimeError]:
        """Replay retained admitted output without any provider/model invocation."""
        if type(request) is not CiboReasoningRequest:
            return Failure(
                CiboReasoningRuntimeValidationError(
                    "replay requires exact CiboReasoningRequest"
                )
            )
        if type(replay_record) is not CiboReasoningReplayRecord:
            return Failure(
                CiboReasoningRuntimeValidationError(
                    "replay requires exact CiboReasoningReplayRecord"
                )
            )
        try:
            CiboReasoningRequest.__post_init__(request)
            replay_record.__post_init__()
            if replay_record.request_id != request.request_id:
                raise CiboReasoningRuntimeValidationError(
                    "replay record request_id did not match request"
                )
            if replay_record.receipt.request_digest != cibo_reasoning_request_digest(
                request
            ):
                raise CiboReasoningRuntimeValidationError(
                    "replay record request digest did not match request"
                )
        except CiboReasoningRuntimeError as error:
            return Failure(error)

        return CiboReasoningRuntime(
            engine=_AdmittedProposalEngine(replay_record.proposal),
            brain=brain,
        ).run(
            request,
            synthesized_at=replay_record.receipt.completed_at,
        )
