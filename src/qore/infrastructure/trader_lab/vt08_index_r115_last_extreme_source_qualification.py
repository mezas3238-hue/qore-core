"""VT08 Index R115 — LAST-extreme x source-qualification attribution.

R114 found a transported adverse structural state: STANDARD setups whose
Protected-Swing extreme is formed on the LAST opposing candle of a multi-bar
CISD series are negative in 5Y, Recent2Y and R66. That observation is not yet a
rule. R115 tests whether LAST_BAR is causal or merely a proxy for missing
source-qualified Protected-Swing evidence.

Every canonical STANDARD setup is classified before economics by:
- exact R114 extreme position;
- exact R82 source-qualification family:
  LIQUIDITY_SWEEP / ORIGINAL_FVG_REACTION / BOTH /
  UNQUALIFIED_GENERIC_CISD;
- combined extreme-position x qualification family;
- multi-bar LAST versus all other anatomy;
- LAST_BAR source qualification versus unqualified.

No trade is removed, no risk is changed and no runtime rule is created. Calendar
blocks are used only after classification for attribution.
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
    vt08_index_v7_ttrades_source_corrected as v7,
)
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import (
    Vt08IndexC2R1Bar,
)

SCHEMA = "qore.trader_lab.vt08_index_r115_last_extreme_source_qualification.v1"
IDENTITY = "VT08_INDEX_R115_LAST_EXTREME_SOURCE_QUALIFICATION_ATTRIBUTION_001"

SOURCE_R114_RUN_ID = 35665635210
SOURCE_R114_ARTIFACT_ID = 10669476302
SOURCE_R114_ARTIFACT_DIGEST = (
    "sha256:134027f3bc4c246c9316cc38df1de5bab6e01ac71a04eacb8516ad88280eaec7"
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
        raise ValueError(f"R115 {window_id} canonical drift")

    standard_ids = r107._standard_ids(
        control,
        bars_by_symbol=bars_by_symbol,
    )
    if len(standard_ids) != EXPECTED_STANDARD[window_id]:
        raise ValueError(f"R115 {window_id} STANDARD drift")

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
            raise ValueError("R115 canonical H4 missing")

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
            raise ValueError("R115 POI touch missing")

        anatomy = r114._trace_anatomy(
            inside,
            side=signal.side,
            start_index=touch_index,
        )
        if anatomy is None:
            raise ValueError("R115 CISD anatomy missing")

        extreme_position = r114._extreme_position(
            sequence_start=int(anatomy["sequence_start"]),
            sequence_end=int(anatomy["sequence_end"]),
            extreme_index=int(anatomy["extreme_index"]),
        )
        family_row = r82._classify_opportunity(
            item.opportunity,
            h4_bars=h4_cache[item.symbol],
        )
        family = str(family_row["family"])
        if family not in r82.FAMILIES:
            raise ValueError("R115 unknown R82 family")

        last_state = (
            "LAST_BAR"
            if extreme_position == "LAST_BAR"
            else "NOT_LAST_BAR"
        )
        if extreme_position == "LAST_BAR":
            last_qualification = (
                "LAST_BAR_SOURCE_QUALIFIED"
                if family != r82.FAMILY_UNQUALIFIED
                else "LAST_BAR_UNQUALIFIED"
            )
        else:
            last_qualification = "NOT_LAST_BAR"

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
                "extreme_position": extreme_position,
                "source_qualification_family": family,
                "last_state": last_state,
                "last_qualification": last_qualification,
                "combined_state": f"{extreme_position}|{family}",
                "primary_r": str(primary),
                "secondary_r": str(secondary),
            }
        )

    if len(rows) != EXPECTED_STANDARD[window_id]:
        raise ValueError(f"R115 {window_id} row drift")

    return {
        "window_id": window_id,
        "sample": len(rows),
        "expected_sample": EXPECTED_STANDARD[window_id],
        "overall": {
            "primary": _metrics(rows, field="primary_r"),
            "secondary": _metrics(rows, field="secondary_r"),
        },
        "by_extreme_position": _group(
            rows,
            lambda row: str(row["extreme_position"]),
        ),
        "by_source_qualification_family": _group(
            rows,
            lambda row: str(row["source_qualification_family"]),
        ),
        "by_last_state": _group(
            rows,
            lambda row: str(row["last_state"]),
        ),
        "by_last_qualification": _group(
            rows,
            lambda row: str(row["last_qualification"]),
        ),
        "by_combined_state": _group(
            rows,
            lambda row: str(row["combined_state"]),
        ),
        "period_x_last_qualification": _period_matrix(
            rows,
            field="last_qualification",
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
    if r114.IDENTITY != (
        "VT08_INDEX_R114_STANDARD_CISD_PS_ANATOMY_ATTRIBUTION_001"
    ):
        raise ValueError("R115 R114 identity drift")

    roots = {
        "NAS100": nas100_root,
        "SP500": sp500_root,
        "US30": us30_root,
    }
    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "source_r114": {
            "run_id": SOURCE_R114_RUN_ID,
            "artifact_id": SOURCE_R114_ARTIFACT_ID,
            "artifact_digest": SOURCE_R114_ARTIFACT_DIGEST,
            "decision": (
                "R114_STANDARD_CISD_PS_ANATOMY_ATTRIBUTION_COMPLETE_NO_RULE_CHANGE"
            ),
        },
        "preregistered_contract": {
            "rule_change": False,
            "standard_only": True,
            "same_r102_fixed_weights": True,
            "classification_cutoff": "CISD_CONFIRMATION",
            "r82_source_qualification_reused_exactly": True,
            "r114_anatomy_reused_exactly": True,
            "outcome_used_for_classification": False,
            "calendar_or_year_used_for_classification": False,
            "runtime_filter_created": False,
            "signals_suppressed": False,
            "trade_count_changed": False,
        },
        "five_year": _window(roots=roots, window_id="5Y"),
        "recent_two_year": _window(roots=roots, window_id="2Y"),
        "r66_failed_holdout": _window(roots=roots, window_id="R66"),
        "decision": "R115_LAST_EXTREME_SOURCE_QUALIFICATION_COMPLETE_NO_RULE_CHANGE",
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
            "last_state": section["by_last_state"],
            "last_qualification": section["by_last_qualification"],
            "source_family": section["by_source_qualification_family"],
            "period_x_last_qualification": section[
                "period_x_last_qualification"
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
