from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    vt08_index_r70_source_complete_funnel_transport as r70,
)


def test_r70_window_contract_preserves_canonical_samples() -> None:
    assert r70._window_contract("5Y")[2] == 2448
    assert r70._window_contract("2Y")[2] == 1017
    assert r70._window_contract("R66")[2] == 773


def test_r70_funnel_payload_exposes_only_causal_generation_stages() -> None:
    funnel = r70.Funnel()
    funnel.bump("anchor_slots", 10)
    funnel.bump("poi_instances", 8)
    funnel.bump("touch_attempts", 5)
    funnel.add_identity(("NAS100", "t", "long", "1", "0"))
    payload = funnel.payload()
    assert payload["unique_signals"] == 1
    assert Decimal(payload["signals_per_anchor_slot"]) == Decimal("0.1")
    assert Decimal(payload["signals_per_poi_instance"]) == Decimal("0.125")
    assert Decimal(payload["signals_per_touch_attempt"]) == Decimal("0.2")


def test_r70_ratio_is_null_only_when_baseline_is_zero() -> None:
    assert r70._ratio(5, 10) == "0.5"
    assert r70._ratio(0, 10) == "0"
    assert r70._ratio(5, 0) is None


def test_r70_stage_contract_keeps_density_pipeline_explicit() -> None:
    required = {
        "anchor_slots",
        "bias_ready_slots",
        "poi_instances",
        "poi_touched_instances",
        "touch_attempts",
        "cisd_confirmed_attempts",
        "continuation_attempts",
        "same_c2_body_pass_attempts",
        "signal_attempts",
        "unique_signals",
    }
    assert required.issubset(set(r70.STAGE_KEYS))
