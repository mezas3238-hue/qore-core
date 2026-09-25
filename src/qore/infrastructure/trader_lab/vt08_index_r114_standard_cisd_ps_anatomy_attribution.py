"""VT08 Index R114 — STANDARD CISD / Protected-Swing anatomy attribution.

R112 mathematically falsified same-M15 ordering as the R66 B2 root cause. R113
is resolving the handful of remaining ambiguities with native M1 for evidence
closure. R114 moves upstream to the source object that defines the STANDARD
stop: the contiguous opposing M15 candle series closed through by CISD.

The exact V6/R82 CISD semantics are reproduced and every STANDARD setup is
classified before economics using discrete, source-interpretable anatomy only:

- opposing-series length: ONE / TWO / THREE_PLUS;
- whether the opposing series begins on the POI-touch M15 or later;
- whether the first opposing-series bar physically overlaps the source POI;
- where the Protected-Swing extreme is formed inside the series:
  ONLY / FIRST / INTERIOR / LAST;
- how many M15 slots after POI touch the series begins and the extreme forms
  (0 / 1 / 2_PLUS);
- whether the protected extreme is created on the POI-touch bar itself.

No price-distance threshold, ATR, percentage, wick/body cutoff, outcome filter
or calendar feature is introduced. The exact R102 fixed weights and canonical
STANDARD_WITHOUT_EXTRA_PS surface remain unchanged. This stage is attribution
only and creates no candidate.
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
    vt08_index_r112_same_m15_ambiguity_census as r112,
)
from qore.infrastructure.trader_lab import (
    vt08_index_v7_ttrades_source_corrected as v7,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import (
    Vt08IndexC2R1Bar,
)

SCHEMA = "qore.trader_lab.vt08_index_r114_standard_cisd_ps_anatomy_attribution.v1"
IDENTITY = "VT08_INDEX_R114_STANDARD_CISD_PS_ANATOMY_ATTRIBUTION_001"

SOURCE_R112_RUN_ID = 35661839898
SOURCE_R112_ARTIFACT_ID = 10667714516
SOURCE_R112_ARTIFACT_DIGEST = (
    "sha256:e0b2dfd0363c2920ba7566672ffef05264d69fbfb4778e81de8568dba05f0e53"
)

EXPECTED_STANDARD = {"5Y": 1756, "2Y": 746, "R66": 546}


def _slot_bucket(value: int) -> str:
    if value <= 0:
        return "M15_0"
    if value == 1:
        return "M15_1"
    return "M15_2_PLUS"


def _series_length_bucket(value: int) -> str:
    if value == 1:
        return "ONE"
    if value == 2:
        return "TWO"
    return "THREE_PLUS"


def _trace_anatomy(
    bars: Sequence[Vt08IndexC2R1Bar],
    *,
    side: DemoTradingSetupSide,
    start_index: int,
) -> dict[str, Any] | None:
    sequence_open: Decimal | None = None
    extreme: Decimal | None = None
    sequence_start: int | None = None
    extreme_index: int | None = None
    in_sequence = False

    for index in range(start_index, len(bars)):
        bar = bars[index]
        opposing = (
            bar.close < bar.open
            if side is DemoTradingSetupSide.LONG
            else bar.close > bar.open
        )
        if opposing:
            if not in_sequence:
                sequence_open = bar.open
                extreme = (
                    bar.low
                    if side is DemoTradingSetupSide.LONG
                    else bar.high
                )
                sequence_start = index
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
            in_sequence = True
            continue

        if (
            in_sequence
            and sequence_open is not None
            and extreme is not None
            and sequence_start is not None
            and extreme_index is not None
        ):
            confirmed = (
                bar.close > sequence_open
                if side is DemoTradingSetupSide.LONG
                else bar.close < sequence_open
            )
            if confirmed:
                sequence_end = index - 1
                return {
                    "confirm_index": index,
                    "sequence_start": sequence_start,
                    "sequence_end": sequence_end,
                    "sequence_open": sequence_open,
                    "extreme": extreme,
                    "extreme_index": extreme_index,
                    "series_length": sequence_end - sequence_start + 1,
                }

        sequence_open = None
        extreme = None
        sequence_start = None
        extreme_index = None
        in_sequence = False
    return None


def _extreme_position(
    *,
    sequence_start: int,
    sequence_end: int,
    extreme_index: int,
) -> str:
    if sequence_start == sequence_end:
        return "ONLY_BAR"
    if extreme_index == sequence_start:
        return "FIRST_BAR"
    if extreme_index == sequence_end:
        return "LAST_BAR"
    return "INTERIOR_BAR"


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
        "wins": sum(value > 0 for value in values),
        "losses": sum(value < 0 for value in values),
        "flats": sum(value == 0 for value in values),
        "total_r": str(total),
        "mean_r": str(total / Decimal(len(values))) if values else "0",
        "profit_factor": str(gains / losses) if losses else None,
        "max_drawdown_r": str(dd),
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
        raise ValueError(f"R114 {window_id} canonical drift")

    standard_ids = r107._standard_ids(
        control,
        bars_by_symbol=bars_by_symbol,
    )
    if len(standard_ids) != EXPECTED_STANDARD[window_id]:
        raise ValueError(f"R114 {window_id} STANDARD drift")

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
            raise ValueError("R114 canonical H4 missing")
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
            raise ValueError("R114 POI touch missing")

        trace = _trace_anatomy(
            inside,
            side=signal.side,
            start_index=touch_index,
        )
        if trace is None:
            raise ValueError("R114 canonical CISD anatomy missing")

        confirm_index = int(trace["confirm_index"])
        sequence_start = int(trace["sequence_start"])
        sequence_end = int(trace["sequence_end"])
        extreme_index = int(trace["extreme_index"])
        if inside[confirm_index].closed_at != signal.cisd_confirmed_at:
            raise ValueError("R114 CISD confirmation drift")
        if Decimal(str(trace["sequence_open"])) != signal.cisd_level:
            raise ValueError("R114 CISD level drift")
        if Decimal(str(trace["extreme"])) != signal.protected_swing_extreme:
            raise ValueError("R114 Protected-Swing drift")

        series_length = int(trace["series_length"])
        start_delay = sequence_start - touch_index
        extreme_delay = extreme_index - touch_index
        start_bar = inside[sequence_start]
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
                "series_length": series_length,
                "series_length_bucket": _series_length_bucket(series_length),
                "series_start_delay": start_delay,
                "series_start_delay_bucket": _slot_bucket(start_delay),
                "extreme_delay": extreme_delay,
                "extreme_delay_bucket": _slot_bucket(extreme_delay),
                "series_starts_on_poi_touch": sequence_start == touch_index,
                "series_start_overlaps_poi": signal.poi.touched_by(start_bar),
                "extreme_on_poi_touch": extreme_index == touch_index,
                "extreme_position": _extreme_position(
                    sequence_start=sequence_start,
                    sequence_end=sequence_end,
                    extreme_index=extreme_index,
                ),
                "primary_r": str(primary),
                "secondary_r": str(secondary),
            }
        )

    if len(rows) != EXPECTED_STANDARD[window_id]:
        raise ValueError(f"R114 {window_id} row drift")

    dimensions: dict[str, Callable[[dict[str, Any]], str]] = {
        "series_length": lambda row: str(row["series_length_bucket"]),
        "series_start_delay": lambda row: str(row["series_start_delay_bucket"]),
        "extreme_delay": lambda row: str(row["extreme_delay_bucket"]),
        "series_starts_on_poi_touch": lambda row: str(
            row["series_starts_on_poi_touch"]
        ),
        "series_start_overlaps_poi": lambda row: str(
            row["series_start_overlaps_poi"]
        ),
        "extreme_on_poi_touch": lambda row: str(row["extreme_on_poi_touch"]),
        "extreme_position": lambda row: str(row["extreme_position"]),
        "market": lambda row: str(row["symbol"]),
        "side": lambda row: str(row["side"]),
        "anchor": lambda row: str(row["anchor"]),
        "poi": lambda row: str(row["poi"]),
        "period": lambda row: str(row["period"]),
    }

    return {
        "window_id": window_id,
        "sample": len(rows),
        "expected_sample": EXPECTED_STANDARD[window_id],
        "overall": {
            "primary": _metrics(rows, field="primary_r"),
            "secondary": _metrics(rows, field="secondary_r"),
        },
        "dimensions": {
            name: _group(rows, selector)
            for name, selector in dimensions.items()
        },
        "period_x_series_length": _period_matrix(
            rows,
            field="series_length_bucket",
        ),
        "period_x_extreme_position": _period_matrix(
            rows,
            field="extreme_position",
        ),
        "period_x_series_start_delay": _period_matrix(
            rows,
            field="series_start_delay_bucket",
        ),
        "period_x_extreme_delay": _period_matrix(
            rows,
            field="extreme_delay_bucket",
        ),
        "provenance": provenance,
    }


def build_report(
    *,
    nas100_root: Path,
    sp500_root: Path,
    us30_root: Path,
) -> dict[str, Any]:
    if r112.IDENTITY != (
        "VT08_INDEX_R112_STANDARD_SAME_M15_AMBIGUITY_CENSUS_001"
    ):
        raise ValueError("R114 R112 identity drift")

    roots = {
        "NAS100": nas100_root,
        "SP500": sp500_root,
        "US30": us30_root,
    }
    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "source_r112": {
            "run_id": SOURCE_R112_RUN_ID,
            "artifact_id": SOURCE_R112_ARTIFACT_ID,
            "artifact_digest": SOURCE_R112_ARTIFACT_DIGEST,
        },
        "source_contract": {
            "protected_swing": "EXTREME_OF_CISD_OPPOSING_SERIES",
            "numeric_price_thresholds": False,
            "atr_or_percentage_cutoff": False,
            "classification_cutoff": "CISD_CONFIRMATION",
            "outcome_used_for_classification": False,
            "calendar_or_year_used_for_classification": False,
        },
        "five_year": _window(roots=roots, window_id="5Y"),
        "recent_two_year": _window(roots=roots, window_id="2Y"),
        "r66_failed_holdout": _window(roots=roots, window_id="R66"),
        "decision": "R114_STANDARD_CISD_PS_ANATOMY_ATTRIBUTION_COMPLETE_NO_RULE_CHANGE",
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
            "overall": section["overall"],
            "series_length": section["dimensions"]["series_length"],
            "series_start_delay": section["dimensions"]["series_start_delay"],
            "extreme_delay": section["dimensions"]["extreme_delay"],
            "series_starts_on_poi_touch": section["dimensions"][
                "series_starts_on_poi_touch"
            ],
            "series_start_overlaps_poi": section["dimensions"][
                "series_start_overlaps_poi"
            ],
            "extreme_position": section["dimensions"]["extreme_position"],
            "period_x_series_length": section["period_x_series_length"],
            "period_x_extreme_position": section["period_x_extreme_position"],
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
