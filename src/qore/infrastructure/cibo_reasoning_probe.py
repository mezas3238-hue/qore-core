from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from uuid import NAMESPACE_URL, UUID, uuid5

from qore.infrastructure.cibo_adaptive_reasoning_runtime import (
    CiboAdaptiveReasoningRuntime,
)
from qore.infrastructure.cibo_reasoning_policy import (
    CiboReasoningEpisodeState,
    CiboReasoningMateriality,
    CiboReasoningSituation,
    CiboReasoningUncertainty,
    select_cibo_reasoning_route,
)
from qore.infrastructure.cibo_reasoning_runtime import CiboReasoningRequest
from qore.infrastructure.openai_cibo_reasoning_engine import (
    StdlibOpenAIResponsesTransport,
)
from qore.infrastructure.openai_cibo_routed_reasoning_engine import (
    OpenAICiboRoutedReasoningConfiguration,
    OpenAICiboRoutedReasoningEngine,
)
from qore.infrastructure.secret_resolution import SecretMaterial
from qore.kernel.result import Failure
from qore.modules.cibo.cognitive_contracts import CiboCognitiveEvidenceRef


def _request_id(
    *,
    asked_at: datetime,
    subject_code: str,
    prompt: str,
    route_identity: str,
) -> UUID:
    return uuid5(
        NAMESPACE_URL,
        (
            "qore:cibo-adaptive-ignition:"
            f"{asked_at.isoformat()}:{subject_code}:{route_identity}:{prompt}"
        ),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run one governed adaptive CIBO Terra/Sol reasoning probe."
    )
    parser.add_argument("prompt")
    parser.add_argument("--subject-code", default="cibo.self-assessment")
    parser.add_argument(
        "--evidence-ref",
        action="append",
        default=[],
        help="Additional opaque evidence reference. May be supplied more than once.",
    )
    parser.add_argument(
        "--elevated-analysis",
        action="store_true",
        help="Typed moderate-complexity signal; routes routine cognition to Terra/high.",
    )
    parser.add_argument(
        "--material-analysis",
        action="store_true",
        help="Typed materiality signal; routes material cognition to Sol/high.",
    )
    parser.add_argument(
        "--serious-controversy",
        action="store_true",
        help="Typed serious controversy signal; routes to Sol/max.",
    )
    parser.add_argument(
        "--council-adversarial",
        action="store_true",
        help="Typed unresolved material multi-Trader disagreement; Sol/max Council.",
    )
    parser.add_argument(
        "--voice",
        action="store_true",
        help="Mark voice as the channel only; it never escalates reasoning by itself.",
    )
    parser.add_argument(
        "--resolved-episode",
        action="store_true",
        help="Prove explicit de-escalation of a resolved episode back to Terra/medium.",
    )
    args = parser.parse_args(argv)

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print(
            json.dumps(
                {
                    "status": "blocked",
                    "error": "OPENAI_API_KEY is required for the live reasoning probe",
                },
                sort_keys=True,
            )
        )
        return 2
    try:
        secret = SecretMaterial(api_key.encode("ascii"))
    except UnicodeEncodeError:
        print(
            json.dumps(
                {
                    "status": "blocked",
                    "error": "OPENAI_API_KEY must be ASCII",
                },
                sort_keys=True,
            )
        )
        return 2

    materiality = CiboReasoningMateriality.ROUTINE
    uncertainty = CiboReasoningUncertainty.LOW
    if args.elevated_analysis:
        materiality = CiboReasoningMateriality.MODERATE
        uncertainty = CiboReasoningUncertainty.MODERATE
    if args.material_analysis:
        materiality = CiboReasoningMateriality.MATERIAL
    if args.serious_controversy:
        materiality = CiboReasoningMateriality.CRITICAL
        uncertainty = CiboReasoningUncertainty.HIGH

    episode_state = (
        CiboReasoningEpisodeState.RESOLVED
        if args.resolved_episode
        else CiboReasoningEpisodeState.ACTIVE
    )
    situation = CiboReasoningSituation(
        materiality=materiality,
        uncertainty=uncertainty,
        episode_state=episode_state,
        material_trader_disagreement=args.council_adversarial,
        unresolved_after_ordinary_analysis=args.council_adversarial,
        serious_controversy=args.serious_controversy,
        adversarial_council=args.council_adversarial,
        voice_channel=args.voice,
    )
    route = select_cibo_reasoning_route(situation)
    config = OpenAICiboRoutedReasoningConfiguration(route=route)

    asked_at = datetime.now(UTC)
    evidence_values = ("input:user-dialogue", *tuple(args.evidence_ref))
    request = CiboReasoningRequest(
        request_id=_request_id(
            asked_at=asked_at,
            subject_code=args.subject_code,
            prompt=args.prompt,
            route_identity=(
                f"{route.tier.value}:{route.model}:"
                f"{route.provider_reasoning_effort}:{route.semantic_mode.value}"
            ),
        ),
        subject_code=args.subject_code,
        asked_at=asked_at,
        prompt=args.prompt,
        evidence_refs=tuple(
            CiboCognitiveEvidenceRef(value) for value in evidence_values
        ),
        observations=(f"runtime.reasoning-route.{route.tier.value}",),
    )
    engine = OpenAICiboRoutedReasoningEngine(
        api_key=secret,
        transport=StdlibOpenAIResponsesTransport(),
        configuration=config,
    )
    runtime = CiboAdaptiveReasoningRuntime(engine=engine, route=route)
    result = runtime.run(request, synthesized_at=datetime.now(UTC))
    if isinstance(result, Failure):
        print(
            json.dumps(
                {
                    "status": "blocked",
                    "error_type": type(result.error).__name__,
                    "error": str(result.error),
                },
                sort_keys=True,
            )
        )
        return 1

    adaptive = result.value
    synthesis = adaptive.runtime_result.synthesis
    receipt = adaptive.receipt
    print(
        json.dumps(
            {
                "status": "success",
                "request_id": str(adaptive.runtime_result.request_id),
                "route_tier": route.tier.value,
                "routing_reason": route.routing_reason,
                "model": route.model,
                "provider_reasoning_effort": route.provider_reasoning_effort,
                "directive": synthesis.directive.value,
                "reasoning_mode": synthesis.reasoning_mode.value,
                "uncertainty_kind": synthesis.uncertainty.kind.value,
                "response": adaptive.runtime_result.response_text,
                "evidence_refs": [ref.value for ref in synthesis.evidence_refs],
                "limitations": list(synthesis.limitations),
                "recommendation_code": (
                    None
                    if synthesis.recommendation is None
                    else synthesis.recommendation.recommendation_code
                ),
                "questions": list(synthesis.questions),
                "request_code": synthesis.request_code,
                "provider_response_ref": receipt.provider_response_ref,
                "request_digest": receipt.request_digest,
                "request_payload_digest": receipt.request_payload_digest,
                "response_digest": receipt.response_digest,
                "configuration_fingerprint": receipt.configuration_fingerprint,
                "schema_fingerprint": receipt.schema_fingerprint,
                "admitted_proposal_digest": receipt.admitted_proposal_digest,
                "started_at": receipt.started_at.isoformat(),
                "completed_at": receipt.completed_at.isoformat(),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
