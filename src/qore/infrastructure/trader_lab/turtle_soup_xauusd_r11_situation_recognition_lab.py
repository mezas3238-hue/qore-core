"""Consumed-evidence audit for the R11 Situation Recognition Engine.

The engine receives only pre-entry observations. Post-entry journey path is
attached afterwards strictly as a forensic label so we can audit whether each
recognized state retained structural capacity through time.

PnL is intentionally excluded from the recognition audit.
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

from qore.infrastructure.trader_lab import turtle_soup_xauusd_r3_causal_regime_forensics as causal
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r3_cibo_journey_binding_repair as repair
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r5_regime_journey_validity_forensics as r5
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r9_causal_break_discriminator as r9
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r9_cisd_sequence_forensics as cisd
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r9_journey_divergence_forensics as divergence
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r9_liquidity_significance_forensics as liquidity
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r10_protected_swing_causality_forensics as ps
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r11_situation_recognition_engine as engine
from qore.infrastructure.trader_lab.ict_turtle_soup_r4_source_exact import (
    SourceCandle,
    build_daily,
    build_h1,
    build_h4,
)

IDENTITY = "TURTLE_SOUP_XAUUSD_R11_SITUATION_RECOGNITION_LAB_V1"
EVIDENCE_STATUS = (
    "CONSUMED_CIBO_10Y_ENGINE_RECOGNITION_AUDIT_NOT_FRESH_HOLDOUT"
)

CAPABLE = "TOUCHED_ANY_ACTIVE_DOL"
INVALIDATED = "INVALIDATED_BEFORE_ANY_ACTIVE_DOL"
PERIODS = {
    "early_2016_2020": frozenset(range(2016, 2021)),
    "transition_2021_2023": frozenset(range(2021, 2024)),
    "recent_2024_2026": frozenset(range(2024, 2027)),
}


def _d(value: Any) -> Decimal:
    return Decimal(str(value))


def _optional_d(value: Any) -> Decimal | None:
    return None if value is None else _d(value)


def _build_observation(row: dict[str, Any]) -> engine.SituationObservation:
    return engine.SituationObservation(
        observed_at=datetime.fromisoformat(str(row["entry_at"])),
        side=str(row["side"]),
        source_timeframe=str(row["timeframe"]),
        raid_depth_source_fraction=_d(row["raid_depth_source_fraction"]),
        reclaim_latency_minutes=_d(row["reclaim_latency_minutes"]),
        cisd_progress_exact=_d(row["cisd_progress_exact"]),
        protected_risk_source_fraction=_d(
            row["protected_risk_source_fraction_exact"]
        ),
        h4_range_state=(
            None if row.get("h4_range_state") is None else str(row["h4_range_state"])
        ),
        raid_depth_range_bucket=str(row["raid_depth_range_bucket"]),
        reclaim_latency_bucket=str(row["reclaim_latency_bucket"]),
        cisd_progress_bucket=str(row["cisd_progress_bucket"]),
        protected_risk_range_bucket=str(row["protected_risk_range_bucket"]),
        h4_range_3v20=(
            None if row.get("h4_range_3v20") is None else str(row["h4_range_3v20"])
        ),
        c1_directional_wick_fraction=_optional_d(
            row.get("c1_directional_wick_fraction")
        ),
        c1_nearest_prior_h4_boundary_source_fraction=_optional_d(
            row.get("c1_nearest_prior_h4_boundary_source_fraction")
        ),
        opposing_series_length=_optional_d(row.get("opposing_series_length")),
        post_reclaim_max_reviolation_source_fraction=_optional_d(
            row.get("post_reclaim_max_reviolation_source_fraction")
        ),
        raid_depth_c1_range_fraction=_optional_d(
            row.get("raid_depth_c1_range_fraction")
        ),
        ps_candle_range_source_fraction=_optional_d(
            row.get("ps_candle_range_source_fraction")
        ),
        confirm_bar_range_vs_prior6_m5=_optional_d(
            row.get("confirm_bar_range_vs_prior6_m5")
        ),
        active_dol_count=(
            None if row.get("active_dol_count") is None else int(row["active_dol_count"])
        ),
        selected_dol_family=(
            None if row.get("selected_dol_family") is None else str(row["selected_dol_family"])
        ),
        selected_dol_distance_source_fraction=_optional_d(
            row.get("dol_distance_source_fraction")
        ),
    )


def _capacity_profile(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    binary = [
        row
        for row in rows
        if row["outcome_class"] in {CAPABLE, INVALIDATED}
    ]
    capable = sum(1 for row in binary if row["outcome_class"] == CAPABLE)
    invalidated = sum(1 for row in binary if row["outcome_class"] == INVALIDATED)
    rate = None if not binary else Decimal(capable) / Decimal(len(binary))
    return {
        "trades": len(rows),
        "binary_labeled": len(binary),
        "dol_capable": capable,
        "invalidated_before_any_active_dol": invalidated,
        "excluded_other_diagnostic": len(rows) - len(binary),
        "dol_capable_rate": None if rate is None else str(rate),
    }


def _state_profiles(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    states = [item.value for item in engine.SituationState]
    return {
        state: _capacity_profile(
            [row for row in rows if row["recognized_state"] == state]
        )
        for state in states
    }


def _period_profiles(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    return {
        period: _state_profiles(
            [row for row in rows if int(row["year"]) in years]
        )
        for period, years in PERIODS.items()
    }


def _mechanism_profiles(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    mechanisms = sorted({str(row["mechanism_code"]) for row in rows})
    return {
        mechanism: {
            "trades": len(members := [
                row for row in rows if row["mechanism_code"] == mechanism
            ]),
            "states": dict(Counter(row["recognized_state"] for row in members)),
            "periods": _period_profiles(members),
        }
        for mechanism in mechanisms
    }


def _by_year(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[int(row["year"])].append(row)
    return {
        str(year): {
            "trades": len(grouped[year]),
            "states": dict(Counter(row["recognized_state"] for row in grouped[year])),
            "state_profiles": _state_profiles(grouped[year]),
        }
        for year in sorted(grouped)
    }


def _jsonable(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    return value


def run(source_root: Path, target_root: Path, output: Path) -> dict[str, Any]:
    evidence, selected, reproduction = causal._reproduce_selected(source_root, target_root)
    episodes, _ = repair._load_targets_fail_closed(target_root)
    opens = tuple(bar.opened_at for bar in evidence.bars)

    h1 = build_h1(evidence.bars)
    h4 = build_h4(evidence.bars)
    daily = build_daily(h4)
    frames: dict[str, Sequence[SourceCandle]] = {"H1": h1, "H4": h4}
    frame_indexes = {
        timeframe: {candle.opened_at: index for index, candle in enumerate(candles)}
        for timeframe, candles in frames.items()
    }
    frame_by_open = {
        timeframe: {candle.opened_at: candle for candle in candles}
        for timeframe, candles in frames.items()
    }
    h1_opens = tuple(candle.opened_at for candle in h1)
    h4_opens = tuple(candle.opened_at for candle in h4)
    d1_opens = tuple(candle.opened_at for candle in daily)
    d1_regime = r5._aggregate(evidence.bars, "D1")
    h4_regime = r5._aggregate(evidence.bars, "H4")

    recognized: list[dict[str, Any]] = []

    for setup, trade in selected:
        base = causal._record(setup, trade, evidence.bars, opens)
        base.update(r5._regime_features(base, d1_regime, h4_regime))

        timeframe = setup.context.timeframe
        c1 = frame_by_open[timeframe].get(setup.context.signal.c1_opened_at)
        if c1 is None:
            raise ValueError("R11 recognition lab missing C1")

        target_rows = episodes.get(trade.episode_id)
        if not target_rows:
            raise ValueError("R11 recognition lab missing target episode")

        prior20 = r9._mean_prior_source_range(
            frames[timeframe],
            frame_indexes[timeframe],
            setup.source.opened_at,
        )
        row: dict[str, Any] = dict(base)
        row["timeframe"] = timeframe
        row["side"] = setup.context.signal.side.value
        row.update(
            r9._continuous_record(
                setup,
                trade,
                c1,
                prior20,
                h1,
                h1_opens,
                h4,
                h4_opens,
                d1_regime,
                h4_regime,
                target_rows,
            )
        )
        row.update(
            liquidity._features(
                setup,
                c1,
                frames,
                frame_indexes,
                h1,
                h4,
                daily,
                h4_opens,
                d1_opens,
            )
        )
        row.update(cisd._sequence_features(setup, c1))
        row.update(ps._ps_features(setup, trade))

        assessment = engine.assess_situation(_build_observation(row))

        # Post-entry information is attached only after recognition.
        path = divergence._path_diagnostic(
            trade,
            target_rows,
            evidence,
            opens,
        )
        outcome_class = ps._outcome_class(str(path["journey_failure_stage"]))

        recognized.append(
            {
                "episode_id": trade.episode_id,
                "entry_at": str(row["entry_at"]),
                "year": datetime.fromisoformat(str(row["entry_at"])).year,
                "side": str(row["side"]),
                "timeframe": str(row["timeframe"]),
                "mechanism_code": assessment.mechanism_code,
                "recognized_state": assessment.state.value,
                "directive": assessment.directive.value,
                "evidence_grade": assessment.evidence_grade.value,
                "knowledge_claim_codes": list(assessment.knowledge_claim_codes),
                "matched_signal_codes": [
                    signal.code
                    for signal in assessment.evidence_signals
                    if signal.matched is True
                ],
                "unknown_signal_codes": [
                    signal.code
                    for signal in assessment.evidence_signals
                    if signal.matched is None
                ],
                "journey_failure_stage": path["journey_failure_stage"],
                "outcome_class": outcome_class,
                "operating_permission": assessment.operating_permission,
            }
        )

    if len(recognized) != len(selected):
        raise ValueError(
            f"R11 recognition count drift: {len(recognized)} != {len(selected)}"
        )

    mechanism_counts = Counter(row["mechanism_code"] for row in recognized)
    expected_mechanisms = {
        "ROBUST_INVALID_DEEP_RAID_LATE_CISD": 273,
        "BREAK_A_DEEP_RAID_MID_LATE_CISD": 151,
        "BREAK_B_MODERATE_RAID_MID_CISD_NORMAL_H4": 88,
    }
    for mechanism, expected_count in expected_mechanisms.items():
        actual = mechanism_counts.get(mechanism, 0)
        if actual != expected_count:
            raise ValueError(
                f"R11 exact evidence-family drift {mechanism}: "
                f"{actual} != {expected_count}"
            )

    state_counts = dict(Counter(row["recognized_state"] for row in recognized))
    candidate_rows = [
        row
        for row in recognized
        if row["recognized_state"]
        == engine.SituationState.STRUCTURALLY_VALID_CANDIDATE.value
    ]
    if len(candidate_rows) != 31:
        raise ValueError(
            f"R11 BREAK A pre-entry candidate drift: "
            f"{len(candidate_rows)} != 31"
        )
    candidate_binary = [
        row
        for row in candidate_rows
        if row["outcome_class"] in {CAPABLE, INVALIDATED}
    ]
    if len(candidate_binary) != 30:
        raise ValueError(
            f"R11 BREAK A binary-auditable candidate drift: "
            f"{len(candidate_binary)} != 30"
        )

    payload = {
        "schema": "qore.turtle_soup_xauusd_r11.situation_recognition_lab.v1",
        "identity": IDENTITY,
        "engine_identity": engine.IDENTITY,
        "evidence_status": EVIDENCE_STATUS,
        "reproduction": {
            **reproduction,
            "recognized_trades": len(recognized),
            "robust_invalid_exact": mechanism_counts[
                "ROBUST_INVALID_DEEP_RAID_LATE_CISD"
            ],
            "break_a_exact": mechanism_counts["BREAK_A_DEEP_RAID_MID_LATE_CISD"],
            "break_b_exact": mechanism_counts[
                "BREAK_B_MODERATE_RAID_MID_CISD_NORMAL_H4"
            ],
            "break_a_pre_entry_candidate_exact": len(candidate_rows),
            "break_a_binary_auditable_candidate_exact": len(candidate_binary),
        },
        "recognition_contract": {
            "engine_receives_post_entry_information": False,
            "post_entry_path_used_only_after_recognition_as_label": True,
            "pnl_used_for_recognition": False,
            "pnl_used_for_audit": False,
            "year_or_date_used_by_engine": False,
            "frozen_anchor_recalibration": False,
            "evidence_family_membership_exact_r7_r8_buckets": True,
            "continuous_values_can_broaden_evidence_family": False,
            "structurally_valid_candidate_is_operating_permission": False,
            "post_entry_other_diagnostic_can_remove_pre_entry_candidate": False,
        },
        "state_counts": state_counts,
        "full_state_profiles": _state_profiles(recognized),
        "temporal_state_profiles": _period_profiles(recognized),
        "mechanism_profiles": _mechanism_profiles(recognized),
        "by_year_diagnostic": _by_year(recognized),
        "positive_candidate_audit": {
            "state": engine.SituationState.STRUCTURALLY_VALID_CANDIDATE.value,
            "trades": len(candidate_rows),
            "full": _capacity_profile(candidate_rows),
            "temporal": {
                period: _capacity_profile(
                    [
                        row
                        for row in candidate_rows
                        if int(row["year"]) in years
                    ]
                )
                for period, years in PERIODS.items()
            },
            "interpretation": (
                "RESEARCH_ONLY_TRANSFER_AUDIT_NOT_POSITIVE_ENTRY_AUTHORIZATION"
            ),
        },
        "governance": {
            "diagnostic_only": True,
            "candidate_promoted": False,
            "fresh_holdout_consumed": False,
            "demo_eligible": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }

    output.mkdir(parents=True, exist_ok=True)
    (output / "situation-recognition-report.json").write_text(
        json.dumps(_jsonable(payload), indent=2, sort_keys=True) + "\n"
    )
    (output / "recognized-cases.json").write_text(
        json.dumps(_jsonable(recognized), indent=2, sort_keys=True) + "\n"
    )
    (output / "engine-manifest.json").write_text(
        json.dumps(_jsonable(engine.engine_manifest()), indent=2, sort_keys=True) + "\n"
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
