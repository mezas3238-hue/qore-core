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
        "build_initial_seed_request(",
        "demo_capital_for(",
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
        "build_ctrader_demo_cibo_sizing(",
    )
    for call in required:
        assert call in source


def test_vt31_adapter_uses_account_cibo_sizing_not_certified_risk_for_volume() -> None:
    source = VT31_ADAPTER.read_text(encoding="utf-8")

    assert "build_risk_request(" not in source
    assert "build_vt31_opportunity(" in source
    assert "build_initial_seed_request(" not in source
    assert "demo_capital_for(" not in source
    assert "build_ctrader_demo_cibo_sizing(" in source
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



def test_demo_runtime_exposes_no_active_trader_risk_fraction_or_private_capital_slice() -> None:
    source = RUNTIME.read_text(encoding="utf-8")
    for key in (
        '"r38_base_risk_fraction"',
        '"r43_base_risk_fraction"',
        '"gbpjpy_r38_base_risk_fraction"',
        '"audjpy_r42_base_risk_fraction"',
    ):
        assert key not in source
    assert "demo_capital_for(" not in source
    assert '"trader_runtime_sizing_authority": False' in source
    assert '"cibo_runtime_sizing_authority": True' in source
    assert '"cibo_sizing_scope": "ACCOUNT"' in source


def test_phase20_runtime_never_assumes_zero_pending_broker_risk() -> None:
    source = RUNTIME.read_text(encoding="utf-8")

    assert 'pending_broker_worst_case_loss_usd=Decimal("0")' not in source
    assert source.count("demo_sink.registry.pending_stop_risk(") == 2


def test_phase20_single_slot_wires_vt08_and_vt31_without_collapsing_oco() -> None:
    source = RUNTIME.read_text(encoding="utf-8")
    adapter = VT31_ADAPTER.read_text(encoding="utf-8")

    assert "phase20_after_submit=observe_vt08_phase20_candidate" in source
    assert "phase20_after_submit=observe_vt31_phase20_candidate" in source
    assert "phase20_after_submit=observe_vt31_phase20_oco_trigger" in source
    assert "VIRTUAL_OCO_ARMED_AS_KNOWN_OPTIONS" in source
    assert "PHASE20D_VT31_OCO_ARM_INELIGIBLE" in source
    assert '"execution_path_blocked": False' in source
    assert "build_ctrader_demo_single_slot_known_option(" in source
    assert "PHASE20D_VT31_OCO_INELIGIBLE" not in source
    assert "BASKET_AWARE_FORWARD_ADAPTER_REQUIRED" not in source
    assert "phase20_after_submit: Phase20AfterSubmit | None = None" in adapter
    assert "build_virtual_order_opportunity(" in adapter
    assert "_observe_phase20_without_execution_authority(" in adapter
    assert "PHASE20D_VT31_OBSERVER_INELIGIBLE" in adapter
    assert '"execution_path_blocked": False' in adapter
    assert "phase20_after_submit(" in adapter
