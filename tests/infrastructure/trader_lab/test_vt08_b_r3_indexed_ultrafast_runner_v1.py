"""VT08 Trader Lab accelerated native chronology: exact B-reference parity."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from test_vt08_b_r3_frozen_source_independent_v1 import _case

from qore.infrastructure.trader_lab.vt08_b_r3_frozen_source_independent_v1 import (
    verify_a_r3_raw_bundle,
)
from qore.infrastructure.trader_lab.vt08_b_r3_indexed_ultrafast_runner_v1 import (
    compare_indexed_against_reference,
    run_indexed_native_geometry,
)


def test_fast_runner_matches_slow_independent_on_raw_bars(
    tmp_path: Path,
) -> None:
    package, m3, m15, _ = _case(tmp_path)
    reference = verify_a_r3_raw_bundle(package, m3, m15)
    indexed = run_indexed_native_geometry(
        market="EURJPY", m3_file=m3, m15_file=m15
    )
    attested = compare_indexed_against_reference(indexed, reference)
    assert attested["c2_windows_total"] == 1
    assert attested["passes_c2_bullish_geometry"] == 1
    assert attested["reference_B_R3_differential_passed"] is True
    assert attested["author_semantics_certified"] is False
    assert attested["economic_gates_evaluated"] is False
    assert attested["orders_authorized"] is False
    assert len(str(attested["geometry_counts_sha256"])) == 64


@pytest.mark.parametrize(
    ("field", "changed"),
    [
        ("c2_windows_total", 11),
        ("missing_raw_windows", 1),
        ("m3_m15_m30_mismatches", 1),
        ("rejected_bullish_c2_geometry", 1),
        ("passes_c2_bullish_geometry", 0),
    ],
)
def test_fast_vs_slow_detects_even_one_drift(
    tmp_path: Path, field: str, changed: int
) -> None:
    package, m3, m15, _ = _case(tmp_path)
    slow = verify_a_r3_raw_bundle(package, m3, m15)
    indexed = run_indexed_native_geometry(
        market="EURJPY", m3_file=m3, m15_file=m15
    )
    indexed[field] = changed
    with pytest.raises(ValueError, match="reference drift"):
        compare_indexed_against_reference(indexed, slow)


def test_fast_runner_rejects_foreign_market_data(tmp_path: Path) -> None:
    _, m3, m15, _ = _case(tmp_path)
    with pytest.raises(ValueError, match="identity"):
        run_indexed_native_geometry(
            market="CADJPY", m3_file=m3, m15_file=m15
        )


def test_fast_runner_reports_cross_feed_disagreement_not_a_trade(
    tmp_path: Path,
) -> None:
    _, m3, m15, _ = _case(tmp_path)
    data = json.loads(m15.read_text())
    data["periods"]["M15"][-1]["high"] = "110"
    m15.write_text(json.dumps(data))
    fast = run_indexed_native_geometry(
        market="EURJPY", m3_file=m3, m15_file=m15
    )
    assert fast["m3_m15_m30_mismatches"] == 1
    assert fast["passes_c2_bullish_geometry"] == 0
    assert fast["orders_authorized"] is False


def test_fast_runner_counts_missing_bar_as_missing_not_positive(
    tmp_path: Path,
) -> None:
    _, m3, m15, _ = _case(tmp_path)
    data = json.loads(m3.read_text())
    data["bars"].pop(13)
    m3.write_text(json.dumps(data))
    fast = run_indexed_native_geometry(
        market="EURJPY", m3_file=m3, m15_file=m15
    )
    assert fast["missing_raw_windows"] == 1
    assert fast["passes_c2_bullish_geometry"] == 0
