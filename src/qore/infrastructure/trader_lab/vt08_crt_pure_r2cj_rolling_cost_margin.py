"""R2-CJ read-only archived rolling-H4 cross-period R-normalized cost audit.

Freeze: docs/research/VT08-CRT-PURE-R2CJ-ROLLING-H4-COST-MARGIN-FREEZE-001.md
All evidence is R2-AO and R2-AQ archived JSONL. No new orders, sizing or trading.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

IDENTITY = "VT08_CRT_PURE_R2CJ_ROLLING_H4_COST_MARGIN_RECONCILIATION_001"
AO_ID = "VT08_CRT_PURE_R2AO_ROLLING_STRUCTURAL_TARGET_001"
AQ_ID = "VT08_CRT_PURE_R2AQ_HIGH_DENSITY_HISTORICAL_VALIDATION_001"
ARM = "FIXED_1_5R"
POLICY = "NEWEST_SUPERSEDES_CONFIRMATION_FIRST"
MARKETS = ("AUDUSD", "USDJPY")
COSTS = (0.0, 0.005, 0.01, 0.02, 0.05)
BOUNDARY = datetime(2020, 9, 21, tzinfo=UTC)
END = datetime(2026, 9, 21, tzinfo=UTC)
EARLIEST = {"AUDUSD": datetime(2016, 9, 21, tzinfo=UTC),
            "USDJPY": datetime(2014, 9, 21, tzinfo=UTC)}


def _lines(path: Path) -> tuple[dict[str, Any], ...]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as fp:
        for number, line in enumerate(fp, 1):
            if not line.strip():
                continue
            data: Any = json.loads(line)
            if not isinstance(data, dict):
                raise ValueError(f"Non-object source row {path}:{number}")
            rows.append(data)
    if not rows:
        raise ValueError(f"Missing immutable source records: {path}")
    return tuple(rows)


def _check_number(actual: Any, expected: Any, label: str) -> None:
    if actual is None or expected is None:
        if actual is not expected:
            raise ValueError(f"Frozen {label} missing-field mismatch")
    elif abs(float(actual) - float(expected)) > 0.000001:
        raise ValueError(f"Frozen {label} mismatch: {actual} != {expected}")


def _time(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValueError("Expected ISO entry timestamp")
    time = datetime.fromisoformat(value)
    if time.tzinfo is None:
        raise ValueError("Naive entry timestamps disallowed")
    return time.astimezone(UTC)


def _gross(rows: tuple[dict[str, Any], ...]) -> dict[str, Any]:
    r = [float(x["r_multiple"]) for x in rows]
    win = sum(v for v in r if v > 0)
    loss = -sum(v for v in r if v < 0)
    return {
        "trades": len(rows),
        "total_r": round(sum(r), 8),
        "profit_factor": round(win / loss, 8) if loss else None,
    }


def _check_frozen(
    market: str, source: str, rows: tuple[dict[str, Any], ...],
    report: dict[str, Any],
) -> dict[str, Any]:
    if market not in MARKETS or report["market"] != market:
        raise ValueError("Market mismatch or unsupported BTCUSD")
    if report["identity"] != (AO_ID if source == "AO" else AQ_ID):
        raise ValueError("Original runner/lineage identity mismatch")
    if report["base_competition_policy"] != POLICY:
        raise ValueError("Unexpected source competition model")
    if source == "AO":
        if report["timing_lattice"] != "ROLLING_H4":
            raise ValueError("AO timing lattice is not rolling H4")
        original_summary = report["arms"][ARM]["full_6y"]
        selected = tuple(row for row in rows if row.get("target_arm") == ARM)
        if len(selected) == 0:
            raise ValueError("No frozen FIXED_1_5R arm rows")
        start, end = BOUNDARY, END
        annual = report["arms"][ARM]["annual"]
    elif source == "AQ":
        if report["timing_lattice"] != "ROLLING_H4" or report["target_arm"] != ARM:
            raise ValueError("AQ arm/lattice mismatched")
        selected = rows
        original_summary = report["full_window"]
        start, end = EARLIEST[market], BOUNDARY
        annual = report["annual"]
    else:
        raise ValueError(f"Unsupported source {source}")

    seen: set[tuple[str, str, str]] = set()
    for row in selected:
        if row["market"] != market:
            raise ValueError("Cross-market source contamination")
        time = _time(row["entry_opened_at"])
        if not start <= time < end:
            raise ValueError("Entry outside frozen AO/AQ source interval")
        if row.get("research_only") is not True:
            raise ValueError("Non-research source event in archive")
        key = (row["c3_opened_at"], row["source_opened_at"], row["entry_opened_at"])
        if key in seen:
            raise ValueError("Duplicated frozen source-entry identity")
        seen.add(key)
    reconstructed = _gross(selected)
    for k in ("trades", "total_r", "profit_factor"):
        _check_number(reconstructed[k], original_summary[k], f"{market}:{source}:{k}")

    for label, stats in annual.items():
        years = label.split("_")
        if len(years) != 2 or int(years[1]) != int(years[0]) + 1:
            raise ValueError("Malformed historical annual fold")
        left, right = (
            datetime(int(y), 9, 21, tzinfo=UTC) for y in years
        )
        annual_rows = tuple(
            row for row in selected
            if left <= _time(row["entry_opened_at"]) < right
        )
        snapshot = _gross(annual_rows)
        for k in ("trades", "total_r", "profit_factor"):
            _check_number(snapshot[k], stats[k], f"{market}:{source}:{label}:{k}")
    if sum(int(x["trades"]) for x in annual.values()) != len(selected):
        raise ValueError("Frozen annual fold coverage not complete")
    return {
        "verified": True,
        "source_run_id": 35863768335 if source == "AO" else 35865028789,
        "rows_count": len(selected),
        "start": start.isoformat(),
        "end_exclusive": end.isoformat(),
        "original_summary": original_summary,
        "annual_folds": len(annual),
    }


def _stats(rs: tuple[float, ...]) -> dict[str, Any]:
    equity = 0.0
    peak = 0.0
    dd = 0.0
    wins = 0.0
    losses = 0.0
    for r in rs:
        if r > 0:
            wins += r
        elif r < 0:
            losses -= r
        equity += r
        peak = max(peak, equity)
        dd = max(dd, peak - equity)
    return {
        "trades": len(rs),
        "total_r": round(sum(rs), 8),
        "mean_r": round(sum(rs) / len(rs), 8) if rs else None,
        "profit_factor": round(wins / losses, 8) if losses else None,
        "max_drawdown_r": round(dd, 8),
    }


def _stress(
    market: str, all_rows: tuple[dict[str, Any], ...]
) -> dict[str, Any]:
    time_sorted = tuple(sorted(all_rows, key=lambda row: _time(row["entry_opened_at"])))
    raw = tuple(float(row["r_multiple"]) for row in time_sorted)
    year_count = END.year - EARLIEST[market].year
    annual_ranges = tuple((
        datetime(y, 9, 21, tzinfo=UTC),
        datetime(y + 1, 9, 21, tzinfo=UTC),
    ) for y in range(EARLIEST[market].year, END.year))
    if year_count != len(annual_ranges):
        raise ValueError("Annual ranges mismatch")
    observations: dict[str, Any] = {}
    for cost in COSTS:
        shifted = tuple(value - cost for value in raw)
        summary = _stats(shifted)
        annual: dict[str, Any] = {}
        for left, right in annual_ranges:
            year_rows = tuple(
                float(row["r_multiple"]) - cost
                for row in time_sorted
                if left <= _time(row["entry_opened_at"]) < right
            )
            annual[f"{left.year}_{right.year}"] = _stats(year_rows)
        if sum(x["trades"] for x in annual.values()) != len(time_sorted):
            raise ValueError("Cost annual trade count mismatch")
        positive = sum(float(x["total_r"]) > 0 for x in annual.values())
        observations[f"COST_{cost:g}R"] = {
            **summary, "positive_years": positive, "total_years": year_count,
            "positive_year_fraction": round(positive / year_count, 8),
            "annual": annual,
        }
        _check_number(
            summary["total_r"], sum(raw) - cost * len(raw),
            f"{market}:cost={cost} adjusted R",
        )
    gross = observations["COST_0R"]
    annual_mean = len(raw) / year_count
    same_entry: Counter[str] = Counter(
        _time(row["entry_opened_at"]).isoformat() for row in time_sorted
    )
    same_source: Counter[str] = Counter(
        row["source_opened_at"] for row in time_sorted
    )
    return {
        "years": year_count,
        "actual_trades": len(raw),
        "annual_density": round(annual_mean, 8),
        "over_170_trades_per_year": annual_mean >= 170,
        "yearly_density_over_170": sum(
            annual["trades"] >= 170
            for annual in observations["COST_0R"]["annual"].values()
        ),
        "gross_break_even_cost_R_per_trade": round(
            float(gross["total_r"]) / len(raw), 8
        ),
        "duplicate_entry_timestamp_events": sum(
            x - 1 for x in same_entry.values() if x > 1
        ),
        "duplicate_source_timestamp_events_not_necessarily_same_parent": sum(
            x - 1 for x in same_source.values() if x > 1
        ),
        "gross_and_cost_stress": observations,
        "independent_execution_fill_validated": False,
        "nonzero_broker_bid_ask_fees_validated": False,
    }


def run_market(
    market: str, *, older_trades: Path, older_report: Path,
    recent_trades: Path, recent_report: Path,
) -> dict[str, Any]:
    if market not in MARKETS:
        raise ValueError("Only AUDUSD and USDJPY; BTCUSD frozen")
    older = _lines(older_trades)
    recent = _lines(recent_trades)
    a_report = json.loads(older_report.read_text(encoding="utf-8"))
    b_report = json.loads(recent_report.read_text(encoding="utf-8"))
    verified_older = _check_frozen(market, "AQ", older, a_report)
    verified_recent = _check_frozen(market, "AO", recent, b_report)
    fixed_recent = tuple(row for row in recent if row.get("target_arm") == ARM)
    combined = older + fixed_recent
    structural_seen: set[tuple[str, str, str]] = set()
    for row in combined:
        key = (row["c3_opened_at"], row["source_opened_at"], row["entry_opened_at"])
        if key in structural_seen:
            raise ValueError("Duplicate combined source/entry identity")
        structural_seen.add(key)
    return {
        "identity": IDENTITY, "market": market,
        "inputs_verified": {"older_AQ": verified_older, "recent_AO": verified_recent},
        "input_sha256": {
            key: hashlib.sha256(path.read_bytes()).hexdigest()
            for key, path in {
                "older_trades": older_trades, "older_report": older_report,
                "recent_trades": recent_trades, "recent_report": recent_report,
            }.items()
        },
        "audited_core": {
            "parent_observation": "ROLLING_H4_SIX_STARTS",
            "target": ARM, "source_competition": POLICY,
            "one_selected_hypothesis_per_parent": True,
        },
        "result": _stress(market, combined),
        "economic_candidate_promoted": False,
        "fresh_holdout_used": False,
        "new_market_data_acquired": False,
        "research_only": True,
        "no_trader_sizing_volume_leverage_capital_authority": True,
        "no_merge_or_deployment": True,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("output", type=Path)
    p.add_argument("--market", choices=MARKETS, required=True)
    for flag in ("older-trades", "older-report", "recent-trades", "recent-report"):
        p.add_argument(f"--{flag}", required=True, type=Path)
    a = p.parse_args()
    result = run_market(
        a.market, older_trades=a.older_trades, older_report=a.older_report,
        recent_trades=a.recent_trades, recent_report=a.recent_report,
    )
    a.output.mkdir(parents=True, exist_ok=True)
    (a.output / "report.json").write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    info = result["result"]
    print("VT08_R2CJ_ROLLING_COST_AUDIT=" + json.dumps({
        "market": a.market, "years": info["years"],
        "trades": info["actual_trades"],
        "annual_density": info["annual_density"],
        "gross_break_even_cost_R_per_trade": info["gross_break_even_cost_R_per_trade"],
        "gross_and_cost_stress": {
            name: {k: v[k] for k in (
                "trades", "total_r", "mean_r", "profit_factor", "max_drawdown_r",
                "positive_years", "total_years",
            )} for name, v in info["gross_and_cost_stress"].items()
        },
        "sources_exactly_reproduced": True,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
