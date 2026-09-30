from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CapitalSource,
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_capital_source_ledger import CapitalSourceLedger
from qore.infrastructure.cibo_protected_base_overlay import (
    ProtectedBaseClass,
    build_protected_base_snapshot,
)
from qore.infrastructure.market_test_environment import (
    MarketRuntimeEnvironment,
)

T0 = datetime(2026, 9, 30, 1, 45, tzinfo=UTC)


def _identity() -> CiboAccountCapitalIdentity:
    return CiboAccountCapitalIdentity(
        provider_key="ctrader",
        account_ref="protected-base-test",
        environment=MarketRuntimeEnvironment.TEST,
    )


def _ledger() -> CapitalSourceLedger:
    return (
        CapitalSourceLedger()
        .add_source(
            source_id="gen0",
            source=CapitalSource.ORIGINAL_BASE_CAPITAL,
            proven_amount_usd=Decimal("100"),
        )
        .reserve(
            reservation_id="existing-reservation",
            source_id="gen0",
            amount_usd=Decimal("20"),
        )
    )


def test_protected_base_overlay_preserves_frozen_source_ledger() -> None:
    ledger = _ledger()
    snapshot = build_protected_base_snapshot(
        account_identity=_identity(),
        ledger=ledger,
        captured_at=T0,
        source_id="gen0",
        protected_base_usd=Decimal("60"),
        protection_class=ProtectedBaseClass.ECONOMICALLY_RESERVED,
        evidence_sha256="sha256:" + "a" * 64,
    )

    assert snapshot.original_base_proven_usd == Decimal("100")
    assert snapshot.original_base_available_usd == Decimal("80")
    assert snapshot.protected_base_usd == Decimal("60")
    assert snapshot.unprotected_available_base_usd == Decimal("20")
    assert snapshot.source_ledger_mutated is False
    assert ledger.accounts[0].available_usd == Decimal("80")
    assert snapshot.runtime_authority is False
    assert snapshot.fingerprint().startswith("sha256:")


def test_protected_base_cannot_use_profit_source() -> None:
    ledger = CapitalSourceLedger().add_source(
        source_id="profit",
        source=CapitalSource.REALIZED_PROFIT,
        proven_amount_usd=Decimal("25"),
    )
    with pytest.raises(
        CiboCapitalManagementError,
        match="ORIGINAL_BASE_CAPITAL",
    ):
        build_protected_base_snapshot(
            account_identity=_identity(),
            ledger=ledger,
            captured_at=T0,
            source_id="profit",
            protected_base_usd=Decimal("10"),
            protection_class=ProtectedBaseClass.ACCOUNTING_PROTECTED,
            evidence_sha256="sha256:" + "b" * 64,
        )


def test_protected_base_cannot_exceed_available_gen0() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="exceeds available original base",
    ):
        build_protected_base_snapshot(
            account_identity=_identity(),
            ledger=_ledger(),
            captured_at=T0,
            source_id="gen0",
            protected_base_usd=Decimal("81"),
            protection_class=ProtectedBaseClass.ACCOUNTING_PROTECTED,
            evidence_sha256="sha256:" + "c" * 64,
        )


def test_policy_protected_base_requires_policy_evidence() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="requires policy evidence",
    ):
        build_protected_base_snapshot(
            account_identity=_identity(),
            ledger=_ledger(),
            captured_at=T0,
            source_id="gen0",
            protected_base_usd=Decimal("50"),
            protection_class=ProtectedBaseClass.POLICY_PROTECTED,
            evidence_sha256="sha256:" + "d" * 64,
        )


def test_broker_guaranteed_base_requires_real_provider_evidence() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="requires policy/provider evidence",
    ):
        build_protected_base_snapshot(
            account_identity=_identity(),
            ledger=_ledger(),
            captured_at=T0,
            source_id="gen0",
            protected_base_usd=Decimal("50"),
            protection_class=ProtectedBaseClass.BROKER_GUARANTEED,
            evidence_sha256="sha256:" + "e" * 64,
            policy_id="BASE_PROTECTION_POLICY_V1",
            policy_sha256="sha256:" + "f" * 64,
            provider_guaranteed=False,
        )

    snapshot = build_protected_base_snapshot(
        account_identity=_identity(),
        ledger=_ledger(),
        captured_at=T0,
        source_id="gen0",
        protected_base_usd=Decimal("50"),
        protection_class=ProtectedBaseClass.BROKER_GUARANTEED,
        evidence_sha256="sha256:" + "1" * 64,
        policy_id="BASE_PROTECTION_POLICY_V1",
        policy_sha256="sha256:" + "2" * 64,
        broker_guarantee_evidence_sha256="sha256:" + "3" * 64,
        provider_guaranteed=True,
    )
    assert snapshot.provider_guaranteed is True
