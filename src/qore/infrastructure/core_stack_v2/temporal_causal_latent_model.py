"""MC-14 latent temporal causal research contracts."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from enum import StrEnum


class TemporalCausalDisposition(StrEnum):
    INSUFFICIENT = "INSUFFICIENT"
    ASSOCIATION_ONLY = "ASSOCIATION_ONLY"
    RESEARCH_CANDIDATE = "RESEARCH_CANDIDATE"
    CONSUMED_TEMPORAL_REPLICATED = "CONSUMED_TEMPORAL_REPLICATED"
    FALSIFIED = "FALSIFIED"


@dataclass(frozen=True, slots=True)
class TemporalCausalLatentRelation:
    latent_concept_id: str
    target_name: str
    disposition: TemporalCausalDisposition
    discovery_effect_bps: int
    r6_effect_bps: int | None
    r5_effect_bps: int | None
    discovery_sign_stability_bps: int
    r6_sign_stability_bps: int | None
    r5_sign_stability_bps: int | None
    discovery_regime_stability_bps: int
    r6_regime_stability_bps: int | None
    r5_regime_stability_bps: int | None
    source_threshold_low_milli_z: int
    source_threshold_high_milli_z: int
    evidence_refs: tuple[str, ...]
    fresh_validation_used: bool = False
    knowledge_promotion_authority: bool = False
    methodology_authority: bool = False
    execution_authority: bool = False
    risk_authority: bool = False
    sizing_authority: bool = False

    def __post_init__(self) -> None:
        if not self.latent_concept_id.startswith("LATENT_CONCEPT_"):
            raise ValueError("MC-14 source must be a provisional latent concept")
        if not self.target_name:
            raise ValueError("MC-14 target_name must be explicit")
        if self.source_threshold_low_milli_z >= self.source_threshold_high_milli_z:
            raise ValueError("MC-14 source thresholds must be strictly ordered")
        for value in (
            self.discovery_effect_bps,
            self.r6_effect_bps,
            self.r5_effect_bps,
        ):
            if value is not None and not -10_000 <= value <= 10_000:
                raise ValueError("MC-14 effect must be within -10000..10000")
        for value in (
            self.discovery_sign_stability_bps,
            self.r6_sign_stability_bps,
            self.r5_sign_stability_bps,
            self.discovery_regime_stability_bps,
            self.r6_regime_stability_bps,
            self.r5_regime_stability_bps,
        ):
            if value is not None and not 0 <= value <= 10_000:
                raise ValueError("MC-14 stability must be within 0..10000")
        if (
            not self.evidence_refs
            or self.evidence_refs != tuple(sorted(set(self.evidence_refs)))
        ):
            raise ValueError("MC-14 evidence refs must be non-empty and canonical")
        if (
            self.knowledge_promotion_authority
            or self.methodology_authority
            or self.execution_authority
            or self.risk_authority
            or self.sizing_authority
        ):
            raise ValueError("MC-14 research relation cannot carry authority")

    def fingerprint(self) -> str:
        payload = asdict(self)
        payload["disposition"] = self.disposition.value
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode()).hexdigest()
