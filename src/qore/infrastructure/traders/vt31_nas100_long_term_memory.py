"""VT31_NAS100 long-term market memory.

Stable, internalized NAS100 knowledge distilled from consumed CIBO evidence.
This is semantic memory: market behavior and priors, not experiment history and
not the current trading day's state.
"""
from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Final

SCHEMA: Final = "qore.vt31.nas100.long_term_memory.v1"
MARKET: Final = "NAS100"

_CIBO_BINDING: Final = {
    "run_id": 35175782935,
    "artifact_id": 10478487667,
    "digest": (
        "sha256:"
        "17c8d1909152d87ed67a05cd986fa9cca39b2ac92598d36822c38e8afccde192"
    ),
}

_SEQUENCE_KNOWLEDGE: Final = {
    "last_structure_touch_to_departure_minutes": {
        "r8_fresh": {"p25": "1", "p50": "8", "p75": "14"},
        "r6": {"p25": "1", "p50": "6", "p75": "12"},
        "r5": {"p25": "1", "p50": "5", "p75": "11"},
    },
    "departure_to_opposite_boundary_minutes": {
        "r8_fresh": {"p25": "3", "p50": "5", "p75": "8"},
        "r6": {"p25": "4", "p50": "5", "p75": "8"},
        "r5": {"p25": "3", "p50": "5", "p75": "8"},
    },
    "principle": (
        "formation/reaction may be prolonged while final departure/delivery "
        "is often fast; freshness is contextual state, not a clock rule"
    ),
}

_STRUCTURE_KNOWLEDGE: Final = {
    "completed_reversal_episodes": 547,
    "last_structure_before_departure_counts": {
        "local-liquidity-sweep": 431,
        "reference-liquidity-sweep": 79,
        "fair-value-gap": 19,
        "breaker": 13,
        "order-block": 4,
        "none": 1,
    },
    "liquidity_event_share_approx": "0.932",
    "principle": (
        "liquidity events dominate final observed pre-departure structure, "
        "but no family guarantees departure"
    ),
}

_STOP_KNOWLEDGE: Final = {
    "initial_stop": {
        "roots": 87,
        "eventual_source_objective_after_stop": 20,
    },
    "protected_stop": {
        "roots": 68,
        "eventual_source_objective_after_stop": 31,
    },
    "principle": (
        "premature management mismatch is material; evidence does not justify "
        "arbitrary widening of the original structural invalidation"
    ),
}

_DESTINATION_KNOWLEDGE: Final = {
    "post_boundary_extension_rate_given_boundary_hit": {
        "r5": {
            "0.25_ref": "0.8287",
            "0.5_ref": "0.6243",
            "1_ref": "0.3757",
            "1.5_ref": "0.2044",
            "2_ref": "0.1050",
        },
        "r6": {
            "0.25_ref": "0.8111",
            "0.5_ref": "0.6111",
            "1_ref": "0.3500",
            "1.5_ref": "0.1667",
            "2_ref": "0.1167",
        },
        "r8_fresh": {
            "0.25_ref": "0.7419",
            "0.5_ref": "0.5215",
            "1_ref": "0.2903",
            "1.5_ref": "0.2097",
            "2_ref": "0.1505",
        },
    },
    "principle": (
        "the opposite reference boundary is a structural destination; "
        "extension is conditional and cannot be assumed"
    ),
}

_GUARDS: Final = {
    "external_cibo_runtime_dependency": False,
    "date_level_lookup_allowed": False,
    "per_date_outcome_memory": False,
    "future_bar_lookup_allowed": False,
    "post_outcome_lookup_allowed": False,
    "runtime_mutation_allowed": False,
}


def long_term_memory_payload() -> dict[str, object]:
    return deepcopy(
        {
            "schema": SCHEMA,
            "market": MARKET,
            "memory_class": "LONG_TERM_SEMANTIC",
            "source_binding": _CIBO_BINDING,
            "sequence_knowledge": _SEQUENCE_KNOWLEDGE,
            "structure_knowledge": _STRUCTURE_KNOWLEDGE,
            "stop_knowledge": _STOP_KNOWLEDGE,
            "destination_knowledge": _DESTINATION_KNOWLEDGE,
            "guards": _GUARDS,
        }
    )


def long_term_memory_fingerprint() -> str:
    encoded = json.dumps(
        long_term_memory_payload(),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_long_term_memory() -> None:
    payload = long_term_memory_payload()
    guards = payload["guards"]
    assert isinstance(guards, dict)
    assert guards["external_cibo_runtime_dependency"] is False
    assert guards["date_level_lookup_allowed"] is False
    assert guards["per_date_outcome_memory"] is False
    assert guards["future_bar_lookup_allowed"] is False
    assert guards["post_outcome_lookup_allowed"] is False
    assert guards["runtime_mutation_allowed"] is False
