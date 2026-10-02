"""Governance for causal sensor admission in Shared Active Perception.

Active perception may ask for new evidence, but a requested source is not
automatically admissible. This module separates *information desire* from
*scientific sensor admission*.

The contract is deliberately outcome-free. It validates provenance, time
semantics, replayability and missingness before a sensor can enter an offline
research experiment. It has no trading, sizing, Risk or execution authority.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from enum import StrEnum


class ActivePerceptionSensorFamily(StrEnum):
    MARKET_MICROSTRUCTURE = "MARKET_MICROSTRUCTURE"
    VOLATILITY_OPTIONALITY = "VOLATILITY_OPTIONALITY"
    RATES_DOLLAR_MACRO = "RATES_DOLLAR_MACRO"
    EQUITY_LEADERSHIP_BREADTH = "EQUITY_LEADERSHIP_BREADTH"
    PROVIDER_OBSERVATION_QUALITY = "PROVIDER_OBSERVATION_QUALITY"


class SensorObservationKind(StrEnum):
    DIRECT_OBSERVATION = "DIRECT_OBSERVATION"
    PROVIDER_DERIVED_OBSERVATION = "PROVIDER_DERIVED_OBSERVATION"
    SHARED_DERIVED_FEATURE = "SHARED_DERIVED_FEATURE"


class SensorTimestampSemantics(StrEnum):
    EVENT_TIME = "EVENT_TIME"
    CLOSE_TIME = "CLOSE_TIME"
    SNAPSHOT_AS_OF = "SNAPSHOT_AS_OF"


class SensorMissingnessSemantics(StrEnum):
    EXPLICIT_MISSING = "EXPLICIT_MISSING"
    LAST_OBSERVATION_AS_OF = "LAST_OBSERVATION_AS_OF"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class SensorAdmissionStatus(StrEnum):
    ADMITTED_FOR_R8_RESEARCH = "ADMITTED_FOR_R8_RESEARCH"
    REJECTED = "REJECTED"


@dataclass(frozen=True, slots=True)
class ActivePerceptionSensorContract:
    sensor_key: str
    family: ActivePerceptionSensorFamily
    observation_kind: SensorObservationKind
    provider_or_source_id: str
    economic_or_market_scope: str
    timestamp_semantics: SensorTimestampSemantics
    missingness_semantics: SensorMissingnessSemantics
    retained_evidence: bool
    deterministic_replay: bool
    exact_provenance: bool
    timezone_aware: bool
    causal_as_of_available: bool
    future_backfill_visible_at_runtime: bool
    provider_revision_policy_known: bool
    runtime_equivalent_source_available: bool
    inferred_from_same_closed_sensor_universe: bool = False
    trader_identity_used: bool = False
    setup_identity_used: bool = False
    pnl_used: bool = False
    outcome_used: bool = False
    methodology_authority: bool = False
    knowledge_promotion_authority: bool = False
    sizing_authority: bool = False
    risk_authority: bool = False
    order_authority: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        if not self.sensor_key.strip():
            raise ValueError("sensor_key must be non-empty")
        if not self.provider_or_source_id.strip():
            raise ValueError("provider_or_source_id must be non-empty")
        if not self.economic_or_market_scope.strip():
            raise ValueError("economic_or_market_scope must be non-empty")
        if (
            self.trader_identity_used
            or self.setup_identity_used
            or self.pnl_used
            or self.outcome_used
            or self.methodology_authority
            or self.knowledge_promotion_authority
            or self.sizing_authority
            or self.risk_authority
            or self.order_authority
            or self.execution_authority
        ):
            raise ValueError(
                "active-perception sensor contract carries forbidden evidence "
                "or sovereign authority"
            )


@dataclass(frozen=True, slots=True)
class SensorAdmissionDecision:
    sensor_key: str
    status: SensorAdmissionStatus
    reasons: tuple[str, ...]
    contract_fingerprint_sha256: str
    r8_research_only: bool = True
    r6_r5_consumed_for_selection: bool = False
    fresh_holdout_opened: bool = False
    methodology_authority: bool = False
    sizing_authority: bool = False
    risk_authority: bool = False
    order_authority: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        if len(self.contract_fingerprint_sha256) != 64:
            raise ValueError("sensor contract fingerprint must be sha256 hex")
        if self.r6_r5_consumed_for_selection or self.fresh_holdout_opened:
            raise ValueError("sensor admission may not consume holdouts")
        if (
            self.methodology_authority
            or self.sizing_authority
            or self.risk_authority
            or self.order_authority
            or self.execution_authority
        ):
            raise ValueError("sensor admission cannot carry trading authority")


def active_perception_sensor_fingerprint(
    contract: ActivePerceptionSensorContract,
) -> str:
    payload = asdict(contract)
    payload["family"] = contract.family.value
    payload["observation_kind"] = contract.observation_kind.value
    payload["timestamp_semantics"] = contract.timestamp_semantics.value
    payload["missingness_semantics"] = contract.missingness_semantics.value
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def admit_active_perception_sensor(
    contract: ActivePerceptionSensorContract,
) -> SensorAdmissionDecision:
    """Fail closed unless a requested sensor can be replayed causally."""

    reasons: list[str] = []

    if not contract.retained_evidence:
        reasons.append("NO_RETAINED_EVIDENCE")
    if not contract.deterministic_replay:
        reasons.append("NON_DETERMINISTIC_REPLAY")
    if not contract.exact_provenance:
        reasons.append("PROVENANCE_INCOMPLETE")
    if not contract.timezone_aware:
        reasons.append("TIMESTAMP_NOT_TIMEZONE_AWARE")
    if not contract.causal_as_of_available:
        reasons.append("NO_CAUSAL_AS_OF_VIEW")
    if contract.future_backfill_visible_at_runtime:
        reasons.append("FUTURE_BACKFILL_LEAKAGE_RISK")
    if not contract.provider_revision_policy_known:
        reasons.append("REVISION_POLICY_UNKNOWN")
    if not contract.runtime_equivalent_source_available:
        reasons.append("NO_RUNTIME_EQUIVALENT_SOURCE")
    if contract.inferred_from_same_closed_sensor_universe:
        reasons.append("NOT_A_GENUINELY_NEW_OBSERVATION")

    if (
        contract.family
        is ActivePerceptionSensorFamily.MARKET_MICROSTRUCTURE
        and contract.observation_kind
        is SensorObservationKind.SHARED_DERIVED_FEATURE
    ):
        reasons.append("MICROSTRUCTURE_CANNOT_BE_FABRICATED_FROM_OHLC")

    status = (
        SensorAdmissionStatus.ADMITTED_FOR_R8_RESEARCH
        if not reasons
        else SensorAdmissionStatus.REJECTED
    )
    return SensorAdmissionDecision(
        sensor_key=contract.sensor_key,
        status=status,
        reasons=tuple(reasons) if reasons else ("CAUSAL_SENSOR_CONTRACT_PASS",),
        contract_fingerprint_sha256=active_perception_sensor_fingerprint(
            contract
        ),
    )
