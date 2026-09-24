"""Shape-only source audit for VT08 Candle 3 closure opportunities."""
from __future__ import annotations

import json
from collections import Counter
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from typing import Final
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_backtest_v1 import (
    load_market_evidence,
)
from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_evaluator_v1 import (
    _candle2_reversal_side,
    _latest_complete_source_days,
)
from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_v1 import (
    ANCHORS_NY,
    EXPANSION_MARKETS,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_b01_r3_8 import (
    Vt08B01Bar,
    resolve_bias,
    source_h4_from_m15,
)

SCHEMA: Final = "qore.trader_lab.vt08_cognitive_c3_shape_opportunity_audit.v1"
_NY = ZoneInfo("America/New_York")


def c2_failure_class(
    c1: Vt08B01Bar,
    c2: Vt08B01Bar,
    *,
    bias: DemoTradingSetupSide,
) -> str:
    swept_high = c2.high > c1.high
    swept_low = c2.low < c1.low
    if swept_high and swept_low:
        return "C2_BOTH_SIDES_SWEPT"
    if not swept_high and not swept_low:
        return "C2_NO_C1_EXTREME_SWEEP"
    inside = c1.low < c2.close < c1.high
    if not inside:
        return "C2_CLOSE_OUTSIDE_C1"
    side = DemoTradingSetupSide.SHORT if swept_high else DemoTradingSetupSide.LONG
    if side is not bias:
        return "C2_REVERSAL_OPPOSES_BIAS"
    return "C2_SAME_SIDE_VALID"


def is_c3_closure_shape(
    c2: Vt08B01Bar,
    c3: Vt08B01Bar,
    *,
    bias: DemoTradingSetupSide,
) -> bool:
    no_extreme_sweep = c3.high <= c2.high and c3.low >= c2.low
    if not no_extreme_sweep:
        return False
    if bias is DemoTradingSetupSide.LONG:
        return c3.close > max(c2.open, c2.close)
    return c3.close < min(c2.open, c2.close)


def evaluate(path: Path) -> dict[str, object]:
    _fingerprint, symbol, checked_at, software_sha, bars = load_market_evidence(path)
    if symbol not in EXPANSION_MARKETS:
        raise ValueError("C3 audit market outside frozen 5M universe")

    bars_by_open = {bar.opened_at: bar for bar in bars}
    counts: Counter[str] = Counter()
    failures: Counter[str] = Counter()
    by_anchor: dict[int, Counter[str]] = {
        anchor: Counter() for anchor in ANCHORS_NY
    }
    shape_dates = set()

    for entry_bar in bars:
        local = entry_bar.opened_at.astimezone(_NY)
        if local.minute != 0 or local.hour not in ANCHORS_NY:
            continue
        anchor = local.hour
        counts["ANCHOR_OBSERVED"] += 1

        c1 = source_h4_from_m15(
            bars_by_open,
            opened_at_local=local - timedelta(hours=12),
        )
        c2 = source_h4_from_m15(
            bars_by_open,
            opened_at_local=local - timedelta(hours=8),
        )
        c3 = source_h4_from_m15(
            bars_by_open,
            opened_at_local=local - timedelta(hours=4),
        )
        if (
            c1 is None
            or c2 is None
            or c3 is None
            or c3.closed_at != entry_bar.opened_at
        ):
            failures["INCOMPLETE_C1_C2_C3"] += 1
            by_anchor[anchor]["INCOMPLETE_C1_C2_C3"] += 1
            continue
        counts["C1_C2_C3_COMPLETE"] += 1

        source_days = _latest_complete_source_days(
            bars_by_open,
            before_local=local,
        )
        if len(source_days) != 2:
            failures["INCOMPLETE_SOURCE_DAY"] += 1
            by_anchor[anchor]["INCOMPLETE_SOURCE_DAY"] += 1
            continue
        current_day, previous_day = source_days
        bias = resolve_bias(previous_day=previous_day, current_day=current_day)
        if bias is None:
            failures["BIAS_UNRESOLVED"] += 1
            by_anchor[anchor]["BIAS_UNRESOLVED"] += 1
            continue
        counts["BIAS_RESOLVED"] += 1

        if _candle2_reversal_side(c1, c2) is bias:
            counts["C2_ALREADY_VALID_SAME_SIDE"] += 1
            by_anchor[anchor]["C2_ALREADY_VALID_SAME_SIDE"] += 1
            continue

        failure_class = c2_failure_class(c1, c2, bias=bias)
        failures[failure_class] += 1
        by_anchor[anchor][failure_class] += 1

        if not is_c3_closure_shape(c2, c3, bias=bias):
            failures["NO_C3_CLOSURE_SHAPE"] += 1
            by_anchor[anchor]["NO_C3_CLOSURE_SHAPE"] += 1
            continue

        counts["C3_CLOSURE_SHAPE"] += 1
        by_anchor[anchor]["C3_CLOSURE_SHAPE"] += 1
        shape_dates.add(local.date())

    first_open = min(bar.opened_at for bar in bars)
    last_close = max(bar.closed_at for bar in bars)
    coverage_days = Decimal(
        str((last_close - first_open).total_seconds())
    ) / Decimal("86400")
    shapes = counts["C3_CLOSURE_SHAPE"]
    annualized = (
        Decimal(shapes) * Decimal("365") / coverage_days
        if coverage_days > 0
        else Decimal(0)
    )

    return {
        "schema": SCHEMA,
        "market": symbol,
        "checked_at": checked_at.isoformat(),
        "software_sha": software_sha,
        "shape_only": True,
        "counts": dict(counts),
        "first_failure_counts": dict(failures.most_common()),
        "c3_shape_unique_ny_dates": len(shape_dates),
        "c3_shape_annualized": format(annualized, "f"),
        "c3_shape_two_year_equivalent": format(
            annualized * Decimal("2"),
            "f",
        ),
        "by_anchor_ny": {
            str(anchor): dict(by_anchor[anchor].most_common())
            for anchor in ANCHORS_NY
        },
        "governance": {
            "point_of_interest_bound": False,
            "lower_timeframe_cisd_bound": False,
            "protected_swing_bound": False,
            "executable_candidate": False,
            "pnl_read": False,
            "target_assigned": False,
            "stop_assigned": False,
            "methodology_changed": False,
            "live_authorized": False,
        },
    }


def to_json(path: Path) -> str:
    return json.dumps(evaluate(path), sort_keys=True, separators=(",", ":"))
