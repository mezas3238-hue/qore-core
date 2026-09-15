"""Consumed-only VT-31 R8 sparse-reference semantics forensics.

cTrader Open API creates trend bars only when incoming ticks exist. Therefore a
missing M1 trend bar inside 09:00-10:00 NY is not, by itself, proof that market
evidence is missing; it can mean that no tick arrived during that minute. The
frozen R8 replay nevertheless requires exactly 60 M1 reference bars and thereby
collapses old SP500 sample density.

This research keeps all R8 trading semantics frozen and changes only the
reference-evidence admission rule. The 10:00-11:00 setup session still requires
all 60 M1 bars so raid/structure/entry timing is unchanged. A finite family of
maximum consecutive missing reference-minute thresholds is tested only on
already-consumed R5/R6/R8 evidence. No candidate is approved here.
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from datetime import UTC, date, datetime, time
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_r5_candidate as r5
import vt31_r8_candidate as r8

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    Vt31R25Variant,
    _Setup,
    _day,
    _metrics,
    _quartiles,
    _wall,
    load_market_evidence,
)
from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_6_composite_entry_research import (
    Vt31R26Variant,
    _select_nearest_retracement,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt31_silver_bullet_r2_2 import (
    Vt31R22ReferenceRange,
    _detect_raid,
    _entry_evidence,
    _session_bars,
    _structure,
    _validate_evidence,
)

FRICTION = Decimal("0.05")
MARKETS = ("NAS100", "SP500", "US30")
POLICIES: dict[str, int | None] = {
    "strict60": 0,
    "gap01": 1,
    "gap03": 3,
    "gap05": 5,
    "gap10": 10,
    "sparse-any": None,
}
CTRADER_TRENDBAR_SEMANTICS = (
    "https://help.ctrader.com/open-api/faq/ : trend bars are created only if "
    "there are incoming ticks"
)


def _d(value: float) -> Decimal:
    return Decimal(str(value))


def _reference_bars(bars: tuple[object, ...]) -> tuple[object, ...]:
    return tuple(
        bar
        for bar in bars
        if (9, 0, 0) <= _wall(getattr(bar, "opened_at")) < (10, 0, 0)
    )


def _max_missing_run(reference: tuple[object, ...]) -> int:
    minutes = {
        getattr(bar, "opened_at").astimezone(r5.NY).minute for bar in reference
    }
    missing = [minute for minute in range(60) if minute not in minutes]
    maximum = 0
    current = 0
    previous: int | None = None
    for minute in missing:
        if previous is not None and minute == previous + 1:
            current += 1
        else:
            current = 1
        maximum = max(maximum, current)
        previous = minute
    return maximum


def _policy_accepts(reference: tuple[object, ...], policy: str) -> bool:
    if not reference:
        return False
    threshold = POLICIES[policy]
    if threshold == 0:
        return len(reference) == 60 and _max_missing_run(reference) == 0
    return threshold is None or _max_missing_run(reference) <= threshold


def _sparse_reference(
    *,
    instrument: object,
    as_of: datetime,
    bars: tuple[object, ...],
) -> Vt31R22ReferenceRange | None:
    _validate_evidence(instrument, as_of, cast(object, bars))
    selected = _reference_bars(bars)
    if not selected:
        return None
    local_day = as_of.astimezone(r5.NY).date()
    opened = datetime.combine(local_day, time(9, 0), tzinfo=r5.NY).astimezone(UTC)
    closed = datetime.combine(local_day, time(10, 0), tzinfo=r5.NY).astimezone(UTC)
    return Vt31R22ReferenceRange(
        high=max(_d(cast(float, getattr(item, "high"))) for item in selected),
        low=min(_d(cast(float, getattr(item, "low"))) for item in selected),
        opened_at=opened,
        closed_at=closed,
    )


def _evaluate_sparse(
    *,
    instrument: object,
    as_of: datetime,
    bars: tuple[object, ...],
    variant: Vt31R26Variant,
) -> tuple[_Setup | None, str]:
    reference = _sparse_reference(
        instrument=instrument,
        as_of=as_of,
        bars=bars,
    )
    if reference is None:
        return None, "reference-incomplete"
    session = _session_bars(as_of, cast(object, bars))
    raid = _detect_raid(session, reference)
    if raid is None:
        return None, "no-raid"
    if raid.high_taken and raid.low_taken:
        return None, "both-sides-swept"
    structure = _structure(session, raid)
    if structure is None:
        return None, "no-structure-confirmation"
    confirmation_index, extreme_index, extreme, _ = structure
    candidates = _entry_evidence(session, raid, confirmation_index, extreme_index)
    if not candidates:
        return None, "no-demonstrated-entry-family"
    confirmation_close = _d(cast(float, getattr(session[confirmation_index], "close")))
    target = (
        reference.low
        if raid.side is DemoTradingSetupSide.SHORT
        else reference.high
    )
    entry, reason = _select_nearest_retracement(
        candidates,
        side=raid.side,
        confirmation_close=confirmation_close,
        extreme=extreme,
        target=target,
        location=variant.location,
    )
    if entry is None:
        return None, reason
    return (
        _Setup(
            raid.side,
            as_of.astimezone(UTC),
            entry,
            extreme,
            target,
            cast(Vt31R25Variant, variant),
        ),
        "setup",
    )


def _quality_sparse(
    prefix: tuple[object, ...], setup: object, reference_width: Decimal
) -> bool:
    signal_at = cast(datetime, getattr(setup, "signal_at"))
    reference = _sparse_reference(
        instrument=getattr(prefix[0], "instrument"),
        as_of=signal_at,
        bars=prefix,
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

    raid_span = _d(cast(float, getattr(raid_bar, "high"))) - _d(
        cast(float, getattr(raid_bar, "low"))
    )
    if raid_span <= 0:
        return False
    raid_body_fraction = abs(
        _d(cast(float, getattr(raid_bar, "close")))
        - _d(cast(float, getattr(raid_bar, "open")))
    ) / raid_span
    raid_to_extreme_bars = extreme_index - raid.index

    confirmation_span = _d(cast(float, getattr(confirmation, "high"))) - _d(
        cast(float, getattr(confirmation, "low"))
    )
    if confirmation_span <= 0:
        return False
    opened = _d(cast(float, getattr(confirmation, "open")))
    closed = _d(cast(float, getattr(confirmation, "close")))
    side = getattr(setup, "side").value
    aligned = closed > opened if side == "long" else closed < opened
    confirmation_body_fraction = abs(closed - opened) / confirmation_span
    risk = cast(Decimal, getattr(setup, "risk"))
    local = signal_at.astimezone(r5.NY)
    signal_minute = local.hour * 60 + local.minute - 10 * 60
    return (
        aligned
        and confirmation_body_fraction >= r8.MIN_CONFIRMATION_BODY_FRACTION
        and signal_minute <= r8.MAX_SIGNAL_MINUTE
        and risk / reference_width <= r8.MAX_RISK_TO_REFERENCE
        and raid_body_fraction >= r8.MIN_RAID_BODY_FRACTION
        and raid_to_extreme_bars <= r8.MAX_RAID_TO_EXTREME_BARS
    )


def _run_market(path: Path, market: str) -> dict[str, object]:
    series, _, _, _, _, provider = load_market_evidence(path)
    by_day: dict[date, list[object]] = defaultdict(list)
    for bar in series:
        by_day[_day(bar.opened_at)].append(bar)

    trades: dict[str, list[dict[str, object]]] = {
        policy: [] for policy in POLICIES
    }
    counters: dict[str, Counter[str]] = {
        policy: Counter() for policy in POLICIES
    }
    reference_histogram: Counter[str] = Counter()

    for local_day in sorted(by_day):
        day_bars = tuple(by_day[local_day])
        reference = _reference_bars(day_bars)
        indexed_session = tuple(
            (index, bar)
            for index, bar in enumerate(day_bars)
            if (10, 0, 0) <= _wall(getattr(bar, "opened_at")) < (11, 0, 0)
        )
        if len(indexed_session) != 60 or not reference:
            continue

        missing_run = _max_missing_run(reference)
        reference_histogram[f"bars-{len(reference):02d}"] += 1
        qualifying = [
            policy for policy in POLICIES if _policy_accepts(reference, policy)
        ]
        if not qualifying:
            continue
        for policy in qualifying:
            counters[policy]["reference_admitted_days"] += 1

        ref_high = max(_d(cast(float, getattr(item, "high"))) for item in reference)
        ref_low = min(_d(cast(float, getattr(item, "low"))) for item in reference)
        ref_width = ref_high - ref_low
        if ref_width <= 0:
            for policy in qualifying:
                counters[policy]["invalid_reference"] += 1
            continue

        prefix = list(reference)
        selected = None
        selected_index: int | None = None
        first_base = False
        quality_pass = False
        terminal_reason = "no-base-candidate"
        for global_index, bar in indexed_session:
            prefix.append(bar)
            candidate, reason = _evaluate_sparse(
                instrument=getattr(bar, "instrument"),
                as_of=getattr(bar, "closed_at"),
                bars=tuple(prefix),
                variant=r5.BASE_VARIANT,
            )
            terminal_reason = reason
            if candidate is None:
                continue
            first_base = True
            if not _quality_sparse(tuple(prefix), candidate, ref_width):
                terminal_reason = "first-base-failed-r8-quality"
                break
            quality_pass = True
            selected = candidate
            selected_index = global_index
            terminal_reason = "selected"
            break

        trade: dict[str, object] | None = None
        if selected is not None and selected_index is not None:
            trade = r5._simulate(day_bars, selected_index, selected)
            if trade is not None:
                trade["market"] = market
                trade["reference_bar_count"] = len(reference)
                trade["reference_max_missing_run"] = missing_run

        for policy in qualifying:
            if first_base:
                counters[policy]["first_base_candidate_days"] += 1
            if quality_pass:
                counters[policy]["quality_pass_days"] += 1
            if trade is not None:
                counters[policy]["resolved_trade_days"] += 1
                trades[policy].append(dict(trade))
            else:
                counters[policy][f"terminal:{terminal_reason}"] += 1

    return {
        "market": market,
        "provider": provider,
        "bar_count": len(series),
        "first_opened_at": series[0].opened_at.astimezone(UTC).isoformat(),
        "last_closed_at": series[-1].closed_at.astimezone(UTC).isoformat(),
        "reference_bar_histogram": dict(sorted(reference_histogram.items())),
        "counters": {
            policy: dict(sorted(counter.items()))
            for policy, counter in counters.items()
        },
        "trades": trades,
    }


def _summarize(trades: list[dict[str, object]]) -> dict[str, object]:
    trades.sort(key=lambda x: (cast(str, x["signal_at"]), cast(str, x["market"])))
    stress = _metrics(trades, friction=FRICTION)
    markets = {
        market: _metrics(
            [row for row in trades if row["market"] == market], friction=FRICTION
        )
        for market in MARKETS
    }
    sides = {
        side: _metrics(
            [row for row in trades if row["side"] == side], friction=FRICTION
        )
        for side in ("long", "short")
    }
    quartiles = _quartiles(trades)
    market_year: dict[str, dict[str, object]] = {}
    for market in MARKETS:
        own = [row for row in trades if row["market"] == market]
        for year in sorted({cast(str, row["local_date"])[:4] for row in own}):
            market_year[f"{market}:{year}"] = _metrics(
                [
                    row
                    for row in own
                    if cast(str, row["local_date"]).startswith(year)
                ],
                friction=FRICTION,
            )
    eligible_temporal = [
        value for value in market_year.values() if cast(int, value["sample"]) >= 10
    ]
    gates = {
        "aggregate_sample_at_least_150": cast(int, stress["sample"]) >= 150,
        "each_market_sample_at_least_30": all(
            cast(int, value["sample"]) >= 30 for value in markets.values()
        ),
        "aggregate_stressed_mean_positive": Decimal(cast(str, stress["mean_r"])) > 0,
        "aggregate_stressed_pf_at_least_1_10": stress["profit_factor"] is not None
        and Decimal(cast(str, stress["profit_factor"])) >= Decimal("1.10"),
        "aggregate_stressed_dd_at_most_20r": Decimal(
            cast(str, stress["max_drawdown_r"])
        )
        <= Decimal(20),
        "every_market_stressed_mean_positive": all(
            Decimal(cast(str, value["mean_r"])) > 0 for value in markets.values()
        ),
        "both_sides_stressed_mean_positive": all(
            cast(int, value["sample"]) > 0
            and Decimal(cast(str, value["mean_r"])) > 0
            for value in sides.values()
        ),
        "three_of_four_quartiles_positive": sum(
            Decimal(cast(str, value["mean_r"])) > 0 for value in quartiles
        )
        >= 3,
        "two_thirds_eligible_temporal_blocks_positive": bool(eligible_temporal)
        and sum(
            Decimal(cast(str, value["mean_r"])) > 0
            for value in eligible_temporal
        )
        * 3
        >= len(eligible_temporal) * 2,
    }
    return {
        "stress": stress,
        "markets": markets,
        "sides": sides,
        "quartiles": quartiles,
        "market_year": market_year,
        "gates": gates,
        "passes_deterministic_gates": all(gates.values()),
    }


def _half_year(local_date: str) -> str:
    year = int(local_date[:4])
    month = int(local_date[5:7])
    return f"{year}-H{1 if month <= 6 else 2}"


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 9:
        print(
            "usage: vt31_r8_sparse_reference_forensics.py "
            "R5_NAS100 R5_SP500 R5_US30 R6_NAS100 R6_SP500 R6_US30 "
            "R8_NAS100 R8_SP500 R8_US30"
        )
        return 2

    r8._configure_parent()
    partitions = {
        "r5": dict(zip(MARKETS, map(Path, args[0:3]), strict=True)),
        "r6": dict(zip(MARKETS, map(Path, args[3:6]), strict=True)),
        "r8_fresh": dict(zip(MARKETS, map(Path, args[6:9]), strict=True)),
    }
    raw: dict[str, dict[str, object]] = {}
    by_policy_all: dict[str, list[dict[str, object]]] = defaultdict(list)
    by_policy_partition: dict[str, dict[str, list[dict[str, object]]]] = defaultdict(
        lambda: defaultdict(list)
    )

    for partition, paths in partitions.items():
        raw[partition] = {}
        for market, path in paths.items():
            result = _run_market(path, market)
            raw[partition][market] = {
                key: value for key, value in result.items() if key != "trades"
            }
            for policy, rows in cast(
                dict[str, list[dict[str, object]]], result["trades"]
            ).items():
                for row in rows:
                    row["partition"] = partition
                by_policy_all[policy].extend(rows)
                by_policy_partition[policy][partition].extend(rows)

    policies: dict[str, object] = {}
    for policy in POLICIES:
        rows = by_policy_all[policy]
        partition_summary = {
            partition: _summarize(list(by_policy_partition[policy][partition]))
            for partition in partitions
        }
        half_years: dict[str, list[dict[str, object]]] = defaultdict(list)
        for row in rows:
            half_years[_half_year(cast(str, row["local_date"]))].append(row)
        half_year_summary = {
            key: _metrics(value, friction=FRICTION)
            for key, value in sorted(half_years.items())
        }
        policies[policy] = {
            "max_consecutive_missing_reference_minutes": POLICIES[policy],
            "all_consumed": _summarize(list(rows)),
            "partition": partition_summary,
            "half_year": half_year_summary,
            "positive_half_years": sum(
                Decimal(cast(str, value["mean_r"])) > 0
                for value in half_year_summary.values()
            ),
            "half_year_count": len(half_year_summary),
        }

    strict_fresh = cast(
        dict[str, object],
        cast(dict[str, object], policies["strict60"])["partition"],
    )["r8_fresh"]
    strict_stress = cast(dict[str, object], strict_fresh)["stress"]
    strict_markets = cast(dict[str, object], strict_fresh)["markets"]
    strict_parity = (
        cast(dict[str, object], strict_stress)["sample"] == 68
        and cast(dict[str, object], cast(dict[str, object], strict_markets)["NAS100"])[
            "sample"
        ]
        == 31
        and cast(dict[str, object], cast(dict[str, object], strict_markets)["SP500"])[
            "sample"
        ]
        == 5
        and cast(dict[str, object], cast(dict[str, object], strict_markets)["US30"])[
            "sample"
        ]
        == 32
    )

    report = {
        "schema": "qore.trader_lab.vt31_r8_sparse_reference_forensics.v1",
        "research_only": True,
        "opens_new_evidence": False,
        "candidate_status": "R8_REJECTED_FRESH_CONSUMED",
        "ctrader_trendbar_semantics": CTRADER_TRENDBAR_SEMANTICS,
        "hypothesis": (
            "exactly-60 M1 reference bars confounds no-tick minutes with missing "
            "evidence and disproportionately censors old SP500 history"
        ),
        "invariants": {
            "setup_session_10_11_requires_60_m1": True,
            "r8_signal_cutoff": "10:20 NY",
            "r8_risk_reference_max": "0.175",
            "r8_confirmation_body_min": "0.50",
            "r8_raid_body_min": "0.35",
            "r8_raid_to_extreme_max_bars": 4,
            "target": "fixed-2R",
            "management": "M1-protected-swing-trail",
            "friction_r": "0.05",
        },
        "policies": policies,
        "raw": raw,
        "strict_r8_fresh_parity": strict_parity,
        "governance": {
            "r8_retuned": False,
            "candidate_approved": False,
            "new_candidate_defined": False,
            "live_authorized": False,
            "production_authorized": False,
        },
    }
    Path("vt31-r8-sparse-reference-forensics.json").write_text(
        json.dumps(report, sort_keys=True, separators=(",", ":")) + "\n"
    )

    compact: dict[str, object] = {}
    for policy, value_obj in policies.items():
        value = cast(dict[str, object], value_obj)
        all_consumed = cast(dict[str, object], value["all_consumed"])
        fresh = cast(dict[str, object], cast(dict[str, object], value["partition"])["r8_fresh"])
        compact[policy] = {
            "all": all_consumed["stress"],
            "all_markets": all_consumed["markets"],
            "all_sides": all_consumed["sides"],
            "all_passes_deterministic": all_consumed["passes_deterministic_gates"],
            "positive_half_years": value["positive_half_years"],
            "half_year_count": value["half_year_count"],
            "fresh": fresh["stress"],
            "fresh_markets": fresh["markets"],
            "fresh_sides": fresh["sides"],
            "fresh_gates": fresh["gates"],
        }
    Path("vt31-r8-sparse-reference-summary.json").write_text(
        json.dumps(compact, sort_keys=True, indent=2) + "\n"
    )
    print(json.dumps({"strict_parity": strict_parity, "policies": compact}, sort_keys=True))
    return 0 if strict_parity else 3


if __name__ == "__main__":
    raise SystemExit(main())
