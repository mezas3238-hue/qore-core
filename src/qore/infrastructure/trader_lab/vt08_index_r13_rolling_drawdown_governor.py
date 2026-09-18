"""VT08 Index R13 — rolling drawdown recovery governor.

R13 preserves the R8 2.5R execution stream. It replaces R6's all-time-peak
drawdown governor with a finite rolling drawdown state. The state is computed
only from completed prior trades and automatically forgets stale peaks.

No trade is skipped and no weight may be zero. The 5Y window is consumed
development evidence.
"""

from __future__ import annotations

import argparse
import itertools
import json
from collections import deque
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import vt08_index_cibo_2y_density_round4 as r4
from qore.infrastructure.trader_lab import vt08_index_cibo_2y_management_round5 as r5
from qore.infrastructure.trader_lab import vt08_index_r6_5y_failure_forensics as fx
from qore.infrastructure.trader_lab import vt08_index_r6_five_year_validation as v5y
from qore.infrastructure.trader_lab import vt08_index_r8_priority_poi_rearm_reset as r8
from qore.infrastructure.trader_lab import vt08_index_r10_contextual_risk as r10
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import Vt08IndexC2R1Bar

SCHEMA = "qore.trader_lab.vt08_index_r13_rolling_drawdown_governor.v1"
IDENTITY = "VT08_INDEX_R13_ROLLING_DRAWDOWN_GOVERNOR_001"
MIN_TRADES = 1500
MAX_TRADES = 1600
PRIMARY_STRESS = Decimal("0.05")
SECONDARY_STRESS = Decimal("0.10")
PRIMARY_PF_GOAL = Decimal("1.50")
PRIMARY_DD_GOAL = Decimal("6")
SECONDARY_PF_GOAL = Decimal("1.30")
SECONDARY_DD_GOAL = Decimal("8")


@dataclass(frozen=True, slots=True)
class RollingScheme:
    aligned_weight: Decimal
    c2_cap: Decimal
    short_cap: Decimal
    rolling_trades: int
    warn_dd_r: Decimal
    warn_multiplier: Decimal
    hard_dd_r: Decimal
    hard_multiplier: Decimal
    loss_trigger: int | None
    loss_multiplier: Decimal | None

    @property
    def scheme_id(self) -> str:
        loss = (
            "OFF"
            if self.loss_trigger is None
            else f"{self.loss_trigger}x{self.loss_multiplier}"
        )
        return (
            "R13-"
            f"A{self.aligned_weight}-C2{self.c2_cap}-S{self.short_cap}-"
            f"W{self.rolling_trades}-"
            f"D{self.warn_dd_r}x{self.warn_multiplier}-"
            f"H{self.hard_dd_r}x{self.hard_multiplier}-L{loss}"
        )

    def payload(self) -> dict[str, Any]:
        return {
            "scheme_id": self.scheme_id,
            "aligned_weight": str(self.aligned_weight),
            "c2_cap": str(self.c2_cap),
            "short_cap": str(self.short_cap),
            "rolling_trades": self.rolling_trades,
            "warn_dd_r": str(self.warn_dd_r),
            "warn_multiplier": str(self.warn_multiplier),
            "hard_dd_r": str(self.hard_dd_r),
            "hard_multiplier": str(self.hard_multiplier),
            "loss_trigger": self.loss_trigger,
            "loss_multiplier": (
                str(self.loss_multiplier)
                if self.loss_multiplier is not None
                else None
            ),
        }


def _schemes() -> tuple[RollingScheme, ...]:
    rows: list[RollingScheme] = []
    loss_modes: tuple[
        tuple[int | None, Decimal | None],
        ...,
    ] = (
        (None, None),
        (2, Decimal("0.25")),
    )
    for (
        aligned_weight,
        rolling_trades,
        warn_dd,
        warn_mult,
        hard_dd,
        hard_mult,
        loss_mode,
    ) in itertools.product(
        (Decimal("0.10"), Decimal("0.25")),
        (20, 40, 60),
        (Decimal("1.5"), Decimal("2.0"), Decimal("2.5")),
        (Decimal("0.25"), Decimal("0.50")),
        (Decimal("3.0"), Decimal("4.0"), Decimal("5.0")),
        (Decimal("0.10"), Decimal("0.25")),
        loss_modes,
    ):
        if hard_dd <= warn_dd:
            continue
        loss_trigger, loss_multiplier = loss_mode
        rows.append(
            RollingScheme(
                aligned_weight=aligned_weight,
                c2_cap=Decimal("0.50"),
                short_cap=Decimal("0.50"),
                rolling_trades=rolling_trades,
                warn_dd_r=warn_dd,
                warn_multiplier=warn_mult,
                hard_dd_r=hard_dd,
                hard_multiplier=hard_mult,
                loss_trigger=loss_trigger,
                loss_multiplier=loss_multiplier,
            )
        )
    return tuple(rows)


def _base_weight(context: r10.Context, scheme: RollingScheme) -> Decimal:
    weight = (
        Decimal("1")
        if context.previous_source_day_body_opposed
        else scheme.aligned_weight
    )
    if context.rearm:
        weight = Decimal("1")
    if context.c2_expansion:
        weight = min(weight, scheme.c2_cap)
    if context.short:
        weight = min(weight, scheme.short_cap)
    if weight <= 0:
        raise ValueError("R13 base weight may not be zero")
    return weight


def _weighted_values(
    outcomes: Sequence[r5.ManagedTrade],
    contexts: Sequence[r10.Context],
    *,
    scheme: RollingScheme,
    stress: Decimal,
) -> tuple[tuple[Decimal, ...], dict[str, Any]]:
    equity = Decimal()
    history: deque[Decimal] = deque([Decimal()], maxlen=scheme.rolling_trades + 1)
    loss_streak = 0
    values: list[Decimal] = []
    weights: list[Decimal] = []
    warn_trades = 0
    hard_trades = 0
    loss_defense_trades = 0

    for outcome, context in zip(outcomes, contexts, strict=True):
        rolling_peak = max(history)
        dd_before = rolling_peak - equity
        weight = _base_weight(context, scheme)

        if dd_before >= scheme.hard_dd_r:
            weight *= scheme.hard_multiplier
            hard_trades += 1
        elif dd_before >= scheme.warn_dd_r:
            weight *= scheme.warn_multiplier
            warn_trades += 1

        if (
            scheme.loss_trigger is not None
            and scheme.loss_multiplier is not None
            and loss_streak >= scheme.loss_trigger
        ):
            weight *= scheme.loss_multiplier
            loss_defense_trades += 1

        if weight <= 0:
            raise ValueError("R13 may not skip a trade")

        value = (outcome.r_multiple - stress) * weight
        values.append(value)
        weights.append(weight)
        equity += value
        history.append(equity)

        if outcome.r_multiple - stress < 0:
            loss_streak += 1
        else:
            loss_streak = 0

    return tuple(values), {
        "minimum_weight": str(min(weights)),
        "maximum_weight": str(max(weights)),
        "mean_weight": str(sum(weights, Decimal()) / len(weights)),
        "zero_weight_trades": sum(weight == 0 for weight in weights),
        "warn_trades": warn_trades,
        "hard_trades": hard_trades,
        "loss_defense_trades": loss_defense_trades,
    }


def _year_metrics(
    stream: Sequence[tuple[r4.ExpandedOpportunity, r5.ManagedTrade]],
    values: Sequence[Decimal],
) -> dict[str, Any]:
    years = sorted(
        {
            opportunity.signal.signal_at.astimezone(v5y._NY).year
            for opportunity, _outcome in stream
        }
    )
    result: dict[str, Any] = {}
    for year in years:
        subset = tuple(
            value
            for (opportunity, _outcome), value in zip(
                stream,
                values,
                strict=True,
            )
            if opportunity.signal.signal_at.astimezone(v5y._NY).year == year
        )
        result[str(year)] = fx._metrics(subset)
    return result


def _candidate(
    stream: Sequence[tuple[r4.ExpandedOpportunity, r5.ManagedTrade]],
    contexts: Sequence[r10.Context],
    *,
    scheme: RollingScheme,
) -> dict[str, Any]:
    outcomes = tuple(outcome for _opportunity, outcome in stream)
    primary_values, primary_diag = _weighted_values(
        outcomes,
        contexts,
        scheme=scheme,
        stress=PRIMARY_STRESS,
    )
    secondary_values, secondary_diag = _weighted_values(
        outcomes,
        contexts,
        scheme=scheme,
        stress=SECONDARY_STRESS,
    )
    primary = fx._metrics(primary_values)
    secondary = fx._metrics(secondary_values)
    years = _year_metrics(stream, primary_values)
    positive_years = sum(
        Decimal(str(row["total_r"])) > 0 for row in years.values()
    )
    sample = len(stream)
    return {
        "scheme": scheme.payload(),
        "sample": sample,
        "primary": primary,
        "secondary": secondary,
        "primary_diagnostics": primary_diag,
        "secondary_diagnostics": secondary_diag,
        "positive_years": positive_years,
        "primary_by_year": years,
        "goal_pass": (
            MIN_TRADES <= sample <= MAX_TRADES
            and Decimal(str(primary["profit_factor"] or "0")) >= PRIMARY_PF_GOAL
            and Decimal(str(primary["max_drawdown_r"])) <= PRIMARY_DD_GOAL
            and Decimal(str(secondary["profit_factor"] or "0")) >= SECONDARY_PF_GOAL
            and Decimal(str(secondary["max_drawdown_r"])) <= SECONDARY_DD_GOAL
            and positive_years >= 4
            and int(primary_diag["zero_weight_trades"]) == 0
        ),
    }


def _rank(row: dict[str, Any]) -> tuple[int, Decimal, Decimal, Decimal, int]:
    primary = row["primary"]
    return (
        int(bool(row["goal_pass"])),
        Decimal(str(primary["profit_factor"] or "0")),
        -Decimal(str(primary["max_drawdown_r"])),
        Decimal(str(primary["total_r"])),
        int(row["positive_years"]),
    )


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
    bars_by_symbol: dict[str, Sequence[Vt08IndexC2R1Bar]] = {}
    indexed_by_symbol: dict[str, dict[datetime, Vt08IndexC2R1Bar]] = {}
    opportunities_by_symbol: dict[
        str,
        tuple[r4.ExpandedOpportunity, ...],
    ] = {}
    provenance: dict[str, Any] = {}

    for symbol in ("NAS100", "SP500", "US30"):
        bars, source = v5y._load_cibo_m15_5y(roots[symbol], symbol=symbol)
        bars_by_symbol[symbol] = bars
        indexed_by_symbol[symbol] = {
            bar.opened_at.astimezone(UTC): bar for bar in bars
        }
        opportunities_by_symbol[symbol] = r8._opportunities(
            symbol=symbol,
            bars=bars,
        )
        provenance[symbol] = source

    stream = r10._base_stream(
        opportunities_by_symbol=opportunities_by_symbol,
        bars_by_symbol=bars_by_symbol,
    )
    contexts = tuple(
        r10._context(
            opportunity,
            indexed=indexed_by_symbol[opportunity.signal.symbol],
        )
        for opportunity, _outcome in stream
    )

    rows = [
        _candidate(stream, contexts, scheme=scheme)
        for scheme in _schemes()
    ]
    rows.sort(key=_rank, reverse=True)
    goals = [row for row in rows if bool(row["goal_pass"])]

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "window": {
            "start_date": v5y.START_DATE.isoformat(),
            "end_date_exclusive": v5y.END_DATE_EXCLUSIVE.isoformat(),
            "status": "CONSUMED_DEVELOPMENT",
            "fresh_certification_holdout": False,
        },
        "execution_architecture": r8.IDENTITY,
        "sample": len(stream),
        "scheme_count": len(rows),
        "goal_candidate_count": len(goals),
        "best": rows[0],
        "top_20": rows[:20],
        "goal_candidates": goals[:20],
        "provenance": provenance,
        "governance": {
            "development_only": True,
            "all_trades_preserved": True,
            "zero_risk_allowed": False,
            "all_time_peak_dd_state_used": False,
            "rolling_drawdown_state_only": True,
            "completed_outcomes_only_for_next_trade_state": True,
            "five_year_window_consumed": True,
            "fresh_holdout_claim": False,
            "candidate_promoted": False,
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
    print(
        json.dumps(
            {
                "identity": IDENTITY,
                "scheme_count": report["scheme_count"],
                "goal_candidate_count": report["goal_candidate_count"],
                "best": report["best"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
