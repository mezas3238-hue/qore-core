"""Fail-closed cTrader DEMO capability-registry reconciliation for CIBO.

Account mode is provider/account evidence. It may prove NETTING semantics, but it
must never be promoted into T16 economic-hedge support or T17 option/spread
support without explicit instrument-class and economic evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
)
from qore.infrastructure.cibo_compound_capital import CiboCompoundCapitalError
from qore.infrastructure.cibo_ctrader_demo_account_capability import (
    CTraderDemoAccountCapabilityObservation,
    CTraderDemoAccountType,
)
from qore.infrastructure.cibo_ctrader_demo_instrument_taxonomy import (
    CTraderDemoInstrumentTaxonomyObservation,
    assert_taxonomy_bound_to_capability,
)
from qore.infrastructure.cibo_instrument_capability_registry import (
    CapabilityStatus,
    InstrumentCapability,
    ProviderCapabilityEvidence,
    ProviderInstrumentCapabilityRegistry,
)
from qore.infrastructure.market_test_environment import MarketRuntimeEnvironment

_POLICY_VERSION = "CIBO_CTRADER_DEMO_CAPABILITY_RECONCILIATION_V1"


@dataclass(frozen=True, slots=True)
class CTraderDemoT16T17CapabilityReport:
    registry: ProviderInstrumentCapabilityRegistry
    account_type: CTraderDemoAccountType
    netting_status: CapabilityStatus
    t16_hedge_status: CapabilityStatus
    t17_option_status: CapabilityStatus
    t17_defined_risk_spread_status: CapabilityStatus
    taxonomy_binding_complete: bool
    option_taxonomy_candidates: tuple[str, ...]
    blockers: tuple[str, ...]
    runtime_authority: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.registry, ProviderInstrumentCapabilityRegistry):
            raise CiboCompoundCapitalError(
                "cTrader capability reconciliation requires canonical registry"
            )
        if type(self.account_type) is not CTraderDemoAccountType:
            raise CiboCompoundCapitalError(
                "cTrader capability reconciliation account type invalid"
            )
        for name in (
            "netting_status",
            "t16_hedge_status",
            "t17_option_status",
            "t17_defined_risk_spread_status",
        ):
            if type(getattr(self, name)) is not CapabilityStatus:
                raise CiboCompoundCapitalError(
                    f"cTrader capability reconciliation {name} invalid"
                )
        if self.t16_hedge_status is not CapabilityStatus.UNKNOWN:
            raise CiboCompoundCapitalError(
                "cTrader account mode cannot certify T16 economic hedge capability"
            )
        if (
            self.t17_option_status is not CapabilityStatus.UNKNOWN
            or self.t17_defined_risk_spread_status
            is not CapabilityStatus.UNKNOWN
        ):
            raise CiboCompoundCapitalError(
                "cTrader symbol names/account mode cannot certify T17 structures"
            )
        if type(self.taxonomy_binding_complete) is not bool:
            raise CiboCompoundCapitalError(
                "cTrader capability taxonomy binding flag invalid"
            )
        if len(self.option_taxonomy_candidates) != len(
            set(self.option_taxonomy_candidates)
        ):
            raise CiboCompoundCapitalError(
                "cTrader capability option taxonomy candidates must be unique"
            )
        if self.runtime_authority:
            raise CiboCompoundCapitalError(
                "cTrader capability reconciliation has no runtime authority"
            )


def reconcile_ctrader_demo_capability_registry(
    *,
    account_identity: CiboAccountCapitalIdentity,
    observation: CTraderDemoAccountCapabilityObservation,
    taxonomy: CTraderDemoInstrumentTaxonomyObservation | None = None,
    produced_at: datetime | None = None,
) -> CTraderDemoT16T17CapabilityReport:
    """Translate account-bound observation into conservative capability truth."""

    if not isinstance(account_identity, CiboAccountCapitalIdentity):
        raise CiboCompoundCapitalError(
            "cTrader capability reconciliation requires account identity"
        )
    if account_identity.environment is not MarketRuntimeEnvironment.DEMO:
        raise CiboCompoundCapitalError(
            "cTrader DEMO capability reconciliation requires DEMO identity"
        )
    if "ctrader" not in account_identity.provider_key.lower():
        raise CiboCompoundCapitalError(
            "cTrader DEMO capability reconciliation provider mismatch"
        )
    if not isinstance(observation, CTraderDemoAccountCapabilityObservation):
        raise CiboCompoundCapitalError(
            "cTrader capability reconciliation requires canonical observation"
        )
    if account_identity.account_ref != observation.account_ref:
        raise CiboCompoundCapitalError(
            "cTrader capability reconciliation account identity mismatch"
        )
    if taxonomy is not None:
        if not isinstance(taxonomy, CTraderDemoInstrumentTaxonomyObservation):
            raise CiboCompoundCapitalError(
                "cTrader capability taxonomy evidence invalid"
            )
        try:
            assert_taxonomy_bound_to_capability(
                capability=observation,
                taxonomy=taxonomy,
            )
        except Exception as error:
            raise CiboCompoundCapitalError(
                f"cTrader capability taxonomy binding invalid: {error}"
            ) from error

    produced = produced_at or (
        taxonomy.observed_at if taxonomy is not None else observation.observed_at
    )
    if produced.tzinfo is None or produced.utcoffset() is None:
        raise CiboCompoundCapitalError(
            "cTrader capability reconciliation produced_at must be timezone-aware"
        )
    if produced < observation.observed_at:
        raise CiboCompoundCapitalError(
            "cTrader capability reconciliation cannot predate observation"
        )
    if taxonomy is not None and produced < taxonomy.observed_at:
        raise CiboCompoundCapitalError(
            "cTrader capability reconciliation cannot predate taxonomy evidence"
        )

    source_sha = observation.fingerprint()
    netting_status = _netting_status(observation.account_type)
    entries = (
        _entry(
            account_identity=account_identity,
            observation=observation,
            produced_at=produced,
            capability=InstrumentCapability.NETTING,
            status=netting_status,
            provider_verified=netting_status is not CapabilityStatus.UNKNOWN,
        ),
        _entry(
            account_identity=account_identity,
            observation=observation,
            produced_at=produced,
            capability=InstrumentCapability.HEDGE,
            status=CapabilityStatus.UNKNOWN,
            provider_verified=False,
        ),
        _entry(
            account_identity=account_identity,
            observation=observation,
            produced_at=produced,
            capability=InstrumentCapability.OPTION,
            status=CapabilityStatus.UNKNOWN,
            provider_verified=False,
        ),
        _entry(
            account_identity=account_identity,
            observation=observation,
            produced_at=produced,
            capability=InstrumentCapability.DEFINED_RISK_SPREAD,
            status=CapabilityStatus.UNKNOWN,
            provider_verified=False,
        ),
    )
    registry = ProviderInstrumentCapabilityRegistry(
        account_identity=account_identity,
        entries=entries,
        captured_at=produced,
    )
    taxonomy_complete = (
        taxonomy is not None and taxonomy.catalog_binding_complete
    )
    option_candidates = (
        ()
        if taxonomy is None
        else taxonomy.option_taxonomy_candidates
    )
    blockers_list = [
        "T16_HEDGE_INSTRUMENT_NOT_PROVIDER_VERIFIED",
        "T16_BASIS_RISK_COST_CORRELATION_EXECUTION_EVIDENCE_REQUIRED",
    ]
    if not taxonomy_complete:
        blockers_list.append("T17_ACCOUNT_TAXONOMY_BINDING_INCOMPLETE")
    elif option_candidates:
        blockers_list.append(
            "T17_OPTION_TAXONOMY_CANDIDATE_REQUIRES_INSTRUMENT_EXECUTION_PROOF"
        )
    else:
        blockers_list.append(
            "T17_NO_EXPLICIT_OPTION_TAXONOMY_CANDIDATE"
        )
    blockers_list.append(
        "T17_DEFINED_RISK_SPREAD_INSTRUMENT_CLASS_NOT_PROVIDER_VERIFIED"
    )
    blockers = tuple(blockers_list)
    if source_sha != observation.fingerprint():
        raise CiboCompoundCapitalError(
            "cTrader capability observation fingerprint drift"
        )
    return CTraderDemoT16T17CapabilityReport(
        registry=registry,
        account_type=observation.account_type,
        netting_status=netting_status,
        t16_hedge_status=registry.status(
            capability=InstrumentCapability.HEDGE,
            at=produced,
        ),
        t17_option_status=registry.status(
            capability=InstrumentCapability.OPTION,
            at=produced,
        ),
        t17_defined_risk_spread_status=registry.status(
            capability=InstrumentCapability.DEFINED_RISK_SPREAD,
            at=produced,
        ),
        taxonomy_binding_complete=taxonomy_complete,
        option_taxonomy_candidates=option_candidates,
        blockers=blockers,
    )


def _entry(
    *,
    account_identity: CiboAccountCapitalIdentity,
    observation: CTraderDemoAccountCapabilityObservation,
    produced_at: datetime,
    capability: InstrumentCapability,
    status: CapabilityStatus,
    provider_verified: bool,
) -> ProviderCapabilityEvidence:
    return ProviderCapabilityEvidence(
        evidence_id=(
            f"ctrader-demo:{observation.account_ref}:"
            f"{capability.value.lower()}"
        ),
        account_identity=account_identity,
        capability=capability,
        status=status,
        observed_at=observation.observed_at,
        produced_at=produced_at,
        source="CTRADER_DEMO_ACCOUNT_CAPABILITY_OBSERVATION",
        source_ref=observation.fingerprint(),
        evidence_sha256=observation.fingerprint(),
        policy_version=_POLICY_VERSION,
        provider_verified=provider_verified,
    )


def _netting_status(account_type: CTraderDemoAccountType) -> CapabilityStatus:
    if account_type is CTraderDemoAccountType.NETTED:
        return CapabilityStatus.SUPPORTED
    if account_type is CTraderDemoAccountType.HEDGED:
        return CapabilityStatus.UNAVAILABLE
    return CapabilityStatus.UNKNOWN
