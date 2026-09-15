from __future__ import annotations

import bisect
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from statistics import median
from typing import Any
from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York")
STOP_REASONS = {"stop", "gap-stop", "stop-first"}


def dt(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return parsed


def dec(value: str) -> Decimal:
    return Decimal(value)


def quantiles(values: list[Decimal]) -> dict[str, str] | None:
    if not values:
        return None
    ordered = sorted(values)

    def pick(p: Decimal) -> Decimal:
        if len(ordered) == 1:
            return ordered[0]
        position = p * Decimal(len(ordered) - 1)
        lower = int(position)
        upper = min(lower + 1, len(ordered) - 1)
        weight = position - Decimal(lower)
        return ordered[lower] * (Decimal(1) - weight) + ordered[upper] * weight

    return {
        "p10": str(pick(Decimal("0.10"))),
        "p25": str(pick(Decimal("0.25"))),
        "p50": str(pick(Decimal("0.50"))),
        "p75": str(pick(Decimal("0.75"))),
        "p90": str(pick(Decimal("0.90"))),
        "p95": str(pick(Decimal("0.95"))),
        "p99": str(pick(Decimal("0.99"))),
    }


def summarize(values: list[Decimal]) -> dict[str, Any]:
    total = sum(values, Decimal(0))
    gains = sum((value for value in values if value > 0), Decimal(0))
    losses = -sum((value for value in values if value < 0), Decimal(0))
    return {
        "count": len(values),
        "total": str(total),
        "mean": None if not values else str(total / len(values)),
        "median": None if not values else str(median(values)),
        "profit_factor": None if losses == 0 else str(gains / losses),
    }


def load_bars(source_root: Path) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    for path in sorted(source_root.rglob("market-evidence.json")):
        payload = json.loads(path.read_text())
        symbol = str(payload["symbol"]["symbol_name"])
        rows: list[dict[str, Any]] = []
        for raw in payload["periods"]["M5"]:
            rows.append(
                {
                    "opened_at": dt(raw["opened_at"]),
                    "closed_at": dt(raw["closed_at"]),
                    "open": dec(raw["open"]),
                    "high": dec(raw["high"]),
                    "low": dec(raw["low"]),
                    "close": dec(raw["close"]),
                }
            )
        result[symbol] = rows
    return result


def containing_index(
    opened: list[datetime],
    bars: list[dict[str, Any]],
    moment: datetime,
) -> int:
    index = bisect.bisect_right(opened, moment) - 1
    if index < 0:
        raise ValueError("event precedes evidence")
    bar = bars[index]
    if not bar["opened_at"] <= moment <= bar["closed_at"]:
        raise ValueError("event does not map to one M5 bar")
    return index


def session_end_index(bars: list[dict[str, Any]], start: int) -> int:
    day = bars[start]["opened_at"].astimezone(NY).date()
    cursor = start + 1
    while cursor < len(bars):
        if bars[cursor]["opened_at"].astimezone(NY).date() != day:
            break
        cursor += 1
    return cursor


def favorable_r(
    bars: list[dict[str, Any]],
    start: int,
    end: int,
    *,
    side: str,
    entry: Decimal,
    risk: Decimal,
) -> Decimal:
    if start >= end:
        return Decimal(0)
    if side == "long":
        best = max(bar["high"] for bar in bars[start:end])
        return max(Decimal(0), (best - entry) / risk)
    best = min(bar["low"] for bar in bars[start:end])
    return max(Decimal(0), (entry - best) / risk)


def final_close_r(
    bar: dict[str, Any],
    *,
    side: str,
    entry: Decimal,
    risk: Decimal,
) -> Decimal:
    if side == "long":
        return (bar["close"] - entry) / risk
    return (entry - bar["close"]) / risk


def group_trade_metric(
    trades: list[dict[str, Any]], field: str
) -> dict[str, dict[str, Any]]:
    groups: dict[str, list[Decimal]] = defaultdict(list)
    for trade in trades:
        groups[str(trade[field])].append(dec(trade["primary_net_r"]))
    return {key: summarize(values) for key, values in sorted(groups.items())}


def family_matrix(trades: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    groups: dict[str, list[Decimal]] = defaultdict(list)
    for trade in trades:
        key = f"{trade['swept_family']}->{trade['target_family']}"
        groups[key].append(dec(trade["primary_net_r"]))
    return {key: summarize(values) for key, values in sorted(groups.items())}


def top_winner_concentration(trades: list[dict[str, Any]]) -> dict[str, str | None]:
    positives = sorted(
        (dec(trade["primary_net_r"]) for trade in trades if dec(trade["primary_net_r"]) > 0),
        reverse=True,
    )
    total = sum(positives, Decimal(0))
    if total <= 0:
        return {"top1": None, "top3": None, "top5": None, "top10": None}
    return {
        "top1": str(sum(positives[:1], Decimal(0)) / total),
        "top3": str(sum(positives[:3], Decimal(0)) / total),
        "top5": str(sum(positives[:5], Decimal(0)) / total),
        "top10": str(sum(positives[:10], Decimal(0)) / total),
    }


def run(source_root: Path, holdout_root: Path, output: Path) -> dict[str, Any]:
    trade_files = list(holdout_root.rglob("trades.json"))
    report_files = list(holdout_root.rglob("report.json"))
    if len(trade_files) != 1 or len(report_files) != 1:
        raise ValueError("expected exactly one immutable holdout trades/report pair")
    trades: list[dict[str, Any]] = json.loads(trade_files[0].read_text())
    parent_report = json.loads(report_files[0].read_text())
    if parent_report["trade_count"] != len(trades):
        raise ValueError("holdout trade census mismatch")

    bars_by_symbol = load_bars(source_root)
    stopped_rows: list[dict[str, Any]] = []
    all_risk_bps: list[Decimal] = []
    all_projected_r: list[Decimal] = []
    all_sweep_cisd_minutes: list[Decimal] = []
    all_entry_exit_minutes: list[Decimal] = []
    stopped_pre_mfe: list[Decimal] = []
    stopped_post_recovery: list[Decimal] = []
    stopped_final_close_r: list[Decimal] = []
    stop_latency_minutes: list[Decimal] = []
    stop_latency_buckets: Counter[str] = Counter()
    post_recovery_counts: Counter[str] = Counter()
    pre_stop_counts: Counter[str] = Counter()

    for trade in trades:
        symbol = str(trade["symbol"])
        bars = bars_by_symbol[symbol]
        opened = [bar["opened_at"] for bar in bars]
        entry_at = dt(trade["entry_at"])
        exit_at = dt(trade["exit_at"])
        sweep_at = dt(trade["sweep_at"])
        cisd_at = dt(trade["cisd_at"])
        entry = dec(trade["entry"])
        stop = dec(trade["stop"])
        target = dec(trade["target"])
        side = str(trade["side"])
        risk = abs(entry - stop)
        if risk <= 0:
            raise ValueError("non-positive frozen risk in authoritative trade")
        risk_bps = risk / entry * Decimal(10000)
        all_risk_bps.append(risk_bps)
        all_projected_r.append(dec(trade["projected_r"]))
        all_sweep_cisd_minutes.append(
            Decimal(str((cisd_at - sweep_at).total_seconds() / 60))
        )
        all_entry_exit_minutes.append(
            Decimal(str((exit_at - entry_at).total_seconds() / 60))
        )

        if trade["exit_reason"] not in STOP_REASONS:
            continue

        entry_index = bisect.bisect_left(opened, entry_at)
        if entry_index >= len(bars) or bars[entry_index]["opened_at"] != entry_at:
            raise ValueError("entry does not bind exact M5 open")
        exit_index = containing_index(opened, bars, exit_at)
        end_index = session_end_index(bars, entry_index)

        pre_mfe = favorable_r(
            bars,
            entry_index,
            exit_index,
            side=side,
            entry=entry,
            risk=risk,
        )
        post_recovery = favorable_r(
            bars,
            exit_index + 1,
            end_index,
            side=side,
            entry=entry,
            risk=risk,
        )
        final_r = final_close_r(
            bars[end_index - 1],
            side=side,
            entry=entry,
            risk=risk,
        )
        latency = Decimal(str((exit_at - entry_at).total_seconds() / 60))

        stopped_pre_mfe.append(pre_mfe)
        stopped_post_recovery.append(post_recovery)
        stopped_final_close_r.append(final_r)
        stop_latency_minutes.append(latency)

        for threshold, name in (
            (Decimal("0.25"), "pre_mfe_ge_0_25r"),
            (Decimal("0.50"), "pre_mfe_ge_0_50r"),
            (Decimal("1.00"), "pre_mfe_ge_1_00r"),
        ):
            if pre_mfe >= threshold:
                pre_stop_counts[name] += 1
        for threshold, name in (
            (Decimal("0.00"), "recovered_entry"),
            (Decimal("0.50"), "post_recovery_ge_0_50r"),
            (Decimal("1.00"), "post_recovery_ge_1_00r"),
        ):
            if post_recovery > threshold if threshold == 0 else post_recovery >= threshold:
                post_recovery_counts[name] += 1
        target_r = abs(target - entry) / risk
        if post_recovery >= target_r:
            post_recovery_counts["post_recovery_reached_original_target"] += 1

        minutes = float(latency)
        if minutes <= 15:
            stop_latency_buckets["le_15m"] += 1
        elif minutes <= 30:
            stop_latency_buckets["gt15_le30m"] += 1
        elif minutes <= 60:
            stop_latency_buckets["gt30_le60m"] += 1
        else:
            stop_latency_buckets["gt60m"] += 1

        stopped_rows.append(
            {
                "symbol": symbol,
                "side": side,
                "swept_family": trade["swept_family"],
                "target_family": trade["target_family"],
                "entry_at": trade["entry_at"],
                "exit_at": trade["exit_at"],
                "risk_bps": str(risk_bps),
                "projected_r": trade["projected_r"],
                "stop_latency_minutes": str(latency),
                "pre_stop_mfe_lower_bound_r": str(pre_mfe),
                "post_stop_recovery_lower_bound_r": str(post_recovery),
                "final_session_close_r": str(final_r),
            }
        )

    stopped_count = len(stopped_rows)

    def share(counter: Counter[str], key: str) -> str | None:
        if stopped_count == 0:
            return None
        return str(Decimal(counter[key]) / Decimal(stopped_count))

    by_exit = group_trade_metric(trades, "exit_reason")
    report: dict[str, Any] = {
        "schema": "qore.trader_lab.ict_turtle_soup_r2_forex_forensics.v1",
        "forensics_only": True,
        "parent_holdout_run": 35030690033,
        "parent_holdout_artifact": 10420839755,
        "parent_trade_count": len(trades),
        "stopped_trade_count": stopped_count,
        "all_trade_distributions": {
            "risk_bps": quantiles(all_risk_bps),
            "projected_r": quantiles(all_projected_r),
            "sweep_to_cisd_minutes": quantiles(all_sweep_cisd_minutes),
            "entry_to_exit_minutes": quantiles(all_entry_exit_minutes),
        },
        "stopped_trade_distributions": {
            "pre_stop_mfe_lower_bound_r": quantiles(stopped_pre_mfe),
            "post_stop_recovery_lower_bound_r": quantiles(stopped_post_recovery),
            "final_session_close_r": quantiles(stopped_final_close_r),
            "stop_latency_minutes": quantiles(stop_latency_minutes),
        },
        "stopped_pre_mfe_shares": {
            key: share(pre_stop_counts, key) for key in sorted(pre_stop_counts)
        },
        "post_stop_recovery_shares": {
            key: share(post_recovery_counts, key)
            for key in (
                "recovered_entry",
                "post_recovery_ge_0_50r",
                "post_recovery_ge_1_00r",
                "post_recovery_reached_original_target",
            )
        },
        "stop_latency_buckets": dict(sorted(stop_latency_buckets.items())),
        "by_exit_reason": by_exit,
        "by_swept_family": group_trade_metric(trades, "swept_family"),
        "by_target_family": group_trade_metric(trades, "target_family"),
        "swept_target_family_matrix": family_matrix(trades),
        "by_symbol": group_trade_metric(trades, "symbol"),
        "by_side": group_trade_metric(trades, "side"),
        "top_winner_concentration": top_winner_concentration(trades),
        "root_cause_labels_are_not_auto_selected": True,
        "candidate_selection_authorized": False,
        "post_result_filtering_authorized": False,
        "fresh_oos_accessed": False,
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "forensics-report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    (output / "stopped-trades-forensics.json").write_text(
        json.dumps(stopped_rows, indent=2, sort_keys=True) + "\n"
    )
    return report


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit(
            "usage: ict_turtle_soup_r2_forex_forensics "
            "SOURCE_ROOT HOLDOUT_ROOT OUTPUT_DIR"
        )
    report = run(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
