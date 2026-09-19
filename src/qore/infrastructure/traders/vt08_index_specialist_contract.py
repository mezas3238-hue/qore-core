"""Exact provider-neutral identity contract for VT08 Index R58.

This module contains no trading execution and no promotion authority. It binds
the already-frozen R58 research candidate to an exact specialized Trader
identity that can traverse the canonical Trader Lab without being mislabeled as
the generic VT-08 CRT 4H AMD evaluator.

VT08INDEX is the synthetic economic portfolio series used by Trader Lab
performance evidence. The actual qualified markets remain explicit and
separate: NAS100, SP500 and US30.
"""

from __future__ import annotations

import json
from hashlib import sha256
from typing import Mapping

TRADER_CODE = "vt-08"
TRADER_VERSION = "v58"

CANDIDATE_ID = "VT08_INDEX_R58_EXACT_R47_DISTRIBUTED_CAUSAL_RISK_001"
CONFIG_FINGERPRINT = (
    "e959c8578a7ac71658cd19daf6d61815dfe277ecd06d8100c2655b30a62f48fa"
)
FREEZE_ID = "VT08_INDEX_R59_R58_CANDIDATE_FREEZE_001"

METHODOLOGY_ID = "vt08-index-source-complete"
METHODOLOGY_VERSION = "v1"
PORTFOLIO_INSTRUMENT = "VT08INDEX"
MARKETS = ("NAS100", "SP500", "US30")
MARKETS_MANIFEST_VALUE = "/".join(MARKETS)
TIMEFRAMES = ("M15", "H4")
LINEAGE = ("R34", "R47", "R58")


def _methodology_payload() -> dict[str, object]:
    return {
        "schema": "qore.traders.vt08_index.specialist_contract.v1",
        "trader_code": TRADER_CODE,
        "trader_version": TRADER_VERSION,
        "candidate_id": CANDIDATE_ID,
        "config_fingerprint": CONFIG_FINGERPRINT,
        "freeze_id": FREEZE_ID,
        "methodology_id": METHODOLOGY_ID,
        "methodology_version": METHODOLOGY_VERSION,
        "portfolio_instrument": PORTFOLIO_INSTRUMENT,
        "markets": list(MARKETS),
        "timeframes": list(TIMEFRAMES),
        "lineage": list(LINEAGE),
        "source_complete_signals_preserved": True,
        "signals_suppressed": False,
        "zero_risk_allowed": False,
        "calendar_or_year_runtime_feature": False,
        "post_entry_outcome_runtime_feature": False,
    }


METHODOLOGY_FINGERPRINT = sha256(
    json.dumps(
        _methodology_payload(),
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode()
).hexdigest()


def manifest_parameters() -> tuple[tuple[str, str], ...]:
    """Return the exact Trader manifest fields for the R58 specialist."""
    return (
        ("trader.code", TRADER_CODE),
        ("trader.config_fingerprint", CONFIG_FINGERPRINT),
        ("trader.instrument", PORTFOLIO_INSTRUMENT),
        ("trader.markets", MARKETS_MANIFEST_VALUE),
        ("trader.methodology_fingerprint", METHODOLOGY_FINGERPRINT),
        ("trader.methodology_id", METHODOLOGY_ID),
        ("trader.methodology_version", METHODOLOGY_VERSION),
    )


def manifest_matches(values: Mapping[str, str]) -> bool:
    """Fail-closed equality check for the exact R58 specialist manifest."""
    return all(values.get(name) == value for name, value in manifest_parameters())
