from __future__ import annotations

from qore.infrastructure.trader_lab import (
    turtle_soup_xauusd_specialist_cognitive_memory_v3 as v3,
)


def _rows(values: list[str]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for index, value in enumerate(values):
        rows.append(
            {
                "strategy_entry_at": f"2020-01-{index + 1:02d}T00:00:00+00:00",
                "STATIC_net_010_r": value,
            }
        )
    return rows


def test_full_lifecycle_validation_requires_positive_combined_and_majority_terciles() -> None:
    result = v3._validation(
        _rows(["1", "1", "1", "1", "1", "-1", "1", "-1", "1"]),
        posture="STATIC",
    )
    assert result["validated"] is True
    assert result["classification"] in v3.VALID_CLASSES


def test_negative_combined_is_not_validated() -> None:
    result = v3._validation(
        _rows(["-1", "-1", "-1", "1", "1", "1", "-1", "-1", "-1"]),
        posture="STATIC",
    )
    assert result["validated"] is False
    assert result["classification"] == "NOT_VALIDATED_010"


def test_validation_does_not_change_causal_definition_or_posture() -> None:
    result = v3._validation(
        _rows(["1", "1", "1", "1", "1", "1"]),
        posture="STATIC",
    )
    assert result["posture_frozen_before_economic_validation"] == "STATIC"
    assert result["situation_definition_changed"] is False
    assert result["target_definition_changed"] is False
    assert result["management_posture_changed"] is False
