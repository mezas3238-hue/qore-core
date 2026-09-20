from __future__ import annotations

from qore.infrastructure.trader_lab.capitalizer_contract import (
    CapitalizerSession,
    allowed_markets,
)
from qore.infrastructure.trader_lab.capitalizer_market_stop_intelligence_v1 import (
    CAUSE_DIMENSIONS,
    IDENTITY,
    MATRIX_IDENTITY,
    CapitalizerMarketStopIntelligenceDossier,
    build_market_dossier_from_payloads,
    build_matrix_from_dossiers,
)


def _cause(symbol: str, session: CapitalizerSession) -> dict[str, object]:
    cohorts: list[dict[str, object]] = []
    keys = {
        "WEEKDAY": "MONDAY",
        "NY_HOUR": "10",
        "SESSION_ELAPSED_HOUR": "H3",
        "SIDE": "LONG",
        "EVENT_SIGNATURE": "HIGH_ACCEPTANCE",
        "EVENT_FAMILY": "ACCEPTANCE",
        "PLANNED_REWARD_BAND": "GE_3R",
        "RELATIVE_STOP_WIDTH_QUARTILE": "Q1_TIGHTEST",
        "REPEAT_STATE": "REPEAT",
        "RECLAIM_STATE": "RECLAIM_MIXED",
        "H1_SOURCE_AGE": "CURRENT_H1_SOURCE",
        "H1_EPISODE_MULTIPLICITY": "MULTI_EPISODE",
        "H1_BOUNDARY_MULTIPLICITY": "MULTI_SOURCE_BOUNDARY",
        "SOURCE_TIMING": "ALL_WITHIN_H1",
        "CISD_TIMING": "ALL_WITHIN_H1",
        "REPEAT_X_RECLAIM": "REPEAT|RECLAIM_MIXED",
        "RISK_X_ELAPSED": "Q1_TIGHTEST|H3",
        "RISK_X_REPEAT": "Q1_TIGHTEST|REPEAT",
        "EVENT_X_REPEAT": "ACCEPTANCE|REPEAT",
    }
    assert set(keys) == set(CAUSE_DIMENSIONS)
    for dimension, key in keys.items():
        cohorts.append(
            {
                "dimension": dimension,
                "key": key,
                "trades": 200,
                "stops": 120,
                "stop_rate": "0.6",
                "baseline_stop_rate": "0.5",
                "relative_lift": "1.2",
            }
        )

    return {
        "identity": "QORE_CAPITALIZER_STOP_LOSS_CAUSAL_FORENSICS_V1",
        "symbol": symbol,
        "session": session.value,
        "trades": 1000,
        "stops": 500,
        "baseline_stop_rate": "0.5",
        "cohorts": cohorts,
        "post_stop_recovery": {
            "stops": 500,
            "later_target_reached": 150,
            "later_target_reached_rate": "0.3",
            "recovered_le_0_25r": 25,
            "recovered_le_0_5r": 50,
            "recovered_le_1_0r": 75,
            "recovered_overshoot_median_r": "0.8",
            "recovered_overshoot_p90_r": "2.0",
            "not_recovered_extension_median_r": "2.0",
            "not_recovered_extension_p90_r": "4.0",
        },
        "source_strategy_status": "WAIT_M1_EVIDENCE",
        "rule_promotion_allowed": False,
    }


def _breathing(symbol: str, session: CapitalizerSession) -> dict[str, object]:
    return {
        "identity": "QORE_CAPITALIZER_STRUCTURAL_STOP_BREATHING_PROBE_V1",
        "symbol": symbol,
        "session": session.value,
        "modes": [
            {
                "mode": "SOURCE_M5_EXTREME",
                "trades": 1000,
                "wins": 500,
                "losses": 500,
                "flats": 0,
                "total_gross_r": "100",
                "profit_factor": "1.4",
                "max_drawdown_r": "20",
                "max_losing_streak": 10,
                "stop_exits": 500,
                "target_exits": 400,
                "session_exits": 100,
                "same_m5_ambiguities": 0,
                "median_stop_width_vs_baseline": "1",
                "unchanged_due_to_history_gap": 0,
            },
            {
                "mode": "TWO_CLOSED_M5_EXTREME",
                "trades": 1000,
                "wins": 520,
                "losses": 480,
                "flats": 0,
                "total_gross_r": "120",
                "profit_factor": "1.6",
                "max_drawdown_r": "12",
                "max_losing_streak": 8,
                "stop_exits": 480,
                "target_exits": 420,
                "session_exits": 100,
                "same_m5_ambiguities": 0,
                "median_stop_width_vs_baseline": "1.3",
                "unchanged_due_to_history_gap": 0,
            },
            {
                "mode": "THREE_CLOSED_M5_EXTREME",
                "trades": 1000,
                "wins": 530,
                "losses": 470,
                "flats": 0,
                "total_gross_r": "130",
                "profit_factor": "1.7",
                "max_drawdown_r": "9",
                "max_losing_streak": 7,
                "stop_exits": 470,
                "target_exits": 430,
                "session_exits": 100,
                "same_m5_ambiguities": 0,
                "median_stop_width_vs_baseline": "1.5",
                "unchanged_due_to_history_gap": 0,
            },
        ],
        "diagnostic_only": True,
        "stop_widening_authorized": False,
    }


def _correction(symbol: str, session: CapitalizerSession) -> dict[str, object]:
    return {
        "identity": "QORE_CAPITALIZER_PROTECTED_SWING_CORRECTED_REPLAY_V1",
        "symbol": symbol,
        "session": session.value,
        "protected_swing_surrogate_coverage": "0.4",
        "baseline_matched_metrics": {
            "trades": 400,
            "wins": 200,
            "losses": 200,
            "flats": 0,
            "total_gross_r": "50",
            "mean_gross_r": "0.125",
            "gross_profit_r": "280",
            "gross_loss_r": "200",
            "profit_factor": "1.4",
            "max_drawdown_r": "15",
            "max_losing_streak": 9,
            "median_planned_reward_r": "2",
            "median_bars_held": "3",
            "stop_exits": 200,
            "target_exits": 150,
            "session_exits": 50,
            "ambiguous_stop_first_exits": 0,
        },
        "corrected_matched_metrics": {
            "trades": 400,
            "wins": 220,
            "losses": 180,
            "flats": 0,
            "total_gross_r": "80",
            "mean_gross_r": "0.2",
            "gross_profit_r": "288",
            "gross_loss_r": "180",
            "profit_factor": "1.6",
            "max_drawdown_r": "10",
            "max_losing_streak": 7,
            "median_planned_reward_r": "1.8",
            "median_bars_held": "4",
            "stop_exits": 180,
            "target_exits": 165,
            "session_exits": 55,
            "ambiguous_stop_first_exits": 0,
        },
        "median_corrected_stop_width_vs_baseline": "1.15",
        "transitions": [
            {"baseline_exit": "STOP", "corrected_exit": "TARGET", "trades": 30},
            {"baseline_exit": "STOP", "corrected_exit": "SESSION_EXIT", "trades": 20},
        ],
        "m1_evidence_present": False,
        "source_faithful_replay_complete": False,
        "rule_promotion_allowed": False,
    }


def _dossier(
    symbol: str,
    session: CapitalizerSession,
) -> CapitalizerMarketStopIntelligenceDossier:
    return build_market_dossier_from_payloads(
        cause=_cause(symbol, session),
        breathing=_breathing(symbol, session),
        correction=_correction(symbol, session),
    )


def test_market_dossier_contains_complete_stop_intelligence_boundary() -> None:
    report = _dossier("EURUSD", CapitalizerSession.LONDON)

    assert report.identity == IDENTITY
    assert report.ict_original_primary is True
    assert report.ttrades_secondary_refinement is True
    assert report.structural_stop_anchor_dual_source_compatible is True
    assert report.exact_stop_expression_universal is False
    assert report.native_m1_required is True
    assert report.native_m1_present is False
    assert report.full_source_faithful_stop_replay_complete is False

    assert report.replay_trades == 1000
    assert report.stop_exits == 500
    assert report.baseline_stop_rate == "0.5"
    assert "REPEAT_STATE:REPEAT" in report.recurring_signal_flags
    assert "RECLAIM_STATE:RECLAIM_MIXED" in report.recurring_signal_flags
    assert "SESSION_ELAPSED_HOUR:H3" in report.recurring_signal_flags

    assert report.later_target_reached_after_stop_rate == "0.3"
    assert report.later_target_reached_with_le_0_5r_extra_count == 50
    assert report.later_target_reached_with_le_0_5r_extra_rate == "0.1"

    assert report.lowest_dd_breathing_probe == "THREE_CLOSED_M5_EXTREME"
    assert report.lowest_dd_breathing_probe_dd_r == "9"
    assert report.lowest_dd_probe_reaches_owner_6r is False

    assert report.protected_swing_pf_delta == "0.2"
    assert report.protected_swing_dd_reduction_r == "5"
    assert report.protected_swing_losing_streak_reduction == 2
    assert report.protected_swing_reaches_owner_6r is False
    assert report.stop_geometry_material is True
    assert report.entry_context_still_material is True

    assert report.rule_promotion_allowed is False
    assert report.stop_rule_frozen is False
    assert report.economic_candidate is False
    assert report.trader_certified is False


def test_nine_market_matrix_requires_every_market_and_preserves_governance() -> None:
    dossiers = tuple(
        _dossier(symbol, session)
        for session in CapitalizerSession
        for symbol in allowed_markets(session)
    )
    matrix = build_matrix_from_dossiers(dossiers)

    assert matrix.identity == MATRIX_IDENTITY
    assert matrix.complete_nine_market_universe is True
    assert len(matrix.markets) == 9
    assert len(matrix.markets_where_stop_geometry_material) == 9
    assert len(matrix.markets_where_entry_context_still_material) == 9
    assert matrix.markets_reaching_owner_6r_on_any_stop_probe == ()
    assert dict(matrix.recurring_signal_market_counts)["REPEAT_STATE:REPEAT"] == 9
    assert matrix.native_m1_required is True
    assert matrix.native_m1_present is False
    assert matrix.rule_promotion_allowed is False
    assert matrix.economic_candidate is False
    assert matrix.trader_certified is False
