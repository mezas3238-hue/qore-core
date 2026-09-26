"""CIBO CMA runtime authority-switch invariants."""
# ruff: noqa: I001

from __future__ import annotations

from pathlib import Path


RUNTIME = Path("scripts/qore_ctrader_demo_free_runtime.py")
VT31_ADAPTER = Path("scripts/vt31_nas100_ctrader_demo_adapter.py")


def test_demo_runtime_no_longer_calls_legacy_trader_sizing_builders() -> None:
    source = RUNTIME.read_text(encoding="utf-8")

    forbidden = (
        "build_ctrader_demo_vt08_cibo_request(",
        "build_r34_risk_request(",
        "build_r38_risk_request(",
        "build_r43_risk_request(",
        "build_r38_gbpjpy_risk_request(",
        "build_r42_audjpy_risk_request(",
    )
    for call in forbidden:
        assert call not in source

    required = (
        "build_ctrader_demo_vt08_opportunity(",
        "build_r34_opportunity(",
        "build_r38_opportunity(",
        "build_r43_opportunity(",
        "build_r38_gbpjpy_opportunity(",
        "build_r42_audjpy_opportunity(",
        "build_initial_seed_request(",
    )
    for call in required:
        assert call in source


def test_vt31_adapter_uses_cibo_seed_not_certified_risk_for_volume() -> None:
    source = VT31_ADAPTER.read_text(encoding="utf-8")

    assert "build_risk_request(" not in source
    assert "build_vt31_opportunity(" in source
    assert "build_initial_seed_request(" in source
    assert "legacy_resolution = resolve_certified_risk(context)" in source
    assert "certified_risk_r=legacy_resolution.final_risk_r" not in source


def test_runtime_records_cibo_seed_risk_as_position_base_risk() -> None:
    source = RUNTIME.read_text(encoding="utf-8")

    assert source.count("base_risk_usd = seed.plan.stop_risk_usd") == 5


def test_runtime_wires_passive_cma_position_observer_without_expansion() -> None:
    source = RUNTIME.read_text(encoding="utf-8")

    assert "observe_runtime_position(" in source
    assert "CmaRuntimePositionSnapshot(" in source
    assert "entries_by_position(position_id)" in source
    assert "registry_leg_count=len(registry_entries)" in source
    assert "cma_result.observation.as_payload()" in source
    assert "plan_self_financing_expansion(" not in source


def test_runtime_cma_observation_has_no_broker_mutation_path() -> None:
    observer = Path(
        "src/qore/infrastructure/cibo_cma_runtime_observer.py"
    ).read_text(encoding="utf-8")

    forbidden = (
        "order_send(",
        "submit_demo_request(",
        "submit_authorized(",
        "plan_self_financing_expansion(",
    )
    for call in forbidden:
        assert call not in observer

    assert '"mutation_authority": "NONE_OBSERVATIONAL"' in observer
    assert "NETTED_MULTI_LEG_POSITION_REQUIRES_ALLOCATION_DECOMPOSITION" in observer
