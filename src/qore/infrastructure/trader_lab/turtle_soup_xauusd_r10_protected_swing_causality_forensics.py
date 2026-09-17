"""Protected Swing causality forensics for Turtle Soup XAUUSD R10.

Research-only diagnostic layer. The objective is to understand whether the
pre-entry anatomy of the CISD Protected Swing differs between journeys that
later demonstrate capacity to touch active Draw-On-Liquidity and journeys that
are invalidated before touching any active DOL.

Post-entry path is used only as a forensic label. Every candidate explanatory
feature in this module is known no later than the entry decision.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Mapping, Sequence
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

from qore.infrastructure.trader_lab import turtle_soup_xauusd_r3_causal_regime_forensics as causal
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r3_cibo_journey as r3
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r3_cibo_journey_binding_repair as repair
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r5_regime_journey_validity_forensics as r5
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r7_structural_abstention_lab as r7
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r8_structural_break_counterfactual as r8
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r9_causal_break_discriminator as r9
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r9_journey_divergence_forensics as divergence
from qore.infrastructure.trader_lab.ict_turtle_soup_r4_source_exact import (
    Side,
    SourceCandle,
    causal_cisd,
)

IDENTITY = "TURTLE_SOUP_XAUUSD_R10_PROTECTED_SWING_CAUSALITY_FORENSICS_V1"
EVIDENCE_STATUS = (
    "CONSUMED_CIBO_10Y_PROTECTED_SWING_CAUSALITY_DIAGNOSTIC_NOT_FRESH_HOLDOUT"
)

FEATURES = (
    "ps_extreme_progress_exact",
    "ps_to_cisd_minutes",
    "ps_to_entry_minutes",
    "ps_candle_range_source_fraction",
    "ps_candle_body_fraction",
    "ps_rejection_wick_fraction",
    "ps_close_away_fraction",
    "ps_externality_prior3_source_fraction",
    "ps_externality_prior6_source_fraction",
    "ps_threshold_distance_source_fraction",
    "ps_threshold_distance_risk_fraction",
    "threshold_to_entry_risk_fraction",
    "post_ps_min_distance_source_fraction",
    "post_ps_min_distance_risk_fraction",
    "post_ps_bars_before_cisd",
    "opposing_series_length",
)

DOL_CAPABLE_STAGES = frozenset(
    {
        "SELECTED_DOL_REACHED",
        "NEARER_DOL_REACHED_THEN_INVALIDATED",
        "NEARER_DOL_REACHED_WITHOUT_SELECTED_DOL",
    }
)
INVALIDATED_STAGE = "INVALIDATED_BEFORE_ANY_ACTIVE_DOL"


def _d(value: Any) -> Decimal:
    return Decimal(str(value))


def _ratio(numerator: Decimal | None, denominator: Decimal | None) -> Decimal | None:
    if numerator is None or denominator is None or denominator <= 0:
        return None
    return numerator / denominator


def _minutes(left: datetime, right: datetime) -> Decimal:
    return Decimal(str((right - left).total_seconds())) / Decimal(60)


def _median(rows: Sequence[Mapping[str, Any]], key: str) -> Decimal | None:
    values = sorted(_d(row[key]) for row in rows if row.get(key) is not None)
    if not values:
        return None
    middle = len(values) // 2
    if len(values) % 2:
        return values[middle]
    return (values[middle - 1] + values[middle]) / Decimal(2)


def _candle_geometry(candle: Any, side: Side) -> tuple[Decimal | None, Decimal | None, Decimal | None]:
    span = _d(candle.high) - _d(candle.low)
    if span <= 0:
        return None, None, None
    body = abs(_d(candle.close) - _d(candle.open)) / span
    if side is Side.LONG:
        rejection = (min(_d(candle.open), _d(candle.close)) - _d(candle.low)) / span
        close_away = (_d(candle.close) - _d(candle.low)) / span
    else:
        rejection = (_d(candle.high) - max(_d(candle.open), _d(candle.close))) / span
        close_away = (_d(candle.high) - _d(candle.close)) / span
    return body, max(rejection, Decimal(0)), close_away


def _externality(
    *,
    lower: Sequence[SourceCandle],
    extreme_index: int,
    side: Side,
    lookback: int,
    source_range: Decimal,
) -> Decimal | None:
    prior = lower[max(0, extreme_index - lookback):extreme_index]
    if not prior or source_range <= 0:
        return None
    extreme = lower[extreme_index].low if side is Side.LONG else lower[extreme_index].high
    if side is Side.LONG:
        reference = min(item.low for item in prior)
        excursion = max(Decimal(0), reference - extreme)
    else:
        reference = max(item.high for item in prior)
        excursion = max(Decimal(0), extreme - reference)
    return excursion / source_range


def _post_ps_min_distance(
    *,
    lower: Sequence[SourceCandle],
    extreme_index: int,
    confirm_index: int,
    side: Side,
    protected_swing: Decimal,
) -> Decimal | None:
    sample = lower[extreme_index + 1:confirm_index + 1]
    if not sample:
        return None
    if side is Side.LONG:
        return min(max(Decimal(0), item.low - protected_swing) for item in sample)
    return min(max(Decimal(0), protected_swing - item.high) for item in sample)


def _ps_features(setup: r3.Setup, trade: r3.RoutedTrade) -> dict[str, Any]:
    signal = setup.context.signal
    side = signal.side
    source = setup.source
    source_range = source.high - source.low
    lower = r3._lower_sources(source, setup.context.timeframe)
    found = causal_cisd(
        lower,
        side=side,
        extreme=signal.protected_swing,
    )
    if found is None or found.confirmed_at != signal.cisd_at:
        raise ValueError("R10 Protected Swing CISD reconstruction drift")

    extreme_index = next(
        (
            index
            for index, item in enumerate(lower)
            if item.opened_at == found.extreme_at
        ),
        None,
    )
    confirm_index = next(
        (
            index
            for index, item in enumerate(lower)
            if item.closed_at == found.confirmed_at
        ),
        None,
    )
    if extreme_index is None or confirm_index is None:
        raise ValueError("R10 Protected Swing lower-timeframe location missing")

    ps_candle = lower[extreme_index]
    body, rejection, close_away = _candle_geometry(ps_candle, side)
    risk = abs(trade.entry - trade.stop)
    threshold_distance = abs(found.threshold - signal.protected_swing)
    threshold_to_entry = abs(trade.entry - found.threshold)
    revisit = _post_ps_min_distance(
        lower=lower,
        extreme_index=extreme_index,
        confirm_index=confirm_index,
        side=side,
        protected_swing=signal.protected_swing,
    )
    source_minutes = _minutes(source.opened_at, source.closed_at)
    ps_range = ps_candle.high - ps_candle.low
    return {
        "ps_extreme_progress_exact": _ratio(
            _minutes(source.opened_at, found.extreme_at),
            source_minutes,
        ),
        "ps_to_cisd_minutes": _minutes(found.extreme_at, found.confirmed_at),
        "ps_to_entry_minutes": _minutes(found.extreme_at, trade.entry_at),
        "ps_candle_range_source_fraction": _ratio(ps_range, source_range),
        "ps_candle_body_fraction": body,
        "ps_rejection_wick_fraction": rejection,
        "ps_close_away_fraction": close_away,
        "ps_externality_prior3_source_fraction": _externality(
            lower=lower,
            extreme_index=extreme_index,
            side=side,
            lookback=3,
            source_range=source_range,
        ),
        "ps_externality_prior6_source_fraction": _externality(
            lower=lower,
            extreme_index=extreme_index,
            side=side,
            lookback=6,
            source_range=source_range,
        ),
        "ps_threshold_distance_source_fraction": _ratio(
            threshold_distance,
            source_range,
        ),
        "ps_threshold_distance_risk_fraction": _ratio(
            threshold_distance,
            risk,
        ),
        "threshold_to_entry_risk_fraction": _ratio(
            threshold_to_entry,
            risk,
        ),
        "post_ps_min_distance_source_fraction": _ratio(revisit, source_range),
        "post_ps_min_distance_risk_fraction": _ratio(revisit, risk),
        "post_ps_bars_before_cisd": confirm_index - extreme_index,
        "opposing_series_length": r9._opposing_series_length(
            setup,
            found.series_opened_at,
            found.extreme_at,
        ),
    }


def _outcome_class(stage: str) -> str:
    if stage in DOL_CAPABLE_STAGES:
        return "TOUCHED_ANY_ACTIVE_DOL"
    if stage == INVALIDATED_STAGE:
        return "INVALIDATED_BEFORE_ANY_ACTIVE_DOL"
    return "OTHER_DIAGNOSTIC"


def _period(rows: Sequence[dict[str, Any]], years: frozenset[int]) -> list[dict[str, Any]]:
    return [row for row in rows if int(row["year"]) in years]


def _feature_period(rows: Sequence[dict[str, Any]], feature: str) -> dict[str, Any]:
    capable = [row for row in rows if row["outcome_class"] == "TOUCHED_ANY_ACTIVE_DOL"]
    invalid = [
        row
        for row in rows
        if row["outcome_class"] == "INVALIDATED_BEFORE_ANY_ACTIVE_DOL"
    ]
    capable_median = _median(capable, feature)
    invalid_median = _median(invalid, feature)
    return {
        "dol_capable_n": len(capable),
        "invalidated_n": len(invalid),
        "dol_capable_median": None if capable_median is None else str(capable_median),
        "invalidated_median": None if invalid_median is None else str(invalid_median),
        "dol_capable_minus_invalidated_median": (
            None
            if capable_median is None or invalid_median is None
            else str(capable_median - invalid_median)
        ),
    }


def _family_report(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    periods = {
        "early_2016_2020": _period(rows, r9.EARLY_YEARS),
        "transition_2021_2023": _period(rows, r9.TRANSITION_YEARS),
        "recent_2024_2026": _period(rows, r9.RECENT_YEARS),
    }
    return {
        "trades": len(rows),
        "outcome_counts": {
            name: sum(1 for row in rows if row["outcome_class"] == name)
            for name in (
                "TOUCHED_ANY_ACTIVE_DOL",
                "INVALIDATED_BEFORE_ANY_ACTIVE_DOL",
                "OTHER_DIAGNOSTIC",
            )
        },
        "feature_separation": {
            feature: {
                period: _feature_period(period_rows, feature)
                for period, period_rows in periods.items()
            }
            for feature in FEATURES
        },
        "by_year_outcome_counts": {
            str(year): {
                name: sum(
                    1
                    for row in rows
                    if int(row["year"]) == year and row["outcome_class"] == name
                )
                for name in (
                    "TOUCHED_ANY_ACTIVE_DOL",
                    "INVALIDATED_BEFORE_ANY_ACTIVE_DOL",
                    "OTHER_DIAGNOSTIC",
                )
            }
            for year in range(2016, 2027)
        },
    }


def _jsonable(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def run(source_root: Path, target_root: Path, output: Path) -> dict[str, Any]:
    evidence, selected, reproduction = causal._reproduce_selected(source_root, target_root)
    episodes, _source_index = repair._load_targets_fail_closed(target_root)
    opens = tuple(bar.opened_at for bar in evidence.bars)
    d1 = r5._aggregate(evidence.bars, "D1")
    h4_regime = r5._aggregate(evidence.bars, "H4")
    family_rows: dict[str, list[dict[str, Any]]] = {
        name: [] for name in r8.BREAK_FAMILIES
    }
    retained = 0

    for setup, trade in selected:
        base = causal._record(setup, trade, evidence.bars, opens)
        base.update(r5._regime_features(base, d1, h4_regime))
        if r7._is_abstain(base):
            continue
        retained += 1
        family = next(
            (
                name
                for name, signature in r8.BREAK_FAMILIES.items()
                if r8._matches(base, signature)
            ),
            None,
        )
        if family is None:
            continue
        target_rows = episodes.get(trade.episode_id)
        if not target_rows:
            raise ValueError("R10 Protected Swing selected episode missing")
        path = divergence._path_diagnostic(trade, target_rows, evidence, opens)
        row: dict[str, Any] = {
            **base,
            **_ps_features(setup, trade),
            "journey_failure_stage": path["journey_failure_stage"],
            "outcome_class": _outcome_class(str(path["journey_failure_stage"])),
            "family": family,
            "year": datetime.fromisoformat(str(base["entry_at"])).year,
        }
        family_rows[family].append(row)

    if retained != 5612:
        raise ValueError(f"R10 Protected Swing R7 retained drift: {retained}")
    expected = {
        "BREAK_A_DEEP_RAID_MID_LATE_CISD": 151,
        "BREAK_B_MODERATE_RAID_MID_CISD_NORMAL_H4": 88,
    }
    for name, expected_count in expected.items():
        if len(family_rows[name]) != expected_count:
            raise ValueError(
                f"R10 Protected Swing family drift {name}: "
                f"{len(family_rows[name])} != {expected_count}"
            )

    payload = {
        "schema": "qore.turtle_soup_xauusd_r10.protected_swing_causality_forensics.v1",
        "identity": IDENTITY,
        "evidence_status": EVIDENCE_STATUS,
        "reproduction": {
            **reproduction,
            "r7_retained": retained,
            "break_a_trades": len(
                family_rows["BREAK_A_DEEP_RAID_MID_LATE_CISD"]
            ),
            "break_b_trades": len(
                family_rows["BREAK_B_MODERATE_RAID_MID_CISD_NORMAL_H4"]
            ),
        },
        "question": (
            "DO_PRE_ENTRY_PROTECTED_SWING_CAUSALITY_FEATURES_SEPARATE_"
            "DOL_CAPABLE_JOURNEYS_FROM_PRE_DOL_INVALIDATIONS_STABLY"
        ),
        "features": list(FEATURES),
        "families": {
            name: _family_report(rows)
            for name, rows in family_rows.items()
        },
        "interpretation_contract": {
            "post_entry_path_used_only_as_forensic_label": True,
            "post_entry_path_allowed_as_operating_input": False,
            "all_explanatory_features_known_by_entry": True,
            "automatic_threshold_search": False,
            "return_maximising_feature_selection": False,
            "candidate_rule_promoted": False,
        },
        "governance": {
            "diagnostic_only": True,
            "fresh_holdout_consumed": False,
            "year_or_date_allowed_as_operating_rule": False,
            "demo_eligible": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "protected-swing-causality-report.json").write_text(
        json.dumps(_jsonable(payload), indent=2, sort_keys=True) + "\n"
    )
    for family, filename in (
        ("BREAK_A_DEEP_RAID_MID_LATE_CISD", "break-a-protected-swing.json"),
        ("BREAK_B_MODERATE_RAID_MID_CISD_NORMAL_H4", "break-b-protected-swing.json"),
    ):
        (output / filename).write_text(
            json.dumps(_jsonable(family_rows[family]), indent=2, sort_keys=True)
            + "\n"
        )
    return cast(dict[str, Any], _jsonable(payload))


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit("usage: module SOURCE_ROOT TARGET_ROOT OUTPUT_DIR")
    print(
        json.dumps(
            run(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])),
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
