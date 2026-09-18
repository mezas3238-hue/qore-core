"""GBPUSD R43 — rank-2 fragility correction after R42 forensics.

R42 established that target-rank 1 is positive in all 5 annual blocks, while
rank-2 is negative in the two problematic blocks. R43 preserves all 907
signals and the frozen R37 structural scale, applies a fixed 0.5% relative
SHORT overlay, and tests only monotonic pre-entry rank-2 risk reductions.
Calendar year is validation only and never an execution input.
"""
from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

from qore.infrastructure.trader_lab import (
    turtle_soup_gbpusd_r37_structural_quality_governor as r37,
)

IDENTITY = "TURTLE_SOUP_GBPUSD_R43_RANK2_FRAGILITY_CORRECTION_V1"
SOURCE_RUN_ID = 35353073610
SOURCE_ARTIFACT_ID = 10550866581
SOURCE_ARTIFACT_DIGEST = (
    "sha256:825b2858d9d471dc85c83d6783536e1b97c597d38333c7c2adae0d0a00552683"
)
SOURCE_GIT_SHA = "e02d9384fbe6521040fc2779a085c43b8d5f0f92"
SOURCE_REPORT_SHA256 = "ba315d13aedf8ba65bce43d628a97b44925ccf810d55a39bfcf60f4a29544690"
SOURCE_TRADES_SHA256 = "693a55aa4f1bed4c211976e0aa54b469c62902caec88d7490268567af32ed8c0"

MIN_TRADES = 800
MIN_PF_010 = Decimal("1.50")
MAX_DD_010 = Decimal("6.0")
MIN_POSITIVE_ANNUAL_BLOCKS = 5
SHORT_SCALE = Decimal("0.005")
DRAWDOWN_GOVERNOR = r37.GOVERNORS["DD_1_3_SCALE_075_025"]

RANK2_SCALES: dict[str, Decimal] = {
    "R43_RANK2_050": Decimal("0.50"),
    "R43_RANK2_025": Decimal("0.25"),
    "R43_RANK2_010": Decimal("0.10"),
    "R43_RANK2_005": Decimal("0.05"),
    "R43_RANK2_001": Decimal("0.01"),
}


@dataclass(frozen=True, slots=True)
class Trade:
    entry_at: datetime
    exit_at: datetime
    side: str
    source: str
    family: str | None
    classification: str
    target_rank: int
    target_route: str
    raw_net_010_r: Decimal
    frozen_structural_scale: Decimal


@dataclass(frozen=True, slots=True)
class CorrectedTrade:
    entry_at: str
    exit_at: str
    side: str
    source: str
    family: str | None
    classification: str
    target_rank: int
    target_route: str
    raw_net_010_r: str
    frozen_structural_scale: str
    short_scale: str
    rank_scale: str
    drawdown_scale: str
    corrected_risk_scale: str
    corrected_net_010_r: str


def _single(root: Path, name: str) -> Path:
    matches = list(root.rglob(name))
    if len(matches) != 1:
        raise ValueError(f"expected one {name}, got {len(matches)}")
    return matches[0]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(root: Path) -> tuple[dict[str, Any], list[Trade]]:
    report_path = _single(root, "r39-5y-validation-report.json")
    trades_path = _single(root, "r39-5y-scaled-trades.jsonl")
    git_path = _single(root, "git-sha.txt")
    if _sha256(report_path) != SOURCE_REPORT_SHA256:
        raise ValueError("R39 report hash drift")
    if _sha256(trades_path) != SOURCE_TRADES_SHA256:
        raise ValueError("R39 trades hash drift")
    if git_path.read_text().strip() != SOURCE_GIT_SHA:
        raise ValueError("R39 git binding drift")

    report = cast(dict[str, Any], json.loads(report_path.read_text()))
    if report["identity"] != "TURTLE_SOUP_GBPUSD_R39_FROZEN_R37_5Y_VALIDATION_V1":
        raise ValueError("unexpected R39 identity")
    if report["result"]["trades"] != 907:
        raise ValueError("R39 trade-count drift")
    if report["governance"]["fresh_holdout_consumed"] is not False:
        raise ValueError("fresh holdout drift")

    trades: list[Trade] = []
    with trades_path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            trades.append(
                Trade(
                    entry_at=datetime.fromisoformat(str(row["entry_at"])),
                    exit_at=datetime.fromisoformat(str(row["exit_at"])),
                    side=str(row["side"]),
                    source=str(row["source"]),
                    family=None if row["family"] is None else str(row["family"]),
                    classification=str(row["classification"]),
                    target_rank=int(row["target_rank"]),
                    target_route=str(row["target_route"]),
                    raw_net_010_r=Decimal(str(row["raw_net_010_r"])),
                    frozen_structural_scale=Decimal(str(row["structural_scale"])),
                )
            )
    if len(trades) != 907:
        raise ValueError("R39 JSONL trade-count drift")
    return report, trades


def _pf(values: Sequence[Decimal]) -> Decimal | None:
    gains = sum((value for value in values if value > 0), Decimal(0))
    losses = -sum((value for value in values if value < 0), Decimal(0))
    return None if losses == 0 else gains / losses


def _stats(values: Sequence[Decimal]) -> dict[str, Any]:
    equity = Decimal(0)
    peak = Decimal(0)
    max_dd = Decimal(0)
    streak = 0
    max_streak = 0
    for value in values:
        equity += value
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
        if value < 0:
            streak += 1
            max_streak = max(max_streak, streak)
        elif value > 0:
            streak = 0
    pf = _pf(values)
    return {
        "trades": len(values),
        "total_r": str(equity),
        "mean_r": None if not values else str(equity / Decimal(len(values))),
        "profit_factor": None if pf is None else str(pf),
        "max_drawdown_r": str(max_dd),
        "max_losing_streak": max_streak,
    }


def _annual(rows: Sequence[CorrectedTrade]) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    for year in range(5):
        start = datetime(2021 + year, 9, 17, tzinfo=UTC)
        end = datetime(2022 + year, 9, 17, tzinfo=UTC)
        values = [
            Decimal(row.corrected_net_010_r)
            for row in rows
            if start <= datetime.fromisoformat(row.entry_at) < end
        ]
        stats = _stats(values)
        blocks.append({
            "open": start.isoformat(),
            "close": end.isoformat(),
            **stats,
            "positive_total": Decimal(str(stats["total_r"])) > 0,
        })
    return blocks


def _run_policy(trades: Sequence[Trade], policy: str) -> dict[str, Any]:
    rank2_scale = RANK2_SCALES[policy]
    equity = Decimal(0)
    peak = Decimal(0)
    rows: list[CorrectedTrade] = []
    scale_counts: Counter[str] = Counter()

    for trade in trades:
        short_scale = SHORT_SCALE if trade.side == "short" else Decimal("1")
        rank_scale = rank2_scale if trade.target_rank == 2 else Decimal("1")
        pretrade_overlay = min(short_scale, rank_scale)
        drawdown_scale = r37._risk_scale(peak - equity, DRAWDOWN_GOVERNOR)
        risk_scale = trade.frozen_structural_scale * pretrade_overlay * drawdown_scale
        contribution = trade.raw_net_010_r * risk_scale
        equity += contribution
        peak = max(peak, equity)
        scale_counts[str(risk_scale)] += 1
        rows.append(
            CorrectedTrade(
                entry_at=trade.entry_at.isoformat(),
                exit_at=trade.exit_at.isoformat(),
                side=trade.side,
                source=trade.source,
                family=trade.family,
                classification=trade.classification,
                target_rank=trade.target_rank,
                target_route=trade.target_route,
                raw_net_010_r=str(trade.raw_net_010_r),
                frozen_structural_scale=str(trade.frozen_structural_scale),
                short_scale=str(short_scale),
                rank_scale=str(rank_scale),
                drawdown_scale=str(drawdown_scale),
                corrected_risk_scale=str(risk_scale),
                corrected_net_010_r=str(contribution),
            )
        )

    values = [Decimal(row.corrected_net_010_r) for row in rows]
    stats = _stats(values)
    annual = _annual(rows)
    positive_years = sum(bool(item["positive_total"]) for item in annual)
    pf_raw = stats["profit_factor"]
    pf = None if pf_raw is None else Decimal(str(pf_raw))
    dd = Decimal(str(stats["max_drawdown_r"]))
    total = Decimal(str(stats["total_r"]))
    passed = bool(
        len(rows) >= MIN_TRADES
        and pf is not None
        and pf >= MIN_PF_010
        and dd <= MAX_DD_010
        and total > 0
        and positive_years == MIN_POSITIVE_ANNUAL_BLOCKS
    )
    return {
        "policy": policy,
        "short_scale": str(SHORT_SCALE),
        "rank2_scale": str(rank2_scale),
        "stats": stats,
        "annual_blocks": annual,
        "positive_annual_blocks": positive_years,
        "risk_scale_counts": dict(scale_counts),
        "acceptance_pass": passed,
        "_rows": rows,
    }


def run(source_root: Path, output: Path) -> dict[str, Any]:
    source_report, trades = _load(source_root)
    results = [_run_policy(trades, policy) for policy in RANK2_SCALES]
    passing = [item for item in results if item["acceptance_pass"]]

    def ranking(item: dict[str, Any]) -> tuple[Decimal, Decimal, Decimal]:
        stats = item["stats"]
        return (
            Decimal(str(stats["profit_factor"])),
            -Decimal(str(stats["max_drawdown_r"])),
            Decimal(str(stats["total_r"])),
        )

    selected = max(passing, key=ranking) if passing else None

    output.mkdir(parents=True, exist_ok=True)
    public_results = [
        {key: value for key, value in item.items() if key != "_rows"}
        for item in results
    ]
    if selected is not None:
        selected_internal = next(
            item for item in results if item["policy"] == selected["policy"]
        )
        with (output / "r43-5y-corrected-trades.jsonl").open("w", encoding="utf-8") as handle:
            for row in selected_internal["_rows"]:
                handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")

    report: dict[str, Any] = {
        "schema": "qore.turtle_soup_gbpusd.r43_rank2_fragility_correction.v1",
        "identity": IDENTITY,
        "source_binding": {
            "run_id": SOURCE_RUN_ID,
            "artifact_id": SOURCE_ARTIFACT_ID,
            "artifact_digest": SOURCE_ARTIFACT_DIGEST,
            "git_sha": SOURCE_GIT_SHA,
            "report_sha256": SOURCE_REPORT_SHA256,
            "trades_sha256": SOURCE_TRADES_SHA256,
        },
        "r42_forensic_basis": {
            "rank1_positive_annual_blocks": 5,
            "rank1_5y_total_r_at_short_0005_baseline": "27.208783870556424",
            "rank2_positive_annual_blocks": 3,
            "rank2_year1_r_at_short_0005_baseline": "-0.15818666524580846",
            "rank2_year3_r_at_short_0005_baseline": "-1.706126572323912",
            "calendar_time_used_as_execution_rule": False,
        },
        "correction_contract": {
            "signals_suppressed": False,
            "all_907_trades_preserved": True,
            "structural_risk_overlay_only": True,
            "preentry_target_rank_only": True,
            "short_side_known_preentry": True,
            "entry_changed": False,
            "target_changed": False,
            "stop_changed": False,
            "lifecycle_changed": False,
            "families_changed": False,
            "fresh_holdout_consumed": False,
            "short_scale": str(SHORT_SCALE),
            "rank2_scales_predeclared": {
                name: str(value) for name, value in RANK2_SCALES.items()
            },
        },
        "predeclared_acceptance": {
            "minimum_trades": MIN_TRADES,
            "minimum_profit_factor": str(MIN_PF_010),
            "maximum_drawdown_r": str(MAX_DD_010),
            "minimum_positive_annual_blocks": MIN_POSITIVE_ANNUAL_BLOCKS,
            "total_must_be_positive": True,
            "calendar_time_not_used_as_rule": True,
        },
        "source_r39": {
            "trades": source_report["result"]["trades"],
            "profit_factor": source_report["result"]["profit_factor_scaled_net_010"],
            "max_drawdown_r": source_report["result"]["max_drawdown_scaled_r"],
        },
        "results": public_results,
        "selected": None if selected is None else {
            key: value for key, value in selected.items() if key != "_rows"
        },
        "governance": {
            "candidate_certified": False,
            "fresh_holdout_consumed": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
            "merge_authorized": False,
        },
    }
    (output / "r43-rank2-fragility-correction-report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    return report


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: module R39_ARTIFACT_ROOT OUTPUT_DIR")
    print(json.dumps(run(Path(sys.argv[1]), Path(sys.argv[2])), sort_keys=True))


if __name__ == "__main__":
    main()
