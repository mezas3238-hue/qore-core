"""V47-S1R-D pre-economic structural-target ambiguity census.

Explains why S1 source events that pass aligned H1 + strict pre-event M15
cannot resolve the frozen S0 structural destination family.

Frozen in PR #623 comment 5896534113.
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
from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerSourceDirection,
)

IDENTITY = "QORE_CAPITALIZER_STRUCTURAL_TARGET_AMBIGUITY_CENSUS_V47_S1R_D"
PREDECLARATION_COMMENT_ID = 5896534113


class TargetAmbiguityClass(StrEnum):
    ZERO_ELIGIBLE_TARGETS = "ZERO_ELIGIBLE_TARGETS"
    ONE_UNIQUE_PRICE_AND_KIND = "ONE_UNIQUE_PRICE_AND_KIND"
    MULTIPLE_DISTINCT_PRICES_SAME_KIND = "MULTIPLE_DISTINCT_PRICES_SAME_KIND"
    SAME_PRICE_MULTIPLE_KINDS = "SAME_PRICE_MULTIPLE_KINDS"
    MULTIPLE_DISTINCT_PRICES_AND_KINDS = "MULTIPLE_DISTINCT_PRICES_AND_KINDS"


@dataclass(frozen=True, slots=True)
class TargetAudit:
    classification: TargetAmbiguityClass
    raw_candidate_count: int
    unique_price_kind_count: int
    provenance: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class TargetPeriodMarketReport:
    identity: str
    period: str
    symbol: str
    session: str
    source_events: int
    aligned_h1_strict_m15_events: int
    ambiguity_counts: dict[str, int]
    provenance_counts: dict[str, int]
    resolved_under_current_s0: int
    unresolved_under_current_s0: int
    target_policy_changed: bool = False
    nearest_target_priority_used: bool = False
    rr_priority_used: bool = False
    outcome_priority_used: bool = False
    terminal_outcome_read: bool = False
    economics_calculated: bool = False
    fresh_holdout_opened: bool = False
    trader_certified: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY:
            raise ValueError("target ambiguity identity drift")
        if self.period not in s1.PERIODS:
            raise ValueError("target ambiguity period drift")
        if sum(self.ambiguity_counts.values()) != self.aligned_h1_strict_m15_events:
            raise ValueError("target ambiguity classification coverage drift")
        if self.resolved_under_current_s0 + self.unresolved_under_current_s0 != (
            self.aligned_h1_strict_m15_events
        ):
            raise ValueError("target resolution count drift")
        if (
            self.target_policy_changed
            or self.nearest_target_priority_used
            or self.rr_priority_used
            or self.outcome_priority_used
            or self.terminal_outcome_read
            or self.economics_calculated
            or self.fresh_holdout_opened
            or self.trader_certified
        ):
            raise ValueError("target ambiguity governance drift")


def _direction(side: CapitalizerSide) -> CapitalizerSourceDirection:
    return (
        CapitalizerSourceDirection.BULLISH
        if side is CapitalizerSide.LONG
        else CapitalizerSourceDirection.BEARISH
    )


def _candidate_provenance(
    bars: tuple[CapitalizerM1Bar, ...],
    *,
    direction: CapitalizerSourceDirection,
    entry_price: Decimal,
    decision_at: datetime,
) -> tuple[str, ...]:
    frames = targets.build_exact_source_frames(bars)
    labels: list[str] = []
    for timeframe in ("H1", "H4", "D1"):
        previous = targets._previous_completed_candidate(
            frames[timeframe],
            timeframe=timeframe,
            decision_at=decision_at,
            entry_price=entry_price,
            direction=direction,
        )
        if previous is not None and targets._untouched_since(
            bars,
            level=previous.target_price,
            known_at=previous.observed_at,
            decision_at=decision_at,
            direction=direction,
        ):
            labels.append(f"PREVIOUS_{timeframe}")

        swing = targets._latest_active_swing_candidate(
            frames[timeframe],
            bars,
            timeframe=timeframe,
            decision_at=decision_at,
            entry_price=entry_price,
            direction=direction,
        )
        if swing is not None:
            labels.append(f"ACTIVE_SWING_{timeframe}")
    return tuple(labels)


def audit_target(
    bars: tuple[CapitalizerM1Bar, ...],
    *,
    direction: CapitalizerSourceDirection,
    entry_price: Decimal,
    decision_at: datetime,
) -> TargetAudit:
    binding = targets.bind_structural_target(
        bars,
        direction=direction,
        entry_price=entry_price,
        decision_at=decision_at,
    )
    unique = {
        (candidate.kind.value, candidate.target_price)
        for candidate in binding.candidates
    }
    prices = {price for _kind, price in unique}
    kinds = {kind for kind, _price in unique}

    if not unique:
        classification = TargetAmbiguityClass.ZERO_ELIGIBLE_TARGETS
    elif len(unique) == 1:
        classification = TargetAmbiguityClass.ONE_UNIQUE_PRICE_AND_KIND
    elif len(prices) == 1 and len(kinds) > 1:
        classification = TargetAmbiguityClass.SAME_PRICE_MULTIPLE_KINDS
    elif len(prices) > 1 and len(kinds) == 1:
        classification = TargetAmbiguityClass.MULTIPLE_DISTINCT_PRICES_SAME_KIND
    else:
        classification = TargetAmbiguityClass.MULTIPLE_DISTINCT_PRICES_AND_KINDS

    expected_resolved = classification is TargetAmbiguityClass.ONE_UNIQUE_PRICE_AND_KIND
    if binding.resolution.resolved != expected_resolved:
        raise ValueError("target ambiguity census drifted from frozen resolver")

    return TargetAudit(
        classification=classification,
        raw_candidate_count=len(binding.candidates),
        unique_price_kind_count=len(unique),
        provenance=_candidate_provenance(
            bars,
            direction=direction,
            entry_price=entry_price,
            decision_at=decision_at,
        ),
    )


def audit_period_market(
    bars: tuple[CapitalizerM1Bar, ...],
    *,
    symbol: str,
    session: CapitalizerSession,
    period: str,
) -> TargetPeriodMarketReport:
    start, end = s1.PERIODS[period]
    prepared = s1._prepare_source_series(bars)
    days = s1._operating_days(
        bars,
        session=session,
        period_start=start,
        period_end=end,
    )
    opened = prepared.opened
    ambiguity: Counter[str] = Counter()
    provenance: Counter[str] = Counter()
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
            audited = audit_target(
                local,
                direction=direction,
                entry_price=event.primary_armed_level,
                decision_at=event.source_event_at,
            )
            ambiguity[audited.classification.value] += 1
            provenance.update(audited.provenance)

    resolved = ambiguity[TargetAmbiguityClass.ONE_UNIQUE_PRICE_AND_KIND.value]
    return TargetPeriodMarketReport(
        identity=IDENTITY,
        period=period,
        symbol=symbol,
        session=session.value,
        source_events=source_events,
        aligned_h1_strict_m15_events=eligible,
        ambiguity_counts=dict(sorted(ambiguity.items())),
        provenance_counts=dict(sorted(provenance.items())),
        resolved_under_current_s0=resolved,
        unresolved_under_current_s0=eligible - resolved,
    )


def _load_consumed(root: Path, symbol: str) -> tuple[CapitalizerM1Bar, ...]:
    rows = tuple(
        row
        for row in iter_cibo_m1(root)
        if s1.CONSUMED_LOAD_START <= row.opened_at < s1.CONSUMED_LOAD_END
    )
    if not rows:
        raise ValueError("target ambiguity provider-native M1 is empty")
    if any(row.symbol != symbol for row in rows):
        raise ValueError("target ambiguity symbol mismatch")
    return rows


def write_report(report: TargetPeriodMarketReport, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / (
        f"capitalizer-v47-s1r-d-target-{report.period}-{report.symbol.lower()}.json"
    )
    path.write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _json_int(row: dict[str, object], key: str) -> int:
    value = row.get(key)
    if type(value) is not int:
        raise ValueError(f"target ambiguity aggregate field {key} must be int")
    return value


def aggregate(root: Path, output: Path) -> dict[str, object]:
    reports: list[dict[str, object]] = []
    for path in sorted(root.rglob("capitalizer-v47-s1r-d-target-*.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("target ambiguity report must be object")
        reports.append(raw)
    if len(reports) != 27:
        raise ValueError(f"target ambiguity census requires 27 reports, got {len(reports)}")

    ambiguity: Counter[str] = Counter()
    provenance: Counter[str] = Counter()
    for row in reports:
        raw_ambiguity = row.get("ambiguity_counts")
        raw_provenance = row.get("provenance_counts")
        if not isinstance(raw_ambiguity, dict) or not isinstance(raw_provenance, dict):
            raise ValueError("target ambiguity aggregate dictionaries missing")
        for key, value in raw_ambiguity.items():
            if type(value) is not int:
                raise ValueError("target ambiguity count must be int")
            ambiguity[str(key)] += value
        for key, value in raw_provenance.items():
            if type(value) is not int:
                raise ValueError("target provenance count must be int")
            provenance[str(key)] += value

    eligible = sum(
        _json_int(row, "aligned_h1_strict_m15_events")
        for row in reports
    )
    resolved = sum(
        _json_int(row, "resolved_under_current_s0")
        for row in reports
    )
    unresolved = sum(
        _json_int(row, "unresolved_under_current_s0")
        for row in reports
    )
    if sum(ambiguity.values()) != eligible or resolved + unresolved != eligible:
        raise ValueError("target ambiguity aggregate coverage drift")

    zero = ambiguity[TargetAmbiguityClass.ZERO_ELIGIBLE_TARGETS.value]
    multi = eligible - zero - resolved
    if multi > zero:
        diagnosis = "MULTI_TARGET_AMBIGUITY_DOMINATES_UNRESOLVED_POPULATION"
    elif zero > multi:
        diagnosis = "ZERO_TARGET_AVAILABILITY_DOMINATES_UNRESOLVED_POPULATION"
    else:
        diagnosis = "TARGET_AMBIGUITY_AND_AVAILABILITY_TIED"

    payload: dict[str, object] = {
        "identity": IDENTITY,
        "predeclaration_comment_id": PREDECLARATION_COMMENT_ID,
        "market_period_reports": len(reports),
        "market_count": len({str(row["symbol"]) for row in reports}),
        "source_events": sum(_json_int(row, "source_events") for row in reports),
        "aligned_h1_strict_m15_events": eligible,
        "ambiguity_counts": dict(sorted(ambiguity.items())),
        "provenance_counts": dict(sorted(provenance.items())),
        "resolved_under_current_s0": resolved,
        "unresolved_under_current_s0": unresolved,
        "target_policy_changed": False,
        "nearest_target_priority_used": False,
        "rr_priority_used": False,
        "outcome_priority_used": False,
        "terminal_outcome_read": False,
        "economics_calculated": False,
        "fresh_holdout_opened": False,
        "trader_certified": False,
        "diagnosis": diagnosis,
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "capitalizer-v47-s1r-d-target-aggregate.json").write_text(
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
