from __future__ import annotations

import json
from dataclasses import dataclass
from typing import cast

from qore.infrastructure.cibo_executive_brain import CiboExecutiveDirectiveKind
from qore.infrastructure.cibo_reasoning_runtime import (
    CiboReasoningProposal,
    CiboReasoningRequest,
    CiboReasoningRuntimeError,
    CiboReasoningRuntimeValidationError,
)
from qore.infrastructure.openai_cibo_reasoning_engine import (
    OpenAICiboReasoningError,
    OpenAICiboReasoningUnavailableError,
    OpenAICiboReasoningValidationError,
    OpenAIResponsesTransportBoundary,
)
from qore.infrastructure.secret_resolution import SecretMaterial
from qore.kernel.result import Failure, Result, Success
from qore.modules.cibo.cognitive_contracts import (
    CiboCognitiveEvidenceRef,
    CiboCognitiveValidationError,
    CiboConfidenceLevel,
    CiboReasoningMode,
    CiboUncertaintyKind,
)

_MODEL = "gpt-5.6-sol"


def provider_reasoning_effort_for_mode(mode: CiboReasoningMode) -> str:
    """Map CIBO semantic depth to the concrete GPT-5.6 Sol effort setting."""
    if type(mode) is not CiboReasoningMode:
        raise OpenAICiboReasoningValidationError(
            "reasoning mode must be exact CiboReasoningMode"
        )
    if mode is CiboReasoningMode.FAST:
        return "low"
    if mode is CiboReasoningMode.HIGH:
        return "high"
    if mode in (CiboReasoningMode.MAX, CiboReasoningMode.COUNCIL_ADVERSARIAL):
        return "max"
    raise OpenAICiboReasoningValidationError("unsupported CIBO reasoning mode")


@dataclass(frozen=True, slots=True)
class OpenAICiboAdaptiveReasoningConfiguration:
    """GPT-5.6 Sol configuration with HIGH default and governed escalation."""

    semantic_mode: CiboReasoningMode = CiboReasoningMode.HIGH
    model: str = _MODEL
    timeout_seconds: float = 90.0
    max_output_tokens: int = 2500

    def __post_init__(self) -> None:
        if type(self.semantic_mode) is not CiboReasoningMode:
            raise OpenAICiboReasoningValidationError(
                "semantic_mode must be exact CiboReasoningMode"
            )
        if type(self.model) is not str or self.model != _MODEL:
            raise OpenAICiboReasoningValidationError(
                "adaptive CIBO reasoning model must be exactly gpt-5.6-sol"
            )
        if type(self.timeout_seconds) is not float or self.timeout_seconds <= 0:
            raise OpenAICiboReasoningValidationError(
                "OpenAI timeout_seconds must be a positive float"
            )
        if (
            type(self.max_output_tokens) is not int
            or self.max_output_tokens < 256
            or self.max_output_tokens > 16000
        ):
            raise OpenAICiboReasoningValidationError(
                "OpenAI max_output_tokens must be an int in [256, 16000]"
            )
        provider_reasoning_effort_for_mode(self.semantic_mode)

    @property
    def provider_reasoning_effort(self) -> str:
        return provider_reasoning_effort_for_mode(self.semantic_mode)


def _proposal_schema(mode: CiboReasoningMode) -> dict[str, object]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "directive": {
                "type": "string",
                "enum": [
                    "recommend",
                    "question",
                    "defer",
                    "request-evidence",
                    "request-research",
                    "abstain",
                ],
            },
            "reasoning_mode": {"type": "string", "enum": [mode.value]},
            "uncertainty_kind": {
                "type": "string",
                "enum": [
                    "insufficient-evidence",
                    "unresolved-contradiction",
                    "competing-hypotheses",
                    "more-evidence-requested",
                    "abstain-defer",
                    "bounded-confidence",
                ],
            },
            "confidence_level": {"enum": ["low", "medium", "high", None]},
            "used_evidence_refs": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 1,
                "uniqueItems": True,
            },
            "response_text": {
                "type": "string",
                "minLength": 1,
                "maxLength": 4000,
            },
            "recommendation_code": {"type": ["string", "null"]},
            "questions": {
                "type": "array",
                "items": {"type": "string"},
                "uniqueItems": True,
            },
            "request_code": {"type": ["string", "null"]},
            "limitations": {
                "type": "array",
                "items": {"type": "string"},
                "uniqueItems": True,
            },
        },
        "required": [
            "directive",
            "reasoning_mode",
            "uncertainty_kind",
            "confidence_level",
            "used_evidence_refs",
            "response_text",
            "recommendation_code",
            "questions",
            "request_code",
            "limitations",
        ],
    }


def _system_instructions(mode: CiboReasoningMode) -> str:
    return (
        "You are the external reasoning motor for CIBO inside QORE Core. "
        "Return only the requested structured JSON object. Never expose chain-of-thought. "
        "Provide one concise decision explanation in response_text, not hidden reasoning. "
        "Use only evidence reference strings supplied in the input; never invent evidence. "
        "CIBO intelligence is advisory: never emit provider orders, account credentials, "
        "position quantities, execution instructions, Risk approval, Trader promotion, or "
        "Production authority. Preserve uncertainty and disagreement. If evidence is "
        "insufficient, request evidence/research, defer, question, or abstain instead of "
        "fabricating certainty. The required semantic reasoning_mode is exactly "
        f"{mode.value}. Codes in recommendation_code, questions, request_code, and "
        "limitations must use lowercase [a-z][a-z0-9._-]* syntax. For recommend, "
        "recommendation_code is required, questions must be empty, and request_code null. "
        "For question, questions must be non-empty and recommendation_code null. For "
        "request-evidence/request-research, request_code is required and recommendation_code "
        "null. For defer/abstain, recommendation_code and request_code are null and questions "
        "empty. bounded-confidence requires confidence_level low/medium/high; every other "
        "uncertainty_kind requires confidence_level null."
    )


def _request_payload(
    request: CiboReasoningRequest,
    config: OpenAICiboAdaptiveReasoningConfiguration,
) -> bytes:
    input_payload = {
        "request_id": str(request.request_id),
        "subject_code": request.subject_code,
        "asked_at": request.asked_at.isoformat(),
        "prompt": request.prompt,
        "evidence_refs": [item.value for item in request.evidence_refs],
        "observations": list(request.observations),
        "memory_refs": [str(item) for item in request.memory_refs],
    }
    payload = {
        "model": config.model,
        "store": False,
        "reasoning": {"effort": config.provider_reasoning_effort},
        "max_output_tokens": config.max_output_tokens,
        "instructions": _system_instructions(config.semantic_mode),
        "input": json.dumps(input_payload, sort_keys=True, separators=(",", ":")),
        "text": {
            "format": {
                "type": "json_schema",
                "name": "qore_cibo_adaptive_reasoning_proposal_v1",
                "strict": True,
                "schema": _proposal_schema(config.semantic_mode),
            }
        },
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _as_str_dict(value: object) -> dict[str, object] | None:
    if not isinstance(value, dict) or any(type(key) is not str for key in value):
        return None
    return cast(dict[str, object], value)


def _extract_output_text(raw_body: bytes) -> str:
    try:
        parsed: object = json.loads(raw_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise OpenAICiboReasoningValidationError(
            "OpenAI response was not valid UTF-8 JSON"
        ) from error
    root = _as_str_dict(parsed)
    if root is None:
        raise OpenAICiboReasoningValidationError("OpenAI response root must be an object")
    output_text = root.get("output_text")
    if isinstance(output_text, str) and output_text:
        return output_text
    output = root.get("output")
    if not isinstance(output, list):
        raise OpenAICiboReasoningValidationError("OpenAI response omitted output text")
    for raw_item in output:
        item = _as_str_dict(raw_item)
        if item is None or item.get("type") != "message":
            continue
        content = item.get("content")
        if not isinstance(content, list):
            continue
        for raw_content in content:
            content_item = _as_str_dict(raw_content)
            if content_item is None:
                continue
            if content_item.get("type") == "refusal":
                raise OpenAICiboReasoningUnavailableError(
                    "OpenAI reasoning request was refused"
                )
            if content_item.get("type") == "output_text":
                text = content_item.get("text")
                if isinstance(text, str) and text:
                    return text
    raise OpenAICiboReasoningValidationError("OpenAI response omitted output text")


def _string_tuple(value: object, *, field_name: str) -> tuple[str, ...]:
    if not isinstance(value, list) or any(type(item) is not str for item in value):
        raise OpenAICiboReasoningValidationError(
            f"{field_name} must be a JSON array of strings"
        )
    return tuple(cast(str, item) for item in value)


def _nullable_string(value: object, *, field_name: str) -> str | None:
    if value is None:
        return None
    if type(value) is not str:
        raise OpenAICiboReasoningValidationError(
            f"{field_name} must be a string or null"
        )
    return value


def _parse_proposal(text: str) -> CiboReasoningProposal:
    try:
        parsed: object = json.loads(text)
    except json.JSONDecodeError as error:
        raise OpenAICiboReasoningValidationError(
            "structured output was not valid JSON"
        ) from error
    root = _as_str_dict(parsed)
    if root is None:
        raise OpenAICiboReasoningValidationError(
            "structured output root must be an object"
        )
    directive_raw = root.get("directive")
    mode_raw = root.get("reasoning_mode")
    uncertainty_raw = root.get("uncertainty_kind")
    confidence_raw = root.get("confidence_level")
    if not all(type(value) is str for value in (directive_raw, mode_raw, uncertainty_raw)):
        raise OpenAICiboReasoningValidationError(
            "structured output enum fields must be strings"
        )
    response_text = root.get("response_text")
    if type(response_text) is not str:
        raise OpenAICiboReasoningValidationError("response_text must be a string")
    used_refs_raw = _string_tuple(
        root.get("used_evidence_refs"), field_name="used_evidence_refs"
    )
    confidence: CiboConfidenceLevel | None
    if confidence_raw is None:
        confidence = None
    elif type(confidence_raw) is str:
        try:
            confidence = CiboConfidenceLevel(confidence_raw)
        except ValueError as error:
            raise OpenAICiboReasoningValidationError(
                "confidence_level is unsupported"
            ) from error
    else:
        raise OpenAICiboReasoningValidationError(
            "confidence_level must be a string or null"
        )
    try:
        return CiboReasoningProposal(
            directive=CiboExecutiveDirectiveKind(cast(str, directive_raw)),
            reasoning_mode=CiboReasoningMode(cast(str, mode_raw)),
            uncertainty_kind=CiboUncertaintyKind(cast(str, uncertainty_raw)),
            confidence_level=confidence,
            used_evidence_refs=tuple(CiboCognitiveEvidenceRef(value) for value in used_refs_raw),
            response_text=response_text,
            recommendation_code=_nullable_string(
                root.get("recommendation_code"), field_name="recommendation_code"
            ),
            questions=_string_tuple(root.get("questions"), field_name="questions"),
            request_code=_nullable_string(
                root.get("request_code"), field_name="request_code"
            ),
            limitations=_string_tuple(root.get("limitations"), field_name="limitations"),
        )
    except (
        ValueError,
        CiboCognitiveValidationError,
        CiboReasoningRuntimeValidationError,
    ) as error:
        raise OpenAICiboReasoningValidationError(
            "structured output violated CIBO proposal contracts"
        ) from error


@dataclass(frozen=True, slots=True, repr=False)
class OpenAICiboAdaptiveReasoningEngine:
    """Operational CIBO motor: HIGH normally, with explicit governed escalation."""

    api_key: SecretMaterial
    transport: OpenAIResponsesTransportBoundary
    configuration: OpenAICiboAdaptiveReasoningConfiguration = (
        OpenAICiboAdaptiveReasoningConfiguration()
    )

    def __post_init__(self) -> None:
        if type(self.api_key) is not SecretMaterial:
            raise OpenAICiboReasoningValidationError(
                "OpenAI engine requires exact opaque SecretMaterial"
            )
        if type(self.configuration) is not OpenAICiboAdaptiveReasoningConfiguration:
            raise OpenAICiboReasoningValidationError(
                "adaptive engine requires exact adaptive configuration"
            )
        self.configuration.__post_init__()

    def __repr__(self) -> str:
        return (
            "OpenAICiboAdaptiveReasoningEngine("
            f"model={self.configuration.model!r}, "
            f"semantic_mode={self.configuration.semantic_mode.value!r}, "
            f"provider_reasoning_effort={self.configuration.provider_reasoning_effort!r}, "
            "api_key=<redacted>)"
        )

    def reason(
        self,
        request: CiboReasoningRequest,
    ) -> Result[CiboReasoningProposal, CiboReasoningRuntimeError]:
        if type(request) is not CiboReasoningRequest:
            return Failure(
                OpenAICiboReasoningValidationError(
                    "adaptive OpenAI engine requires CiboReasoningRequest"
                )
            )
        try:
            CiboReasoningRequest.__post_init__(request)
            self.configuration.__post_init__()
            payload = _request_payload(request, self.configuration)
        except CiboReasoningRuntimeError as error:
            return Failure(error)
        raw = self.transport.post_json(
            payload,
            api_key=self.api_key,
            timeout_seconds=self.configuration.timeout_seconds,
        )
        if isinstance(raw, Failure):
            return raw
        try:
            proposal = _parse_proposal(_extract_output_text(raw.value))
        except OpenAICiboReasoningError as error:
            return Failure(error)
        if proposal.reasoning_mode is not self.configuration.semantic_mode:
            return Failure(
                OpenAICiboReasoningValidationError(
                    "provider reasoning mode did not match the governed requested mode"
                )
            )
        return Success(proposal)
