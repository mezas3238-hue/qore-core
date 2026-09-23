"""Extended five-year validation for the frozen VT08 EURJPY Core Stack."""
from __future__ import annotations

import json
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from typing import Final, cast

from qore.infrastructure.trader_lab.vt08_cognitive_core_stack_dev_v1 import (
    CoreStackTrade,
    stack_rows,
)
from qore.infrastructure.trader_lab.vt08_cognitive_core_stack_robustness_v1 import (
    _remove_top,
    _stress,
    monte_carlo,
)
from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_backtest_v1 import (
    load_market_evidence,
    metrics,
)

SCHEMA: Final = "qore.trader_lab.vt08_eurjpy_core_stack_5y_validation.v1"
MARKET: Final = "EURJPY"
MIN_SAMPLE: Final = 100
MIN_PF: Final = Decimal("1.50")
MAX_DD_R: Final = Decimal("6")
ROLLING_MIN_SAMPLE: Final = 30
ROLLING_MIN_PF: Final = Decimal("1.20")
ROLLING_MAX_DD_R: Final = Decimal("8")
MC_MIN_POSITIVE: Final = Decimal("0.90")
MC_MAX_P95_DD_R: Final = Decimal("15")


def _d(payload: dict[str, object], key: str) -> Decimal:
    raw = payload[key]
    if raw is None:
        raise ValueError(f"{key} is unavailable")
    return Decimal(str(raw))


def _managed(rows: tuple[CoreStackTrade, ...]) -> tuple:
    return tuple(row.as_trade() for row in rows)


def _window(
    rows: tuple[CoreStackTrade, ...],
    *,
    start,
    end,
) -> dict[str, object]:
    selected = tuple(
        row
        for row in rows
        if start <= row.baseline.signal_at < end
    )
    result = metrics(_managed(selected))
    return {
        "start": start.isoformat(),
        "end_exclusive": end.isoformat(),
        "trade_count": len(selected),
        "metrics": result,
    }


def evaluate(path: Path) -> dict[str, object]:
    _fingerprint, symbol, checked_at, software_sha, bars = load_market_evidence(path)
    if symbol != MARKET:
        raise ValueError("5Y validation is frozen to EURJPY")
    rows = stack_rows(path)
    if not rows:
        raise ValueError("5Y validation emitted no Core Stack trades")

    m15 = tuple(bar for bar in bars if True)
    coverage_start = min(bar.opened_at for bar in m15)
    coverage_end = max(bar.closed_at for bar in m15)
    full = metrics(_managed(rows))

    annual_blocks: list[dict[str, object]] = []
    for index in range(5):
        start = coverage_start + timedelta(days=365 * index)
        end = min(start + timedelta(days=365), coverage_end)
        item = _window(rows, start=start, end=end)
        item["block"] = index + 1
        item["positive"] = (
            item["trade_count"] > 0
            and _d(cast(dict[str, object], item["metrics"]), "total_r") > 0
            and _d(cast(dict[str, object], item["metrics"]), "mean_r") > 0
        )
        annual_blocks.append(item)

    rolling: list[dict[str, object]] = []
    for index in range(4):
        start = coverage_start + timedelta(days=365 * index)
        end = start + timedelta(days=730)
        item = _window(rows, start=start, end=end)
        m = cast(dict[str, object], item["metrics"])
        pf = m["profit_factor"]
        gates = {
            "sample_at_least_30": int(item["trade_count"]) >= ROLLING_MIN_SAMPLE,
            "pf_at_least_1_20": (
                pf is not None and Decimal(str(pf)) >= ROLLING_MIN_PF
            ),
            "total_positive": _d(m, "total_r") > 0,
            "dd_at_most_8r": _d(m, "max_drawdown_r") <= ROLLING_MAX_DD_R,
        }
        item["window"] = index + 1
        item["gates"] = gates
        item["passes"] = all(gates.values())
        rolling.append(item)

    mc = monte_carlo(rows, market=MARKET)
    stress_001 = _stress(rows, Decimal("0.01"))
    stress_002 = _stress(rows, Decimal("0.02"))
    stress_005 = _stress(rows, Decimal("0.05"))
    top1 = _remove_top(rows, 1)
    top5 = _remove_top(rows, min(5, len(rows)))
    pf = full["profit_factor"]

    gates = {
        "sample_at_least_100": len(rows) >= MIN_SAMPLE,
        "profit_factor_at_least_1_50": (
            pf is not None and Decimal(str(pf)) >= MIN_PF
        ),
        "total_positive": _d(full, "total_r") > 0,
        "observed_dd_at_most_6r": _d(full, "max_drawdown_r") <= MAX_DD_R,
        "all_five_365d_blocks_positive": all(
            bool(item["positive"]) for item in annual_blocks
        ),
        "all_four_rolling_730d_windows_pass": all(
            bool(item["passes"]) for item in rolling
        ),
        "mc_positive_at_least_0_90": (
            Decimal(str(mc["positive_terminal_probability"])) >= MC_MIN_POSITIVE
        ),
        "mc_p95_dd_at_most_15r": (
            Decimal(str(mc["p95_max_drawdown_r"])) <= MC_MAX_P95_DD_R
        ),
        "stress_002_positive_pf_1_20_dd_7": (
            _d(stress_002, "total_r") > 0
            and stress_002["profit_factor"] is not None
            and Decimal(str(stress_002["profit_factor"])) >= Decimal("1.20")
            and _d(stress_002, "max_drawdown_r") <= Decimal("7")
        ),
        "stress_005_remains_positive": (
            _d(stress_005, "total_r") > 0
            and stress_005["profit_factor"] is not None
            and Decimal(str(stress_005["profit_factor"])) > 1
        ),
        "remove_top_1_positive_pf_1_20": (
            _d(top1, "total_r") > 0
            and top1["profit_factor"] is not None
            and Decimal(str(top1["profit_factor"])) > Decimal("1.20")
        ),
    }
    passed = all(gates.values())
    return {
        "schema": SCHEMA,
        "market": MARKET,
        "candidate": "VT08_COGNITIVE_CORE_STACK_DEV_V1",
        "evidence_status": "CONSUMED_EXTENDED_VALIDATION",
        "checked_at": checked_at.isoformat(),
        "software_sha": software_sha,
        "coverage_start": coverage_start.isoformat(),
        "coverage_end": coverage_end.isoformat(),
        "trade_count": len(rows),
        "metrics": full,
        "annual_365d_blocks": annual_blocks,
        "rolling_730d_windows": rolling,
        "monte_carlo": mc,
        "execution_stress": {
            "0.01": stress_001,
            "0.02": stress_002,
            "0.05": stress_005,
        },
        "extreme_winner_dependence": {
            "remove_top_1": top1,
            "remove_top_5": top5,
        },
        "gates": gates,
        "extended_validation_pass": passed,
        "decision": (
            "EURJPY_5Y_EXTENDED_VALIDATION_PASS"
            if passed
            else "EURJPY_5Y_REJECTED"
        ),
        "governance": {
            "parameter_scan": False,
            "retuning_after_result": False,
            "freshness_claimed": False,
            "live_authorized": False,
            "production_authorized": False,
            "real_capital_authorized": False,
        },
    }


def to_json(path: Path) -> str:
    return json.dumps(evaluate(path), sort_keys=True, separators=(",", ":"))
