"""X-01/X-02/X-03 Opportunity Surface, Rarity and Asymmetry.

These are descriptive cognition layers over STI-3. They never encode order,
capital, Risk or Trader-methodology priority.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import StrEnum

from qore.infrastructure.core_stack_v2.shared_global_opportunity_board import (
    SharedGlobalOpportunityAttentionBoard,
    SharedOpportunityBoardEntry,
)
from qore.infrastructure.core_stack_v2.shared_trader_intelligence import (
    SharedTraderIntelligenceValidationError,
)


class SharedOpportunityRarityState(StrEnum):
    COMMON = "COMMON"
    UNCOMMON = "UNCOMMON"
    RARE = "RARE"
    VERY_RARE = "VERY_RARE"
    INSUFFICIENT = "INSUFFICIENT"


@dataclass(frozen=True, slots=True)
class SharedOpportunitySurfacePoint:
    candidate_id: str
    market: str
    horizon: str
    maturity: str
    trajectory: str | None
    support_bps: int
    contradiction_bps: int
    uncertainty_bps: int
    data_health_bps: int
    rarity_bps: int
    rarity_state: SharedOpportunityRarityState
    evidence_asymmetry_bps: int
    relevant_traders: tuple[str, ...]
    provenance_refs: tuple[str, ...]
    attention_only: bool = True
    order_priority: bool = False
    capital_priority: bool = False

    def __post_init__(self) -> None:
        for name in (
            "candidate_id",
            "market",
            "horizon",
            "maturity",
        ):
            if not str(getattr(self, name)).strip():
                raise SharedTraderIntelligenceValidationError(
                    f"{name} must be non-empty"
                )
        for name in (
            "support_bps",
            "contradiction_bps",
            "uncertainty_bps",
            "data_health_bps",
            "rarity_bps",
            "evidence_asymmetry_bps",
        ):
            value = getattr(self, name)
            if type(value) is not int or not 0 <= value <= 10_000:
                raise SharedTraderIntelligenceValidationError(
                    f"{name} must be int within 0..10000"
                )
        if self.relevant_traders != tuple(sorted(set(self.relevant_traders))):
            raise SharedTraderIntelligenceValidationError(
                "relevant_traders must be canonical"
            )
        if (
            not self.provenance_refs
            or self.provenance_refs != tuple(sorted(set(self.provenance_refs)))
        ):
            raise SharedTraderIntelligenceValidationError(
                "surface provenance must be non-empty and canonical"
            )
        if not self.attention_only or self.order_priority or self.capital_priority:
            raise SharedTraderIntelligenceValidationError(
                "opportunity surface is descriptive attention only"
            )


@dataclass(frozen=True, slots=True)
class SharedGlobalOpportunitySurface:
    surface_id: str
    as_of: datetime
    history_board_count: int
    points: tuple[SharedOpportunitySurfacePoint, ...]
    canonical_order_only: bool = True
    execution_authority: bool = False
    capital_authority: bool = False
    risk_authority: bool = False

    def __post_init__(self) -> None:
        if not self.surface_id.strip():
            raise SharedTraderIntelligenceValidationError(
                "surface_id must be non-empty"
            )
        if self.as_of.tzinfo is None or self.as_of.utcoffset() is None:
            raise SharedTraderIntelligenceValidationError(
                "surface as_of must be timezone-aware"
            )
        if self.history_board_count < 0:
            raise SharedTraderIntelligenceValidationError(
                "history_board_count cannot be negative"
            )
        keys = tuple(
            (point.market, point.horizon, point.candidate_id)
            for point in self.points
        )
        if keys != tuple(sorted(keys)):
            raise SharedTraderIntelligenceValidationError(
                "surface points must use canonical identity order"
            )
        if (
            not self.canonical_order_only
            or self.execution_authority
            or self.capital_authority
            or self.risk_authority
        ):
            raise SharedTraderIntelligenceValidationError(
                "opportunity surface cannot encode sovereign priority"
            )

    @property
    def is_empty(self) -> bool:
        return not self.points

    def fingerprint(self) -> str:
        payload = asdict(self)
        payload["as_of"] = self.as_of.astimezone(UTC).isoformat()
        for point in payload["points"]:
            point["rarity_state"] = str(point["rarity_state"])
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode()).hexdigest()


def _signature(entry: SharedOpportunityBoardEntry) -> tuple[str, str, str, str]:
    return (
        entry.market,
        entry.horizon,
        entry.maturity.value,
        "NONE" if entry.trajectory is None else entry.trajectory.value,
    )


def _rarity_state(rarity_bps: int) -> SharedOpportunityRarityState:
    if rarity_bps >= 9_500:
        return SharedOpportunityRarityState.VERY_RARE
    if rarity_bps >= 8_000:
        return SharedOpportunityRarityState.RARE
    if rarity_bps >= 5_000:
        return SharedOpportunityRarityState.UNCOMMON
    return SharedOpportunityRarityState.COMMON


def build_global_opportunity_surface(
    *,
    surface_id: str,
    as_of: datetime,
    current_board: SharedGlobalOpportunityAttentionBoard,
    historical_boards: Sequence[SharedGlobalOpportunityAttentionBoard],
) -> SharedGlobalOpportunitySurface:
    if current_board.as_of > as_of:
        raise SharedTraderIntelligenceValidationError(
            "surface cannot consume future current board"
        )
    if any(board.as_of > as_of for board in historical_boards):
        raise SharedTraderIntelligenceValidationError(
            "surface cannot consume future historical board"
        )

    history_entries = [
        entry
        for board in historical_boards
        for entry in board.entries
    ]
    counts = Counter(_signature(entry) for entry in history_entries)
    denominator = max(1, len(historical_boards))

    points = []
    for entry in current_board.entries:
        frequency = counts[_signature(entry)]
        rarity = max(0, 10_000 - min(10_000, frequency * 10_000 // denominator))
        asymmetry = max(
            0,
            min(
                10_000,
                entry.support_bps
                - (entry.contradiction_bps + entry.uncertainty_bps) // 2,
            ),
        )
        points.append(
            SharedOpportunitySurfacePoint(
                candidate_id=entry.candidate_id,
                market=entry.market,
                horizon=entry.horizon,
                maturity=entry.maturity.value,
                trajectory=(
                    None if entry.trajectory is None else entry.trajectory.value
                ),
                support_bps=entry.support_bps,
                contradiction_bps=entry.contradiction_bps,
                uncertainty_bps=entry.uncertainty_bps,
                data_health_bps=entry.data_health_bps,
                rarity_bps=rarity,
                rarity_state=(
                    SharedOpportunityRarityState.INSUFFICIENT
                    if not historical_boards
                    else _rarity_state(rarity)
                ),
                evidence_asymmetry_bps=asymmetry,
                relevant_traders=entry.relevant_traders,
                provenance_refs=entry.provenance_refs,
            )
        )

    return SharedGlobalOpportunitySurface(
        surface_id=surface_id,
        as_of=as_of,
        history_board_count=len(historical_boards),
        points=tuple(
            sorted(
                points,
                key=lambda point: (
                    point.market,
                    point.horizon,
                    point.candidate_id,
                ),
            )
        ),
    )
