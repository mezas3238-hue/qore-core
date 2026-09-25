"""VT08 Index R117 — STANDARD late-revalidation x CISD anatomy attribution.

R116 falsified source-retest execution as a repair for LAST_BAR. The existing
R55 engine already contains a distinct causal state, CISD_LATE_REVALIDATION,
but R104 only attributed promotion labels to explicit-PS setups; STANDARD rows
were intentionally collapsed to STANDARD_BASE_NO_PROMOTION.

R117 closes that gap without changing risk. It applies the exact existing
R55._late_revalidation detector to the frozen STANDARD surface and crosses it
with R114 CISD anatomy.

The reused late-revalidation contract is:
- source POI kind is CISD;
- frozen continuation-latency bucket is 5+;
- Reaction Atlas detects a fresh M15 liquidity take;
- the reaction occurs strictly after canonical CISD confirmation.

No new threshold or learned state is introduced. The detector is reused exactly
as implemented before this experiment. R117 creates no promotion, filter,
suppression, candidate or runtime rule.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from collections.abc import Callable, Sequence
from datetime import UTC
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    vt08_index_r55_distributed_causal_risk as r55,
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
    vt08_index_r102_source_confidence_risk_ablation as r102,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r107_standard_economic_root_attribution as r107,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r108_standard_source_retest_execution_replay as r108,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r109_standard_retest_timing_decay_attribution as r109,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r114_standard_cisd_ps_anatomy_attribution as r114,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r116_anatomy_retest_execution_attribution as r116,
)
from qore.infrastructure.trader_lab import (
    vt08_index_v7_ttrades_source_corrected as v7,
)
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import (
    Vt08IndexC2R1Bar,
)

SCHEMA = "qore.trader_lab.vt08_index_r117_standard_late_revalidation_anatomy.v1"
IDENTITY = "VT08_INDEX_R117_STANDARD_LATE_REVALIDATION_ANATOMY_ATTRIBUTION_001"

SOURCE_R116_RUN_ID = 35666472208
SOURCE_R116_ARTIFACT_ID = 10669207820
SOURCE_R116_ARTIFACT_DIGEST = (
    "sha256:b3d6aa3e0af0cb9aeaf809fb54f40d2f3e1a7d0de9a98808b0a5227c9228e9f2"
)

EXPECTED_STANDARD = r114.EXPECTED_STANDARD


def _metrics(
    rows: Sequence[dict[str, Any]],
    *,
    field: str,
) -> dict[str, Any]:
    ordered = sorted(
        rows,
        key=lambda row: (
            str(row["exit_timestamp"]),
            str(row["symbol"]),
            int(row["trade_id"]),
        ),
    )
    values = tuple(Decimal(str(row[field])) for row in ordered)
    total = sum(values, Decimal())
    gains = sum((value for value in values if value > 0), Decimal())
    losses = -sum((value for value in values if value < 0), Decimal())
    equity = Decimal()
    peak = Decimal()
    drawdown = Decimal()
    streak = 0
    max_streak = 0
    for value in values:
        equity += value
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
        if value < 0:
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0
    return {
        "sample": len(values),
        "wins": sum(value > 0 for value in values),
        "losses": sum(value < 0 for value in values),
        "flats": sum(value == 0 for value in values),
        "total_r": str(total),
        "mean_r": str(total / Decimal(len(values))) if values else "0",
        "profit_factor": str(gains / losses) if losses else None,
        "max_drawdown_r": str(drawdown),
        "max_losing_streak": max_streak,
    }


def _group(
    rows: Sequence[dict[str, Any]],
    selector: Callable[[dict[str, Any]], str],
) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[selector(row)].append(row)
    return {
        label: {
            "sample": len(items),
            "primary": _metrics(items, field="primary_r"),
            "secondary": _metrics(items, field="secondary_r"),
        }
        for label, items in sorted(grouped.items())
    }


def _period_matrix(
    rows: Sequence[dict[str, Any]],
    *,
    field: str,
) -> dict[str, Any]:
    periods: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        periods[str(row["period"])].append(row)
    return {
        period: _group(items, lambda row: str(row[field]))
        for period, items in sorted(periods.items())
    }


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
        raise ValueError(f"R117 {window_id} canonical drift")

    standard_ids = r107._standard_ids(
        control,
        bars_by_symbol=bars_by_symbol,
    )
    if len(standard_ids) != EXPECTED_STANDARD[window_id]:
        raise ValueError(f"R117 {window_id} STANDARD drift")

    h4_cache = {
        symbol: r82._h4_bar_cache(bars)
        for symbol, bars in bars_by_symbol.items()
    }
    reaction_bars, reaction_opened = r55._reaction_bars(
        bars_by_symbol
    )

    rows: list[dict[str, Any]] = []
    for item in control:
        if item.opportunity.identity() not in standard_ids:
            continue

        signal = item.opportunity.signal
        inside = h4_cache[item.symbol].get(
            signal.h4_opened_at.astimezone(UTC)
        )
        if inside is None:
            raise ValueError("R117 canonical H4 missing")
        touch_index = next(
            (
                index
                for index, bar in enumerate(inside)
                if bar.opened_at.astimezone(UTC)
                == item.opportunity.poi_touch_at.astimezone(UTC)
            ),
            None,
        )
        if touch_index is None:
            raise ValueError("R117 POI touch missing")
        anatomy = r114._trace_anatomy(
            inside,
            side=signal.side,
            start_index=touch_index,
        )
        if anatomy is None:
            raise ValueError("R117 CISD anatomy missing")
        extreme_position = r114._extreme_position(
            sequence_start=int(anatomy["sequence_start"]),
            sequence_end=int(anatomy["sequence_end"]),
            extreme_index=int(anatomy["extreme_index"]),
        )
        last_state = (
            "LAST_BAR"
            if extreme_position == "LAST_BAR"
            else "NOT_LAST_BAR"
        )

        late = r55._late_revalidation(
            item,
            bars=reaction_bars[item.symbol],
            opened=reaction_opened[item.symbol],
        )
        rearm = int(item.opportunity.rearm_index) > 0
        combined = (
            f"{last_state}|"
            f"{'LATE_REVALIDATION' if late else 'NO_LATE_REVALIDATION'}"
        )
        period = r109._period_label(
            exit_date=item.exited_at.astimezone(v7._NY).date(),
            window_id=window_id,
            start_date=start_date,
            end_date=end_date,
        )
        primary = (
            item.outcome.r_multiple - r108.PRIMARY_STRESS
        ) * item.weight
        secondary = (
            item.outcome.r_multiple - r108.SECONDARY_STRESS
        ) * item.weight

        rows.append(
            {
                "trade_id": item.trade_id,
                "symbol": item.symbol,
                "side": signal.side.value,
                "anchor": str(
                    signal.h4_opened_at.astimezone(v7._NY).hour
                ),
                "poi": item.opportunity.source_poi_kind,
                "period": period,
                "exit_timestamp": item.exited_at.astimezone(UTC).isoformat(),
                "last_state": last_state,
                "extreme_position": extreme_position,
                "late_revalidation": late,
                "rearm": rearm,
                "combined_state": combined,
                "primary_r": str(primary),
                "secondary_r": str(secondary),
            }
        )

    if len(rows) != EXPECTED_STANDARD[window_id]:
        raise ValueError(f"R117 {window_id} row drift")

    return {
        "window_id": window_id,
        "sample": len(rows),
        "expected_sample": EXPECTED_STANDARD[window_id],
        "late_revalidation_count": sum(
            bool(row["late_revalidation"]) for row in rows
        ),
        "rearm_count": sum(bool(row["rearm"]) for row in rows),
        "by_late_revalidation": _group(
            rows,
            lambda row: (
                "LATE_REVALIDATION"
                if bool(row["late_revalidation"])
                else "NO_LATE_REVALIDATION"
            ),
        ),
        "by_last_state": _group(
            rows,
            lambda row: str(row["last_state"]),
        ),
        "by_combined_state": _group(
            rows,
            lambda row: str(row["combined_state"]),
        ),
        "by_rearm": _group(
            rows,
            lambda row: "REARM" if bool(row["rearm"]) else "NO_REARM",
        ),
        "period_x_combined_state": _period_matrix(
            rows,
            field="combined_state",
        ),
        "period_x_late_revalidation": _period_matrix(
            rows,
            field="late_revalidation",
        ),
        "provenance": provenance,
    }


def build_report(
    *,
    nas100_root: Path,
    sp500_root: Path,
    us30_root: Path,
) -> dict[str, Any]:
    if r116.IDENTITY != (
        "VT08_INDEX_R116_ANATOMY_RETEST_EXECUTION_ATTRIBUTION_001"
    ):
        raise ValueError("R117 R116 identity drift")

    roots = {
        "NAS100": nas100_root,
        "SP500": sp500_root,
        "US30": us30_root,
    }
    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "source_r116": {
            "run_id": SOURCE_R116_RUN_ID,
            "artifact_id": SOURCE_R116_ARTIFACT_ID,
            "artifact_digest": SOURCE_R116_ARTIFACT_DIGEST,
            "decision": (
                "R116_ANATOMY_RETEST_EXECUTION_ATTRIBUTION_COMPLETE_NO_RULE_CHANGE"
            ),
        },
        "reused_detector_contract": {
            "implementation": "R55._late_revalidation",
            "source_poi_required": "cisd",
            "continuation_latency_bucket_required": "5+",
            "fresh_liquidity_take_15m_required": True,
            "reaction_after_cisd_required": True,
            "detector_modified": False,
        },
        "preregistered_contract": {
            "rule_change": False,
            "standard_only": True,
            "same_r102_fixed_weights": True,
            "risk_promotion_applied": False,
            "signals_suppressed": False,
            "trade_count_changed": False,
            "target_changed": False,
            "stop_changed": False,
            "entry_changed": False,
            "runtime_filter_created": False,
        },
        "five_year": _window(roots=roots, window_id="5Y"),
        "recent_two_year": _window(roots=roots, window_id="2Y"),
        "r66_failed_holdout": _window(roots=roots, window_id="R66"),
        "decision": "R117_STANDARD_LATE_REVALIDATION_ANATOMY_COMPLETE_NO_RULE_CHANGE",
        "governance": {
            "research_only": True,
            "consumed_evidence_only": True,
            "fresh_holdout_claim": False,
            "candidate_created": False,
            "signals_suppressed": False,
            "trade_count_changed": False,
            "target_changed": False,
            "stop_changed": False,
            "risk_allocator_changed": False,
            "runtime_filter_created": False,
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
            "late_revalidation_count": section["late_revalidation_count"],
            "rearm_count": section["rearm_count"],
            "late_revalidation": section["by_late_revalidation"],
            "combined": section["by_combined_state"],
            "period_x_combined": section["period_x_combined_state"],
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
