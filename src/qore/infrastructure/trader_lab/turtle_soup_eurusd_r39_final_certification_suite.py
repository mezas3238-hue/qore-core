"""R39 final certification suite for frozen EURUSD R38.

Inputs:
- exact official R38 corrected 5Y artifact;
- exact R38 freeze artifact;
- no rule changes;
- no fresh-holdout consumption.

Suite:
1. fixed-rule walk-forward stability;
2. block-bootstrap Monte Carlo;
3. additional friction stress;
4. exit-type slippage stress;
5. temporal/source/subfamily robustness;
6. fail-closed internal QORE certification.

This is an internal QORE research certification, not a broker, prop-firm,
regulator, or exchange endorsement.
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
from typing import Any

IDENTITY = "TURTLE_SOUP_EURUSD_R39_FINAL_CERTIFICATION_SUITE_V1"
CANDIDATE_IDENTITY = "TURTLE_SOUP_EURUSD_R38_STRUCTURAL_RISK_CANDIDATE_001"

R38_RUN_ID = 35327677519
R38_ARTIFACT_ID = 10539313228
R38_ARTIFACT_DIGEST = (
    "sha256:2fc7246d9aac4b7c281301e94b71ff336d3f0967859a46a33f3fa62e4fe74e00"
)
R38_GIT_SHA = "324fb91d44a6fa328e66de2e22ace7386630c7aa"
R38_REPORT_SHA256 = (
    "baafaaf385a91b17d9427ba56dc563ab30e453f065fe84d88436a7ba6c402b27"
)
R38_TRADES_SHA256 = (
    "61746b6866dce66c2b522be56016c5d5b786821704f71f947b4cf2337aeefc9a"
)

FREEZE_RUN_ID = 35327938780
FREEZE_ARTIFACT_ID = 10539358304
FREEZE_ARTIFACT_DIGEST = (
    "sha256:1d0c0525ac036128aef369bf6c2cdfbdc53b0b9496a5b6025adad54ec1524415"
)
FREEZE_MANIFEST_SHA256 = (
    "45cea7e39a89016e7a7ed870a3b43c0d90ad8eafc4b5eba214d4a22ac0347c28"
)

WINDOW_OPEN = datetime.fromisoformat("2021-09-17T00:00:00+00:00")
WINDOW_CLOSE = datetime.fromisoformat("2026-09-17T00:00:00+00:00")

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
        "STOP_FIRST": Decimal("0.020"),
        "GAP_STOP": Decimal("0.030"),
        "TIME_24H": Decimal("0.010"),
        "min_pf": Decimal("1.35"),
        "max_dd": Decimal("12.0"),
    },
    "ADVERSE": {
        "TARGET": Decimal("0.010"),
        "STOP": Decimal("0.050"),
        "TRAIL_STOP": Decimal("0.050"),
        "STOP_FIRST": Decimal("0.050"),
        "GAP_STOP": Decimal("0.080"),
        "TIME_24H": Decimal("0.025"),
        "min_pf": Decimal("1.30"),
        "max_dd": Decimal("14.0"),
    },
    "SEVERE": {
        "TARGET": Decimal("0.020"),
        "STOP": Decimal("0.100"),
        "TRAIL_STOP": Decimal("0.100"),
        "STOP_FIRST": Decimal("0.100"),
        "GAP_STOP": Decimal("0.150"),
        "TIME_24H": Decimal("0.050"),
        "min_pf": Decimal("1.20"),
        "max_dd": Decimal("15.0"),
    },
}

ROBUST_MIN_POSITIVE_ANNUAL_BLOCKS = 4
ROBUST_MIN_POSITIVE_HALF_YEAR_BLOCKS = 6
ROBUST_MIN_SOURCE_PF = Decimal("1.30")
ROBUST_MIN_POSITIVE_FAMILIES = 3
ROBUST_MIN_LOYO_PF = Decimal("1.30")


@dataclass(frozen=True, slots=True)
class Trade:
    entry_at: datetime
    exit_at: datetime
    source: str
    family: str | None
    exit_reason: str
    risk_scale: Decimal
    scaled_net_010_r: Decimal


def _single(root: Path, name: str) -> Path:
    matches = list(root.rglob(name))
    if len(matches) != 1:
        raise ValueError(f"expected exactly one {name}, got {len(matches)}")
    return matches[0]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _verify_freeze(root: Path) -> dict[str, Any]:
    path = _single(root, "r38-candidate-freeze-manifest.json")
    if _sha256(path) != FREEZE_MANIFEST_SHA256:
        raise ValueError("R38 freeze manifest hash drift")
    freeze: dict[str, Any] = json.loads(path.read_text())
    if freeze["identity"] != CANDIDATE_IDENTITY:
        raise ValueError("R38 freeze candidate identity drift")
    if freeze["status"] != "FROZEN_FOR_FINAL_ROBUSTNESS":
        raise ValueError("R38 candidate not frozen for final robustness")
    if freeze["source"]["run_id"] != R38_RUN_ID:
        raise ValueError("R38 freeze run binding drift")
    if freeze["source"]["artifact_id"] != R38_ARTIFACT_ID:
        raise ValueError("R38 freeze artifact binding drift")
    if freeze["source"]["artifact_digest"] != R38_ARTIFACT_DIGEST:
        raise ValueError("R38 freeze artifact digest drift")
    if freeze["source"]["git_sha"] != R38_GIT_SHA:
        raise ValueError("R38 freeze git binding drift")
    if freeze["source"]["report_sha256"] != R38_REPORT_SHA256:
        raise ValueError("R38 freeze report binding drift")
    if freeze["next_stage"]["fresh_holdout_status"] != "SEALED_UNTOUCHED":
        raise ValueError("fresh holdout seal drift")
    if freeze["governance"]["fresh_holdout_consumed"] is not False:
        raise ValueError("fresh holdout consumption drift")
    if freeze["governance"]["candidate_frozen"] is not True:
        raise ValueError("candidate freeze drift")
    if freeze["governance"]["candidate_certified"] is not False:
        raise ValueError("candidate certification state drift")
    return freeze


def _load(
    r38_root: Path,
    freeze_root: Path,
) -> tuple[dict[str, Any], dict[str, Any], list[Trade]]:
    freeze = _verify_freeze(freeze_root)
    report_path = _single(r38_root, "r38-5y-correction-report.json")
    trades_path = _single(r38_root, "r38-5y-corrected-trades.jsonl")
    git_path = _single(r38_root, "git-sha.txt")

    if _sha256(report_path) != R38_REPORT_SHA256:
        raise ValueError("R38 report hash drift")
    if _sha256(trades_path) != R38_TRADES_SHA256:
        raise ValueError("R38 trades hash drift")
    if git_path.read_text().strip() != R38_GIT_SHA:
        raise ValueError("R38 git binding drift")

    report = json.loads(report_path.read_text())
    if report["identity"] != "TURTLE_SOUP_EURUSD_R38_5Y_STRUCTURAL_RISK_CORRECTION_V1":
        raise ValueError("unexpected R38 identity")
    if report["result"]["acceptance_pass"] is not True:
        raise ValueError("R38 did not pass 5Y correction gate")
    if report["governance"]["fresh_holdout_consumed"] is not False:
        raise ValueError("fresh holdout drift")
    if report["correction_contract"]["signals_suppressed"] is not False:
        raise ValueError("signal suppression drift")
    if report["correction_contract"]["structural_risk_overlay_only"] is not True:
        raise ValueError("R38 correction type drift")

    if freeze["consumed_5y_result"]["trades"] != report["result"]["trades"]:
        raise ValueError("freeze/report trade count mismatch")
    if (
        freeze["consumed_5y_result"]["profit_factor_scaled_net_010"]
        != report["result"]["profit_factor_scaled_net_010"]
    ):
        raise ValueError("freeze/report PF mismatch")
    if (
        freeze["consumed_5y_result"]["max_drawdown_scaled_r"]
        != report["result"]["max_drawdown_scaled_r"]
    ):
        raise ValueError("freeze/report DD mismatch")

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
                    source=str(row["source"]),
                    family=None if row["family"] is None else str(row["family"]),
                    exit_reason=str(row["exit_reason"]),
                    risk_scale=Decimal(str(row["risk_scale"])),
                    scaled_net_010_r=Decimal(str(row["scaled_net_010_r"])),
                )
            )
    if len(trades) != 863:
        raise ValueError("R38 trade-count drift")
    return report, freeze, trades


def _pf(values: list[Decimal]) -> Decimal | None:
    gains = sum((value for value in values if value > 0), Decimal(0))
    losses = -sum((value for value in values if value < 0), Decimal(0))
    return None if losses == 0 else gains / losses


def _stats(values: list[Decimal]) -> dict[str, Any]:
    equity = Decimal(0)
    peak = Decimal(0)
    max_dd = Decimal(0)
    max_losing = 0
    losing = 0
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
        members = [trade for trade in trades if start <= trade.entry_at < end]
        stats = _stats([trade.scaled_net_010_r for trade in members])
        blocks.append(
            {
                "index": index + 1,
                "open": start.isoformat(),
                "close": end.isoformat(),
                **stats,
                "positive": Decimal(str(stats["total_r"])) > 0,
            }
        )

    aggregate = _stats([trade.scaled_net_010_r for trade in trades])
    positive = sum(bool(block["positive"]) for block in blocks)
    worst_total = min(Decimal(str(block["total_r"])) for block in blocks)
    aggregate_pf = Decimal(str(aggregate["profit_factor"]))
    passed = (
        positive >= WFO_MIN_POSITIVE_BLOCKS
        and aggregate_pf >= WFO_MIN_AGGREGATE_PF
        and worst_total > WFO_WORST_BLOCK_TOTAL_FLOOR_R
    )
    return {
        "method": "FIXED_RULE_WALK_FORWARD_STABILITY_NO_REOPTIMIZATION",
        "blocks": blocks,
        "positive_blocks": positive,
        "aggregate": aggregate,
        "worst_block_total_r": str(worst_total),
        "gate": {
            "minimum_positive_blocks": WFO_MIN_POSITIVE_BLOCKS,
            "minimum_aggregate_pf": str(WFO_MIN_AGGREGATE_PF),
            "worst_block_total_floor_r": str(WFO_WORST_BLOCK_TOTAL_FLOOR_R),
        },
        "pass": passed,
    }


def _quantile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("quantile requires values")
    pos = (len(ordered) - 1) * q
    low = int(pos)
    high = min(low + 1, len(ordered) - 1)
    weight = pos - low
    return ordered[low] * (1.0 - weight) + ordered[high] * weight


def _mc_path(values: list[float], rng: random.Random) -> tuple[float, float]:
    n = len(values)
    generated: list[float] = []
    max_start = n - MC_BLOCK_SIZE
    while len(generated) < n:
        start = rng.randint(0, max_start)
        generated.extend(values[start : start + MC_BLOCK_SIZE])
    generated = generated[:n]

    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    for value in generated:
        equity += value
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
    return equity, max_dd


def _monte_carlo(trades: list[Trade]) -> dict[str, Any]:
    values = [float(trade.scaled_net_010_r) for trade in trades]
    rng = random.Random(MC_SEED)
    terminals: list[float] = []
    drawdowns: list[float] = []
    for _ in range(MC_PATHS):
        terminal, drawdown = _mc_path(values, rng)
        terminals.append(terminal)
        drawdowns.append(drawdown)

    positive_prob = Decimal(str(sum(value > 0 for value in terminals) / MC_PATHS))
    p05_terminal = Decimal(str(_quantile(terminals, 0.05)))
    p50_terminal = Decimal(str(_quantile(terminals, 0.50)))
    p95_terminal = Decimal(str(_quantile(terminals, 0.95)))
    p95_dd = Decimal(str(_quantile(drawdowns, 0.95)))
    p99_dd = Decimal(str(_quantile(drawdowns, 0.99)))
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
            "minimum_positive_terminal_probability": str(
                MC_MIN_POSITIVE_TERMINAL_PROB
            ),
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
            trade.scaled_net_010_r - rule["extra_r"] * trade.risk_scale
            for trade in trades
        ]
        stats = _stats(values)
        pf = Decimal(str(stats["profit_factor"]))
        dd = Decimal(str(stats["max_drawdown_r"]))
        total = Decimal(str(stats["total_r"]))
        passed = total > 0 and pf >= rule["min_pf"] and dd <= rule["max_dd"]
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
        "baseline_friction_already_in_r38_r": "0.10",
        "scenarios": scenarios,
        "pass": all_pass,
    }


def _slippage(trades: list[Trade]) -> dict[str, Any]:
    scenarios: dict[str, Any] = {}
    all_pass = True
    for name, rule in SLIPPAGE_SCENARIOS.items():
        values: list[Decimal] = []
        for trade in trades:
            if trade.exit_reason not in rule:
                raise ValueError(f"unsupported exit reason {trade.exit_reason}")
            adverse = Decimal(str(rule[trade.exit_reason]))
            values.append(trade.scaled_net_010_r - adverse * trade.risk_scale)
        stats = _stats(values)
        pf = Decimal(str(stats["profit_factor"]))
        dd = Decimal(str(stats["max_drawdown_r"]))
        total = Decimal(str(stats["total_r"]))
        passed = total > 0 and pf >= rule["min_pf"] and dd <= rule["max_dd"]
        all_pass = all_pass and passed
        scenarios[name] = {
            "adverse_r_by_exit": {
                exit_reason: str(rule[exit_reason])
                for exit_reason in (
                    "TARGET",
                    "STOP",
                    "TRAIL_STOP",
                    "STOP_FIRST",
                    "GAP_STOP",
                    "TIME_24H",
                )
            },
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
        groups.setdefault(key, []).append(trade.scaled_net_010_r)
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
    r38_report: dict[str, Any],
) -> dict[str, Any]:
    source_stats = _group_stats(trades, "source")
    family_stats = _group_stats(
        [trade for trade in trades if trade.family is not None],
        "family",
    )

    source_pf_pass = all(
        stats["profit_factor"] is not None
        and Decimal(str(stats["profit_factor"])) >= ROBUST_MIN_SOURCE_PF
        for stats in source_stats.values()
    )
    positive_families = sum(
        Decimal(str(stats["total_r"])) > 0 for stats in family_stats.values()
    )

    annual = _annual_members(trades)
    loyo: list[dict[str, Any]] = []
    loyo_pass = True
    for index, (start, end, _members) in enumerate(annual):
        remaining = [
            trade.scaled_net_010_r
            for trade in trades
            if not (start <= trade.entry_at < end)
        ]
        stats = _stats(remaining)
        pf_raw = stats["profit_factor"]
        pf = None if pf_raw is None else Decimal(str(pf_raw))
        passed = (
            Decimal(str(stats["total_r"])) > 0
            and pf is not None
            and pf >= ROBUST_MIN_LOYO_PF
        )
        loyo_pass = loyo_pass and passed
        loyo.append(
            {
                "omitted_block": index + 1,
                "open": start.isoformat(),
                "close": end.isoformat(),
                "stats": stats,
                "pass": passed,
            }
        )

    positive_annual = int(r38_report["result"]["positive_annual_blocks"])
    positive_half_year = int(wfo["positive_blocks"])
    passed = (
        positive_annual >= ROBUST_MIN_POSITIVE_ANNUAL_BLOCKS
        and positive_half_year >= ROBUST_MIN_POSITIVE_HALF_YEAR_BLOCKS
        and source_pf_pass
        and positive_families >= ROBUST_MIN_POSITIVE_FAMILIES
        and loyo_pass
    )
    return {
        "positive_annual_blocks": positive_annual,
        "positive_half_year_blocks": positive_half_year,
        "source_stats": source_stats,
        "source_pf_pass": source_pf_pass,
        "family_stats": family_stats,
        "positive_families": positive_families,
        "leave_one_year_out": loyo,
        "gate": {
            "minimum_positive_annual_blocks": ROBUST_MIN_POSITIVE_ANNUAL_BLOCKS,
            "minimum_positive_half_year_blocks": ROBUST_MIN_POSITIVE_HALF_YEAR_BLOCKS,
            "minimum_each_source_pf": str(ROBUST_MIN_SOURCE_PF),
            "minimum_positive_families": ROBUST_MIN_POSITIVE_FAMILIES,
            "minimum_each_leave_one_year_out_pf": str(ROBUST_MIN_LOYO_PF),
        },
        "pass": passed,
    }


def run(
    r38_root: Path,
    freeze_root: Path,
    output: Path,
) -> dict[str, Any]:
    r38_report, freeze, trades = _load(r38_root, freeze_root)

    wfo = _wfo(trades)
    monte_carlo = _monte_carlo(trades)
    stress = _stress(trades)
    slippage = _slippage(trades)
    robustness = _robustness(trades, wfo, r38_report)

    gates = {
        "r38_5y": bool(r38_report["result"]["acceptance_pass"]),
        "freeze_binding": bool(freeze["governance"]["candidate_frozen"]),
        "wfo": bool(wfo["pass"]),
        "monte_carlo": bool(monte_carlo["pass"]),
        "stress": bool(stress["pass"]),
        "slippage": bool(slippage["pass"]),
        "robustness": bool(robustness["pass"]),
    }
    certified = all(gates.values())

    report: dict[str, Any] = {
        "schema": "qore.turtle_soup_eurusd.r39_final_certification_suite.v1",
        "identity": IDENTITY,
        "candidate_identity": CANDIDATE_IDENTITY,
        "source_binding": {
            "r38_run_id": R38_RUN_ID,
            "r38_artifact_id": R38_ARTIFACT_ID,
            "r38_artifact_digest": R38_ARTIFACT_DIGEST,
            "r38_git_sha": R38_GIT_SHA,
            "r38_report_sha256": R38_REPORT_SHA256,
            "r38_trades_sha256": R38_TRADES_SHA256,
            "freeze_run_id": FREEZE_RUN_ID,
            "freeze_artifact_id": FREEZE_ARTIFACT_ID,
            "freeze_artifact_digest": FREEZE_ARTIFACT_DIGEST,
            "freeze_manifest_sha256": FREEZE_MANIFEST_SHA256,
        },
        "certification_contract": {
            "internal_qore_research_certification": True,
            "external_regulatory_certification": False,
            "broker_or_prop_firm_endorsement": False,
            "rules_reoptimized_after_r38_freeze": False,
            "fresh_holdout_consumed": False,
            "all_thresholds_predeclared_in_source": True,
            "fail_closed": True,
        },
        "r38_5y": {
            "trades": r38_report["result"]["trades"],
            "total_scaled_net_010_r": r38_report["result"]["total_scaled_net_010_r"],
            "profit_factor_scaled_net_010": r38_report["result"][
                "profit_factor_scaled_net_010"
            ],
            "max_drawdown_scaled_r": r38_report["result"][
                "max_drawdown_scaled_r"
            ],
            "positive_annual_blocks": r38_report["result"][
                "positive_annual_blocks"
            ],
            "pass": r38_report["result"]["acceptance_pass"],
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
            "candidate": "TURTLE_SOUP_EURUSD_R38",
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
    (output / "r39-final-certification-report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )

    manifest = {
        "candidate": "TURTLE_SOUP_EURUSD_R38",
        "status": report["certification"]["status"],
        "all_gates_pass": certified,
        "gate_results": gates,
        "source_r38_run_id": R38_RUN_ID,
        "source_r38_artifact_id": R38_ARTIFACT_ID,
        "source_freeze_run_id": FREEZE_RUN_ID,
        "source_freeze_artifact_id": FREEZE_ARTIFACT_ID,
        "fresh_holdout_consumed": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
    }
    (output / "r39-certification-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    )
    return report


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit("usage: module R38_ARTIFACT_ROOT FREEZE_ROOT OUTPUT_DIR")
    print(
        json.dumps(
            run(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])),
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
