from decimal import Decimal

import pytest

from qore.infrastructure.cibo_capital_efficiency_reconstruction import (
    SIZING_PATH_CONTRACTS,
    ReconstructionStatus,
    SizingAuthority,
    SizingReconstructionError,
    reconstruct_sizing_decision,
    reconstruct_sizing_ledger,
)


def _event(trader: str = "R38_EURUSD") -> dict[str, object]:
    contract = SIZING_PATH_CONTRACTS[trader]
    return {
        "event": "CTRADER_DEMO_FREE_SUBMIT",
        "trader": trader,
        "symbol": contract.symbol if contract.symbol != "MULTI" else "GBPUSD",
        "sizing_path": contract.sizing_path,
        "requested_volume": "0.19",
        "assigned_capital": "10000",
        "requested_stop_risk": "19",
        "strategy_requested_risk_usd": "20",
        "stop_loss_per_volume": "100",
        "requested_margin": "38",
        "margin_per_volume": "200",
        "volume_step": "0.01",
        "minimum_volume": "0.01",
        "minimum_volume_uplifted": False,
    }


def test_complete_row_reconstructs_unused_risk_and_margin_fraction() -> None:
    row = reconstruct_sizing_decision(_event())

    assert row.status is ReconstructionStatus.COMPLETE
    assert row.sizing_path_observed is True
    assert row.sizing_authority is SizingAuthority.LEGACY_TRADER_SIZING
    assert row.risk_budget_utilization == Decimal("0.95")
    assert row.unused_strategy_risk_usd == Decimal("1")
    assert row.margin_fraction_of_assigned_capital == Decimal("0.0038")
    assert row.missing_fields == ()


def test_historical_pre_enrichment_row_is_explicitly_partial() -> None:
    event = _event("R34_XAUUSD")
    for key in (
        "sizing_path",
        "strategy_requested_risk_usd",
        "stop_loss_per_volume",
        "requested_margin",
        "margin_per_volume",
        "volume_step",
        "minimum_volume",
        "minimum_volume_uplifted",
    ):
        event.pop(key)

    row = reconstruct_sizing_decision(event)

    assert row.status is ReconstructionStatus.PARTIAL
    assert row.sizing_path_observed is False
    assert row.sizing_authority is SizingAuthority.LEGACY_TRADER_SIZING
    assert "sizing_path" in row.missing_fields
    assert "strategy_requested_risk_usd" in row.missing_fields
    assert "requested_margin" in row.missing_fields
    assert row.risk_budget_utilization is None
    assert row.unused_strategy_risk_usd is None


def test_sizing_path_must_match_frozen_source_contract() -> None:
    event = _event()
    event["sizing_path"] = "FAKE_CIBO_PATH"

    with pytest.raises(SizingReconstructionError, match="sizing_path"):
        reconstruct_sizing_decision(event)


def test_all_seven_trader_paths_are_frozen() -> None:
    assert set(SIZING_PATH_CONTRACTS) == {
        "VT08_FOREX",
        "R34_XAUUSD",
        "R38_EURUSD",
        "R43_GBPUSD",
        "R38_GBPJPY",
        "R42_AUDJPY",
        "VT31_NAS100",
    }


def test_ledger_ignores_non_submit_events_without_reordering() -> None:
    first = _event("R34_XAUUSD")
    second = _event("VT31_NAS100")

    ledger = reconstruct_sizing_ledger(
        (
            {"event": "CTRADER_DEMO_MARKET_TICK"},
            first,
            {"event": "CTRADER_DEMO_POSITION_PATH_SAMPLE"},
            second,
        )
    )

    assert [row.trader for row in ledger] == ["R34_XAUUSD", "VT31_NAS100"]


def test_zero_requested_stop_risk_is_invalid_evidence() -> None:
    event = _event()
    event["requested_stop_risk"] = "0"

    with pytest.raises(SizingReconstructionError, match="requested_stop_risk"):
        reconstruct_sizing_decision(event)



def test_cma_submit_is_complete_without_strategy_risk_budget() -> None:
    event = _event("R38_EURUSD")
    contract = SIZING_PATH_CONTRACTS["R38_EURUSD"]
    event["sizing_path"] = contract.cma_sizing_path
    event["strategy_requested_risk_usd"] = None
    event["requested_volume"] = "0.01"
    event["requested_stop_risk"] = "1"
    event["requested_margin"] = "2"

    row = reconstruct_sizing_decision(event)

    assert row.status is ReconstructionStatus.COMPLETE
    assert row.sizing_authority is SizingAuthority.CIBO_CMA
    assert row.strategy_requested_risk_usd is None
    assert row.risk_budget_utilization is None
    assert row.unused_strategy_risk_usd is None
    assert row.missing_fields == ()


def test_cma_path_is_frozen_for_all_seven_traders() -> None:
    assert {
        contract.cma_sizing_path
        for contract in SIZING_PATH_CONTRACTS.values()
    } == {"CIBO_CMA_MINIMAL_SEED"}
