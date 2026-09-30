"""WP-06 / MC-17 Market Agency Model research engine.

The engine emits source-time behavioral mechanism hypotheses. It never claims
known actor identity and carries no Trader, Risk, capital or execution authority.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from enum import StrEnum

from qore.infrastructure.core_stack_v2.shared_global_opportunity_discovery import (
    SharedOpportunitySourceObservation,
)
from qore.infrastructure.core_stack_v2.shared_trader_intelligence import (
    SharedTraderIntelligenceValidationError,
)


class SharedAgencyMechanism(StrEnum):
    LIQUIDITY_SEEKING = "LIQUIDITY_SEEKING"
    FORCED_LIQUIDATION = "FORCED_LIQUIDATION"
    MOMENTUM_CHASING = "MOMENTUM_CHASING"
    INVENTORY_ADJUSTMENT = "INVENTORY_ADJUSTMENT"
    PASSIVE_ABSORPTION = "PASSIVE_ABSORPTION"
    ARBITRAGE_REBALANCING = "ARBITRAGE_REBALANCING"
    RISK_OFF_TRANSITION = "RISK_OFF_TRANSITION"


@dataclass(frozen=True, slots=True)
class SharedAgencyHypothesis:
    mechanism: SharedAgencyMechanism
    support_bps: int
    contradiction_bps: int
    uncertainty_bps: int
    evidence_refs: tuple[str, ...]
    actor_identity_claimed: bool = False
    calibrated_probability_claimed: bool = False

    def __post_init__(self) -> None:
        for name in ("support_bps", "contradiction_bps", "uncertainty_bps"):
            value = getattr(self, name)
            if type(value) is not int or not 0 <= value <= 10_000:
                raise SharedTraderIntelligenceValidationError(
                    f"{name} must be int within 0..10000"
                )
        if (
            not self.evidence_refs
            or self.evidence_refs != tuple(sorted(set(self.evidence_refs)))
        ):
            raise SharedTraderIntelligenceValidationError(
                "agency evidence_refs must be non-empty, unique and canonical"
            )
        if self.actor_identity_claimed:
            raise SharedTraderIntelligenceValidationError(
                "Market Agency may infer mechanisms, never actor identity"
            )
        if self.calibrated_probability_claimed:
            raise SharedTraderIntelligenceValidationError(
                "uncalibrated agency support cannot masquerade as probability"
            )


@dataclass(frozen=True, slots=True)
class SharedMarketAgencyAssessment:
    asset: str
    as_of_iso: str
    dominant_mechanism: SharedAgencyMechanism | None
    hypotheses: tuple[SharedAgencyHypothesis, ...]
    data_integrity_bps: int
    insufficient: bool
    source_only: bool = True
    trader_methodology_used: bool = False
    creates_trader_setup: bool = False
    execution_authority: bool = False
    risk_authority: bool = False
    sizing_authority: bool = False
    capital_authority: bool = False

    def __post_init__(self) -> None:
        if not self.asset.strip() or not self.as_of_iso.strip():
            raise SharedTraderIntelligenceValidationError(
                "agency assessment requires asset and timestamp"
            )
        if type(self.data_integrity_bps) is not int or not 0 <= self.data_integrity_bps <= 10_000:
            raise SharedTraderIntelligenceValidationError(
                "data_integrity_bps must be int within 0..10000"
            )
        mechanisms = tuple(item.mechanism for item in self.hypotheses)
        if mechanisms != tuple(SharedAgencyMechanism):
            raise SharedTraderIntelligenceValidationError(
                "agency hypotheses must preserve canonical mechanism order"
            )
        if self.insufficient and self.dominant_mechanism is not None:
            raise SharedTraderIntelligenceValidationError(
                "insufficient agency state cannot claim a dominant mechanism"
            )
        if (
            not self.source_only
            or self.trader_methodology_used
            or self.creates_trader_setup
            or self.execution_authority
            or self.risk_authority
            or self.sizing_authority
            or self.capital_authority
        ):
            raise SharedTraderIntelligenceValidationError(
                "Market Agency research cannot carry sovereign authority"
            )

    def fingerprint(self) -> str:
        payload = asdict(self)
        payload["dominant_mechanism"] = (
            None if self.dominant_mechanism is None else self.dominant_mechanism.value
        )
        for row in payload["hypotheses"]:
            row["mechanism"] = str(row["mechanism"])
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode()).hexdigest()


def _avg(*values: int) -> int:
    return sum(values) // len(values)


def _hypothesis(
    mechanism: SharedAgencyMechanism,
    *,
    support: int,
    contradiction: int,
    uncertainty: int,
    observation: SharedOpportunitySourceObservation,
) -> SharedAgencyHypothesis:
    return SharedAgencyHypothesis(
        mechanism=mechanism,
        support_bps=max(0, min(10_000, support)),
        contradiction_bps=max(0, min(10_000, contradiction)),
        uncertainty_bps=max(0, min(10_000, uncertainty)),
        evidence_refs=tuple(
            sorted(
                set(
                    observation.provenance_refs
                    + (
                        f"agency-mechanism:{mechanism.value}",
                        "wp06-source-time-mechanism-hypothesis",
                    )
                )
            )
        ),
    )


def assess_market_agency(
    observation: SharedOpportunitySourceObservation,
    *,
    minimum_integrity_bps: int = 9_500,
) -> SharedMarketAgencyAssessment:
    if type(minimum_integrity_bps) is not int or not 0 <= minimum_integrity_bps <= 10_000:
        raise SharedTraderIntelligenceValidationError(
            "minimum_integrity_bps must be int within 0..10000"
        )

    common_uncertainty = _avg(
        10_000 - observation.data_integrity_bps,
        observation.anomaly_bps,
        observation.regime_transition_bps,
    )

    supports = {
        SharedAgencyMechanism.LIQUIDITY_SEEKING: _avg(
            observation.liquidity_vacuum_bps,
            observation.displacement_bps,
            observation.failed_auction_bps,
        ),
        SharedAgencyMechanism.FORCED_LIQUIDATION: _avg(
            observation.liquidity_vacuum_bps,
            observation.displacement_bps,
            observation.structural_fragility_bps,
            observation.regime_transition_bps,
        ),
        SharedAgencyMechanism.MOMENTUM_CHASING: _avg(
            observation.displacement_bps,
            observation.acceptance_bps,
            observation.momentum_persistence_bps,
            observation.leader_confirmation_bps,
        ),
        SharedAgencyMechanism.INVENTORY_ADJUSTMENT: _avg(
            observation.absorption_bps,
            observation.failed_auction_bps,
            observation.momentum_decay_bps,
            10_000 - observation.displacement_bps,
        ),
        SharedAgencyMechanism.PASSIVE_ABSORPTION: _avg(
            observation.absorption_bps,
            observation.compression_bps,
            observation.failed_auction_bps,
            10_000 - observation.liquidity_vacuum_bps,
        ),
        SharedAgencyMechanism.ARBITRAGE_REBALANCING: _avg(
            observation.leader_divergence_bps,
            observation.acceptance_bps,
            observation.regime_transition_bps,
            observation.anomaly_bps,
        ),
        SharedAgencyMechanism.RISK_OFF_TRANSITION: _avg(
            observation.structural_fragility_bps,
            observation.leader_divergence_bps,
            observation.regime_transition_bps,
            observation.anomaly_bps,
        ),
    }

    contradictions = {
        SharedAgencyMechanism.LIQUIDITY_SEEKING: observation.acceptance_bps,
        SharedAgencyMechanism.FORCED_LIQUIDATION: observation.world_support_bps
        if hasattr(observation, "world_support_bps")
        else observation.leader_confirmation_bps,
        SharedAgencyMechanism.MOMENTUM_CHASING: observation.momentum_decay_bps,
        SharedAgencyMechanism.INVENTORY_ADJUSTMENT: observation.momentum_persistence_bps,
        SharedAgencyMechanism.PASSIVE_ABSORPTION: observation.displacement_bps,
        SharedAgencyMechanism.ARBITRAGE_REBALANCING: observation.leader_confirmation_bps,
        SharedAgencyMechanism.RISK_OFF_TRANSITION: observation.leader_confirmation_bps,
    }

    hypotheses = tuple(
        _hypothesis(
            mechanism,
            support=supports[mechanism],
            contradiction=contradictions[mechanism],
            uncertainty=common_uncertainty,
            observation=observation,
        )
        for mechanism in SharedAgencyMechanism
    )

    if observation.data_integrity_bps < minimum_integrity_bps:
        dominant = None
        insufficient = True
    else:
        dominant = max(
            hypotheses,
            key=lambda row: (
                row.support_bps - row.contradiction_bps,
                row.support_bps,
                row.mechanism.value,
            ),
        ).mechanism
        insufficient = False

    return SharedMarketAgencyAssessment(
        asset=observation.asset,
        as_of_iso=observation.as_of.isoformat(),
        dominant_mechanism=dominant,
        hypotheses=hypotheses,
        data_integrity_bps=observation.data_integrity_bps,
        insufficient=insufficient,
    )
