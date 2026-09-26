"""Exact causal alignment forensics between Capitalizer M5 events and CIBO Journey.

This research layer joins two already-consumed evidence streams:
- Capitalizer decision-time M5 transition events; and
- CIBO Market Journey causal raid/reclaim/departure events.

The join uses exact event timing only. It does not tune a lookback window, use target-touch
outcomes as context, rank configurations, or promote an operating rule.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from statistics import median
from typing import Any

from qore.infrastructure.trader_lab.capitalizer_atlas_m5_reader import (
    BAR_DURATION,
    CapitalizerM5Bar,
    iter_atlas_m5,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_microstructure_discovery import (
    CapitalizerMicrostructureEvent,
    classify_microstructure_events,
    designated_session,
)
from qore.infrastructure.trader_lab.capitalizer_session_clock import capitalizer_session_at

JOURNEY_IDENTITY = "CIBO_MARKET_JOURNEY_LAYER_V1"
JOURNEY_SCHEMA = "qore.cibo_market_atlas.market_journey.v1"
HORIZON_BARS = (3, 6, 12)


class CapitalizerCiboEventKind(StrEnum):
    RAID = "RAID"
    RECLAIM = "RECLAIM"
    DEPARTURE = "DEPARTURE"


_DIRECTIONAL_EVENTS: dict[CapitalizerMicrostructureEvent, CapitalizerSide] = {
    CapitalizerMicrostructureEvent.HIGH_RAID_REJECTION: CapitalizerSide.SHORT,
    CapitalizerMicrostructureEvent.LOW_RAID_REJECTION: CapitalizerSide.LONG,
    CapitalizerMicrostructureEvent.HIGH_ACCEPTANCE: CapitalizerSide.LONG,
    CapitalizerMicrostructureEvent.LOW_ACCEPTANCE: CapitalizerSide.SHORT,
}


@dataclass(frozen=True, slots=True)
class CapitalizerCiboJourneyEvent:
    kind: CapitalizerCiboEventKind
    observed_at: datetime
    side: CapitalizerSide
    timeframe: str
    episode_id: str

    def __post_init__(self) -> None:
        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise ValueError("CIBO event timestamp must be timezone-aware")
        if self.timeframe not in {"H1", "H4", "D1"}:
            raise ValueError("unsupported CIBO Journey timeframe")
        if not self.episode_id:
            raise ValueError("CIBO Journey event requires episode_id")


@dataclass(frozen=True, slots=True)
class CapitalizerCiboAlignmentResponse:
    symbol: str
    event: CapitalizerMicrostructureEvent
    side: CapitalizerSide
    context_tag: str
    decision_at: datetime
    horizon_minutes: int
    source_range: Decimal
    favorable_range_units: Decimal
    adverse_range_units: Decimal
    close_displacement_range_units: Decimal
    outcome_only: bool = True

    def __post_init__(self) -> None:
        if self.source_range <= 0:
            raise ValueError("source range must be positive")
        if self.horizon_minutes <= 0 or self.horizon_minutes % 5:
            raise ValueError("horizon must be a positive M5 multiple")
        if self.favorable_range_units < 0 or self.adverse_range_units < 0:
            raise ValueError("MFE/MAE must be non-negative")
        if not self.context_tag:
            raise ValueError("context tag must be non-empty")
        if not self.outcome_only:
            raise ValueError("alignment response must remain outcome-only")


@dataclass(frozen=True, slots=True)
class CapitalizerCiboAlignmentAggregate:
    event: CapitalizerMicrostructureEvent
    context_tag: str
    horizon_minutes: int
    observations: int
    positive_close_rate: str
    median_close_displacement_range_units: str
    median_favorable_range_units: str
    median_adverse_range_units: str


@dataclass(frozen=True, slots=True)
class CapitalizerCiboAlignmentAnnual:
    event: CapitalizerMicrostructureEvent
    context_tag: str
    horizon_minutes: int
    year: int
    observations: int
    positive_close_rate: str
    median_close_displacement_range_units: str


@dataclass(frozen=True, slots=True)
class CapitalizerCiboAlignmentReport:
    identity: str
    symbol: str
    session: str
    aggregates: tuple[CapitalizerCiboAlignmentAggregate, ...]
    annual: tuple[CapitalizerCiboAlignmentAnnual, ...]
    total_labeled_responses: int
    evidence_status: str = "CONSUMED_RESEARCH_EVIDENCE"
    context_fields_causal: bool = True
    outcome_fields_causal: bool = False
    lookback_tuning_used: bool = False
    rule_promotion_allowed: bool = False
    candidate_freeze_allowed: bool = False


def _dt(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValueError("Journey timestamp must be ISO string")
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("Journey timestamp must be timezone-aware")
    return parsed


def _side(value: object) -> CapitalizerSide:
    if value == "long":
        return CapitalizerSide.LONG
    if value == "short":
        return CapitalizerSide.SHORT
    raise ValueError("Journey side must be long/short")


def load_causal_journey_events(root: Path) -> tuple[CapitalizerCiboJourneyEvent, ...]:
    """Load only Journey fields explicitly marked causal/non-outcome."""

    path = root / "MARKET_JOURNEY_LEDGER.jsonl"
    if not path.exists():
        raise ValueError("MARKET_JOURNEY_LEDGER.jsonl not found")

    result: list[CapitalizerCiboJourneyEvent] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError("Journey row must be an object")
            if row.get("identity") != JOURNEY_IDENTITY or row.get("schema") != JOURNEY_SCHEMA:
                raise ValueError("unexpected Journey identity/schema")
            if row.get("causal_feature") is not True or row.get("outcome_only") is not False:
                raise ValueError("Journey context must be causal and non-outcome")
            side = _side(row.get("side"))
            timeframe = str(row.get("source_timeframe"))
            episode_id = str(row.get("episode_id"))
            result.append(
                CapitalizerCiboJourneyEvent(
                    kind=CapitalizerCiboEventKind.RAID,
                    observed_at=_dt(row.get("liquidity_raid_at")),
                    side=side,
                    timeframe=timeframe,
                    episode_id=episode_id,
                )
            )
            reclaim_at = row.get("reclaim_at")
            if reclaim_at is not None:
                result.append(
                    CapitalizerCiboJourneyEvent(
                        kind=CapitalizerCiboEventKind.RECLAIM,
                        observed_at=_dt(reclaim_at),
                        side=side,
                        timeframe=timeframe,
                        episode_id=episode_id,
                    )
                )
            departure_at = row.get("departure_at")
            if departure_at is not None:
                if row.get("departure_detector") != "CAUSAL_CISD_V1":
                    raise ValueError("resolved departure must use CAUSAL_CISD_V1")
                result.append(
                    CapitalizerCiboJourneyEvent(
                        kind=CapitalizerCiboEventKind.DEPARTURE,
                        observed_at=_dt(departure_at),
                        side=side,
                        timeframe=timeframe,
                        episode_id=episode_id,
                    )
                )
    return tuple(
        sorted(
            result,
            key=lambda item: (
                item.observed_at,
                item.kind.value,
                item.timeframe,
                item.episode_id,
            ),
        )
    )


def _event_index(
    events: tuple[CapitalizerCiboJourneyEvent, ...],
) -> dict[tuple[CapitalizerCiboEventKind, datetime], tuple[CapitalizerCiboJourneyEvent, ...]]:
    grouped: dict[
        tuple[CapitalizerCiboEventKind, datetime],
        list[CapitalizerCiboJourneyEvent],
    ] = defaultdict(list)
    for event in events:
        grouped[(event.kind, event.observed_at)].append(event)
    return {key: tuple(value) for key, value in grouped.items()}


def _context_tags(
    *,
    bar: CapitalizerM5Bar,
    side: CapitalizerSide,
    index: dict[
        tuple[CapitalizerCiboEventKind, datetime],
        tuple[CapitalizerCiboJourneyEvent, ...],
    ],
) -> tuple[str, ...]:
    """Return only exact CIBO events available no later than this bar close."""

    matched: set[str] = set()
    # Journey raid_at records the M5 bar open containing the raid. It is known by this bar close.
    raid_events = index.get((CapitalizerCiboEventKind.RAID, bar.opened_at), ())
    for event in raid_events:
        relation = "ALIGNED" if event.side is side else "OPPOSED"
        matched.add(f"RAID_{relation}_{event.timeframe}")

    # Reclaim/departure are confirmation instants and must equal the current decision time.
    for kind in (CapitalizerCiboEventKind.RECLAIM, CapitalizerCiboEventKind.DEPARTURE):
        for event in index.get((kind, bar.closed_at), ()):
            relation = "ALIGNED" if event.side is side else "OPPOSED"
            matched.add(f"{kind.value}_{relation}_{event.timeframe}")

    if not matched:
        return ("NO_EXACT_CIBO_EVENT",)
    return tuple(sorted(matched))


def _future(
    bars: tuple[CapitalizerM5Bar, ...],
    *,
    source_index: int,
    count: int,
) -> tuple[CapitalizerM5Bar, ...] | None:
    end = source_index + count
    if end >= len(bars):
        return None
    source = bars[source_index]
    future = bars[source_index + 1 : end + 1]
    if any(
        bar.opened_at != source.opened_at + BAR_DURATION * offset
        for offset, bar in enumerate(future, start=1)
    ):
        return None
    return future


def _response(
    *,
    source: CapitalizerM5Bar,
    future: tuple[CapitalizerM5Bar, ...],
    event: CapitalizerMicrostructureEvent,
    side: CapitalizerSide,
    context_tag: str,
) -> CapitalizerCiboAlignmentResponse:
    anchor = source.close
    if side is CapitalizerSide.LONG:
        favorable = max(bar.high for bar in future) - anchor
        adverse = anchor - min(bar.low for bar in future)
        close_delta = future[-1].close - anchor
    else:
        favorable = anchor - min(bar.low for bar in future)
        adverse = max(bar.high for bar in future) - anchor
        close_delta = anchor - future[-1].close
    return CapitalizerCiboAlignmentResponse(
        symbol=source.symbol,
        event=event,
        side=side,
        context_tag=context_tag,
        decision_at=source.closed_at,
        horizon_minutes=len(future) * 5,
        source_range=source.range,
        favorable_range_units=max(favorable, Decimal("0")) / source.range,
        adverse_range_units=max(adverse, Decimal("0")) / source.range,
        close_displacement_range_units=close_delta / source.range,
    )


def build_cibo_alignment_responses(
    *,
    m5_root: Path,
    journey_root: Path,
) -> tuple[CapitalizerCiboAlignmentResponse, ...]:
    """Build exact causal-context / future-outcome rows for one market."""

    bars = tuple(iter_atlas_m5(m5_root))
    if not bars:
        raise ValueError("M5 artifact contained no bars")
    session = designated_session(bars[0].symbol)
    journey = load_causal_journey_events(journey_root)
    index = _event_index(journey)
    responses: list[CapitalizerCiboAlignmentResponse] = []

    for position in range(1, len(bars)):
        current = bars[position]
        previous = bars[position - 1]
        if current.opened_at - previous.opened_at != BAR_DURATION:
            continue
        if capitalizer_session_at(current.opened_at) is not session:
            continue
        if current.range <= 0:
            continue

        observed = classify_microstructure_events(current, previous)
        directional = tuple(
            (event, _DIRECTIONAL_EVENTS[event])
            for event in observed
            if event in _DIRECTIONAL_EVENTS
        )
        if not directional:
            continue
        if len({side for _, side in directional}) != 1:
            continue

        for event, side in directional:
            tags = _context_tags(bar=current, side=side, index=index)
            for count in HORIZON_BARS:
                future = _future(bars, source_index=position, count=count)
                if future is None:
                    continue
                for tag in tags:
                    responses.append(
                        _response(
                            source=current,
                            future=future,
                            event=event,
                            side=side,
                            context_tag=tag,
                        )
                    )
    return tuple(responses)


def _aggregate(
    group: tuple[CapitalizerCiboAlignmentResponse, ...],
) -> tuple[str, str, str, str]:
    positive = sum(item.close_displacement_range_units > 0 for item in group)
    return (
        str(Decimal(positive) / Decimal(len(group))),
        str(median(item.close_displacement_range_units for item in group)),
        str(median(item.favorable_range_units for item in group)),
        str(median(item.adverse_range_units for item in group)),
    )


def summarize_cibo_alignment(
    responses: tuple[CapitalizerCiboAlignmentResponse, ...],
) -> CapitalizerCiboAlignmentReport:
    if not responses:
        raise ValueError("CIBO alignment report requires responses")
    symbol = responses[0].symbol
    if any(item.symbol != symbol for item in responses):
        raise ValueError("CIBO alignment report requires one symbol")

    grouped: dict[
        tuple[CapitalizerMicrostructureEvent, str, int],
        list[CapitalizerCiboAlignmentResponse],
    ] = defaultdict(list)
    annual_grouped: dict[
        tuple[CapitalizerMicrostructureEvent, str, int, int],
        list[CapitalizerCiboAlignmentResponse],
    ] = defaultdict(list)
    for item in responses:
        grouped[(item.event, item.context_tag, item.horizon_minutes)].append(item)
        annual_grouped[
            (
                item.event,
                item.context_tag,
                item.horizon_minutes,
                item.decision_at.year,
            )
        ].append(item)

    aggregates: list[CapitalizerCiboAlignmentAggregate] = []
    for (event, tag, horizon), raw in sorted(
        grouped.items(),
        key=lambda item: (item[0][0].value, item[0][1], item[0][2]),
    ):
        group = tuple(raw)
        positive, med_close, med_favorable, med_adverse = _aggregate(group)
        aggregates.append(
            CapitalizerCiboAlignmentAggregate(
                event=event,
                context_tag=tag,
                horizon_minutes=horizon,
                observations=len(group),
                positive_close_rate=positive,
                median_close_displacement_range_units=med_close,
                median_favorable_range_units=med_favorable,
                median_adverse_range_units=med_adverse,
            )
        )

    annual: list[CapitalizerCiboAlignmentAnnual] = []
    for (event, tag, horizon, year), raw in sorted(
        annual_grouped.items(),
        key=lambda item: (item[0][0].value, item[0][1], item[0][2], item[0][3]),
    ):
        group = tuple(raw)
        positive, med_close, _, _ = _aggregate(group)
        annual.append(
            CapitalizerCiboAlignmentAnnual(
                event=event,
                context_tag=tag,
                horizon_minutes=horizon,
                year=year,
                observations=len(group),
                positive_close_rate=positive,
                median_close_displacement_range_units=med_close,
            )
        )

    return CapitalizerCiboAlignmentReport(
        identity="QORE_CAPITALIZER_CIBO_ALIGNMENT_FORENSICS_V1",
        symbol=symbol,
        session=designated_session(symbol).value,
        aggregates=tuple(aggregates),
        annual=tuple(annual),
        total_labeled_responses=len(responses),
    )


def write_cibo_alignment_report(
    report: CapitalizerCiboAlignmentReport,
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / f"capitalizer-{report.symbol.lower()}-cibo-alignment-v1.json"
    payload: dict[str, Any] = asdict(report)
    for row in payload["aggregates"]:
        row["event"] = row["event"].value
    for row in payload["annual"]:
        row["event"] = row["event"].value
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Capitalizer exact CIBO alignment forensics")
    parser.add_argument("m5_root", type=Path)
    parser.add_argument("journey_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    responses = build_cibo_alignment_responses(
        m5_root=args.m5_root,
        journey_root=args.journey_root,
    )
    report = summarize_cibo_alignment(responses)
    write_cibo_alignment_report(report, args.output)
    print(
        json.dumps(
            {
                "identity": report.identity,
                "symbol": report.symbol,
                "session": report.session,
                "total_labeled_responses": report.total_labeled_responses,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
