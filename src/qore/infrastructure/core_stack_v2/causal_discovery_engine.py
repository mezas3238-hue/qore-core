"""WP-03 Causal Discovery Engine for Shared Brain.

This module discovers *candidate* structural relations between generic market
concepts. It is deliberately stricter than correlation mining:

- source observations must precede target observations;
- raw association is separated from confounder-conditioned contrast;
- regime stability is explicit;
- independent replication partitions are explicit;
- intervention-like evidence is tracked when available;
- matched/model counterfactual evidence is tracked when available;
- contradictory evidence can falsify a candidate.

Even a replicated result remains RESEARCH_REPLICATED. This module has no
authority to mutate certified knowledge, trader methodology, Risk, sizing,
orders or execution.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from qore.infrastructure.core_stack_v2.dynamic_causal_graph import (
    CausalConcept,
)


class CausalDiscoveryStatus(StrEnum):
    INSUFFICIENT = "INSUFFICIENT"
    ASSOCIATION_ONLY = "ASSOCIATION_ONLY"
    RESEARCH_CANDIDATE = "RESEARCH_CANDIDATE"
    RESEARCH_REPLICATED = "RESEARCH_REPLICATED"
    FALSIFIED = "FALSIFIED"


class CausalEffectDirection(StrEnum):
    SUPPORTS = "SUPPORTS"
    SUPPRESSES = "SUPPRESSES"
    UNRESOLVED = "UNRESOLVED"


@dataclass(frozen=True, slots=True)
class CausalDiscoveryEpisode:
    source: CausalConcept
    target: CausalConcept
    source_at: datetime
    target_at: datetime
    source_state_bps: int
    target_state_bps: int
    confounder_key: str
    regime_key: str
    replication_partition: str
    integrity_bps: int = 10_000
    natural_intervention: bool = False
    counterfactual_target_without_source_bps: int | None = None

    def __post_init__(self) -> None:
        if self.source is self.target:
            raise ValueError("causal discovery relation cannot self-reference")
        for name in ("source_at", "target_at"):
            value = getattr(self, name)
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError(f"{name} must be timezone-aware")
        for name in (
            "source_state_bps",
            "target_state_bps",
            "integrity_bps",
        ):
            value = int(getattr(self, name))
            if not 0 <= value <= 10_000:
                raise ValueError(f"{name} must be within 0..10000")
        if self.counterfactual_target_without_source_bps is not None:
            if not 0 <= self.counterfactual_target_without_source_bps <= 10_000:
                raise ValueError(
                    "counterfactual_target_without_source_bps "
                    "must be within 0..10000"
                )
        if not self.confounder_key:
            raise ValueError("confounder_key must be non-empty")
        if not self.regime_key:
            raise ValueError("regime_key must be non-empty")
        if not self.replication_partition:
            raise ValueError("replication_partition must be non-empty")


@dataclass(frozen=True, slots=True)
class CausalDiscoveryPolicy:
    exposed_threshold_bps: int = 6_500
    control_threshold_bps: int = 3_500
    minimum_effect_bps: int = 500
    minimum_group_count: int = 8
    minimum_stratum_group_count: int = 2
    minimum_conditional_strata: int = 2
    minimum_regimes: int = 2
    minimum_replication_partitions: int = 2
    minimum_intervention_group_count: int = 4
    minimum_counterfactual_pairs: int = 4
    minimum_integrity_bps: int = 8_000
    sign_stability_gate_bps: int = 7_500
    temporal_precedence_gate_bps: int = 10_000

    def __post_init__(self) -> None:
        for name in (
            "exposed_threshold_bps",
            "control_threshold_bps",
            "minimum_effect_bps",
            "minimum_integrity_bps",
            "sign_stability_gate_bps",
            "temporal_precedence_gate_bps",
        ):
            value = int(getattr(self, name))
            if not 0 <= value <= 10_000:
                raise ValueError(f"{name} must be within 0..10000")
        if self.control_threshold_bps >= self.exposed_threshold_bps:
            raise ValueError(
                "control threshold must be below exposed threshold"
            )
        for name in (
            "minimum_group_count",
            "minimum_stratum_group_count",
            "minimum_conditional_strata",
            "minimum_regimes",
            "minimum_replication_partitions",
            "minimum_intervention_group_count",
            "minimum_counterfactual_pairs",
        ):
            if int(getattr(self, name)) < 1:
                raise ValueError(f"{name} must be positive")


@dataclass(frozen=True, slots=True)
class CausalDiscoveryAssessment:
    source: CausalConcept
    target: CausalConcept
    as_of: datetime
    status: CausalDiscoveryStatus
    direction: CausalEffectDirection
    sample_count: int
    exposed_count: int
    control_count: int
    raw_effect_bps: int
    conditional_effect_bps: int | None
    intervention_effect_bps: int | None
    counterfactual_effect_bps: int | None
    temporal_precedence_bps: int
    conditional_sign_stability_bps: int
    cross_regime_stability_bps: int
    replication_stability_bps: int
    conditional_strata_count: int
    regime_count: int
    replication_partition_count: int
    excluded_low_integrity_count: int
    intervention_evidence_available: bool
    counterfactual_evidence_available: bool
    replicated: bool
    observational_association_only: bool
    reasons: tuple[str, ...]
    outcome_used: bool = False
    pnl_used: bool = False
    future_market_used: bool = False
    methodology_authority: bool = False
    knowledge_promotion_authority: bool = False
    sizing_authority: bool = False
    risk_authority: bool = False
    order_authority: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        if self.as_of.tzinfo is None or self.as_of.utcoffset() is None:
            raise ValueError("as_of must be timezone-aware")
        for name in (
            "temporal_precedence_bps",
            "conditional_sign_stability_bps",
            "cross_regime_stability_bps",
            "replication_stability_bps",
        ):
            value = int(getattr(self, name))
            if not 0 <= value <= 10_000:
                raise ValueError(f"{name} must be within 0..10000")
        for name in (
            "raw_effect_bps",
            "conditional_effect_bps",
            "intervention_effect_bps",
            "counterfactual_effect_bps",
        ):
            value = getattr(self, name)
            if value is not None and not -10_000 <= int(value) <= 10_000:
                raise ValueError(f"{name} must be within -10000..10000")
        for name in (
            "sample_count",
            "exposed_count",
            "control_count",
            "conditional_strata_count",
            "regime_count",
            "replication_partition_count",
            "excluded_low_integrity_count",
        ):
            if int(getattr(self, name)) < 0:
                raise ValueError(f"{name} cannot be negative")
        if (
            self.outcome_used
            or self.pnl_used
            or self.future_market_used
            or self.methodology_authority
            or self.knowledge_promotion_authority
            or self.sizing_authority
            or self.risk_authority
            or self.order_authority
            or self.execution_authority
        ):
            raise ValueError(
                "causal discovery cannot consume outcomes or carry authority"
            )


def _mean(values: list[int]) -> int:
    if not values:
        raise ValueError("mean requires at least one value")
    return sum(values) // len(values)


def _signed_effect(
    episodes: list[CausalDiscoveryEpisode],
    policy: CausalDiscoveryPolicy,
) -> tuple[int | None, int, int]:
    exposed = [
        item.target_state_bps
        for item in episodes
        if item.source_state_bps >= policy.exposed_threshold_bps
    ]
    control = [
        item.target_state_bps
        for item in episodes
        if item.source_state_bps <= policy.control_threshold_bps
    ]
    if (
        len(exposed) < policy.minimum_group_count
        or len(control) < policy.minimum_group_count
    ):
        return None, len(exposed), len(control)
    return _mean(exposed) - _mean(control), len(exposed), len(control)


def _direction(
    effect_bps: int | None,
    minimum_effect_bps: int,
) -> CausalEffectDirection:
    if effect_bps is None or abs(effect_bps) < minimum_effect_bps:
        return CausalEffectDirection.UNRESOLVED
    if effect_bps > 0:
        return CausalEffectDirection.SUPPORTS
    return CausalEffectDirection.SUPPRESSES


def _same_sign(left: int, right: int) -> bool:
    return (left > 0 and right > 0) or (left < 0 and right < 0)


def _stability_bps(
    effects: list[int],
    reference_effect: int,
    minimum_effect_bps: int,
) -> int:
    """Measure support across every eligible stratum, regime or partition.

    Near-zero effects are evidence that the relation is not stable there.
    Excluding them from the denominator can manufacture 100% stability from
    one strong slice while the remaining slices carry no material effect.
    """
    if not effects:
        return 0
    consistent = sum(
        abs(effect) >= minimum_effect_bps
        and _same_sign(effect, reference_effect)
        for effect in effects
    )
    return consistent * 10_000 // len(effects)


def _conditioned_effects(
    episodes: tuple[CausalDiscoveryEpisode, ...],
    *,
    key_name: str,
    policy: CausalDiscoveryPolicy,
) -> tuple[list[int], int]:
    grouped: dict[str, list[CausalDiscoveryEpisode]] = {}
    for item in episodes:
        key = str(getattr(item, key_name))
        grouped.setdefault(key, []).append(item)

    effects: list[int] = []
    weighted_numerator = 0
    weighted_denominator = 0
    for rows in grouped.values():
        exposed = [
            item.target_state_bps
            for item in rows
            if item.source_state_bps >= policy.exposed_threshold_bps
        ]
        control = [
            item.target_state_bps
            for item in rows
            if item.source_state_bps <= policy.control_threshold_bps
        ]
        if (
            len(exposed) < policy.minimum_stratum_group_count
            or len(control) < policy.minimum_stratum_group_count
        ):
            continue
        effect = _mean(exposed) - _mean(control)
        weight = len(exposed) + len(control)
        effects.append(effect)
        weighted_numerator += effect * weight
        weighted_denominator += weight

    aggregate = (
        0
        if weighted_denominator == 0
        else weighted_numerator // weighted_denominator
    )
    return effects, aggregate


def _intervention_effect(
    episodes: tuple[CausalDiscoveryEpisode, ...],
    policy: CausalDiscoveryPolicy,
) -> int | None:
    intervention = [
        item for item in episodes if item.natural_intervention
    ]
    exposed = [
        item.target_state_bps
        for item in intervention
        if item.source_state_bps >= policy.exposed_threshold_bps
    ]
    control = [
        item.target_state_bps
        for item in intervention
        if item.source_state_bps <= policy.control_threshold_bps
    ]
    if (
        len(exposed) < policy.minimum_intervention_group_count
        or len(control) < policy.minimum_intervention_group_count
    ):
        return None
    return _mean(exposed) - _mean(control)


def _counterfactual_effect(
    episodes: tuple[CausalDiscoveryEpisode, ...],
    policy: CausalDiscoveryPolicy,
) -> int | None:
    differences = [
        item.target_state_bps
        - cast_counterfactual(item.counterfactual_target_without_source_bps)
        for item in episodes
        if (
            item.source_state_bps >= policy.exposed_threshold_bps
            and item.counterfactual_target_without_source_bps is not None
        )
    ]
    if len(differences) < policy.minimum_counterfactual_pairs:
        return None
    return _mean(differences)


def cast_counterfactual(value: int | None) -> int:
    if value is None:
        raise ValueError("counterfactual value is missing")
    return value


def discover_causal_relation(
    *,
    as_of: datetime,
    episodes: tuple[CausalDiscoveryEpisode, ...],
    policy: CausalDiscoveryPolicy | None = None,
) -> CausalDiscoveryAssessment:
    """Discover one research-only causal relation from bounded episodes."""

    if as_of.tzinfo is None or as_of.utcoffset() is None:
        raise ValueError("as_of must be timezone-aware")
    if not episodes:
        raise ValueError("causal discovery requires episodes")

    effective = policy or CausalDiscoveryPolicy()
    source = episodes[0].source
    target = episodes[0].target
    if any(item.source is not source or item.target is not target for item in episodes):
        raise ValueError("all discovery episodes must describe one relation")
    if any(item.target_at > as_of or item.source_at > as_of for item in episodes):
        raise ValueError("future causal-discovery evidence is forbidden")

    usable = tuple(
        item
        for item in episodes
        if item.integrity_bps >= effective.minimum_integrity_bps
    )
    excluded_low_integrity_count = len(episodes) - len(usable)
    if not usable:
        raise ValueError("no causal-discovery evidence meets integrity gate")

    temporal_hits = sum(item.source_at < item.target_at for item in usable)
    temporal_precedence_bps = temporal_hits * 10_000 // len(usable)

    raw_effect, exposed_count, control_count = _signed_effect(
        list(usable),
        effective,
    )
    raw_direction = _direction(raw_effect, effective.minimum_effect_bps)

    conditional_effects, conditional_effect = _conditioned_effects(
        usable,
        key_name="confounder_key",
        policy=effective,
    )
    regime_effects, _ = _conditioned_effects(
        usable,
        key_name="regime_key",
        policy=effective,
    )
    replication_effects, _ = _conditioned_effects(
        usable,
        key_name="replication_partition",
        policy=effective,
    )

    if raw_effect is None:
        conditional_stability = 0
        regime_stability = 0
        replication_stability = 0
    else:
        conditional_stability = _stability_bps(
            conditional_effects,
            raw_effect,
            effective.minimum_effect_bps,
        )
        regime_stability = _stability_bps(
            regime_effects,
            raw_effect,
            effective.minimum_effect_bps,
        )
        replication_stability = _stability_bps(
            replication_effects,
            raw_effect,
            effective.minimum_effect_bps,
        )

    intervention_effect = _intervention_effect(usable, effective)
    counterfactual_effect = _counterfactual_effect(usable, effective)

    conditional_gate = (
        raw_effect is not None
        and len(conditional_effects) >= effective.minimum_conditional_strata
        and abs(conditional_effect) >= effective.minimum_effect_bps
        and _same_sign(conditional_effect, raw_effect)
        and conditional_stability >= effective.sign_stability_gate_bps
    )
    regime_gate = (
        raw_effect is not None
        and len(regime_effects) >= effective.minimum_regimes
        and regime_stability >= effective.sign_stability_gate_bps
    )
    replication_gate = (
        raw_effect is not None
        and len(replication_effects)
        >= effective.minimum_replication_partitions
        and replication_stability >= effective.sign_stability_gate_bps
    )
    intervention_gate = (
        intervention_effect is None
        or (
            raw_effect is not None
            and abs(intervention_effect) >= effective.minimum_effect_bps
            and _same_sign(intervention_effect, raw_effect)
        )
    )
    counterfactual_gate = (
        counterfactual_effect is None
        or (
            raw_effect is not None
            and abs(counterfactual_effect) >= effective.minimum_effect_bps
            and _same_sign(counterfactual_effect, raw_effect)
        )
    )
    temporal_gate = (
        temporal_precedence_bps >= effective.temporal_precedence_gate_bps
    )

    reasons: list[str] = []
    falsified = False

    if raw_effect is None or raw_direction is CausalEffectDirection.UNRESOLVED:
        status = CausalDiscoveryStatus.INSUFFICIENT
        reasons.append("RAW_ASSOCIATION_INSUFFICIENT")
    else:
        if not temporal_gate:
            falsified = True
            reasons.append("TEMPORAL_PRECEDENCE_FAILED")
        if (
            len(conditional_effects) >= effective.minimum_conditional_strata
            and abs(conditional_effect) >= effective.minimum_effect_bps
            and not _same_sign(conditional_effect, raw_effect)
        ):
            falsified = True
            reasons.append("CONDITIONAL_EFFECT_SIGN_REVERSED")
        if (
            len(regime_effects) >= effective.minimum_regimes
            and regime_stability < effective.sign_stability_gate_bps
        ):
            falsified = True
            reasons.append("CROSS_REGIME_INSTABILITY")
        if (
            len(replication_effects)
            >= effective.minimum_replication_partitions
            and replication_stability < effective.sign_stability_gate_bps
        ):
            falsified = True
            reasons.append("REPLICATION_SIGN_INSTABILITY")
        if not intervention_gate:
            falsified = True
            reasons.append("INTERVENTION_EVIDENCE_CONTRADICTS")
        if not counterfactual_gate:
            falsified = True
            reasons.append("COUNTERFACTUAL_EVIDENCE_CONTRADICTS")

        if falsified:
            status = CausalDiscoveryStatus.FALSIFIED
        elif (
            conditional_gate
            and regime_gate
            and replication_gate
            and counterfactual_effect is not None
            and counterfactual_gate
        ):
            status = CausalDiscoveryStatus.RESEARCH_REPLICATED
            reasons.extend(
                (
                    "TEMPORAL_PRECEDENCE_PASS",
                    "CONDITIONAL_CONTRAST_PASS",
                    "CROSS_REGIME_STABILITY_PASS",
                    "INDEPENDENT_REPLICATION_PASS",
                    "COUNTERFACTUAL_CONSISTENCY_PASS",
                )
            )
        elif conditional_gate and regime_gate:
            status = CausalDiscoveryStatus.RESEARCH_CANDIDATE
            reasons.extend(
                (
                    "TEMPORAL_PRECEDENCE_PASS",
                    "CONDITIONAL_CONTRAST_PASS",
                    "CROSS_REGIME_STABILITY_PASS",
                )
            )
        else:
            status = CausalDiscoveryStatus.ASSOCIATION_ONLY
            reasons.append("OBSERVATIONAL_ASSOCIATION_NOT_CAUSAL")

    return CausalDiscoveryAssessment(
        source=source,
        target=target,
        as_of=as_of,
        status=status,
        direction=raw_direction,
        sample_count=len(usable),
        exposed_count=exposed_count,
        control_count=control_count,
        raw_effect_bps=0 if raw_effect is None else raw_effect,
        conditional_effect_bps=(
            None if not conditional_effects else conditional_effect
        ),
        intervention_effect_bps=intervention_effect,
        counterfactual_effect_bps=counterfactual_effect,
        temporal_precedence_bps=temporal_precedence_bps,
        conditional_sign_stability_bps=conditional_stability,
        cross_regime_stability_bps=regime_stability,
        replication_stability_bps=replication_stability,
        conditional_strata_count=len(conditional_effects),
        regime_count=len(regime_effects),
        replication_partition_count=len(replication_effects),
        excluded_low_integrity_count=excluded_low_integrity_count,
        intervention_evidence_available=intervention_effect is not None,
        counterfactual_evidence_available=counterfactual_effect is not None,
        replicated=status is CausalDiscoveryStatus.RESEARCH_REPLICATED,
        observational_association_only=(
            status is CausalDiscoveryStatus.ASSOCIATION_ONLY
        ),
        reasons=tuple(dict.fromkeys(reasons)),
    )
