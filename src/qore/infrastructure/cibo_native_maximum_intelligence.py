"""Native-only maximum intelligence engine for sovereign CIBO.

This engine is deliberately independent from OpenAI/GPT/TERRA/SOL or any other
external reasoning provider. It consumes only:
- complete native Trader predecision perception;
- sovereign CF01-CF19 native semantic receipts;
- CIBO's provider-neutral Executive Brain.

It emits an advisory executive synthesis only. It never chooses broker orders,
never grants Risk/execution authority and never bypasses CMA/QORE Risk.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from uuid import NAMESPACE_URL, uuid5

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
    TraderOpportunityEnvelope,
)
from qore.infrastructure.cibo_native_max_cognitive_episode import (
    CiboNativeMaxCognitiveEpisode,
    build_native_max_cognitive_episode,
)
from qore.infrastructure.cibo_executive_brain import (
    CiboExecutiveBrain,
    CiboExecutiveDirectiveKind,
    CiboExecutiveSynthesis,
)
from qore.infrastructure.cibo_sovereign_function_consultation import (
    CiboEconomicConsultationReceipt,
)
from qore.kernel.result import Success
from qore.modules.cibo.cognitive_contracts import (
    CiboCognitiveEvidenceRef,
    CiboConfidence,
    CiboConfidenceLevel,
    CiboFormalRecommendation,
    CiboReasoningMode,
    CiboUncertainty,
    CiboUncertaintyKind,
)


_TURTLE_TRADERS = frozenset(
    {
        TraderLineage.R34_XAUUSD,
        TraderLineage.R38_EURUSD,
        TraderLineage.R43_GBPUSD,
        TraderLineage.R38_GBPJPY,
        TraderLineage.R42_AUDJPY,
    }
)
_POST_OUTCOME_NOT_APPLICABLE = frozenset({"CF08", "CF18", "CF19"})
_FORBIDDEN_CONTEXT_TOKENS = (
    "outcome",
    "realized",
    "pnl",
    "mfe",
    "mae",
    "winner",
    "loser",
    "future",
)
_VT08_REQUIRED = frozenset(
    {
        "strategy_family",
        "entry_anchor_hour_ny",
        "reference_h4_opened_at",
        "reference_h4_direction",
        "reference_h4_range",
        "reference_important_level",
        "candle2_opened_at",
        "candle2_direction",
        "candle2_range",
        "protected_swing_price",
        "cisd_level",
        "cisd_confirmed_at",
        "cisd_age_minutes",
        "risk_distance",
        "target_distance",
        "planned_target_r",
        "source_context_causal",
        "cibo_native_perception_complete",
        "cibo_native_perception_version",
    }
)


@dataclass(frozen=True, slots=True)
class CiboNativeMaximumIntelligenceResult:
    synthesis: CiboExecutiveSynthesis
    consultation_id: str
    semantic_digest: str
    cognitive_episode: CiboNativeMaxCognitiveEpisode
    applicable_faculty_count: int
    successful_faculty_count: int
    not_applicable_faculty_count: int
    blocked_function_codes: tuple[str, ...]
    perception_key_counts: tuple[tuple[str, int], ...]
    native_only: bool = True
    external_ai_call_count: int = 0
    external_reasoning_provider_used: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.synthesis, CiboExecutiveSynthesis):
            raise CiboCapitalManagementError(
                "native maximum intelligence requires executive synthesis"
            )
        self.synthesis.revalidate()
        if (
            not isinstance(self.consultation_id, str)
            or not self.consultation_id.startswith("sha256:")
        ):
            raise CiboCapitalManagementError(
                "native maximum intelligence consultation id invalid"
            )
        if not isinstance(
            self.cognitive_episode,
            CiboNativeMaxCognitiveEpisode,
        ):
            raise CiboCapitalManagementError(
                "native maximum intelligence requires cognitive episode"
            )
        self.cognitive_episode.__post_init__()
        if (
            not isinstance(self.semantic_digest, str)
            or not self.semantic_digest.startswith("sha256:")
        ):
            raise CiboCapitalManagementError(
                "native maximum intelligence semantic digest invalid"
            )
        for name in (
            "applicable_faculty_count",
            "successful_faculty_count",
            "not_applicable_faculty_count",
            "external_ai_call_count",
        ):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise CiboCapitalManagementError(
                    f"native maximum intelligence {name} invalid"
                )
        if self.applicable_faculty_count + self.not_applicable_faculty_count != 19:
            raise CiboCapitalManagementError(
                "native maximum intelligence must account for CF01-CF19 exactly"
            )
        if self.successful_faculty_count > self.applicable_faculty_count:
            raise CiboCapitalManagementError(
                "native maximum intelligence success count exceeds applicable faculties"
            )
        if type(self.native_only) is not bool or not self.native_only:
            raise CiboCapitalManagementError(
                "maximum-capability intelligence must be native-only"
            )
        if self.external_ai_call_count != 0:
            raise CiboCapitalManagementError(
                "maximum-capability intelligence cannot call external AI"
            )
        if (
            type(self.external_reasoning_provider_used) is not bool
            or self.external_reasoning_provider_used
        ):
            raise CiboCapitalManagementError(
                "maximum-capability intelligence cannot use external reasoning provider"
            )


def _context_map(opportunity: TraderOpportunityEnvelope) -> dict[str, str]:
    context = dict(opportunity.decision_context)
    if len(context) != len(opportunity.decision_context):
        raise CiboCapitalManagementError(
            "native maximum intelligence decision context contains duplicate keys"
        )
    for key in context:
        lowered = key.lower()
        if any(token in lowered for token in _FORBIDDEN_CONTEXT_TOKENS):
            raise CiboCapitalManagementError(
                "native maximum intelligence context contains outcome/future material"
            )
    return context


def validate_native_maximum_perception(
    opportunities: tuple[TraderOpportunityEnvelope, ...],
) -> tuple[tuple[str, int], ...]:
    if (
        not isinstance(opportunities, tuple)
        or not opportunities
        or any(
            not isinstance(item, TraderOpportunityEnvelope)
            for item in opportunities
        )
    ):
        raise CiboCapitalManagementError(
            "native maximum intelligence requires canonical opportunities"
        )

    counts: list[tuple[str, int]] = []
    for opportunity in opportunities:
        context = _context_map(opportunity)
        counts.append((opportunity.signal_fingerprint, len(context)))

        if opportunity.trader_id in _TURTLE_TRADERS:
            if len(context) < 30:
                raise CiboCapitalManagementError(
                    f"{opportunity.trader_id.value} native perception is incomplete"
                )
            continue

        if opportunity.trader_id is TraderLineage.VT08_FOREX:
            missing = _VT08_REQUIRED - set(context)
            if missing:
                raise CiboCapitalManagementError(
                    "VT08 native perception incomplete: "
                    + ",".join(sorted(missing))
                )
            if context.get("cibo_native_perception_complete") != "true":
                raise CiboCapitalManagementError(
                    "VT08 native perception is not complete"
                )
            continue

        if opportunity.trader_id is TraderLineage.VT31_NAS100:
            if len(context) < 20:
                raise CiboCapitalManagementError(
                    "VT31 native M1/H1/H4 perception is incomplete"
                )
            if context.get("cibo_native_perception_complete") != "true":
                raise CiboCapitalManagementError(
                    "VT31 native perception is not complete"
                )
            if not context.get("cibo_native_perception_version"):
                raise CiboCapitalManagementError(
                    "VT31 native perception version is missing"
                )
            continue

        raise CiboCapitalManagementError(
            "native maximum intelligence received unsupported Trader"
        )

    return tuple(sorted(counts))


def _semantic_digest(
    consultation: CiboEconomicConsultationReceipt,
) -> tuple[str, int, int, tuple[str, ...]]:
    if len(consultation.faculty_receipts) != 19:
        raise CiboCapitalManagementError(
            "native maximum intelligence requires exact CF01-CF19 receipts"
        )

    canonical: list[dict[str, object]] = []
    applicable = 0
    successful = 0
    formal_blocked: list[str] = []

    for receipt in consultation.faculty_receipts:
        payload = receipt.output_payload
        called = payload.get("native_engine_called")
        status = payload.get("native_engine_status")
        formal_native = payload.get("native_engine_output")
        research = payload.get("research_semantic_observation")
        if type(called) is not bool or not isinstance(formal_native, dict):
            raise CiboCapitalManagementError(
                f"{receipt.function_code} native receipt malformed"
            )
        if not isinstance(research, dict):
            raise CiboCapitalManagementError(
                f"{receipt.function_code} native research semantics missing"
            )
        if research.get("schema") != (
            "qore.cibo.native-faculty-research-semantics.v1"
        ):
            raise CiboCapitalManagementError(
                f"{receipt.function_code} research semantic schema drift"
            )
        if (
            research.get("function_code") != receipt.function_code
            or research.get("research_read_only") is not True
            or research.get("causal_predecision_only") is not True
            or research.get("memory_is_evidence_not_authority") is not True
            or research.get("economic_authority") is not False
            or research.get("sizing_authority") is not False
            or research.get("risk_authority") is not False
            or research.get("execution_authority") is not False
            or research.get("broker_authority") is not False
            or research.get("outcome_used") is not False
            or not isinstance(research.get("semantics"), dict)
            or not isinstance(research.get("semantic_sha256"), str)
        ):
            raise CiboCapitalManagementError(
                f"{receipt.function_code} research semantic authority drift"
            )

        if called:
            applicable += 1
            if status == "SUCCESS":
                successful += 1
            else:
                formal_blocked.append(receipt.function_code)
        else:
            if receipt.function_code not in _POST_OUTCOME_NOT_APPLICABLE:
                raise CiboCapitalManagementError(
                    f"{receipt.function_code} was fractionally skipped"
                )
            if status != "JUSTIFIED_NOT_APPLICABLE":
                raise CiboCapitalManagementError(
                    f"{receipt.function_code} invalid not-applicable status"
                )

        canonical.append(
            {
                "function_code": receipt.function_code,
                "faculty": receipt.faculty.value,
                "formal_status": status,
                "formal_engine_name": payload.get("native_engine_name"),
                "research_semantics": research,
                "input_sha256": receipt.input_sha256,
                "output_sha256": receipt.output_sha256,
            }
        )

    raw = json.dumps(
        canonical,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    ).encode()
    return (
        "sha256:" + hashlib.sha256(raw).hexdigest(),
        applicable,
        successful,
        tuple(sorted(formal_blocked)),
    )

def run_native_maximum_intelligence(
    *,
    consultation: CiboEconomicConsultationReceipt,
    opportunities: tuple[TraderOpportunityEnvelope, ...],
    target: TraderOpportunityEnvelope,
    regime_state,
) -> CiboNativeMaximumIntelligenceResult:
    """Run native CIBO intelligence without any external AI/provider."""

    if not isinstance(consultation, CiboEconomicConsultationReceipt):
        raise CiboCapitalManagementError(
            "native maximum intelligence requires canonical consultation"
        )
    if consultation.outcome_used or consultation.broker_mutation:
        raise CiboCapitalManagementError(
            "native maximum intelligence consultation is contaminated"
        )
    fingerprints = tuple(item.signal_fingerprint for item in opportunities)
    if target.signal_fingerprint not in fingerprints:
        raise CiboCapitalManagementError(
            "native maximum intelligence target absent from opportunity surface"
        )
    perception_counts = validate_native_maximum_perception(opportunities)
    semantic_digest, applicable, successful, blocked = _semantic_digest(
        consultation
    )
    not_applicable = 19 - applicable

    cognitive_episode = build_native_max_cognitive_episode(
        consultation=consultation,
        opportunities=opportunities,
        target=target,
        regime_state=regime_state,
    )

    evidence_refs = tuple(
        sorted(
            (
                CiboCognitiveEvidenceRef(
                    "cibo:native-consultation:"
                    + consultation.consultation_id.removeprefix("sha256:")
                ),
                CiboCognitiveEvidenceRef(
                    "cibo:native-semantic:"
                    + semantic_digest.removeprefix("sha256:")
                ),
                CiboCognitiveEvidenceRef(
                    "cibo:native-opportunity:" + target.signal_fingerprint
                ),
            ),
            key=lambda item: item.value,
        )
    )
    synthesis_id = uuid5(
        NAMESPACE_URL,
        "qore:cibo:native-max:"
        + consultation.consultation_id
        + ":"
        + target.signal_fingerprint,
    )

    brain = CiboExecutiveBrain()
    if cognitive_episode.abstention_required:
        result = brain.synthesize(
            synthesis_id=synthesis_id,
            directive=CiboExecutiveDirectiveKind.ABSTAIN,
            reasoning_mode=CiboReasoningMode.MAX,
            subject_code="native-max-capital",
            synthesized_at=consultation.decision_at,
            evidence_refs=evidence_refs,
            uncertainty=cognitive_episode.uncertainty,
            observations=(
                "cf01-cf19-consumed",
                "native-only-intelligence",
                "full-research-semantics",
                "world-model-consumed",
                "scenarios-consumed",
                "causality-consumed",
                "metacognition-consumed",
            ),
            limitations=(
                "qore-risk-sovereign",
                "no-external-ai",
                "native-cognitive-abstention",
            ),
        )
    else:
        recommendation = CiboFormalRecommendation(
            recommendation_id=uuid5(
                NAMESPACE_URL,
                "qore:cibo:native-max:recommendation:"
                + consultation.consultation_id
                + ":"
                + target.signal_fingerprint,
            ),
            recommendation_code="evaluate-capital",
            reasoning_mode=CiboReasoningMode.MAX,
            summary=(
                "Native MAX CIBO consumed CF01-CF19, world model, scenarios, "
                "causal reasoning and metacognition without external AI; "
                "evaluate capital under CMA and QORE Risk."
            ),
            evidence_refs=evidence_refs,
            uncertainty=cognitive_episode.uncertainty,
            issued_at=consultation.decision_at,
            limitations=(
                "advisory-only",
                "qore-risk-sovereign",
                "no-external-ai",
                *(
                    ("formal-authority-evidence-pending",)
                    if blocked
                    else ()
                ),
            ),
        )
        result = brain.synthesize(
            synthesis_id=synthesis_id,
            directive=CiboExecutiveDirectiveKind.RECOMMEND,
            reasoning_mode=CiboReasoningMode.MAX,
            subject_code="native-max-capital",
            synthesized_at=consultation.decision_at,
            evidence_refs=evidence_refs,
            uncertainty=cognitive_episode.uncertainty,
            observations=(
                "cf01-cf19-consumed",
                "native-only-intelligence",
                "full-research-semantics",
                "world-model-consumed",
                "scenarios-consumed",
                "causality-consumed",
                "metacognition-consumed",
            ),
            recommendation=recommendation,
            limitations=(
                "qore-risk-sovereign",
                "no-external-ai",
                *(
                    ("formal-authority-evidence-pending",)
                    if blocked
                    else ()
                ),
            ),
        )

    if not isinstance(result, Success):
        raise CiboCapitalManagementError(
            "native maximum intelligence Executive Brain synthesis failed closed"
        )

    return CiboNativeMaximumIntelligenceResult(
        synthesis=result.value,
        consultation_id=consultation.consultation_id,
        semantic_digest=semantic_digest,
        cognitive_episode=cognitive_episode,
        applicable_faculty_count=applicable,
        successful_faculty_count=successful,
        not_applicable_faculty_count=not_applicable,
        blocked_function_codes=blocked,
        perception_key_counts=perception_counts,
    )
