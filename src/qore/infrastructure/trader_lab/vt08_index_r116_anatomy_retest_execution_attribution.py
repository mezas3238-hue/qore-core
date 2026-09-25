"""VT08 Index R116 — CISD anatomy x source-retest execution attribution.

R114 found LAST_BAR to be a transported adverse STANDARD anatomy. R115 proved
that the entire STANDARD surface is, by construction, R82
UNQUALIFIED_GENERIC_CISD; therefore R82 qualification cannot be used to explain
or gate STANDARD without reintroducing the already-falsified universal
Protected-Swing requirement.

R116 tests the next source-authorized explanation without changing signals:
whether the same STANDARD setup behaves differently under the continuation
close versus the source-valid continuation retest already frozen in R108.

For every STANDARD setup:
- reconstruct exact R114 CISD/Protected-Swing anatomy at CISD confirmation;
- preserve canonical continuation-close economics;
- detect the exact R89/R108 retest path;
- where a retest exists, replay that same setup with the same Protected Swing,
  fixed 2.5R target and frozen R102 weight;
- report retest availability, baseline/retest economics and delta by anatomy,
  especially LAST_BAR versus NOT_LAST_BAR, plus temporal blocks.

Retest is never a second trade. No fallback or suppression policy is created in
R116. No runtime rule, candidate, target, stop, allocator, market, side or
anchor change is permitted.
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
    vt08_index_r109_standard_retest_timing_decay_attribution as r109,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r114_standard_cisd_ps_anatomy_attribution as r114,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r115_last_extreme_source_qualification as r115,
)
from qore.infrastructure.trader_lab import (
    vt08_index_v7_ttrades_source_corrected as v7,
)
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import (
    Vt08IndexC2R1Bar,
)

SCHEMA = "qore.trader_lab.vt08_index_r116_anatomy_retest_execution_attribution.v1"
IDENTITY = "VT08_INDEX_R116_ANATOMY_RETEST_EXECUTION_ATTRIBUTION_001"

SOURCE_R115_RUN_ID = 35666028472
SOURCE_R115_ARTIFACT_ID = 10669327043
SOURCE_R115_ARTIFACT_DIGEST = (
    "sha256:86c7b0851e39f78fa6d5bc3c8d8c961d53cde79acb5011570c9753e6a3ddbbc4"
)

EXPECTED_STANDARD = r114.EXPECTED_STANDARD
EXPECTED_RETEST = r108.EXPECTED_RETEST


def _metrics(
    rows: Sequence[dict[str, Any]],
    *,
    field: str,
) -> dict[str, Any]:
    ordered = sorted(
        rows,
        key=lambda row: (
            str(row["baseline_exit_timestamp"]),
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

    result: dict[str, Any] = {}
    for label, items in sorted(grouped.items()):
        retest = [row for row in items if bool(row["retest_available"])]
        delta_primary = sum(
            (
                Decimal(str(row["retest_primary_r"]))
                - Decimal(str(row["baseline_primary_r"]))
                for row in retest
            ),
            Decimal(),
        )
        delta_secondary = sum(
            (
                Decimal(str(row["retest_secondary_r"]))
                - Decimal(str(row["baseline_secondary_r"]))
                for row in retest
            ),
            Decimal(),
        )
        result[label] = {
            "sample": len(items),
            "baseline_primary_all": _metrics(
                items,
                field="baseline_primary_r",
            ),
            "baseline_secondary_all": _metrics(
                items,
                field="baseline_secondary_r",
            ),
            "retest_available_count": len(retest),
            "retest_available_fraction": (
                str(Decimal(len(retest)) / Decimal(len(items)))
                if items
                else "0"
            ),
            "baseline_primary_retest_available": (
                _metrics(retest, field="baseline_primary_r")
                if retest
                else None
            ),
            "baseline_secondary_retest_available": (
                _metrics(retest, field="baseline_secondary_r")
                if retest
                else None
            ),
            "retest_primary": (
                _metrics(retest, field="retest_primary_r")
                if retest
                else None
            ),
            "retest_secondary": (
                _metrics(retest, field="retest_secondary_r")
                if retest
                else None
            ),
            "retest_primary_delta_r": str(delta_primary),
            "retest_secondary_delta_r": str(delta_secondary),
            "close_fallback_count_if_retest_required": len(items) - len(retest),
        }
    return result


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
        raise ValueError(f"R116 {window_id} canonical drift")

    standard_ids = r107._standard_ids(
        control,
        bars_by_symbol=bars_by_symbol,
    )
    if len(standard_ids) != EXPECTED_STANDARD[window_id]:
        raise ValueError(f"R116 {window_id} STANDARD drift")

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
            raise ValueError("R116 canonical H4 missing")

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
            raise ValueError("R116 POI touch missing")

        anatomy = r114._trace_anatomy(
            inside,
            side=signal.side,
            start_index=touch_index,
        )
        if anatomy is None:
            raise ValueError("R116 CISD anatomy missing")
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
            raise ValueError("R116 continuation bar missing")

        retest_index = r89._retest_fill_index(
            inside,
            continuation_index=continuation_index,
            side=signal.side,
            protected_swing=signal.protected_swing_extreme,
            model_kind=signal.model_kind,
            h4_open=inside[0].open,
        )

        baseline_primary = (
            item.outcome.r_multiple - r108.PRIMARY_STRESS
        ) * item.weight
        baseline_secondary = (
            item.outcome.r_multiple - r108.SECONDARY_STRESS
        ) * item.weight

        retest_primary: Decimal | None = None
        retest_secondary: Decimal | None = None
        retest_delay_bars: int | None = None
        if retest_index is not None:
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
            retest_primary = (
                new_outcome.r_multiple - r108.PRIMARY_STRESS
            ) * item.weight
            retest_secondary = (
                new_outcome.r_multiple - r108.SECONDARY_STRESS
            ) * item.weight
            retest_delay_bars = retest_index - continuation_index

        period = r109._period_label(
            exit_date=item.exited_at.astimezone(v7._NY).date(),
            window_id=window_id,
            start_date=start_date,
            end_date=end_date,
        )
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
                "baseline_exit_timestamp": (
                    item.exited_at.astimezone(UTC).isoformat()
                ),
                "extreme_position": extreme_position,
                "last_state": last_state,
                "series_length_bucket": r114._series_length_bucket(
                    int(anatomy["series_length"])
                ),
                "retest_available": retest_index is not None,
                "retest_delay_bars": retest_delay_bars,
                "baseline_primary_r": str(baseline_primary),
                "baseline_secondary_r": str(baseline_secondary),
                "retest_primary_r": (
                    str(retest_primary)
                    if retest_primary is not None
                    else None
                ),
                "retest_secondary_r": (
                    str(retest_secondary)
                    if retest_secondary is not None
                    else None
                ),
            }
        )

    if len(rows) != EXPECTED_STANDARD[window_id]:
        raise ValueError(f"R116 {window_id} row drift")
    retest_count = sum(bool(row["retest_available"]) for row in rows)
    if retest_count != EXPECTED_RETEST[window_id]:
        raise ValueError(f"R116 {window_id} retest coverage drift")

    return {
        "window_id": window_id,
        "sample": len(rows),
        "expected_sample": EXPECTED_STANDARD[window_id],
        "retest_available_count": retest_count,
        "expected_retest_available_count": EXPECTED_RETEST[window_id],
        "by_last_state": _group(
            rows,
            lambda row: str(row["last_state"]),
        ),
        "by_extreme_position": _group(
            rows,
            lambda row: str(row["extreme_position"]),
        ),
        "by_series_length": _group(
            rows,
            lambda row: str(row["series_length_bucket"]),
        ),
        "period_x_last_state": _period_matrix(
            rows,
            field="last_state",
        ),
        "period_x_extreme_position": _period_matrix(
            rows,
            field="extreme_position",
        ),
        "provenance": provenance,
    }


def build_report(
    *,
    nas100_root: Path,
    sp500_root: Path,
    us30_root: Path,
) -> dict[str, Any]:
    if r115.IDENTITY != (
        "VT08_INDEX_R115_LAST_EXTREME_SOURCE_QUALIFICATION_ATTRIBUTION_001"
    ):
        raise ValueError("R116 R115 identity drift")

    roots = {
        "NAS100": nas100_root,
        "SP500": sp500_root,
        "US30": us30_root,
    }
    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "source_r115": {
            "run_id": SOURCE_R115_RUN_ID,
            "artifact_id": SOURCE_R115_ARTIFACT_ID,
            "artifact_digest": SOURCE_R115_ARTIFACT_DIGEST,
            "decision": (
                "R115_LAST_EXTREME_SOURCE_QUALIFICATION_COMPLETE_NO_RULE_CHANGE"
            ),
        },
        "preregistered_contract": {
            "rule_change": False,
            "same_setup_only": True,
            "retest_creates_second_trade": False,
            "standard_only": True,
            "same_r102_fixed_weights": True,
            "same_protected_swing_stop": True,
            "same_target_r": str(r108.TARGET_R),
            "retest_bar_target_credit_allowed": False,
            "retest_required_policy_created": False,
            "fallback_policy_changed": False,
            "signals_suppressed": False,
            "trade_count_changed": False,
            "runtime_filter_created": False,
        },
        "five_year": _window(roots=roots, window_id="5Y"),
        "recent_two_year": _window(roots=roots, window_id="2Y"),
        "r66_failed_holdout": _window(roots=roots, window_id="R66"),
        "decision": "R116_ANATOMY_RETEST_EXECUTION_ATTRIBUTION_COMPLETE_NO_RULE_CHANGE",
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
            "retest_available_count": section["retest_available_count"],
            "last_state": section["by_last_state"],
            "extreme_position": section["by_extreme_position"],
            "period_x_last_state": section["period_x_last_state"],
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
