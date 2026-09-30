from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
)
from qore.infrastructure.cibo_integrated_capital_scope_store import (
    DurableLegacyCapitalStoreScopeStore,
)
from qore.infrastructure.cibo_integrated_capital_transaction_store import (
    IntegratedCapitalComponent,
    IntegratedCapitalComponentRef,
    IntegratedCapitalTransactionError,
)
from qore.infrastructure.market_test_environment import (
    MarketRuntimeEnvironment,
)

T0 = datetime(2026, 9, 30, 2, 40, tzinfo=UTC)


def _identity() -> CiboAccountCapitalIdentity:
    return CiboAccountCapitalIdentity(
        provider_key="ctrader",
        account_ref="legacy-scope",
        environment=MarketRuntimeEnvironment.TEST,
    )


def _refs(
    digit: str,
    generation: int = 1,
) -> tuple[IntegratedCapitalComponentRef, ...]:
    components = (
        IntegratedCapitalComponent.SOURCE_LEDGER,
        IntegratedCapitalComponent.T19_ALLOCATION,
        IntegratedCapitalComponent.CMA_SETTLEMENT,
    )
    return tuple(
        IntegratedCapitalComponentRef(
            component=component,
            generation=generation,
            sha256="sha256:" + digit * 64,
        )
        for component in components
    )


def test_legacy_scope_is_hash_chained_and_restart_safe(
    tmp_path: Path,
) -> None:
    path = tmp_path / "scope.json"
    store = DurableLegacyCapitalStoreScopeStore(
        path,
        account_identity=_identity(),
    )
    first = store.seal(
        _refs("1"),
        sealed_at=T0,
        expected_generation=0,
    )
    second = store.seal(
        _refs("2", generation=2),
        sealed_at=T0 + timedelta(seconds=1),
        expected_generation=1,
    )

    assert first.generation == 1
    assert second.generation == 2
    assert second.records[1].previous_chain_sha256 == (
        second.records[0].chain_sha256
    )
    assert (
        DurableLegacyCapitalStoreScopeStore(
            path,
            account_identity=_identity(),
        ).load()
        == second
    )


def test_legacy_scope_detects_stale_component_refs(tmp_path: Path) -> None:
    store = DurableLegacyCapitalStoreScopeStore(
        tmp_path / "scope.json",
        account_identity=_identity(),
    )
    store.seal(
        _refs("1"),
        sealed_at=T0,
        expected_generation=0,
    )

    with pytest.raises(
        IntegratedCapitalTransactionError,
        match="legacy capital store scope is stale",
    ):
        store.verify(_refs("2", generation=2))


def test_legacy_scope_rejects_cross_account_reopen(tmp_path: Path) -> None:
    path = tmp_path / "scope.json"
    store = DurableLegacyCapitalStoreScopeStore(
        path,
        account_identity=_identity(),
    )
    store.seal(
        _refs("1"),
        sealed_at=T0,
        expected_generation=0,
    )
    other = CiboAccountCapitalIdentity(
        provider_key="ctrader",
        account_ref="other-account",
        environment=MarketRuntimeEnvironment.TEST,
    )

    with pytest.raises(
        IntegratedCapitalTransactionError,
        match="account identity drift",
    ):
        DurableLegacyCapitalStoreScopeStore(
            path,
            account_identity=other,
        ).load()
