"""VT08 Index R109 — STANDARD retest timing-decay attribution.

R108 proved that source-valid retest execution improves aggregate PF/DD, but it
does not repair 5Y Y1 or R66 B2. R109 makes NO rule change. It attributes the
economic delta of the exact R108 retest cohort to timing/geometry that is
observable by the moment the retest arrives.

Preregistered diagnostics:
- delay from continuation close to retest: next M15 / 2-3 M15 / 4+ M15;
- favorable excursion completed BEFORE the retest bar, in original-close R;
- whether the original 2.5R continuation-close target had already completed
  before the retest window opened;
- remaining M15 bars in the source H4 after the retest;
- entry-improvement fraction using the same Protected Swing;
- baseline-vs-retest weighted economic delta.

The retest fill bar itself is excluded from pre-retest MFE because M15 OHLC
cannot order the retest touch against favorable excursion inside that bar.
This is forensic attribution only: no cohort is promoted, filtered, demoted or
turned into a runtime rule in R109.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from collections.abc import Callable, Sequence
from datetime import UTC, date
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    vt08_index_r15_concurrent_portfolio_validation as r15,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r58_exact_r47_distributed_risk as r58,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r74_ambiguous_bias_resolvers as r74,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r82_protected_swing_source_qualification as r82,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r89_execution_path_coverage as r89,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r102_source_confidence_risk_ablation as r102,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r107_standard_economic_root_attribution as r107,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r108_standard_source_retest_execution_replay as r108,
)
from qore.infrastructure.trader_lab import (
    vt08_index_v7_ttrades_source_corrected as v7,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import (
    Vt08IndexC2R1Bar,
)

SCHEMA = "qore.trader_lab.vt08_index_r109_standard_retest_timing_decay_attribution.v1"
IDENTITY = "VT08_INDEX_R109_STANDARD_RETEST_TIMING_DECAY_ATTRIBUTION_001"
SOURCE_R108_RUN_ID = 35588274260
SOURCE_R108_ARTIFACT_ID = 10633277043
SOURCE_R108_ARTIFACT_DIGEST = (
    "sha256:dabea18405b56a58f9c0cf69aa2e60b7f9efd30788ed4a1f4372c9d7cdc33564"
)


def _favorable_r(
    *,
    side: DemoTradingSetupSide,
    entry: Decimal,
    stop: Decimal,
    bar: Vt08IndexC2R1Bar,
) -> Decimal:
    risk = abs(entry - stop)
    if risk <= 0:
        raise ValueError("R109 invalid original risk")
    if side is DemoTradingSetupSide.LONG:
        return (bar.high - entry) / risk
    return (entry - bar.low) / risk


def _delay_bucket(delay_bars: int) -> str:
    if delay_bars == 1:
        return "NEXT_M15"
    if delay_bars <= 3:
        return "M15_2_3"
    return "M15_4_PLUS"


def _mfe_bucket(value: Decimal) -> str:
    if value < Decimal("0.5"):
        return "LT_0_5R"
    if value < Decimal("1"):
        return "R_0_5_TO_1"
    if value < Decimal("2"):
        return "R_1_TO_2"
    if value < Decimal("2.5"):
        return "R_2_TO_2_5"
    return "GE_2_5R"


def _improvement_bucket(value: Decimal) -> str:
    if value <= 0:
        return "LE_0"
    if value < Decimal("0.10"):
        return "GT_0_LT_10PCT"
    if value < Decimal("0.25"):
        return "PCT_10_TO_25"
    if value < Decimal("0.50"):
        return "PCT_25_TO_50"
    return "GE_50PCT"


def _remaining_bucket(remaining_bars: int) -> str:
    if remaining_bars <= 1:
        return "H4_REMAIN_0_1"
    if remaining_bars <= 4:
        return "H4_REMAIN_2_4"
    return "H4_REMAIN_5_PLUS"


def _weighted_metrics(
    rows: Sequence[dict[str, Any]],
    *,
    field: str,
) -> dict[str, Any]:
    values = tuple(Decimal(str(row[field])) for row in rows)
    total = sum(values, Decimal())
    gains = sum((value for value in values if value > 0), Decimal())
    losses = -sum((value for value in values if value < 0), Decimal())
    equity = Decimal()
    peak = Decimal()
    dd = Decimal()
    streak = 0
    max_streak = 0
    for value in values:
        equity += value
        peak = max(peak, equity)
        dd = max(dd, peak - equity)
        if value < 0:
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0
    return {
        "sample": len(values),
        "total_r": str(total),
        "mean_r": str(total / len(values)) if values else "0",
        "profit_factor": str(gains / losses) if losses else None,
        "max_drawdown_r": str(dd),
        "max_losing_streak": max_streak,
        "wins": sum(value > 0 for value in values),
        "losses": sum(value < 0 for value in values),
        "flats": sum(value == 0 for value in values),
    }


def _group(
    rows: Sequence[dict[str, Any]],
    selector: Callable[[dict[str, Any]], str],
) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[selector(row)].append(row)
    report: dict[str, Any] = {}
    for label, items in sorted(grouped.items()):
        delta = sum(
            (Decimal(str(item["weighted_delta_r"])) for item in items),
            Decimal(),
        )
        report[label] = {
            "sample": len(items),
            "weighted_delta_r": str(delta),
            "mean_weighted_delta_r": (
                str(delta / Decimal(len(items))) if items else "0"
            ),
            "baseline_primary": _weighted_metrics(
                items,
                field="baseline_primary_r",
            ),
            "retest_primary": _weighted_metrics(
                items,
                field="retest_primary_r",
            ),
            "baseline_secondary": _weighted_metrics(
                items,
                field="baseline_secondary_r",
            ),
            "retest_secondary": _weighted_metrics(
                items,
                field="retest_secondary_r",
            ),
        }
    return report


def _period_label(
    *,
    exit_date: date,
    window_id: str,
    start_date: date,
    end_date: date,
) -> str:
    boundaries = r108.r80._boundaries(
        window_id=window_id,
        start_date=start_date,
        end_date=end_date,
    )
    prefix = "B" if window_id == "R66" else "Y"
    for index in range(len(boundaries) - 1):
        if boundaries[index] <= exit_date < boundaries[index + 1]:
            return f"{prefix}{index + 1}"
    return "OUTSIDE"


def _window(
    *,
    roots: dict[str, Path],
    window_id: str,
) -> dict[str, Any]:
    canonical, bars_by_symbol_raw, provenance = r74._load_window(
        roots=roots,
        window_id=window_id,
    )
    start_date, end_date, expected = r74._window_contract(window_id)
    bars_by_symbol: dict[str, Sequence[Vt08IndexC2R1Bar]] = {
        symbol: tuple(bars)
        for symbol, bars in bars_by_symbol_raw.items()
    }
    opened_by_symbol = {
        symbol: tuple(bar.opened_at.astimezone(UTC) for bar in bars)
        for symbol, bars in bars_by_symbol.items()
    }
    base, _ = r58._exact_r47(
        tuple(canonical),
        bars_by_symbol=bars_by_symbol,
    )
    control, _ = r102._apply_confidence_policy(
        tuple(base),
        bars_by_symbol=bars_by_symbol,
        policy_id=r102.POLICY_EXPLICIT_FULL,
    )
    control = tuple(control)
    if len(control) != expected or expected != r108.EXPECTED_CANONICAL[window_id]:
        raise ValueError(f"R109 {window_id} canonical drift")

    standard_ids = r107._standard_ids(
        control,
        bars_by_symbol=bars_by_symbol,
    )
    if len(standard_ids) != r108.EXPECTED_STANDARD[window_id]:
        raise ValueError(f"R109 {window_id} STANDARD drift")

    h4_cache = {
        symbol: r82._h4_bar_cache(bars)
        for symbol, bars in bars_by_symbol.items()
    }

    rows: list[dict[str, Any]] = []
    for item in control:
        if item.opportunity.identity() not in standard_ids:
            continue

        signal = item.opportunity.signal
        inside = h4_cache[item.symbol].get(
            signal.h4_opened_at.astimezone(UTC)
        )
        if inside is None:
            raise ValueError("R109 canonical H4 missing")

        continuation_index = next(
            (
                index
                for index, bar in enumerate(inside)
                if bar.closed_at.astimezone(UTC)
                == signal.signal_at.astimezone(UTC)
            ),
            None,
        )
        if continuation_index is None or continuation_index <= 0:
            raise ValueError("R109 continuation bar missing")

        retest_index = r89._retest_fill_index(
            inside,
            continuation_index=continuation_index,
            side=signal.side,
            protected_swing=signal.protected_swing_extreme,
            model_kind=signal.model_kind,
            h4_open=inside[0].open,
        )
        if retest_index is None:
            continue

        retest_level = r89._continuation_breakout_level(
            inside,
            continuation_index=continuation_index,
            side=signal.side,
        )
        fill_bar = inside[retest_index]
        new_signal = r108._build_retest_signal(
            signal,
            retest_level=retest_level,
            retest_window_opened_at=fill_bar.opened_at,
        )
        new_outcome = r108._manage_retest(
            new_signal,
            fill_bar=fill_bar,
            bars=bars_by_symbol[item.symbol],
            opened=opened_by_symbol[item.symbol],
        )

        original_risk = abs(signal.entry - signal.stop)
        new_risk = abs(new_signal.entry - new_signal.stop)
        improvement = (
            (original_risk - new_risk) / original_risk
            if original_risk > 0
            else Decimal()
        )
        prior_bars = inside[continuation_index + 1 : retest_index]
        pre_mfe = max(
            (
                _favorable_r(
                    side=signal.side,
                    entry=signal.entry,
                    stop=signal.stop,
                    bar=bar,
                )
                for bar in prior_bars
            ),
            default=Decimal(),
        )
        target_completed_before_retest = pre_mfe >= r108.TARGET_R
        baseline_completed_before_retest = (
            item.outcome.exited_at.astimezone(UTC)
            <= fill_bar.opened_at.astimezone(UTC)
        )

        baseline_primary = (
            item.outcome.r_multiple - r108.PRIMARY_STRESS
        ) * item.weight
        retest_primary = (
            new_outcome.r_multiple - r108.PRIMARY_STRESS
        ) * item.weight
        baseline_secondary = (
            item.outcome.r_multiple - r108.SECONDARY_STRESS
        ) * item.weight
        retest_secondary = (
            new_outcome.r_multiple - r108.SECONDARY_STRESS
        ) * item.weight

        delay_bars = retest_index - continuation_index
        remaining = len(inside) - retest_index - 1
        exit_date = new_outcome.exited_at.astimezone(v7._NY).date()

        rows.append(
            {
                "trade_id": item.trade_id,
                "symbol": item.symbol,
                "side": signal.side.value,
                "anchor": str(
                    signal.h4_opened_at.astimezone(v7._NY).hour
                ),
                "poi": item.opportunity.source_poi_kind,
                "period": _period_label(
                    exit_date=exit_date,
                    window_id=window_id,
                    start_date=start_date,
                    end_date=end_date,
                ),
                "delay_bars": delay_bars,
                "delay_bucket": _delay_bucket(delay_bars),
                "remaining_h4_bars": remaining,
                "remaining_bucket": _remaining_bucket(remaining),
                "pre_retest_mfe_original_r": str(pre_mfe),
                "pre_retest_mfe_bucket": _mfe_bucket(pre_mfe),
                "original_2_5r_target_completed_before_retest": (
                    target_completed_before_retest
                ),
                "baseline_trade_completed_before_retest": (
                    baseline_completed_before_retest
                ),
                "entry_improvement_risk_fraction": str(improvement),
                "entry_improvement_bucket": _improvement_bucket(improvement),
                "baseline_primary_r": str(baseline_primary),
                "retest_primary_r": str(retest_primary),
                "baseline_secondary_r": str(baseline_secondary),
                "retest_secondary_r": str(retest_secondary),
                "weighted_delta_r": str(retest_primary - baseline_primary),
                "baseline_exit_reason": item.outcome.exit_reason,
                "retest_exit_reason": new_outcome.exit_reason,
            }
        )

    if len(rows) != r108.EXPECTED_RETEST[window_id]:
        raise ValueError(f"R109 {window_id} retest sample drift")

    stale_rows = [
        row
        for row in rows
        if bool(row["baseline_trade_completed_before_retest"])
    ]
    live_rows = [
        row
        for row in rows
        if not bool(row["baseline_trade_completed_before_retest"])
    ]
    target_done_rows = [
        row
        for row in rows
        if bool(row["original_2_5r_target_completed_before_retest"])
    ]

    return {
        "window_id": window_id,
        "sample": len(rows),
        "expected_sample": r108.EXPECTED_RETEST[window_id],
        "baseline_completed_before_retest": {
            "count": len(stale_rows),
            "fraction": str(Decimal(len(stale_rows)) / Decimal(len(rows))),
            "attribution": _group(
                rows,
                lambda row: (
                    "BASELINE_ALREADY_COMPLETE"
                    if bool(row["baseline_trade_completed_before_retest"])
                    else "BASELINE_STILL_OPEN"
                ),
            ),
        },
        "original_target_completed_before_retest": {
            "count": len(target_done_rows),
            "fraction": str(
                Decimal(len(target_done_rows)) / Decimal(len(rows))
            ),
            "attribution": _group(
                rows,
                lambda row: (
                    "TARGET_ALREADY_COMPLETE"
                    if bool(
                        row["original_2_5r_target_completed_before_retest"]
                    )
                    else "TARGET_NOT_COMPLETE"
                ),
            ),
        },
        "live_at_retest_sample": len(live_rows),
        "by_delay": _group(
            rows,
            lambda row: str(row["delay_bucket"]),
        ),
        "by_pre_retest_mfe": _group(
            rows,
            lambda row: str(row["pre_retest_mfe_bucket"]),
        ),
        "by_remaining_h4": _group(
            rows,
            lambda row: str(row["remaining_bucket"]),
        ),
        "by_entry_improvement": _group(
            rows,
            lambda row: str(row["entry_improvement_bucket"]),
        ),
        "by_period": _group(
            rows,
            lambda row: str(row["period"]),
        ),
        "by_market": _group(
            rows,
            lambda row: str(row["symbol"]),
        ),
        "by_side": _group(
            rows,
            lambda row: str(row["side"]),
        ),
        "by_anchor": _group(
            rows,
            lambda row: str(row["anchor"]),
        ),
        "by_poi": _group(
            rows,
            lambda row: str(row["poi"]),
        ),
        "provenance": provenance,
    }


def build_report(
    *,
    nas100_root: Path,
    sp500_root: Path,
    us30_root: Path,
) -> dict[str, Any]:
    if r108.IDENTITY != (
        "VT08_INDEX_R108_STANDARD_SOURCE_RETEST_EXECUTION_REPLAY_001"
    ):
        raise ValueError("R109 R108 identity drift")

    roots = {
        "NAS100": nas100_root,
        "SP500": sp500_root,
        "US30": us30_root,
    }
    five = _window(roots=roots, window_id="5Y")
    two = _window(roots=roots, window_id="2Y")
    failed = _window(roots=roots, window_id="R66")

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "source_r108": {
            "run_id": SOURCE_R108_RUN_ID,
            "artifact_id": SOURCE_R108_ARTIFACT_ID,
            "artifact_digest": SOURCE_R108_ARTIFACT_DIGEST,
            "decision": "R108_RETEST_EXECUTION_REPLAY_COMPLETE_NO_CANDIDATE",
        },
        "preregistered_diagnostics": {
            "rule_change": False,
            "same_r108_retest_sample": True,
            "pre_retest_mfe_excludes_fill_bar": True,
            "delay_bins": ["NEXT_M15", "M15_2_3", "M15_4_PLUS"],
            "mfe_bins_r": [
                "LT_0_5R",
                "R_0_5_TO_1",
                "R_1_TO_2",
                "R_2_TO_2_5",
                "GE_2_5R",
            ],
            "entry_improvement_bins": [
                "LE_0",
                "GT_0_LT_10PCT",
                "PCT_10_TO_25",
                "PCT_25_TO_50",
                "GE_50PCT",
            ],
            "runtime_filter_created": False,
        },
        "five_year": five,
        "recent_two_year": two,
        "r66_failed_holdout": failed,
        "decision": "R109_RETEST_TIMING_DECAY_ATTRIBUTION_COMPLETE_NO_RULE_CHANGE",
        "governance": {
            "research_only": True,
            "consumed_evidence_only": True,
            "candidate_created": False,
            "signals_suppressed": False,
            "trade_count_changed": False,
            "target_changed": False,
            "stop_changed": False,
            "risk_allocator_changed": False,
            "anchor_14_enabled": False,
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

    def brief(section: dict[str, Any]) -> dict[str, Any]:
        return {
            "sample": section["sample"],
            "baseline_completed_before_retest": section[
                "baseline_completed_before_retest"
            ],
            "original_target_completed_before_retest": section[
                "original_target_completed_before_retest"
            ],
            "by_delay": section["by_delay"],
            "by_pre_retest_mfe": section["by_pre_retest_mfe"],
            "by_period": section["by_period"],
        }

    print(
        json.dumps(
            {
                "identity": IDENTITY,
                "five_year": brief(report["five_year"]),
                "recent_two_year": brief(report["recent_two_year"]),
                "r66": brief(report["r66_failed_holdout"]),
                "decision": report["decision"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
