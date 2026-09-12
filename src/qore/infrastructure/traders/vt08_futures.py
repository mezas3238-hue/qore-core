"""VT-08 Futures family contract over the shared source-faithful H4 PO3 kernel.

Futures/index session policy, allowlist and daily execution cardinality are
intentionally separate from VT-08 Forex.  The shared kernel remains the
conservative source reconstruction and still fails closed where source execution
geometry is not resolved.
"""

from __future__ import annotations

import json
from datetime import datetime
from hashlib import sha256

from qore.infrastructure.trader_lab.trader_daily_cardinality import (
    MarketDayLedger,
    market_day_id_from_timestamp,
)
from qore.infrastructure.traders.vt08_crt_h4_amd_v2 import (
    METHODOLOGY_VERSION as SHARED_METHODOLOGY_VERSION,
    Vt08CrtH4AmdV2Candle,
    Vt08CrtH4AmdV2Evaluation,
    Vt08CrtH4AmdV2SourceContext,
    Vt08CrtH4AmdV2WickProfile,
    evaluate_continuation_expansion_candle3 as evaluate_shared_c3,
    evaluate_reversal_expansion_candle2 as evaluate_shared_c2,
    methodology_fingerprint as shared_methodology_fingerprint,
)
from qore.kernel.errors import InfrastructureError

TRADER_FAMILY = "vt08-futures"
TRADER_NAME = "VT-08-FUTURES"
FAMILY_CONTRACT_VERSION = "v1-owner-daily-cardinality"
AUTHORIZED_MARKETS = ("NAS100", "SP500", "US30")
AUTHORIZED_H4_ANCHOR_HOURS_NEW_YORK = (2, 6, 10)
OPERATING_TIMEZONE = "America/New_York"
MAXIMUM_FILLED_TRADES_PER_MARKET_PER_NY_DATE = 1
DAILY_SELECTION_POLICY = "owner-policy-required-not-yet-frozen"


class VT08FuturesError(InfrastructureError):
    __slots__ = ()


class VT08FuturesValidationError(VT08FuturesError):
    __slots__ = ()


def _fingerprint(kind: str) -> str:
    material = {
        "kind": kind,
        "trader_family": TRADER_FAMILY,
        "family_contract_version": FAMILY_CONTRACT_VERSION,
        "shared_methodology_version": SHARED_METHODOLOGY_VERSION,
        "shared_methodology_fingerprint": shared_methodology_fingerprint(),
        "authorized_markets": AUTHORIZED_MARKETS,
        "authorized_h4_anchor_hours_new_york": AUTHORIZED_H4_ANCHOR_HOURS_NEW_YORK,
        "operating_timezone": OPERATING_TIMEZONE,
        "maximum_filled_trades_per_market_per_ny_date": (
            MAXIMUM_FILLED_TRADES_PER_MARKET_PER_NY_DATE
        ),
        "daily_selection_policy": DAILY_SELECTION_POLICY,
        "policy_provenance": "human-owner-execution-policy",
    }
    return sha256(
        json.dumps(material, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def methodology_fingerprint() -> str:
    return _fingerprint("methodology")


def config_fingerprint() -> str:
    return _fingerprint("config")


def _require_market(symbol: str) -> None:
    if symbol not in AUTHORIZED_MARKETS:
        raise VT08FuturesValidationError("market is outside VT-08-FUTURES authority")


class VT08FuturesTrader:
    """Independent futures/index authority wrapper; no Forex market can pass it."""

    @staticmethod
    def new_market_day_ledger(
        *,
        symbol: str,
        observed_at: datetime,
        eligible_day: bool,
        data_complete: bool,
        software_sha: str,
        evidence_fingerprint: str,
    ) -> MarketDayLedger:
        _require_market(symbol)
        market_day = market_day_id_from_timestamp(
            trader_family=TRADER_FAMILY,
            canonical_market=symbol,
            observed_at=observed_at,
        )
        return MarketDayLedger(
            market_day_id=market_day,
            eligible_day=eligible_day,
            data_complete=data_complete,
            authorized_windows=AUTHORIZED_H4_ANCHOR_HOURS_NEW_YORK,
            source_rule_version=SHARED_METHODOLOGY_VERSION,
            software_sha=software_sha,
            evidence_fingerprint=evidence_fingerprint,
        )

    @staticmethod
    def evaluate_candle2(
        *,
        symbol: str,
        h4_reference: Vt08CrtH4AmdV2Candle,
        h4_candle2_closes_at: datetime,
        observed_m15: tuple[Vt08CrtH4AmdV2Candle, ...],
        context: Vt08CrtH4AmdV2SourceContext,
    ) -> Vt08CrtH4AmdV2Evaluation:
        _require_market(symbol)
        return evaluate_shared_c2(
            symbol=symbol,
            h4_reference=h4_reference,
            h4_candle2_closes_at=h4_candle2_closes_at,
            observed_m15=observed_m15,
            context=context,
        )

    @staticmethod
    def evaluate_candle3(
        *,
        symbol: str,
        h4_reference: Vt08CrtH4AmdV2Candle,
        h4_candle2: Vt08CrtH4AmdV2Candle,
        h4_candle3_closes_at: datetime,
        observed_m15: tuple[Vt08CrtH4AmdV2Candle, ...],
        candle2_wick_profile: Vt08CrtH4AmdV2WickProfile,
        context: Vt08CrtH4AmdV2SourceContext,
    ) -> Vt08CrtH4AmdV2Evaluation:
        _require_market(symbol)
        return evaluate_shared_c3(
            symbol=symbol,
            h4_reference=h4_reference,
            h4_candle2=h4_candle2,
            h4_candle3_closes_at=h4_candle3_closes_at,
            observed_m15=observed_m15,
            candle2_wick_profile=candle2_wick_profile,
            context=context,
        )
