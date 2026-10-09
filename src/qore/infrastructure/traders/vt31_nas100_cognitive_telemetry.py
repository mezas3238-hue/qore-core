"""Read-only cognitive telemetry for VT31 NAS100.

These sensors observe causal input -> cognition -> reasoning -> position output
-> actuation. They never authorize, suppress, resize, or mutate a trade.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from qore.infrastructure.traders.vt31_nas100_causal_fact_producers import (
    MarketNativeProducerReport,
)
from qore.infrastructure.traders.vt31_nas100_post_entry_cognitive_runtime import (
    PostEntryCausalObservation,
    PostEntryCognitiveDecision,
    PostEntryMarketFacts,
)

_UNRESOLVED_TOKENS = frozenset(
    {
        "UNWIRED",
        "UNAVAILABLE",
        "UNKNOWN",
        "UNRESOLVED",
        "UNCALIBRATED",
        "NOT_EVALUATED",
    }
)
_ACTIONS_REQUIRING_ROUTE = frozenset(
    {"TRAIL", "DOL_LOCK", "BANK", "EXTEND", "EXIT", "REARM_REQUIRED"}
)


def _normalize(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(key): _normalize(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_normalize(item) for item in value]
    return value


def _unresolved_string(value: str) -> bool:
    # Multiword states such as NOT_EVALUATED must not disappear merely
    # because separators tokenize the phrase. Never use substring matches:
    # NO_CONFIRMED_EXHAUSTION is a valid negative observation, not UNKNOWN.
    normalized = re.sub(r"[^A-Z0-9]+", "_", value.upper()).strip("_")
    parts = tuple(part for part in normalized.split("_") if part)
    singles = _UNRESOLVED_TOKENS - {"NOT_EVALUATED"}
    return (
        bool(set(parts) & singles)
        or any(
            left == "NOT" and right == "EVALUATED"
            for left, right in zip(parts, parts[1:], strict=False)
        )
    )


def _input_health(
    values: dict[str, Any],
    *,
    prefix: str,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    missing: list[str] = []
    unresolved: list[str] = []
    for name, value in values.items():
        key = f"{prefix}.{name}"
        if value is None:
            missing.append(key)
        elif isinstance(value, str) and _unresolved_string(value):
            unresolved.append(key)
    return tuple(sorted(missing)), tuple(sorted(unresolved))


@dataclass(frozen=True, slots=True)
class CognitiveSensorFrame:
    """One immutable read-only view of a complete cognitive evaluation."""

    as_of: str
    input_snapshot: dict[str, Any]
    missing_inputs: tuple[str, ...]
    unresolved_inputs: tuple[str, ...]
    observed_domains: tuple[str, ...]
    actuated_situation_fields: tuple[str, ...]
    observation_only_situation_fields: tuple[str, ...]
    cognitive_coverage_ratio: str
    full_cognitive_accounting_verified: bool
    maximum_cognition_verified: bool
    maximum_intelligence_blockers: tuple[str, ...]
    entry_reasoning_action: str
    current_reasoning_action: str
    output_action: str
    output_reason: str
    output_next_stop: str | None
    output_next_target: str | None
    output_requires_actuation: bool
    native_fact_statuses: dict[str, str] = field(default_factory=dict)
    native_fact_evidence: dict[str, dict[str, Any]] = field(default_factory=dict)
    read_only: bool = True
    policy_authority: bool = False
    sizing_authority: bool = False
    terminal_outcome_authority: bool = False

    def payload(self) -> dict[str, Any]:
        return _normalize(asdict(self))

    def fingerprint(self) -> str:
        encoded = json.dumps(
            self.payload(), sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class CognitiveActuationSensor:
    """Observe whether a cognitive output is wired to an execution route."""

    expected_action: str
    routed_actions: tuple[str, ...]
    executed_actions: tuple[str, ...] | None
    status: str
    output_requires_actuation: bool
    read_only: bool = True
    policy_authority: bool = False

    def payload(self) -> dict[str, Any]:
        return _normalize(asdict(self))


def _verify_native_fact_parity(
    *,
    observation: PostEntryCausalObservation,
    market: PostEntryMarketFacts,
    producer_report: MarketNativeProducerReport | None,
) -> tuple[dict[str, str], dict[str, dict[str, Any]]]:
    """Never mark an unconnected producer as a verified False.

    When a producer has been connected, reject disagreements between its
    evidenced value and the value consumed by canonical position cognition.
    This is telemetry/parity validation only, not a separate decision policy.
    """
    names = (
        "structure_invalidated",
        "liquidity_failure_confirmed",
        "regime_changed_against_thesis",
        "next_structural_target",
    )
    if producer_report is None:
        return ({name: "UNWIRED" for name in names}, {})

    observed_at = datetime.fromisoformat(observation.as_of)
    if observed_at.tzinfo is None or observed_at.utcoffset() is None:
        raise ValueError("sensor decision timestamp must be timezone-aware")
    if producer_report.as_of != observed_at:
        raise ValueError("native producer and cognition as_of mismatch")

    statuses: dict[str, str] = {}
    evidence: dict[str, dict[str, Any]] = {}
    for name in names:
        fact = getattr(producer_report, name)
        statuses[name] = fact.status
        evidence[name] = _normalize(asdict(fact))
        if name == "next_structural_target":
            if fact.status == "AVAILABLE":
                if market.next_structural_target != fact.candidate:
                    raise ValueError("producer/runtime next target disagreement")
            elif market.next_structural_target is not None:
                raise ValueError("runtime has destination without producer proof")
        elif (
            fact.status == "OBSERVED"
            and getattr(market, name) != fact.value
        ):
            raise ValueError(f"producer/runtime {name} disagreement")
    return statuses, evidence


def capture_post_entry_cognitive_sensor(
    *,
    observation: PostEntryCausalObservation,
    market: PostEntryMarketFacts,
    decision: PostEntryCognitiveDecision,
    producer_report: MarketNativeProducerReport | None = None,
) -> CognitiveSensorFrame:
    """Capture inputs/process/output without changing the canonical decision."""

    observation_values = asdict(observation)
    market_values = asdict(market)
    missing_observation, unresolved_observation = _input_health(
        observation_values, prefix="observation"
    )
    missing_market, unresolved_market = _input_health(
        market_values, prefix="market"
    )

    native_fact_statuses, native_fact_evidence = _verify_native_fact_parity(
        observation=observation,
        market=market,
        producer_report=producer_report,
    )
    cognition = decision.cognition
    position = decision.position
    action = position.action.value
    next_stop = (
        None if position.next_stop is None else format(position.next_stop, "f")
    )
    next_target = (
        None
        if position.next_target is None
        else format(position.next_target, "f")
    )
    snapshot = {
        "observation": _normalize(observation_values),
        "market": _normalize(market_values),
        "entry_situation_fingerprint": decision.entry_situation_fingerprint,
        "current_situation_fingerprint": decision.current_situation_fingerprint,
        "current_reasoning_situation_fingerprint": (
            decision.current_reasoning_situation_fingerprint
        ),
    }
    return CognitiveSensorFrame(
        as_of=observation.as_of,
        input_snapshot=snapshot,
        missing_inputs=missing_observation + missing_market,
        unresolved_inputs=unresolved_observation + unresolved_market,
        observed_domains=tuple(cognition.observed_domains),
        actuated_situation_fields=tuple(cognition.actuated_situation_fields),
        observation_only_situation_fields=tuple(
            cognition.observation_only_situation_fields
        ),
        cognitive_coverage_ratio=format(
            cognition.cognitive_coverage_ratio, "f"
        ),
        full_cognitive_accounting_verified=(
            cognition.full_cognitive_accounting_verified
        ),
        maximum_cognition_verified=cognition.maximum_cognition_verified,
        maximum_intelligence_blockers=tuple(
            cognition.reasoning_max_intelligence_blockers
        ),
        entry_reasoning_action=decision.entry_reasoning_action,
        current_reasoning_action=decision.current_reasoning_action,
        output_action=action,
        output_reason=position.reason,
        output_next_stop=next_stop,
        output_next_target=next_target,
        output_requires_actuation=action in _ACTIONS_REQUIRING_ROUTE,
        native_fact_statuses=native_fact_statuses,
        native_fact_evidence=native_fact_evidence,
    )


def observe_cognitive_actuation(
    *,
    expected_action: str,
    routed_actions: tuple[str, ...],
    executed_actions: tuple[str, ...] | None = None,
) -> CognitiveActuationSensor:
    """Classify output routing independently from policy economics."""

    expected = expected_action.upper()
    routed = tuple(action.upper() for action in routed_actions)
    executed = (
        None
        if executed_actions is None
        else tuple(action.upper() for action in executed_actions)
    )
    requires = expected in _ACTIONS_REQUIRING_ROUTE

    if not requires:
        status = (
            "ALIGNED_NO_ACTION"
            if not routed
            else "UNEXPECTED_ROUTE_WHILE_HOLDING"
        )
    elif expected not in routed:
        status = "OUTPUT_NOT_ROUTED"
    elif executed is None:
        status = "ROUTED_EXECUTION_UNOBSERVED"
    elif expected not in executed:
        status = "ROUTED_NOT_EXECUTED"
    else:
        status = "ROUTED_AND_EXECUTED"

    return CognitiveActuationSensor(
        expected_action=expected,
        routed_actions=routed,
        executed_actions=executed,
        status=status,
        output_requires_actuation=requires,
    )
