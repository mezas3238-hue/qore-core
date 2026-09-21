"""VT08 Index R118 — pre-CISD failed-attempt journey attribution.

R117 showed that the existing late-revalidation state is too sparse to explain
STANDARD failure. R118 audits a deeper implementation choice in V6._first_cisd:
whenever an opposing candle series is followed by a non-opposing candle that
does NOT close through the first opposing candle open, the series is discarded
and scanning restarts. A later series can therefore confirm CISD with a
Protected-Swing extreme that is shallower than an earlier failed attempt.

R118 reproduces the exact V6 reset semantics and records, before the canonical
CISD confirmation:
- number of failed opposing-series attempts;
- whether any failed attempt produced a deeper adverse extreme than the final
  canonical Protected Swing;
- the relation between the deepest prior failed-attempt extreme and the final
  Protected Swing;
- the final R114 extreme position (LAST_BAR vs NOT_LAST_BAR).

These are discrete causal states known by CISD confirmation. No price-distance
threshold, ATR, outcome-derived split, signal suppression, stop replacement or
candidate is created in R118.
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
    vt08_index_r117_standard_late_revalidation_anatomy as r117,
)
from qore.infrastructure.trader_lab import (
    vt08_index_v7_ttrades_source_corrected as v7,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import (
    Vt08IndexC2R1Bar,
)

SCHEMA = "qore.trader_lab.vt08_index_r118_pre_cisd_failed_attempt_journey.v1"
IDENTITY = "VT08_INDEX_R118_PRE_CISD_FAILED_ATTEMPT_JOURNEY_ATTRIBUTION_001"

SOURCE_R117_RUN_ID = 35666961998
SOURCE_R117_ARTIFACT_ID = 10668719511
SOURCE_R117_ARTIFACT_DIGEST = (
    "sha256:966a40d7fb9ff2ae11a48a2de1a83b5dcec59d1f6a804da1f64f8139ad6bd984"
)

EXPECTED_STANDARD = r114.EXPECTED_STANDARD


def _attempt_count_bucket(value: int) -> str:
    if value == 0:
        return "ZERO"
    if value == 1:
        return "ONE"
    return "TWO_PLUS"


def _cisd_journey(
    bars: Sequence[Vt08IndexC2R1Bar],
    *,
    side: DemoTradingSetupSide,
    start_index: int,
) -> dict[str, Any] | None:
    """Exact V6 first-CISD reset semantics plus failed-attempt provenance."""

    sequence_open: Decimal | None = None
    extreme: Decimal | None = None
    sequence_start: int | None = None
    extreme_index: int | None = None
    failed: list[dict[str, Any]] = []

    for index in range(start_index, len(bars)):
        bar = bars[index]
        opposing = (
            bar.close < bar.open
            if side is DemoTradingSetupSide.LONG
            else bar.close > bar.open
        )
        if opposing:
            if sequence_start is None:
                sequence_start = index
                sequence_open = bar.open
                extreme = (
                    bar.low
                    if side is DemoTradingSetupSide.LONG
                    else bar.high
                )
                extreme_index = index
            else:
                assert extreme is not None
                candidate = (
                    min(extreme, bar.low)
                    if side is DemoTradingSetupSide.LONG
                    else max(extreme, bar.high)
                )
                if candidate != extreme:
                    extreme = candidate
                    extreme_index = index
            continue

        if (
            sequence_start is not None
            and sequence_open is not None
            and extreme is not None
            and extreme_index is not None
        ):
            confirmed = (
                bar.close > sequence_open
                if side is DemoTradingSetupSide.LONG
                else bar.close < sequence_open
            )
            if confirmed:
                return {
                    "confirm_index": index,
                    "sequence_start": sequence_start,
                    "sequence_end": index - 1,
                    "sequence_open": sequence_open,
                    "extreme": extreme,
                    "extreme_index": extreme_index,
                    "failed_attempts": tuple(failed),
                }

            failed.append(
                {
                    "sequence_start": sequence_start,
                    "sequence_end": index - 1,
                    "sequence_open": sequence_open,
                    "extreme": extreme,
                    "extreme_index": extreme_index,
                    "failed_on_index": index,
                }
            )

        sequence_open = None
        extreme = None
        sequence_start = None
        extreme_index = None

    return None


def _prior_extreme_relation(
    *,
    side: DemoTradingSetupSide,
    final_extreme: Decimal,
    failed_attempts: Sequence[dict[str, Any]],
) -> str:
    if not failed_attempts:
        return "NO_FAILED_ATTEMPT"

    prior_extremes = tuple(
        Decimal(str(row["extreme"]))
        for row in failed_attempts
    )
    prior_deepest = (
        min(prior_extremes)
        if side is DemoTradingSetupSide.LONG
        else max(prior_extremes)
    )
    if prior_deepest == final_extreme:
        return "FINAL_EQUALS_PRIOR_DEEPEST"
    final_deeper = (
        final_extreme < prior_deepest
        if side is DemoTradingSetupSide.LONG
        else final_extreme > prior_deepest
    )
    return (
        "FINAL_DEEPER_THAN_PRIOR"
        if final_deeper
        else "PRIOR_DEEPER_THAN_FINAL_PS"
    )


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
        raise ValueError(f"R118 {window_id} canonical drift")

    standard_ids = r107._standard_ids(
        control,
        bars_by_symbol=bars_by_symbol,
    )
    if len(standard_ids) != EXPECTED_STANDARD[window_id]:
        raise ValueError(f"R118 {window_id} STANDARD drift")

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
            raise ValueError("R118 canonical H4 missing")

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
            raise ValueError("R118 POI touch missing")

        journey = _cisd_journey(
            inside,
            side=signal.side,
            start_index=touch_index,
        )
        if journey is None:
            raise ValueError("R118 canonical CISD journey missing")

        confirm_index = int(journey["confirm_index"])
        sequence_start = int(journey["sequence_start"])
        sequence_end = int(journey["sequence_end"])
        extreme_index = int(journey["extreme_index"])
        final_extreme = Decimal(str(journey["extreme"]))
        sequence_open = Decimal(str(journey["sequence_open"]))
        failed = tuple(journey["failed_attempts"])

        if inside[confirm_index].closed_at != signal.cisd_confirmed_at:
            raise ValueError("R118 CISD confirmation drift")
        if sequence_open != signal.cisd_level:
            raise ValueError("R118 CISD level drift")
        if final_extreme != signal.protected_swing_extreme:
            raise ValueError("R118 Protected-Swing drift")

        relation = _prior_extreme_relation(
            side=signal.side,
            final_extreme=final_extreme,
            failed_attempts=failed,
        )
        extreme_position = r114._extreme_position(
            sequence_start=sequence_start,
            sequence_end=sequence_end,
            extreme_index=extreme_index,
        )
        last_state = (
            "LAST_BAR"
            if extreme_position == "LAST_BAR"
            else "NOT_LAST_BAR"
        )
        failed_count = len(failed)
        combined = f"{last_state}|{relation}"
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
                "failed_attempt_count": failed_count,
                "failed_attempt_bucket": _attempt_count_bucket(failed_count),
                "prior_extreme_relation": relation,
                "prior_deeper_than_final_ps": (
                    relation == "PRIOR_DEEPER_THAN_FINAL_PS"
                ),
                "last_state": last_state,
                "extreme_position": extreme_position,
                "combined_state": combined,
                "primary_r": str(primary),
                "secondary_r": str(secondary),
            }
        )

    if len(rows) != EXPECTED_STANDARD[window_id]:
        raise ValueError(f"R118 {window_id} row drift")

    return {
        "window_id": window_id,
        "sample": len(rows),
        "expected_sample": EXPECTED_STANDARD[window_id],
        "failed_attempt_present_count": sum(
            int(row["failed_attempt_count"]) > 0 for row in rows
        ),
        "prior_deeper_than_final_ps_count": sum(
            bool(row["prior_deeper_than_final_ps"]) for row in rows
        ),
        "by_failed_attempt_bucket": _group(
            rows,
            lambda row: str(row["failed_attempt_bucket"]),
        ),
        "by_prior_extreme_relation": _group(
            rows,
            lambda row: str(row["prior_extreme_relation"]),
        ),
        "by_last_state": _group(
            rows,
            lambda row: str(row["last_state"]),
        ),
        "by_combined_state": _group(
            rows,
            lambda row: str(row["combined_state"]),
        ),
        "period_x_prior_extreme_relation": _period_matrix(
            rows,
            field="prior_extreme_relation",
        ),
        "period_x_combined_state": _period_matrix(
            rows,
            field="combined_state",
        ),
        "provenance": provenance,
    }


def build_report(
    *,
    nas100_root: Path,
    sp500_root: Path,
    us30_root: Path,
) -> dict[str, Any]:
    if r117.IDENTITY != (
        "VT08_INDEX_R117_STANDARD_LATE_REVALIDATION_ANATOMY_ATTRIBUTION_001"
    ):
        raise ValueError("R118 R117 identity drift")

    roots = {
        "NAS100": nas100_root,
        "SP500": sp500_root,
        "US30": us30_root,
    }
    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "source_r117": {
            "run_id": SOURCE_R117_RUN_ID,
            "artifact_id": SOURCE_R117_ARTIFACT_ID,
            "artifact_digest": SOURCE_R117_ARTIFACT_DIGEST,
            "decision": (
                "R117_STANDARD_LATE_REVALIDATION_ANATOMY_COMPLETE_NO_RULE_CHANGE"
            ),
        },
        "reset_semantics_under_audit": {
            "implementation_reference": "V6._first_cisd",
            "failed_series_is_discarded": True,
            "later_series_can_confirm_new_cisd": True,
            "classification_cutoff": "CANONICAL_CISD_CONFIRMATION",
            "numeric_price_threshold_used": False,
            "outcome_used_for_classification": False,
            "calendar_or_year_used_for_classification": False,
        },
        "preregistered_contract": {
            "rule_change": False,
            "standard_only": True,
            "same_r102_fixed_weights": True,
            "signals_suppressed": False,
            "trade_count_changed": False,
            "entry_changed": False,
            "stop_changed": False,
            "target_changed": False,
            "runtime_filter_created": False,
            "candidate_created": False,
        },
        "five_year": _window(roots=roots, window_id="5Y"),
        "recent_two_year": _window(roots=roots, window_id="2Y"),
        "r66_failed_holdout": _window(roots=roots, window_id="R66"),
        "decision": "R118_PRE_CISD_FAILED_ATTEMPT_JOURNEY_COMPLETE_NO_RULE_CHANGE",
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
            "failed_attempt_present_count": section[
                "failed_attempt_present_count"
            ],
            "prior_deeper_than_final_ps_count": section[
                "prior_deeper_than_final_ps_count"
            ],
            "failed_attempt_bucket": section["by_failed_attempt_bucket"],
            "prior_extreme_relation": section["by_prior_extreme_relation"],
            "combined": section["by_combined_state"],
            "period_x_relation": section[
                "period_x_prior_extreme_relation"
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
