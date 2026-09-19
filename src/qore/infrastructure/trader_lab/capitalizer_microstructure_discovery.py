"""Causal M5 microstructure discovery for the QORE Capitalizer.

The scanner derives threshold-light, source-compatible structural observations from each
completed M5 bar relative to the previous completed M5 bar. It is descriptive only: it does
not select trades or claim edge.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from statistics import median

from qore.infrastructure.trader_lab.capitalizer_atlas_m5_reader import (
    BAR_DURATION,
    CapitalizerM5Bar,
    iter_atlas_m5,
)
from qore.infrastructure.trader_lab.capitalizer_contract import CapitalizerSession
from qore.infrastructure.trader_lab.capitalizer_research_lineage import (
    CAPITALIZER_CONSUMED_LINEAGE,
)
from qore.infrastructure.trader_lab.capitalizer_session_clock import (
    capitalizer_session_at,
)


class CapitalizerMicrostructureEvent(StrEnum):
    INSIDE_BAR = "INSIDE_BAR"
    OUTSIDE_BAR = "OUTSIDE_BAR"
    HIGH_RAID_REJECTION = "HIGH_RAID_REJECTION"
    LOW_RAID_REJECTION = "LOW_RAID_REJECTION"
    HIGH_ACCEPTANCE = "HIGH_ACCEPTANCE"
    LOW_ACCEPTANCE = "LOW_ACCEPTANCE"
    HIGH_BREAK_ATTEMPT = "HIGH_BREAK_ATTEMPT"
    LOW_BREAK_ATTEMPT = "LOW_BREAK_ATTEMPT"


@dataclass(frozen=True, slots=True)
class CapitalizerM5MicroObservation:
    symbol: str
    session: CapitalizerSession
    bar_opened_at: datetime
    decision_at: datetime
    events: tuple[CapitalizerMicrostructureEvent, ...]
    range_price: Decimal
    body_price: Decimal
    body_fraction: Decimal
    close_location: Decimal
    previous_range_ratio: Decimal | None

    def __post_init__(self) -> None:
        if self.decision_at <= self.bar_opened_at:
            raise ValueError("microstructure decision must follow bar open")
        if self.range_price < 0 or self.body_price < 0:
            raise ValueError("range/body must be non-negative")
        if not Decimal("0") <= self.body_fraction <= Decimal("1"):
            raise ValueError("body_fraction must be within 0..1")
        if not Decimal("0") <= self.close_location <= Decimal("1"):
            raise ValueError("close_location must be within 0..1")
        if self.previous_range_ratio is not None and self.previous_range_ratio < 0:
            raise ValueError("previous_range_ratio must be non-negative")


@dataclass(frozen=True, slots=True)
class CapitalizerMicrostructureSummary:
    identity: str
    symbol: str
    session: CapitalizerSession
    observations: int
    event_counts: dict[str, int]
    event_rates: dict[str, str]
    median_range_price: str
    median_body_fraction: str
    median_previous_range_ratio: str | None
    research_only: bool = True
    rule_promotion_allowed: bool = False


def _events(
    current: CapitalizerM5Bar,
    previous: CapitalizerM5Bar,
) -> tuple[CapitalizerMicrostructureEvent, ...]:
    events: set[CapitalizerMicrostructureEvent] = set()

    if current.high < previous.high and current.low > previous.low:
        events.add(CapitalizerMicrostructureEvent.INSIDE_BAR)
    if current.high > previous.high and current.low < previous.low:
        events.add(CapitalizerMicrostructureEvent.OUTSIDE_BAR)

    if current.high > previous.high:
        events.add(CapitalizerMicrostructureEvent.HIGH_BREAK_ATTEMPT)
        if current.close < previous.high:
            events.add(CapitalizerMicrostructureEvent.HIGH_RAID_REJECTION)
        elif current.close > previous.high:
            events.add(CapitalizerMicrostructureEvent.HIGH_ACCEPTANCE)

    if current.low < previous.low:
        events.add(CapitalizerMicrostructureEvent.LOW_BREAK_ATTEMPT)
        if current.close > previous.low:
            events.add(CapitalizerMicrostructureEvent.LOW_RAID_REJECTION)
        elif current.close < previous.low:
            events.add(CapitalizerMicrostructureEvent.LOW_ACCEPTANCE)

    return tuple(sorted(events, key=lambda item: item.value))


def _observation(
    current: CapitalizerM5Bar,
    previous: CapitalizerM5Bar,
    *,
    session: CapitalizerSession,
) -> CapitalizerM5MicroObservation:
    current_range = current.range
    body_fraction = (
        current.body / current_range if current_range > 0 else Decimal("0")
    )
    close_location = (
        (current.close - current.low) / current_range
        if current_range > 0
        else Decimal("0.5")
    )
    previous_range_ratio = (
        current_range / previous.range if previous.range > 0 else None
    )
    return CapitalizerM5MicroObservation(
        symbol=current.symbol,
        session=session,
        bar_opened_at=current.opened_at,
        decision_at=current.closed_at,
        events=_events(current, previous),
        range_price=current_range,
        body_price=current.body,
        body_fraction=body_fraction,
        close_location=close_location,
        previous_range_ratio=previous_range_ratio,
    )


def designated_session(symbol: str) -> CapitalizerSession:
    matches = tuple(
        item.session for item in CAPITALIZER_CONSUMED_LINEAGE if item.symbol == symbol
    )
    if len(matches) != 1:
        raise ValueError(f"symbol must have exactly one Capitalizer session: {symbol}")
    return matches[0]


def scan_microstructure(root: Path) -> tuple[CapitalizerM5MicroObservation, ...]:
    """Scan only the symbol's frozen Capitalizer research session."""

    result: list[CapitalizerM5MicroObservation] = []
    previous: CapitalizerM5Bar | None = None
    expected_session: CapitalizerSession | None = None

    for current in iter_atlas_m5(root):
        if expected_session is None:
            expected_session = designated_session(current.symbol)
        if previous is not None:
            observed_session = capitalizer_session_at(current.opened_at)
            is_contiguous_m5 = current.opened_at - previous.opened_at == BAR_DURATION
            if observed_session is expected_session and is_contiguous_m5:
                result.append(
                    _observation(
                        current,
                        previous,
                        session=expected_session,
                    )
                )
        previous = current

    if expected_session is None:
        raise ValueError("M5 artifact contained no bars")
    return tuple(result)


def summarize_microstructure(
    observations: tuple[CapitalizerM5MicroObservation, ...],
) -> CapitalizerMicrostructureSummary:
    if not observations:
        raise ValueError("microstructure summary requires observations")
    symbol = observations[0].symbol
    session = observations[0].session
    if any(item.symbol != symbol or item.session is not session for item in observations):
        raise ValueError("summary requires one symbol/session cell")

    counts: Counter[str] = Counter(
        event.value for item in observations for event in item.events
    )
    total = len(observations)
    rates = {
        event.value: str(Decimal(counts[event.value]) / Decimal(total))
        for event in CapitalizerMicrostructureEvent
    }
    ratios = tuple(
        item.previous_range_ratio
        for item in observations
        if item.previous_range_ratio is not None
    )
    return CapitalizerMicrostructureSummary(
        identity="QORE_CAPITALIZER_M5_MICROSTRUCTURE_DISCOVERY_V1",
        symbol=symbol,
        session=session,
        observations=total,
        event_counts={event.value: counts[event.value] for event in CapitalizerMicrostructureEvent},
        event_rates=rates,
        median_range_price=str(median(item.range_price for item in observations)),
        median_body_fraction=str(median(item.body_fraction for item in observations)),
        median_previous_range_ratio=(
            str(median(ratios)) if ratios else None
        ),
    )


def write_microstructure_summary(
    summary: CapitalizerMicrostructureSummary,
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / f"capitalizer-{summary.symbol.lower()}-microstructure-v1.json"
    payload = asdict(summary)
    payload["session"] = summary.session.value
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Capitalizer M5 microstructure discovery")
    parser.add_argument("artifact_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    observations = scan_microstructure(args.artifact_root)
    summary = summarize_microstructure(observations)
    write_microstructure_summary(summary, args.output)
    print(json.dumps({**asdict(summary), "session": summary.session.value}, sort_keys=True))


if __name__ == "__main__":
    main()
