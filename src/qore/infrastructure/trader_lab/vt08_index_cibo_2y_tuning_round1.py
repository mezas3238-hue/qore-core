"""VT08 Index CIBO 2Y tuning lab — Round 1.

This lab consumes the previously unused pre-VT08 CIBO M5 interval
2016-09-18 .. 2018-09-15 as an explicit TUNING window. Because the owner
authorized iterative adjustment, this window is *not* called a fresh
certification holdout after the first run.

Round 1 preserves:
- frozen V7 setup identity;
- V7 source/POI/CISD/Protected-Swing mechanics;
- structural stop;
- next-H4 lifecycle;
- same-bar stop-first execution semantics.

It explores only pre-decision operating choices:
- active index specialist set;
- NY anchor subset;
- side subset;
- fixed target depth per active market.

No trailing, stop widening, post-entry hindsight filter, or future CIBO state is
used. The search reports a Pareto-style PF/DD frontier and temporal stability.
"""

from __future__ import annotations

import argparse
import itertools
import json
from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from typing import Any, cast
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab import vt08_index_v6_ttrades_source_faithful as v6
from qore.infrastructure.trader_lab import vt08_index_v7_ttrades_source_corrected as v7
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import Vt08IndexC2R1Bar

SCHEMA = "qore.trader_lab.vt08_index_cibo_2y_tuning_round1.v1"
IDENTITY = "VT08_INDEX_CIBO_2Y_TUNING_ROUND1"
WINDOW_ID = "VT08_INDEX_TUNING_2Y_2016_2018"
START_DATE = date(2016, 9, 18)
END_DATE_EXCLUSIVE = date(2018, 9, 15)
SOURCE_CIBO_RUN_ID = 35166210458
SOURCE_CIBO_GIT_SHA = "ab782b8e9f890f86a2b6500070f0556b4b685e3d"
SOURCE_IDENTITY = "CIBO_MARKET_ATLAS_10Y_CONSUMPTION_V1"
RAW_SCHEMA = "qore.cibo_market_atlas.raw_m5.v1"
PRICE_SCALE = Decimal("100000")
PRIMARY_STRESS = Decimal("0.05")
SECONDARY_STRESS = Decimal("0.10")
TARGET_GRID = tuple(
    Decimal(value)
    for value in ("1.0", "1.25", "1.5", "1.75", "2.0", "2.5")
)
ANCHORS = (2, 6, 10)
SIDES = ("long", "short")
SYMBOLS = ("NAS100", "SP500", "US30")
_NY = ZoneInfo("America/New_York")


@dataclass(frozen=True, slots=True)
class TradeSurfaceRow:
    symbol: str
    signal_at: datetime
    side: str
    anchor: int
    model_kind: str
    poi_kind: str
    outcomes: dict[str, Decimal]

    def payload(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "signal_at": self.signal_at.astimezone(UTC).isoformat(),
            "side": self.side,
            "anchor": self.anchor,
            "model_kind": self.model_kind,
            "poi_kind": self.poi_kind,
            "outcomes": {
                key: format(value, "f") for key, value in sorted(self.outcomes.items())
            },
        }


def _single(root: Path, name: str) -> Path:
    paths = list(root.rglob(name))
    if len(paths) != 1:
        raise ValueError(f"expected exactly one {name} under {root}, got {len(paths)}")
    return paths[0]


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object in {path}")
    return cast(dict[str, Any], payload)


def _parse_time(value: object) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("raw CIBO timestamp must be timezone-aware")
    return parsed.astimezone(UTC)


def _int(value: object) -> int:
    return int(str(value))


def _price(value: object) -> Decimal:
    return Decimal(_int(value)) / PRICE_SCALE


def _load_cibo_m15(
    root: Path,
    *,
    symbol: str,
) -> tuple[tuple[Vt08IndexC2R1Bar, ...], dict[str, Any]]:
    manifest = _read_json(_single(root, "symbol-consumption-manifest.json"))
    if manifest.get("identity") != SOURCE_IDENTITY:
        raise ValueError(f"CIBO source identity drift for {symbol}")
    if manifest.get("canonical_symbol") != symbol:
        raise ValueError(f"CIBO canonical symbol drift for {symbol}")
    if not bool(manifest.get("read_only")):
        raise ValueError(f"CIBO source must be read-only for {symbol}")
    if bool(manifest.get("live_authorized")):
        raise ValueError(f"CIBO source unexpectedly LIVE-authorized for {symbol}")
    if bool(manifest.get("real_capital_authorized")):
        raise ValueError(f"CIBO source unexpectedly real-capital-authorized for {symbol}")
    if str(manifest.get("target_start")) != "2016-09-17T00:00:00+00:00":
        raise ValueError(f"CIBO target start drift for {symbol}")
    if str(manifest.get("target_end_exclusive")) != "2026-09-17T00:00:00+00:00":
        raise ValueError(f"CIBO target end drift for {symbol}")

    start_dt = datetime.combine(START_DATE, datetime.min.time(), tzinfo=UTC)
    end_dt = datetime.combine(END_DATE_EXCLUSIVE, datetime.min.time(), tzinfo=UTC)
    buckets: dict[datetime, list[tuple[datetime, dict[str, Any]]]] = defaultdict(list)
    retained_rows = 0
    for year in (2016, 2017, 2018):
        path = root / "RAW_M5_LEDGER" / f"{year}.jsonl"
        if not path.is_file():
            raise ValueError(f"missing raw CIBO M5 partition {year} for {symbol}")
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                decoded = json.loads(line)
                if not isinstance(decoded, dict):
                    raise ValueError("raw CIBO M5 row must be an object")
                row = cast(dict[str, Any], decoded)
                if row.get("schema") != RAW_SCHEMA:
                    raise ValueError(f"raw CIBO schema drift for {symbol}")
                if row.get("identity") != SOURCE_IDENTITY:
                    raise ValueError(f"raw CIBO identity drift for {symbol}")
                if row.get("canonical_symbol") != symbol:
                    raise ValueError(f"raw CIBO symbol drift for {symbol}")
                opened = _parse_time(row.get("opened_at"))
                if opened < start_dt or opened >= end_dt:
                    continue
                if opened.minute % 5 != 0 or opened.second != 0:
                    raise ValueError(f"unaligned raw M5 timestamp for {symbol}")
                retained_rows += 1
                bucket = opened.replace(
                    minute=(opened.minute // 15) * 15,
                    second=0,
                    microsecond=0,
                )
                buckets[bucket].append((opened, row))

    bars: list[Vt08IndexC2R1Bar] = []
    complete = 0
    incomplete = 0
    for bucket in sorted(buckets):
        entries = sorted(buckets[bucket], key=lambda item: item[0])
        expected_times = (
            bucket,
            bucket + timedelta(minutes=5),
            bucket + timedelta(minutes=10),
        )
        observed_times = tuple(item[0] for item in entries)
        if observed_times != expected_times:
            incomplete += 1
            continue
        complete += 1
        rows = [item[1] for item in entries]
        opens = [_price(row["open_relative"]) for row in rows]
        highs = [_price(row["high_relative"]) for row in rows]
        lows = [_price(row["low_relative"]) for row in rows]
        closes = [_price(row["close_relative"]) for row in rows]
        bars.append(
            Vt08IndexC2R1Bar(
                opened_at=bucket,
                closed_at=bucket + timedelta(minutes=15),
                open=opens[0],
                high=max(highs),
                low=min(lows),
                close=closes[-1],
            )
        )
    if not bars:
        raise ValueError(f"no complete reconstructed M15 bars for {symbol}")
    return tuple(bars), {
        "source_run_id": SOURCE_CIBO_RUN_ID,
        "source_git_sha": SOURCE_CIBO_GIT_SHA,
        "source_identity": SOURCE_IDENTITY,
        "raw_m5_rows_in_window": retained_rows,
        "m15_complete_buckets": complete,
        "m15_incomplete_buckets_dropped": incomplete,
        "m15_complete_rate": (
            format(
                Decimal(complete) / Decimal(complete + incomplete),
                "f",
            )
            if complete + incomplete
            else "0"
        ),
        "first_m15": bars[0].opened_at.isoformat(),
        "last_m15": bars[-1].opened_at.isoformat(),
    }


def _retarget(
    signal: v6.CandidateSignal,
    target_r: Decimal,
) -> v6.CandidateSignal:
    risk = abs(signal.entry - signal.stop)
    target = (
        signal.entry + target_r * risk
        if signal.side is DemoTradingSetupSide.LONG
        else signal.entry - target_r * risk
    )
    return v6.CandidateSignal(
        symbol=signal.symbol,
        side=signal.side,
        model_kind=signal.model_kind,
        h4_opened_at=signal.h4_opened_at,
        signal_at=signal.signal_at,
        entry=signal.entry,
        stop=signal.stop,
        target=target,
        poi=signal.poi,
        cisd_level=signal.cisd_level,
        cisd_confirmed_at=signal.cisd_confirmed_at,
        protected_swing_extreme=signal.protected_swing_extreme,
    )


def _surface_rows(
    *,
    symbol: str,
    bars: Sequence[Vt08IndexC2R1Bar],
) -> tuple[tuple[TradeSurfaceRow, ...], dict[str, Any]]:
    report = v7._market_report(
        symbol=symbol,
        bars=bars,
        start_date=START_DATE,
        end_date_exclusive=END_DATE_EXCLUSIVE,
    )
    trades = cast(tuple[v6.ModeledV6Trade, ...], report["trades"])
    indexed = {bar.opened_at.astimezone(UTC): bar for bar in bars}
    rows: list[TradeSurfaceRow] = []
    missing_outcomes = 0
    for trade in trades:
        outcomes: dict[str, Decimal] = {}
        for target_r in TARGET_GRID:
            modeled = v6._model_trade(
                _retarget(trade.signal, target_r),
                indexed=indexed,
                end_date_exclusive=END_DATE_EXCLUSIVE,
            )
            if modeled is None:
                missing_outcomes += 1
                continue
            outcomes[format(target_r, "f")] = modeled.r_multiple
        if not outcomes:
            continue
        signal = trade.signal
        rows.append(
            TradeSurfaceRow(
                symbol=symbol,
                signal_at=signal.signal_at.astimezone(UTC),
                side=signal.side.value,
                anchor=signal.h4_opened_at.astimezone(_NY).hour,
                model_kind=signal.model_kind.value,
                poi_kind=signal.poi.kind.value,
                outcomes=outcomes,
            )
        )
    return tuple(rows), {
        "baseline_v7_signal_count": len(cast(list[Any], report["signals"])),
        "baseline_v7_trade_count": len(trades),
        "surface_trade_count": len(rows),
        "missing_target_outcomes": missing_outcomes,
        "session_reconstruction": report["session_reconstruction"],
    }


def _metrics(values: Sequence[Decimal]) -> dict[str, Any]:
    n = len(values)
    if n == 0:
        return {
            "sample": 0,
            "wins": 0,
            "losses": 0,
            "flats": 0,
            "total_r": "0",
            "mean_r": "0",
            "profit_factor": "0",
            "max_drawdown_r": "0",
            "max_losing_streak": 0,
        }
    wins = sum(value > 0 for value in values)
    losses = sum(value < 0 for value in values)
    flats = n - wins - losses
    gross_profit = sum((value for value in values if value > 0), Decimal())
    gross_loss = -sum((value for value in values if value < 0), Decimal())
    total = sum(values, Decimal())
    equity = Decimal()
    peak = Decimal()
    max_dd = Decimal()
    losing_streak = 0
    max_losing_streak = 0
    for value in values:
        equity += value
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
        if value < 0:
            losing_streak += 1
            max_losing_streak = max(max_losing_streak, losing_streak)
        else:
            losing_streak = 0
    pf = gross_profit / gross_loss if gross_loss > 0 else Decimal("999")
    return {
        "sample": n,
        "wins": wins,
        "losses": losses,
        "flats": flats,
        "win_rate": format(Decimal(wins) / Decimal(n), "f"),
        "total_r": format(total, "f"),
        "mean_r": format(total / Decimal(n), "f"),
        "profit_factor": format(pf, "f"),
        "max_drawdown_r": format(max_dd, "f"),
        "max_losing_streak": max_losing_streak,
    }


def _quarter_key(timestamp: datetime) -> str:
    local = timestamp.astimezone(_NY)
    return f"{local.year}-Q{((local.month - 1) // 3) + 1}"


def _candidate_values(
    rows: Sequence[TradeSurfaceRow],
    *,
    targets: dict[str, str | None],
    anchors: tuple[int, ...],
    sides: tuple[str, ...],
    stress: Decimal,
) -> tuple[list[Decimal], list[TradeSurfaceRow]]:
    selected: list[tuple[TradeSurfaceRow, Decimal]] = []
    for row in rows:
        target_key = targets.get(row.symbol)
        if target_key is None or row.anchor not in anchors or row.side not in sides:
            continue
        outcome = row.outcomes.get(target_key)
        if outcome is None:
            continue
        selected.append((row, outcome - stress))
    selected.sort(key=lambda item: (item[0].signal_at, item[0].symbol))
    return [item[1] for item in selected], [item[0] for item in selected]


def _candidate_report(
    rows: Sequence[TradeSurfaceRow],
    *,
    targets: dict[str, str | None],
    anchors: tuple[int, ...],
    sides: tuple[str, ...],
) -> dict[str, Any]:
    primary, selected_rows = _candidate_values(
        rows,
        targets=targets,
        anchors=anchors,
        sides=sides,
        stress=PRIMARY_STRESS,
    )
    secondary, _ = _candidate_values(
        rows,
        targets=targets,
        anchors=anchors,
        sides=sides,
        stress=SECONDARY_STRESS,
    )
    n = len(primary)
    split = n // 2
    half_metrics = [_metrics(primary[:split]), _metrics(primary[split:])]
    by_quarter: dict[str, list[Decimal]] = defaultdict(list)
    by_market: dict[str, list[Decimal]] = defaultdict(list)
    by_anchor: dict[str, list[Decimal]] = defaultdict(list)
    by_side: dict[str, list[Decimal]] = defaultdict(list)
    for row, value in zip(selected_rows, primary, strict=True):
        by_quarter[_quarter_key(row.signal_at)].append(value)
        by_market[row.symbol].append(value)
        by_anchor[str(row.anchor)].append(value)
        by_side[row.side].append(value)

    quarter_metrics = {
        key: _metrics(values) for key, values in sorted(by_quarter.items())
    }
    positive_quarters = sum(
        Decimal(str(metrics["total_r"])) > 0 for metrics in quarter_metrics.values()
    )
    positive_halves = sum(
        Decimal(str(metrics["total_r"])) > 0 for metrics in half_metrics
    )
    metrics_primary = _metrics(primary)
    metrics_secondary = _metrics(secondary)
    config_material = {
        "targets": targets,
        "anchors": anchors,
        "sides": sides,
    }
    candidate_id = sha256(
        json.dumps(
            config_material,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()[:16]
    return {
        "candidate_id": f"T2Y-{candidate_id}",
        "config": {
            "targets": targets,
            "anchors": list(anchors),
            "sides": list(sides),
        },
        "primary_stress": metrics_primary,
        "secondary_stress": metrics_secondary,
        "positive_halves": positive_halves,
        "positive_quarters": positive_quarters,
        "quarter_count": len(quarter_metrics),
        "halves_primary": half_metrics,
        "quarters_primary": quarter_metrics,
        "by_market_primary": {
            key: _metrics(values) for key, values in sorted(by_market.items())
        },
        "by_anchor_primary": {
            key: _metrics(values) for key, values in sorted(by_anchor.items())
        },
        "by_side_primary": {
            key: _metrics(values) for key, values in sorted(by_side.items())
        },
    }


def _anchor_sets() -> tuple[tuple[int, ...], ...]:
    return tuple(
        subset
        for size in range(1, len(ANCHORS) + 1)
        for subset in itertools.combinations(ANCHORS, size)
    )


def _side_sets() -> tuple[tuple[str, ...], ...]:
    return (("long",), ("short",), ("long", "short"))


def _target_maps() -> Iterable[dict[str, str | None]]:
    choices: tuple[str | None, ...] = (None,) + tuple(
        format(target, "f") for target in TARGET_GRID
    )
    for values in itertools.product(choices, repeat=len(SYMBOLS)):
        if all(value is None for value in values):
            continue
        yield dict(zip(SYMBOLS, values, strict=True))


def _sort_key(candidate: dict[str, Any]) -> tuple[int, int, Decimal, Decimal, Decimal]:
    primary = cast(dict[str, Any], candidate["primary_stress"])
    sample = int(primary["sample"])
    pf = Decimal(str(primary["profit_factor"]))
    dd = Decimal(str(primary["max_drawdown_r"]))
    mean = Decimal(str(primary["mean_r"]))
    stable = int(
        int(candidate["positive_halves"]) == 2
        and int(candidate["positive_quarters"]) >= 6
    )
    high_activity = int(sample >= 400)
    return (stable, high_activity, pf, -dd, mean)


def build_report(
    *,
    nas100_root: Path,
    sp500_root: Path,
    us30_root: Path,
) -> dict[str, Any]:
    roots = {
        "NAS100": nas100_root,
        "SP500": sp500_root,
        "US30": us30_root,
    }
    provenance: dict[str, Any] = {}
    market_diagnostics: dict[str, Any] = {}
    all_rows: list[TradeSurfaceRow] = []
    for symbol in SYMBOLS:
        bars, source = _load_cibo_m15(roots[symbol], symbol=symbol)
        rows, diagnostics = _surface_rows(symbol=symbol, bars=bars)
        provenance[symbol] = source
        market_diagnostics[symbol] = diagnostics
        all_rows.extend(rows)

    all_rows.sort(key=lambda row: (row.signal_at, row.symbol))
    candidates: list[dict[str, Any]] = []
    for targets in _target_maps():
        for anchors in _anchor_sets():
            for sides in _side_sets():
                report = _candidate_report(
                    all_rows,
                    targets=targets,
                    anchors=anchors,
                    sides=sides,
                )
                sample = int(cast(dict[str, Any], report["primary_stress"])["sample"])
                if sample < 100:
                    continue
                candidates.append(report)
    candidates.sort(key=_sort_key, reverse=True)

    robust = [
        candidate
        for candidate in candidates
        if (
            int(cast(dict[str, Any], candidate["primary_stress"])["sample"]) >= 400
            and Decimal(
                str(cast(dict[str, Any], candidate["primary_stress"])["profit_factor"])
            )
            >= Decimal("1.15")
            and Decimal(
                str(cast(dict[str, Any], candidate["primary_stress"])["max_drawdown_r"])
            )
            <= Decimal("12")
            and int(candidate["positive_halves"]) == 2
            and int(candidate["positive_quarters"]) >= 6
        )
    ]
    best = robust[0] if robust else (candidates[0] if candidates else None)
    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "window": {
            "window_id": WINDOW_ID,
            "start_date": START_DATE.isoformat(),
            "end_date_exclusive": END_DATE_EXCLUSIVE.isoformat(),
            "status": "CONSUMED_TUNING_ON_FIRST_OBSERVATION",
            "fresh_certification_holdout": False,
            "known_overlap_with_prior_vt08_consumed_windows": False,
        },
        "strategy": {
            "base_candidate_id": v7.CANDIDATE_ID,
            "base_rule_fingerprint": v7.RULE_FINGERPRINT,
            "v7_setup_identity_changed": False,
            "stop_changed": False,
            "lifecycle_changed": False,
        },
        "search_contract": {
            "target_grid_r": [format(value, "f") for value in TARGET_GRID],
            "anchor_universe": list(ANCHORS),
            "side_universe": list(SIDES),
            "minimum_reported_sample": 100,
            "high_activity_goal_sample_2y": 400,
            "research_goal_profit_factor_primary": "1.15",
            "research_goal_max_drawdown_primary_r": "12",
            "research_goal_positive_halves": 2,
            "research_goal_positive_quarters": 6,
            "optimization_label": (
                "PF_DD_ACTIVITY_STABILITY_TUNING_NOT_CERTIFICATION"
            ),
        },
        "provenance": provenance,
        "market_diagnostics": market_diagnostics,
        "surface_trade_count": len(all_rows),
        "candidate_count": len(candidates),
        "robust_goal_candidate_count": len(robust),
        "best_candidate": best,
        "top_25": candidates[:25],
        "governance": {
            "research_only": True,
            "tuning_window_consumed": True,
            "fresh_holdout_claim": False,
            "rule_promotion_automatic": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--nas100-root", type=Path, required=True)
    parser.add_argument("--sp500-root", type=Path, required=True)
    parser.add_argument("--us30-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = build_report(
        nas100_root=args.nas100_root,
        sp500_root=args.sp500_root,
        us30_root=args.us30_root,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    best = cast(dict[str, Any] | None, report["best_candidate"])
    print(
        json.dumps(
            {
                "identity": IDENTITY,
                "surface_trade_count": report["surface_trade_count"],
                "candidate_count": report["candidate_count"],
                "robust_goal_candidate_count": report["robust_goal_candidate_count"],
                "best_candidate_id": best["candidate_id"] if best else None,
                "best_primary": best["primary_stress"] if best else None,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
