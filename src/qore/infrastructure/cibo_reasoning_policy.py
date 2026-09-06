from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from qore.kernel.errors import InfrastructureError
from qore.modules.cibo.cognitive_contracts import CiboReasoningMode

_TERRA_MODEL = "gpt-5.6-terra"
_SOL_MODEL = "gpt-5.6-sol"


class CiboReasoningPolicyError(InfrastructureError):
    """A reasoning-routing situation violated the governed policy contract."""

    __slots__ = ()


class CiboReasoningMateriality(StrEnum):
    """Economic/operational consequence of the current reasoning episode."""

    ROUTINE = "routine"
    MODERATE = "moderate"
    MATERIAL = "material"
    CRITICAL = "critical"


class CiboReasoningUncertainty(StrEnum):
    """Typed uncertainty signal used by the router instead of prompt heuristics."""

    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class CiboReasoningEvidenceQuality(StrEnum):
    """Quality/completeness of evidence admitted to the current episode."""

    STRONG = "strong"
    LIMITED = "limited"
    DEGRADED = "degraded"


class CiboReasoningEpisodeState(StrEnum):
    """Explicit lifecycle signal used to guarantee de-escalation."""

    NORMAL = "normal"
    ACTIVE = "active"
    RESOLVED = "resolved"


class CiboReasoningRouteTier(StrEnum):
    """Provider/model route, separate from CIBO semantic reasoning mode."""

    TERRA_MEDIUM = "terra-medium"
    TERRA_HIGH = "terra-high"
    SOL_HIGH = "sol-high"
    SOL_MAX = "sol-max"
    COUNCIL_ADVERSARIAL = "council-adversarial"


@dataclass(frozen=True, slots=True)
class CiboReasoningRoute:
    """Exact auditable model/effort decision for one reasoning episode."""

    tier: CiboReasoningRouteTier
    semantic_mode: CiboReasoningMode
    model: str
    provider_reasoning_effort: str
    routing_reason: str

    def __post_init__(self) -> None:
        if type(self.tier) is not CiboReasoningRouteTier:
            raise CiboReasoningPolicyError(
                "route tier must be exact CiboReasoningRouteTier"
            )
        if type(self.semantic_mode) is not CiboReasoningMode:
            raise CiboReasoningPolicyError(
                "semantic_mode must be exact CiboReasoningMode"
            )
        if type(self.model) is not str:
            raise CiboReasoningPolicyError("model must be exact str")
        if type(self.provider_reasoning_effort) is not str:
            raise CiboReasoningPolicyError(
                "provider_reasoning_effort must be exact str"
            )
        if type(self.routing_reason) is not str or not self.routing_reason:
            raise CiboReasoningPolicyError(
                "routing_reason must be non-empty exact str"
            )

        expected = {
            CiboReasoningRouteTier.TERRA_MEDIUM: (
                CiboReasoningMode.FAST,
                _TERRA_MODEL,
                "medium",
            ),
            CiboReasoningRouteTier.TERRA_HIGH: (
                CiboReasoningMode.HIGH,
                _TERRA_MODEL,
                "high",
            ),
            CiboReasoningRouteTier.SOL_HIGH: (
                CiboReasoningMode.HIGH,
                _SOL_MODEL,
                "high",
            ),
            CiboReasoningRouteTier.SOL_MAX: (
                CiboReasoningMode.MAX,
                _SOL_MODEL,
                "max",
            ),
            CiboReasoningRouteTier.COUNCIL_ADVERSARIAL: (
                CiboReasoningMode.COUNCIL_ADVERSARIAL,
                _SOL_MODEL,
                "max",
            ),
        }[self.tier]
        actual = (
            self.semantic_mode,
            self.model,
            self.provider_reasoning_effort,
        )
        if actual != expected:
            raise CiboReasoningPolicyError(
                "route tier/model/effort/semantic_mode combination is not governed"
            )


@dataclass(frozen=True, slots=True)
class CiboReasoningSituation:
    """Typed signals used to route CIBO without natural-language keyword heuristics."""

    materiality: CiboReasoningMateriality = CiboReasoningMateriality.ROUTINE
    uncertainty: CiboReasoningUncertainty = CiboReasoningUncertainty.LOW
    evidence_quality: CiboReasoningEvidenceQuality = CiboReasoningEvidenceQuality.STRONG
    episode_state: CiboReasoningEpisodeState = CiboReasoningEpisodeState.NORMAL
    direct_contradiction: bool = False
    material_trader_disagreement: bool = False
    unresolved_after_ordinary_analysis: bool = False
    serious_controversy: bool = False
    adversarial_council: bool = False
    degraded_state: bool = False
    deeper_analysis_requested: bool = False
    voice_channel: bool = False

    def __post_init__(self) -> None:
        if type(self.materiality) is not CiboReasoningMateriality:
            raise CiboReasoningPolicyError(
                "materiality must be exact CiboReasoningMateriality"
            )
        if type(self.uncertainty) is not CiboReasoningUncertainty:
            raise CiboReasoningPolicyError(
                "uncertainty must be exact CiboReasoningUncertainty"
            )
        if type(self.evidence_quality) is not CiboReasoningEvidenceQuality:
            raise CiboReasoningPolicyError(
                "evidence_quality must be exact CiboReasoningEvidenceQuality"
            )
        if type(self.episode_state) is not CiboReasoningEpisodeState:
            raise CiboReasoningPolicyError(
                "episode_state must be exact CiboReasoningEpisodeState"
            )
        for field_name in (
            "direct_contradiction",
            "material_trader_disagreement",
            "unresolved_after_ordinary_analysis",
            "serious_controversy",
            "adversarial_council",
            "degraded_state",
            "deeper_analysis_requested",
            "voice_channel",
        ):
            if type(getattr(self, field_name)) is not bool:
                raise CiboReasoningPolicyError(f"{field_name} must be exact bool")

        if self.adversarial_council and not (
            self.material_trader_disagreement
            and self.unresolved_after_ordinary_analysis
        ):
            raise CiboReasoningPolicyError(
                "adversarial council requires unresolved material Trader disagreement"
            )
        if self.episode_state is CiboReasoningEpisodeState.RESOLVED and any(
            (
                self.direct_contradiction,
                self.material_trader_disagreement,
                self.unresolved_after_ordinary_analysis,
                self.serious_controversy,
                self.adversarial_council,
                self.degraded_state,
            )
        ):
            raise CiboReasoningPolicyError(
                "resolved episode cannot retain active escalation signals"
            )


def _route(
    tier: CiboReasoningRouteTier,
    *,
    reason: str,
) -> CiboReasoningRoute:
    mapping = {
        CiboReasoningRouteTier.TERRA_MEDIUM: (
            CiboReasoningMode.FAST,
            _TERRA_MODEL,
            "medium",
        ),
        CiboReasoningRouteTier.TERRA_HIGH: (
            CiboReasoningMode.HIGH,
            _TERRA_MODEL,
            "high",
        ),
        CiboReasoningRouteTier.SOL_HIGH: (
            CiboReasoningMode.HIGH,
            _SOL_MODEL,
            "high",
        ),
        CiboReasoningRouteTier.SOL_MAX: (
            CiboReasoningMode.MAX,
            _SOL_MODEL,
            "max",
        ),
        CiboReasoningRouteTier.COUNCIL_ADVERSARIAL: (
            CiboReasoningMode.COUNCIL_ADVERSARIAL,
            _SOL_MODEL,
            "max",
        ),
    }
    semantic_mode, model, effort = mapping[tier]
    return CiboReasoningRoute(
        tier=tier,
        semantic_mode=semantic_mode,
        model=model,
        provider_reasoning_effort=effort,
        routing_reason=reason,
    )


def select_cibo_reasoning_route(
    situation: CiboReasoningSituation,
) -> CiboReasoningRoute:
    """Select the minimum sufficient governed route from typed situational signals."""
    if type(situation) is not CiboReasoningSituation:
        raise CiboReasoningPolicyError(
            "reasoning situation must be exact CiboReasoningSituation"
        )
    situation.__post_init__()

    if situation.episode_state is CiboReasoningEpisodeState.RESOLVED:
        return _route(
            CiboReasoningRouteTier.TERRA_MEDIUM,
            reason="episode-resolved-deescalation",
        )

    if situation.adversarial_council:
        return _route(
            CiboReasoningRouteTier.COUNCIL_ADVERSARIAL,
            reason="unresolved-material-multi-trader-disagreement",
        )

    if situation.serious_controversy or (
        situation.materiality is CiboReasoningMateriality.CRITICAL
        and situation.uncertainty is CiboReasoningUncertainty.HIGH
    ):
        return _route(
            CiboReasoningRouteTier.SOL_MAX,
            reason="critical-material-uncertainty-or-serious-controversy",
        )

    if (
        situation.materiality
        in (CiboReasoningMateriality.MATERIAL, CiboReasoningMateriality.CRITICAL)
        or situation.direct_contradiction
        or situation.material_trader_disagreement
        or situation.degraded_state
    ):
        return _route(
            CiboReasoningRouteTier.SOL_HIGH,
            reason="material-analysis-or-contradiction",
        )

    if (
        situation.materiality is CiboReasoningMateriality.MODERATE
        or situation.uncertainty
        in (CiboReasoningUncertainty.MODERATE, CiboReasoningUncertainty.HIGH)
        or situation.evidence_quality
        in (CiboReasoningEvidenceQuality.LIMITED, CiboReasoningEvidenceQuality.DEGRADED)
        or situation.deeper_analysis_requested
    ):
        return _route(
            CiboReasoningRouteTier.TERRA_HIGH,
            reason="bounded-elevated-analysis",
        )

    return _route(
        CiboReasoningRouteTier.TERRA_MEDIUM,
        reason="routine-sufficient-evidence",
    )


def select_cibo_reasoning_mode(
    situation: CiboReasoningSituation,
) -> CiboReasoningMode:
    """Compatibility projection of the richer route into the CIBO semantic mode."""
    return select_cibo_reasoning_route(situation).semantic_mode
