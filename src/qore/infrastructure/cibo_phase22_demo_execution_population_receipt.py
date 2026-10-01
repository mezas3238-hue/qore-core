"""Immutable receipt for the real Phase22 cTrader DEMO execution population.

The receipt proves that the minimum real DEMO execution population now exists
for all required symbols. It does not claim causal slippage calibration and it
does not inspect Phase22 holdout outcomes.
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

RUN_ID = 36922694706
RUN_HEAD_SHA = "380a7ee726c97eef700ff31a1fa7839efd0436c9"
ARTIFACT_ID = 11192332824
ARTIFACT_DIGEST = (
    "sha256:049da53fe89fe5e56176b5a32771be674fafd3b94d425d4594a6a06eb149ac70"
)
STATUS = "EXECUTION_POPULATION_READY_QUOTE_RECONSTRUCTION_PENDING"


@dataclass(frozen=True, slots=True)
class Phase22DemoExecutionPopulationReceipt:
    provider_key: str
    environment: str
    required_symbols: tuple[str, ...]
    minimum_distinct_entry_orders_per_symbol: int
    execution_counts: tuple[tuple[str, int], ...]
    execution_population_ready: bool
    causal_quote_reconstruction_ready: bool
    broker_mutation_performed_by_receipt_run: bool
    holdout_outcomes_used: bool
    historical_provider_economics_claimed: bool
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if self.provider_key != "ctrader-demo" or self.environment != "demo":
            raise CiboCapitalManagementError(
                "Phase22 DEMO execution population provider drift"
            )
        if self.required_symbols != REQUIRED_SYMBOLS:
            raise CiboCapitalManagementError(
                "Phase22 DEMO execution population symbol surface drift"
            )
        if self.minimum_distinct_entry_orders_per_symbol != (
            MINIMUM_DISTINCT_ENTRY_ORDERS_PER_SYMBOL
        ):
            raise CiboCapitalManagementError(
                "Phase22 DEMO execution population minimum drift"
            )
        names = tuple(name for name, _ in self.execution_counts)
        if names != REQUIRED_SYMBOLS:
            raise CiboCapitalManagementError(
                "Phase22 DEMO execution count ordering drift"
            )
        expected_ready = all(
            count >= self.minimum_distinct_entry_orders_per_symbol
            for _, count in self.execution_counts
        )
        if self.execution_population_ready != expected_ready:
            raise CiboCapitalManagementError(
                "Phase22 DEMO execution population readiness drift"
            )
        if (
            self.causal_quote_reconstruction_ready
            or self.broker_mutation_performed_by_receipt_run
            or self.holdout_outcomes_used
            or self.historical_provider_economics_claimed
            or self.productive_authority
        ):
            raise CiboCapitalManagementError(
                "Phase22 DEMO execution population receipt governance drift"
            )

    def fingerprint(self) -> str:
        raw = json.dumps(
            asdict(self),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return "sha256:" + hashlib.sha256(raw).hexdigest()


PHASE22_DEMO_EXECUTION_POPULATION_RECEIPT = (
    Phase22DemoExecutionPopulationReceipt(
        provider_key="ctrader-demo",
        environment="demo",
        required_symbols=REQUIRED_SYMBOLS,
        minimum_distinct_entry_orders_per_symbol=(
            MINIMUM_DISTINCT_ENTRY_ORDERS_PER_SYMBOL
        ),
        execution_counts=(
            ("AUDJPY", 12),
            ("EURUSD", 8),
            ("GBPJPY", 8),
            ("GBPUSD", 8),
            ("NAS100", 8),
            ("XAUUSD", 8),
        ),
        execution_population_ready=True,
        causal_quote_reconstruction_ready=False,
        broker_mutation_performed_by_receipt_run=False,
        holdout_outcomes_used=False,
        historical_provider_economics_claimed=False,
    )
)


def phase22_demo_execution_population_receipt_payload() -> dict[str, object]:
    receipt = PHASE22_DEMO_EXECUTION_POPULATION_RECEIPT
    return {
        "schema": "qore.cibo.phase22.demo-execution-population-receipt.v1",
        "status": STATUS,
        "run_id": RUN_ID,
        "run_head_sha": RUN_HEAD_SHA,
        "artifact_id": ARTIFACT_ID,
        "artifact_digest": ARTIFACT_DIGEST,
        **asdict(receipt),
        "receipt_sha256": receipt.fingerprint(),
    }
