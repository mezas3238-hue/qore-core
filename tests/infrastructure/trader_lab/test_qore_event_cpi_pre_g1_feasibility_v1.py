"""Pure source/mathematical tests for CPI feasibility. NO price data loaded."""
from __future__ import annotations

import math
from pathlib import Path

import pytest

from qore.infrastructure.trader_lab import qore_event_cpi_pre_g1_feasibility_v1 as v


def test_frozen_pit_sample_is_24_dates_and_unique_across_decade() -> None:
    assert len(v.FROZEN_24) == len(set(v.FROZEN_24)) == 24
    assert v.FROZEN_24[0] == "2016-10-18"
    assert v.FROZEN_24[-1] == "2026-09-11"
    assert "2025-10-24" in v.FROZEN_24
    assert "2025-11-01" not in v.FROZEN_24


def test_normal_cdf_and_predeclared_power_constant() -> None:
    assert math.isclose(v.normal_cdf(0), 0.5, abs_tol=1e-12)
    assert math.isclose(v.normal_cdf(-1), 1 - v.normal_cdf(1), abs_tol=1e-12)
    assert math.isclose(v.Z_TWO_SIDED, 1.959963984540054)
    assert v.POWER_GOAL == 0.80
    assert v.ALPHA == 0.05


@pytest.mark.parametrize(
    ("n", "sigma", "expected"),
    [
        (113, 20, 5.271),
        (113, 40, 10.542),
        (56, 20, 7.488),
        (56, 40, 14.975),
        (560, 20, 2.368),
        (560, 40, 4.736),
    ],
)
def test_mde_matches_only_hypothetical_independent_event_scenarios(
    n: int, sigma: float, expected: float,
) -> None:
    assert v.mde_bps(n=n, sigma_bps=sigma) == pytest.approx(
        expected, abs=0.001
    )


def test_power_sensitive_to_noise_and_events() -> None:
    low_noise = v.hypothetical_power(n=113, effect_bps=5, sigma_bps=20)
    high_noise = v.hypothetical_power(n=113, effect_bps=5, sigma_bps=40)
    assert low_noise == pytest.approx(0.757, abs=0.003)
    assert high_noise == pytest.approx(0.264, abs=0.003)
    assert 0 < high_noise < low_noise < 0.80
    assert v.hypothetical_power(n=113, effect_bps=15, sigma_bps=40) > 0.97


@pytest.mark.parametrize("n, sigma", [(0, 20), (-5, 20), (113, 0), (113, -1)])
def test_unsupported_power_inputs_fail_closed(n: int, sigma: float) -> None:
    with pytest.raises(ValueError):
        v.mde_bps(n=n, sigma_bps=sigma)
    with pytest.raises(ValueError):
        v.hypothetical_power(n=n, effect_bps=5, sigma_bps=sigma)


def test_locked_witness_artifact_identifiers() -> None:
    assert v.G0_RUN == 38189483643
    assert v.G0_BLS_ARTIFACT == 11720651765
    assert v.G0_CIBO_PRESENCE_ARTIFACT == 11720822239
    assert v.G0B_RUN == 38191275999
    assert v.G0B_ARCHIVE_ARTIFACT == 11721212991
    assert len(v.EXPECTED_BLS_HASH) == 64
    assert len(v.EXPECTED_CIBO_HASH) == 64
    assert len(v.EXPECTED_G0B_HASH) == 64


def test_source_only_code_does_not_consume_OHLC_or_consensus() -> None:
    code = Path(v.__file__).read_text()
    for forbidden in (
        '["open_relative"]', '["high_relative"]', '["low_relative"]',
        '["close_relative"]', '["Actual"]', '["Forecast"]',
        "ctrader_open_api", "ProtoOA", "download_broker_ticks",
        "profit_factor", "win_rate", "portfolio_backtest",
    ):
        assert forbidden not in code


def test_metadata_119_cohort_fail_closed_using_mocked_immutable_inputs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_source(root: Path, file: str, expected: str) -> list[dict]:
        return []  # deliberately invalid; sample dates must never be fabricated
    monkeypatch.setattr(v, "load_verified", fake_source)
    with pytest.raises(ValueError, match="119-row"):
        v.audit(Path("."), Path("."), Path("."))
