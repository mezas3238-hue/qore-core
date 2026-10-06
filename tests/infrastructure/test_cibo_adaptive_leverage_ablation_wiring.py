import inspect

import qore.infrastructure.cibo_economic_engine_wiring as economic
import qore.infrastructure.cibo_native_sovereign_capital_runtime as native
import qore.infrastructure.cibo_single_account_historical_ceiling_epoch as epoch
import qore.infrastructure.cibo_single_account_historical_ceiling_replay as replay
import qore.infrastructure.cibo_single_account_sovereign_ceiling_executor as executor
import qore.infrastructure.cibo_sovereign_capital_runtime as sovereign


def _has_parameter(function, name: str) -> bool:
    return name in inspect.signature(function).parameters


def test_fixed_multiplier_ablation_is_threaded_through_sovereign_chain() -> None:
    assert _has_parameter(
        replay.run_historical_ceiling_replay,
        "portfolio_fixed_multiplier",
    )
    assert _has_parameter(
        epoch.run_predecision_historical_sovereign_ceiling_epoch,
        "portfolio_fixed_multiplier",
    )
    assert _has_parameter(
        executor.execute_sovereign_ceiling_epoch,
        "portfolio_fixed_multiplier",
    )
    assert _has_parameter(
        native.run_cibo_native_sovereign_capital_runtime,
        "portfolio_fixed_multiplier",
    )
    assert _has_parameter(
        sovereign.run_cibo_sovereign_capital_runtime,
        "portfolio_fixed_multiplier",
    )
    assert _has_parameter(
        economic.run_cibo_economic_engine_chain,
        "fixed_multiplier",
    )


def test_fixed_multiplier_reaches_canonical_portfolio_engine() -> None:
    source = inspect.getsource(economic.run_cibo_economic_engine_chain)
    assert "plan_account_wide_capital_allocation(" in source
    assert "fixed_multiplier=fixed_multiplier" in source


def test_each_runtime_layer_forwards_exact_ablation_value() -> None:
    sources = (
        inspect.getsource(replay.run_historical_ceiling_replay),
        inspect.getsource(
            epoch.run_predecision_historical_sovereign_ceiling_epoch
        ),
        inspect.getsource(executor.execute_sovereign_ceiling_epoch),
        inspect.getsource(native.run_cibo_native_sovereign_capital_runtime),
    )
    for source in sources:
        assert (
            "portfolio_fixed_multiplier=portfolio_fixed_multiplier"
            in source
        )

    sovereign_source = inspect.getsource(
        sovereign.run_cibo_sovereign_capital_runtime
    )
    assert "fixed_multiplier=portfolio_fixed_multiplier" in sovereign_source
