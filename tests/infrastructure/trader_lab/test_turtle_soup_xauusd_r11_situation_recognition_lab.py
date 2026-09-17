from __future__ import annotations

from qore.infrastructure.trader_lab.turtle_soup_xauusd_r11_situation_recognition_lab import (
    CAPABLE,
    INVALIDATED,
    _capacity_profile,
    _period_profiles,
    _state_profiles,
)
from qore.infrastructure.trader_lab.turtle_soup_xauusd_r11_situation_recognition_engine import (
    SituationState,
)


def _row(year: int, state: str, outcome: str) -> dict[str, object]:
    return {
        "year": year,
        "recognized_state": state,
        "outcome_class": outcome,
    }


def test_capacity_profile_uses_structural_journey_label_not_pnl() -> None:
    rows = [
        _row(2018, SituationState.STRUCTURALLY_VALID_CANDIDATE.value, CAPABLE),
        _row(2019, SituationState.STRUCTURALLY_VALID_CANDIDATE.value, CAPABLE),
        _row(2020, SituationState.STRUCTURALLY_VALID_CANDIDATE.value, INVALIDATED),
        _row(
            2020,
            SituationState.STRUCTURALLY_VALID_CANDIDATE.value,
            "OTHER_DIAGNOSTIC",
        ),
    ]
    result = _capacity_profile(rows)
    assert result["trades"] == 4
    assert result["binary_labeled"] == 3
    assert result["dol_capable"] == 2
    assert result["invalidated_before_any_active_dol"] == 1
    assert result["excluded_other_diagnostic"] == 1
    assert result["dol_capable_rate"] == "0.6666666666666666666666666667"


def test_state_profiles_are_fail_closed() -> None:
    rows = [
        _row(2025, SituationState.KNOWN_INVALID.value, INVALIDATED),
        _row(2025, SituationState.CONFLICTED.value, CAPABLE),
        _row(2025, SituationState.UNKNOWN.value, INVALIDATED),
    ]
    result = _state_profiles(rows)
    assert result[SituationState.KNOWN_INVALID.value]["trades"] == 1
    assert result[SituationState.STRUCTURALLY_VALID_CANDIDATE.value]["trades"] == 0
    assert result[SituationState.CONFLICTED.value]["trades"] == 1
    assert result[SituationState.UNKNOWN.value]["trades"] == 1


def test_period_profiles_do_not_turn_year_into_engine_input() -> None:
    rows = [
        _row(2019, SituationState.CONFLICTED.value, CAPABLE),
        _row(2022, SituationState.CONFLICTED.value, INVALIDATED),
        _row(2025, SituationState.CONFLICTED.value, CAPABLE),
    ]
    result = _period_profiles(rows)
    assert result["early_2016_2020"][SituationState.CONFLICTED.value]["trades"] == 1
    assert (
        result["transition_2021_2023"][SituationState.CONFLICTED.value]["trades"]
        == 1
    )
    assert result["recent_2024_2026"][SituationState.CONFLICTED.value]["trades"] == 1
