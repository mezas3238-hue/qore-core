from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
)
from qore.infrastructure.cibo_compound_capital import CiboCompoundCapitalError
from qore.infrastructure.cibo_instrument_capability_registry import (
    CapabilityStatus,
    InstrumentCapability,
    ProviderCapabilityEvidence,
    ProviderInstrumentCapabilityRegistry,
)
from qore.infrastructure.market_test_environment import MarketRuntimeEnvironment

T0 = datetime(2026, 9, 30, 0, 20, tzinfo=UTC)


def _identity() -> CiboAccountCapitalIdentity:
    return CiboAccountCapitalIdentity(
        provider_key="ctrader",
        account_ref="provider-capability-test",
        environment=MarketRuntimeEnvironment.TEST,
    )


def _evidence(
    *,
    capability: InstrumentCapability = InstrumentCapability.CFD,
    status: CapabilityStatus = CapabilityStatus.SUPPORTED,
    qore_symbol: str | None = None,
    provider_symbol: str | None = None,
    conditions: tuple[str, ...] = (),
    provider_verified: bool = True,
    expires_at: datetime | None = None,
) -> ProviderCapabilityEvidence:
    return ProviderCapabilityEvidence(
        evidence_id=f"cap-{capability.value}",
        account_identity=_identity(),
        capability=capability,
        status=status,
        observed_at=T0,
        produced_at=T0 + timedelta(seconds=1),
        source="PROVIDER_NORMALIZED_TEST_EVIDENCE",
        source_ref=f"provider-source:{capability.value}",
        evidence_sha256="sha256:" + "a" * 64,
        policy_version="CIBO_PROVIDER_CAPABILITY_REGISTRY_V1",
        qore_symbol=qore_symbol,
        provider_symbol=provider_symbol,
        conditions=conditions,
        expires_at=expires_at,
        provider_verified=provider_verified,
    )


def test_supported_capability_requires_provider_verified_evidence() -> None:
    evidence = _evidence()

    assert evidence.status is CapabilityStatus.SUPPORTED
    assert evidence.provider_verified is True
    assert evidence.productive_authority is False
    assert evidence.fingerprint().startswith("sha256:")

    with pytest.raises(
        CiboCompoundCapitalError,
        match="requires provider-verified evidence",
    ):
        replace(evidence, provider_verified=False)


def test_conditional_capability_requires_explicit_conditions() -> None:
    with pytest.raises(
        CiboCompoundCapitalError,
        match="requires explicit conditions",
    ):
        _evidence(
            capability=InstrumentCapability.OPTION,
            status=CapabilityStatus.CONDITIONALLY_SUPPORTED,
        )

    conditional = _evidence(
        capability=InstrumentCapability.OPTION,
        status=CapabilityStatus.CONDITIONALLY_SUPPORTED,
        conditions=("DEFINED_RISK_ONLY",),
    )
    assert conditional.conditions == ("DEFINED_RISK_ONLY",)


def test_unknown_is_default_and_cannot_claim_verification() -> None:
    registry = ProviderInstrumentCapabilityRegistry(
        account_identity=_identity(),
        entries=(),
        captured_at=T0 + timedelta(minutes=1),
    )

    assert registry.status(
        capability=InstrumentCapability.FUTURE,
        at=T0 + timedelta(seconds=30),
    ) is CapabilityStatus.UNKNOWN

    with pytest.raises(
        CiboCompoundCapitalError,
        match="UNKNOWN capability cannot claim provider verification",
    ):
        _evidence(
            capability=InstrumentCapability.FUTURE,
            status=CapabilityStatus.UNKNOWN,
            provider_verified=True,
        )


def test_symbol_specific_capability_overrides_account_scope() -> None:
    account_cfd = _evidence()
    symbol_cfd = _evidence(
        status=CapabilityStatus.UNAVAILABLE,
        qore_symbol="NAS100",
        provider_symbol="US100",
    )
    registry = ProviderInstrumentCapabilityRegistry(
        account_identity=_identity(),
        entries=(account_cfd, symbol_cfd),
        captured_at=T0 + timedelta(minutes=1),
    )

    assert registry.status(
        capability=InstrumentCapability.CFD,
        at=T0 + timedelta(seconds=30),
        qore_symbol="NAS100",
        provider_symbol="US100",
    ) is CapabilityStatus.UNAVAILABLE
    assert registry.status(
        capability=InstrumentCapability.CFD,
        at=T0 + timedelta(seconds=30),
        qore_symbol="XAUUSD",
        provider_symbol="XAUUSD",
    ) is CapabilityStatus.SUPPORTED


def test_expired_capability_fails_back_to_unknown() -> None:
    entry = _evidence(
        capability=InstrumentCapability.HEDGE,
        expires_at=T0 + timedelta(minutes=5),
    )
    registry = ProviderInstrumentCapabilityRegistry(
        account_identity=_identity(),
        entries=(entry,),
        captured_at=T0 + timedelta(minutes=2),
    )

    assert registry.status(
        capability=InstrumentCapability.HEDGE,
        at=T0 + timedelta(minutes=4),
    ) is CapabilityStatus.SUPPORTED
    assert registry.status(
        capability=InstrumentCapability.HEDGE,
        at=T0 + timedelta(minutes=5),
    ) is CapabilityStatus.UNKNOWN


def test_registry_rejects_cross_account_and_duplicate_scope() -> None:
    entry = _evidence()
    other_identity = CiboAccountCapitalIdentity(
        provider_key="ctrader",
        account_ref="other-account",
        environment=MarketRuntimeEnvironment.TEST,
    )

    with pytest.raises(
        CiboCompoundCapitalError,
        match="cannot mix account domains",
    ):
        ProviderInstrumentCapabilityRegistry(
            account_identity=other_identity,
            entries=(entry,),
            captured_at=T0 + timedelta(minutes=1),
        )

    with pytest.raises(
        CiboCompoundCapitalError,
        match="duplicate capability scope",
    ):
        ProviderInstrumentCapabilityRegistry(
            account_identity=_identity(),
            entries=(entry, entry),
            captured_at=T0 + timedelta(minutes=1),
        )


def test_missing_option_evidence_never_infers_option_support() -> None:
    registry = ProviderInstrumentCapabilityRegistry(
        account_identity=_identity(),
        entries=(
            _evidence(
                capability=InstrumentCapability.CFD,
                status=CapabilityStatus.SUPPORTED,
            ),
        ),
        captured_at=T0 + timedelta(minutes=1),
    )

    assert registry.status(
        capability=InstrumentCapability.OPTION,
        at=T0 + timedelta(seconds=30),
    ) is CapabilityStatus.UNKNOWN
    assert registry.status(
        capability=InstrumentCapability.DEFINED_RISK_SPREAD,
        at=T0 + timedelta(seconds=30),
    ) is CapabilityStatus.UNKNOWN
