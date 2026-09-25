"""VT08 Core Stack robustness suite using VT31/Core validation architecture."""
from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from typing import Final

from qore.infrastructure.trader_lab.vt08_cognitive_core_stack_dev_v1 import (
    CoreStackTrade,
    stack_rows,
)
from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_backtest_v1 import (
    ExpansionTrade,
    metrics,
)

SCHEMA: Final = "qore.trader_lab.vt08_cognitive_core_stack_robustness.v1"
SURVIVOR_MARKETS: Final = ("EURJPY", "NZDUSD", "CADJPY")
MC_PATHS: Final = 10_000
MC_BLOCK_LENGTH: Final = 5
EXTRA_COSTS_R: Final = (
    Decimal("0.01"),
    Decimal("0.02"),
    Decimal("0.05"),
)
MIN_SAMPLE: Final = 60
MIN_PF: Final = Decimal("1.80")
MAX_DD_R: Final = Decimal("6")
MIN_MC_POSITIVE: Final = Decimal("0.90")
MAX_MC_P95_DD_R: Final = Decimal("15")


def _managed(rows: tuple[CoreStackTrade, ...]) -> tuple[ExpansionTrade, ...]:
    return tuple(row.as_trade() for row in rows)


def _d(payload: dict[str, object], key: str) -> Decimal:
    value = payload[key]
    if value is None:
        raise ValueError(f"{key} is unavailable")
    return Decimal(str(value))


def _chronological_blocks(
    rows: tuple[CoreStackTrade, ...],
) -> list[dict[str, object]]:
    count = len(rows)
    boundaries = (0, count // 3, (2 * count) // 3, count)
    result: list[dict[str, object]] = []
    for index in range(3):
        block = rows[boundaries[index] : boundaries[index + 1]]
        block_metrics = metrics(_managed(block))
        result.append(
            {
                "block": index + 1,
                "trade_count": len(block),
                "start_signal_at": (
                    None if not block else block[0].baseline.signal_at.isoformat()
                ),
                "end_signal_at": (
                    None if not block else block[-1].baseline.signal_at.isoformat()
                ),
                "metrics": block_metrics,
                "positive": (
                    bool(block)
                    and _d(block_metrics, "total_r") > 0
                    and _d(block_metrics, "mean_r") > 0
                ),
            }
        )
    return result


def _max_drawdown(values: tuple[Decimal, ...]) -> Decimal:
    equity = Decimal(0)
    peak = Decimal(0)
    maximum = Decimal(0)
    for value in values:
        equity += value
        peak = max(peak, equity)
        maximum = max(maximum, peak - equity)
    return maximum


def monte_carlo(
    rows: tuple[CoreStackTrade, ...],
    *,
    market: str,
) -> dict[str, object]:
    values = tuple(row.managed_r for row in rows)
    if not values:
        raise ValueError("Monte Carlo requires terminal rows")
    n = len(values)
    terminals: list[Decimal] = []
    drawdowns: list[Decimal] = []
    domain = (
        b"qore-vt08-core-stack-robustness-v1:"
        + market.encode("ascii")
    )
    for path_index in range(MC_PATHS):
        sampled: list[Decimal] = []
        block_index = 0
        while len(sampled) < n:
            digest = hashlib.sha256(
                domain
                + b":"
                + str(path_index).encode("ascii")
                + b":"
                + str(block_index).encode("ascii")
            ).digest()
            start = int.from_bytes(digest, "big") % n
            sampled.extend(
                values[(start + offset) % n]
                for offset in range(MC_BLOCK_LENGTH)
            )
            block_index += 1
        path = tuple(sampled[:n])
        terminals.append(sum(path, Decimal(0)))
        drawdowns.append(_max_drawdown(path))

    terminals.sort()
    drawdowns.sort()
    return {
        "algorithm": "sha256-moving-block-bootstrap-v1",
        "paths": MC_PATHS,
        "block_length": MC_BLOCK_LENGTH,
        "positive_terminal_probability": format(
            Decimal(sum(item > 0 for item in terminals)) / Decimal(MC_PATHS),
            "f",
        ),
        "p05_terminal_r": format(
            terminals[(MC_PATHS - 1) * 5 // 100],
            "f",
        ),
        "p50_terminal_r": format(
            terminals[(MC_PATHS - 1) * 50 // 100],
            "f",
        ),
        "p95_max_drawdown_r": format(
            drawdowns[(MC_PATHS - 1) * 95 // 100],
            "f",
        ),
        "p99_max_drawdown_r": format(
            drawdowns[(MC_PATHS - 1) * 99 // 100],
            "f",
        ),
    }


def _stress(
    rows: tuple[CoreStackTrade, ...],
    cost: Decimal,
) -> dict[str, object]:
    stressed = tuple(
        replace(
            row.as_trade(),
            r_multiple=row.managed_r - cost,
        )
        for row in rows
    )
    return metrics(stressed)


def _remove_top(
    rows: tuple[CoreStackTrade, ...],
    count: int,
) -> dict[str, object]:
    ordered = sorted(
        range(len(rows)),
        key=lambda index: rows[index].managed_r,
        reverse=True,
    )
    removed = set(ordered[:count])
    retained = tuple(
        row.as_trade()
        for index, row in enumerate(rows)
        if index not in removed
    )
    return metrics(retained)


def _group(
    rows: tuple[CoreStackTrade, ...],
    *,
    field: str,
) -> dict[str, object]:
    if field == "anchor":
        values = sorted({str(row.baseline.anchor_hour_ny) for row in rows})
        return {
            value: metrics(
                tuple(
                    row.as_trade()
                    for row in rows
                    if str(row.baseline.anchor_hour_ny) == value
                )
            )
            for value in values
        }
    if field == "side":
        values = sorted({row.baseline.side.value for row in rows})
        return {
            value: metrics(
                tuple(
                    row.as_trade()
                    for row in rows
                    if row.baseline.side.value == value
                )
            )
            for value in values
        }
    raise ValueError(field)


def evaluate(path: Path) -> dict[str, object]:
    rows = stack_rows(path)
    if not rows:
        raise ValueError("Core Stack robustness requires rows")
    market = rows[0].baseline.symbol
    if market not in SURVIVOR_MARKETS:
        raise ValueError("market did not pass frozen fresh screen")

    full = metrics(_managed(rows))
    blocks = _chronological_blocks(rows)
    mc = monte_carlo(rows, market=market)
    stress = {
        format(cost, "f"): _stress(rows, cost)
        for cost in EXTRA_COSTS_R
    }
    top1 = _remove_top(rows, 1)
    top5 = _remove_top(rows, min(5, len(rows)))
    pf = full["profit_factor"]
    stress_002 = stress["0.02"]

    gates = {
        "sample_at_least_60": len(rows) >= MIN_SAMPLE,
        "profit_factor_at_least_1_80": (
            pf is not None and Decimal(str(pf)) >= MIN_PF
        ),
        "total_positive": _d(full, "total_r") > 0,
        "observed_dd_at_most_6r": _d(full, "max_drawdown_r") <= MAX_DD_R,
        "all_three_blocks_positive": all(bool(item["positive"]) for item in blocks),
        "mc_positive_at_least_0_90": (
            Decimal(str(mc["positive_terminal_probability"])) >= MIN_MC_POSITIVE
        ),
        "mc_p95_dd_at_most_15r": (
            Decimal(str(mc["p95_max_drawdown_r"])) <= MAX_MC_P95_DD_R
        ),
        "stress_002_positive_pf_gt_1": (
            _d(stress_002, "total_r") > 0
            and stress_002["profit_factor"] is not None
            and Decimal(str(stress_002["profit_factor"])) > 1
        ),
        "remove_top_1_positive_pf_gt_1": (
            _d(top1, "total_r") > 0
            and top1["profit_factor"] is not None
            and Decimal(str(top1["profit_factor"])) > 1
        ),
    }
    passed = all(gates.values())

    return {
        "schema": SCHEMA,
        "market": market,
        "candidate": "VT08_COGNITIVE_CORE_STACK_DEV_V1",
        "evidence_status": "CONSUMED_EXTENDED_VALIDATION",
        "trade_count": len(rows),
        "full_metrics": full,
        "chronological_blocks": blocks,
        "monte_carlo": mc,
        "stress": stress,
        "extreme_winner_dependence": {
            "remove_top_1": top1,
            "remove_top_5": top5,
        },
        "by_anchor_ny": _group(rows, field="anchor"),
        "by_side": _group(rows, field="side"),
        "gates": gates,
        "robustness_pass": passed,
        "decision": (
            "ROBUSTNESS_PASS"
            if passed
            else "REJECTED_ROBUSTNESS_GATES"
        ),
        "governance": {
            "parameter_scan": False,
            "retuning_inside_suite": False,
            "freshness_claimed": False,
            "market_selection_inside_suite": False,
            "entry_changed": False,
            "initial_stop_changed": False,
            "target_changed": False,
            "live_authorized": False,
            "production_authorized": False,
            "real_capital_authorized": False,
        },
    }


def to_json(path: Path) -> str:
    return json.dumps(evaluate(path), sort_keys=True, separators=(",", ":"))
