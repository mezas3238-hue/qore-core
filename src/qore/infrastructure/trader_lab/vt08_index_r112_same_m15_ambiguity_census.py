"""VT08 Index R112 — STANDARD same-M15 STOP/TARGET ambiguity census.

R111 falsified a simple continuation-semantic explanation for R66 B2. The next
frozen investigation path is execution precedence. Canonical VT08 historical
management is deliberately conservative: after gap handling, if a single M15
bar contains both the structural stop and fixed 2.5R target, STOP is adjudicated
first because M15 OHLC cannot reveal which level traded first.

R112 does not change that rule and does not replay target-first results as a
candidate. It measures the exact ambiguity surface on the fixed R102-weighted
STANDARD_WITHOUT_EXTRA_PS cohort:

- whether the canonical exit M15 contains both stop and 2.5R target;
- the current STOP-first weighted result;
- a TARGET-first *upper-bound uncertainty envelope* only, to quantify how much
  ordering uncertainty could theoretically matter before acquiring M1;
- concentration by temporal block, market, side, anchor and POI.

Classification uses the already-completed exit bar only because this stage is
execution forensics, not signal generation. No ambiguity state becomes a
runtime feature. Signal count, target, stop, allocator and anchors remain
unchanged.

If R66 B2 contains any genuine same-M15 ambiguity, native-M1 ordering resolution
is scientifically warranted for those exact bars. If it contains none, the M1
precedence route is closed without provider replay.
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
    vt08_index_cibo_2y_management_round5 as r5,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r58_exact_r47_distributed_risk as r58,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r74_ambiguous_bias_resolvers as r74,
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
    vt08_index_r111_continuation_semantic_parity_attribution as r111,
)
from qore.infrastructure.trader_lab import vt08_index_v2_candidate as v2
from qore.infrastructure.trader_lab import (
    vt08_index_v7_ttrades_source_corrected as v7,
)
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import (
    Vt08IndexC2R1Bar,
)

SCHEMA = "qore.trader_lab.vt08_index_r112_same_m15_ambiguity_census.v1"
IDENTITY = "VT08_INDEX_R112_STANDARD_SAME_M15_AMBIGUITY_CENSUS_001"

SOURCE_R111_RUN_ID = 35661275019
SOURCE_R111_ARTIFACT_ID = 10666554085
SOURCE_R111_ARTIFACT_DIGEST = (
    "sha256:f80a38fa197f005ec50f16d7f05ac640e19d86d9aad30c501c5ca45959850ed4"
)

TARGET_R = Decimal("2.5")
EXPECTED_STANDARD = {"5Y": 1756, "2Y": 746, "R66": 546}


def _touches(
    bar: Vt08IndexC2R1Bar,
    level: Decimal,
) -> bool:
    return bar.low <= level <= bar.high


def _is_same_m15_ambiguous(
    *,
    signal: Any,
    exit_bar: Vt08IndexC2R1Bar,
) -> bool:
    target = r5._price_at_r(signal, TARGET_R)
    gap = v2._gap_exit(
        side=signal.side,
        bar=exit_bar,
        stop=signal.stop,
        target=target,
    )
    if gap is not None:
        return False
    return _touches(exit_bar, signal.stop) and _touches(exit_bar, target)


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

    result: dict[str, Any] = {}
    for label, items in sorted(grouped.items()):
        ambiguous = [row for row in items if bool(row["same_m15_ambiguous"])]
        delta = sum(
            (
                Decimal(str(row["target_first_upper_delta_r"]))
                for row in ambiguous
            ),
            Decimal(),
        )
        actual_primary = _metrics(items, field="primary_r")
        actual_secondary = _metrics(items, field="secondary_r")
        result[label] = {
            "sample": len(items),
            "ambiguous_count": len(ambiguous),
            "ambiguous_fraction": (
                str(Decimal(len(ambiguous)) / Decimal(len(items)))
                if items
                else "0"
            ),
            "actual_primary": actual_primary,
            "actual_secondary": actual_secondary,
            "target_first_upper_bound_delta_r": str(delta),
            "primary_total_upper_bound_if_all_ambiguities_target_first": str(
                Decimal(str(actual_primary["total_r"])) + delta
            ),
            "secondary_total_upper_bound_if_all_ambiguities_target_first": str(
                Decimal(str(actual_secondary["total_r"])) + delta
            ),
        }
    return result


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
        raise ValueError(f"R112 {window_id} canonical drift")

    standard_ids = r107._standard_ids(
        control,
        bars_by_symbol=bars_by_symbol,
    )
    if len(standard_ids) != EXPECTED_STANDARD[window_id]:
        raise ValueError(f"R112 {window_id} STANDARD drift")

    exit_bars = {
        symbol: {
            bar.closed_at.astimezone(UTC): bar
            for bar in bars
        }
        for symbol, bars in bars_by_symbol.items()
    }

    rows: list[dict[str, Any]] = []
    for item in control:
        if item.opportunity.identity() not in standard_ids:
            continue
        signal = item.opportunity.signal
        exit_at = item.outcome.exited_at.astimezone(UTC)
        exit_bar = exit_bars[item.symbol].get(exit_at)
        if exit_bar is None:
            raise ValueError("R112 canonical exit bar missing")

        target = r5._price_at_r(signal, TARGET_R)
        ambiguous = _is_same_m15_ambiguous(
            signal=signal,
            exit_bar=exit_bar,
        )
        if ambiguous and item.outcome.exit_reason != "stop":
            raise ValueError(
                "R112 same-M15 ambiguity did not resolve STOP-first canonically"
            )

        primary = (
            item.outcome.r_multiple - r108.PRIMARY_STRESS
        ) * item.weight
        secondary = (
            item.outcome.r_multiple - r108.SECONDARY_STRESS
        ) * item.weight
        # Stress is identical in both adjudications, so the uncertainty delta
        # is simply target-R minus actual outcome, scaled by frozen weight.
        upper_delta = (
            (TARGET_R - item.outcome.r_multiple) * item.weight
            if ambiguous
            else Decimal()
        )
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
                "signal_timestamp": signal.signal_at.astimezone(UTC).isoformat(),
                "exit_timestamp": exit_at.isoformat(),
                "entry": str(signal.entry),
                "stop": str(signal.stop),
                "target_2_5r": str(target),
                "exit_bar_open": str(exit_bar.open),
                "exit_bar_high": str(exit_bar.high),
                "exit_bar_low": str(exit_bar.low),
                "exit_bar_close": str(exit_bar.close),
                "exit_reason": item.outcome.exit_reason,
                "same_m15_ambiguous": ambiguous,
                "primary_r": str(primary),
                "secondary_r": str(secondary),
                "target_first_upper_delta_r": str(upper_delta),
            }
        )

    if len(rows) != EXPECTED_STANDARD[window_id]:
        raise ValueError(f"R112 {window_id} STANDARD row drift")

    ambiguous_rows = [row for row in rows if bool(row["same_m15_ambiguous"])]
    actual_primary = _metrics(rows, field="primary_r")
    actual_secondary = _metrics(rows, field="secondary_r")
    upper_delta = sum(
        (
            Decimal(str(row["target_first_upper_delta_r"]))
            for row in ambiguous_rows
        ),
        Decimal(),
    )

    return {
        "window_id": window_id,
        "sample": len(rows),
        "expected_sample": EXPECTED_STANDARD[window_id],
        "ambiguity": {
            "count": len(ambiguous_rows),
            "fraction": str(
                Decimal(len(ambiguous_rows)) / Decimal(len(rows))
            ),
            "all_canonical_ambiguous_exits_are_stop_first": all(
                str(row["exit_reason"]) == "stop"
                for row in ambiguous_rows
            ),
            "target_first_is_upper_bound_only": True,
            "target_first_upper_bound_delta_r": str(upper_delta),
        },
        "actual": {
            "primary": actual_primary,
            "secondary": actual_secondary,
        },
        "upper_bound": {
            "primary_total_if_all_ambiguities_target_first": str(
                Decimal(str(actual_primary["total_r"])) + upper_delta
            ),
            "secondary_total_if_all_ambiguities_target_first": str(
                Decimal(str(actual_secondary["total_r"])) + upper_delta
            ),
        },
        "by_period": _group(rows, lambda row: str(row["period"])),
        "by_market": _group(rows, lambda row: str(row["symbol"])),
        "by_side": _group(rows, lambda row: str(row["side"])),
        "by_anchor": _group(rows, lambda row: str(row["anchor"])),
        "by_poi": _group(rows, lambda row: str(row["poi"])),
        "ambiguous_rows": ambiguous_rows,
        "provenance": provenance,
    }


def build_report(
    *,
    nas100_root: Path,
    sp500_root: Path,
    us30_root: Path,
) -> dict[str, Any]:
    if r111.IDENTITY != (
        "VT08_INDEX_R111_CONTINUATION_SEMANTIC_PARITY_ATTRIBUTION_001"
    ):
        raise ValueError("R112 R111 identity drift")

    roots = {
        "NAS100": nas100_root,
        "SP500": sp500_root,
        "US30": us30_root,
    }
    five = _window(roots=roots, window_id="5Y")
    two = _window(roots=roots, window_id="2Y")
    failed = _window(roots=roots, window_id="R66")

    r66_b2 = failed["by_period"].get("B2")
    if r66_b2 is None:
        raise ValueError("R112 R66 B2 missing")
    m1_warranted = int(r66_b2["ambiguous_count"]) > 0

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "source_r111": {
            "run_id": SOURCE_R111_RUN_ID,
            "artifact_id": SOURCE_R111_ARTIFACT_ID,
            "artifact_digest": SOURCE_R111_ARTIFACT_DIGEST,
            "decision": "R111_CONTINUATION_SEMANTIC_PARITY_ATTRIBUTION_COMPLETE_NO_RULE_CHANGE",
        },
        "precedence_contract": {
            "canonical_same_m15_order": "STOP_FIRST",
            "gap_handling_precedes_intrabar_touch": True,
            "target_r": str(TARGET_R),
            "target_first_used_as_candidate": False,
            "target_first_role": "UNCERTAINTY_UPPER_BOUND_ONLY",
            "m1_resolution_trigger": "ANY_GENUINE_R66_B2_SAME_M15_AMBIGUITY",
        },
        "five_year": five,
        "recent_two_year": two,
        "r66_failed_holdout": failed,
        "next_step": (
            "NATIVE_M1_ORDERING_RESOLUTION_WARRANTED"
            if m1_warranted
            else "M1_PRECEDENCE_ROUTE_CLOSED_NO_R66_B2_AMBIGUITY"
        ),
        "decision": "R112_SAME_M15_AMBIGUITY_CENSUS_COMPLETE_NO_RULE_CHANGE",
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
            "canonical_stop_first_changed": False,
            "m1_used": False,
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
    print(
        json.dumps(
            {
                "identity": IDENTITY,
                "five_year": {
                    "sample": report["five_year"]["sample"],
                    "ambiguity": report["five_year"]["ambiguity"],
                    "by_period": report["five_year"]["by_period"],
                },
                "recent_two_year": {
                    "sample": report["recent_two_year"]["sample"],
                    "ambiguity": report["recent_two_year"]["ambiguity"],
                    "by_period": report["recent_two_year"]["by_period"],
                },
                "r66": {
                    "sample": report["r66_failed_holdout"]["sample"],
                    "ambiguity": report["r66_failed_holdout"]["ambiguity"],
                    "by_period": report["r66_failed_holdout"]["by_period"],
                },
                "next_step": report["next_step"],
                "decision": report["decision"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
