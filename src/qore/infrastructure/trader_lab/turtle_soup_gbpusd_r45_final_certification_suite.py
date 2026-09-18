"""Final QORE certification suite for frozen GBPUSD R43.

Inputs are immutable artifacts:
- R43 exact passing 5Y corrected trades;
- R39 original frozen trade metadata for exit-reason binding;
- R44 candidate freeze.

No rules are changed and the fresh holdout remains sealed.
"""
from __future__ import annotations

import hashlib
import json
import random
import sys
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

IDENTITY = "TURTLE_SOUP_GBPUSD_R45_FINAL_CERTIFICATION_SUITE_V1"
CANDIDATE_IDENTITY = "TURTLE_SOUP_GBPUSD_R43_5Y_CANDIDATE_001"

R43_RUN_ID = 35357443440
R43_ARTIFACT_ID = 10552052483
R43_ARTIFACT_DIGEST = (
    "sha256:1157e9e3079d46e04d541744c012f75cc5405cb0e299d593622ab11777b9308f"
)
R43_GIT_SHA = "2748596bd132e6577e87851849a338b9a7a9c42e"
R43_REPORT_SHA256 = (
    "39df0bb2984e8ad9e62b7eac0cf4f716ae88f0d0f9e7c81173965e037e48cbe0"
)
R43_TRADES_SHA256 = (
    "4af1c2977b2b80437f1a58436efa4967fec09d0d8968946e41f41f5c9db1025e"
)

R39_RUN_ID = 35353073610
R39_ARTIFACT_ID = 10550866581
R39_GIT_SHA = "e02d9384fbe6521040fc2779a085c43b8d5f0f92"
R39_REPORT_SHA256 = (
    "ba315d13aedf8ba65bce43d628a97b44925ccf810d55a39bfcf60f4a29544690"
)
R39_TRADES_SHA256 = (
    "693a55aa4f1bed4c211976e0aa54b469c62902caec88d7490268567af32ed8c0"
)

FREEZE_RUN_ID = 35357779125
FREEZE_ARTIFACT_ID = 10552911323
FREEZE_ARTIFACT_DIGEST = (
    "sha256:cb648b672eedd43afad918380b815eb3a619448ffd74b8d8ae421d3c98491087"
)

WINDOW_OPEN = datetime.fromisoformat("2021-09-17T00:00:00+00:00")
WINDOW_CLOSE = datetime.fromisoformat("2026-09-17T00:00:00+00:00")

BASELINE_TRADES = 907
BASELINE_PF = Decimal("1.713624514596208498825398640")
BASELINE_DD = Decimal("4.401231922815307849576052766")
BASELINE_TOTAL = Decimal("35.40396721533287699752413575")
BASELINE_POSITIVE_ANNUAL = 5

WFO_BLOCK_MONTHS = 6
WFO_BLOCKS = 10
WFO_MIN_POSITIVE_BLOCKS = 6
WFO_MIN_AGGREGATE_PF = Decimal("1.30")
WFO_WORST_BLOCK_TOTAL_FLOOR_R = Decimal("-6.0")

MC_PATHS = 20_000
MC_BLOCK_SIZE = 5
MC_SEED = 20260918
MC_MIN_POSITIVE_TERMINAL_PROB = Decimal("0.99")
MC_MAX_P95_DD_R = Decimal("20.0")
MC_MAX_P99_DD_R = Decimal("25.0")
MC_MIN_P05_TERMINAL_R = Decimal("0")

STRESS_SCENARIOS: dict[str, dict[str, Decimal]] = {
    "EXTRA_002": {
        "extra_r": Decimal("0.02"),
        "min_pf": Decimal("1.35"),
        "max_dd": Decimal("12.0"),
    },
    "EXTRA_005": {
        "extra_r": Decimal("0.05"),
        "min_pf": Decimal("1.25"),
        "max_dd": Decimal("15.0"),
    },
    "EXTRA_010": {
        "extra_r": Decimal("0.10"),
        "min_pf": Decimal("1.10"),
        "max_dd": Decimal("20.0"),
    },
}

SLIPPAGE_SCENARIOS: dict[str, dict[str, Any]] = {
    "NORMAL": {
        "TARGET": Decimal("0.005"),
        "STOP": Decimal("0.020"),
        "TRAIL_STOP": Decimal("0.020"),
        "TRAIL_STOP_FIRST": Decimal("0.020"),
        "STOP_FIRST": Decimal("0.020"),
        "GAP_STOP": Decimal("0.030"),
        "GAP_TRAIL": Decimal("0.030"),
        "TIME_24H": Decimal("0.010"),
        "min_pf": Decimal("1.35"),
        "max_dd": Decimal("12.0"),
    },
    "ADVERSE": {
        "TARGET": Decimal("0.010"),
        "STOP": Decimal("0.050"),
        "TRAIL_STOP": Decimal("0.050"),
        "TRAIL_STOP_FIRST": Decimal("0.050"),
        "STOP_FIRST": Decimal("0.050"),
        "GAP_STOP": Decimal("0.080"),
        "GAP_TRAIL": Decimal("0.080"),
        "TIME_24H": Decimal("0.025"),
        "min_pf": Decimal("1.30"),
        "max_dd": Decimal("14.0"),
    },
    "SEVERE": {
        "TARGET": Decimal("0.020"),
        "STOP": Decimal("0.100"),
        "TRAIL_STOP": Decimal("0.100"),
        "TRAIL_STOP_FIRST": Decimal("0.100"),
        "STOP_FIRST": Decimal("0.100"),
        "GAP_STOP": Decimal("0.150"),
        "GAP_TRAIL": Decimal("0.150"),
        "TIME_24H": Decimal("0.050"),
        "min_pf": Decimal("1.20"),
        "max_dd": Decimal("15.0"),
    },
}

ROBUST_REQUIRED_POSITIVE_ANNUAL_BLOCKS = 5
ROBUST_MIN_POSITIVE_HALF_YEAR_BLOCKS = 6
ROBUST_MIN_SOURCE_PF = Decimal("1.30")
ROBUST_REQUIRED_POSITIVE_FAMILIES = 2
ROBUST_MIN_LOYO_PF = Decimal("1.30")


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
    exit_reason: str
    risk_scale: Decimal
    corrected_net_010_r: Decimal


def _single(root: Path, name: str) -> Path:
    matches = list(root.rglob(name))
    if len(matches) != 1:
        raise ValueError(f"expected exactly one {name}, got {len(matches)}")
    return matches[0]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _verify_freeze(root: Path) -> dict[str, Any]:
    path = _single(root, "r44-candidate-freeze-manifest.json")
    freeze = cast(dict[str, Any], json.loads(path.read_text()))
    if freeze["identity"] != CANDIDATE_IDENTITY:
        raise ValueError("freeze candidate identity drift")
    if freeze["status"] != "FROZEN_FOR_FINAL_ROBUSTNESS":
        raise ValueError("candidate not frozen")
    source = freeze["source"]
    if source["run_id"] != R43_RUN_ID:
        raise ValueError("R43 run binding drift")
    if source["artifact_id"] != R43_ARTIFACT_ID:
        raise ValueError("R43 artifact binding drift")
    if source["artifact_digest"] != R43_ARTIFACT_DIGEST:
        raise ValueError("R43 digest binding drift")
    if source["git_sha"] != R43_GIT_SHA:
        raise ValueError("R43 git binding drift")
    if source["report_sha256"] != R43_REPORT_SHA256:
        raise ValueError("R43 report binding drift")
    if source["trades_sha256"] != R43_TRADES_SHA256:
        raise ValueError("R43 trades binding drift")
    result = freeze["consumed_5y_result"]
    if int(result["trades"]) != BASELINE_TRADES:
        raise ValueError("freeze trade-count drift")
    if Decimal(str(result["profit_factor"])) != BASELINE_PF:
        raise ValueError("freeze PF drift")
    if Decimal(str(result["max_drawdown_r"])) != BASELINE_DD:
        raise ValueError("freeze DD drift")
    if Decimal(str(result["total_r"])) != BASELINE_TOTAL:
        raise ValueError("freeze total-R drift")
    if int(result["positive_annual_blocks"]) != BASELINE_POSITIVE_ANNUAL:
        raise ValueError("freeze annual stability drift")
    if freeze["next_stage"]["fresh_holdout_status"] != "SEALED_UNTOUCHED":
        raise ValueError("fresh holdout seal drift")
    if freeze["governance"]["candidate_frozen"] is not True:
        raise ValueError("freeze governance drift")
    if freeze["governance"]["fresh_holdout_consumed"] is not False:
        raise ValueError("fresh holdout consumption drift")
    return freeze


def _load(
    r43_root: Path,
    r39_root: Path,
    freeze_root: Path,
) -> tuple[dict[str, Any], dict[str, Any], list[Trade]]:
    freeze = _verify_freeze(freeze_root)

    r43_report_path = _single(r43_root, "r43-rank2-fragility-correction-report.json")
    r43_trades_path = _single(r43_root, "r43-5y-corrected-trades.jsonl")
    r43_git_path = _single(r43_root, "git-sha.txt")
    if _sha256(r43_report_path) != R43_REPORT_SHA256:
        raise ValueError("R43 report hash drift")
    if _sha256(r43_trades_path) != R43_TRADES_SHA256:
        raise ValueError("R43 trade hash drift")
    if r43_git_path.read_text().strip() != R43_GIT_SHA:
        raise ValueError("R43 git drift")

    r43_report = cast(dict[str, Any], json.loads(r43_report_path.read_text()))
    selected = r43_report["selected"]
    if selected is None or selected["acceptance_pass"] is not True:
        raise ValueError("R43 acceptance drift")
    if selected["policy"] != "R43_RANK2_025":
        raise ValueError("R43 policy drift")
    if int(selected["positive_annual_blocks"]) != 5:
        raise ValueError("R43 5/5 annual drift")
    stats = selected["stats"]
    if int(stats["trades"]) != BASELINE_TRADES:
        raise ValueError("R43 trades drift")
    if Decimal(str(stats["profit_factor"])) != BASELINE_PF:
        raise ValueError("R43 PF drift")
    if Decimal(str(stats["max_drawdown_r"])) != BASELINE_DD:
        raise ValueError("R43 DD drift")
    if Decimal(str(stats["total_r"])) != BASELINE_TOTAL:
        raise ValueError("R43 total drift")

    r39_report_path = _single(r39_root, "r39-5y-validation-report.json")
    r39_trades_path = _single(r39_root, "r39-5y-scaled-trades.jsonl")
    r39_git_path = _single(r39_root, "git-sha.txt")
    if _sha256(r39_report_path) != R39_REPORT_SHA256:
        raise ValueError("R39 report hash drift")
    if _sha256(r39_trades_path) != R39_TRADES_SHA256:
        raise ValueError("R39 trade hash drift")
    if r39_git_path.read_text().strip() != R39_GIT_SHA:
        raise ValueError("R39 git drift")

    r43_rows = [
        json.loads(line)
        for line in r43_trades_path.read_text().splitlines()
        if line.strip()
    ]
    r39_rows = [
        json.loads(line)
        for line in r39_trades_path.read_text().splitlines()
        if line.strip()
    ]
    if len(r43_rows) != BASELINE_TRADES or len(r39_rows) != BASELINE_TRADES:
        raise ValueError("trade row count drift")

    trades: list[Trade] = []
    for corrected, original in zip(r43_rows, r39_rows, strict=True):
        identity_fields = (
            "entry_at",
            "exit_at",
            "side",
            "source",
            "family",
            "classification",
            "target_rank",
            "target_route",
        )
        for field in identity_fields:
            if corrected[field] != original[field]:
                raise ValueError(f"R43/R39 trade identity drift: {field}")
        exit_reason = str(original["exit_reason"])
        if exit_reason not in SLIPPAGE_SCENARIOS["NORMAL"]:
            raise ValueError(f"unsupported exit reason: {exit_reason}")
        trades.append(
            Trade(
                entry_at=datetime.fromisoformat(str(corrected["entry_at"])),
                exit_at=datetime.fromisoformat(str(corrected["exit_at"])),
                side=str(corrected["side"]),
                source=str(corrected["source"]),
                family=None if corrected["family"] is None else str(corrected["family"]),
                classification=str(corrected["classification"]),
                target_rank=int(corrected["target_rank"]),
                target_route=str(corrected["target_route"]),
                exit_reason=exit_reason,
                risk_scale=Decimal(str(corrected["corrected_risk_scale"])),
                corrected_net_010_r=Decimal(str(corrected["corrected_net_010_r"])),
            )
        )
    return r43_report, freeze, trades


def _pf(values: list[Decimal]) -> Decimal | None:
    gains = sum((value for value in values if value > 0), Decimal(0))
    losses = -sum((value for value in values if value < 0), Decimal(0))
    return None if losses == 0 else gains / losses


def _stats(values: list[Decimal]) -> dict[str, Any]:
    equity = Decimal(0)
    peak = Decimal(0)
    max_dd = Decimal(0)
    losing = 0
    max_losing = 0
    for value in values:
        equity += value
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
        if value < 0:
            losing += 1
            max_losing = max(max_losing, losing)
        elif value > 0:
            losing = 0
    pf = _pf(values)
    return {
        "trades": len(values),
        "total_r": str(equity),
        "mean_r": None if not values else str(equity / Decimal(len(values))),
        "profit_factor": None if pf is None else str(pf),
        "max_drawdown_r": str(max_dd),
        "max_losing_streak": max_losing,
    }


def _add_months(at: datetime, months: int) -> datetime:
    index = at.year * 12 + (at.month - 1) + months
    year, month0 = divmod(index, 12)
    return at.replace(year=year, month=month0 + 1)


def _wfo(trades: list[Trade]) -> dict[str, Any]:
    blocks: list[dict[str, Any]] = []
    for index in range(WFO_BLOCKS):
        start = _add_months(WINDOW_OPEN, index * WFO_BLOCK_MONTHS)
        end = _add_months(start, WFO_BLOCK_MONTHS)
        members = [
            trade.corrected_net_010_r
            for trade in trades
            if start <= trade.entry_at < end
        ]
        stats = _stats(members)
        blocks.append({
            "block": index + 1,
            "open": start.isoformat(),
            "close": end.isoformat(),
            "stats": stats,
            "positive": Decimal(str(stats["total_r"])) > 0,
        })
    aggregate = _stats([trade.corrected_net_010_r for trade in trades])
    positive_blocks = sum(bool(block["positive"]) for block in blocks)
    worst_total = min(Decimal(str(block["stats"]["total_r"])) for block in blocks)
    aggregate_pf_raw = aggregate["profit_factor"]
    aggregate_pf = None if aggregate_pf_raw is None else Decimal(str(aggregate_pf_raw))
    passed = bool(
        positive_blocks >= WFO_MIN_POSITIVE_BLOCKS
        and aggregate_pf is not None
        and aggregate_pf >= WFO_MIN_AGGREGATE_PF
        and worst_total >= WFO_WORST_BLOCK_TOTAL_FLOOR_R
    )
    return {
        "method": "FIXED_RULE_6M_BLOCK_STABILITY",
        "blocks": blocks,
        "positive_blocks": positive_blocks,
        "aggregate": aggregate,
        "worst_block_total_r": str(worst_total),
        "gate": {
            "minimum_positive_blocks": WFO_MIN_POSITIVE_BLOCKS,
            "minimum_aggregate_pf": str(WFO_MIN_AGGREGATE_PF),
            "worst_block_total_floor_r": str(WFO_WORST_BLOCK_TOTAL_FLOOR_R),
        },
        "pass": passed,
    }


def _quantile(values: list[Decimal], q: float) -> Decimal:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("empty quantile input")
    pos = (len(ordered) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(ordered) - 1)
    frac = Decimal(str(pos - lo))
    return ordered[lo] * (Decimal(1) - frac) + ordered[hi] * frac


def _mc_path(values: list[Decimal], rng: random.Random) -> tuple[Decimal, Decimal]:
    sampled: list[Decimal] = []
    n = len(values)
    while len(sampled) < n:
        start = rng.randrange(0, max(1, n - MC_BLOCK_SIZE + 1))
        sampled.extend(values[start : start + MC_BLOCK_SIZE])
    sampled = sampled[:n]
    stats = _stats(sampled)
    return Decimal(str(stats["total_r"])), Decimal(str(stats["max_drawdown_r"]))


def _monte_carlo(trades: list[Trade]) -> dict[str, Any]:
    values = [trade.corrected_net_010_r for trade in trades]
    rng = random.Random(MC_SEED)
    terminals: list[Decimal] = []
    drawdowns: list[Decimal] = []
    for _ in range(MC_PATHS):
        terminal, drawdown = _mc_path(values, rng)
        terminals.append(terminal)
        drawdowns.append(drawdown)

    positive_prob = Decimal(str(sum(value > 0 for value in terminals) / MC_PATHS))
    p05_terminal = _quantile(terminals, 0.05)
    p50_terminal = _quantile(terminals, 0.50)
    p95_terminal = _quantile(terminals, 0.95)
    p95_dd = _quantile(drawdowns, 0.95)
    p99_dd = _quantile(drawdowns, 0.99)
    passed = (
        positive_prob >= MC_MIN_POSITIVE_TERMINAL_PROB
        and p05_terminal > MC_MIN_P05_TERMINAL_R
        and p95_dd <= MC_MAX_P95_DD_R
        and p99_dd <= MC_MAX_P99_DD_R
    )
    return {
        "method": "CONTIGUOUS_BLOCK_BOOTSTRAP",
        "paths": MC_PATHS,
        "block_size": MC_BLOCK_SIZE,
        "seed": MC_SEED,
        "positive_terminal_probability": str(positive_prob),
        "terminal_r": {
            "p05": str(p05_terminal),
            "p50": str(p50_terminal),
            "p95": str(p95_terminal),
        },
        "max_drawdown_r": {"p95": str(p95_dd), "p99": str(p99_dd)},
        "gate": {
            "minimum_positive_terminal_probability": str(MC_MIN_POSITIVE_TERMINAL_PROB),
            "minimum_p05_terminal_r_exclusive": str(MC_MIN_P05_TERMINAL_R),
            "maximum_p95_drawdown_r": str(MC_MAX_P95_DD_R),
            "maximum_p99_drawdown_r": str(MC_MAX_P99_DD_R),
        },
        "pass": passed,
    }


def _stress(trades: list[Trade]) -> dict[str, Any]:
    scenarios: dict[str, Any] = {}
    all_pass = True
    for name, rule in STRESS_SCENARIOS.items():
        values = [
            trade.corrected_net_010_r - rule["extra_r"] * trade.risk_scale
            for trade in trades
        ]
        stats = _stats(values)
        pf_raw = stats["profit_factor"]
        pf = None if pf_raw is None else Decimal(str(pf_raw))
        dd = Decimal(str(stats["max_drawdown_r"]))
        total = Decimal(str(stats["total_r"]))
        passed = bool(
            total > 0
            and pf is not None
            and pf >= rule["min_pf"]
            and dd <= rule["max_dd"]
        )
        all_pass = all_pass and passed
        scenarios[name] = {
            "additional_friction_r_per_1r_risk": str(rule["extra_r"]),
            "stats": stats,
            "gate": {
                "total_must_be_positive": True,
                "minimum_pf": str(rule["min_pf"]),
                "maximum_dd_r": str(rule["max_dd"]),
            },
            "pass": passed,
        }
    return {
        "baseline_friction_already_in_candidate_r": "0.10",
        "scenarios": scenarios,
        "pass": all_pass,
    }


def _slippage(trades: list[Trade]) -> dict[str, Any]:
    scenarios: dict[str, Any] = {}
    all_pass = True
    for name, rule in SLIPPAGE_SCENARIOS.items():
        values: list[Decimal] = []
        for trade in trades:
            adverse = Decimal(str(rule[trade.exit_reason]))
            values.append(
                trade.corrected_net_010_r - adverse * trade.risk_scale
            )
        stats = _stats(values)
        pf_raw = stats["profit_factor"]
        pf = None if pf_raw is None else Decimal(str(pf_raw))
        dd = Decimal(str(stats["max_drawdown_r"]))
        total = Decimal(str(stats["total_r"]))
        passed = bool(
            total > 0
            and pf is not None
            and pf >= Decimal(str(rule["min_pf"]))
            and dd <= Decimal(str(rule["max_dd"]))
        )
        all_pass = all_pass and passed
        scenarios[name] = {
            "stats": stats,
            "gate": {
                "total_must_be_positive": True,
                "minimum_pf": str(rule["min_pf"]),
                "maximum_dd_r": str(rule["max_dd"]),
            },
            "pass": passed,
        }
    return {"scenarios": scenarios, "pass": all_pass}


def _group_stats(trades: list[Trade], field: str) -> dict[str, Any]:
    groups: dict[str, list[Decimal]] = {}
    for trade in trades:
        value = getattr(trade, field)
        key = "NONE" if value is None else str(value)
        groups.setdefault(key, []).append(trade.corrected_net_010_r)
    return {key: _stats(values) for key, values in sorted(groups.items())}


def _annual_members(
    trades: list[Trade],
) -> list[tuple[datetime, datetime, list[Trade]]]:
    result: list[tuple[datetime, datetime, list[Trade]]] = []
    for index in range(5):
        start = _add_months(WINDOW_OPEN, 12 * index)
        end = _add_months(start, 12)
        result.append(
            (
                start,
                end,
                [trade for trade in trades if start <= trade.entry_at < end],
            )
        )
    return result


def _robustness(
    trades: list[Trade],
    wfo: dict[str, Any],
    r43_report: dict[str, Any],
) -> dict[str, Any]:
    source_stats = _group_stats(trades, "source")
    family_trades = [trade for trade in trades if trade.family is not None]
    family_stats = _group_stats(family_trades, "family")

    source_pf_pass = all(
        stats["profit_factor"] is not None
        and Decimal(str(stats["profit_factor"])) >= ROBUST_MIN_SOURCE_PF
        for stats in source_stats.values()
    )
    positive_families = sum(
        Decimal(str(stats["total_r"])) > 0 for stats in family_stats.values()
    )

    loyo: list[dict[str, Any]] = []
    loyo_pass = True
    for index, (start, end, _members) in enumerate(_annual_members(trades)):
        remaining = [
            trade.corrected_net_010_r
            for trade in trades
            if not (start <= trade.entry_at < end)
        ]
        stats = _stats(remaining)
        pf_raw = stats["profit_factor"]
        pf = None if pf_raw is None else Decimal(str(pf_raw))
        passed = bool(
            Decimal(str(stats["total_r"])) > 0
            and pf is not None
            and pf >= ROBUST_MIN_LOYO_PF
        )
        loyo_pass = loyo_pass and passed
        loyo.append({
            "omitted_block": index + 1,
            "open": start.isoformat(),
            "close": end.isoformat(),
            "stats": stats,
            "pass": passed,
        })

    positive_annual = int(r43_report["selected"]["positive_annual_blocks"])
    positive_half_year = int(wfo["positive_blocks"])
    annual_exact_pass = positive_annual == ROBUST_REQUIRED_POSITIVE_ANNUAL_BLOCKS
    passed = bool(
        annual_exact_pass
        and positive_half_year >= ROBUST_MIN_POSITIVE_HALF_YEAR_BLOCKS
        and source_pf_pass
        and positive_families >= ROBUST_REQUIRED_POSITIVE_FAMILIES
        and loyo_pass
    )
    return {
        "positive_annual_blocks": positive_annual,
        "all_five_annual_blocks_positive": annual_exact_pass,
        "positive_half_year_blocks": positive_half_year,
        "source_stats": source_stats,
        "source_pf_pass": source_pf_pass,
        "family_stats": family_stats,
        "positive_families": positive_families,
        "leave_one_year_out": loyo,
        "gate": {
            "required_positive_annual_blocks": ROBUST_REQUIRED_POSITIVE_ANNUAL_BLOCKS,
            "minimum_positive_half_year_blocks": ROBUST_MIN_POSITIVE_HALF_YEAR_BLOCKS,
            "minimum_each_source_pf": str(ROBUST_MIN_SOURCE_PF),
            "required_positive_families": ROBUST_REQUIRED_POSITIVE_FAMILIES,
            "minimum_each_leave_one_year_out_pf": str(ROBUST_MIN_LOYO_PF),
        },
        "pass": passed,
    }


def run(
    r43_root: Path,
    r39_root: Path,
    freeze_root: Path,
    output: Path,
) -> dict[str, Any]:
    r43_report, freeze, trades = _load(r43_root, r39_root, freeze_root)

    baseline = _stats([trade.corrected_net_010_r for trade in trades])
    baseline_pass = bool(
        int(baseline["trades"]) == BASELINE_TRADES
        and Decimal(str(baseline["profit_factor"])) == BASELINE_PF
        and Decimal(str(baseline["max_drawdown_r"])) == BASELINE_DD
        and Decimal(str(baseline["total_r"])) == BASELINE_TOTAL
        and int(r43_report["selected"]["positive_annual_blocks"]) == 5
    )

    wfo = _wfo(trades)
    monte_carlo = _monte_carlo(trades)
    stress = _stress(trades)
    slippage = _slippage(trades)
    robustness = _robustness(trades, wfo, r43_report)

    gates = {
        "frozen_5y_baseline": baseline_pass,
        "freeze_binding": bool(freeze["governance"]["candidate_frozen"]),
        "five_of_five_annual_positive": bool(
            robustness["all_five_annual_blocks_positive"]
        ),
        "wfo": bool(wfo["pass"]),
        "monte_carlo": bool(monte_carlo["pass"]),
        "stress": bool(stress["pass"]),
        "slippage": bool(slippage["pass"]),
        "robustness": bool(robustness["pass"]),
    }
    certified = all(gates.values())

    report: dict[str, Any] = {
        "schema": "qore.turtle_soup_gbpusd.r45_final_certification_suite.v1",
        "identity": IDENTITY,
        "candidate_identity": CANDIDATE_IDENTITY,
        "source_binding": {
            "r43_run_id": R43_RUN_ID,
            "r43_artifact_id": R43_ARTIFACT_ID,
            "r43_artifact_digest": R43_ARTIFACT_DIGEST,
            "r43_git_sha": R43_GIT_SHA,
            "r43_report_sha256": R43_REPORT_SHA256,
            "r43_trades_sha256": R43_TRADES_SHA256,
            "r39_run_id": R39_RUN_ID,
            "r39_artifact_id": R39_ARTIFACT_ID,
            "r39_git_sha": R39_GIT_SHA,
            "freeze_run_id": FREEZE_RUN_ID,
            "freeze_artifact_id": FREEZE_ARTIFACT_ID,
            "freeze_artifact_digest": FREEZE_ARTIFACT_DIGEST,
        },
        "certification_contract": {
            "internal_qore_research_certification": True,
            "external_regulatory_certification": False,
            "broker_or_prop_firm_endorsement": False,
            "rules_reoptimized_after_r44_freeze": False,
            "fresh_holdout_consumed": False,
            "all_five_annual_blocks_required_positive": True,
            "fail_closed": True,
        },
        "frozen_5y": {
            **baseline,
            "positive_annual_blocks": int(
                r43_report["selected"]["positive_annual_blocks"]
            ),
            "pass": baseline_pass,
        },
        "wfo": wfo,
        "monte_carlo": monte_carlo,
        "stress": stress,
        "slippage": slippage,
        "robustness": robustness,
        "gate_results": gates,
        "certification": {
            "status": "TRADER_CERTIFIED" if certified else "NOT_CERTIFIED",
            "certified": certified,
            "scope": "QORE_INTERNAL_RESEARCH_CERTIFICATION",
            "candidate": "TURTLE_SOUP_GBPUSD_R43",
        },
        "governance": {
            "fresh_holdout_consumed": False,
            "demo_eligible": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
            "merge_authorized": False,
            "certification_does_not_authorize_live_capital": True,
        },
    }

    output.mkdir(parents=True, exist_ok=True)
    (output / "r45-final-certification-report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    manifest = {
        "candidate": "TURTLE_SOUP_GBPUSD_R43",
        "status": report["certification"]["status"],
        "all_gates_pass": certified,
        "gate_results": gates,
        "five_of_five_annual_positive": bool(
            robustness["all_five_annual_blocks_positive"]
        ),
        "source_r43_run_id": R43_RUN_ID,
        "source_r43_artifact_id": R43_ARTIFACT_ID,
        "source_freeze_run_id": FREEZE_RUN_ID,
        "source_freeze_artifact_id": FREEZE_ARTIFACT_ID,
        "fresh_holdout_consumed": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
    }
    (output / "r45-certification-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    )
    return report


def main() -> None:
    if len(sys.argv) != 5:
        raise SystemExit(
            "usage: module R43_ARTIFACT_ROOT R39_ARTIFACT_ROOT FREEZE_ROOT OUTPUT_DIR"
        )
    print(
        json.dumps(
            run(
                Path(sys.argv[1]),
                Path(sys.argv[2]),
                Path(sys.argv[3]),
                Path(sys.argv[4]),
            ),
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
