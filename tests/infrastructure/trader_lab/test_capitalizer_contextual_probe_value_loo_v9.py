from __future__ import annotations

from qore.infrastructure.trader_lab import capitalizer_contextual_probe_value_loo_v9 as lab


def _example(window: str, value: str) -> lab.ProbeExample:
    return lab.ProbeExample(
        window=window,
        symbol="NAS100",
        session="NEW_YORK",
        entry_at="2026-01-01T10:00:00+00:00",
        selected_mode="STAGED_050_100_150",
        destination_state="LT_1R",
        volatility_state="NORMAL",
        h1_body_alignment="ALIGNED",
        m15_slope_alignment="ALIGNED",
        regime_signature="M15=ALIGNED|H1=ALIGNED|VOL=NORMAL",
        hazard_score=9,
        adverse_votes=1,
        normalized_realized_r=value,
    )


def test_hazard_and_adverse_buckets_are_fixed() -> None:
    assert lab._hazard_bucket(6) == "LE_6"
    assert lab._hazard_bucket(8) == "7_8"
    assert lab._hazard_bucket(10) == "9_10"
    assert lab._hazard_bucket(11) == "GE_11"
    assert lab._adverse_bucket(0) == "0"
    assert lab._adverse_bucket(3) == "3_PLUS"


def test_model_requires_support_in_both_training_windows() -> None:
    a = "A"
    b = "B"
    rows = tuple(_example(a, "1") for _ in range(6))
    model = lab._freeze_model(
        policy="LOO_BALANCED_035",
        training_examples=rows,
        training_windows=(a, b),
    )
    assert model["cell_count"] == 0


def test_balanced_model_accepts_temporally_positive_cell() -> None:
    a = "A"
    b = "B"
    rows = (
        *tuple(_example(a, "1") for _ in range(4)),
        *tuple(_example(b, "1") for _ in range(4)),
    )
    model = lab._freeze_model(
        policy="LOO_BALANCED_035",
        training_examples=tuple(rows),
        training_windows=(a, b),
    )
    assert int(model["cell_count"]) > 0
    assert b in model["training_windows"]


def test_strong_dynamic_can_release_to_point_five_five() -> None:
    a = "A"
    b = "B"
    rows = (
        *tuple(_example(a, "1") for _ in range(6)),
        *tuple(_example(b, "1") for _ in range(6)),
    )
    model = lab._freeze_model(
        policy="LOO_STRONG_DYNAMIC",
        training_examples=tuple(rows),
        training_windows=(a, b),
    )
    releases = {
        str(cell["release_to"])
        for cell in model["cells"].values()
    }
    assert "0.55" in releases


def test_levels_are_preentry_context_only() -> None:
    row = _example("A", "2")
    levels = lab._levels_from_example(row)
    flattened = repr(levels)
    assert "normalized_realized_r" not in flattened
    assert "NAS100" in flattened
