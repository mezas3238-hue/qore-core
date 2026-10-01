import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_phase22_parity_lane_evidence import (
    CiboPhase22ParityLaneEvidence,
)


def _lane(
    *,
    trader_id: str,
    markets: tuple[str, ...],
    population: int,
) -> CiboPhase22ParityLaneEvidence:
    return CiboPhase22ParityLaneEvidence(
        trader_id=trader_id,
        frozen_source_git_sha="1" * 40,
        methodology_sha256="sha256:" + "2" * 64,
        replay_engine_sha256="sha256:" + "3" * 64,
        parameter_sha256="sha256:" + "4" * 64,
        authorized_markets=markets,
        processed_markets=markets,
        historical_artifact_refs=("github-actions-artifact://1",),
        expected_population=population,
        observed_population=population,
        exact_historical_match=True,
    )


def test_vt31_lane_can_bind_exact_806_population() -> None:
    lane = _lane(
        trader_id="VT31_NAS100",
        markets=("NAS100",),
        population=806,
    )
    assert lane.payload()["expected_population"] == 806
    assert lane.fingerprint().startswith("sha256:")


def test_vt08_lane_can_bind_exact_seven_market_surface() -> None:
    markets = (
        "AUDJPY",
        "AUDUSD",
        "EURUSD",
        "GBPJPY",
        "GBPUSD",
        "USDCAD",
        "USDJPY",
    )
    lane = _lane(
        trader_id="VT08_FOREX",
        markets=markets,
        population=124,
    )
    assert lane.processed_markets == markets


def test_lane_rejects_reduced_market_surface() -> None:
    with pytest.raises(CiboCapitalManagementError, match="exact authorized"):
        CiboPhase22ParityLaneEvidence(
            trader_id="VT08_FOREX",
            frozen_source_git_sha="1" * 40,
            methodology_sha256="sha256:" + "2" * 64,
            replay_engine_sha256="sha256:" + "3" * 64,
            parameter_sha256="sha256:" + "4" * 64,
            authorized_markets=("AUDJPY", "AUDUSD"),
            processed_markets=("AUDJPY",),
            historical_artifact_refs=("artifact://1",),
            expected_population=124,
            observed_population=124,
            exact_historical_match=True,
        )
