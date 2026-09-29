"""V47-S1R-E event-specific source opposite-boundary census.

The original consumed Target Destination V2 retained SOURCE_OPPOSITE_BOUNDARY:
the opposite extreme of the exact causal reference object that was raided.
S0/S1 currently retains the raided boundary but not this paired boundary.

This module reconstructs that identity pre-economically. It does not change
target selection, admission, fills, exits, economics or certification.

Frozen in PR #623 comment 5896750454.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from pathlib import Path

from qore.infrastructure.trader_lab import (
    capitalizer_canonical_source_context_binders_v47_s0 as binders,
)
from qore.infrastructure.trader_lab import (
    capitalizer_canonical_structural_targets_v47_s0 as targets,
)
from qore.infrastructure.trader_lab import (
    capitalizer_source_strategy_isolation_v47_s1 as s1,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
    iter_cibo_m1,
)
from qore.infrastructure.trader_lab.capitalizer_contract import CapitalizerSession
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_full_ict_density_scanner_1y_v1 import (
    AggregatedBar,
)
from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerSourceDirection,
)

IDENTITY = "QORE_CAPITALIZER_EVENT_SPECIFIC_OPPOSITE_BOUNDARY_CENSUS_V47_S1R_E"
PREDECLARATION_COMMENT_ID = 5896750454


class OppositeBoundaryClass(StrEnum):
    EVENT_OPPOSITE_BOUNDARY_VALID = "EVENT_OPPOSITE_BOUNDARY_VALID"
    EVENT_OPPOSITE_BOUNDARY_ALREADY_CONSUMED = (
        "EVENT_OPPOSITE_BOUNDARY_ALREADY_CONSUMED"
    )
    EVENT_OPPOSITE_BOUNDARY_WRONG_SIDE = "EVENT_OPPOSITE_BOUNDARY_WRONG_SIDE"
    EVENT_REFERENCE_PAIR_UNRESOLVED = "EVENT_REFERENCE_PAIR_UNRESOLVED"


class CurrentTargetSetRelation(StrEnum):
    PRESENT_UNIQUE_CURRENT_SET = "PRESENT_UNIQUE_CURRENT_SET"
    PRESENT_INSIDE_MULTI_TARGET_AMBIGUITY = "PRESENT_INSIDE_MULTI_TARGET_AMBIGUITY"
    ABSENT_FROM_CURRENT_TARGET_SET = "ABSENT_FROM_CURRENT_TARGET_SET"
    NOT_APPLICABLE_INVALID_EVENT_BOUNDARY = "NOT_APPLICABLE_INVALID_EVENT_BOUNDARY"


@dataclass(frozen=True, slots=True)
class PairedBoundary:
    price: Decimal
    known_at: datetime
    provenance: str

    def __post_init__(self) -> None:
        if not self.price.is_finite() or self.price <= 0:
            raise ValueError("paired boundary price must be positive finite")
        s1._aware(self.known_at)


@dataclass(frozen=True, slots=True)
class EventBoundaryAudit:
    classification: OppositeBoundaryClass
    relation_to_current_target_set: CurrentTargetSetRelation
    paired_boundary: PairedBoundary | None
    current_target_candidate_count: int
    current_target_distinct_price_count: int
    current_target_resolved: bool

    def __post_init__(self) -> None:
        valid = (
            self.classification
            is OppositeBoundaryClass.EVENT_OPPOSITE_BOUNDARY_VALID
        )
        if valid != (self.paired_boundary is not None):
            raise ValueError("valid event boundary payload mismatch")
        if self.current_target_candidate_count < 0:
            raise ValueError("candidate count cannot be negative")
        if self.current_target_distinct_price_count < 0:
            raise ValueError("target price count cannot be negative")


@dataclass(frozen=True, slots=True)
class EventBoundaryPeriodMarketReport:
    identity: str
    period: str
    symbol: str
    session: str
    source_events: int
    aligned_h1_strict_m15_events: int
    classification_counts: dict[str, int]
    current_target_relation_counts: dict[str, int]
    valid_event_opposite_boundaries: int
    valid_hidden_inside_multi_target_ambiguity: int
    target_policy_changed: bool = False
    nearest_target_priority_used: bool = False
    rr_priority_used: bool = False
    outcome_priority_used: bool = False
    terminal_outcome_read: bool = False
    economics_calculated: bool = False
    fresh_holdout_opened: bool = False
    admission_changed: bool = False
    trader_certified: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY:
            raise ValueError("event opposite-boundary identity drift")
        if self.period not in s1.PERIODS:
            raise ValueError("event opposite-boundary period drift")
        if sum(self.classification_counts.values()) != self.aligned_h1_strict_m15_events:
            raise ValueError("event opposite-boundary classification coverage drift")
        if sum(self.current_target_relation_counts.values()) != (
            self.aligned_h1_strict_m15_events
        ):
            raise ValueError("event opposite-boundary target relation coverage drift")
        if self.valid_event_opposite_boundaries != self.classification_counts.get(
            OppositeBoundaryClass.EVENT_OPPOSITE_BOUNDARY_VALID.value,
            0,
        ):
            raise ValueError("valid opposite-boundary count drift")
        if (
            self.target_policy_changed
            or self.nearest_target_priority_used
            or self.rr_priority_used
            or self.outcome_priority_used
            or self.terminal_outcome_read
            or self.economics_calculated
            or self.fresh_holdout_opened
            or self.admission_changed
            or self.trader_certified
        ):
            raise ValueError("event opposite-boundary governance drift")


def _direction(side: CapitalizerSide) -> CapitalizerSourceDirection:
    return (
        CapitalizerSourceDirection.BULLISH
        if side is CapitalizerSide.LONG
        else CapitalizerSourceDirection.BEARISH
    )


def _ahead(
    price: Decimal,
    entry_price: Decimal,
    side: CapitalizerSide,
) -> bool:
    return price > entry_price if side is CapitalizerSide.LONG else price < entry_price


def _target_touched(
    bar: CapitalizerM1Bar,
    *,
    price: Decimal,
    side: CapitalizerSide,
) -> bool:
    return bar.high >= price if side is CapitalizerSide.LONG else bar.low <= price


def _h1_between(
    prepared: s1._PreparedSourceSeries,
    *,
    start: datetime,
    end: datetime,
) -> tuple[AggregatedBar, ...]:
    raw = s1._prepared_tf_between(
        prepared.h1,
        prepared.h1_opened,
        start=start,
        end=end,
    )
    return tuple(row for row in raw if isinstance(row, AggregatedBar))


def _latest_matching_h1_swing_pivot(
    prepared: s1._PreparedSourceSeries,
    *,
    kind: str,
    price: Decimal,
    before: datetime,
) -> tuple[AggregatedBar, datetime] | None:
    """Recover the exact V3 five-bar-confirmed swing pivot and its known_at."""

    frames = _h1_between(
        prepared,
        start=s1._aware(before) - s1.LOOKBACK,
        end=s1._aware(before) + timedelta(hours=1),
    )
    matches: list[tuple[AggregatedBar, datetime]] = []
    for index in range(2, len(frames) - 2):
        pivot = frames[index]
        left = frames[index - 2 : index]
        right = frames[index + 1 : index + 3]
        confirmed_at = frames[index + 2].closed_at
        if confirmed_at > s1._aware(before):
            continue
        if kind == "HIGH":
            structural = all(
                pivot.source.high > item.source.high for item in left + right
            )
            level = pivot.source.high
        elif kind == "LOW":
            structural = all(
                pivot.source.low < item.source.low for item in left + right
            )
            level = pivot.source.low
        else:
            raise ValueError("unsupported H1 swing kind")
        if structural and level == price:
            matches.append((pivot, confirmed_at))
    if not matches:
        return None
    return matches[-1]


def reconstruct_event_opposite_boundary(
    bars: tuple[CapitalizerM1Bar, ...],
    *,
    prepared: s1._PreparedSourceSeries,
    event: s1.s0.S0ICTSourceEvent,
) -> PairedBoundary | None:
    """Recover only the paired boundary of the exact raided reference."""

    source = event.closeback.reference.source
    reference_price = event.closeback.reference.price

    if source.startswith("SESSION_"):
        prior = s1._reference_liquidity(
            bars,
            operating_day=event.operating_date,
            session=event.session,
            prepared=prepared,
        )
        if prior is None:
            return None
        if source.startswith("SESSION_HIGH:"):
            if prior.high != reference_price:
                return None
            return PairedBoundary(
                price=prior.low,
                known_at=prior.closed_at,
                provenance="SAME_COMPLETED_PRIOR_SESSION_RANGE_LOW",
            )
        if source.startswith("SESSION_LOW:"):
            if prior.low != reference_price:
                return None
            return PairedBoundary(
                price=prior.high,
                known_at=prior.closed_at,
                provenance="SAME_COMPLETED_PRIOR_SESSION_RANGE_HIGH",
            )
        return None

    if source in {"PDH", "PDL"}:
        previous = s1._prepared_previous_day_range(
            prepared,
            operating_day=event.operating_date,
        )
        if previous is None:
            return None
        high, low = previous
        known_at = min(
            (
                row.closed_at
                for row in prepared.m1
                if row.opened_at.astimezone(s1.NEW_YORK).date()
                < event.operating_date
                and row.high <= high
                and row.low >= low
            ),
            default=event.closeback.h1_open - timedelta(days=1),
        )
        if source == "PDH" and high == reference_price:
            return PairedBoundary(
                price=low,
                known_at=known_at,
                provenance="SAME_PREVIOUS_DAY_RANGE_LOW",
            )
        if source == "PDL" and low == reference_price:
            return PairedBoundary(
                price=high,
                known_at=known_at,
                provenance="SAME_PREVIOUS_DAY_RANGE_HIGH",
            )
        return None

    if source == "MAJOR_H1_SWING_HIGH":
        match = _latest_matching_h1_swing_pivot(
            prepared,
            kind="HIGH",
            price=reference_price,
            before=event.closeback.h1_open,
        )
        if match is None:
            return None
        pivot, known_at = match
        return PairedBoundary(
            price=pivot.source.low,
            known_at=known_at,
            provenance="SAME_FIVE_BAR_CONFIRMED_H1_SWING_PIVOT_LOW",
        )

    if source == "MAJOR_H1_SWING_LOW":
        match = _latest_matching_h1_swing_pivot(
            prepared,
            kind="LOW",
            price=reference_price,
            before=event.closeback.h1_open,
        )
        if match is None:
            return None
        pivot, known_at = match
        return PairedBoundary(
            price=pivot.source.high,
            known_at=known_at,
            provenance="SAME_FIVE_BAR_CONFIRMED_H1_SWING_PIVOT_HIGH",
        )

    return None


def audit_event_boundary(
    bars: tuple[CapitalizerM1Bar, ...],
    *,
    prepared: s1._PreparedSourceSeries,
    event: s1.s0.S0ICTSourceEvent,
) -> EventBoundaryAudit:
    paired = reconstruct_event_opposite_boundary(
        bars,
        prepared=prepared,
        event=event,
    )
    direction = _direction(event.side)
    current = targets.bind_structural_target(
        bars,
        direction=direction,
        entry_price=event.primary_armed_level,
        decision_at=event.source_event_at,
    )
    prices = {candidate.target_price for candidate in current.candidates}

    if paired is None:
        return EventBoundaryAudit(
            classification=OppositeBoundaryClass.EVENT_REFERENCE_PAIR_UNRESOLVED,
            relation_to_current_target_set=(
                CurrentTargetSetRelation.NOT_APPLICABLE_INVALID_EVENT_BOUNDARY
            ),
            paired_boundary=None,
            current_target_candidate_count=len(current.candidates),
            current_target_distinct_price_count=len(prices),
            current_target_resolved=current.resolution.resolved,
        )

    if not _ahead(paired.price, event.primary_armed_level, event.side):
        return EventBoundaryAudit(
            classification=OppositeBoundaryClass.EVENT_OPPOSITE_BOUNDARY_WRONG_SIDE,
            relation_to_current_target_set=(
                CurrentTargetSetRelation.NOT_APPLICABLE_INVALID_EVENT_BOUNDARY
            ),
            paired_boundary=None,
            current_target_candidate_count=len(current.candidates),
            current_target_distinct_price_count=len(prices),
            current_target_resolved=current.resolution.resolved,
        )

    consumed = any(
        _target_touched(row, price=paired.price, side=event.side)
        for row in bars
        if event.closeback.sweep_at <= row.opened_at < event.source_event_at
    )
    if consumed:
        return EventBoundaryAudit(
            classification=(
                OppositeBoundaryClass.EVENT_OPPOSITE_BOUNDARY_ALREADY_CONSUMED
            ),
            relation_to_current_target_set=(
                CurrentTargetSetRelation.NOT_APPLICABLE_INVALID_EVENT_BOUNDARY
            ),
            paired_boundary=None,
            current_target_candidate_count=len(current.candidates),
            current_target_distinct_price_count=len(prices),
            current_target_resolved=current.resolution.resolved,
        )

    if paired.price not in prices:
        relation = CurrentTargetSetRelation.ABSENT_FROM_CURRENT_TARGET_SET
    elif len(prices) == 1:
        relation = CurrentTargetSetRelation.PRESENT_UNIQUE_CURRENT_SET
    else:
        relation = (
            CurrentTargetSetRelation.PRESENT_INSIDE_MULTI_TARGET_AMBIGUITY
        )

    return EventBoundaryAudit(
        classification=OppositeBoundaryClass.EVENT_OPPOSITE_BOUNDARY_VALID,
        relation_to_current_target_set=relation,
        paired_boundary=paired,
        current_target_candidate_count=len(current.candidates),
        current_target_distinct_price_count=len(prices),
        current_target_resolved=current.resolution.resolved,
    )


def audit_period_market(
    bars: tuple[CapitalizerM1Bar, ...],
    *,
    symbol: str,
    session: CapitalizerSession,
    period: str,
) -> EventBoundaryPeriodMarketReport:
    start, end = s1.PERIODS[period]
    prepared = s1._prepare_source_series(bars)
    days = s1._operating_days(
        bars,
        session=session,
        period_start=start,
        period_end=end,
    )
    opened = prepared.opened
    classes: Counter[str] = Counter()
    relations: Counter[str] = Counter()
    source_events = 0
    eligible = 0

    for day in days:
        local = s1._day_slice(
            bars,
            opened,
            operating_day=day,
            session=session,
        )
        if not local:
            continue
        events = s1.bind_source_window_ict_events(
            local,
            session=session,
            operating_day=day,
            prepared=prepared,
        )
        source_events += len(events)
        for event in events:
            direction = _direction(event.side)
            htf = binders.bind_latest_h1_context(
                local,
                decision_at=event.source_event_at,
            )
            if htf is None:
                continue
            if (
                htf.closure.direction is not direction
                or htf.daily_bias.direction is not direction
            ):
                continue
            m15 = binders.bind_first_m15_cisd(
                local,
                direction=direction,
                higher_timeframe_closure=htf.closure,
                important_pois=htf.poi_context.interacting_pois,
                after=htf.confirmed_at,
                before=event.source_event_at,
            )
            if m15 is None:
                continue

            eligible += 1
            audited = audit_event_boundary(
                local,
                prepared=prepared,
                event=event,
            )
            classes[audited.classification.value] += 1
            relations[audited.relation_to_current_target_set.value] += 1

    valid = classes[OppositeBoundaryClass.EVENT_OPPOSITE_BOUNDARY_VALID.value]
    hidden = relations[
        CurrentTargetSetRelation.PRESENT_INSIDE_MULTI_TARGET_AMBIGUITY.value
    ]
    return EventBoundaryPeriodMarketReport(
        identity=IDENTITY,
        period=period,
        symbol=symbol,
        session=session.value,
        source_events=source_events,
        aligned_h1_strict_m15_events=eligible,
        classification_counts=dict(sorted(classes.items())),
        current_target_relation_counts=dict(sorted(relations.items())),
        valid_event_opposite_boundaries=valid,
        valid_hidden_inside_multi_target_ambiguity=hidden,
    )


def _load_consumed(root: Path, symbol: str) -> tuple[CapitalizerM1Bar, ...]:
    rows = tuple(
        row
        for row in iter_cibo_m1(root)
        if s1.CONSUMED_LOAD_START <= row.opened_at < s1.CONSUMED_LOAD_END
    )
    if not rows:
        raise ValueError("event opposite-boundary provider-native M1 is empty")
    if any(row.symbol != symbol for row in rows):
        raise ValueError("event opposite-boundary symbol mismatch")
    return rows


def write_report(
    report: EventBoundaryPeriodMarketReport,
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / (
        f"capitalizer-v47-s1r-e-opposite-{report.period}-{report.symbol.lower()}.json"
    )
    path.write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _json_int(row: dict[str, object], key: str) -> int:
    value = row.get(key)
    if type(value) is not int:
        raise ValueError(f"event opposite-boundary field {key} must be int")
    return value


def aggregate(root: Path, output: Path) -> dict[str, object]:
    reports: list[dict[str, object]] = []
    for path in sorted(root.rglob("capitalizer-v47-s1r-e-opposite-*.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("event opposite-boundary report must be object")
        reports.append(raw)
    if len(reports) != 27:
        raise ValueError(
            f"event opposite-boundary census requires 27 reports, got {len(reports)}"
        )

    classes: Counter[str] = Counter()
    relations: Counter[str] = Counter()
    for row in reports:
        raw_classes = row.get("classification_counts")
        raw_relations = row.get("current_target_relation_counts")
        if not isinstance(raw_classes, dict) or not isinstance(raw_relations, dict):
            raise ValueError("event opposite-boundary dictionaries missing")
        for key, value in raw_classes.items():
            if type(value) is not int:
                raise ValueError("event opposite-boundary class count must be int")
            classes[str(key)] += value
        for key, value in raw_relations.items():
            if type(value) is not int:
                raise ValueError("event opposite-boundary relation count must be int")
            relations[str(key)] += value

    eligible = sum(
        _json_int(row, "aligned_h1_strict_m15_events") for row in reports
    )
    valid = sum(
        _json_int(row, "valid_event_opposite_boundaries") for row in reports
    )
    hidden = sum(
        _json_int(row, "valid_hidden_inside_multi_target_ambiguity")
        for row in reports
    )
    if sum(classes.values()) != eligible or sum(relations.values()) != eligible:
        raise ValueError("event opposite-boundary aggregate coverage drift")

    decision = (
        "EVENT_SPECIFIC_SOURCE_TARGET_IDENTITY_RECOVERY_SUPPORTED"
        if valid > 0
        else "EVENT_SPECIFIC_SOURCE_TARGET_IDENTITY_NOT_RECOVERED"
    )
    payload: dict[str, object] = {
        "identity": IDENTITY,
        "predeclaration_comment_id": PREDECLARATION_COMMENT_ID,
        "market_period_reports": len(reports),
        "market_count": len({str(row["symbol"]) for row in reports}),
        "source_events": sum(
            _json_int(row, "source_events") for row in reports
        ),
        "aligned_h1_strict_m15_events": eligible,
        "classification_counts": dict(sorted(classes.items())),
        "current_target_relation_counts": dict(sorted(relations.items())),
        "valid_event_opposite_boundaries": valid,
        "valid_hidden_inside_multi_target_ambiguity": hidden,
        "target_policy_changed": False,
        "nearest_target_priority_used": False,
        "rr_priority_used": False,
        "outcome_priority_used": False,
        "terminal_outcome_read": False,
        "economics_calculated": False,
        "fresh_holdout_opened": False,
        "admission_changed": False,
        "trader_certified": False,
        "decision": decision,
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "capitalizer-v47-s1r-e-opposite-aggregate.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    market = sub.add_parser("market")
    market.add_argument("m1_root", type=Path)
    market.add_argument("--symbol", required=True)
    market.add_argument("--session", required=True)
    market.add_argument("--output", type=Path, required=True)
    matrix = sub.add_parser("aggregate")
    matrix.add_argument("input", type=Path)
    matrix.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if args.command == "market":
        bars = _load_consumed(args.m1_root, args.symbol)
        for period in s1.PERIODS:
            report = audit_period_market(
                bars,
                symbol=args.symbol,
                session=CapitalizerSession(args.session),
                period=period,
            )
            write_report(report, args.output)
            print(json.dumps(asdict(report), sort_keys=True))
        return

    payload = aggregate(args.input, args.output)
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
