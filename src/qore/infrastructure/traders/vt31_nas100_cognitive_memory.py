"""Internalized NAS100 market memory for VT31_NAS100_SPECIALIST_R1.

This module is the specialist's long-term memory.  It is distilled from
consumed CIBO Atlas and laboratory evidence and ships *inside* VT31.

Runtime code must never query CIBO ledgers, CIBO services, historical dates,
or post-outcome labels.  The memory contains only versioned aggregate knowledge
and already-adjudicated laboratory lessons.
"""
from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Final

SCHEMA: Final = "qore.vt31.nas100.cognitive_memory.v1"
MARKET: Final = "NAS100"

_CIBO_BINDING: Final = {
    "run_id": 35175782935,
    "artifact_id": 10478487667,
    "digest": (
        "sha256:"
        "17c8d1909152d87ed67a05cd986fa9cca39b2ac92598d36822c38e8afccde192"
    ),
}

_LAB_BINDINGS: Final = {
    "market_state_v2_run": 35284479467,
    "temporal_stability_v1_run": 35284842202,
    "intelligence_v2a_run": 35285082329,
    "stale_renewal_forensics_run": 35285506160,
    "cibo_intelligence_bridge_v1_run": 35288950361,
    "market_understanding_snapshot_v1_run": 35289940990,
    "intelligence_policy_lab_v2b_run": 35290200552,
}

_SEQUENCE_MEMORY: Final = {
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
    "interpretation": (
        "formation/reaction can be long; final departure/delivery is often "
        "fast; freshness is state information, not a mechanical clock rule"
    ),
}

_STRUCTURE_MEMORY: Final = {
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
}

_STOP_MEMORY: Final = {
    "initial_stop": {
        "roots": 87,
        "eventual_source_objective_after_stop": 20,
    },
    "protected_stop": {
        "roots": 68,
        "eventual_source_objective_after_stop": 31,
    },
    "lesson": (
        "management mismatch is material; evidence does not justify arbitrary "
        "initial-stop widening"
    ),
}

_TARGET_MEMORY: Final = {
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
    "interpretation": (
        "opposite reference boundary remains a structural destination; "
        "extension is conditional and must not become a guaranteed runner"
    ),
}

_LAB_MEMORY: Final = {
    "supported_mechanisms": {
        "sequence_freshness": (
            "stale 8-14m reclaim state was negative across all consumed folds"
        ),
        "reference_liquidity_state": (
            "last observed reference-liquidity-sweep was directionally "
            "positive across R8/R6/R5 under baseline economics"
        ),
        "context_required": (
            "generic stale renewal failed as a universal policy; higher-order "
            "market state is required"
        ),
        "dynamic_destination_management": (
            "universal partial+runner was unstable; management must depend on "
            "causal market state"
        ),
    },
    "falsified_or_rejected": {
        "generic_renewal_policy": (
            "rejected as a general rule because R5 remained materially negative"
        ),
        "static_stale_filter_freeze": (
            "mechanism supported but static filter not freeze-ready"
        ),
        "universal_target_plan": (
            "rejected; boundary and partial-runner behavior differ by state"
        ),
    },
    "unresolved": {
        "runtime_structure_touch_semantics": (
            "raw-M1 reconstruction must exactly match CIBO causal touch "
            "semantics before candidate freeze"
        ),
    },
}

_RUNTIME_GUARDS: Final = {
    "external_cibo_runtime_dependency": False,
    "date_level_lookup_allowed": False,
    "future_bar_lookup_allowed": False,
    "post_outcome_lookup_allowed": False,
    "per_date_historical_outcome_keys_present": False,
    "memory_mutable_at_runtime": False,
}


def memory_payload() -> dict[str, object]:
    """Return an isolated copy of the specialist's embedded long-term memory."""
    return deepcopy(
        {
            "schema": SCHEMA,
            "market": MARKET,
            "memory_type": "INTERNALIZED_CONSUMED_KNOWLEDGE",
            "cibo_source_binding": _CIBO_BINDING,
            "laboratory_bindings": _LAB_BINDINGS,
            "sequence_memory": _SEQUENCE_MEMORY,
            "structure_memory": _STRUCTURE_MEMORY,
            "stop_memory": _STOP_MEMORY,
            "target_memory": _TARGET_MEMORY,
            "laboratory_memory": _LAB_MEMORY,
            "runtime_guards": _RUNTIME_GUARDS,
        }
    )


def memory_fingerprint() -> str:
    encoded = json.dumps(
        memory_payload(),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_memory() -> None:
    payload = memory_payload()
    guards = payload["runtime_guards"]
    assert isinstance(guards, dict)
    assert guards["external_cibo_runtime_dependency"] is False
    assert guards["date_level_lookup_allowed"] is False
    assert guards["future_bar_lookup_allowed"] is False
    assert guards["post_outcome_lookup_allowed"] is False
    assert guards["memory_mutable_at_runtime"] is False
    assert len(memory_fingerprint()) == 64
