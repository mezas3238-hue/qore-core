"""Composite brain-memory facade for VT31_NAS100_SPECIALIST_R1.

The trader has exactly three persistent governed memories:

1. Strategy / Identity Memory
2. CIBO Market Memory
3. Trader Experience / Lab Memory

The live Market Situation Model is intentionally separate and ephemeral.
"""
from __future__ import annotations

import hashlib
import json
from functools import lru_cache

from qore.infrastructure.traders.vt31_nas100_cibo_market_memory import (
    cibo_market_memory_fingerprint,
    market_memory_manifest,
    validate_cibo_market_memory,
)
from qore.infrastructure.traders.vt31_nas100_strategy_identity_memory import (
    strategy_identity_fingerprint,
    strategy_identity_payload,
    validate_strategy_identity,
)
from qore.infrastructure.traders.vt31_nas100_trader_experience_memory import (
    trader_experience_fingerprint,
    trader_experience_payload,
    validate_trader_experience,
)

SCHEMA = "qore.vt31.nas100.cognitive_memory_bundle.v3"
MARKET = "NAS100"


def memory_payload() -> dict[str, object]:
    return {
        "schema": SCHEMA,
        "market": MARKET,
        "mind_model": "THREE_PERSISTENT_MEMORIES_PLUS_SITUATION",
        "strategy_identity_memory": strategy_identity_payload(),
        "cibo_market_memory_manifest": market_memory_manifest(),
        "trader_experience_memory": trader_experience_payload(),
        "situation_model_contract": {
            "schema": "qore.vt31.nas100.situation_model.v1",
            "persistent": False,
            "rebuilt_each_decision": True,
            "causal_as_of_only": True,
            "terminal_pnl_allowed": False,
            "historical_date_outcome_allowed": False,
        },
        "fingerprints": {
            "strategy_identity": strategy_identity_fingerprint(),
            "cibo_market": cibo_market_memory_fingerprint(),
            "trader_experience": trader_experience_fingerprint(),
        },
        "runtime_guards": {
            "external_cibo_runtime_dependency": False,
            "date_level_historical_outcome_lookup": False,
            "future_bar_lookup": False,
            "persistent_memory_mutable_at_runtime": False,
            "strategy_identity_mutable_by_pnl": False,
            "fresh_holdout_opened": False,
        },
    }


@lru_cache(maxsize=1)
def memory_fingerprint() -> str:
    encoded = json.dumps(
        memory_payload(),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_memory() -> None:
    validate_strategy_identity()
    validate_cibo_market_memory()
    validate_trader_experience()

    payload = memory_payload()
    assert payload["mind_model"] == "THREE_PERSISTENT_MEMORIES_PLUS_SITUATION"
    guards = payload["runtime_guards"]
    assert isinstance(guards, dict)
    assert guards["external_cibo_runtime_dependency"] is False
    assert guards["date_level_historical_outcome_lookup"] is False
    assert guards["future_bar_lookup"] is False
    assert guards["persistent_memory_mutable_at_runtime"] is False
    assert guards["strategy_identity_mutable_by_pnl"] is False
    assert guards["fresh_holdout_opened"] is False

    contract = payload["situation_model_contract"]
    assert isinstance(contract, dict)
    assert contract["persistent"] is False
    assert contract["rebuilt_each_decision"] is True
    assert contract["causal_as_of_only"] is True
    assert contract["terminal_pnl_allowed"] is False
    assert contract["historical_date_outcome_allowed"] is False
    assert len(memory_fingerprint()) == 64
