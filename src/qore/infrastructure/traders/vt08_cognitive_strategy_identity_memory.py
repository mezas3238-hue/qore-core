"""Immutable Strategy Identity Memory for VT08 Forex Cognitive V1.

This memory describes what VT08 is. It contains source/methodology identity only
and deliberately excludes PnL, fold statistics, market rankings, and learned
runtime filters.
"""
from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from functools import lru_cache
from typing import Final

from qore.infrastructure.traders.vt08_forex import (
    AUTHORIZED_MARKETS,
    MAXIMUM_FILLED_TRADES_PER_MARKET_PER_NY_DATE,
)
from qore.infrastructure.traders.vt08_forex import (
    methodology_fingerprint as forex_methodology_fingerprint,
)
from qore.infrastructure.traders.vt08_source_kernel_r3_2 import (
    METHODOLOGY_VERSION,
    OPERATING_TIMEZONE,
    OWNER_FOREX_ANCHORS,
    PRIMARY_SOURCE,
    PRIMARY_SOURCE_SHA256,
    VT08EntryFamily,
    VT08LtfProfile,
    VT08StopFamily,
    VT08TargetFamily,
)
from qore.infrastructure.traders.vt08_source_kernel_r3_2 import (
    methodology_fingerprint as source_kernel_fingerprint,
)

SCHEMA: Final = "qore.vt08.forex.cognitive.strategy_identity.v1"
TRADER_ID: Final = "VT08_FOREX_COGNITIVE_V1"


@lru_cache(maxsize=1)
def _cached() -> dict[str, object]:
    return {
        "schema": SCHEMA,
        "memory_class": "STRATEGY_IDENTITY",
        "trader_id": TRADER_ID,
        "market_family": "FOREX",
        "authorized_markets": tuple(AUTHORIZED_MARKETS),
        "timezone": OPERATING_TIMEZONE,
        "owner_operational_h4_anchors_ny": tuple(OWNER_FOREX_ANCHORS),
        "source": {
            "primary_source": PRIMARY_SOURCE,
            "primary_source_sha256": PRIMARY_SOURCE_SHA256,
            "methodology_version": METHODOLOGY_VERSION,
            "source_kernel_fingerprint": source_kernel_fingerprint(),
            "forex_methodology_fingerprint": forex_methodology_fingerprint(),
        },
        "ltf_profiles": tuple(item.value for item in VT08LtfProfile),
        "entry_families": tuple(item.value for item in VT08EntryFamily),
        "stop_families": tuple(item.value for item in VT08StopFamily),
        "target_families": tuple(item.value for item in VT08TargetFamily),
        "source_semantics": {
            "daily_bias": "four-case-pdh-pdl-continuation-reversal",
            "scenario_family": ("C2", "C3"),
            "cisd_confirmation": "body-close-through-opposing-series-open",
            "protected_swing": (
                "structural-extreme-after-important-level-interaction-plus-cisd"
            ),
            "positional_entry_reference": "new-htf-open",
            "structural_invalidation_reference": "protected-swing-extreme",
            "trade_outer_lifecycle": "current-h4-close",
        },
        "cardinality": {
            "maximum_filled_trades_per_market_per_ny_date": (
                MAXIMUM_FILLED_TRADES_PER_MARKET_PER_NY_DATE
            ),
            "multiple_candidate_winner_priority": "UNRESOLVED_OWNER_POLICY",
        },
        "identity_guards": {
            "cognition_may_rewrite_methodology": False,
            "market_memory_may_rewrite_methodology": False,
            "experience_memory_may_rewrite_methodology": False,
            "pnl_may_rewrite_methodology": False,
            "future_information_allowed": False,
            "runtime_self_training_allowed": False,
            "cross_trader_rules_allowed": False,
            "qore_risk_final_capital_authority": True,
        },
    }


def strategy_identity_payload() -> dict[str, object]:
    return deepcopy(_cached())


def strategy_identity_runtime_view() -> dict[str, object]:
    return _cached()


@lru_cache(maxsize=1)
def strategy_identity_fingerprint() -> str:
    encoded = json.dumps(
        _cached(),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_strategy_identity() -> None:
    payload = strategy_identity_payload()
    guards = payload["identity_guards"]
    assert isinstance(guards, dict)
    assert guards["cognition_may_rewrite_methodology"] is False
    assert guards["market_memory_may_rewrite_methodology"] is False
    assert guards["experience_memory_may_rewrite_methodology"] is False
    assert guards["pnl_may_rewrite_methodology"] is False
    assert guards["future_information_allowed"] is False
    assert guards["runtime_self_training_allowed"] is False
    assert guards["cross_trader_rules_allowed"] is False
    assert guards["qore_risk_final_capital_authority"] is True
    assert payload["owner_operational_h4_anchors_ny"] == (1, 5, 9)
    assert len(strategy_identity_fingerprint()) == 64
