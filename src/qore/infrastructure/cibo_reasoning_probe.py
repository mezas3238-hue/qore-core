from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from uuid import NAMESPACE_URL, UUID, uuid5

from qore.infrastructure.cibo_reasoning_runtime import (
    CiboReasoningRequest,
    CiboReasoningRuntime,
)
from qore.infrastructure.openai_cibo_reasoning_engine import (
    OpenAICiboReasoningConfiguration,
    OpenAICiboReasoningEngine,
    StdlibOpenAIResponsesTransport,
)
from qore.infrastructure.secret_resolution import SecretMaterial
from qore.kernel.result import Failure
from qore.modules.cibo.cognitive_contracts import CiboCognitiveEvidenceRef


def _request_id(*, asked_at: datetime, subject_code: str, prompt: str) -> UUID:
    return uuid5(
        NAMESPACE_URL,
        f"qore:cibo-first-ignition:{asked_at.isoformat()}:{subject_code}:{prompt}",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run one governed CIBO cognitive reasoning ignition probe."
    )
    parser.add_argument("prompt")
    parser.add_argument("--subject-code", default="cibo.self-assessment")
    parser.add_argument(
        "--evidence-ref",
        action="append",
        default=[],
        help="Additional opaque evidence reference. May be supplied more than once.",
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

    model = os.environ.get("QORE_CIBO_MODEL", "gpt-5.6-sol")
    asked_at = datetime.now(UTC)
    evidence_values = ("input:user-dialogue", *tuple(args.evidence_ref))
    request = CiboReasoningRequest(
        request_id=_request_id(
            asked_at=asked_at,
            subject_code=args.subject_code,
            prompt=args.prompt,
        ),
        subject_code=args.subject_code,
        asked_at=asked_at,
        prompt=args.prompt,
        evidence_refs=tuple(
            CiboCognitiveEvidenceRef(value) for value in evidence_values
        ),
    )
    engine = OpenAICiboReasoningEngine(
        api_key=secret,
        transport=StdlibOpenAIResponsesTransport(),
        configuration=OpenAICiboReasoningConfiguration(
            model=model,
            reasoning_effort="max",
        ),
    )
    runtime = CiboReasoningRuntime(engine=engine)
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

    synthesis = result.value.synthesis
    print(
        json.dumps(
            {
                "status": "success",
                "request_id": str(result.value.request_id),
                "directive": synthesis.directive.value,
                "reasoning_mode": synthesis.reasoning_mode.value,
                "uncertainty_kind": synthesis.uncertainty.kind.value,
                "response": result.value.response_text,
                "evidence_refs": [ref.value for ref in synthesis.evidence_refs],
                "limitations": list(synthesis.limitations),
                "recommendation_code": (
                    None
                    if synthesis.recommendation is None
                    else synthesis.recommendation.recommendation_code
                ),
                "questions": list(synthesis.questions),
                "request_code": synthesis.request_code,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
