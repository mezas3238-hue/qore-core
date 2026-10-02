from copy import deepcopy

import pytest

from qore.infrastructure.cibo_arch2_t11_market_impact_terminal_receipt import (
    COMPLETED,
    FALSIFIED,
    build_t11_market_impact_terminal_receipt,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_arch2_t11_nonlinear_input_freeze import (
    REQUIRED_SYMBOLS,
)


def _report(*, failed_symbol: str | None = None) -> dict[str, object]:
    symbols = [
        {
            "qore_symbol": symbol,
            "four_of_four_validated": symbol != failed_symbol,
        }
        for symbol in REQUIRED_SYMBOLS
    ]
    ready = failed_symbol is None
    return {
        "schema": "qore.cibo.arch2.t11.market-impact-demo.v2",
        "provider_key": "ctrader-demo",
        "environment": "demo",
        "deposit_asset": "USD",
        "metric": "ADVERSE_REALIZED_ALL_IN_SETTLEMENT_COST_USD",
        "episode_count": 144,
        "child_entry_count": 216,
        "minimum_volume_child_orders_only": True,
        "two_x_children_open_before_close": True,
        "balanced_long_short_pairs": True,
        "alternating_level_order": True,
        "evaluation": {
            "symbols": symbols,
            "market_impact_model_ready": ready,
        },
        "all_created_positions_closed": True,
        "broker_mutation_performed": True,
        "holdout_outcomes_used": False,
        "phase22_v2_consumed": False,
        "fundednext_touched": False,
        "vps_touched": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "canonical_ledger_modified": False,
        "productive_authority": False,
    }


def test_t11_terminal_receipt_completes_only_on_exact_4_of_4_surface() -> None:
    receipt = build_t11_market_impact_terminal_receipt(_report())

    assert receipt.market_impact_model_ready is True
    assert receipt.terminal_recommendation == COMPLETED
    assert receipt.episode_count == 144
    assert receipt.child_entry_count == 216
    assert receipt.canonical_ledger_modified is False
    assert receipt.productive_authority is False


def test_t11_terminal_receipt_falsifies_without_pooled_rescue() -> None:
    receipt = build_t11_market_impact_terminal_receipt(
        _report(failed_symbol="NAS100")
    )

    assert receipt.market_impact_model_ready is False
    assert receipt.terminal_recommendation == FALSIFIED
    assert dict(receipt.four_of_four_by_symbol)["NAS100"] is False


def test_t11_terminal_receipt_rejects_uncontained_broker_mutation() -> None:
    report = deepcopy(_report())
    report["all_created_positions_closed"] = False

    with pytest.raises(
        CiboCapitalManagementError,
        match="governance drift",
    ):
        build_t11_market_impact_terminal_receipt(report)
