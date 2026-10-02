from qore.infrastructure.cibo_arch2_t11_experiment_plan import (
    T11_MARKET_IMPACT_EXPERIMENT_PLAN,
)
from qore.infrastructure.cibo_arch2_t11_nonlinear_input_freeze import (
    FROZEN_AT,
    REQUIRED_SYMBOLS,
)
from qore.infrastructure.cibo_arch2_t11_v3_terminal_receipt import (
    COMPLETED,
    FALSIFIED,
    V3_CANONICAL_HEAD_SHA,
    V3_CANONICAL_RUN_ATTEMPT,
    V3_CANONICAL_RUN_ID,
    build_t11_v3_terminal_receipt,
)
from scripts.cibo_arch2_t11_market_impact_terminal import build_terminal_payload


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
        "status": (
            "MARKET_IMPACT_MODEL_READY"
            if ready
            else "MARKET_IMPACT_MODEL_FALSIFIED_OR_NOT_READY"
        ),
        "protocol_frozen_at": FROZEN_AT.isoformat(),
        "experiment_plan_sha256": T11_MARKET_IMPACT_EXPERIMENT_PLAN.fingerprint(),
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
        "git_sha": V3_CANONICAL_HEAD_SHA,
        "run_id": str(V3_CANONICAL_RUN_ID),
        "run_attempt": str(V3_CANONICAL_RUN_ATTEMPT),
        "evaluation": {
            "symbols": symbols,
            "market_impact_model_ready": ready,
        },
    }


def test_t11_v3_terminal_receipt_completes_only_on_all_six_symbols() -> None:
    receipt = build_t11_v3_terminal_receipt(_report())

    assert receipt.market_impact_model_ready is True
    assert receipt.terminal_recommendation == COMPLETED
    assert receipt.symbol_count == 6
    assert receipt.episode_count == 144
    assert receipt.child_entry_count == 216
    assert receipt.phase22_v2_consumed is False
    assert receipt.canonical_ledger_modified is False
    assert receipt.productive_authority is False


def test_t11_v3_terminal_receipt_falsifies_without_pooled_rescue() -> None:
    receipt = build_t11_v3_terminal_receipt(
        _report(failed_symbol=REQUIRED_SYMBOLS[-1])
    )

    assert receipt.market_impact_model_ready is False
    assert receipt.four_of_four_by_symbol[-1][1] is False
    assert receipt.terminal_recommendation == FALSIFIED


def test_t11_terminal_cli_materializes_v3_retry_lineage() -> None:
    payload = build_terminal_payload(_report())

    assert payload["cycle_id"] == "CIBO_ARCH2_T11_MARKET_IMPACT_EXECUTION_CYCLE_V3"
    assert payload["canonical_run_id"] == V3_CANONICAL_RUN_ID
    assert payload["canonical_run_attempt"] == V3_CANONICAL_RUN_ATTEMPT
    assert payload["canonical_head_sha"] == V3_CANONICAL_HEAD_SHA
    assert payload["precursor_failed_run_id"] > 0
    assert payload["cancelled_duplicate_run_id"] > 0
    assert payload["holdout_outcomes_used"] is False
    assert payload["phase22_v2_consumed"] is False
    assert payload["canonical_ledger_modified"] is False
    assert payload["productive_authority"] is False
