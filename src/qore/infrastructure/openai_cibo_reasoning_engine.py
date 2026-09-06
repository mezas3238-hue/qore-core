from __future__ import annotations

import json
from dataclasses import dataclass
from http.client import HTTPException, HTTPSConnection
from typing import Protocol, cast

from qore.infrastructure.cibo_executive_brain import CiboExecutiveDirectiveKind
from qore.infrastructure.cibo_reasoning_runtime import (
    CiboReasoningEngineError,
    CiboReasoningProposal,
    CiboReasoningRequest,
    CiboReasoningRuntimeError,
    CiboReasoningRuntimeValidationError,
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

_OPENAI_HOST = "api.openai.com"
_OPENAI_PATH = "/v1/responses"


class OpenAICiboReasoningError(CiboReasoningEngineError):
    """Base error for the OpenAI Responses reasoning adapter."""

    __slots__ = ()


class OpenAICiboReasoningValidationError(OpenAICiboReasoningError):
    """Provider configuration or response violated the adapter contract."""

    __slots__ = ()


class OpenAICiboReasoningUnavailableError(OpenAICiboReasoningError):
    """OpenAI transport could not complete the request."""

    __slots__ = ()


class OpenAIResponsesTransportBoundary(Protocol):
    """Injectable network boundary. Secret material never enters request payloads."""

    def post_json(
        self,
        payload: bytes,
        *,
        api_key: SecretMaterial,
        timeout_seconds: float,
    ) -> Result[bytes, CiboReasoningRuntimeError]:
        """POST a Responses API payload and return raw response bytes."""
        ...


@dataclass(frozen=True, slots=True)
class StdlibOpenAIResponsesTransport:
    """Minimal stdlib HTTPS transport for the OpenAI Responses API."""

    host: str = _OPENAI_HOST
    path: str = _OPENAI_PATH

    def __post_init__(self) -> None:
        if self.host != _OPENAI_HOST or self.path != _OPENAI_PATH:
            raise OpenAICiboReasoningValidationError(
                "OpenAI transport endpoint is fixed to api.openai.com/v1/responses"
            )

    def post_json(
        self,
        payload: bytes,
        *,
        api_key: SecretMaterial,
        timeout_seconds: float,
    ) -> Result[bytes, CiboReasoningRuntimeError]:
        if not isinstance(payload, bytes) or not payload:
            return Failure(
                OpenAICiboReasoningValidationError(
                    "OpenAI payload must be non-empty bytes"
                )
            )
        if not isinstance(api_key, SecretMaterial):
            return Failure(
                OpenAICiboReasoningValidationError(
                    "OpenAI API key must be opaque SecretMaterial"
                )
            )
        if type(timeout_seconds) is not float or timeout_seconds <= 0:
            return Failure(
                OpenAICiboReasoningValidationError(
                    "OpenAI timeout_seconds must be a positive float"
                )
            )
        try:
            key = api_key.reveal_bytes().decode("ascii")
        except UnicodeDecodeError:
            return Failure(
                OpenAICiboReasoningValidationError(
                    "OpenAI API key must be ASCII"
                )
            )
        if any(ord(ch) < 33 or ord(ch) > 126 for ch in key):
            return Failure(
                OpenAICiboReasoningValidationError(
                    "OpenAI API key must be visible ASCII without whitespace"
                )
            )

        connection: HTTPSConnection | None = None
        try:
            connection = HTTPSConnection(
                self.host,
                443,
                timeout=timeout_seconds,
            )
            connection.request(
                "POST",
                self.path,
                body=payload,
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                },
            )
            response = connection.getresponse()
            body = response.read()
            if response.status < 200 or response.status >= 300:
                return Failure(
                    OpenAICiboReasoningUnavailableError(
                        f"OpenAI Responses API returned HTTP {response.status}"
                    )
                )
            return Success(body)
        except TimeoutError:
            return Failure(
                OpenAICiboReasoningUnavailableError(
                    "OpenAI Responses API timed out"
                )
            )
        except (HTTPException, OSError):
            return Failure(
                OpenAICiboReasoningUnavailableError(
                    "OpenAI Responses API transport unavailable"
                )
            )
        finally:
            if connection is not None:
                connection.close()


@dataclass(frozen=True, slots=True)
class OpenAICiboReasoningConfiguration:
    """Explicit first-ignition model configuration."""

    model: str = "gpt-5.6-sol"
    reasoning_effort: str = "max"
    timeout_seconds: float = 90.0
    max_output_tokens: int = 2500

    def __post_init__(self) -> None:
        if type(self.model) is not str or not self.model.strip():
            raise OpenAICiboReasoningValidationError(
                "OpenAI model must be non-empty"
            )
        if self.reasoning_effort not in {
            "none",
            "low",
            "medium",
            "high",
            "xhigh",
            "max",
        }:
            raise OpenAICiboReasoningValidationError(
                "OpenAI reasoning_effort is unsupported"
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


def _proposal_schema() -> dict[str, object]:
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
            "reasoning_mode": {
                "type": "string",
                "enum": ["max"],
            },
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
            "confidence_level": {
                "enum": ["low", "medium", "high", None],
            },
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
            "recommendation_code": {
                "type": ["string", "null"],
            },
            "questions": {
                "type": "array",
                "items": {"type": "string"},
                "uniqueItems": True,
            },
            "request_code": {
                "type": ["string", "null"],
            },
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


_SYSTEM_INSTRUCTIONS = """\
You are the external reasoning motor for CIBO inside QORE Core.
Return only the requested structured JSON object. Never expose chain-of-thought.
Provide a concise one-line decision explanation in response_text, not hidden reasoning.
Use only evidence reference strings supplied in the input; never invent evidence.
CIBO intelligence is advisory: never emit provider orders, account credentials,
position quantities, execution instructions, Risk approval, Trader promotion, or
Production authority. Preserve uncertainty and disagreement. If evidence is
insufficient, request evidence/research, defer, question, or abstain instead of
fabricating certainty. The semantic reasoning_mode for this first ignition is max.
Codes in recommendation_code, questions, request_code, and limitations must use
lowercase [a-z][a-z0-9._-]* syntax. For recommend, recommendation_code is required,
questions must be empty, and request_code must be null. For question, questions
must be non-empty and recommendation_code must be null. For request-evidence or
request-research, request_code is required and recommendation_code must be null.
For defer/abstain, recommendation_code and request_code are null and questions empty.
bounded-confidence requires confidence_level low/medium/high; every other
uncertainty_kind requires confidence_level null.
"""


def _request_payload(
    request: CiboReasoningRequest,
    config: OpenAICiboReasoningConfiguration,
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
        "reasoning": {"effort": config.reasoning_effort},
        "max_output_tokens": config.max_output_tokens,
        "instructions": _SYSTEM_INSTRUCTIONS,
        "input": json.dumps(
            input_payload,
            sort_keys=True,
            separators=(",", ":"),
        ),
        "text": {
            "format": {
                "type": "json_schema",
                "name": "qore_cibo_reasoning_proposal_v1",
                "strict": True,
                "schema": _proposal_schema(),
            }
        },
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _as_str_dict(value: object) -> dict[str, object] | None:
    if not isinstance(value, dict):
        return None
    if any(type(key) is not str for key in value):
        return None
    return cast(dict[str, object], value)


def _extract_output_text(raw_body: bytes) -> str:
    try:
        decoded = raw_body.decode("utf-8")
        parsed: object = json.loads(decoded)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise OpenAICiboReasoningValidationError(
            "OpenAI response was not valid UTF-8 JSON"
        ) from error
    root = _as_str_dict(parsed)
    if root is None:
        raise OpenAICiboReasoningValidationError(
            "OpenAI response root must be an object"
        )
    output_text = root.get("output_text")
    if isinstance(output_text, str) and output_text:
        return output_text

    output = root.get("output")
    if not isinstance(output, list):
        raise OpenAICiboReasoningValidationError(
            "OpenAI response omitted output text"
        )
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
    reasoning_mode_raw = root.get("reasoning_mode")
    uncertainty_raw = root.get("uncertainty_kind")
    confidence_raw = root.get("confidence_level")
    if not all(
        type(value) is str
        for value in (directive_raw, reasoning_mode_raw, uncertainty_raw)
    ):
        raise OpenAICiboReasoningValidationError(
            "structured output enum fields must be strings"
        )
    response_text = root.get("response_text")
    if type(response_text) is not str:
        raise OpenAICiboReasoningValidationError(
            "response_text must be a string"
        )
    used_refs_raw = _string_tuple(
        root.get("used_evidence_refs"),
        field_name="used_evidence_refs",
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
            reasoning_mode=CiboReasoningMode(cast(str, reasoning_mode_raw)),
            uncertainty_kind=CiboUncertaintyKind(cast(str, uncertainty_raw)),
            confidence_level=confidence,
            used_evidence_refs=tuple(
                CiboCognitiveEvidenceRef(value) for value in used_refs_raw
            ),
            response_text=response_text,
            recommendation_code=_nullable_string(
                root.get("recommendation_code"),
                field_name="recommendation_code",
            ),
            questions=_string_tuple(root.get("questions"), field_name="questions"),
            request_code=_nullable_string(
                root.get("request_code"),
                field_name="request_code",
            ),
            limitations=_string_tuple(
                root.get("limitations"),
                field_name="limitations",
            ),
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
class OpenAICiboReasoningEngine:
    """GPT-5.6 Sol reasoning adapter. Proposal only; no execution authority."""

    api_key: SecretMaterial
    transport: OpenAIResponsesTransportBoundary
    configuration: OpenAICiboReasoningConfiguration = OpenAICiboReasoningConfiguration()

    def __post_init__(self) -> None:
        if not isinstance(self.api_key, SecretMaterial):
            raise OpenAICiboReasoningValidationError(
                "OpenAI engine requires opaque SecretMaterial"
            )
        if not isinstance(self.configuration, OpenAICiboReasoningConfiguration):
            raise OpenAICiboReasoningValidationError(
                "OpenAI engine requires explicit configuration"
            )

    def __repr__(self) -> str:
        return (
            "OpenAICiboReasoningEngine("
            f"model={self.configuration.model!r}, "
            f"reasoning_effort={self.configuration.reasoning_effort!r}, "
            "api_key=<redacted>)"
        )

    def reason(
        self,
        request: CiboReasoningRequest,
    ) -> Result[CiboReasoningProposal, CiboReasoningRuntimeError]:
        if type(request) is not CiboReasoningRequest:
            return Failure(
                OpenAICiboReasoningValidationError(
                    "OpenAI engine requires CiboReasoningRequest"
                )
            )
        try:
            CiboReasoningRequest.__post_init__(request)
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
        if proposal.reasoning_mode is not CiboReasoningMode.MAX:
            return Failure(
                OpenAICiboReasoningValidationError(
                    "first-ignition OpenAI engine must return MAX reasoning mode"
                )
            )
        return Success(proposal)
