"""VT31_NAS100 episodic/research memory.

This memory records what the specialist development program has learned:
supported mechanisms, rejected hypotheses, failures, and unresolved warnings.
It contains no current-day market state and no per-date historical outcome map.
"""
from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Final

SCHEMA: Final = "qore.vt31.nas100.episodic_research_memory.v1"
MARKET: Final = "NAS100"

_LAB_BINDINGS: Final = {
    "market_state_v2_run": 35284479467,
    "temporal_stability_v1_run": 35284842202,
    "intelligence_v2a_run": 35285082329,
    "stale_renewal_forensics_run": 35285506160,
    "cibo_intelligence_bridge_v1_run": 35288950361,
    "market_understanding_snapshot_v1_run": 35289940990,
    "intelligence_policy_lab_v2b_run": 35290200552,
}

_SUPPORTED: Final = {
    "sequence_freshness": (
        "stale 8-14m reclaim state was negative across all consumed folds"
    ),
    "reference_liquidity_state": (
        "last observed reference-liquidity-sweep was directionally positive "
        "across R8/R6/R5 under baseline economics"
    ),
    "context_required": (
        "generic stale renewal failed as a universal policy; higher-order "
        "market state is required"
    ),
    "dynamic_destination_management": (
        "universal partial+runner was unstable; management must depend on "
        "causal market state"
    ),
}

_REJECTED: Final = {
    "generic_renewal_policy": (
        "rejected as a general rule because R5 remained materially negative"
    ),
    "static_stale_filter_freeze": (
        "mechanism supported but static filter was not freeze-ready"
    ),
    "universal_target_plan": (
        "rejected because boundary and partial-runner behavior differ by state"
    ),
}

_FAILURE_LESSONS: Final = {
    "do_not_convert_aggregate_prior_to_oracle": (
        "historical CIBO frequencies may shape reasoning but never reveal the "
        "outcome of the current or matching historical date"
    ),
    "do_not_reuse_consumed_evidence_as_fresh": (
        "R5/R6/R8 and CIBO Atlas are development memory only"
    ),
    "do_not_auto_promote_best_bin": (
        "aggregate-best context bins require mechanistic temporal validation"
    ),
}

_UNRESOLVED: Final = {
    "runtime_structure_touch_semantics": (
        "raw-M1 reconstruction must exactly match CIBO causal touch semantics "
        "before candidate freeze"
    ),
    "full_wait_state_machine": (
        "WAIT lifecycle remains to be formalized without changing economics "
        "post hoc"
    ),
}

_GUARDS: Final = {
    "contains_current_day_state": False,
    "contains_per_date_outcome_map": False,
    "runtime_retraining_allowed": False,
    "promotion_without_revalidation_allowed": False,
}


def episodic_memory_payload() -> dict[str, object]:
    return deepcopy(
        {
            "schema": SCHEMA,
            "market": MARKET,
            "memory_class": "EPISODIC_RESEARCH",
            "laboratory_bindings": _LAB_BINDINGS,
            "supported_mechanisms": _SUPPORTED,
            "rejected_hypotheses": _REJECTED,
            "failure_lessons": _FAILURE_LESSONS,
            "unresolved": _UNRESOLVED,
            "guards": _GUARDS,
        }
    )


def episodic_memory_fingerprint() -> str:
    encoded = json.dumps(
        episodic_memory_payload(),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_episodic_memory() -> None:
    payload = episodic_memory_payload()
    guards = payload["guards"]
    assert isinstance(guards, dict)
    assert guards["contains_current_day_state"] is False
    assert guards["contains_per_date_outcome_map"] is False
    assert guards["runtime_retraining_allowed"] is False
    assert guards["promotion_without_revalidation_allowed"] is False
