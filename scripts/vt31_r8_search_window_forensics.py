"""VT-31 R8 consumed-only search/window forensics.

This research never changes or revives rejected R8. It tests two causal questions
raised by the R8 fresh failure using only already-consumed R5/R6/R8 evidence:

1. The frozen replay stops the day when the first base R2.6 setup fails QORE
   quality. The contract says "first executable setup", so test the causal
   alternative of continuing to the first quality-eligible setup.
2. The source Silver Bullet window is 10:00-11:00 NY while QORE empirically
   contained signals to <=10:20. Test a finite, predeclared cutoff neighborhood
   without changing any other quality rule.

No new evidence is opened and no result from this file is candidate approval.
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, date
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_r5_candidate as r5
import vt31_r8_candidate as r8

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    _metrics,
    _quartiles,
    _wall,
    load_market_evidence,
)
from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_6_composite_entry_research import (
    _evaluate,
)
from qore.infrastructure.traders.vt31_silver_bullet_r2_2 import (
    _detect_raid,
    _session_bars,
    _structure,
    build_reference_range,
)

CUTOFFS = (20, 30, 40, 50, 59)
SEMANTICS = ("first-base", "first-quality-eligible")
FRICTION = Decimal("0.05")


@dataclass(frozen=True, slots=True)
class CandidateObservation:
    minute: int
    index: int
    setup: object
    non_time_quality: bool


def _d(value: float) -> Decimal:
    return Decimal(str(value))


def _non_time_quality(
    prefix: tuple[object, ...], setup: object, reference_width: Decimal
) -> bool:
    instrument = getattr(prefix[0], "instrument")
    signal_at = getattr(setup, "signal_at")
    reference = build_reference_range(
        instrument=instrument,
        as_of=signal_at,
        bars=cast(object, prefix),
    )
    if reference is None:
        return False
    session = _session_bars(signal_at, cast(object, prefix))
    raid = _detect_raid(session, reference)
    if raid is None or (raid.high_taken and raid.low_taken):
        return False
    structure = _structure(session, raid)
    if structure is None:
        return False
    confirmation_index, extreme_index, _, _ = structure
    confirmation = session[confirmation_index]
    raid_bar = session[raid.index]

    raid_span = _d(raid_bar.high) - _d(raid_bar.low)
    if raid_span <= 0:
        return False
    raid_body_fraction = abs(_d(raid_bar.close) - _d(raid_bar.open)) / raid_span
    raid_to_extreme_bars = extreme_index - raid.index

    span = _d(confirmation.high) - _d(confirmation.low)
    if span <= 0:
        return False
    opened = _d(confirmation.open)
    closed = _d(confirmation.close)
    side = getattr(setup, "side").value
    aligned = closed > opened if side == "long" else closed < opened
    confirmation_body_fraction = abs(closed - opened) / span
    risk = cast(Decimal, getattr(setup, "risk"))
    return (
        aligned
        and confirmation_body_fraction >= r8.MIN_CONFIRMATION_BODY_FRACTION
        and risk / reference_width <= r8.MAX_RISK_TO_REFERENCE
        and raid_body_fraction >= r8.MIN_RAID_BODY_FRACTION
        and raid_to_extreme_bars <= r8.MAX_RAID_TO_EXTREME_BARS
    )


def _variant_id(semantics: str, cutoff: int) -> str:
    return f"{semantics}:cutoff-{cutoff:02d}"


def _choose(
    observations: list[CandidateObservation], semantics: str, cutoff: int
) -> CandidateObservation | None:
    eligible_time = [item for item in observations if item.minute <= cutoff]
    if not eligible_time:
        return None
    if semantics == "first-base":
        first = eligible_time[0]
        return first if first.non_time_quality else None
    for item in eligible_time:
        if item.non_time_quality:
            return item
    return None


def _run_market(path: Path, market: str) -> dict[str, object]:
    series, _, _, _, _, _ = load_market_evidence(path)
    by_day: dict[date, list[object]] = defaultdict(list)
    for bar in series:
        by_day[_day(bar.opened_at)].append(bar)

    trades: dict[str, list[dict[str, object]]] = {
        _variant_id(s, c): [] for s in SEMANTICS for c in CUTOFFS
    }
    terminal_reason_at_cutoff: dict[str, Counter[str]] = {
        f"cutoff-{c:02d}": Counter() for c in CUTOFFS
    }
    day_counts: Counter[str] = Counter()
    rescue_counts: Counter[str] = Counter()

    for local_day in sorted(by_day):
        day_counts["days"] += 1
        day_bars = tuple(by_day[local_day])
        reference = tuple(
            item
            for item in day_bars
            if (9, 0, 0) <= _wall(getattr(item, "opened_at")) < (10, 0, 0)
        )
        indexed_session = tuple(
            (index, item)
            for index, item in enumerate(day_bars)
            if (10, 0, 0) <= _wall(getattr(item, "opened_at")) < (11, 0, 0)
        )
        if len(reference) != 60 or len(indexed_session) != 60:
            day_counts["incomplete_session"] += 1
            continue
        ref_high = max(_d(cast(float, getattr(item, "high"))) for item in reference)
        ref_low = min(_d(cast(float, getattr(item, "low"))) for item in reference)
        ref_width = ref_high - ref_low
        if ref_width <= 0:
            day_counts["invalid_reference"] += 1
            continue

        prefix = list(reference)
        observations: list[CandidateObservation] = []
        reasons_by_minute: dict[int, str] = {}
        for global_index, bar in indexed_session:
            prefix.append(bar)
            local = getattr(bar, "closed_at").astimezone(r5.NY)
            minute = local.hour * 60 + local.minute - 10 * 60
            setup, reason = _evaluate(
                instrument=getattr(bar, "instrument"),
                as_of=getattr(bar, "closed_at"),
                bars=cast(object, tuple(prefix)),
                variant=r5.BASE_VARIANT,
            )
            reasons_by_minute[minute] = reason
            if setup is None:
                continue
            observations.append(
                CandidateObservation(
                    minute=minute,
                    index=global_index,
                    setup=setup,
                    non_time_quality=_non_time_quality(tuple(prefix), setup, ref_width),
                )
            )

        if observations:
            day_counts["any_base_candidate"] += 1
        else:
            day_counts["no_base_candidate"] += 1

        for cutoff in CUTOFFS:
            key = f"cutoff-{cutoff:02d}"
            first_base = _choose(observations, "first-base", cutoff)
            first_quality = _choose(observations, "first-quality-eligible", cutoff)
            if first_quality is not None and first_base is None:
                rescue_counts[key] += 1
            terminal_reason_at_cutoff[key][reasons_by_minute.get(cutoff, "missing-minute")] += 1

        for semantics in SEMANTICS:
            for cutoff in CUTOFFS:
                chosen = _choose(observations, semantics, cutoff)
                if chosen is None:
                    continue
                trade = r5._simulate(day_bars, chosen.index, chosen.setup)
                if trade is None:
                    continue
                trade["market"] = market
                trades[_variant_id(semantics, cutoff)].append(trade)

    return {
        "market": market,
        "bar_count": len(series),
        "first_opened_at": series[0].opened_at.astimezone(UTC).isoformat(),
        "last_closed_at": series[-1].closed_at.astimezone(UTC).isoformat(),
        "day_counts": dict(day_counts),
        "rescued_days": dict(rescue_counts),
        "terminal_reason_at_cutoff": {
            key: dict(counter) for key, counter in terminal_reason_at_cutoff.items()
        },
        "trades": trades,
    }


def _summarize(trades: list[dict[str, object]]) -> dict[str, object]:
    trades.sort(key=lambda x: (cast(str, x["signal_at"]), cast(str, x["market"])))
    stress = _metrics(trades, friction=FRICTION)
    markets = {
        market: _metrics(
            [x for x in trades if x["market"] == market], friction=FRICTION
        )
        for market in r8.MARKETS
    }
    sides = {
        side: _metrics([x for x in trades if x["side"] == side], friction=FRICTION)
        for side in ("long", "short")
    }
    quartiles = _quartiles(trades)
    return {
        "stress": stress,
        "markets": markets,
        "sides": sides,
        "quartiles": quartiles,
    }


def _half_year(local_date: str) -> str:
    year = int(local_date[:4])
    month = int(local_date[5:7])
    return f"{year}-H{1 if month <= 6 else 2}"


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 9:
        print(
            "usage: vt31_r8_search_window_forensics.py "
            "R5_NAS100 R5_SP500 R5_US30 R6_NAS100 R6_SP500 R6_US30 "
            "R8_NAS100 R8_SP500 R8_US30"
        )
        return 2

    r8._configure_parent()
    partitions = {
        "r5": dict(zip(r8.MARKETS, map(Path, args[0:3]), strict=True)),
        "r6": dict(zip(r8.MARKETS, map(Path, args[3:6]), strict=True)),
        "r8_fresh": dict(zip(r8.MARKETS, map(Path, args[6:9]), strict=True)),
    }
    raw: dict[str, dict[str, object]] = {}
    by_variant_all: dict[str, list[dict[str, object]]] = defaultdict(list)
    by_variant_partition: dict[str, dict[str, list[dict[str, object]]]] = defaultdict(
        lambda: defaultdict(list)
    )

    for partition, paths in partitions.items():
        raw[partition] = {}
        for market, path in paths.items():
            result = _run_market(path, market)
            raw[partition][market] = {
                key: value for key, value in result.items() if key != "trades"
            }
            for variant, rows in cast(
                dict[str, list[dict[str, object]]], result["trades"]
            ).items():
                for row in rows:
                    row["partition"] = partition
                by_variant_all[variant].extend(rows)
                by_variant_partition[variant][partition].extend(rows)

    variants: dict[str, object] = {}
    for variant, rows in sorted(by_variant_all.items()):
        fixed = _summarize(list(rows))
        partitions_summary = {
            partition: _summarize(list(part_rows))
            for partition, part_rows in by_variant_partition[variant].items()
        }
        half_years: dict[str, list[dict[str, object]]] = defaultdict(list)
        for row in rows:
            half_years[_half_year(cast(str, row["local_date"]))].append(row)
        half_year_summary = {
            key: _metrics(value, friction=FRICTION)
            for key, value in sorted(half_years.items())
        }
        variants[variant] = {
            "all_consumed": fixed,
            "partition": partitions_summary,
            "half_year": half_year_summary,
            "positive_half_years": sum(
                Decimal(cast(str, value["mean_r"])) > 0
                for value in half_year_summary.values()
            ),
            "half_year_count": len(half_year_summary),
        }

    report = {
        "schema": "qore.trader_lab.vt31_r8_search_window_forensics.v1",
        "candidate_status": "R8_REJECTED_FRESH",
        "fresh_evidence_opened": False,
        "new_evidence_opened_by_this_run": False,
        "hypotheses": {
            "H1": "continue from rejected base setups to first quality-eligible setup causally",
            "H2": "test predeclared source-window cutoffs 10:20/30/40/50/59 with all other R8 rules frozen",
        },
        "cutoffs": list(CUTOFFS),
        "semantics": list(SEMANTICS),
        "raw_funnel": raw,
        "variants": variants,
        "governance": {
            "r8_retuned": False,
            "candidate_approved": False,
            "new_candidate_defined": False,
            "live_authorized": False,
            "production_authorized": False,
        },
    }
    Path("vt31-r8-search-window-forensics.json").write_text(
        json.dumps(report, sort_keys=True, separators=(",", ":")) + "\n"
    )

    compact = {
        variant: {
            "sample": value["all_consumed"]["stress"]["sample"],
            "mean_r": value["all_consumed"]["stress"]["mean_r"],
            "pf": value["all_consumed"]["stress"]["profit_factor"],
            "dd": value["all_consumed"]["stress"]["max_drawdown_r"],
            "positive_half_years": value["positive_half_years"],
            "half_year_count": value["half_year_count"],
            "fresh": value["partition"]["r8_fresh"]["stress"],
            "fresh_markets": value["partition"]["r8_fresh"]["markets"],
            "fresh_sides": value["partition"]["r8_fresh"]["sides"],
        }
        for variant, value in cast(dict[str, dict[str, object]], variants).items()
    }
    Path("vt31-r8-search-window-summary.json").write_text(
        json.dumps(compact, sort_keys=True, indent=2) + "\n"
    )
    print(json.dumps(compact, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
