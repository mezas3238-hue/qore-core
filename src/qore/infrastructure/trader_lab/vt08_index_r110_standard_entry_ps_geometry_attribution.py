"""VT08 Index R110 — STANDARD entry / Protected-Swing geometry attribution.

R108 showed that source-valid retest execution materially improves aggregate
economics but does not repair 5Y Y1 or R66 B2. R109 then falsified a simple
"late retest" explanation. R110 moves upstream and attributes STANDARD weakness
to geometry already observable no later than the continuation close.

No rule is changed. The exact R102 fixed-weight canonical surface is retained.
Only STANDARD_WITHOUT_EXTRA_PS is studied, with these preregistered dimensions:

- Protected-Swing risk span / pre-entry H4 observed range;
- CISD-level -> continuation-close distance / structural risk;
- continuation breakout extension / structural risk;
- continuation candle body/range and directional close location;
- CISD-confirmation -> continuation-close age in M15 bars;
- POI-touch -> continuation-close age in M15 bars;
- continuation phase inside the source H4 and known remaining H4 slots.

All price geometry uses only M15 bars whose close is <= signal_at. No final-H4
range, future candle, outcome, year, or calendar state is used to construct a
bucket. Economic results are attached only after every row has been classified.
R108 retest delta is reported as a secondary attribution on the same setup when
available, never as a second signal.

This is consumed-evidence forensics only. It cannot create a candidate or grant
LIVE / real-capital / production authority.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
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
    vt08_index_v7_ttrades_source_corrected as v7,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import (
    Vt08IndexC2R1Bar,
)

SCHEMA = "qore.trader_lab.vt08_index_r110_standard_entry_ps_geometry_attribution.v1"
IDENTITY = "VT08_INDEX_R110_STANDARD_ENTRY_PS_GEOMETRY_ATTRIBUTION_001"

SOURCE_R109_RUN_ID = 35588958471
SOURCE_R109_ARTIFACT_ID = 10633686630
SOURCE_R109_ARTIFACT_DIGEST = (
    "sha256:8c964890737439fe5c9473bc9d0eb2de2645f5d359f8d7bb99f5b14fefad51e0"
)

EXPECTED_STANDARD = {"5Y": 1756, "2Y": 746, "R66": 546}


def _ratio_bucket(value: Decimal) -> str:
    if value < Decimal("0.25"):
        return "LT_0_25"
    if value < Decimal("0.50"):
        return "R_0_25_TO_0_50"
    if value < Decimal("1"):
        return "R_0_50_TO_1"
    return "GE_1"


def _extension_bucket(value: Decimal) -> str:
    if value <= Decimal("0.10"):
        return "LE_0_10R"
    if value <= Decimal("0.25"):
        return "R_0_10_TO_0_25"
    if value <= Decimal("0.50"):
        return "R_0_25_TO_0_50"
    return "GT_0_50R"


def _body_bucket(value: Decimal) -> str:
    if value < Decimal("0.25"):
        return "BODY_LT_25PCT"
    if value < Decimal("0.50"):
        return "BODY_25_TO_50PCT"
    if value < Decimal("0.75"):
        return "BODY_50_TO_75PCT"
    return "BODY_GE_75PCT"


def _close_location_bucket(value: Decimal) -> str:
    if value < Decimal("0.25"):
        return "CLOSE_Q1"
    if value < Decimal("0.50"):
        return "CLOSE_Q2"
    if value < Decimal("0.75"):
        return "CLOSE_Q3"
    return "CLOSE_Q4"


def _age_bucket(bars: int) -> str:
    if bars <= 1:
        return "M15_0_1"
    if bars <= 3:
        return "M15_2_3"
    return "M15_4_PLUS"


def _phase_bucket(index: int) -> str:
    # H4 contains 16 M15 bars. These are clock-phase bins, not learned cutoffs.
    if index <= 3:
        return "H4_Q1"
    if index <= 7:
        return "H4_Q2"
    if index <= 11:
        return "H4_Q3"
    return "H4_Q4"


def _remaining_bucket(remaining: int) -> str:
    if remaining <= 1:
        return "H4_REMAIN_0_1"
    if remaining <= 4:
        return "H4_REMAIN_2_4"
    return "H4_REMAIN_5_PLUS"


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
        "mean_r": str(total / len(values)) if values else "0",
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
        retest = [
            row for row in items
            if row["retest_primary_r"] is not None
        ]
        result[label] = {
            "sample": len(items),
            "canonical_primary": _weighted_metrics(
                items,
                field="canonical_primary_r",
            ),
            "canonical_secondary": _weighted_metrics(
                items,
                field="canonical_secondary_r",
            ),
            "retest_available_count": len(retest),
            "retest_primary": (
                _weighted_metrics(retest, field="retest_primary_r")
                if retest
                else None
            ),
            "retest_secondary": (
                _weighted_metrics(retest, field="retest_secondary_r")
                if retest
                else None
            ),
            "retest_primary_delta_r": (
                str(
                    sum(
                        (
                            Decimal(str(row["retest_primary_r"]))
                            - Decimal(str(row["canonical_primary_r"]))
                            for row in retest
                        ),
                        Decimal(),
                    )
                )
                if retest
                else "0"
            ),
        }
    return result


def _bar_index_at_or_before(
    bars: Sequence[Vt08IndexC2R1Bar],
    timestamp: datetime,
) -> int | None:
    target = timestamp.astimezone(UTC)
    candidates = [
        index
        for index, bar in enumerate(bars)
        if bar.closed_at.astimezone(UTC) <= target
    ]
    return candidates[-1] if candidates else None


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
        raise ValueError(f"R110 {window_id} canonical drift")

    standard_ids = r107._standard_ids(
        control,
        bars_by_symbol=bars_by_symbol,
    )
    if len(standard_ids) != EXPECTED_STANDARD[window_id]:
        raise ValueError(f"R110 {window_id} STANDARD drift")

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
            raise ValueError("R110 canonical H4 missing")

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
            raise ValueError("R110 continuation bar missing")

        continuation = inside[continuation_index]
        observed = inside[: continuation_index + 1]
        if any(
            bar.closed_at.astimezone(UTC)
            > signal.signal_at.astimezone(UTC)
            for bar in observed
        ):
            raise ValueError("R110 future bar leaked into entry geometry")

        observed_high = max(bar.high for bar in observed)
        observed_low = min(bar.low for bar in observed)
        observed_range = observed_high - observed_low
        risk = abs(signal.entry - signal.stop)
        if observed_range <= 0 or risk <= 0:
            raise ValueError("R110 non-positive geometry denominator")

        cisd_distance = abs(signal.entry - signal.cisd_level) / risk
        breakout_level = r89._continuation_breakout_level(
            inside,
            continuation_index=continuation_index,
            side=signal.side,
        )
        extension = abs(signal.entry - breakout_level) / risk

        bar_range = continuation.high - continuation.low
        if bar_range <= 0:
            body_fraction = Decimal()
            close_location = Decimal("0.5")
        else:
            body_fraction = abs(continuation.close - continuation.open) / bar_range
            close_location = (
                (continuation.close - continuation.low) / bar_range
                if signal.side is DemoTradingSetupSide.LONG
                else (continuation.high - continuation.close) / bar_range
            )

        cisd_index = _bar_index_at_or_before(
            inside,
            signal.cisd_confirmed_at,
        )
        cisd_age = (
            continuation_index - cisd_index
            if cisd_index is not None
            else 0
        )
        touch_index = next(
            (
                index
                for index, bar in enumerate(inside)
                if bar.opened_at.astimezone(UTC)
                >= item.opportunity.poi_touch_at.astimezone(UTC)
            ),
            None,
        )
        if touch_index is None or touch_index > continuation_index:
            raise ValueError("R110 POI touch not causally located")
        touch_age = continuation_index - touch_index
        remaining = len(inside) - continuation_index - 1

        canonical_primary = (
            item.outcome.r_multiple - r108.PRIMARY_STRESS
        ) * item.weight
        canonical_secondary = (
            item.outcome.r_multiple - r108.SECONDARY_STRESS
        ) * item.weight

        retest_index = r89._retest_fill_index(
            inside,
            continuation_index=continuation_index,
            side=signal.side,
            protected_swing=signal.protected_swing_extreme,
            model_kind=signal.model_kind,
            h4_open=inside[0].open,
        )
        retest_primary: Decimal | None = None
        retest_secondary: Decimal | None = None
        if retest_index is not None:
            retest_level = r89._continuation_breakout_level(
                inside,
                continuation_index=continuation_index,
                side=signal.side,
            )
            fill_bar = inside[retest_index]
            retest_signal = r108._build_retest_signal(
                signal,
                retest_level=retest_level,
                retest_window_opened_at=fill_bar.opened_at,
            )
            retest_outcome = r108._manage_retest(
                retest_signal,
                fill_bar=fill_bar,
                bars=bars_by_symbol[item.symbol],
                opened=opened_by_symbol[item.symbol],
            )
            retest_primary = (
                retest_outcome.r_multiple - r108.PRIMARY_STRESS
            ) * item.weight
            retest_secondary = (
                retest_outcome.r_multiple - r108.SECONDARY_STRESS
            ) * item.weight

        period = r109._period_label(
            exit_date=item.exited_at.astimezone(v7._NY).date(),
            window_id=window_id,
            start_date=start_date,
            end_date=end_date,
        )
        risk_to_observed_range = risk / observed_range

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
                "risk_to_preentry_h4_range": str(risk_to_observed_range),
                "risk_range_bucket": _ratio_bucket(risk_to_observed_range),
                "cisd_to_entry_r": str(cisd_distance),
                "cisd_distance_bucket": _ratio_bucket(cisd_distance),
                "breakout_extension_r": str(extension),
                "breakout_extension_bucket": _extension_bucket(extension),
                "continuation_body_fraction": str(body_fraction),
                "continuation_body_bucket": _body_bucket(body_fraction),
                "directional_close_location": str(close_location),
                "close_location_bucket": _close_location_bucket(close_location),
                "cisd_to_entry_bars": cisd_age,
                "cisd_age_bucket": _age_bucket(cisd_age),
                "poi_touch_to_entry_bars": touch_age,
                "touch_age_bucket": _age_bucket(touch_age),
                "h4_continuation_index": continuation_index,
                "h4_phase_bucket": _phase_bucket(continuation_index),
                "remaining_h4_bars": remaining,
                "remaining_h4_bucket": _remaining_bucket(remaining),
                "canonical_primary_r": str(canonical_primary),
                "canonical_secondary_r": str(canonical_secondary),
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
        raise ValueError(f"R110 {window_id} STANDARD row drift")

    dimensions: dict[str, Callable[[dict[str, Any]], str]] = {
        "risk_to_preentry_h4_range": (
            lambda row: str(row["risk_range_bucket"])
        ),
        "cisd_to_entry_distance": (
            lambda row: str(row["cisd_distance_bucket"])
        ),
        "breakout_extension": (
            lambda row: str(row["breakout_extension_bucket"])
        ),
        "continuation_body": (
            lambda row: str(row["continuation_body_bucket"])
        ),
        "directional_close_location": (
            lambda row: str(row["close_location_bucket"])
        ),
        "cisd_to_entry_age": (
            lambda row: str(row["cisd_age_bucket"])
        ),
        "poi_touch_to_entry_age": (
            lambda row: str(row["touch_age_bucket"])
        ),
        "h4_phase": lambda row: str(row["h4_phase_bucket"]),
        "remaining_h4": lambda row: str(row["remaining_h4_bucket"]),
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
        "retest_available_count": sum(
            row["retest_primary_r"] is not None for row in rows
        ),
        "overall": {
            "canonical_primary": _weighted_metrics(
                rows,
                field="canonical_primary_r",
            ),
            "canonical_secondary": _weighted_metrics(
                rows,
                field="canonical_secondary_r",
            ),
        },
        "dimensions": {
            name: _group(rows, selector)
            for name, selector in dimensions.items()
        },
        "provenance": provenance,
    }


def build_report(
    *,
    nas100_root: Path,
    sp500_root: Path,
    us30_root: Path,
) -> dict[str, Any]:
    if r109.IDENTITY != (
        "VT08_INDEX_R109_STANDARD_RETEST_TIMING_DECAY_ATTRIBUTION_001"
    ):
        raise ValueError("R110 R109 identity drift")
    if r109.SOURCE_R108_RUN_ID != 35588274260:
        raise ValueError("R110 R109 predecessor drift")

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
        "source_r109": {
            "run_id": SOURCE_R109_RUN_ID,
            "artifact_id": SOURCE_R109_ARTIFACT_ID,
            "artifact_digest": SOURCE_R109_ARTIFACT_DIGEST,
            "decision": "R109_RETEST_TIMING_DECAY_ATTRIBUTION_COMPLETE_NO_RULE_CHANGE",
        },
        "preregistered_contract": {
            "rule_change": False,
            "same_r102_fixed_weights": True,
            "standard_only": True,
            "classification_cutoff": "CONTINUATION_CLOSE",
            "future_h4_prices_used": False,
            "outcome_used_for_bucket": False,
            "calendar_or_year_used_for_bucket": False,
            "target_changed": False,
            "stop_changed": False,
            "risk_allocator_changed": False,
            "signals_suppressed": False,
            "trade_count_changed": False,
            "retest_is_secondary_same_setup_attribution": True,
            "runtime_filter_created": False,
        },
        "five_year": five,
        "recent_two_year": two,
        "r66_failed_holdout": failed,
        "decision": "R110_STANDARD_ENTRY_PS_GEOMETRY_ATTRIBUTION_COMPLETE_NO_RULE_CHANGE",
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
            "retest_available_count": section["retest_available_count"],
            "overall": section["overall"],
            "risk_to_preentry_h4_range": section["dimensions"][
                "risk_to_preentry_h4_range"
            ],
            "cisd_to_entry_distance": section["dimensions"][
                "cisd_to_entry_distance"
            ],
            "breakout_extension": section["dimensions"][
                "breakout_extension"
            ],
            "continuation_body": section["dimensions"][
                "continuation_body"
            ],
            "cisd_to_entry_age": section["dimensions"][
                "cisd_to_entry_age"
            ],
            "poi_touch_to_entry_age": section["dimensions"][
                "poi_touch_to_entry_age"
            ],
            "h4_phase": section["dimensions"]["h4_phase"],
            "period": section["dimensions"]["period"],
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
