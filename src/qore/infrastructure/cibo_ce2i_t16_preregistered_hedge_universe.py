"""Pre-outcome preregistration for the CIBO CE2I T16 hedge universe.

The current cTrader DEMO catalog proves that USTEC, US500 and US30 are enabled
provider instruments. This module freezes a deliberately narrow NAS100 hedge
candidate universe before any pair return, correlation, basis-risk, hedge-cost
or fresh-OOS utility observation is consumed.

Preregistration is not hedge certification. The declarations carry no sizing,
Risk, execution, LIVE or productive authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_t16_hedge_candidate import (
    T16HedgePairDeclaration,
)

T16_PREREGISTRATION_ID = "CIBO_T16_CTRADER_DEMO_HEDGE_UNIVERSE_V1"
T16_PROVIDER_KEY = "ctrader-demo"
T16_ACCOUNT_FINGERPRINT_SHA256 = (
    "70d38b13a2afb1ada12883a486ddb39aa0626e4c262b69ee44410bb6531d6086"
)
T16_PROVIDER_CATALOG_SHA256 = (
    "sha256:47ddbd42c083d7709f1c7b9922c4ef6826219f91c25aff9c894513a480fcbcf1"
)
T16_PROVIDER_CATALOG_OBSERVED_AT = datetime(
    2026,
    10,
    1,
    4,
    1,
    14,
    559916,
    tzinfo=UTC,
)
T16_DECLARED_AT = datetime(2026, 10, 1, 4, 3, 30, tzinfo=UTC)


@dataclass(frozen=True, slots=True)
class T16PreregisteredHedgeCandidate:
    declaration: T16HedgePairDeclaration
    target_provider_symbol: str
    hedge_provider_symbol: str
    provider_asset_class: str
    selection_basis: str
    account_fingerprint_sha256: str
    provider_catalog_sha256: str
    provider_catalog_observed_at: datetime
    returns_inspected_at_selection: bool = False
    correlation_inspected_at_selection: bool = False
    basis_risk_inspected_at_selection: bool = False
    hedge_cost_inspected_at_selection: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.declaration, T16HedgePairDeclaration):
            raise CiboCapitalManagementError(
                "T16 preregistration requires canonical hedge declaration"
            )
        for name in (
            "target_provider_symbol",
            "hedge_provider_symbol",
            "provider_asset_class",
            "selection_basis",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise CiboCapitalManagementError(
                    f"T16 preregistration {name} is required"
                )
        if (
            len(self.account_fingerprint_sha256) != 64
            or any(
                char not in "0123456789abcdef"
                for char in self.account_fingerprint_sha256
            )
        ):
            raise CiboCapitalManagementError(
                "T16 preregistration account fingerprint must be SHA-256"
            )
        if (
            self.provider_catalog_sha256 != self.declaration.evidence_sha256
            or not self.provider_catalog_sha256.startswith("sha256:")
        ):
            raise CiboCapitalManagementError(
                "T16 preregistration catalog/declaration evidence drift"
            )
        if (
            self.provider_catalog_observed_at.tzinfo is None
            or self.provider_catalog_observed_at.utcoffset() is None
        ):
            raise CiboCapitalManagementError(
                "T16 preregistration provider observation must be timezone-aware"
            )
        if self.declaration.declared_at <= self.provider_catalog_observed_at:
            raise CiboCapitalManagementError(
                "T16 preregistration must postdate provider catalog observation"
            )
        if self.declaration.provider_key != T16_PROVIDER_KEY:
            raise CiboCapitalManagementError(
                "T16 preregistration provider drift"
            )
        if self.declaration.target_symbol != "NAS100":
            raise CiboCapitalManagementError(
                "T16 preregistration V1 target must remain NAS100"
            )
        if self.target_provider_symbol != "USTEC":
            raise CiboCapitalManagementError(
                "T16 preregistration V1 target provider symbol drift"
            )
        if self.declaration.hedge_symbol != self.hedge_provider_symbol:
            raise CiboCapitalManagementError(
                "T16 preregistration hedge symbol drift"
            )
        if self.returns_inspected_at_selection:
            raise CiboCapitalManagementError(
                "T16 preregistration cannot consume pair returns"
            )
        if self.correlation_inspected_at_selection:
            raise CiboCapitalManagementError(
                "T16 preregistration cannot consume correlation"
            )
        if self.basis_risk_inspected_at_selection:
            raise CiboCapitalManagementError(
                "T16 preregistration cannot consume basis-risk outcomes"
            )
        if self.hedge_cost_inspected_at_selection:
            raise CiboCapitalManagementError(
                "T16 preregistration cannot consume hedge-cost outcomes"
            )
        if self.productive_authority:
            raise CiboCapitalManagementError(
                "T16 preregistration has no productive authority"
            )


def _candidate(
    *,
    declaration_id: str,
    hedge_provider_symbol: str,
) -> T16PreregisteredHedgeCandidate:
    declaration = T16HedgePairDeclaration(
        declaration_id=declaration_id,
        provider_key=T16_PROVIDER_KEY,
        target_symbol="NAS100",
        hedge_symbol=hedge_provider_symbol,
        declared_at=T16_DECLARED_AT,
        evidence_sha256=T16_PROVIDER_CATALOG_SHA256,
    )
    return T16PreregisteredHedgeCandidate(
        declaration=declaration,
        target_provider_symbol="USTEC",
        hedge_provider_symbol=hedge_provider_symbol,
        provider_asset_class="Indices",
        selection_basis=(
            "PREOUTCOME_SAME_PROVIDER_BROAD_US_EQUITY_INDEX_FACTOR"
        ),
        account_fingerprint_sha256=T16_ACCOUNT_FINGERPRINT_SHA256,
        provider_catalog_sha256=T16_PROVIDER_CATALOG_SHA256,
        provider_catalog_observed_at=T16_PROVIDER_CATALOG_OBSERVED_AT,
    )


PREREGISTERED_T16_HEDGE_CANDIDATES = (
    _candidate(
        declaration_id="T16_CTRADER_DEMO_NAS100_US30_V1",
        hedge_provider_symbol="US30",
    ),
    _candidate(
        declaration_id="T16_CTRADER_DEMO_NAS100_US500_V1",
        hedge_provider_symbol="US500",
    ),
)


def preregistered_t16_hedge_declarations(
) -> tuple[T16HedgePairDeclaration, ...]:
    """Return the immutable pre-outcome T16 declaration set."""

    return tuple(
        candidate.declaration
        for candidate in PREREGISTERED_T16_HEDGE_CANDIDATES
    )
