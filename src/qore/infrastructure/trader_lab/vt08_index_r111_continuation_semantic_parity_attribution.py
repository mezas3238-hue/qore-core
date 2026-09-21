"""VT08 Index R111 — continuation semantic parity attribution.

R110 found one transported adverse geometry: continuation candles with very
small bodies. The V6 freeze explicitly forbids wick/body ratio thresholds, so
that observation cannot become a rule. R111 instead tests source semantics with
no numeric cutoff and no rule change.

The current V6 continuation scanner accepts a bar whenever its high/low breaks
the previous bar and its close finishes beyond that previous extreme. R111
classifies every STANDARD continuation, using only information known at its
close, into discrete semantic states:

- continuation body is bias-direction / opposing-direction / doji;
- the bar crosses the previous extreme from inside/at the level, or opens
  already beyond it;
- the immediately previous M15 body is bias-direction / opposing / doji;
- the combined body-direction + breakout-origin state.

Economic outcomes are attached only after classification. The exact R102 fixed
weights and canonical STANDARD surface remain unchanged. Period x semantic
cross-tabs are emitted explicitly so R66 B2 can be compared with B1 and the
other consumed windows without using calendar state as a runtime feature.

This is forensic attribution only. It creates no filter, candidate, LIVE,
real-capital or production authority.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from collections.abc import Callable, Sequence
from decimal import Decimal
from pathlib import Path
from typing import Any

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
    vt08_index_r110_standard_entry_ps_geometry_attribution as r110,
)
from qore.infrastructure.trader_lab import (
    vt08_index_v7_ttrades_source_corrected as v7,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import (
    Vt08IndexC2R1Bar,
)

SCHEMA = "qore.trader_lab.vt08_index_r111_continuation_semantic_parity_attribution.v1"
IDENTITY = "VT08_INDEX_R111_CONTINUATION_SEMANTIC_PARITY_ATTRIBUTION_001"

SOURCE_R110_RUN_ID = 35660671874
SOURCE_R110_ARTIFACT_ID = 10667527471
SOURCE_R110_ARTIFACT_DIGEST = (
    "sha256:cdf274169f12d74126b4be417b2a1ac2baa4f8051895d883a393e79877ac4f42"
)

EXPECTED_STANDARD = r110.EXPECTED_STANDARD


def _body_state(
    *,
    side: DemoTradingSetupSide,
    open_: Decimal,
    close: Decimal,
) -> str:
    if close == open_:
        return "DOJI"
    bias_direction = (
        close > open_
        if side is DemoTradingSetupSide.LONG
        else close < open_
    )
    return "BIAS_DIRECTION_BODY" if bias_direction else "OPPOSING_BODY"


def _breakout_origin(
    *,
    side: DemoTradingSetupSide,
    open_: Decimal,
    previous_high: Decimal,
    previous_low: Decimal,
) -> str:
    opened_beyond = (
        open_ > previous_high
        if side is DemoTradingSetupSide.LONG
        else open_ < previous_low
    )
    return "OPENED_BEYOND_PREVIOUS_EXTREME" if opened_beyond else "CROSSED_EXTREME_DURING_BAR"


def _weighted_metrics(
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
        "mean_r": str(total / len(values)) if values else "0",
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
            "primary": _weighted_metrics(items, field="primary_r"),
            "secondary": _weighted_metrics(items, field="secondary_r"),
        }
        for label, items in sorted(grouped.items())
    }


def _period_semantic_matrix(
    rows: Sequence[dict[str, Any]],
    *,
    semantic_field: str,
) -> dict[str, Any]:
    periods: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        periods[str(row["period"])].append(row)
    return {
        period: _group(
            items,
            lambda row: str(row[semantic_field]),
        )
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
        raise ValueError(f"R111 {window_id} canonical drift")

    standard_ids = r107._standard_ids(
        control,
        bars_by_symbol=bars_by_symbol,
    )
    if len(standard_ids) != EXPECTED_STANDARD[window_id]:
        raise ValueError(f"R111 {window_id} STANDARD drift")

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
            signal.h4_opened_at
        )
        if inside is None:
            raise ValueError("R111 canonical H4 missing")

        continuation_index = next(
            (
                index
                for index, bar in enumerate(inside)
                if bar.closed_at == signal.signal_at
            ),
            None,
        )
        if continuation_index is None or continuation_index <= 0:
            raise ValueError("R111 continuation bar missing")

        continuation = inside[continuation_index]
        previous = inside[continuation_index - 1]

        continuation_body = _body_state(
            side=signal.side,
            open_=continuation.open,
            close=continuation.close,
        )
        previous_body = _body_state(
            side=signal.side,
            open_=previous.open,
            close=previous.close,
        )
        origin = _breakout_origin(
            side=signal.side,
            open_=continuation.open,
            previous_high=previous.high,
            previous_low=previous.low,
        )
        combined = f"{continuation_body}|{origin}"

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
                "period": period,
                "exit_timestamp": item.exited_at.isoformat(),
                "continuation_body_state": continuation_body,
                "breakout_origin": origin,
                "previous_body_state": previous_body,
                "combined_semantic_state": combined,
                "primary_r": str(primary),
                "secondary_r": str(secondary),
            }
        )

    if len(rows) != EXPECTED_STANDARD[window_id]:
        raise ValueError(f"R111 {window_id} STANDARD row drift")

    return {
        "window_id": window_id,
        "sample": len(rows),
        "expected_sample": EXPECTED_STANDARD[window_id],
        "overall": {
            "primary": _weighted_metrics(rows, field="primary_r"),
            "secondary": _weighted_metrics(rows, field="secondary_r"),
        },
        "by_continuation_body_state": _group(
            rows,
            lambda row: str(row["continuation_body_state"]),
        ),
        "by_breakout_origin": _group(
            rows,
            lambda row: str(row["breakout_origin"]),
        ),
        "by_previous_body_state": _group(
            rows,
            lambda row: str(row["previous_body_state"]),
        ),
        "by_combined_semantic_state": _group(
            rows,
            lambda row: str(row["combined_semantic_state"]),
        ),
        "period_x_continuation_body_state": _period_semantic_matrix(
            rows,
            semantic_field="continuation_body_state",
        ),
        "period_x_breakout_origin": _period_semantic_matrix(
            rows,
            semantic_field="breakout_origin",
        ),
        "period_x_combined_semantic_state": _period_semantic_matrix(
            rows,
            semantic_field="combined_semantic_state",
        ),
        "provenance": provenance,
    }


def build_report(
    *,
    nas100_root: Path,
    sp500_root: Path,
    us30_root: Path,
) -> dict[str, Any]:
    if r110.IDENTITY != (
        "VT08_INDEX_R110_STANDARD_ENTRY_PS_GEOMETRY_ATTRIBUTION_001"
    ):
        raise ValueError("R111 R110 identity drift")

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
        "source_r110": {
            "run_id": SOURCE_R110_RUN_ID,
            "artifact_id": SOURCE_R110_ARTIFACT_ID,
            "artifact_digest": SOURCE_R110_ARTIFACT_DIGEST,
            "decision": "R110_STANDARD_ENTRY_PS_GEOMETRY_ATTRIBUTION_COMPLETE_NO_RULE_CHANGE",
        },
        "source_semantic_basis": {
            "v6_no_numeric_wick_body_cutoff": True,
            "continuation_confirmation_m15_close": True,
            "same_c2_wick_then_body_logic": True,
            "discrete_semantics_only": True,
        },
        "preregistered_contract": {
            "rule_change": False,
            "same_r102_fixed_weights": True,
            "standard_only": True,
            "classification_cutoff": "CONTINUATION_CLOSE",
            "numeric_body_threshold_used": False,
            "outcome_used_for_classification": False,
            "calendar_or_year_used_for_classification": False,
            "period_only_for_post_classification_attribution": True,
            "signals_suppressed": False,
            "trade_count_changed": False,
            "runtime_filter_created": False,
        },
        "five_year": five,
        "recent_two_year": two,
        "r66_failed_holdout": failed,
        "decision": "R111_CONTINUATION_SEMANTIC_PARITY_ATTRIBUTION_COMPLETE_NO_RULE_CHANGE",
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
            "overall": section["overall"],
            "body": section["by_continuation_body_state"],
            "origin": section["by_breakout_origin"],
            "combined": section["by_combined_semantic_state"],
            "period_x_body": section["period_x_continuation_body_state"],
            "period_x_combined": section[
                "period_x_combined_semantic_state"
            ],
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
