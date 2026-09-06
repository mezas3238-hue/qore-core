from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from typing import cast

from qore.infrastructure.cibo_adaptive_reasoning_runtime import (
    CiboReasoningEngineAdmission,
    CiboReasoningProviderEvidence,
    cibo_reasoning_proposal_digest,
    cibo_reasoning_request_digest,
)
from qore.infrastructure.cibo_reasoning_policy import CiboReasoningRoute
from qore.infrastructure.cibo_reasoning_runtime import (
    CiboReasoningRequest,
    CiboReasoningRuntimeError,
)
from qore.infrastructure.openai_cibo_adaptive_reasoning_engine import (
    _extract_output_text,
    _parse_proposal,
    _proposal_schema,
    _system_instructions,
)
from qore.infrastructure.openai_cibo_reasoning_engine import (
    OpenAICiboReasoningError,
    OpenAICiboReasoningValidationError,
    OpenAIResponsesTransportBoundary,
)
from qore.infrastructure.secret_resolution import SecretMaterial
from qore.kernel.result import Failure, Result, Success

_ALLOWED_MODELS = frozenset(("gpt-5.6-terra", "gpt-5.6-sol"))
_ALLOWED_EFFORTS_BY_MODEL: dict[str, frozenset[str]] = {
    "gpt-5.6-terra": frozenset(("medium", "high")),
    "gpt-5.6-sol": frozenset(("high", "max")),
}


def _sha256_bytes(value: bytes) -> str:
    return f"sha256:{sha256(value).hexdigest()}"


def _sha256_json(value: object) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return _sha256_bytes(encoded)


def _provider_response_ref(raw_body: bytes) -> str:
    try:
        parsed: object = json.loads(raw_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise OpenAICiboReasoningValidationError(
            "OpenAI response was not valid UTF-8 JSON"
        ) from error
    if not isinstance(parsed, dict):
        raise OpenAICiboReasoningValidationError(
            "OpenAI response root must be an object"
        )
    root = cast(dict[object, object], parsed)
    response_ref = root.get("id")
    if type(response_ref) is not str or not response_ref:
        raise OpenAICiboReasoningValidationError(
            "OpenAI response omitted provider response id"
        )
    if any(ch in response_ref for ch in "\x00\n\r\t"):
        raise OpenAICiboReasoningValidationError(
            "OpenAI response id contained control characters"
        )
    return response_ref


@dataclass(frozen=True, slots=True)
class OpenAICiboRoutedReasoningConfiguration:
    """Exact route-bound OpenAI configuration selected by CIBO policy."""

    route: CiboReasoningRoute
    timeout_seconds: float = 90.0
    max_output_tokens: int = 2500

    def __post_init__(self) -> None:
        if type(self.route) is not CiboReasoningRoute:
            raise OpenAICiboReasoningValidationError(
                "routed configuration requires exact CiboReasoningRoute"
            )
        self.route.__post_init__()
        if self.route.model not in _ALLOWED_MODELS:
            raise OpenAICiboReasoningValidationError(
                "routed CIBO model is not in the governed registry"
            )
        if self.route.provider_reasoning_effort not in _ALLOWED_EFFORTS_BY_MODEL[
            self.route.model
        ]:
            raise OpenAICiboReasoningValidationError(
                "provider effort is not allowed for the selected governed model"
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

    @property
    def model(self) -> str:
        return self.route.model

    @property
    def provider_reasoning_effort(self) -> str:
        return self.route.provider_reasoning_effort

    @property
    def semantic_mode_value(self) -> str:
        return self.route.semantic_mode.value

    @property
    def schema_fingerprint(self) -> str:
        return _sha256_json(_proposal_schema(self.route.semantic_mode))

    @property
    def configuration_fingerprint(self) -> str:
        return _sha256_json(
            {
                "engine": "openai-responses",
                "model": self.model,
                "provider_reasoning_effort": self.provider_reasoning_effort,
                "semantic_mode": self.semantic_mode_value,
                "route_tier": self.route.tier.value,
                "routing_reason": self.route.routing_reason,
                "max_output_tokens": self.max_output_tokens,
                "schema_fingerprint": self.schema_fingerprint,
            }
        )


def _request_payload(
    request: CiboReasoningRequest,
    config: OpenAICiboRoutedReasoningConfiguration,
) -> bytes:
    input_payload = {
        "request_id": str(request.request_id),
        "subject_code": request.subject_code,
        "asked_at": request.asked_at.isoformat(),
        "prompt": request.prompt,
        "evidence_refs": [item.value for item in request.evidence_refs],
        "observations": list(request.observations),
        "memory_refs": [str(item) for item in request.memory_refs],
        "routing": {
            "semantic_mode": config.route.semantic_mode.value,
            "route_tier": config.route.tier.value,
            "routing_reason": config.route.routing_reason,
        },
    }
    payload = {
        "model": config.model,
        "store": False,
        "reasoning": {"effort": config.provider_reasoning_effort},
        "max_output_tokens": config.max_output_tokens,
        "instructions": _system_instructions(config.route.semantic_mode),
        "input": json.dumps(input_payload, sort_keys=True, separators=(",", ":")),
        "text": {
            "format": {
                "type": "json_schema",
                "name": "qore_cibo_routed_reasoning_proposal_v1",
                "strict": True,
                "schema": _proposal_schema(config.route.semantic_mode),
            }
        },
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


@dataclass(frozen=True, slots=True, repr=False)
class OpenAICiboRoutedReasoningEngine:
    """Operational Terra/Sol engine selected only by a governed CIBO route."""

    api_key: SecretMaterial
    transport: OpenAIResponsesTransportBoundary
    configuration: OpenAICiboRoutedReasoningConfiguration

    def __post_init__(self) -> None:
        if type(self.api_key) is not SecretMaterial:
            raise OpenAICiboReasoningValidationError(
                "OpenAI routed engine requires exact opaque SecretMaterial"
            )
        if type(self.configuration) is not OpenAICiboRoutedReasoningConfiguration:
            raise OpenAICiboReasoningValidationError(
                "OpenAI routed engine requires exact routed configuration"
            )
        self.configuration.__post_init__()

    def __repr__(self) -> str:
        return (
            "OpenAICiboRoutedReasoningEngine("
            f"model={self.configuration.model!r}, "
            f"semantic_mode={self.configuration.route.semantic_mode.value!r}, "
            f"route_tier={self.configuration.route.tier.value!r}, "
            "provider_reasoning_effort="
            f"{self.configuration.provider_reasoning_effort!r}, "
            "api_key=<redacted>)"
        )

    def reason_with_evidence(
        self,
        request: CiboReasoningRequest,
    ) -> Result[CiboReasoningEngineAdmission, CiboReasoningRuntimeError]:
        if type(request) is not CiboReasoningRequest:
            return Failure(
                OpenAICiboReasoningValidationError(
                    "routed OpenAI engine requires exact CiboReasoningRequest"
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
            response_ref = _provider_response_ref(raw.value)
            proposal = _parse_proposal(_extract_output_text(raw.value))
            if proposal.reasoning_mode is not self.configuration.route.semantic_mode:
                raise OpenAICiboReasoningValidationError(
                    "provider semantic mode did not match governed selected route"
                )
            evidence = CiboReasoningProviderEvidence(
                route=self.configuration.route,
                provider_code="openai",
                engine_code="openai.responses",
                request_digest=cibo_reasoning_request_digest(request),
                request_payload_digest=_sha256_bytes(payload),
                response_digest=_sha256_bytes(raw.value),
                configuration_fingerprint=(
                    self.configuration.configuration_fingerprint
                ),
                schema_fingerprint=self.configuration.schema_fingerprint,
                provider_response_ref=response_ref,
                admitted_proposal_digest=cibo_reasoning_proposal_digest(proposal),
            )
            return Success(
                CiboReasoningEngineAdmission(
                    proposal=proposal,
                    provider_evidence=evidence,
                )
            )
        except OpenAICiboReasoningError as error:
            return Failure(error)
        except CiboReasoningRuntimeError as error:
            return Failure(error)
