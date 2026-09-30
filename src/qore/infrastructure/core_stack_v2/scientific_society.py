"""MC-21 Scientific Society / Ensemble of Minds governance.

This layer arbitrates scientific roles, not trading actions. It explicitly
forbids simple-majority suppression of minority falsification evidence.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from enum import StrEnum


class ScientificRole(StrEnum):
    OBSERVER = "OBSERVER"
    HYPOTHESIS_GENERATOR = "HYPOTHESIS_GENERATOR"
    CAUSAL_SCIENTIST = "CAUSAL_SCIENTIST"
    STATISTICIAN = "STATISTICIAN"
    ADVERSARIAL_CRITIC = "ADVERSARIAL_CRITIC"
    DEFENDER = "DEFENDER"
    SKEPTIC = "SKEPTIC"
    COUNTERFACTUAL_ANALYST = "COUNTERFACTUAL_ANALYST"
    REGIME_SPECIALIST = "REGIME_SPECIALIST"
    TRAJECTORY_SPECIALIST = "TRAJECTORY_SPECIALIST"
    RISK_OF_ERROR_ANALYST = "RISK_OF_ERROR_ANALYST"
    REPLICATION_SCIENTIST = "REPLICATION_SCIENTIST"


class ScientificClaim(StrEnum):
    SUPPORT = "SUPPORT"
    OPPOSE = "OPPOSE"
    FALSIFY = "FALSIFY"
    ABSTAIN = "ABSTAIN"
    INSUFFICIENT = "INSUFFICIENT"


class ScientificSocietyVerdict(StrEnum):
    REJECTED_BY_FALSIFICATION = "REJECTED_BY_FALSIFICATION"
    CONTESTED = "CONTESTED"
    RESEARCH_ONLY = "RESEARCH_ONLY"
    INSUFFICIENT = "INSUFFICIENT"


@dataclass(frozen=True, slots=True)
class ScientificContribution:
    role: ScientificRole
    claim: ScientificClaim
    confidence_bps: int
    model_family: str
    evidence_refs: tuple[str, ...]
    real_engine_bound: bool

    def __post_init__(self) -> None:
        if type(self.confidence_bps) is not int or not 0 <= self.confidence_bps <= 10_000:
            raise ValueError("scientific confidence must be int within 0..10000")
        if not self.model_family.strip():
            raise ValueError("scientific contribution needs model_family")
        if (
            not self.evidence_refs
            or self.evidence_refs != tuple(sorted(set(self.evidence_refs)))
        ):
            raise ValueError("scientific contribution evidence must be canonical")


@dataclass(frozen=True, slots=True)
class ScientificSocietyDecision:
    proposition_id: str
    verdict: ScientificSocietyVerdict
    contributions: tuple[ScientificContribution, ...]
    minority_falsification_preserved: bool
    simple_majority_voting_used: bool = False
    knowledge_promotion_authority: bool = False
    methodology_authority: bool = False
    execution_authority: bool = False
    risk_authority: bool = False
    sizing_authority: bool = False

    def __post_init__(self) -> None:
        if not self.proposition_id:
            raise ValueError("scientific proposition identity required")
        if self.contributions != tuple(
            sorted(self.contributions, key=lambda item: item.role.value)
        ):
            raise ValueError("scientific contributions must be role-canonical")
        roles = {item.role for item in self.contributions}
        if roles != set(ScientificRole):
            raise ValueError("Scientific Society requires all 12 roles")
        if self.simple_majority_voting_used:
            raise ValueError("simple majority voting is forbidden")
        if not self.minority_falsification_preserved:
            raise ValueError("minority falsification evidence must survive")
        if (
            self.knowledge_promotion_authority
            or self.methodology_authority
            or self.execution_authority
            or self.risk_authority
            or self.sizing_authority
        ):
            raise ValueError("Scientific Society cannot self-promote or trade")

    def fingerprint(self) -> str:
        payload = {
            "proposition_id": self.proposition_id,
            "verdict": self.verdict.value,
            "contributions": tuple(
                {
                    **asdict(item),
                    "role": item.role.value,
                    "claim": item.claim.value,
                }
                for item in self.contributions
            ),
            "minority_falsification_preserved": (
                self.minority_falsification_preserved
            ),
            "simple_majority_voting_used": self.simple_majority_voting_used,
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode()).hexdigest()


def arbitrate_scientific_society(
    *,
    proposition_id: str,
    contributions: tuple[ScientificContribution, ...],
) -> ScientificSocietyDecision:
    ordered = tuple(sorted(contributions, key=lambda item: item.role.value))
    roles = {item.role for item in ordered}
    if roles != set(ScientificRole):
        raise ValueError("Scientific Society requires exactly the 12 required roles")

    falsifications = [
        item for item in ordered if item.claim is ScientificClaim.FALSIFY
    ]
    material_falsifications = [
        item for item in falsifications if item.confidence_bps >= 5_000
    ]
    if material_falsifications:
        verdict = ScientificSocietyVerdict.REJECTED_BY_FALSIFICATION
    else:
        support = sum(
            item.confidence_bps
            for item in ordered
            if item.claim is ScientificClaim.SUPPORT
        )
        opposition = sum(
            item.confidence_bps
            for item in ordered
            if item.claim is ScientificClaim.OPPOSE
        )
        informative = [
            item
            for item in ordered
            if item.claim not in {
                ScientificClaim.ABSTAIN,
                ScientificClaim.INSUFFICIENT,
            }
        ]
        if not informative:
            verdict = ScientificSocietyVerdict.INSUFFICIENT
        elif opposition >= support:
            verdict = ScientificSocietyVerdict.CONTESTED
        else:
            verdict = ScientificSocietyVerdict.RESEARCH_ONLY

    return ScientificSocietyDecision(
        proposition_id=proposition_id,
        verdict=verdict,
        contributions=ordered,
        minority_falsification_preserved=True,
    )
