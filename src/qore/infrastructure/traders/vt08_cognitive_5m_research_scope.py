"""Explicit, non-operational five-market context for VT08 cognitive research.

This is an identity/availability adapter, NOT a license to trade new markets.
The original seven-market production authority and market memories stay frozen.
New market/anchor memory is honestly UNKNOWN until a causally bounded research
snapshot is independently versioned; do not reuse other traders' or markets' PnL.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, fields
from datetime import datetime
from typing import Final

from qore.infrastructure.traders.vt08_cognitive_situation_model import (
    Vt08ForexSituationModel,
)
from qore.infrastructure.traders.vt08_cognitive_strategy_identity_memory import (
    strategy_identity_fingerprint,
)
from qore.infrastructure.traders.vt08_cognitive_v1_contracts import (
    architecture_fingerprint,
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
RESEARCH_SITUATION_SCHEMA: Final = "qore.vt08.cognitive_5m.situation.research.v2"

# The producer must timestamp EACH decision and journey input. No fallback to
# a single all-purpose latest-bar timestamp is accepted. This is a provenance
# attestation contract; a later integration test must independently prove that
# each timestamp actually describes its source data.
CAUSAL_FIELDS: Final = tuple(
    item.name for item in fields(Vt08ForexSituationModel)
    if item.name not in {
        "as_of", "market", "anchor_hour_ny", "side", "ltf_profile",
        "terminal_pnl", "post_outcome_label",
    }
)


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
    feature_cutoffs: tuple[tuple[str, datetime], ...] = ()
    source_cycle_id: str = ""
    cycle_expires_at: datetime | None = None
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
        if not isinstance(self.source_cycle_id, str) or not self.source_cycle_id.strip():
            raise ValueError("VT08 research situation requires H4 source cycle id")
        expiry = self.cycle_expires_at
        if expiry is None or expiry.tzinfo is None or expiry.utcoffset() is None:
            raise ValueError("VT08 research situation requires timezone-aware cycle expiry")
        if not isinstance(self.feature_cutoffs, tuple):
            raise ValueError("VT08 research feature cutoffs must be immutable tuple")
        if len(self.feature_cutoffs) != len(CAUSAL_FIELDS):
            raise ValueError("VT08 research needs complete feature causal cutoffs")
        observed_fields: list[str] = []
        feature_max: datetime | None = None
        for feature in self.feature_cutoffs:
            if not isinstance(feature, tuple) or len(feature) != 2:
                raise ValueError("VT08 research requires immutable feature/time pairs")
            name, cutoff = feature
            if not isinstance(name, str) or name not in CAUSAL_FIELDS:
                raise ValueError("VT08 research contains unknown feature cutoff")
            if not isinstance(cutoff, datetime) or (
                cutoff.tzinfo is None or cutoff.utcoffset() is None
            ):
                raise ValueError("VT08 research feature cutoff must be timezone-aware")
            if cutoff > self.as_of:
                raise ValueError("VT08 research feature cutoff consumes future information")
            observed_fields.append(name)
            if feature_max is None or cutoff > feature_max:
                feature_max = cutoff
        if tuple(observed_fields) != CAUSAL_FIELDS:
            raise ValueError("VT08 research feature cutoffs incomplete, duplicate or unordered")
        if observed != feature_max:
            raise ValueError("VT08 latest closed bar must match maximum feature cutoff")

    def payload(self) -> dict[str, object]:
        """Canonical JSON-safe event payload, including every feature timestamp."""
        result = super().payload()
        result["schema"] = RESEARCH_SITUATION_SCHEMA
        result["feature_cutoffs"] = tuple(
            (name, timestamp.isoformat()) for name, timestamp in self.feature_cutoffs
        )
        if self.cycle_expires_at is not None:
            result["cycle_expires_at"] = self.cycle_expires_at.isoformat()
        return result


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


def research_strategy_identity_fingerprint() -> str:
    """Add five-market research scope without modifying certified identity."""
    payload = {
        "schema": "qore.vt08.cognitive_5m.strategy_identity.research.v1",
        "scope": RESEARCH_SCOPE_ID,
        "parent_strategy_identity_fingerprint": strategy_identity_fingerprint(),
        "markets": RESEARCH_MARKETS,
        "anchors": tuple(OWNER_FOREX_ANCHORS),
        "operational_authority": False,
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def research_cognitive_memory_fingerprint() -> str:
    """Research MEMORY_UNKNOWN envelope, not the seven-market memory's data."""
    payload = {
        "schema": "qore.vt08.cognitive_5m.memory_bundle.research.v1",
        "scope": RESEARCH_SCOPE_ID,
        "architecture": architecture_fingerprint(),
        "strategy": research_strategy_identity_fingerprint(),
        "markets": RESEARCH_MARKETS,
        "state": MEMORY_STATE,
        "temporal_coverage": "NOT_VALIDATED",
        "runtime_self_training": False,
        "operational_authority": False,
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
