from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from qore.infrastructure.trader_lab import (
    capitalizer_preentry_full_stop_causal_separability_v37 as v37,
)
from qore.infrastructure.trader_lab import (
    capitalizer_preentry_native_m1_geometry_collector_v38 as collector,
)
from qore.infrastructure.trader_lab import (
    capitalizer_preentry_native_m1_geometry_separability_v38 as v38,
)
from qore.infrastructure.trader_lab import (
    capitalizer_preentry_native_m1_geometry_v38 as geometry,
)


def _state() -> v37.LabeledEntryState:
    return v37.LabeledEntryState(
        period="DEVELOPMENT_2024_2026",
        symbol="EURUSD",
        session="LONDON",
        operating_date="2026-01-05",
        entry_at="2026-01-05T10:05:00+00:00",
        label="STOP",
        original_realized_r="-1",
        vector=tuple(float(index) for index in range(45)),
    )


def _geometry() -> collector.SelectedGeometry:
    nested = geometry.PreentryNativeM1Geometry(
        symbol="EURUSD",
        side="LONG",
        entry_at="2026-01-05T10:05:00+00:00",
        m5_closeback_at="2026-01-05T09:58:00+00:00",
        m3_mss_confirmed_at="2026-01-05T10:03:00+00:00",
        m1_fvg_confirmed_at="2026-01-05T10:02:00+00:00",
        m1_ob_opened_at="2026-01-05T09:59:00+00:00",
        risk_price="0.6",
        feature_names=geometry.FEATURE_NAMES,
        vector=tuple(str(index / 10) for index in range(12)),
        feature_count=12,
        feature_timestamp_max="2026-01-05T10:03:00+00:00",
    )
    return collector.SelectedGeometry(
        symbol="EURUSD",
        session="LONDON",
        operating_date="2026-01-05",
        side="LONG",
        h1_open="2026-01-05T10:00:00+00:00",
        entry_at="2026-01-05T10:05:00+00:00",
        provenance="CAUSAL_ARBITRATION_BASE",
        geometry=nested,
    )


def test_load_period_geometry_rehydrates_json_list_fields(
    tmp_path: Path,
) -> None:
    selected = _geometry()
    path = tmp_path / "capitalizer-v38-development-selected-geometry.jsonl"
    path.write_text(json.dumps(asdict(selected)) + "\n", encoding="utf-8")

    loaded = v38._load_period_geometry(tmp_path, slug="development")

    assert loaded == {(selected.symbol, selected.entry_at): selected}


def test_extend_states_adds_exact_12d_geometry() -> None:
    state = _state()
    selected = _geometry()

    result = v38._extend_states(
        (state,),
        {(selected.symbol, selected.entry_at): selected},
    )

    assert len(result) == 1
    assert len(result[0].vector) == 57
    assert result[0].vector[:45] == state.vector
    assert result[0].vector[45:] == tuple(
        float(value) for value in selected.geometry.vector
    )
    assert result[0].label == "STOP"


def test_extend_states_fails_when_geometry_missing() -> None:
    try:
        v38._extend_states((_state(),), {})
    except ValueError as exc:
        assert "missing causal geometry" in str(exc)
    else:
        raise AssertionError("expected missing geometry failure")


def test_frozen_dimensions_are_v11_plus_native_m1() -> None:
    assert v38.V11_DIMENSION == 45
    assert v38.M1_GEOMETRY_DIMENSION == 12
    assert v38.FEATURE_DIMENSION == 57
