"""Canonical pre-holdout provider execution calibration receipt for Phase22 V2.

This receipt composes two immutable cTrader DEMO evidence artifacts:

1. the bounded minimum-volume execution-population calibration proving the
   required symbol population existed and calibration-created positions were
   closed; and
2. the later causal quote/fill reconstruction proving empirical slippage and
   the execution model are READY.

Neither artifact reads Phase22 V2 outcomes or claims 2015-2016 broker fills.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_phase22_demo_calibration_contract import (
    MINIMUM_DISTINCT_ENTRY_ORDERS_PER_SYMBOL,
    REQUIRED_SYMBOLS,
)

STATUS = "READY"
POPULATION_RUN_ID = 36922694706
POPULATION_RUN_HEAD_SHA = "380a7ee726c97eef700ff31a1fa7839efd0436c9"
POPULATION_ARTIFACT_ID = 11192332824
POPULATION_ARTIFACT_DIGEST = (
    "sha256:049da53fe89fe5e56176b5a32771be674fafd3b94d425d4594a6a06eb149ac70"
)
EMPIRICAL_RUN_ID = 36929985176
EMPIRICAL_RUN_HEAD_SHA = "59a7e9bc6051883f7090193860546dcb3e1f3e74"
EMPIRICAL_ARTIFACT_ID = 11194919112
EMPIRICAL_ARTIFACT_DIGEST = (
    "sha256:9e20c1d1486391cc1c9e70ab4fa8b9cae7eb36bd23b8774ae70353c93a8852ab"
)
ACCOUNT_FINGERPRINT_SHA256 = (
    "17585ecd6f116a92d19919e46948f06c027d0cbf9f1cb8d97802f20055bad17b"
)
_EMPIRICAL_OBSERVED_AT = "2026-10-01T21:39:01.692605+00:00"
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class Phase22ProviderExecutionCalibrationReceipt:
    provider_key: str
    environment: str
    account_fingerprint_sha256: str
    required_symbols: tuple[str, ...]
    minimum_distinct_entry_orders_per_symbol: int
    population_run_id: int
    population_run_head_sha: str
    population_artifact_id: int
    population_artifact_digest: str
    empirical_run_id: int
    empirical_run_head_sha: str
    empirical_artifact_id: int
    empirical_artifact_digest: str
    empirical_observed_at: str
    population_entry_orders_by_symbol: tuple[tuple[str, int], ...]
    empirical_orders_by_symbol: tuple[tuple[str, int], ...]
    empirical_observation_count: int
    execution_population_ready: bool
    empirical_slippage_calibrated: bool
    execution_model_ready: bool
    created_positions_closed: bool
    minimum_volume_only: bool
    broker_mutation_performed: bool
    holdout_outcomes_used: bool
    historical_provider_economics_claimed: bool
    historical_holdout_execution_claimed: bool
    fundednext_touched: bool
    vps_touched: bool
    live_authorized: bool
    real_capital_authorized: bool
    productive_authority: bool
    blockers: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.provider_key != "ctrader-demo" or self.environment != "demo":
            raise CiboCapitalManagementError(
                "Phase22 provider execution calibration environment drift"
            )
        if (
            len(self.account_fingerprint_sha256) != 64
            or any(
                char not in "0123456789abcdef"
                for char in self.account_fingerprint_sha256
            )
        ):
            raise CiboCapitalManagementError(
                "Phase22 provider execution calibration account fingerprint invalid"
            )
        if self.required_symbols != REQUIRED_SYMBOLS:
            raise CiboCapitalManagementError(
                "Phase22 provider execution calibration symbol surface drift"
            )
        if self.minimum_distinct_entry_orders_per_symbol != (
            MINIMUM_DISTINCT_ENTRY_ORDERS_PER_SYMBOL
        ):
            raise CiboCapitalManagementError(
                "Phase22 provider execution calibration minimum drift"
            )
        for name in ("population_run_head_sha", "empirical_run_head_sha"):
            if _SHA_RE.fullmatch(getattr(self, name)) is None:
                raise CiboCapitalManagementError(
                    f"Phase22 provider execution calibration {name} invalid"
                )
        for name in ("population_artifact_digest", "empirical_artifact_digest"):
            if _DIGEST_RE.fullmatch(getattr(self, name)) is None:
                raise CiboCapitalManagementError(
                    f"Phase22 provider execution calibration {name} invalid"
                )
        for name in (
            "population_run_id",
            "population_artifact_id",
            "empirical_run_id",
            "empirical_artifact_id",
            "empirical_observation_count",
        ):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                raise CiboCapitalManagementError(
                    f"Phase22 provider execution calibration {name} invalid"
                )
        population = dict(self.population_entry_orders_by_symbol)
        empirical = dict(self.empirical_orders_by_symbol)
        if (
            tuple(name for name, _ in self.population_entry_orders_by_symbol)
            != REQUIRED_SYMBOLS
            or tuple(name for name, _ in self.empirical_orders_by_symbol)
            != REQUIRED_SYMBOLS
        ):
            raise CiboCapitalManagementError(
                "Phase22 provider execution calibration count ordering drift"
            )
        if any(
            population[symbol] < self.minimum_distinct_entry_orders_per_symbol
            or empirical[symbol] < self.minimum_distinct_entry_orders_per_symbol
            for symbol in REQUIRED_SYMBOLS
        ):
            raise CiboCapitalManagementError(
                "Phase22 provider execution calibration population below minimum"
            )
        if self.empirical_observation_count != sum(empirical.values()):
            raise CiboCapitalManagementError(
                "Phase22 provider execution calibration observation count drift"
            )
        required_true = (
            self.execution_population_ready,
            self.empirical_slippage_calibrated,
            self.execution_model_ready,
            self.created_positions_closed,
            self.minimum_volume_only,
        )
        if not all(required_true):
            raise CiboCapitalManagementError(
                "Phase22 provider execution calibration readiness incomplete"
            )
        prohibited = (
            self.broker_mutation_performed,
            self.holdout_outcomes_used,
            self.historical_provider_economics_claimed,
            self.historical_holdout_execution_claimed,
            self.fundednext_touched,
            self.vps_touched,
            self.live_authorized,
            self.real_capital_authorized,
            self.productive_authority,
        )
        if any(prohibited):
            raise CiboCapitalManagementError(
                "Phase22 provider execution calibration governance contamination"
            )
        if self.blockers:
            raise CiboCapitalManagementError(
                "Phase22 provider execution calibration READY cannot retain blockers"
            )

    def fingerprint(self) -> str:
        raw = json.dumps(
            asdict(self),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return "sha256:" + hashlib.sha256(raw).hexdigest()


PHASE22_PROVIDER_EXECUTION_CALIBRATION_RECEIPT = (
    Phase22ProviderExecutionCalibrationReceipt(
        provider_key="ctrader-demo",
        environment="demo",
        account_fingerprint_sha256=ACCOUNT_FINGERPRINT_SHA256,
        required_symbols=REQUIRED_SYMBOLS,
        minimum_distinct_entry_orders_per_symbol=(
            MINIMUM_DISTINCT_ENTRY_ORDERS_PER_SYMBOL
        ),
        population_run_id=POPULATION_RUN_ID,
        population_run_head_sha=POPULATION_RUN_HEAD_SHA,
        population_artifact_id=POPULATION_ARTIFACT_ID,
        population_artifact_digest=POPULATION_ARTIFACT_DIGEST,
        empirical_run_id=EMPIRICAL_RUN_ID,
        empirical_run_head_sha=EMPIRICAL_RUN_HEAD_SHA,
        empirical_artifact_id=EMPIRICAL_ARTIFACT_ID,
        empirical_artifact_digest=EMPIRICAL_ARTIFACT_DIGEST,
        empirical_observed_at=_EMPIRICAL_OBSERVED_AT,
        population_entry_orders_by_symbol=(
            ("AUDJPY", 12),
            ("EURUSD", 8),
            ("GBPJPY", 8),
            ("GBPUSD", 8),
            ("NAS100", 8),
            ("XAUUSD", 8),
        ),
        empirical_orders_by_symbol=(
            ("AUDJPY", 12),
            ("EURUSD", 9),
            ("GBPJPY", 8),
            ("GBPUSD", 8),
            ("NAS100", 8),
            ("XAUUSD", 8),
        ),
        empirical_observation_count=53,
        execution_population_ready=True,
        empirical_slippage_calibrated=True,
        execution_model_ready=True,
        created_positions_closed=True,
        minimum_volume_only=True,
        broker_mutation_performed=False,
        holdout_outcomes_used=False,
        historical_provider_economics_claimed=False,
        historical_holdout_execution_claimed=False,
        fundednext_touched=False,
        vps_touched=False,
        live_authorized=False,
        real_capital_authorized=False,
        productive_authority=False,
        blockers=(),
    )
)


def phase22_provider_execution_calibration_payload() -> dict[str, object]:
    receipt = PHASE22_PROVIDER_EXECUTION_CALIBRATION_RECEIPT
    return {
        "schema": "qore.cibo.phase22.provider-execution-calibration-receipt.v1",
        "status": STATUS,
        **asdict(receipt),
        "receipt_sha256": receipt.fingerprint(),
    }
