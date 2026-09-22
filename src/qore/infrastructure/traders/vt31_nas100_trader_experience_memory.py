"""VT31_NAS100 Trader Experience / Lab Memory.

This memory answers: "What have I learned when *my VT31 methodology* interacts
with NAS100?"

It is distinct from general CIBO market memory. It retains adjudicated
laboratory lessons, failed hypotheses, consumed-research bindings and
strategy-market interaction diagnostics. It cannot rewrite Strategy Identity
Memory and cannot self-train at runtime.
"""
from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from functools import lru_cache
from typing import Final

from qore.infrastructure.traders.vt31_nas100_cibo_market_memory import (
    dossier_runtime_view,
)

SCHEMA: Final = "qore.vt31.nas100.trader_experience_memory.v1"
TRADER_ID: Final = "VT31_NAS100_SPECIALIST_R1"
MARKET: Final = "NAS100"

_LAB_BINDINGS: Final = {
    "market_state_v2_run": 35284479467,
    "temporal_stability_v1_run": 35284842202,
    "intelligence_v2a_run": 35285082329,
    "stale_renewal_forensics_run": 35285506160,
    "market_context_v3_run": 35288495678,
    "cibo_intelligence_bridge_v1_run": 35288950361,
    "market_understanding_snapshot_v1_run": 35289940990,
    "intelligence_policy_lab_v2b_run": 35290200552,
    "direct_m1_wfo_run": 35291106350,
    "state_equivalence_run": 35291288678,
    "handoff_cross_fold_intelligence_run": 35301231110,
}

_SUPPORTED: Final = {
    "sequence_freshness": (
        "reclaim-age 8-14m was negative across all consumed folds; mechanism "
        "supported but not a universal standalone law"
    ),
    "reference_liquidity_context": (
        "last observed reference-liquidity-sweep was directionally positive "
        "across consumed R8/R6/R5 diagnostics"
    ),
    "context_is_multidimensional": (
        "generic renewal and single-variable routing were unstable; reasoning "
        "must combine causal state rather than promote isolated bins"
    ),
    "dynamic_destination_management": (
        "full-boundary versus partial+runner behavior differs by causal market "
        "state; no universal target plan survived research"
    ),
    "initial_invalidation_identity": (
        "source structural swing remains the methodological initial "
        "invalidation; widening is not justified by stop-mismatch evidence"
    ),
    "causal_structure_timestamp_semantics": (
        "legacy Eight-Ledger structure timestamps are retained only as "
        "consumed aggregate research; runtime CIBO structure state uses "
        "closed-M1 causal V2 timestamps and never backdates a reclaim/touch"
    ),
    "low_dd_reference_gate": (
        "consumed R5/R6/R8 low-drawdown research supports a compressed "
        "09-reference as the primary executable state; outside compression, "
        "the only retained calibration fallback is SHORT with mixed H1 state. "
        "This gate is development-calibration evidence and still requires "
        "independent 2Y validation before any freeze"
    ),
}

_REJECTED: Final = {
    "generic_wait_renewal": (
        "WAIT->new local confirmation->fresh same-side FVG was not stable "
        "across all consumed folds"
    ),
    "static_stale_filter_freeze": (
        "mechanism supported but static filter was not freeze-ready because "
        "secondary stability diagnostics degraded"
    ),
    "universal_partial_runner": (
        "indiscriminate partial+runner management was unstable across folds"
    ),
    "best_bin_promotion": (
        "historically attractive bins are not operational rules without "
        "mechanistic and temporal validation"
    ),
}

_UNRESOLVED: Final = {
    "journey_capacity_memory": (
        "must be learned with structural labels and target-depth calibration, "
        "not selected directly from PnL"
    ),
    "contextual_position_management": (
        "SUPPORTIVE/MIXED/CAUTIOUS-like VT31 states must be learned from NAS100 "
        "evidence before activating structural trailing policy"
    ),
    "structural_rearm_economics": (
        "rearm mechanism can be defined methodologically, but its effect must "
        "be measured on consumed evidence before candidate freeze"
    ),
}


@lru_cache(maxsize=1)
def _trader_experience_cached() -> dict[str, object]:
    dossier = dossier_runtime_view()
    overlay = dossier["trader_overlay_research_source"]
    assert isinstance(overlay, dict)
    return {
        "schema": SCHEMA,
        "memory_class": "TRADER_EXPERIENCE_LAB",
        "trader_id": TRADER_ID,
        "market": MARKET,
        "laboratory_bindings": _LAB_BINDINGS,
        "strategy_market_overlay": deepcopy(overlay),
        "supported_mechanisms": _SUPPORTED,
        "rejected_hypotheses": _REJECTED,
        "unresolved": _UNRESOLVED,
        "experience_governance": {
            "consumed_evidence_only": True,
            "contains_per_date_outcome_map": False,
            "runtime_self_training_allowed": False,
            "pnl_direct_rule_promotion_allowed": False,
            "strategy_identity_rewrite_allowed": False,
            "fresh_holdout_opened": False,
        },
    }


def trader_experience_payload() -> dict[str, object]:
    return deepcopy(_trader_experience_cached())


def trader_experience_runtime_view() -> dict[str, object]:
    """Read-only-by-contract internal view of immutable experience memory."""
    return _trader_experience_cached()


@lru_cache(maxsize=1)
def trader_experience_fingerprint() -> str:
    encoded = json.dumps(
        _trader_experience_cached(),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_trader_experience() -> None:
    payload = trader_experience_payload()
    governance = payload["experience_governance"]
    assert isinstance(governance, dict)
    assert governance["consumed_evidence_only"] is True
    assert governance["contains_per_date_outcome_map"] is False
    assert governance["runtime_self_training_allowed"] is False
    assert governance["pnl_direct_rule_promotion_allowed"] is False
    assert governance["strategy_identity_rewrite_allowed"] is False
    assert governance["fresh_holdout_opened"] is False
    assert len(trader_experience_fingerprint()) == 64
