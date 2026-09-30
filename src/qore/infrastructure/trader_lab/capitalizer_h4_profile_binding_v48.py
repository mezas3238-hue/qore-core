"""V48 H4 profile/time binding ledger for TTrades Asia and London routes.

The TTrades Asia/London source material uses 4H candles as methodology objects. The reviewed
PDFs visibly show profile labels such as 22:00, 02:00 and 06:00 around H4 examples. cTrader
also exposes provider-native H4 trendbars.

What is *not* yet proven is that the provider H4 candle boundary is identical to the TTrades
chart/profile boundary. V48 therefore fails closed for productive H4-route census until this
clock identity is source-bound. Generic H1/M15/M1 Scalping and non-H4 routes are independent.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from qore.infrastructure.trader_lab.capitalizer_source_native_route_registry_v48 import (
    V48RouteId,
)

IDENTITY = "QORE_CAPITALIZER_V48_H4_PROFILE_BINDING"


class V48H4BindingState(StrEnum):
    SOURCE_BINDING_BLOCKED = "SOURCE_BINDING_BLOCKED"
    RESOLVED = "RESOLVED"


@dataclass(frozen=True, slots=True)
class V48H4ProfileEvidence:
    source_id: str
    source_url: str
    evidence: str
    proves_exact_provider_boundary: bool = False

    def __post_init__(self) -> None:
        if not self.source_id or self.source_id != self.source_id.upper():
            raise ValueError("H4 evidence id must be non-empty uppercase")
        if not self.source_url.startswith("https://"):
            raise ValueError("H4 evidence requires source URL")
        if not self.evidence:
            raise ValueError("H4 evidence requires a description")


EVIDENCE: tuple[V48H4ProfileEvidence, ...] = (
    V48H4ProfileEvidence(
        "TTRADES_LONDON_PDF_H4_PROFILE_LABELS",
        "https://ttrades.com/wp-content/uploads/2026/09/TTrades-Trading-London.pdf",
        (
            "Reviewed London PDF H4 examples visibly label profile candles around "
            "22:00, 02:00 and 06:00."
        ),
    ),
    V48H4ProfileEvidence(
        "TTRADES_ASIA_PDF_D1_H4_15M_STACK",
        "https://ttrades.com/wp-content/uploads/2026/08/TTrades-Asia-Entries.pdf",
        "Reviewed Asia PDF explicitly demonstrates D1 to H4 and H4 to 15M fractal stacks.",
    ),
    V48H4ProfileEvidence(
        "CTRADER_PROVIDER_NATIVE_H4_AVAILABLE",
        "https://help.ctrader.com/open-api/model-messages/",
        (
            "cTrader Open API exposes provider-native H4 trendbars, but availability alone "
            "does not prove candle-boundary identity with the TTrades chart."
        ),
    ),
)


@dataclass(frozen=True, slots=True)
class V48H4ProfileBinding:
    identity: str = IDENTITY
    state: V48H4BindingState = V48H4BindingState.SOURCE_BINDING_BLOCKED
    evidence: tuple[V48H4ProfileEvidence, ...] = EVIDENCE
    provider_native_h4_available: bool = True
    provider_boundary_equals_ttrades_profile_proven: bool = False
    synthetic_h4_authorized: bool = False
    productive_h4_route_census_authorized: bool = False
    blocked_routes: tuple[V48RouteId, ...] = (
        V48RouteId.TTRADES_ASIA_4H_15M,
        V48RouteId.TTRADES_LONDON_DAILY_4H_15M,
    )
    generic_scalp_blocked: bool = False
    fresh_holdout_authorized: bool = False
    economics_authorized: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY:
            raise ValueError("H4 binding identity is frozen")
        if self.state is V48H4BindingState.RESOLVED:
            if not self.provider_boundary_equals_ttrades_profile_proven:
                raise ValueError("resolved H4 binding requires proven boundary identity")
        if self.synthetic_h4_authorized:
            raise ValueError("V48 cannot synthesize an unbound H4 methodology candle")
        if self.productive_h4_route_census_authorized:
            if self.state is not V48H4BindingState.RESOLVED:
                raise ValueError("blocked H4 binding cannot authorize productive census")
        if self.generic_scalp_blocked:
            raise ValueError("H4 binding cannot block independent H1/M15/M1 Scalping route")
        if self.fresh_holdout_authorized or self.economics_authorized:
            raise ValueError("H4 binding ledger grants no Fresh/economic authority")


V48_H4_PROFILE_BINDING = V48H4ProfileBinding()
