"""Causal Target Destination V2 context adapter for QORE Capitalizer.

The adapter exposes only destination facts that existed at CIBO departure time. Post-departure
touch/result fields are deliberately ignored and cannot enter the returned context.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide

TARGET_IDENTITY = "CIBO_TARGET_DESTINATION_V2_SUPPORTED_REFERENCE_UNIVERSE"
TARGET_SCHEMA = "qore.cibo_market_atlas.target_destination.v2"


@dataclass(frozen=True, slots=True)
class CapitalizerTargetCandidate:
    candidate_id: str
    family: str
    timeframe: str
    price: Decimal
    distance_ticks: Decimal
    known_at: datetime
    structural_opened_at: datetime

    def __post_init__(self) -> None:
        if not self.candidate_id or not self.family:
            raise ValueError("target candidate identity/family must be non-empty")
        if self.timeframe not in {"H1", "H4", "D1"}:
            raise ValueError("target candidate timeframe must be H1/H4/D1")
        if self.price <= 0 or self.distance_ticks < 0:
            raise ValueError("target price/distance must be non-negative")
        if self.known_at.tzinfo is None or self.known_at.utcoffset() is None:
            raise ValueError("target known_at must be timezone-aware")
        if (
            self.structural_opened_at.tzinfo is None
            or self.structural_opened_at.utcoffset() is None
        ):
            raise ValueError("target structural timestamp must be timezone-aware")


@dataclass(frozen=True, slots=True)
class CapitalizerTargetContext:
    symbol: str
    side: CapitalizerSide
    departure_at: datetime
    candidates: tuple[CapitalizerTargetCandidate, ...]
    complete_all_dol_claim: bool = False
    post_departure_outcomes_used: bool = False

    def __post_init__(self) -> None:
        if not self.symbol or self.symbol != self.symbol.upper():
            raise ValueError("target context symbol must be uppercase")
        if self.departure_at.tzinfo is None or self.departure_at.utcoffset() is None:
            raise ValueError("target context departure_at must be timezone-aware")
        if self.complete_all_dol_claim:
            raise ValueError("Target V2 does not claim complete DOL coverage")
        if self.post_departure_outcomes_used:
            raise ValueError("Capitalizer target context cannot use future outcomes")
        for candidate in self.candidates:
            if candidate.known_at > self.departure_at:
                raise ValueError("future target candidate cannot enter causal context")

    @property
    def active_candidate_count(self) -> int:
        return len(self.candidates)

    @property
    def nearest_distance_ticks(self) -> Decimal | None:
        if not self.candidates:
            return None
        return min(item.distance_ticks for item in self.candidates)

    @property
    def families(self) -> tuple[str, ...]:
        return tuple(sorted({item.family for item in self.candidates}))

    @property
    def timeframes(self) -> tuple[str, ...]:
        return tuple(sorted({item.timeframe for item in self.candidates}))


def _dt(value: object, *, field_name: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be ISO timestamp string")
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return parsed


def _side(value: object) -> CapitalizerSide:
    if value == "long":
        return CapitalizerSide.LONG
    if value == "short":
        return CapitalizerSide.SHORT
    raise ValueError("target side must be long/short")


def load_target_contexts(root: Path) -> tuple[CapitalizerTargetContext, ...]:
    """Load exact departure-time contexts without reading result/touch values."""

    path = root / "TARGET_DESTINATION_LEDGER_V2.jsonl"
    if not path.exists():
        raise ValueError("TARGET_DESTINATION_LEDGER_V2.jsonl not found")

    grouped: dict[
        tuple[str, CapitalizerSide, datetime],
        dict[tuple[str, str, Decimal, datetime, datetime], CapitalizerTargetCandidate],
    ] = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row: Any = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError("Target V2 row must be an object")
            if row.get("identity") != TARGET_IDENTITY or row.get("schema") != TARGET_SCHEMA:
                raise ValueError("unexpected Target V2 identity/schema")
            if row.get("causal_feature") is not True or row.get("outcome_only") is not False:
                raise ValueError("Target V2 candidate row must be causal/non-outcome")
            if row.get("result_fields_outcome_only") is not True:
                raise ValueError("Target V2 result fields must remain outcome-only")
            if row.get("active_untouched_at_departure") is not True:
                continue

            symbol = str(row.get("symbol"))
            side = _side(row.get("side"))
            departure_at = _dt(row.get("departure_at"), field_name="departure_at")
            known_at = _dt(row.get("candidate_known_at"), field_name="candidate_known_at")
            structural_at = _dt(
                row.get("candidate_structural_opened_at"),
                field_name="candidate_structural_opened_at",
            )
            if known_at > departure_at:
                raise ValueError("Target V2 candidate known after departure")
            candidate = CapitalizerTargetCandidate(
                candidate_id=str(row.get("candidate_id")),
                family=str(row.get("candidate_type")),
                timeframe=str(row.get("source_timeframe")),
                price=Decimal(str(row.get("candidate_price"))),
                distance_ticks=Decimal(str(row.get("candidate_distance_ticks"))),
                known_at=known_at,
                structural_opened_at=structural_at,
            )
            key = (symbol, side, departure_at)
            dedupe = (
                candidate.family,
                candidate.timeframe,
                candidate.price,
                candidate.known_at,
                candidate.structural_opened_at,
            )
            grouped.setdefault(key, {})[dedupe] = candidate

    result = [
        CapitalizerTargetContext(
            symbol=symbol,
            side=side,
            departure_at=departure_at,
            candidates=tuple(
                sorted(
                    candidates.values(),
                    key=lambda item: (
                        item.distance_ticks,
                        item.timeframe,
                        item.family,
                        item.candidate_id,
                    ),
                )
            ),
        )
        for (symbol, side, departure_at), candidates in grouped.items()
    ]
    return tuple(
        sorted(
            result,
            key=lambda item: (item.departure_at, item.symbol, item.side.value),
        )
    )


def target_context_at(
    contexts: tuple[CapitalizerTargetContext, ...],
    *,
    symbol: str,
    side: CapitalizerSide,
    departure_at: datetime,
) -> CapitalizerTargetContext | None:
    matches = tuple(
        item
        for item in contexts
        if item.symbol == symbol
        and item.side is side
        and item.departure_at == departure_at
    )
    if len(matches) > 1:
        raise ValueError("target context key must be unique")
    return None if not matches else matches[0]
