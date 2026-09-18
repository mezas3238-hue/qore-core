"""Immutable Strategy / Identity Memory for VT31_NAS100.

This memory answers: "What am I and what must I look for?"

It contains methodology identity only. It must not absorb retrospective market
statistics or laboratory PnL findings. Any methodology change requires a new
strategy-memory fingerprint and full revalidation.
"""
from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from functools import lru_cache
from typing import Final

from qore.infrastructure.traders.vt31_silver_bullet_r2_2 import (
    Vt31R22ExecutionPolicy,
)

SCHEMA: Final = "qore.vt31.nas100.strategy_identity_memory.v1"
TRADER_ID: Final = "VT31_NAS100_SPECIALIST_R1"
MARKET: Final = "NAS100"


@lru_cache(maxsize=1)
def _strategy_identity_cached() -> dict[str, object]:
    policy = Vt31R22ExecutionPolicy()
    return {
        "schema": SCHEMA,
        "memory_class": "STRATEGY_IDENTITY",
        "trader_id": TRADER_ID,
        "market": MARKET,
        "methodology_family": "AM_SILVER_BULLET_TTRADES",
        "timezone": "America/New_York",
        "reference_window": "09:00-10:00-NY",
        "source_window": "10:00-11:00-NY",
        "source_identity": {
            "first_side_raid": "strict-penetration-of-frozen-09-reference",
            "both_sides_swept": "fail-closed",
            "reversal_side": "opposite-first-raid",
            "structural_confirmation": (
                "close-through-structure-after-first-side-raid"
            ),
            "entry_evidence_families": [
                "breaker",
                "fair-value-gap",
                "order-block",
            ],
            "entry_selection": (
                "earliest-causally-formed-source-evidence;"
                "contemporaneous-price-disagreement-fails-closed"
            ),
        },
        "invalidation_identity": {
            "initial_stop": "source-methodological-swing-extreme",
            "stop_widening_after_entry": False,
            "future_information_allowed": False,
        },
        "destination_identity": {
            "primary_structural_destination": (
                "opposite-frozen-09-reference-boundary"
            ),
            "fixed-r-target_is_methodology_identity": False,
            "destination_may_be_contextualized": True,
        },
        "lifecycle": {
            "pending_setup_expiry": "11:00-NY",
            "filled_trade_outer_boundary": "16:00-NY",
            "same_bar_ambiguity": "fail-closed/censor",
        },
        "execution_policy_fingerprint": policy.fingerprint(),
        "identity_guards": {
            "market_memory_may_rewrite_methodology": False,
            "experience_memory_may_rewrite_methodology": False,
            "pnl_may_rewrite_methodology": False,
            "retrospective_loss_repair_allowed": False,
            "explicit_versioned_methodology_revision_required": True,
        },
    }


def strategy_identity_payload() -> dict[str, object]:
    """Return a defensive copy for external/governance consumers."""
    return deepcopy(_strategy_identity_cached())


def strategy_identity_runtime_view() -> dict[str, object]:
    """Read-only-by-contract internal view of immutable strategy memory."""
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
    assert guards["market_memory_may_rewrite_methodology"] is False
    assert guards["experience_memory_may_rewrite_methodology"] is False
    assert guards["pnl_may_rewrite_methodology"] is False
    assert guards["retrospective_loss_repair_allowed"] is False
    assert len(strategy_identity_fingerprint()) == 64
