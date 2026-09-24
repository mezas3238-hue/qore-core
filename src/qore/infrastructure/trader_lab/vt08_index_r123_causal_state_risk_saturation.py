"""VT08 Index R123 — R120 causal-state risk saturation attribution.

R122 showed that restoring existing R58 promotions inside the strongest
transport-positive R120 STANDARD cohort is not transport-safe. Before any
further risk experiment, R123 measures whether the transport-adverse R120
causal states still have effective risk above the existing 0.005R floor.

This stage changes nothing. It joins the exact R102 control allocation to the
R120 daily-bias mechanism and R118 failed-attempt relation known causally by
entry. It reports economic contribution and risk saturation for:
- bias mechanism;
- mechanism x prior-extreme relation;
- mechanism x LAST_BAR state.

No signal suppression, risk change, entry/stop/target change, calendar rule,
candidate identity, certification or LIVE authorization is created.
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
    vt08_index_r120_daily_bias_mechanism as r120,
)
from qore.infrastructure.trader_lab import (
    vt08_index_v7_ttrades_source_corrected as v7,
)
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import (
    Vt08IndexC2R1Bar,
)

SCHEMA = "qore.trader_lab.vt08_index_r123_causal_state_risk_saturation.v1"
IDENTITY = "VT08_INDEX_R123_R120_CAUSAL_STATE_RISK_SATURATION_001"

SOURCE_R122_RUN_ID = 36055703336
SOURCE_R122_ARTIFACT_ID = 10833130590
SOURCE_R122_ARTIFACT_DIGEST = (
    "sha256:6c8a35c137e791504dc921e8ed76920a"
    "0989a2c627448f820c7c845a052e4c08"
)

EXPECTED_STANDARD = r120.EXPECTED_STANDARD
FLOOR = r102.MIN_EFFECTIVE_WEIGHT


def _risk_bundle(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    weights = tuple(Decimal(str(row["weight"])) for row in rows)
    floor_count = sum(weight == FLOOR for weight in weights)
    above_floor = sum(weight > FLOOR for weight in weights)
    return {
        "sample": len(rows),
        "floor_count": floor_count,
        "above_floor_count": above_floor,
        "floor_fraction": (
            str(Decimal(floor_count) / Decimal(len(rows)))
            if rows
            else "0"
        ),
        "total_effective_risk_r": str(sum(weights, Decimal())),
        "mean_effective_weight_r": (
            str(sum(weights, Decimal()) / Decimal(len(weights)))
            if weights
            else "0"
        ),
        "minimum_effective_weight_r": str(min(weights)) if weights else None,
        "maximum_effective_weight_r": str(max(weights)) if weights else None,
        "primary": r118._metrics(rows, field="primary_r"),
        "secondary": r118._metrics(rows, field="secondary_r"),
    }


def _group(
    rows: Sequence[dict[str, Any]],
    selector: Callable[[dict[str, Any]], str],
) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[selector(row)].append(row)
    return {
        label: _risk_bundle(items)
        for label, items in sorted(groups.items())
    }


def _period_group(
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
        symbol: {
            bar.opened_at.astimezone(UTC): bar
            for bar in bars
        }
        for symbol, bars in bars_by_symbol.items()
    }

    base, _base_diag = r58._exact_r47(
        tuple(canonical),
        bars_by_symbol=bars_by_symbol,
    )
    control, control_diag = r102._apply_confidence_policy(
        tuple(base),
        bars_by_symbol=bars_by_symbol,
        policy_id=r102.POLICY_EXPLICIT_FULL,
    )
    control = tuple(control)
    if len(control) != expected:
        raise ValueError(f"R123 {window_id} canonical density drift")

    standard_ids = r107._standard_ids(
        control,
        bars_by_symbol=bars_by_symbol,
    )
    if len(standard_ids) != EXPECTED_STANDARD[window_id]:
        raise ValueError(f"R123 {window_id} STANDARD drift")

    h4_cache = {
        symbol: r82._h4_bar_cache(bars)
        for symbol, bars in bars_by_symbol.items()
    }

    rows: list[dict[str, Any]] = []
    for item in control:
        identity = item.opportunity.identity()
        if identity not in standard_ids:
            continue

        signal = item.opportunity.signal
        previous_day, current_day = r119._source_days(
            indexed_by_symbol[item.symbol],
            before_local=signal.h4_opened_at.astimezone(v7._NY),
        )
        mechanism = r120._bias_mechanism(
            previous_day=previous_day,
            current_day=current_day,
            side=signal.side,
        )

        inside = h4_cache[item.symbol].get(
            signal.h4_opened_at.astimezone(UTC)
        )
        if inside is None:
            raise ValueError("R123 canonical H4 missing")
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
            raise ValueError("R123 POI touch missing")
        journey = r118._cisd_journey(
            inside,
            side=signal.side,
            start_index=touch_index,
        )
        if journey is None:
            raise ValueError("R123 canonical CISD journey missing")

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
        rows.append(
            {
                "trade_id": item.trade_id,
                "symbol": item.symbol,
                "side": signal.side.value,
                "anchor": str(signal.h4_opened_at.astimezone(v7._NY).hour),
                "period": period,
                "bias_mechanism": mechanism,
                "prior_extreme_relation": relation,
                "last_state": last_state,
                "mechanism_x_relation": f"{mechanism}|{relation}",
                "mechanism_x_last_state": f"{mechanism}|{last_state}",
                "weight": str(item.weight),
                "primary_r": str(
                    (item.outcome.r_multiple - r102.PRIMARY_STRESS)
                    * item.weight
                ),
                "secondary_r": str(
                    (item.outcome.r_multiple - r102.SECONDARY_STRESS)
                    * item.weight
                ),
            }
        )

    if len(rows) != EXPECTED_STANDARD[window_id]:
        raise ValueError(f"R123 {window_id} row drift")

    return {
        "window_id": window_id,
        "canonical_sample": expected,
        "standard_sample": len(rows),
        "control_policy": r102.POLICY_EXPLICIT_FULL,
        "control_diagnostics": control_diag,
        "overall": _risk_bundle(rows),
        "by_bias_mechanism": _group(
            rows,
            lambda row: str(row["bias_mechanism"]),
        ),
        "by_mechanism_x_relation": _group(
            rows,
            lambda row: str(row["mechanism_x_relation"]),
        ),
        "by_mechanism_x_last_state": _group(
            rows,
            lambda row: str(row["mechanism_x_last_state"]),
        ),
        "period_x_mechanism_x_relation": _period_group(
            rows,
            field="mechanism_x_relation",
        ),
        "period_x_mechanism_x_last_state": _period_group(
            rows,
            field="mechanism_x_last_state",
        ),
        "provenance": provenance,
    }


def _transport_adverse_actionability(
    five: dict[str, Any],
    two: dict[str, Any],
    failed: dict[str, Any],
) -> list[dict[str, Any]]:
    sections = (five, two, failed)
    labels = set.intersection(
        *(
            set(section["by_mechanism_x_relation"])
            for section in sections
        )
    )
    result: list[dict[str, Any]] = []
    for label in sorted(labels):
        values = [
            section["by_mechanism_x_relation"][label]
            for section in sections
        ]
        if min(int(value["sample"]) for value in values) < 20:
            continue
        totals = [
            Decimal(str(value["secondary"]["total_r"]))
            for value in values
        ]
        if not all(total < 0 for total in totals):
            continue
        result.append(
            {
                "state": label,
                "samples": {
                    "five_year": int(values[0]["sample"]),
                    "recent_two_year": int(values[1]["sample"]),
                    "r66": int(values[2]["sample"]),
                },
                "above_floor_count": {
                    "five_year": int(values[0]["above_floor_count"]),
                    "recent_two_year": int(values[1]["above_floor_count"]),
                    "r66": int(values[2]["above_floor_count"]),
                },
                "floor_fraction": {
                    "five_year": values[0]["floor_fraction"],
                    "recent_two_year": values[1]["floor_fraction"],
                    "r66": values[2]["floor_fraction"],
                },
                "secondary_total_r": {
                    "five_year": str(totals[0]),
                    "recent_two_year": str(totals[1]),
                    "r66": str(totals[2]),
                },
                "demotion_actionable": any(
                    int(value["above_floor_count"]) > 0
                    for value in values
                ),
            }
        )
    return result


def build_report(
    *,
    nas100_root: Path,
    sp500_root: Path,
    us30_root: Path,
) -> dict[str, Any]:
    if r120.IDENTITY != (
        "VT08_INDEX_R120_DAILY_BIAS_MECHANISM_ATTRIBUTION_001"
    ):
        raise ValueError("R123 R120 identity drift")

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
        "source_r122": {
            "run_id": SOURCE_R122_RUN_ID,
            "artifact_id": SOURCE_R122_ARTIFACT_ID,
            "artifact_digest": SOURCE_R122_ARTIFACT_DIGEST,
            "decision": (
                "R122_R121_PROMOTION_MECHANISM_ATTRIBUTION_COMPLETE_"
                "NO_RULE_CHANGE"
            ),
        },
        "risk_contract": {
            "control_policy": r102.POLICY_EXPLICIT_FULL,
            "minimum_effective_weight_r": str(FLOOR),
            "risk_changed": False,
            "signals_suppressed": False,
        },
        "five_year": five,
        "recent_two_year": two,
        "r66_failed_holdout": failed,
        "transport_adverse_actionability": (
            _transport_adverse_actionability(five, two, failed)
        ),
        "decision": (
            "R123_R120_CAUSAL_STATE_RISK_SATURATION_COMPLETE_"
            "NO_RULE_CHANGE"
        ),
        "governance": {
            "research_only": True,
            "forensics_only": True,
            "consumed_evidence_only": True,
            "fresh_holdout_claim": False,
            "signals_suppressed": False,
            "risk_changed": False,
            "entries_changed": False,
            "stops_changed": False,
            "targets_changed": False,
            "candidate_created": False,
            "trader_certified": False,
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
                "transport_adverse_actionability": report[
                    "transport_adverse_actionability"
                ],
                "decision": report["decision"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
