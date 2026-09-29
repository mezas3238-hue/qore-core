"""USTEC provider-normalized source replay for the ICT NQ AM reversal.

V6 changes only the provider settlement adapter relative to V5. The source uses
NQ's Friday 16:14 ET final RTH print; cTrader USTEC does not always expose that
timestamp. V6 uses the latest provider bar from 15:30-16:30 ET without fabricating
a 16:14 bar.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab import nq_am_temporal_liquidity_reversal_v1 as v1
from qore.infrastructure.trader_lab import nq_am_tlr_v4_ustec_capability as v4
from qore.infrastructure.trader_lab import nq_am_tlr_v5_source_resolved as v5
from qore.infrastructure.trader_lab.ict_turtle_soup_r4_source_exact import (
    Bar,
    Evidence,
)

IDENTITY = "QORE_NQ_AM_TLR_V6_USTEC_PROVIDER_NORMALIZED_001"
EVAL_OPEN_NY = v5.EVAL_OPEN_NY
EVAL_CLOSE_NY = v5.EVAL_CLOSE_NY
NY = ZoneInfo("America/New_York")
FINAL_WINDOW_OPEN = time(15, 30)
FINAL_WINDOW_CLOSE = time(16, 30)


@dataclass(frozen=True, slots=True)
class ProviderAnchor:
    ny_day: date
    opened_at: datetime
    close: Decimal


def _wall(moment: datetime) -> time:
    return moment.astimezone(NY).timetz().replace(tzinfo=None)


def _ny_day(moment: datetime) -> date:
    return moment.astimezone(NY).date()


def build_provider_rth_sessions(
    bars: tuple[Bar, ...],
) -> tuple[v1.RthSession, ...]:
    by_day: dict[date, list[Bar]] = {}
    for bar in bars:
        wall = _wall(bar.opened_at)
        if v1.RTH_OPEN <= wall <= FINAL_WINDOW_CLOSE:
            by_day.setdefault(_ny_day(bar.opened_at), []).append(bar)

    sessions: list[v1.RthSession] = []
    for day, raw in sorted(by_day.items()):
        ordered = tuple(sorted(raw, key=lambda item: item.opened_at))
        open_at = v1._at_ny(day, v1.RTH_OPEN)
        opening = next(
            (item for item in ordered if item.opened_at == open_at),
            None,
        )
        final_candidates = tuple(
            item
            for item in ordered
            if FINAL_WINDOW_OPEN <= _wall(item.opened_at) <= FINAL_WINDOW_CLOSE
        )
        if opening is None or not final_candidates:
            continue
        final_bar = final_candidates[-1]
        sessions.append(
            v1.RthSession(
                ny_day=day,
                open_at=open_at,
                settle_at=final_bar.opened_at,
                open=opening.open,
                high=max(item.high for item in ordered),
                low=min(item.low for item in ordered),
                settle=final_bar.close,
                bars=ordered,
            )
        )
    return tuple(sessions)


def replay(
    evidence: Evidence,
) -> tuple[list[v5.DayRecord], dict[date, ProviderAnchor]]:
    rth = build_provider_rth_sessions(evidence.bars)
    by_rth_day = {item.ny_day: item for item in rth}
    eth = v4._build_eth_daily_sessions(evidence.bars)
    by_eth_day = {item.trade_day: item for item in eth}
    anchors = {
        item.ny_day: ProviderAnchor(
            ny_day=item.ny_day,
            opened_at=item.settle_at,
            close=item.settle,
        )
        for item in rth
    }

    records: list[v5.DayRecord] = []
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
                v5.DayRecord(
                    day,
                    "calendar-context",
                    "exact-prior-thursday-or-provider-friday-missing",
                    None,
                    None,
                    None,
                )
            )
            continue

        gap = friday.settle - current.open
        if gap <= 0:
            records.append(
                v5.DayRecord(
                    day,
                    "gap",
                    "not-discount-provider-opening-gap",
                    None,
                    None,
                    None,
                )
            )
            continue

        lower_quadrant_top = current.open + gap / Decimal(4)
        lowest_octant_top = current.open + gap / Decimal(8)
        opening = v5._opening_telemetry(
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
                v5.DayRecord(
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
            v5._complete_body_below(bar, thursday.low)
            for bar in after_sweep_macro
        )
        no_close_below_sd2 = not any(
            bar.close <= inferred_sd2 for bar in after_sweep_macro
        )
        if not no_body_below:
            records.append(
                v5.DayRecord(
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
                v5.DayRecord(
                    day,
                    "acceptance",
                    "close-at-or-below-inferred-2sd",
                    opening,
                    distance_ratio,
                    None,
                )
            )
            continue

        zone = v5._delivery_fvg(
            evidence.bars,
            start=current.open_at,
            sweep_at=sweep.opened_at,
        )
        if zone is None:
            records.append(
                v5.DayRecord(
                    day,
                    "fvg",
                    "no-bearish-delivery-fvg",
                    opening,
                    distance_ratio,
                    None,
                )
            )
            continue

        session_end = current.settle_at + v1.M1
        inversion = v5._causal_inversion_and_retest(
            evidence.bars,
            zone=zone,
            sweep_at=sweep.opened_at,
            session_end=session_end,
        )
        if inversion is None:
            records.append(
                v5.DayRecord(
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
                v5.DayRecord(
                    day,
                    "data",
                    "missing-post-entry-provider-rth-path",
                    opening,
                    distance_ratio,
                    None,
                )
            )
            continue

        sweep_path = tuple(
            bar
            for bar in evidence.bars
            if sweep.opened_at <= bar.opened_at < entry_at
        )
        if not sweep_path:
            records.append(
                v5.DayRecord(
                    day,
                    "data",
                    "missing-sweep-to-entry-path",
                    opening,
                    distance_ratio,
                    None,
                )
            )
            continue
        sweep_low = min(bar.low for bar in sweep_path)
        thursday_ce = (thursday.close + thursday.low) / Decimal(2)
        targets = (
            v5._target_outcome(
                post_entry,
                entry_at=entry_at,
                sweep_low=sweep_low,
                target_name="thursday_wick_ce",
                target_price=thursday_ce,
                entry=entry,
            ),
            v5._target_outcome(
                post_entry,
                entry_at=entry_at,
                sweep_low=sweep_low,
                target_name="rth_0930_open",
                target_price=current.open,
                entry=entry,
            ),
        )
        mfe_points, mae_points = v5._excursions(
            post_entry,
            entry_at=entry_at,
            entry=entry,
        )
        robustness = v5._robustness(
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

        event = v5.V5Event(
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
            v5.DayRecord(
                day,
                "event",
                "provider-normalized-source-event",
                opening,
                distance_ratio,
                event,
            )
        )

    return records, anchors


def summarize(
    records: list[v5.DayRecord],
    anchors: dict[date, ProviderAnchor],
) -> dict[str, Any]:
    summary = v5.summarize(records)
    summary["schema"] = "qore.nq_am_tlr_v6.ustec_provider_normalized.v1"
    summary["identity"] = IDENTITY
    summary["scope"] = "MONDAY_USTEC_PROVIDER_NORMALIZED_REPLAY"
    summary["provider_anchor_source_authority"] = False
    summary["provider_anchor_rule"] = (
        "latest USTEC M1 bar in 15:30-16:30 America/New_York"
    )
    friday_anchors = [
        anchor
        for day, anchor in anchors.items()
        if day.weekday() == 4 and EVAL_OPEN_NY - timedelta(days=4) <= day < EVAL_CLOSE_NY
    ]
    summary["provider_anchor_telemetry"] = {
        "friday_anchor_count": len(friday_anchors),
        "times": dict(
            sorted(
                Counter(
                    anchor.opened_at.astimezone(NY).strftime("%H:%M")
                    for anchor in friday_anchors
                ).items()
            )
        ),
    }
    return summary


def _json_anchor(anchor: ProviderAnchor) -> dict[str, str]:
    return {
        "ny_day": anchor.ny_day.isoformat(),
        "opened_at": anchor.opened_at.isoformat(),
        "close": str(anchor.close),
    }


def write_study(evidence_path: Path, output: Path) -> dict[str, Any]:
    evidence, payload = v4.load_evidence(evidence_path)
    if payload.get("provider_symbol_name") != "USTEC":
        raise ValueError("V6 requires retained USTEC evidence")
    records, anchors = replay(evidence)
    summary = summarize(records, anchors)
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
                    "opening": v5._json_value(row.opening),
                    "inferred_sd2_distance_gap_ratio": v5._json_value(
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
            [v5._json_value(row.event) for row in records if row.event is not None],
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    (output / "provider-anchors.json").write_text(
        json.dumps(
            [_json_anchor(anchor) for _, anchor in sorted(anchors.items())],
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
