from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

import pytest

from qore.infrastructure.core_stack_v2.shared_swing_trader_support import (
    SharedSwingHorizon,
    SharedSwingTraderFamily,
    build_research_swing_support_profile,
)
from qore.infrastructure.core_stack_v2.shared_trader_intelligence import (
    SharedIntelligenceClass,
    SharedTraderIntelligenceValidationError,
)

NOW = datetime(2026, 9, 29, 21, 30, tzinfo=UTC)


def _profile():
    return build_research_swing_support_profile(
        profile_id="swing-support-001",
        trader_family=SharedSwingTraderFamily.GLOBAL_MACRO_SWING,
        version="001",
        frozen_at=NOW,
        markets=("EURUSD", "XAUUSD"),
        horizons=(
            SharedSwingHorizon.D1,
            SharedSwingHorizon.H4,
            SharedSwingHorizon.W1,
        ),
        intelligence_classes=(
            SharedIntelligenceClass.CONTINUATION,
            SharedIntelligenceClass.OPPORTUNITY,
            SharedIntelligenceClass.POSITION_THREAT,
            SharedIntelligenceClass.REGIME_TRANSITION,
            SharedIntelligenceClass.WORLD_EXPLANATION,
        ),
        source_evidence_refs=("owner-directive-007",),
    )


def test_swing_support_profile_is_interface_not_runtime_trader() -> None:
    profile = _profile()

    assert profile.runtime_trader_exists is False
    assert profile.trader_certified is False
    assert profile.setup_authority is False
    assert profile.direction_authority is False
    assert profile.entry_authority is False
    assert profile.stop_target_authority is False
    assert profile.position_management_authority is False
    assert profile.execution_authority is False
    assert profile.sizing_authority is False
    assert len(profile.fingerprint()) == 64


@pytest.mark.parametrize(
    "field_name",
    (
        "runtime_trader_exists",
        "trader_certified",
    ),
)
def test_sti12_cannot_create_or_certify_swing_trader(field_name: str) -> None:
    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="cannot create or certify",
    ):
        replace(_profile(), **{field_name: True})


@pytest.mark.parametrize(
    "field_name",
    (
        "setup_authority",
        "direction_authority",
        "entry_authority",
        "stop_target_authority",
        "position_management_authority",
        "execution_authority",
        "sizing_authority",
    ),
)
def test_shared_swing_support_cannot_take_trader_authority(
    field_name: str,
) -> None:
    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="cannot own Trader authority",
    ):
        replace(_profile(), **{field_name: True})


def test_swing_support_maps_to_read_only_routing_capability() -> None:
    profile = _profile()
    capability = profile.as_routing_capability()

    assert capability.trader_id == (
        "QORE_GLOBAL_MACRO_SWING_RESEARCH_INTERFACE"
    )
    assert capability.markets == ("EURUSD", "XAUUSD")
    assert capability.horizons == ("D1", "H4", "W1")
    assert capability.open_position_monitoring_capability is True
    assert capability.methodology_visible_to_shared is False
    assert capability.shared_methodology_mutation_authority is False


def test_swing_profile_requires_canonical_market_order() -> None:
    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="markets must be non-empty and canonical",
    ):
        replace(_profile(), markets=("XAUUSD", "EURUSD"))


def test_swing_profile_has_no_m1_m5_requirement() -> None:
    profile = _profile()
    assert SharedSwingHorizon.H1 not in profile.horizons
    assert tuple(item.value for item in profile.horizons) == ("D1", "H4", "W1")
