from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from qore.infrastructure.trader_lab.turtle_soup_xauusd_r11_situation_recognition_engine import (
    EvidenceGrade,
    SituationDirective,
    SituationObservation,
    SituationState,
    assess_situation,
    engine_manifest,
)


def _observation(
    *,
    family: str = "unknown",
    raid: str,
    reclaim: str,
    cisd: str,
    risk: str,
    h4: str | None = None,
    wick: str | None = None,
    h4_proximity: str | None = None,
    opposing_series: str | None = None,
    reviolation: str | None = None,
    raid_c1: str | None = None,
    ps_range: str | None = None,
    confirm_range: str | None = None,
) -> SituationObservation:
    def d(value: str | None) -> Decimal | None:
        return None if value is None else Decimal(value)

    signatures = {
        "invalid": {
            "raid_depth_range_bucket": "q4:<=0.50",
            "reclaim_latency_bucket": "<=5m",
            "cisd_progress_bucket": "q4:>0.75",
            "protected_risk_range_bucket": "q3:<=1.0",
            "h4_range_3v20": "normal_0.75_1.25",
        },
        "a": {
            "raid_depth_range_bucket": "q4:<=0.50",
            "reclaim_latency_bucket": "<=5m",
            "cisd_progress_bucket": "q3:<=0.75",
            "protected_risk_range_bucket": "q3:<=1.0",
            "h4_range_3v20": "normal_0.75_1.25",
        },
        "b": {
            "raid_depth_range_bucket": "q3:<=0.25",
            "reclaim_latency_bucket": "<=5m",
            "cisd_progress_bucket": "q2:<=0.50",
            "protected_risk_range_bucket": "q3:<=1.0",
            "h4_range_3v20": "normal_0.75_1.25",
        },
        "unknown": {
            "raid_depth_range_bucket": "q2:<=0.10",
            "reclaim_latency_bucket": "<=5m",
            "cisd_progress_bucket": "q2:<=0.50",
            "protected_risk_range_bucket": "q2:<=0.50",
            "h4_range_3v20": "normal_0.75_1.25",
        },
    }
    signature = signatures[family]

    return SituationObservation(
        observed_at=datetime(2026, 9, 17, 12, tzinfo=UTC),
        side="short",
        source_timeframe="H1",
        raid_depth_source_fraction=Decimal(raid),
        reclaim_latency_minutes=Decimal(reclaim),
        cisd_progress_exact=Decimal(cisd),
        protected_risk_source_fraction=Decimal(risk),
        h4_range_state=h4,
        raid_depth_range_bucket=signature["raid_depth_range_bucket"],
        reclaim_latency_bucket=signature["reclaim_latency_bucket"],
        cisd_progress_bucket=signature["cisd_progress_bucket"],
        protected_risk_range_bucket=signature["protected_risk_range_bucket"],
        h4_range_3v20=signature["h4_range_3v20"],
        c1_directional_wick_fraction=d(wick),
        c1_nearest_prior_h4_boundary_source_fraction=d(h4_proximity),
        opposing_series_length=d(opposing_series),
        post_reclaim_max_reviolation_source_fraction=d(reviolation),
        raid_depth_c1_range_fraction=d(raid_c1),
        ps_candle_range_source_fraction=d(ps_range),
        confirm_bar_range_vs_prior6_m5=d(confirm_range),
        active_dol_count=3,
        selected_dol_family="PRIOR_H4_DIRECTIONAL_BOUNDARY",
        selected_dol_distance_source_fraction=Decimal("1.2"),
    )


def test_robust_invalid_is_known_invalid_and_abstains() -> None:
    result = assess_situation(
        _observation(
            family="invalid",
            raid="0.35",
            reclaim="4",
            cisd="0.80",
            risk="0.75",
        )
    )
    assert result.state is SituationState.KNOWN_INVALID
    assert result.directive is SituationDirective.ABSTAIN_STRUCTURAL
    assert result.evidence_grade is EvidenceGrade.ESTABLISHED_NEGATIVE
    assert result.operating_permission is False
    assert result.knowledge_claim_codes == ("K01_ROBUST_INVALID_DEEP_RAID_LATE_CISD",)


def test_break_a_strong_multichannel_match_is_research_candidate_only() -> None:
    result = assess_situation(
        _observation(
            family="a",
            raid="0.35",
            reclaim="4",
            cisd="0.65",
            risk="0.75",
            wick="0.30",
            reviolation="0.20",
            opposing_series="3",
            h4_proximity="0.10",
        )
    )
    assert result.state is SituationState.STRUCTURALLY_VALID_CANDIDATE
    assert result.directive is SituationDirective.RESEARCH_CANDIDATE_NO_ENTRY
    assert result.evidence_grade is EvidenceGrade.MULTICHANNEL_TRANSFERRED_CLUE
    assert result.operating_permission is False
    assert "K09_BREAK_A_MULTICHANNEL_TRANSFER_CLUE" in result.knowledge_claim_codes
    signals = {item.code: item.matched for item in result.evidence_signals}
    assert signals["A_LIQUIDITY_DIRECTIONAL_WICK"] is True
    assert signals["A_CISD_POST_RECLAIM_REVIOLATION"] is True


def test_break_a_missing_one_strong_channel_remains_conflicted() -> None:
    result = assess_situation(
        _observation(
            family="a",
            raid="0.35",
            reclaim="4",
            cisd="0.65",
            risk="0.75",
            wick="0.30",
            reviolation="0.50",
            opposing_series="4",
        )
    )
    assert result.state is SituationState.CONFLICTED
    assert result.directive is SituationDirective.ABSTAIN_CONFLICTED
    assert result.operating_permission is False


def test_break_b_favorable_pair_does_not_become_positive_permission() -> None:
    result = assess_situation(
        _observation(
            family="b",
            raid="0.20",
            reclaim="4",
            cisd="0.40",
            risk="0.75",
            h4="normal_0.75_1.25",
            raid_c1="0.20",
            ps_range="0.50",
            confirm_range="0.90",
            reviolation="0.20",
        )
    )
    assert result.state is SituationState.CONFLICTED
    assert result.directive is SituationDirective.ABSTAIN_CONFLICTED
    assert result.evidence_grade is EvidenceGrade.CONFLICTED_WITH_CONTEXT
    assert result.operating_permission is False
    assert "K10_BREAK_B_RAID_PS_TRANSFER_CLUE" in result.knowledge_claim_codes
    assert "K11_BREAK_B_CISD_EXPANSION_NOT_STABLE" in result.knowledge_claim_codes


def test_unresolved_anatomy_is_unknown_not_permission() -> None:
    result = assess_situation(
        _observation(
            raid="0.07",
            reclaim="3",
            cisd="0.30",
            risk="0.40",
        )
    )
    assert result.state is SituationState.UNKNOWN
    assert result.directive is SituationDirective.NO_DECISION
    assert result.operating_permission is False


def test_missing_break_a_secondary_context_does_not_block_strong_pair() -> None:
    result = assess_situation(
        _observation(
            family="a",
            raid="0.35",
            reclaim="4",
            cisd="0.65",
            risk="0.75",
            wick="0.25",
            reviolation="0.30",
        )
    )
    assert result.state is SituationState.STRUCTURALLY_VALID_CANDIDATE
    signals = {item.code: item.matched for item in result.evidence_signals}
    assert signals["A_PS_OPPOSING_SERIES"] is None
    assert signals["A_LIQUIDITY_H4_PROXIMITY"] is None



def test_continuous_a_like_values_cannot_broaden_exact_evidence_family() -> None:
    result = assess_situation(
        _observation(
            family="unknown",
            raid="0.35",
            reclaim="4",
            cisd="0.65",
            risk="0.75",
            wick="0.30",
            reviolation="0.20",
        )
    )
    assert result.state is SituationState.UNKNOWN
    assert result.mechanism_code == "UNRESOLVED_JOURNEY"
    assert result.operating_permission is False


def test_engine_manifest_is_fail_closed() -> None:
    payload = engine_manifest()
    assert payload["reasoning_contract"]["pnl_score"] is False
    assert payload["reasoning_contract"]["probability_of_profit"] is False
    assert payload["reasoning_contract"]["automatic_threshold_search"] is False
    assert payload["reasoning_contract"]["later_period_recalibration"] is False
    assert (
        payload["reasoning_contract"][
            "continuous_values_can_define_evidence_family_membership"
        ]
        is False
    )
    assert (
        payload["reasoning_contract"][
            "evidence_family_membership_uses_exact_r7_r8_buckets"
        ]
        is True
    )
    assert payload["reasoning_contract"]["year_or_date_operating_input"] is False
    assert payload["reasoning_contract"]["post_entry_input"] is False
    assert (
        payload["reasoning_contract"][
            "structurally_valid_candidate_is_operating_permission"
        ]
        is False
    )
    assert payload["governance"]["candidate_promoted"] is False
    assert payload["governance"]["fresh_holdout_consumed"] is False
    assert payload["governance"]["live_authorized"] is False
    assert payload["governance"]["real_capital_authorized"] is False
