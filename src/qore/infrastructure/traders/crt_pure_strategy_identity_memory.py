"""Source-gated Strategy Identity Memory for VT08 CRT PURE.

The memory can be constructed before the CRT methodology is fully closed, but it must
fail closed for execution until every core source concept has been promoted from approved
primary evidence.
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from functools import lru_cache
from typing import Final

from qore.infrastructure.traders.crt_pure_identity import CRT_PURE_IDENTITY
from qore.infrastructure.traders.crt_pure_source_registry import (
    CRT_PURE_SOURCE_REGISTRY,
    CrtPureConceptId,
    promotable_concepts,
)


SCHEMA: Final = "qore.vt08.crt_pure.strategy_identity_memory.v1"
STRATEGY_ID: Final = "VT08_CRT_PURE"
METHODOLOGY_FAMILY: Final = "CRT"
METHODOLOGY_VARIANT: Final = "PURE"


CRT_PURE_CORE_EXECUTION_CONCEPTS: Final[tuple[CrtPureConceptId, ...]] = (
    CrtPureConceptId.REFERENCE_RANGE,
    CrtPureConceptId.CRH_CRL,
    CrtPureConceptId.LIQUIDATION_SWEEP,
    CrtPureConceptId.RECLAIM_CLOSE_BACK_INSIDE,
    CrtPureConceptId.CANDLE_1_2_3,
    CrtPureConceptId.INVALIDATION,
    CrtPureConceptId.ENTRY_FAMILIES,
    CrtPureConceptId.STRUCTURAL_STOP,
    CrtPureConceptId.STRUCTURAL_DESTINATION,
)


def unresolved_core_execution_concepts() -> tuple[CrtPureConceptId, ...]:
    promoted = set(promotable_concepts())
    return tuple(
        concept
        for concept in CRT_PURE_CORE_EXECUTION_CONCEPTS
        if concept not in promoted
    )


def strategy_identity_ready() -> bool:
    return not unresolved_core_execution_concepts()


@lru_cache(maxsize=1)
def _strategy_identity_cached() -> dict[str, object]:
    promoted = promotable_concepts()
    promoted_set = set(promoted)

    canonical_rules: dict[str, tuple[str, ...]] = {}
    for record in CRT_PURE_SOURCE_REGISTRY:
        if record.concept_id not in promoted_set:
            continue
        canonical_rules[record.concept_id.value] = tuple(
            evidence.normalized_statement
            for evidence in record.evidence
            if evidence.adjudication.value == "CANONICAL"
        )

    unresolved = unresolved_core_execution_concepts()
    return {
        "schema": SCHEMA,
        "memory_class": "STRATEGY_IDENTITY",
        "strategy_id": STRATEGY_ID,
        "methodology_family": METHODOLOGY_FAMILY,
        "methodology_variant": METHODOLOGY_VARIANT,
        "markets": tuple(market.value for market in CRT_PURE_IDENTITY.markets),
        "canonical_concepts": tuple(concept.value for concept in promoted),
        "canonical_rules": canonical_rules,
        "core_execution_concepts": tuple(
            concept.value for concept in CRT_PURE_CORE_EXECUTION_CONCEPTS
        ),
        "unresolved_core_execution_concepts": tuple(
            concept.value for concept in unresolved
        ),
        "strategy_identity_ready": not unresolved,
        "source_adjudication_complete": CRT_PURE_IDENTITY.source_adjudication_complete,
        "identity_guards": {
            "crt_amd_allowed": False,
            "market_memory_may_rewrite_methodology": False,
            "experience_memory_may_rewrite_methodology": False,
            "pnl_may_rewrite_methodology": False,
            "runtime_mutation_allowed": False,
            "level_b_may_define_methodology": False,
            "unresolved_rule_may_execute": False,
        },
    }


def strategy_identity_payload() -> dict[str, object]:
    return deepcopy(_strategy_identity_cached())


def strategy_identity_runtime_view() -> dict[str, object]:
    return _strategy_identity_cached()


@lru_cache(maxsize=1)
def strategy_identity_fingerprint() -> str:
    encoded = json.dumps(
        _strategy_identity_cached(),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_strategy_identity() -> None:
    payload = strategy_identity_payload()
    guards = payload["identity_guards"]
    assert isinstance(guards, dict)
    assert guards["crt_amd_allowed"] is False
    assert guards["level_b_may_define_methodology"] is False
    assert guards["unresolved_rule_may_execute"] is False
    assert len(strategy_identity_fingerprint()) == 64
