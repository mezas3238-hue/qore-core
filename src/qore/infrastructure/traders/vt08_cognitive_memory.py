"""Combined governed memory view for VT08 Forex Cognitive V1."""
from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from functools import lru_cache

from qore.infrastructure.traders.vt08_cognitive_cibo_market_memory import (
    cibo_market_memory_fingerprint,
    market_anchor_prior,
    validate_cibo_market_memory,
)
from qore.infrastructure.traders.vt08_cognitive_strategy_identity_memory import (
    strategy_identity_fingerprint,
    validate_strategy_identity,
)
from qore.infrastructure.traders.vt08_cognitive_trader_experience_memory import (
    experience_cell,
    trader_experience_fingerprint,
    validate_trader_experience,
)
from qore.infrastructure.traders.vt08_cognitive_v1_contracts import (
    architecture_fingerprint,
)


def market_anchor_context(market: str, anchor_hour_ny: int) -> dict[str, object]:
    context = {
        "market": market,
        "anchor_hour_ny": anchor_hour_ny,
        "cibo_market_prior": market_anchor_prior(market, anchor_hour_ny),
        "trader_experience": experience_cell(market, anchor_hour_ny),
        "use": "CONTEXT_ONLY_NOT_DIRECT_EXECUTION_GATE",
    }
    encoded = json.dumps(
        context,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    context["fingerprint"] = hashlib.sha256(encoded).hexdigest()
    return context


@lru_cache(maxsize=1)
def _bundle_cached() -> dict[str, object]:
    return {
        "schema": "qore.vt08.forex.cognitive.memory_bundle.v1",
        "architecture_fingerprint": architecture_fingerprint(),
        "strategy_identity_fingerprint": strategy_identity_fingerprint(),
        "cibo_market_memory_fingerprint": cibo_market_memory_fingerprint(),
        "trader_experience_memory_fingerprint": trader_experience_fingerprint(),
        "memory_classes": (
            "STRATEGY_IDENTITY",
            "CIBO_MARKET_SPECIALIST",
            "TRADER_EXPERIENCE_LAB",
        ),
        "runtime_self_training_allowed": False,
        "direct_pnl_rule_promotion_allowed": False,
    }


def cognitive_memory_payload() -> dict[str, object]:
    return deepcopy(_bundle_cached())


@lru_cache(maxsize=1)
def cognitive_memory_fingerprint() -> str:
    encoded = json.dumps(
        _bundle_cached(),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_cognitive_memory() -> None:
    validate_strategy_identity()
    validate_cibo_market_memory()
    validate_trader_experience()
    assert _bundle_cached()["runtime_self_training_allowed"] is False
    assert _bundle_cached()["direct_pnl_rule_promotion_allowed"] is False
    assert len(cognitive_memory_fingerprint()) == 64
