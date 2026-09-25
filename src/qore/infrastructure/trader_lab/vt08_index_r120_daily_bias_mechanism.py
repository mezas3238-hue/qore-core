"""VT08 Index R120 — source-corrected daily-bias mechanism attribution.

R119 falsified previous-source-day body opposition as a universal transported
rule on the current R100+ STANDARD surface. It did, however, show that the R66
B2 degradation is concentrated upstream of the M15 entry anatomy.

R120 therefore classifies the exact V7 daily-bias mechanism that existed before
the executable H4 decision:
- CLOSE_BREAKOUT: current source-day close exits the previous source-day range
  in the eventual trade direction;
- SWEEP_REVERSAL: current source day sweeps the adverse previous-day extreme
  and reclaims it, producing the eventual trade direction.

The classifier calls the same resolve_daily_bias() contract and the same V7
source-day pair used by the canonical signal. No outcome, calendar label,
numeric threshold, signal suppression, or runtime rule is used to classify.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
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
    vt08_index_r118_pre_cisd_failed_attempt_journey as r118,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r119_previous_source_day_alignment as r119,
)
from qore.infrastructure.trader_lab import (
    vt08_index_v7_ttrades_source_corrected as v7,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import (
    Vt08IndexC2R1Bar,
    resolve_daily_bias,
)

SCHEMA = "qore.trader_lab.vt08_index_r120_daily_bias_mechanism.v1"
IDENTITY = "VT08_INDEX_R120_DAILY_BIAS_MECHANISM_ATTRIBUTION_001"

SOURCE_R119_RUN_ID = 35791895806
SOURCE_R119_ARTIFACT_ID = 10721819322
SOURCE_R119_ARTIFACT_DIGEST = (
    "sha256:99a03b8a00e150c16c868fbbede903973f4d14914c0c0dbe931e13249a94a17a"
)

EXPECTED_STANDARD = r119.EXPECTED_STANDARD

MECHANISM_BREAKOUT = "CLOSE_BREAKOUT"
MECHANISM_REVERSAL = "SWEEP_REVERSAL"


def _bias_mechanism(
    *,
    previous_day: Vt08IndexC2R1Bar,
    current_day: Vt08IndexC2R1Bar,
    side: DemoTradingSetupSide,
) -> str:
    resolved = resolve_daily_bias(
        previous_day=previous_day,
        current_day=current_day,
    )
    if resolved is not side:
        raise ValueError("R120 reconstructed daily bias differs from signal side")

    if side is DemoTradingSetupSide.LONG:
        if current_day.close > previous_day.high:
            return MECHANISM_BREAKOUT
        bullish_reversal = (
            current_day.low < previous_day.low
            and current_day.close > previous_day.low
        )
        if bullish_reversal:
            return MECHANISM_REVERSAL
    else:
        if current_day.close < previous_day.low:
            return MECHANISM_BREAKOUT
        bearish_reversal = (
            current_day.high > previous_day.high
            and current_day.close < previous_day.high
        )
        if bearish_reversal:
            return MECHANISM_REVERSAL

    raise ValueError("R120 resolved side has no matching V7 bias mechanism")


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
        symbol: {bar.opened_at.astimezone(UTC): bar for bar in bars}
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
        raise ValueError(f"R120 {window_id} canonical drift")

    standard_ids = r107._standard_ids(
        control,
        bars_by_symbol=bars_by_symbol,
    )
    if len(standard_ids) != EXPECTED_STANDARD[window_id]:
        raise ValueError(f"R120 {window_id} STANDARD drift")

    h4_cache = {
        symbol: r82._h4_bar_cache(bars)
        for symbol, bars in bars_by_symbol.items()
    }

    rows: list[dict[str, Any]] = []
    for item in control:
        if item.opportunity.identity() not in standard_ids:
            continue

        signal = item.opportunity.signal
        previous_day, current_day = r119._source_days(
            indexed_by_symbol[item.symbol],
            before_local=signal.h4_opened_at.astimezone(v7._NY),
        )
        mechanism = _bias_mechanism(
            previous_day=previous_day,
            current_day=current_day,
            side=signal.side,
        )
        previous_alignment = (
            "ALIGNED"
            if r119._aligned(previous_day, signal.side)
            else "OPPOSED"
        )
        current_alignment = (
            "ALIGNED"
            if r119._aligned(current_day, signal.side)
            else "OPPOSED"
        )

        inside = h4_cache[item.symbol].get(
            signal.h4_opened_at.astimezone(UTC)
        )
        if inside is None:
            raise ValueError("R120 canonical H4 missing")
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
            raise ValueError("R120 POI touch missing")
        journey = r118._cisd_journey(
            inside,
            side=signal.side,
            start_index=touch_index,
        )
        if journey is None:
            raise ValueError("R120 canonical CISD journey missing")
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
                "bias_mechanism": mechanism,
                "previous_alignment": previous_alignment,
                "current_alignment": current_alignment,
                "r118_prior_extreme_relation": relation,
                "last_state": last_state,
                "mechanism_x_previous_alignment": (
                    f"{mechanism}|{previous_alignment}"
                ),
                "mechanism_x_current_alignment": (
                    f"{mechanism}|{current_alignment}"
                ),
                "mechanism_x_relation": f"{mechanism}|{relation}",
                "mechanism_x_last_state": f"{mechanism}|{last_state}",
                "mechanism_x_market": f"{mechanism}|{item.symbol}",
                "mechanism_x_side": f"{mechanism}|{signal.side.value}",
                "mechanism_x_anchor": (
                    f"{mechanism}|"
                    f"{signal.h4_opened_at.astimezone(v7._NY).hour}"
                ),
                "primary_r": str(primary),
                "secondary_r": str(secondary),
            }
        )

    if len(rows) != EXPECTED_STANDARD[window_id]:
        raise ValueError(f"R120 {window_id} row drift")

    return {
        "window_id": window_id,
        "sample": len(rows),
        "expected_sample": EXPECTED_STANDARD[window_id],
        "bias_mechanism": r119._group(
            rows,
            lambda row: str(row["bias_mechanism"]),
        ),
        "mechanism_x_previous_alignment": r119._group(
            rows,
            lambda row: str(row["mechanism_x_previous_alignment"]),
        ),
        "mechanism_x_current_alignment": r119._group(
            rows,
            lambda row: str(row["mechanism_x_current_alignment"]),
        ),
        "mechanism_x_relation": r119._group(
            rows,
            lambda row: str(row["mechanism_x_relation"]),
        ),
        "mechanism_x_last_state": r119._group(
            rows,
            lambda row: str(row["mechanism_x_last_state"]),
        ),
        "mechanism_x_market": r119._group(
            rows,
            lambda row: str(row["mechanism_x_market"]),
        ),
        "mechanism_x_side": r119._group(
            rows,
            lambda row: str(row["mechanism_x_side"]),
        ),
        "mechanism_x_anchor": r119._group(
            rows,
            lambda row: str(row["mechanism_x_anchor"]),
        ),
        "period_x_bias_mechanism": r119._period_matrix(
            rows,
            field="bias_mechanism",
        ),
        "period_x_mechanism_relation": r119._period_matrix(
            rows,
            field="mechanism_x_relation",
        ),
        "provenance": provenance,
    }


def build_report(
    *,
    nas100_root: Path,
    sp500_root: Path,
    us30_root: Path,
) -> dict[str, Any]:
    if r119.IDENTITY != (
        "VT08_INDEX_R119_PREVIOUS_SOURCE_DAY_ALIGNMENT_ATTRIBUTION_001"
    ):
        raise ValueError("R120 R119 identity drift")

    roots = {
        "NAS100": nas100_root,
        "SP500": sp500_root,
        "US30": us30_root,
    }
    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "source_r119": {
            "run_id": SOURCE_R119_RUN_ID,
            "artifact_id": SOURCE_R119_ARTIFACT_ID,
            "artifact_digest": SOURCE_R119_ARTIFACT_DIGEST,
            "decision": (
                "R119_PREVIOUS_SOURCE_DAY_ALIGNMENT_COMPLETE_NO_RULE_CHANGE"
            ),
        },
        "source_contract": {
            "daily_bias_function": "resolve_daily_bias",
            "source_day_pair": (
                "EXACT_CURRENT_V7_SOURCE_CORRECTED_SOURCE_DAY_PAIR"
            ),
            "classification_cutoff": "H4_DECISION_OPEN",
            "mechanisms": [MECHANISM_BREAKOUT, MECHANISM_REVERSAL],
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
        "decision": "R120_DAILY_BIAS_MECHANISM_COMPLETE_NO_RULE_CHANGE",
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
            "bias_mechanism": section["bias_mechanism"],
            "mechanism_x_previous_alignment": section[
                "mechanism_x_previous_alignment"
            ],
            "mechanism_x_relation": section["mechanism_x_relation"],
            "period_x_bias_mechanism": section[
                "period_x_bias_mechanism"
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
