import pytest

from qore.infrastructure.cibo_ce2i_tool_registry import (
    CE2I_TOOL_REGISTRY,
    ToolMaturity,
    tool_by_code,
    validate_registry,
)


def test_registry_has_twenty_unique_capital_tools() -> None:
    validate_registry()

    assert len(CE2I_TOOL_REGISTRY) == 20
    assert len({tool.code for tool in CE2I_TOOL_REGISTRY}) == 20


def test_minimal_seed_is_contract_implemented() -> None:
    tool = tool_by_code("T01")

    assert tool.name == "Minimal Seed"
    assert tool.maturity is ToolMaturity.CONTRACT_IMPLEMENTED
    assert tool.roadmap_phase == 5


def test_capacity_reservation_is_explicit_tool() -> None:
    tool = tool_by_code("T19")

    assert "double" in tool.risk_effect.lower()
    assert tool.maturity is ToolMaturity.CONTRACT_IMPLEMENTED


def test_unknown_tool_code_fails_closed() -> None:
    with pytest.raises(KeyError):
        tool_by_code("T99")


def test_every_tool_has_evidence_and_capital_source_contract() -> None:
    for tool in CE2I_TOOL_REGISTRY:
        assert tool.required_evidence
        assert tool.eligible_capital_sources
        assert tool.rollback_condition
