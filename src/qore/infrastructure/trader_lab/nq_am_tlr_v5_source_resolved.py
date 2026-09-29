"""Source-resolved one-year USTEC study for the ICT NQ AM reversal.

V5 separates source-explicit event logic from QORE-required mechanization and
from source-undefined economic robustness. Research only.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import nq_am_temporal_liquidity_reversal_v1 as v1
from qore.infrastructure.trader_lab import nq_am_tlr_v4_ustec_capability as v4
from qore.infrastructure.trader_lab.ict_turtle_soup_r4_source_exact import (
    Bar,
    BearishFvg,
    Evidence,
    _max_drawdown,
    _profit_factor,
)

IDENTITY = "QORE_NQ_AM_TLR_V5_SOURCE_RESOLVED_001"
EVAL_OPEN_NY = date(2016, 4, 20)
EVAL_CLOSE_NY = date(2017, 4, 20)
SOURCE_RUN_ID = 34981033027
SOURCE_ARTIFACT_ID = 10402199719
SOURCE_EVIDENCE_SHA256 = (
    "4031c7e21bb311fdb99d7b1028fd9ff154ace1dc4886249ff978b700fdeeedcb"
)
PRIMARY_FRICTION_R = Decimal("0.05")
STRESS_FRICTION_R = Decimal("0.10")


@dataclass(frozen=True, slots=True)
class OpeningTelemetry:
    pair_0930_0931: bool | None
    pair_0931_0932: bool | None


@dataclass(frozen=True, slots=True)
class TargetOutcome:
    target_name: str
    target_price: Decimal
    eligible: bool
    reached_before_new_sweep_low: bool | None
    time_to_target_minutes: int | None


@dataclass(frozen=True, slots=True)
class V5Event:
    ny_day: date
    thursday_day: date
    friday_day: date
    thursday_low: Decimal
    thursday_close: Decimal
    thursday_ce: Decimal
    friday_settlement: Decimal
    monday_open: Decimal
    gap: Decimal
    lower_quadrant_top: Decimal
    lowest_octant_top: Decimal
    inferred_sd2: Decimal
    sd2_distance_abs: Decimal
    sd2_distance_gap_ratio: Decimal
    opening: OpeningTelemetry
    sweep_at: datetime
    sweep_low: Decimal
    no_complete_body_below_thursday_low: bool
    no_close_at_or_below_inferred_sd2: bool
    fvg_created_at: datetime
    fvg_low: Decimal
    fvg_high: Decimal
    inversion_at: datetime
    inversion_close_above: bool
    entry_at: datetime
    entry: Decimal
    target_outcomes: tuple[TargetOutcome, ...]
    mfe_points: Decimal
    mae_points: Decimal
    robustness_gross_r: Decimal | None
    robustness_primary_r: Decimal | None
    robustness_stress_r: Decimal | None
    robustness_exit_reason: str | None


@dataclass(frozen=True, slots=True)
class DayRecord:
    ny_day: date
    terminal_stage: str
    reason: str
    opening: OpeningTelemetry | None
    inferred_sd2_distance_gap_ratio: Decimal | None
    event: V5Event | None


def _opening_pair_signature(
    bars: tuple[Bar, ...],
    *,
    index_a: int,
    lower_quadrant_top: Decimal,
    lowest_octant_top: Decimal,
) -> bool | None:
    index_b = index_a + 1
    if index_b >= len(bars):
        return None
    a = bars[index_a]
    b = bars[index_b]
    body_b_top = max(b.open, b.close)
    return (
        a.high < lower_quadrant_top
        and a.close < lowest_octant_top
        and body_b_top < lowest_octant_top
    )


def _opening_telemetry(
    current: v1.RthSession,
    *,
    lower_quadrant_top: Decimal,
    lowest_octant_top: Decimal,
) -> OpeningTelemetry:
    return OpeningTelemetry(
        pair_0930_0931=_opening_pair_signature(
            current.bars,
            index_a=0,
            lower_quadrant_top=lower_quadrant_top,
            lowest_octant_top=lowest_octant_top,
        ),
        pair_0931_0932=_opening_pair_signature(
            current.bars,
            index_a=1,
            lower_quadrant_top=lower_quadrant_top,
            lowest_octant_top=lowest_octant_top,
        ),
    )


def _complete_body_below(bar: Bar, level: Decimal) -> bool:
    return max(bar.open, bar.close) < level


def _delivery_fvg(
    bars: tuple[Bar, ...],
    *,
    start: datetime,
    sweep_at: datetime,
) -> BearishFvg | None:
    zones = v1._bearish_fvgs(
        bars,
        start=start,
        end=sweep_at + v1.M1,
    )
    if not zones:
        return None
    return zones[-1]


def _causal_inversion_and_retest(
    bars: tuple[Bar, ...],
    *,
    zone: BearishFvg,
    sweep_at: datetime,
    session_end: datetime,
) -> tuple[datetime, bool, datetime, Decimal] | None:
    after = tuple(
        bar for bar in bars if sweep_at <= bar.opened_at < session_end
    )
    inversion_index = next(
        (
            idx
            for idx, bar in enumerate(after)
            if bar.high > zone.high
        ),
        None,
    )
    if inversion_index is None:
        return None
    inversion_bar = after[inversion_index]
    for bar in after[inversion_index + 1 :]:
        overlaps = bar.low <= zone.high and bar.high >= zone.low
        if overlaps:
            return (
                inversion_bar.closed_at,
                inversion_bar.close > zone.high,
                bar.opened_at,
                zone.high,
            )
    return None


def _target_outcome(
    bars: tuple[Bar, ...],
    *,
    entry_at: datetime,
    sweep_low: Decimal,
    target_name: str,
    target_price: Decimal,
    entry: Decimal,
) -> TargetOutcome:
    if target_price <= entry:
        return TargetOutcome(target_name, target_price, False, None, None)
    start = entry_at
    for bar in bars:
        if bar.opened_at < start:
            continue
        structural_loss = bar.low < sweep_low
        target_touch = bar.high >= target_price
        if structural_loss:
            return TargetOutcome(target_name, target_price, True, False, None)
        if target_touch:
            minutes = int((bar.closed_at - entry_at).total_seconds() // 60)
            return TargetOutcome(target_name, target_price, True, True, minutes)
    return TargetOutcome(target_name, target_price, True, False, None)


def _excursions(
    bars: tuple[Bar, ...],
    *,
    entry_at: datetime,
    entry: Decimal,
) -> tuple[Decimal, Decimal]:
    path = tuple(bar for bar in bars if bar.opened_at >= entry_at)
    if not path:
        return Decimal(0), Decimal(0)
    max_high = max([entry, *(bar.high for bar in path)])
    min_low = min([entry, *(bar.low for bar in path)])
    return max_high - entry, entry - min_low


def _robustness(
    evidence: Evidence,
    bars: tuple[Bar, ...],
    *,
    entry_at: datetime,
    entry: Decimal,
    sweep_low: Decimal,
    target: Decimal,
    session_end: datetime,
) -> tuple[Decimal, Decimal, Decimal, str] | None:
    stop = sweep_low - v1._tick_size(evidence.digits)
    if not stop < entry < target:
        return None
    exit_at, exit_price, reason, gross_r, _mfe, _mae = v1._simulate(
        bars,
        entry_at=entry_at,
        expiry=session_end,
        entry=entry,
        stop=stop,
        target=target,
    )
    _ = exit_at, exit_price
    return (
        gross_r,
        gross_r - PRIMARY_FRICTION_R,
        gross_r - STRESS_FRICTION_R,
        reason,
    )


def replay(evidence: Evidence) -> list[DayRecord]:
    rth = v1.build_rth_sessions(evidence.bars)
    by_rth_day = {item.ny_day: item for item in rth}
    eth = v4._build_eth_daily_sessions(evidence.bars)
    by_eth_day = {item.trade_day: item for item in eth}

    records: list[DayRecord] = []
    for current in rth:
        day = current.ny_day
        if not EVAL_OPEN_NY <= day < EVAL_CLOSE_NY:
            continue
        if day.weekday() != 0:
            continue

        thursday_day = day - timedelta(days=4)
        friday_day = day - timedelta(days=3)
        thursday = by_eth_day.get(thursday_day)
        friday = by_rth_day.get(friday_day)
        if thursday is None or friday is None:
            records.append(
                DayRecord(
                    day,
                    "calendar-context",
                    "exact-prior-thursday-or-friday-missing",
                    None,
                    None,
                    None,
                )
            )
            continue

        gap = friday.settle - current.open
        if gap <= 0:
            records.append(
                DayRecord(
                    day,
                    "gap",
                    "not-discount-rth-opening-gap",
                    None,
                    None,
                    None,
                )
            )
            continue

        lower_quadrant_top = current.open + gap / Decimal(4)
        lowest_octant_top = current.open + gap / Decimal(8)
        opening = _opening_telemetry(
            current,
            lower_quadrant_top=lower_quadrant_top,
            lowest_octant_top=lowest_octant_top,
        )
        inferred_sd2 = current.open - Decimal(2) * gap
        distance_abs = abs(inferred_sd2 - thursday.low)
        distance_ratio = distance_abs / gap

        macro_open = v1._at_ny(day, v1.MACRO_FIRST_HALF_OPEN)
        macro_close = v1._at_ny(day, v1.MACRO_CLOSE)
        macro = tuple(
            bar
            for bar in evidence.bars
            if macro_open <= bar.opened_at < macro_close
        )
        sweep = next((bar for bar in macro if bar.low < thursday.low), None)
        if sweep is None:
            records.append(
                DayRecord(
                    day,
                    "sweep",
                    "no-thursday-low-trade-through-in-macro",
                    opening,
                    distance_ratio,
                    None,
                )
            )
            continue

        after_sweep_macro = tuple(
            bar for bar in macro if bar.opened_at >= sweep.opened_at
        )
        no_body_below = not any(
            _complete_body_below(bar, thursday.low)
            for bar in after_sweep_macro
        )
        no_close_below_sd2 = not any(
            bar.close <= inferred_sd2 for bar in after_sweep_macro
        )
        if not no_body_below:
            records.append(
                DayRecord(
                    day,
                    "acceptance",
                    "complete-body-established-below-thursday-low",
                    opening,
                    distance_ratio,
                    None,
                )
            )
            continue
        if not no_close_below_sd2:
            records.append(
                DayRecord(
                    day,
                    "acceptance",
                    "close-at-or-below-inferred-2sd",
                    opening,
                    distance_ratio,
                    None,
                )
            )
            continue

        zone = _delivery_fvg(
            evidence.bars,
            start=current.open_at,
            sweep_at=sweep.opened_at,
        )
        if zone is None:
            records.append(
                DayRecord(
                    day,
                    "fvg",
                    "no-bearish-delivery-fvg",
                    opening,
                    distance_ratio,
                    None,
                )
            )
            continue

        session_end = friday.settle_at
        session_end = v1._at_ny(day, v1.RTH_SETTLE_BAR) + v1.M1
        inversion = _causal_inversion_and_retest(
            evidence.bars,
            zone=zone,
            sweep_at=sweep.opened_at,
            session_end=session_end,
        )
        if inversion is None:
            records.append(
                DayRecord(
                    day,
                    "ifvg",
                    "no-causal-trade-above-and-later-retest",
                    opening,
                    distance_ratio,
                    None,
                )
            )
            continue

        inversion_at, inversion_close_above, entry_at, entry = inversion
        post_entry = tuple(
            bar
            for bar in evidence.bars
            if entry_at <= bar.opened_at < session_end
        )
        if not post_entry:
            records.append(
                DayRecord(
                    day,
                    "data",
                    "missing-post-entry-rth-path",
                    opening,
                    distance_ratio,
                    None,
                )
            )
            continue

        sweep_low = min(
            bar.low
            for bar in evidence.bars
            if sweep.opened_at <= bar.opened_at < entry_at
        )
        thursday_ce = (thursday.close + thursday.low) / Decimal(2)
        targets = (
            _target_outcome(
                post_entry,
                entry_at=entry_at,
                sweep_low=sweep_low,
                target_name="thursday_wick_ce",
                target_price=thursday_ce,
                entry=entry,
            ),
            _target_outcome(
                post_entry,
                entry_at=entry_at,
                sweep_low=sweep_low,
                target_name="rth_0930_open",
                target_price=current.open,
                entry=entry,
            ),
        )
        mfe_points, mae_points = _excursions(
            post_entry,
            entry_at=entry_at,
            entry=entry,
        )
        robustness = _robustness(
            evidence,
            post_entry,
            entry_at=entry_at,
            entry=entry,
            sweep_low=sweep_low,
            target=current.open,
            session_end=session_end,
        )
        gross_r: Decimal | None = None
        primary_r: Decimal | None = None
        stress_r: Decimal | None = None
        robustness_reason: str | None = None
        if robustness is not None:
            gross_r, primary_r, stress_r, robustness_reason = robustness

        event = V5Event(
            ny_day=day,
            thursday_day=thursday_day,
            friday_day=friday_day,
            thursday_low=thursday.low,
            thursday_close=thursday.close,
            thursday_ce=thursday_ce,
            friday_settlement=friday.settle,
            monday_open=current.open,
            gap=gap,
            lower_quadrant_top=lower_quadrant_top,
            lowest_octant_top=lowest_octant_top,
            inferred_sd2=inferred_sd2,
            sd2_distance_abs=distance_abs,
            sd2_distance_gap_ratio=distance_ratio,
            opening=opening,
            sweep_at=sweep.opened_at,
            sweep_low=sweep_low,
            no_complete_body_below_thursday_low=no_body_below,
            no_close_at_or_below_inferred_sd2=no_close_below_sd2,
            fvg_created_at=zone.created_at,
            fvg_low=zone.low,
            fvg_high=zone.high,
            inversion_at=inversion_at,
            inversion_close_above=inversion_close_above,
            entry_at=entry_at,
            entry=entry,
            target_outcomes=targets,
            mfe_points=mfe_points,
            mae_points=mae_points,
            robustness_gross_r=gross_r,
            robustness_primary_r=primary_r,
            robustness_stress_r=stress_r,
            robustness_exit_reason=robustness_reason,
        )
        records.append(
            DayRecord(
                day,
                "event",
                "source-resolved-event",
                opening,
                distance_ratio,
                event,
            )
        )

    return records


def _decimal_quantiles(values: list[Decimal]) -> dict[str, str] | None:
    if not values:
        return None
    ordered = sorted(values)

    def pick(frac: Decimal) -> Decimal:
        index = int((Decimal(len(ordered) - 1) * frac).to_integral_value())
        return ordered[index]

    return {
        "min": str(ordered[0]),
        "p25": str(pick(Decimal("0.25"))),
        "p50": str(pick(Decimal("0.50"))),
        "p75": str(pick(Decimal("0.75"))),
        "max": str(ordered[-1]),
    }


def summarize(records: list[DayRecord]) -> dict[str, Any]:
    events = [row.event for row in records if row.event is not None]
    event_list = [item for item in events if item is not None]
    primary_values = [
        item.robustness_primary_r
        for item in event_list
        if item.robustness_primary_r is not None
    ]
    stress_values = [
        item.robustness_stress_r
        for item in event_list
        if item.robustness_stress_r is not None
    ]
    primary_typed = [item for item in primary_values if item is not None]
    stress_typed = [item for item in stress_values if item is not None]

    targets: dict[str, dict[str, Any]] = {}
    for name in ("thursday_wick_ce", "rth_0930_open"):
        rows = [
            outcome
            for event in event_list
            for outcome in event.target_outcomes
            if outcome.target_name == name and outcome.eligible
        ]
        hits = [row for row in rows if row.reached_before_new_sweep_low is True]
        targets[name] = {
            "eligible_events": len(rows),
            "reached_before_new_sweep_low": len(hits),
            "reach_rate": None if not rows else len(hits) / len(rows),
            "time_to_target_minutes": _decimal_quantiles(
                [Decimal(row.time_to_target_minutes) for row in hits]
            ),
        }

    opening_rows = [row.opening for row in records if row.opening is not None]
    distance = [
        row.inferred_sd2_distance_gap_ratio
        for row in records
        if row.inferred_sd2_distance_gap_ratio is not None
    ]
    distance_typed = [item for item in distance if item is not None]
    close_above_count = sum(item.inversion_close_above for item in event_list)

    primary_pf = _profit_factor(primary_typed)
    stress_pf = _profit_factor(stress_typed)
    return {
        "schema": "qore.nq_am_tlr_v5.source_resolved_ustec_1y.v1",
        "identity": IDENTITY,
        "evaluation_open_ny": EVAL_OPEN_NY.isoformat(),
        "evaluation_close_ny": EVAL_CLOSE_NY.isoformat(),
        "scope": "MONDAY_SOURCE_REPLAY_ONLY",
        "source_run_id": SOURCE_RUN_ID,
        "source_artifact_id": SOURCE_ARTIFACT_ID,
        "source_evidence_sha256": SOURCE_EVIDENCE_SHA256,
        "inferred_2sd_formula": "monday_open - 2 * opening_gap",
        "inferred_2sd_has_source_authority": False,
        "source_stop_defined": False,
        "source_expiry_defined": False,
        "evaluated_mondays": len(records),
        "funnel": dict(sorted(Counter(row.terminal_stage for row in records).items())),
        "reasons": dict(sorted(Counter(row.reason for row in records).items())),
        "source_resolved_event_count": len(event_list),
        "opening_context_telemetry": {
            "pair_0930_0931_true": sum(
                row.pair_0930_0931 is True for row in opening_rows
            ),
            "pair_0931_0932_true": sum(
                row.pair_0931_0932 is True for row in opening_rows
            ),
            "hard_gate": False,
        },
        "inferred_2sd_distance_gap_ratio": _decimal_quantiles(distance_typed),
        "ifvg_inversion": {
            "trade_above_events": len(event_list),
            "also_closed_above_fvg_high": close_above_count,
            "close_above_was_required": False,
        },
        "targets": targets,
        "excursions_points": {
            "mfe": _decimal_quantiles([item.mfe_points for item in event_list]),
            "mae": _decimal_quantiles([item.mae_points for item in event_list]),
        },
        "qore_structural_stop_robustness_only": {
            "source_rule_authority": False,
            "trade_count": len(primary_typed),
            "primary_total_r": str(sum(primary_typed, Decimal(0))),
            "primary_pf": None if primary_pf is None else str(primary_pf),
            "primary_max_drawdown_r": str(_max_drawdown(primary_typed)),
            "stress_total_r": str(sum(stress_typed, Decimal(0))),
            "stress_pf": None if stress_pf is None else str(stress_pf),
            "exit_reasons": dict(
                sorted(
                    Counter(
                        item.robustness_exit_reason
                        for item in event_list
                        if item.robustness_exit_reason is not None
                    ).items()
                )
            ),
        },
        "diagnostic_selection_authority": False,
        "demo_eligible": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
    }


def _json_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, tuple):
        return [_json_value(item) for item in value]
    if hasattr(value, "__dataclass_fields__"):
        return {
            key: _json_value(item)
            for key, item in asdict(value).items()
        }
    return value


def write_study(evidence_path: Path, output: Path) -> dict[str, Any]:
    evidence, payload = v4.load_evidence(evidence_path)
    if payload.get("provider_symbol_name") != "USTEC":
        raise ValueError("V5 requires retained USTEC evidence")
    records = replay(evidence)
    summary = summarize(records)
    output.mkdir(parents=True, exist_ok=True)
    (output / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n"
    )
    (output / "records.json").write_text(
        json.dumps(
            [
                {
                    "ny_day": row.ny_day.isoformat(),
                    "terminal_stage": row.terminal_stage,
                    "reason": row.reason,
                    "opening": _json_value(row.opening),
                    "inferred_sd2_distance_gap_ratio": _json_value(
                        row.inferred_sd2_distance_gap_ratio
                    ),
                    "has_event": row.event is not None,
                }
                for row in records
            ],
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    (output / "events.json").write_text(
        json.dumps(
            [_json_value(row.event) for row in records if row.event is not None],
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(json.dumps(write_study(args.evidence, args.output), sort_keys=True))


if __name__ == "__main__":
    main()
