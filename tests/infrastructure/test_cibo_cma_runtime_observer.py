# ruff: noqa: I001
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import CapitalStage
from qore.infrastructure.cibo_cma_lifecycle_store import DurableCmaLifecycleStore
from qore.infrastructure.cibo_cma_runtime_observer import (
    CmaRuntimePositionSnapshot,
    observe_runtime_position,
)
from qore.infrastructure.cibo_cma_settlement_store import DurableCmaSettlementStore


NOW = datetime(2026, 9, 26, 12, 0, tzinfo=UTC)


def _snapshot(**overrides: object) -> CmaRuntimePositionSnapshot:
    values: dict[str, object] = {
        "trader_id": TraderLineage.R38_EURUSD,
        "signal_fingerprint": "signal-1",
        "qore_symbol": "EURUSD",
        "position_id": 101,
        "registry_leg_count": 1,
        "side": "long",
        "entry_price": Decimal("100"),
        "current_stop": Decimal("95"),
        "initial_volume": Decimal("0.20"),
        "remaining_volume": Decimal("0.20"),
        "tick_size": Decimal("1"),
        "tick_value": Decimal("10"),
        "broker_position_reconciled": True,
        "broker_stop_reconciled": True,
        "mutation_outcome_unknown": False,
        "observed_at": NOW,
    }
    values.update(overrides)
    return CmaRuntimePositionSnapshot(**values)  # type: ignore[arg-type]


def _stores(
    tmp_path: Path,
) -> tuple[DurableCmaSettlementStore, DurableCmaLifecycleStore]:
    return (
        DurableCmaSettlementStore(tmp_path / "settlements.json"),
        DurableCmaLifecycleStore(tmp_path / "lifecycle.json"),
    )


def test_first_open_observation_registers_and_advances_lifecycle(
    tmp_path: Path,
) -> None:
    settlement, lifecycle = _stores(tmp_path)

    result = observe_runtime_position(
        _snapshot(),
        settlement_store=settlement,
        lifecycle_store=lifecycle,
    )

    assert result.observation is not None
    assert result.observation.stage is CapitalStage.PROTECT_BASE
    assert result.lifecycle_stage is CapitalStage.PROTECT_BASE
    persisted = lifecycle.load().record_for(
        signal_fingerprint="signal-1",
        position_id=101,
    )
    assert persisted is not None
    assert persisted.stage is CapitalStage.PROTECT_BASE


def test_multi_leg_netted_position_fails_closed_without_lifecycle_creation(
    tmp_path: Path,
) -> None:
    settlement, lifecycle = _stores(tmp_path)

    result = observe_runtime_position(
        _snapshot(registry_leg_count=2),
        settlement_store=settlement,
        lifecycle_store=lifecycle,
    )

    assert result.observation is None
    assert result.failure_payload is not None
    assert "NETTED_MULTI_LEG" in str(result.failure_payload["reason"])
    assert lifecycle.load().records == ()


def test_protected_floor_can_persist_capitalize_then_deescalate(
    tmp_path: Path,
) -> None:
    settlement, lifecycle = _stores(tmp_path)
    first = observe_runtime_position(
        _snapshot(current_stop=Decimal("103")),
        settlement_store=settlement,
        lifecycle_store=lifecycle,
    )
    second = observe_runtime_position(
        _snapshot(current_stop=Decimal("0")),
        settlement_store=settlement,
        lifecycle_store=lifecycle,
    )

    assert first.lifecycle_stage is CapitalStage.CAPITALIZE
    assert second.observation is not None
    assert second.observation.stage is CapitalStage.OBSERVE
    assert second.lifecycle_stage is CapitalStage.OBSERVE


def test_partial_without_realized_settlement_is_observe_fail_closed(
    tmp_path: Path,
) -> None:
    settlement, lifecycle = _stores(tmp_path)

    result = observe_runtime_position(
        _snapshot(remaining_volume=Decimal("0.10")),
        settlement_store=settlement,
        lifecycle_store=lifecycle,
    )

    assert result.observation is not None
    assert result.observation.evidence_sufficient is False
    assert result.observation.stage is CapitalStage.OBSERVE
    assert result.observation.expansion_eligible is False
