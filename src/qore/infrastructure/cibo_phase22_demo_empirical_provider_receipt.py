"""Immutable receipt for Phase22 cTrader DEMO empirical provider evidence.

This receipt binds the read-only causal quote/fill population collected after
the bounded DEMO execution calibration. It proves current DEMO provider
execution evidence only. It does not claim historical provider fills or consume
the Phase22 V2 holdout.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_phase22_demo_calibration_contract import (
    MINIMUM_DISTINCT_ENTRY_ORDERS_PER_SYMBOL,
    REQUIRED_SYMBOLS,
)

RUN_ID = 36927602692
RUN_HEAD_SHA = "9896fd96c95480744b2de123d42f1f7848993537"
ARTIFACT_ID = 11194039517
ARTIFACT_DIGEST = (
    "sha256:5957a77cceb44c15319785aa26a1a0574fef46535ff7ce69fcec3757d02972c4"
)
OBSERVED_AT = "2026-10-01T21:18:04.499274+00:00"
ACCOUNT_FINGERPRINT_SHA256 = (
    "17585ecd6f116a92d19919e46948f06c027d0cbf9f1cb8d97802f20055bad17b"
)
STATUS = "EMPIRICAL_PROVIDER_CALIBRATION_READY"


@dataclass(frozen=True, slots=True)
class Phase22DemoEmpiricalProviderReceipt:
    provider_key: str
    environment: str
    account_fingerprint_sha256: str
    required_symbols: tuple[str, ...]
    minimum_distinct_entry_orders_per_symbol: int
    qore_deals_found: int
    observation_count: int
    distinct_orders_by_symbol: tuple[tuple[str, int], ...]
    p95_execution_latency_ms_by_symbol: tuple[tuple[str, int], ...]
    p95_quote_age_ms_by_symbol: tuple[tuple[str, int], ...]
    empirical_slippage_calibrated: bool
    execution_model_ready: bool
    blockers: tuple[str, ...]
    deal_history_truncated: bool
    broker_mutation_performed: bool
    holdout_outcomes_used: bool
    historical_provider_economics_claimed: bool
    target_aware: bool
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if self.provider_key != "ctrader-demo" or self.environment != "demo":
            raise CiboCapitalManagementError(
                "Phase22 empirical provider receipt environment drift"
            )
        if len(self.account_fingerprint_sha256) != 64:
            raise CiboCapitalManagementError(
                "Phase22 empirical provider account fingerprint invalid"
            )
        if self.required_symbols != REQUIRED_SYMBOLS:
            raise CiboCapitalManagementError(
                "Phase22 empirical provider symbol surface drift"
            )
        if self.minimum_distinct_entry_orders_per_symbol != (
            MINIMUM_DISTINCT_ENTRY_ORDERS_PER_SYMBOL
        ):
            raise CiboCapitalManagementError(
                "Phase22 empirical provider minimum drift"
            )
        counts = dict(self.distinct_orders_by_symbol)
        if tuple(name for name, _ in self.distinct_orders_by_symbol) != REQUIRED_SYMBOLS:
            raise CiboCapitalManagementError(
                "Phase22 empirical provider count ordering drift"
            )
        if any(
            counts[symbol] < self.minimum_distinct_entry_orders_per_symbol
            for symbol in REQUIRED_SYMBOLS
        ):
            raise CiboCapitalManagementError(
                "Phase22 empirical provider population below minimum"
            )
        if self.qore_deals_found != self.observation_count:
            raise CiboCapitalManagementError(
                "Phase22 empirical provider causal observation gap"
            )
        if self.qore_deals_found < sum(
            self.minimum_distinct_entry_orders_per_symbol
            for _ in REQUIRED_SYMBOLS
        ):
            raise CiboCapitalManagementError(
                "Phase22 empirical provider total population below minimum"
            )
        if tuple(name for name, _ in self.p95_execution_latency_ms_by_symbol) != (
            REQUIRED_SYMBOLS
        ):
            raise CiboCapitalManagementError(
                "Phase22 empirical provider latency ordering drift"
            )
        if tuple(name for name, _ in self.p95_quote_age_ms_by_symbol) != REQUIRED_SYMBOLS:
            raise CiboCapitalManagementError(
                "Phase22 empirical provider quote-age ordering drift"
            )
        if any(value < 0 for _, value in self.p95_execution_latency_ms_by_symbol):
            raise CiboCapitalManagementError(
                "Phase22 empirical provider negative execution latency"
            )
        if any(value < 0 for _, value in self.p95_quote_age_ms_by_symbol):
            raise CiboCapitalManagementError(
                "Phase22 empirical provider negative quote age"
            )
        if (
            not self.empirical_slippage_calibrated
            or not self.execution_model_ready
            or self.blockers
            or self.deal_history_truncated
            or self.broker_mutation_performed
            or self.holdout_outcomes_used
            or self.historical_provider_economics_claimed
            or self.target_aware
            or self.productive_authority
        ):
            raise CiboCapitalManagementError(
                "Phase22 empirical provider receipt governance/readiness drift"
            )

    def fingerprint(self) -> str:
        raw = json.dumps(
            asdict(self),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return "sha256:" + hashlib.sha256(raw).hexdigest()


PHASE22_DEMO_EMPIRICAL_PROVIDER_RECEIPT = Phase22DemoEmpiricalProviderReceipt(
    provider_key="ctrader-demo",
    environment="demo",
    account_fingerprint_sha256=ACCOUNT_FINGERPRINT_SHA256,
    required_symbols=REQUIRED_SYMBOLS,
    minimum_distinct_entry_orders_per_symbol=(
        MINIMUM_DISTINCT_ENTRY_ORDERS_PER_SYMBOL
    ),
    qore_deals_found=53,
    observation_count=53,
    distinct_orders_by_symbol=(
        ("AUDJPY", 12),
        ("EURUSD", 9),
        ("GBPJPY", 8),
        ("GBPUSD", 8),
        ("NAS100", 8),
        ("XAUUSD", 8),
    ),
    p95_execution_latency_ms_by_symbol=(
        ("AUDJPY", 290),
        ("EURUSD", 277),
        ("GBPJPY", 264),
        ("GBPUSD", 296),
        ("NAS100", 301),
        ("XAUUSD", 297),
    ),
    p95_quote_age_ms_by_symbol=(
        ("AUDJPY", 2496),
        ("EURUSD", 4045),
        ("GBPJPY", 1886),
        ("GBPUSD", 5574),
        ("NAS100", 399),
        ("XAUUSD", 1341),
    ),
    empirical_slippage_calibrated=True,
    execution_model_ready=True,
    blockers=(),
    deal_history_truncated=False,
    broker_mutation_performed=False,
    holdout_outcomes_used=False,
    historical_provider_economics_claimed=False,
    target_aware=False,
)


def phase22_demo_empirical_provider_receipt_payload() -> dict[str, object]:
    receipt = PHASE22_DEMO_EMPIRICAL_PROVIDER_RECEIPT
    return {
        "schema": "qore.cibo.phase22.demo-empirical-provider-receipt.v1",
        "status": STATUS,
        "run_id": RUN_ID,
        "run_head_sha": RUN_HEAD_SHA,
        "artifact_id": ARTIFACT_ID,
        "artifact_digest": ARTIFACT_DIGEST,
        "observed_at": OBSERVED_AT,
        **asdict(receipt),
        "receipt_sha256": receipt.fingerprint(),
    }
