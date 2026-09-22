"""VT08 Index R119 — previous source-day alignment attribution.

R118 shows that the failed R66 B2 regime damages multiple CISD/Protected-Swing
journey states, so the remaining defect is likely upstream context rather than
one M15 anatomy detail. R119 revalidates, without alteration, the strongest
consumed V4 context lead on the current R100+ STANDARD surface:

    previous source-day body aligned/opposed to the current trade side.

The source-day reconstruction and alignment semantics are copied from V4
root-cause forensics. Classification is causal and available before the
canonical continuation entry. R119 also crosses this context state with the
R118 failed-attempt relation and LAST_BAR anatomy. No signal is removed and no
runtime rule or candidate is created.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from collections.abc import Callable, Sequence
from datetime import UTC, datetime, timedelta
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
    vt08_index_r118_pre_cisd_failed_attempt_journey as r118,
)
from qore.infrastructure.trader_lab import (
    vt08_index_v7_ttrades_source_corrected as v7,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import (
    Vt08IndexC2R1Bar,
    _source_day,
)

SCHEMA = "qore.trader_lab.vt08_index_r119_previous_source_day_alignment.v1"
IDENTITY = "VT08_INDEX_R119_PREVIOUS_SOURCE_DAY_ALIGNMENT_ATTRIBUTION_001"

SOURCE_R118_RUN_ID = 35667373524
SOURCE_R118_ARTIFACT_ID = 10669755410
SOURCE_R118_ARTIFACT_DIGEST = (
    "sha256:0a5fd516e7d3c795171b31f63a0eabf957ddb35ad27a934c6ba2746c7032421a"
)

EXPECTED_STANDARD = r114.EXPECTED_STANDARD


def _body_sign(bar: Vt08IndexC2R1Bar) -> int:
    return (bar.close > bar.open) - (bar.close < bar.open)


def _side_sign(side: DemoTradingSetupSide) -> int:
    return 1 if side is DemoTradingSetupSide.LONG else -1


def _aligned(bar: Vt08IndexC2R1Bar, side: DemoTradingSetupSide) -> bool:
    """Exact V4 alignment semantics; doji is therefore classified opposed."""

    return _body_sign(bar) == _side_sign(side)


def _source_days(
    indexed: dict[datetime, Vt08IndexC2R1Bar],
    *,
    before_local: datetime,
    count: int,
) -> tuple[Vt08IndexC2R1Bar, ...]:
    """Return the two complete source days actually consumed by V4 classification."""

    end_date = before_local.astimezone(v7._NY).date() - timedelta(days=1)
    retained: list[Vt08IndexC2R1Bar] = []
    for offset in range(30):
        candidate = _source_day(
            indexed,
            end_date=end_date - timedelta(days=offset),
        )
        if candidate is not None:
            retained.append(candidate)
            if len(retained) == count:
                return tuple(reversed(retained))
    raise ValueError("R119 insufficient complete source-day history")


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
            "primary": r118._metrics(items, field="primary_r"),
            "secondary": r118._metrics(items, field="secondary_r"),
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
    indexed_by_symbol = {
        symbol: {bar.opened_at: bar for bar in bars}
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
        raise ValueError(f"R119 {window_id} canonical drift")

    standard_ids = r107._standard_ids(
        control,
        bars_by_symbol=bars_by_symbol,
    )
    if len(standard_ids) != EXPECTED_STANDARD[window_id]:
        raise ValueError(f"R119 {window_id} STANDARD drift")

    h4_cache = {
        symbol: r82._h4_bar_cache(bars)
        for symbol, bars in bars_by_symbol.items()
    }

    rows: list[dict[str, Any]] = []
    for item in control:
        if item.opportunity.identity() not in standard_ids:
            continue

        signal = item.opportunity.signal
        days = _source_days(
            indexed_by_symbol[item.symbol],
            before_local=signal.signal_at.astimezone(v7._NY),
            count=3,
        )
        _previous_previous, previous_day, current_day = days[-3:]
        previous_alignment = (
            "ALIGNED"
            if _aligned(previous_day, signal.side)
            else "OPPOSED"
        )
        current_alignment = (
            "ALIGNED"
            if _aligned(current_day, signal.side)
            else "OPPOSED"
        )

        inside = h4_cache[item.symbol].get(
            signal.h4_opened_at.astimezone(UTC)
        )
        if inside is None:
            raise ValueError("R119 canonical H4 missing")
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
            raise ValueError("R119 POI touch missing")
        journey = r118._cisd_journey(
            inside,
            side=signal.side,
            start_index=touch_index,
        )
        if journey is None:
            raise ValueError("R119 canonical CISD journey missing")

        relation = r118._prior_extreme_relation(
            side=signal.side,
            final_extreme=Decimal(str(journey["extreme"])),
            failed_attempts=tuple(journey["failed_attempts"]),
        )
        extreme_position = r114._extreme_position(
            sequence_start=int(journey["sequence_start"]),
            sequence_end=int(journey["sequence_end"]),
            extreme_index=int(journey["extreme_index"]),
        )
        last_state = (
            "LAST_BAR"
            if extreme_position == "LAST_BAR"
            else "NOT_LAST_BAR"
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
                "previous_source_day_body_alignment": previous_alignment,
                "current_source_day_body_alignment": current_alignment,
                "r118_prior_extreme_relation": relation,
                "last_state": last_state,
                "alignment_x_relation": (
                    f"{previous_alignment}|{relation}"
                ),
                "alignment_x_last_state": (
                    f"{previous_alignment}|{last_state}"
                ),
                "primary_r": str(primary),
                "secondary_r": str(secondary),
            }
        )

    if len(rows) != EXPECTED_STANDARD[window_id]:
        raise ValueError(f"R119 {window_id} row drift")

    return {
        "window_id": window_id,
        "sample": len(rows),
        "expected_sample": EXPECTED_STANDARD[window_id],
        "previous_source_day_alignment": _group(
            rows,
            lambda row: str(row["previous_source_day_body_alignment"]),
        ),
        "current_source_day_alignment": _group(
            rows,
            lambda row: str(row["current_source_day_body_alignment"]),
        ),
        "alignment_x_relation": _group(
            rows,
            lambda row: str(row["alignment_x_relation"]),
        ),
        "alignment_x_last_state": _group(
            rows,
            lambda row: str(row["alignment_x_last_state"]),
        ),
        "period_x_previous_alignment": _period_matrix(
            rows,
            field="previous_source_day_body_alignment",
        ),
        "period_x_alignment_relation": _period_matrix(
            rows,
            field="alignment_x_relation",
        ),
        "provenance": provenance,
    }


def build_report(
    *,
    nas100_root: Path,
    sp500_root: Path,
    us30_root: Path,
) -> dict[str, Any]:
    if r118.IDENTITY != (
        "VT08_INDEX_R118_PRE_CISD_FAILED_ATTEMPT_JOURNEY_ATTRIBUTION_001"
    ):
        raise ValueError("R119 R118 identity drift")

    roots = {
        "NAS100": nas100_root,
        "SP500": sp500_root,
        "US30": us30_root,
    }
    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "source_r118": {
            "run_id": SOURCE_R118_RUN_ID,
            "artifact_id": SOURCE_R118_ARTIFACT_ID,
            "artifact_digest": SOURCE_R118_ARTIFACT_DIGEST,
            "decision": (
                "R118_PRE_CISD_FAILED_ATTEMPT_JOURNEY_COMPLETE_NO_RULE_CHANGE"
            ),
        },
        "v4_semantic_freeze": {
            "source_day_reconstruction": "EXACT_V4_SOURCE_DAYS",
            "previous_alignment": (
                "BODY_SIGN_EQUALS_SIDE_SIGN_ELSE_OPPOSED"
            ),
            "source_days_requested": 2,
            "v4_retained_source_days_original": 3,
            "classification_consumed_source_days": 2,
            "classification_cutoff": "BEFORE_CANONICAL_ENTRY",
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
        "decision": "R119_PREVIOUS_SOURCE_DAY_ALIGNMENT_COMPLETE_NO_RULE_CHANGE",
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
            "previous_alignment": section[
                "previous_source_day_alignment"
            ],
            "alignment_x_relation": section["alignment_x_relation"],
            "period_x_previous_alignment": section[
                "period_x_previous_alignment"
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
