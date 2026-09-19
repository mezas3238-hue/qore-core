"""Causal target-capacity forensics for the frozen Capitalizer/CIBO hypothesis.

This layer measures geometry available at decision time only. It does not simulate a fill,
choose a minimum-R filter, define the final strategy stop, or use target-touch outcomes.

The source M5 extreme is used strictly as a diagnostic invalidation proxy so that structural
capacity can be measured before a candidate contract exists.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path
from statistics import median, quantiles
from typing import Any

from qore.infrastructure.trader_lab.capitalizer_atlas_m5_reader import (
    BAR_DURATION,
    CapitalizerM5Bar,
    iter_atlas_m5,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_alignment_forensics import (
    CapitalizerCiboEventKind,
    load_causal_journey_events,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_departure_hypothesis import (
    HYPOTHESIS_ID,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_microstructure_discovery import (
    CapitalizerMicrostructureEvent,
    classify_microstructure_events,
    designated_session,
)
from qore.infrastructure.trader_lab.capitalizer_session_clock import capitalizer_session_at
from qore.infrastructure.trader_lab.capitalizer_target_context import (
    CapitalizerTargetContext,
    load_target_contexts,
)

IDENTITY = "QORE_CAPITALIZER_TARGET_CAPACITY_FORENSICS_V1"

_DIRECTIONAL_EVENTS: dict[CapitalizerMicrostructureEvent, CapitalizerSide] = {
    CapitalizerMicrostructureEvent.HIGH_RAID_REJECTION: CapitalizerSide.SHORT,
    CapitalizerMicrostructureEvent.LOW_RAID_REJECTION: CapitalizerSide.LONG,
    CapitalizerMicrostructureEvent.HIGH_ACCEPTANCE: CapitalizerSide.LONG,
    CapitalizerMicrostructureEvent.LOW_ACCEPTANCE: CapitalizerSide.SHORT,
}


@dataclass(frozen=True, slots=True)
class CapitalizerTargetCapacityObservation:
    symbol: str
    event: CapitalizerMicrostructureEvent
    side: CapitalizerSide
    decision_at: str
    active_candidate_count: int
    nearest_target_distance_ticks: Decimal
    diagnostic_risk_ticks: Decimal
    prospective_capacity_r: Decimal

    def __post_init__(self) -> None:
        if self.active_candidate_count <= 0:
            raise ValueError("target-capacity observation requires active candidates")
        if self.nearest_target_distance_ticks <= 0:
            raise ValueError("nearest target distance must be positive")
        if self.diagnostic_risk_ticks <= 0:
            raise ValueError("diagnostic risk must be positive")
        if self.prospective_capacity_r <= 0:
            raise ValueError("prospective capacity must be positive")


@dataclass(frozen=True, slots=True)
class CapitalizerTargetCapacityAggregate:
    event: str
    observations: int
    median_active_candidate_count: str
    median_capacity_r: str
    p25_capacity_r: str
    p75_capacity_r: str


@dataclass(frozen=True, slots=True)
class CapitalizerTargetCapacityReport:
    identity: str
    hypothesis_id: str
    symbol: str
    session: str
    aligned_departure_events: int
    target_context_events: int
    geometry_observations: int
    target_context_coverage: str
    geometry_coverage: str
    total: CapitalizerTargetCapacityAggregate
    by_event: tuple[CapitalizerTargetCapacityAggregate, ...]
    evidence_status: str = "CONSUMED_RESEARCH_EVIDENCE"
    geometry_kind: str = "DECISION_TIME_PROSPECTIVE_CAPACITY"
    entry_fill_used: bool = False
    diagnostic_stop_proxy: str = "SOURCE_M5_DIRECTIONAL_EXTREME"
    final_stop_contract_defined: bool = False
    minimum_r_filter_defined: bool = False
    target_outcomes_used: bool = False
    economic_candidate: bool = False
    rule_promotion_allowed: bool = False


def _target_index(
    contexts: tuple[CapitalizerTargetContext, ...],
) -> dict[tuple[str, CapitalizerSide, str], CapitalizerTargetContext]:
    result: dict[tuple[str, CapitalizerSide, str], CapitalizerTargetContext] = {}
    for context in contexts:
        key = (context.symbol, context.side, context.departure_at.isoformat())
        if key in result:
            raise ValueError("target context keys must be unique")
        result[key] = context
    return result


def _capacity(
    *,
    bar: CapitalizerM5Bar,
    event: CapitalizerMicrostructureEvent,
    side: CapitalizerSide,
    context: CapitalizerTargetContext,
) -> CapitalizerTargetCapacityObservation | None:
    tick = Decimal(1).scaleb(-bar.digits)
    if side is CapitalizerSide.LONG:
        risk = bar.close - bar.low
        ahead = tuple(
            candidate
            for candidate in context.candidates
            if candidate.price > bar.close
        )
        rewards = tuple(candidate.price - bar.close for candidate in ahead)
    else:
        risk = bar.high - bar.close
        ahead = tuple(
            candidate
            for candidate in context.candidates
            if candidate.price < bar.close
        )
        rewards = tuple(bar.close - candidate.price for candidate in ahead)
    if risk <= 0 or not rewards:
        return None

    reward = min(rewards)
    return CapitalizerTargetCapacityObservation(
        symbol=bar.symbol,
        event=event,
        side=side,
        decision_at=bar.closed_at.isoformat(),
        active_candidate_count=len(context.candidates),
        nearest_target_distance_ticks=reward / tick,
        diagnostic_risk_ticks=risk / tick,
        prospective_capacity_r=reward / risk,
    )


def build_target_capacity_observations(
    *,
    m5_root: Path,
    journey_root: Path,
    target_root: Path,
) -> tuple[
    tuple[CapitalizerTargetCapacityObservation, ...],
    int,
    int,
]:
    bars = tuple(iter_atlas_m5(m5_root))
    if not bars:
        raise ValueError("M5 artifact contained no bars")
    symbol = bars[0].symbol
    session = designated_session(symbol)

    departures = {
        (item.observed_at, item.side)
        for item in load_causal_journey_events(journey_root)
        if item.kind is CapitalizerCiboEventKind.DEPARTURE
        and item.timeframe == "H1"
    }
    contexts = _target_index(load_target_contexts(target_root))

    result: list[CapitalizerTargetCapacityObservation] = []
    aligned_events = 0
    context_events = 0
    for index in range(1, len(bars)):
        current = bars[index]
        previous = bars[index - 1]
        if current.opened_at - previous.opened_at != BAR_DURATION:
            continue
        if capitalizer_session_at(current.opened_at) is not session:
            continue

        directional = tuple(
            (event, _DIRECTIONAL_EVENTS[event])
            for event in classify_microstructure_events(current, previous)
            if event in _DIRECTIONAL_EVENTS
        )
        if not directional or len({side for _, side in directional}) != 1:
            continue

        for event, side in directional:
            if (current.closed_at, side) not in departures:
                continue
            aligned_events += 1
            context = contexts.get((symbol, side, current.closed_at.isoformat()))
            if context is None:
                continue
            context_events += 1
            observation = _capacity(
                bar=current,
                event=event,
                side=side,
                context=context,
            )
            if observation is not None:
                result.append(observation)

    return tuple(result), aligned_events, context_events


def _aggregate(
    observations: tuple[CapitalizerTargetCapacityObservation, ...],
    *,
    event: str,
) -> CapitalizerTargetCapacityAggregate:
    if not observations:
        raise ValueError("target-capacity aggregate requires observations")
    capacities = [item.prospective_capacity_r for item in observations]
    quartiles = quantiles(capacities, n=4)
    return CapitalizerTargetCapacityAggregate(
        event=event,
        observations=len(observations),
        median_active_candidate_count=str(
            median(item.active_candidate_count for item in observations)
        ),
        median_capacity_r=str(median(capacities)),
        p25_capacity_r=str(quartiles[0]),
        p75_capacity_r=str(quartiles[2]),
    )


def summarize_target_capacity(
    observations: tuple[CapitalizerTargetCapacityObservation, ...],
    *,
    aligned_events: int,
    context_events: int,
) -> CapitalizerTargetCapacityReport:
    if not observations:
        raise ValueError("target-capacity report requires observations")
    symbol = observations[0].symbol
    if any(item.symbol != symbol for item in observations):
        raise ValueError("target-capacity report requires one symbol")
    if aligned_events <= 0 or context_events < 0 or context_events > aligned_events:
        raise ValueError("invalid target-capacity coverage counts")

    by_event = tuple(
        _aggregate(
            tuple(item for item in observations if item.event.value == event),
            event=event,
        )
        for event in sorted({item.event.value for item in observations})
    )
    return CapitalizerTargetCapacityReport(
        identity=IDENTITY,
        hypothesis_id=HYPOTHESIS_ID,
        symbol=symbol,
        session=designated_session(symbol).value,
        aligned_departure_events=aligned_events,
        target_context_events=context_events,
        geometry_observations=len(observations),
        target_context_coverage=str(Decimal(context_events) / Decimal(aligned_events)),
        geometry_coverage=str(Decimal(len(observations)) / Decimal(aligned_events)),
        total=_aggregate(observations, event="ALL"),
        by_event=by_event,
    )


def write_target_capacity_report(
    report: CapitalizerTargetCapacityReport,
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / f"capitalizer-{report.symbol.lower()}-target-capacity-v1.json"
    payload: dict[str, Any] = asdict(report)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Capitalizer causal target-capacity forensics")
    parser.add_argument("m5_root", type=Path)
    parser.add_argument("journey_root", type=Path)
    parser.add_argument("target_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    observations, aligned, context = build_target_capacity_observations(
        m5_root=args.m5_root,
        journey_root=args.journey_root,
        target_root=args.target_root,
    )
    report = summarize_target_capacity(
        observations,
        aligned_events=aligned,
        context_events=context,
    )
    write_target_capacity_report(report, args.output)
    print(
        json.dumps(
            {
                "identity": report.identity,
                "symbol": report.symbol,
                "aligned": report.aligned_departure_events,
                "geometry": report.geometry_observations,
                "median_capacity_r": report.total.median_capacity_r,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
