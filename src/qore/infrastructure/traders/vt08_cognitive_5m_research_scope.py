"""Explicit, non-operational five-market context for VT08 cognitive research.

This is an identity/availability adapter, NOT a license to trade new markets.
The original seven-market production authority and market memories stay frozen.
New market/anchor memory is honestly UNKNOWN until a causally bounded research
snapshot is independently versioned; do not reuse other traders' or markets' PnL.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Final

from qore.infrastructure.traders.vt08_cognitive_situation_model import (
    Vt08ForexSituationModel,
)
from qore.infrastructure.traders.vt08_source_kernel_r3_2 import OWNER_FOREX_ANCHORS

RESEARCH_MARKETS: Final = (
    "EURJPY",
    "USDCHF",
    "NZDUSD",
    "CADJPY",
    "USDCAD",
)
RESEARCH_SCOPE_ID: Final = "VT08_COGNITIVE_EXPANSION_5M_V1_RESEARCH_ONLY"
MEMORY_STATE: Final = "UNKNOWN_NOT_BOUND"
CONTEXT_SCHEMA: Final = "qore.vt08.cognitive_5m.market_context.research.v1"


@dataclass(frozen=True, slots=True)
class Vt08FiveMarketResearchSituation(Vt08ForexSituationModel):
    """The full original Situation Model with explicit isolated research scope.

    All parent validations still apply; only market authorization is overridden
    for the exactly-five-market test universe. This class has NO broker authority.
    source_evidence_id and latest_available_bar_close prove timestamp lineage at
    a minimum; the future CandidateEvent contract must enforce provenance across
    every constituent candle and feature.
    """

    source_evidence_id: str = ""
    latest_available_bar_close: datetime | None = None
    research_only: bool = True
    operational_authority: bool = False

    def _validate_market(self) -> None:
        if self.market not in RESEARCH_MARKETS:
            raise ValueError("VT08 research situation market outside five-market scope")

    def __post_init__(self) -> None:
        Vt08ForexSituationModel.__post_init__(self)
        if not self.research_only or self.operational_authority:
            raise ValueError("VT08 5M cognitive situation is research-only")
        if not self.source_evidence_id.strip():
            raise ValueError("VT08 5M research situation needs source evidence id")
        observed = self.latest_available_bar_close
        if observed is None or observed.tzinfo is None or observed.utcoffset() is None:
            raise ValueError("VT08 5M research situation requires bar close timezone")
        if observed > self.as_of:
            raise ValueError("VT08 5M research situation cannot consume future bars")


def research_market_anchor_context(
    market: str, anchor_hour_ny: int
) -> dict[str, object]:
    """Produce honest UNKNOWN memory, never invent a best-market prior.

    Even the USDCAD control memory is not attached to this research interface
    until temporal/as-of provenance and partition validity can be established.
    UNKNOWN here is contextual: it cannot veto a methodologically valid event
    without a *specific execution-material* uncertainty in the Situation Model.
    """
    if market not in RESEARCH_MARKETS:
        raise ValueError("VT08 research memory market outside 5M universe")
    if anchor_hour_ny not in OWNER_FOREX_ANCHORS:
        raise ValueError("VT08 research memory anchor outside Owner 01/05/09")
    context: dict[str, object] = {
        "schema": CONTEXT_SCHEMA,
        "scope": RESEARCH_SCOPE_ID,
        "market": market,
        "anchor_hour_ny": anchor_hour_ny,
        "cibo_market_prior_state": MEMORY_STATE,
        "trader_experience_state": MEMORY_STATE,
        "market_memory_version": None,
        "experience_memory_version": None,
        "temporal_memory_coverage": "NOT_VALIDATED",
        "execution_gate_from_pnl": False,
        "research_only": True,
        "operational_authority": False,
    }
    raw = json.dumps(context, sort_keys=True, separators=(",", ":"))
    context["fingerprint"] = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return context
