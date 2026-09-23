"""Frozen architecture contract for VT08 Forex Cognitive V1.

This module freezes cognitive vocabulary and authority boundaries only.
It does not alter VT08 source methodology, produce broker orders, size risk,
or wire Cognitive V1 into the current LIVE runtime.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Final

ARCHITECTURE_ID: Final = "VT08_FOREX_COGNITIVE_V1"
ARCHITECTURE_VERSION: Final = "v1-freeze-001"
OWNER_OPERATIONAL_ANCHORS_NY: Final = (1, 5, 9)

METHODOLOGY_MUTATION_ALLOWED: Final = False
RUNTIME_SELF_TRAINING_ALLOWED: Final = False
FUTURE_INFORMATION_ALLOWED: Final = False
CAPITAL_AUTHORITY: Final = False
ORDER_AUTHORITY: Final = False
LIVE_INTEGRATION_AUTHORIZED: Final = False
PRODUCTION_AUTHORIZED: Final = False
REAL_CAPITAL_AUTHORIZED: Final = False


class Vt08CognitiveAction(StrEnum):
    EXECUTE = "EXECUTE"
    WAIT = "WAIT"
    ABSTAIN = "ABSTAIN"


class Vt08HypothesisState(StrEnum):
    FORMING = "FORMING"
    CONFIRMED = "CONFIRMED"
    WAITING = "WAITING"
    EXECUTABLE = "EXECUTABLE"
    CONTRADICTED = "CONTRADICTED"
    KILLED = "KILLED"


class Vt08KnowledgeState(StrEnum):
    KNOWN = "KNOWN"
    SUPPORTED = "SUPPORTED"
    AMBIGUOUS = "AMBIGUOUS"
    CONTRADICTED = "CONTRADICTED"
    UNKNOWN = "UNKNOWN"


class Vt08PositionAction(StrEnum):
    HOLD = "HOLD"
    PROTECT = "PROTECT"
    REDUCE = "REDUCE"
    EXIT = "EXIT"


PERSISTENT_MEMORIES: Final = (
    "STRATEGY_IDENTITY_MEMORY",
    "CIBO_MARKET_MEMORY",
    "TRADER_EXPERIENCE_MEMORY",
)

EPHEMERAL_COMPONENTS: Final = (
    "CAUSAL_SITUATION_MODEL",
    "HYPOTHESIS_LIFECYCLE",
    "SOVEREIGN_REASONING_ENGINE",
    "ADVERSARIAL_REASONING",
    "METACOGNITION",
    "JOURNEY_DESTINATION_INTELLIGENCE",
    "POSITION_INTELLIGENCE",
)

ARCHITECTURAL_REFERENCES: Final = (
    "VT31_ARCHITECTURE_ONLY",
    "CAPITALIZER_ARCHITECTURE_ONLY",
    "CIBO_GOVERNED_MEMORY_AND_JOURNEY_CONTEXT",
)

PROHIBITED_CROSS_TRADER_IMPORTS: Final = (
    "NAS100_SPECIFIC_RULES",
    "SILVER_BULLET_RULES",
    "CAPITALIZER_ENTRY_LOGIC",
    "TURTLE_SOUP_RULES",
    "OTHER_TRADER_PNL_FILTERS",
    "OTHER_TRADER_MARKET_MEMORY",
)

RUNTIME_FORBIDDEN_INPUTS: Final = (
    "FUTURE_BAR",
    "TERMINAL_PNL",
    "POST_OUTCOME_DATE_ORACLE",
    "FOLD_IDENTITY",
    "CALENDAR_DATE_AS_EDGE_FEATURE",
)


@dataclass(frozen=True, slots=True)
class Vt08CognitiveArchitectureFreeze:
    architecture_id: str = ARCHITECTURE_ID
    architecture_version: str = ARCHITECTURE_VERSION
    owner_operational_anchors_ny: tuple[int, ...] = OWNER_OPERATIONAL_ANCHORS_NY
    persistent_memories: tuple[str, ...] = PERSISTENT_MEMORIES
    ephemeral_components: tuple[str, ...] = EPHEMERAL_COMPONENTS
    reasoning_actions: tuple[str, ...] = tuple(item.value for item in Vt08CognitiveAction)
    hypothesis_states: tuple[str, ...] = tuple(item.value for item in Vt08HypothesisState)
    knowledge_states: tuple[str, ...] = tuple(item.value for item in Vt08KnowledgeState)
    position_actions: tuple[str, ...] = tuple(item.value for item in Vt08PositionAction)
    market_anchor_specialization: bool = True
    methodology_mutation_allowed: bool = METHODOLOGY_MUTATION_ALLOWED
    runtime_self_training_allowed: bool = RUNTIME_SELF_TRAINING_ALLOWED
    future_information_allowed: bool = FUTURE_INFORMATION_ALLOWED
    capital_authority: bool = CAPITAL_AUTHORITY
    order_authority: bool = ORDER_AUTHORITY
    live_integration_authorized: bool = LIVE_INTEGRATION_AUTHORIZED
    production_authorized: bool = PRODUCTION_AUTHORIZED
    real_capital_authorized: bool = REAL_CAPITAL_AUTHORIZED

    def __post_init__(self) -> None:
        if self.owner_operational_anchors_ny != (1, 5, 9):
            raise ValueError("VT08 Cognitive V1 owner anchors must remain 01/05/09 NY")
        if self.methodology_mutation_allowed:
            raise ValueError("cognition may not mutate VT08 methodology")
        if self.runtime_self_training_allowed:
            raise ValueError("runtime PnL self-training is prohibited")
        if self.future_information_allowed:
            raise ValueError("future information is prohibited")
        if self.capital_authority or self.order_authority:
            raise ValueError("cognition has no capital/order authority")
        if (
            self.live_integration_authorized
            or self.production_authorized
            or self.real_capital_authorized
        ):
            raise ValueError("architecture freeze is research/shadow only")


def architecture_payload() -> dict[str, object]:
    freeze = Vt08CognitiveArchitectureFreeze()
    return {
        "schema": "qore.vt08.forex.cognitive_architecture_freeze.v1",
        **asdict(freeze),
        "architectural_references": ARCHITECTURAL_REFERENCES,
        "prohibited_cross_trader_imports": PROHIBITED_CROSS_TRADER_IMPORTS,
        "runtime_forbidden_inputs": RUNTIME_FORBIDDEN_INPUTS,
        "abstain_sovereignty": True,
        "killed_hypothesis_reuse_allowed": False,
        "rearm_requires_new_structural_source": True,
        "stop_widening_allowed": False,
        "qore_risk_final_capital_authority": True,
        "current_vt08_live_runtime_modified": False,
    }


def architecture_fingerprint() -> str:
    encoded = json.dumps(
        architecture_payload(),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
