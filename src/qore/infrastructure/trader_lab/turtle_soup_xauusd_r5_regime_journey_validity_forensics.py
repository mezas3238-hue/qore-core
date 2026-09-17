"""Regime-conditioned journey-validity forensics for Turtle Soup XAUUSD.

Research only. Reproduces frozen R3 on the already-consumed CIBO 10Y corpus and
asks why the same raid/CISD topology changed behavior across regimes. All
explanatory variables are built only from completed market structure before
entry. No discovered state is promoted to a trading rule in this module.
"""
from __future__ import annotations

import bisect
import json
import sys
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import turtle_soup_xauusd_r3_causal_regime_forensics as causal
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r3_cibo_journey as r3

IDENTITY = "TURTLE_SOUP_XAUUSD_R5_REGIME_JOURNEY_VALIDITY_FORENSICS_V1"
EVIDENCE_STATUS = "CONSUMED_CIBO_10Y_REGIME_VALIDITY_RESEARCH_NOT_FRESH_HOLDOUT"
EARLY_YEARS = frozenset({2016, 2017, 2018, 2019, 2020})
TRANSITION_YEARS = frozenset({2021, 2022, 2023})
RECENT_YEARS = frozenset({2024, 2025, 2026})

STABLE_RAID = "q2:<=0.10"  # >5% and <=10% of prior mean source range.
FAILING_RAID = "q4:<=0.50"  # >25% and <=50%.
LATE_CISD = "q4:>0.75"


@dataclass(frozen=True, slots=True)
class AggBar:
    opened_at: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal


@dataclass(frozen=True, slots=True)
class RegimeSeries:
    bars: tuple[AggBar, ...]
    opens: tuple[datetime, ...]
    timeframe: str


def _d(value: Any) -> Decimal:
    return Decimal(str(value))


def _stat(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    values = [_d(row["primary_net_r"]) for row in rows]
    gp = sum((v for v in values if v > 0), Decimal(0))
    gl = -sum((v for v in values if v < 0), Decimal(0))
    target = sum(1 for row in rows if "TARGET" in str(row["exit_reason"]))
    stop = sum(1 for row in rows if "STOP" in str(row["exit_reason"]))
    total = sum(values, Decimal(0))
    return {
        "trades": len(rows),
        "total_primary_r": str(total),
        "mean_primary_r": str(total / len(rows)) if rows else None,
        "profit_factor": str(gp / gl) if gl > 0 else None,
        "target_rate": str(Decimal(target) / len(rows)) if rows else None,
        "stop_rate": str(Decimal(stop) / len(rows)) if rows else None,
    }


def _period(rows: Sequence[dict[str, Any]], years: frozenset[int]) -> list[dict[str, Any]]:
    return [row for row in rows if int(row["year"]) in years]


def _bucket_ratio(value: Decimal | None) -> str:
    if value is None:
        return "missing"
    if value <= Decimal("0.75"):
        return "compressed<=0.75"
    if value <= Decimal("1.25"):
        return "normal_0.75_1.25"
    return "expanded>1.25"


def _bucket_efficiency(value: Decimal | None) -> str:
    if value is None:
        return "missing"
    if value < Decimal("0.25"):
        return "choppy<0.25"
    if value < Decimal("0.50"):
        return "directional_0.25_0.50"
    return "persistent>=0.50"


def _bucket_location(value: Decimal | None) -> str:
    if value is None:
        return "missing"
    if value <= Decimal("0.20"):
        return "low_edge<=0.20"
    if value >= Decimal("0.80"):
        return "high_edge>=0.80"
    return "middle"


def _bucket_reversal_edge(value: Decimal | None) -> str:
    if value is None:
        return "missing"
    if value <= Decimal("0.20"):
        return "near_reversal_edge<=0.20"
    if value <= Decimal("0.50"):
        return "mid_edge_0.20_0.50"
    return "away_from_reversal_edge>0.50"


def _aggregate(raw_bars: Sequence[Any], timeframe: str) -> RegimeSeries:
    grouped: dict[datetime, list[Any]] = defaultdict(list)
    for bar in raw_bars:
        at = bar.opened_at
        if timeframe == "D1":
            key = at.replace(hour=0, minute=0, second=0, microsecond=0)
        elif timeframe == "H4":
            key = at.replace(hour=(at.hour // 4) * 4, minute=0, second=0, microsecond=0)
        else:
            raise ValueError(f"unsupported regime timeframe: {timeframe}")
        grouped[key].append(bar)
    bars: list[AggBar] = []
    for key in sorted(grouped):
        items = grouped[key]
        bars.append(AggBar(
            opened_at=key,
            open=_d(items[0].open),
            high=max(_d(x.high) for x in items),
            low=min(_d(x.low) for x in items),
            close=_d(items[-1].close),
        ))
    return RegimeSeries(tuple(bars), tuple(x.opened_at for x in bars), timeframe)


def _cut_key(at: datetime, timeframe: str) -> datetime:
    if timeframe == "D1":
        return at.replace(hour=0, minute=0, second=0, microsecond=0)
    if timeframe == "H4":
        return at.replace(hour=(at.hour // 4) * 4, minute=0, second=0, microsecond=0)
    raise ValueError(timeframe)


def _history(series: RegimeSeries, at: datetime, count: int) -> tuple[AggBar, ...]:
    pos = bisect.bisect_left(series.opens, _cut_key(at, series.timeframe))
    return series.bars[max(0, pos - count):pos]


def _mean_range(items: Sequence[AggBar]) -> Decimal | None:
    if not items:
        return None
    return sum((x.high - x.low for x in items), Decimal(0)) / len(items)


def _range_ratio(short: Sequence[AggBar], long: Sequence[AggBar]) -> Decimal | None:
    a, b = _mean_range(short), _mean_range(long)
    if a is None or b is None or b <= 0:
        return None
    return a / b


def _efficiency(items: Sequence[AggBar]) -> Decimal | None:
    if len(items) < 2:
        return None
    path = sum((abs(items[i].close - items[i - 1].close) for i in range(1, len(items))), Decimal(0))
    if path <= 0:
        return Decimal(0)
    return abs(items[-1].close - items[0].close) / path


def _location(items: Sequence[AggBar]) -> Decimal | None:
    if not items:
        return None
    low = min(x.low for x in items)
    high = max(x.high for x in items)
    span = high - low
    if span <= 0:
        return Decimal("0.5")
    return (items[-1].close - low) / span


def _reversal_edge(location: Decimal | None, side: str) -> Decimal | None:
    if location is None:
        return None
    return location if side == "long" else Decimal(1) - location


def _trend_state(items: Sequence[AggBar], side: str) -> str:
    eff = _efficiency(items)
    if eff is None:
        return "missing"
    if eff < Decimal("0.25"):
        return "choppy"
    net = items[-1].close - items[0].close
    if net == 0:
        return "flat_directional"
    with_trade = net > 0 if side == "long" else net < 0
    strength = "persistent" if eff >= Decimal("0.50") else "directional"
    return f"{strength}_{'with_trade' if with_trade else 'against_trade'}"


def _streak3(items: Sequence[AggBar], side: str) -> str:
    if len(items) < 4:
        return "missing"
    moves = [items[i].close - items[i - 1].close for i in range(len(items) - 3, len(items))]
    if all(x > 0 for x in moves):
        direction = "up"
    elif all(x < 0 for x in moves):
        direction = "down"
    else:
        return "mixed"
    with_trade = direction == "up" if side == "long" else direction == "down"
    return "three_with_trade" if with_trade else "three_against_trade"


def _regime_features(row: dict[str, Any], d1: RegimeSeries, h4: RegimeSeries) -> dict[str, str]:
    at = datetime.fromisoformat(str(row["entry_at"]))
    side = str(row["side"])
    d20 = _history(d1, at, 20)
    d5 = d20[-5:]
    d1last = d20[-1:] if d20 else ()
    h20 = _history(h4, at, 20)
    h6 = h20[-6:]
    h3 = h20[-3:]

    d_loc = _location(d20)
    h_loc = _location(h20)
    features = {
        "d1_prior_range_vs20": _bucket_ratio(_range_ratio(d1last, d20)),
        "d1_range_5v20": _bucket_ratio(_range_ratio(d5, d20)),
        "d1_efficiency_5": _bucket_efficiency(_efficiency(d5)),
        "d1_efficiency_20": _bucket_efficiency(_efficiency(d20)),
        "d1_location_20": _bucket_location(d_loc),
        "d1_reversal_edge_20": _bucket_reversal_edge(_reversal_edge(d_loc, side)),
        "d1_trend_state_5": _trend_state(d5, side),
        "d1_trend_state_20": _trend_state(d20, side),
        "d1_streak3": _streak3(d20, side),
        "h4_range_3v20": _bucket_ratio(_range_ratio(h3, h20)),
        "h4_efficiency_6": _bucket_efficiency(_efficiency(h6)),
        "h4_efficiency_20": _bucket_efficiency(_efficiency(h20)),
        "h4_location_20": _bucket_location(h_loc),
        "h4_reversal_edge_20": _bucket_reversal_edge(_reversal_edge(h_loc, side)),
        "h4_trend_state_6": _trend_state(h6, side),
        "h4_trend_state_20": _trend_state(h20, side),
        "h4_streak3": _streak3(h20, side),
    }
    return features


def _family(row: dict[str, Any]) -> str:
    raid = str(row["raid_depth_range_bucket"])
    cisd = str(row["cisd_progress_bucket"])
    if raid == STABLE_RAID:
        return "STABLE_RAID_5_10"
    if raid == FAILING_RAID and cisd == LATE_CISD:
        return "DEEP_RAID_25_50_LATE_CISD"
    return "OTHER"


def _feature_matrix(rows: Sequence[dict[str, Any]], feature: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    values = sorted({str(row[feature]) for row in rows})
    for value in values:
        selected = [row for row in rows if str(row[feature]) == value]
        out[value] = {
            "all": _stat(selected),
            "early_2016_2020": _stat(_period(selected, EARLY_YEARS)),
            "transition_2021_2023": _stat(_period(selected, TRANSITION_YEARS)),
            "recent_2024_2026": _stat(_period(selected, RECENT_YEARS)),
            "recent_by_year": {
                str(year): _stat([row for row in selected if int(row["year"]) == year])
                for year in (2024, 2025, 2026)
            },
        }
    return out


def _persistent_recent_failures(family_rows: Sequence[dict[str, Any]], features: Sequence[str]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for feature in features:
        for value in sorted({str(row[feature]) for row in family_rows}):
            yearly = []
            valid = True
            for year in (2024, 2025, 2026):
                part = [row for row in family_rows if int(row["year"]) == year and str(row[feature]) == value]
                stat = _stat(part)
                yearly.append({"year": year, **stat})
                mean = stat["mean_primary_r"]
                if len(part) < 10 or mean is None or _d(mean) >= 0:
                    valid = False
            if valid:
                recent = [row for row in family_rows if int(row["year"]) in RECENT_YEARS and str(row[feature]) == value]
                found.append({"feature": feature, "value": value, "recent": _stat(recent), "yearly": yearly})
    found.sort(key=lambda item: _d(item["recent"]["mean_primary_r"] or 0))
    return found


def run(source_root: Path, target_root: Path, output: Path) -> dict[str, Any]:
    evidence, selected, reproduction = causal._reproduce_selected(source_root, target_root)
    opens = tuple(bar.opened_at for bar in evidence.bars)
    rows = [causal._record(setup, trade, evidence.bars, opens) for setup, trade in selected]
    if len(rows) != 5885:
        raise ValueError(f"R3 reproduction drift: {len(rows)}")
    total = sum((_d(row["primary_net_r"]) for row in rows), Decimal(0))
    if abs(total - Decimal("707.7490491424")) > Decimal("0.0001"):
        raise ValueError(f"R3 R-total reproduction drift: {total}")

    d1 = _aggregate(evidence.bars, "D1")
    h4 = _aggregate(evidence.bars, "H4")
    enriched: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item.update(_regime_features(item, d1, h4))
        item["journey_family"] = _family(item)
        enriched.append(item)

    regime_features = (
        "d1_prior_range_vs20", "d1_range_5v20", "d1_efficiency_5", "d1_efficiency_20",
        "d1_location_20", "d1_reversal_edge_20", "d1_trend_state_5", "d1_trend_state_20",
        "d1_streak3", "h4_range_3v20", "h4_efficiency_6", "h4_efficiency_20",
        "h4_location_20", "h4_reversal_edge_20", "h4_trend_state_6", "h4_trend_state_20",
        "h4_streak3",
    )
    stable = [row for row in enriched if row["journey_family"] == "STABLE_RAID_5_10"]
    failing = [row for row in enriched if row["journey_family"] == "DEEP_RAID_25_50_LATE_CISD"]

    payload = {
        "schema": "qore.turtle_soup_xauusd_r5.regime_journey_validity_forensics.v1",
        "identity": IDENTITY,
        "evidence_status": EVIDENCE_STATUS,
        "reproduction": reproduction,
        "full_r3": _stat(enriched),
        "families": {
            "stable_raid_5_10": {
                "definition": {"raid_depth": STABLE_RAID},
                "all": _stat(stable),
                "early_2016_2020": _stat(_period(stable, EARLY_YEARS)),
                "transition_2021_2023": _stat(_period(stable, TRANSITION_YEARS)),
                "recent_2024_2026": _stat(_period(stable, RECENT_YEARS)),
                "feature_matrix": {feature: _feature_matrix(stable, feature) for feature in regime_features},
            },
            "deep_raid_25_50_late_cisd": {
                "definition": {"raid_depth": FAILING_RAID, "cisd_progress": LATE_CISD},
                "all": _stat(failing),
                "early_2016_2020": _stat(_period(failing, EARLY_YEARS)),
                "transition_2021_2023": _stat(_period(failing, TRANSITION_YEARS)),
                "recent_2024_2026": _stat(_period(failing, RECENT_YEARS)),
                "feature_matrix": {feature: _feature_matrix(failing, feature) for feature in regime_features},
                "persistent_recent_failure_states": _persistent_recent_failures(failing, regime_features),
            },
        },
        "regime_features": list(regime_features),
        "research_question": "WHICH_CAUSAL_PRE_ENTRY_REGIME_STATE_EXPLAINS_WHY_DEEP_RAID_LATE_CISD_CHANGED_FROM_VALID_TO_INVALID_JOURNEY",
        "governance": {
            "diagnostic_only": True,
            "year_or_date_allowed_as_rule": False,
            "post_entry_leakage_allowed": False,
            "rules_promoted": False,
            "fresh_holdout_consumed": False,
            "automatic_candidate_promotion": False,
            "demo_eligible": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "regime-journey-validity-forensics.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    (output / "enriched-regime-trades.json").write_text(json.dumps(enriched, indent=2, sort_keys=True) + "\n")
    return payload


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit("usage: module SOURCE_ROOT TARGET_ROOT OUTPUT_DIR")
    print(json.dumps(run(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])), sort_keys=True))


if __name__ == "__main__":
    main()
