"""Independent VT-08 Forex authority over the Revision 3.2 source kernel."""

from __future__ import annotations

import json
from datetime import datetime
from hashlib import sha256

from qore.infrastructure.trader_lab.trader_daily_cardinality import (
    MarketDayLedger,
    market_day_id_from_timestamp,
)
from qore.infrastructure.trader_lab.vt08_market_day_ledger import VT08MarketDayLedger
from qore.infrastructure.traders.vt08_source_kernel_r3_2 import (
    METHODOLOGY_VERSION as SOURCE_KERNEL_VERSION,
)
from qore.infrastructure.traders.vt08_source_kernel_r3_2 import (
    OWNER_FOREX_ANCHORS,
    SOURCE_FOREX_ANCHORS,
    VT08LtfProfile,
    VT08MarketFamily,
    VT08TimingProfile,
    anchor_hours,
)
from qore.infrastructure.traders.vt08_source_kernel_r3_2 import (
    methodology_fingerprint as source_kernel_fingerprint,
)
from qore.kernel.errors import InfrastructureError

TRADER_FAMILY = "vt08-forex"
TRADER_NAME = "VT-08-FOREX"
TRADER_VERSION = "r3.2-rebuild-v1"
AUTHORIZED_MARKETS = (
    "AUDJPY",
    "AUDUSD",
    "EURUSD",
    "GBPJPY",
    "GBPUSD",
    "USDCAD",
    "USDJPY",
)
SOURCE_COMPLETE_H4_ANCHORS_NEW_YORK = SOURCE_FOREX_ANCHORS
OWNER_OPERATIONAL_H4_ANCHORS_NEW_YORK = OWNER_FOREX_ANCHORS
MAXIMUM_FILLED_TRADES_PER_MARKET_PER_NY_DATE = 1
DAILY_SELECTION_POLICY = "owner-policy-required-not-yet-frozen"


class VT08ForexError(InfrastructureError):
    __slots__ = ()


class VT08ForexValidationError(VT08ForexError):
    __slots__ = ()


def _require_market(symbol: str) -> None:
    if symbol not in AUTHORIZED_MARKETS:
        raise VT08ForexValidationError("market is outside VT-08-FOREX authority")


def _fingerprint(kind: str) -> str:
    material = {
        "kind": kind,
        "trader_family": TRADER_FAMILY,
        "trader_version": TRADER_VERSION,
        "source_kernel_version": SOURCE_KERNEL_VERSION,
        "source_kernel_fingerprint": source_kernel_fingerprint(),
        "authorized_markets": AUTHORIZED_MARKETS,
        "source_complete_anchors": SOURCE_COMPLETE_H4_ANCHORS_NEW_YORK,
        "owner_operational_anchors": OWNER_OPERATIONAL_H4_ANCHORS_NEW_YORK,
        "ltf_profiles": [item.value for item in VT08LtfProfile],
        "maximum_filled_trades_per_market_per_ny_date": 1,
        "daily_selection_policy": DAILY_SELECTION_POLICY,
    }
    encoded = json.dumps(material, sort_keys=True, separators=(",", ":")).encode()
    return sha256(encoded).hexdigest()


def methodology_fingerprint() -> str:
    return _fingerprint("methodology")


def config_fingerprint() -> str:
    return _fingerprint("config")


class VT08ForexTrader:
    """Forex-only research authority; Futures/index symbols fail closed."""

    @staticmethod
    def new_market_day_ledger(
        *,
        symbol: str,
        observed_at: datetime,
        eligible_day: bool,
        data_complete: bool,
        software_sha: str,
        evidence_fingerprint: str,
        timing_profile: VT08TimingProfile,
        ltf_profile: VT08LtfProfile,
        source_provenance: tuple[str, ...] = (),
    ) -> VT08MarketDayLedger:
        _require_market(symbol)
        if type(timing_profile) is not VT08TimingProfile:
            raise VT08ForexValidationError("timing_profile must be exact")
        if type(ltf_profile) is not VT08LtfProfile:
            raise VT08ForexValidationError("ltf_profile must be exact")
        windows = anchor_hours(VT08MarketFamily.FOREX, timing_profile)
        cardinality = MarketDayLedger(
            market_day_id=market_day_id_from_timestamp(
                trader_family=TRADER_FAMILY,
                canonical_market=symbol,
                observed_at=observed_at,
            ),
            eligible_day=eligible_day,
            data_complete=data_complete,
            authorized_windows=windows,
            source_rule_version=SOURCE_KERNEL_VERSION,
            software_sha=software_sha,
            evidence_fingerprint=evidence_fingerprint,
        )
        return VT08MarketDayLedger(
            cardinality=cardinality,
            market_family=VT08MarketFamily.FOREX,
            timing_profile=timing_profile,
            ltf_profile=ltf_profile,
            source_provenance=source_provenance,
        )
