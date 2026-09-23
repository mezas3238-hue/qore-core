from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_v3_m5_directional_state_v1 import (
    CapitalizerM5DirectionalState,
    IDENTITY,
    classify_m5_directional_state,
)


def test_directional_state_identity_is_frozen() -> None:
    assert IDENTITY == "QORE_CAPITALIZER_V3_M5_DIRECTIONAL_STATE_V1"


def test_long_directional_mapping() -> None:
    assert classify_m5_directional_state(
        side=CapitalizerSide.LONG,
        microstructure_signature="LOW_BREAK_ATTEMPT+LOW_RAID_REJECTION",
    ) is CapitalizerM5DirectionalState.ALIGNED
    assert classify_m5_directional_state(
        side=CapitalizerSide.LONG,
        microstructure_signature="HIGH_ACCEPTANCE+HIGH_BREAK_ATTEMPT",
    ) is CapitalizerM5DirectionalState.ALIGNED
    assert classify_m5_directional_state(
        side=CapitalizerSide.LONG,
        microstructure_signature="LOW_ACCEPTANCE+LOW_BREAK_ATTEMPT",
    ) is CapitalizerM5DirectionalState.OPPOSED
    assert classify_m5_directional_state(
        side=CapitalizerSide.LONG,
        microstructure_signature="HIGH_BREAK_ATTEMPT+HIGH_RAID_REJECTION",
    ) is CapitalizerM5DirectionalState.OPPOSED


def test_short_directional_mapping() -> None:
    assert classify_m5_directional_state(
        side=CapitalizerSide.SHORT,
        microstructure_signature="HIGH_BREAK_ATTEMPT+HIGH_RAID_REJECTION",
    ) is CapitalizerM5DirectionalState.ALIGNED
    assert classify_m5_directional_state(
        side=CapitalizerSide.SHORT,
        microstructure_signature="LOW_ACCEPTANCE+LOW_BREAK_ATTEMPT",
    ) is CapitalizerM5DirectionalState.ALIGNED
    assert classify_m5_directional_state(
        side=CapitalizerSide.SHORT,
        microstructure_signature="HIGH_ACCEPTANCE+HIGH_BREAK_ATTEMPT",
    ) is CapitalizerM5DirectionalState.OPPOSED
    assert classify_m5_directional_state(
        side=CapitalizerSide.SHORT,
        microstructure_signature="LOW_BREAK_ATTEMPT+LOW_RAID_REJECTION",
    ) is CapitalizerM5DirectionalState.OPPOSED


def test_mixed_or_undecided_is_neutral() -> None:
    mixed = (
        "HIGH_ACCEPTANCE+HIGH_BREAK_ATTEMPT+"
        "LOW_BREAK_ATTEMPT+LOW_RAID_REJECTION+OUTSIDE_BAR"
    )
    assert classify_m5_directional_state(
        side=CapitalizerSide.LONG,
        microstructure_signature=mixed,
    ) is CapitalizerM5DirectionalState.NEUTRAL
    assert classify_m5_directional_state(
        side=CapitalizerSide.SHORT,
        microstructure_signature=mixed,
    ) is CapitalizerM5DirectionalState.NEUTRAL
    assert classify_m5_directional_state(
        side=CapitalizerSide.LONG,
        microstructure_signature="INSIDE_BAR",
    ) is CapitalizerM5DirectionalState.NEUTRAL
    assert classify_m5_directional_state(
        side=CapitalizerSide.SHORT,
        microstructure_signature="NONE",
    ) is CapitalizerM5DirectionalState.NEUTRAL
