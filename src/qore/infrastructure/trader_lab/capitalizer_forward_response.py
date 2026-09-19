"""Outcome-only forward-response study for Capitalizer M5 transition events.

Decision-time event detection and post-decision response are intentionally separated. Future
bars are used only to label research outcomes and are never returned as causal features.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from statistics import median

from qore.infrastructure.trader_lab.capitalizer_atlas_m5_reader import (
    BAR_DURATION,
    CapitalizerM5Bar,
    iter_atlas_m5,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_microstructure_discovery import (
    CapitalizerMicrostructureEvent,
    _events,
    designated_session,
)
from qore.infrastructure.trader_lab.capitalizer_session_clock import capitalizer_session_at


HORIZON_BARS = (1, 2, 3, 6, 12)


class CapitalizerForwardEvent(StrEnum):
    HIGH_RAID_REJECTION = CapitalizerMicrostructureEvent.HIGH_RAID_REJECTION.value
    LOW_RAID_REJECTION = CapitalizerMicrostructureEvent.LOW_RAID_REJECTION.value
    HIGH_ACCEPTANCE = CapitalizerMicrostructureEvent.HIGH_ACCEPTANCE.value
    LOW_ACCEPTANCE = CapitalizerMicrostructureEvent.LOW_ACCEPTANCE.value


_EVENT_SIDE: dict[CapitalizerForwardEvent, CapitalizerSide] = {
    CapitalizerForwardEvent.HIGH_RAID_REJECTION: CapitalizerSide.SHORT,
    CapitalizerForwardEvent.LOW_RAID_REJECTION: CapitalizerSide.LONG,
    CapitalizerForwardEvent.HIGH_ACCEPTANCE: CapitalizerSide.LONG,
    CapitalizerForwardEvent.LOW_ACCEPTANCE: CapitalizerSide.SHORT,
}


@dataclass(frozen=True, slots=True)
class CapitalizerForwardResponse:
    symbol: str
    event: CapitalizerForwardEvent
    side: CapitalizerSide
    decision_at: str
    horizon_minutes: int
    source_range: Decimal
    favorable_range_units: Decimal
    adverse_range_units: Decimal
    close_displacement_range_units: Decimal
    outcome_only: bool = True

    def __post_init__(self) -> None:
        if self.source_range <= 0:
            raise ValueError("forward response source range must be positive")
        if self.horizon_minutes <= 0 or self.horizon_minutes % 5:
            raise ValueError("forward response horizon must be positive M5 multiple")
        if self.favorable_range_units < 0 or self.adverse_range_units < 0:
            raise ValueError("MFE/MAE range units must be non-negative")
        if not self.outcome_only:
            raise ValueError("forward response must remain outcome-only")


@dataclass(frozen=True, slots=True)
class CapitalizerForwardAggregate:
    event: CapitalizerForwardEvent
    side: CapitalizerSide
    horizon_minutes: int
    observations: int
    median_favorable_range_units: str
    median_adverse_range_units: str
    median_close_displacement_range_units: str
    positive_close_rate: str


@dataclass(frozen=True, slots=True)
class CapitalizerForwardResponseReport:
    identity: str
    symbol: str
    session: str
    aggregates: tuple[CapitalizerForwardAggregate, ...]
    total_labeled_responses: int
    evidence_status: str = "CONSUMED_RESEARCH_EVIDENCE"
    causal_feature_allowed: bool = False
    rule_promotion_allowed: bool = False


def _directional_delta(value: Decimal, anchor: Decimal, side: CapitalizerSide) -> Decimal:
    return value - anchor if side is CapitalizerSide.LONG else anchor - value


def _response(
    *,
    source: CapitalizerM5Bar,
    future: tuple[CapitalizerM5Bar, ...],
    event: CapitalizerForwardEvent,
) -> CapitalizerForwardResponse:
    side = _EVENT_SIDE[event]
    anchor = source.close
    if side is CapitalizerSide.LONG:
        favorable = max(bar.high for bar in future) - anchor
        adverse = anchor - min(bar.low for bar in future)
    else:
        favorable = anchor - min(bar.low for bar in future)
        adverse = max(bar.high for bar in future) - anchor
    favorable = max(favorable, Decimal("0"))
    adverse = max(adverse, Decimal("0"))
    return CapitalizerForwardResponse(
        symbol=source.symbol,
        event=event,
        side=side,
        decision_at=source.closed_at.isoformat(),
        horizon_minutes=len(future) * 5,
        source_range=source.range,
        favorable_range_units=favorable / source.range,
        adverse_range_units=adverse / source.range,
        close_displacement_range_units=(
            _directional_delta(future[-1].close, anchor, side) / source.range
        ),
    )


def _exact_contiguous_future(
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
    for offset, bar in enumerate(future, start=1):
        if bar.opened_at != source.opened_at + BAR_DURATION * offset:
            return None
    return future


def build_forward_responses(root: Path) -> tuple[CapitalizerForwardResponse, ...]:
    """Label four directional transition events over fixed post-decision horizons."""

    bars = tuple(iter_atlas_m5(root))
    if not bars:
        raise ValueError("M5 artifact contained no bars")
    session = designated_session(bars[0].symbol)
    result: list[CapitalizerForwardResponse] = []

    for index in range(1, len(bars)):
        current = bars[index]
        previous = bars[index - 1]
        if current.opened_at - previous.opened_at != BAR_DURATION:
            continue
        if capitalizer_session_at(current.opened_at) is not session:
            continue
        if current.range <= 0:
            continue

        observed = set(_events(current, previous))
        directional = tuple(
            event
            for event in CapitalizerForwardEvent
            if CapitalizerMicrostructureEvent(event.value) in observed
        )
        if not directional:
            continue

        for count in HORIZON_BARS:
            future = _exact_contiguous_future(bars, source_index=index, count=count)
            if future is None:
                continue
            for event in directional:
                result.append(_response(source=current, future=future, event=event))

    return tuple(result)


def summarize_forward_responses(
    responses: tuple[CapitalizerForwardResponse, ...],
) -> CapitalizerForwardResponseReport:
    if not responses:
        raise ValueError("forward response report requires labeled responses")
    symbol = responses[0].symbol
    if any(item.symbol != symbol for item in responses):
        raise ValueError("forward response report requires one symbol")
    session = designated_session(symbol)

    aggregates: list[CapitalizerForwardAggregate] = []
    for event in CapitalizerForwardEvent:
        side = _EVENT_SIDE[event]
        for count in HORIZON_BARS:
            horizon = count * 5
            group = tuple(
                item
                for item in responses
                if item.event is event and item.horizon_minutes == horizon
            )
            if not group:
                continue
            positive = sum(item.close_displacement_range_units > 0 for item in group)
            aggregates.append(
                CapitalizerForwardAggregate(
                    event=event,
                    side=side,
                    horizon_minutes=horizon,
                    observations=len(group),
                    median_favorable_range_units=str(
                        median(item.favorable_range_units for item in group)
                    ),
                    median_adverse_range_units=str(
                        median(item.adverse_range_units for item in group)
                    ),
                    median_close_displacement_range_units=str(
                        median(item.close_displacement_range_units for item in group)
                    ),
                    positive_close_rate=str(Decimal(positive) / Decimal(len(group))),
                )
            )

    return CapitalizerForwardResponseReport(
        identity="QORE_CAPITALIZER_FORWARD_RESPONSE_V1",
        symbol=symbol,
        session=session.value,
        aggregates=tuple(aggregates),
        total_labeled_responses=len(responses),
    )


def write_forward_response_report(
    report: CapitalizerForwardResponseReport,
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / f"capitalizer-{report.symbol.lower()}-forward-response-v1.json"
    payload = asdict(report)
    for row in payload["aggregates"]:
        row["event"] = row["event"].value
        row["side"] = row["side"].value
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Capitalizer M5 outcome-only forward response")
    parser.add_argument("artifact_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    responses = build_forward_responses(args.artifact_root)
    report = summarize_forward_responses(responses)
    write_forward_response_report(report, args.output)
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
