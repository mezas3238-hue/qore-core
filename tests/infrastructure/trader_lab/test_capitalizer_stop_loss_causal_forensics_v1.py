from __future__ import annotations

from qore.infrastructure.trader_lab.capitalizer_contract import (
    CapitalizerSession,
    allowed_markets,
)
from qore.infrastructure.trader_lab.capitalizer_stop_loss_causal_forensics_v1 import (
    IDENTITY,
    MATRIX_IDENTITY,
    CapitalizerPostStopRecovery,
    CapitalizerStopCausalCohort,
    CapitalizerStopCauseMarketReport,
    _reward_band,
    _session_elapsed_hour,
    build_matrix_from_reports,
)


def _market_report(
    symbol: str,
    session: CapitalizerSession,
    *,
    lift: str,
) -> CapitalizerStopCauseMarketReport:
    return CapitalizerStopCauseMarketReport(
        identity=IDENTITY,
        symbol=symbol,
        session=session.value,
        trades=100,
        stops=50,
        baseline_stop_rate="0.5",
        cohorts=(
            CapitalizerStopCausalCohort(
                dimension="REPEAT_STATE",
                key="REPEAT",
                trades=40,
                stops=22,
                stop_rate="0.55",
                baseline_stop_rate="0.5",
                relative_lift=lift,
            ),
        ),
        post_stop_recovery=CapitalizerPostStopRecovery(
            stops=50,
            later_target_reached=10,
            later_target_reached_rate="0.2",
            recovered_le_0_25r=2,
            recovered_le_0_5r=3,
            recovered_le_1_0r=5,
            recovered_overshoot_median_r="0.8",
            recovered_overshoot_p90_r="2.0",
            not_recovered_extension_median_r="1.5",
            not_recovered_extension_p90_r="4.0",
        ),
    )


def test_reward_bands_are_structural_and_deterministic() -> None:
    assert _reward_band({"planned_reward_r": "0.9"}) == "LT_1R"
    assert _reward_band({"planned_reward_r": "1.2"}) == "1_TO_LT_1_5R"
    assert _reward_band({"planned_reward_r": "1.7"}) == "1_5_TO_LT_2R"
    assert _reward_band({"planned_reward_r": "2.5"}) == "2_TO_LT_3R"
    assert _reward_band({"planned_reward_r": "3.0"}) == "GE_3R"


def test_elapsed_hour_respects_frozen_session_starts() -> None:
    assert (
        _session_elapsed_hour(
            {"entry_at": "2026-01-05T03:00:00+00:00", "session": "ASIA"}
        )
        == "H2"
    )
    assert (
        _session_elapsed_hour(
            {"entry_at": "2026-01-05T08:00:00+00:00", "session": "LONDON"}
        )
        == "H1"
    )


def test_matrix_requires_complete_universe_and_stays_diagnostic() -> None:
    reports = tuple(
        _market_report(symbol, session, lift="1.10")
        for session in CapitalizerSession
        for symbol in allowed_markets(session)
    )
    matrix = build_matrix_from_reports(reports)

    assert matrix.identity == MATRIX_IDENTITY
    assert matrix.complete_nine_market_universe is True
    assert len(matrix.markets) == 9
    assert "REPEAT_STATE:REPEAT" in matrix.universal_elevated
    assert matrix.causal_claimed is False
    assert matrix.rule_promotion_allowed is False
    assert matrix.stop_widening_authorized is False
    assert matrix.economic_candidate is False
    assert matrix.trader_certified is False


def test_market_report_cannot_claim_execution_authority() -> None:
    report = _market_report("USDJPY", CapitalizerSession.ASIA, lift="1.10")
    assert report.source_strategy_status == "WAIT_M1_EVIDENCE"
    assert report.outcome_aware_forensics is True
    assert report.causal_claimed is False
    assert report.rule_promotion_allowed is False
    assert report.stop_widening_authorized is False
    assert report.trader_certified is False
