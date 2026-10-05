from qore.infrastructure.core_stack_v2.shared_lab import SharedLabLevel
from qore.infrastructure.core_stack_v2.shared_lab_gate_policy import (
    CapabilityNature,
    default_gate_policy,
)


def test_sensor_does_not_fake_cognitive_gate_pass():
    policy = default_gate_policy(CapabilityNature.SENSOR)
    decision = policy.decision_for(SharedLabLevel.L3_COGNITIVE_REALITY)
    assert decision.required is False
    assert "N/A" in decision.justification


def test_trader_facing_intelligence_requires_l8():
    policy = default_gate_policy(CapabilityNature.TRADER_FACING_INTELLIGENCE)
    assert SharedLabLevel.L8_SEVEN_TRADER_REALITY in policy.required_levels


def test_full_organism_requires_every_level():
    policy = default_gate_policy(CapabilityNature.FULL_ORGANISM)
    assert set(policy.required_levels) == set(SharedLabLevel)
