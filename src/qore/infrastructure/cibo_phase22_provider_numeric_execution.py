"""Pre-outcome provider-account lineage and numeric USD execution model.

The model is derived only from already-sealed cTrader DEMO provider terms plus
the empirical Phase22 execution-calibration artifact. It does not read holdout
market data or outcomes and never relabels current provider observations as
historical fills.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_provider_economics_evidence import (
    CURRENT_CTRADER_DEMO_PROVIDER_ECONOMICS,
)
from qore.infrastructure.cibo_phase22_provider_execution_calibration_receipt import (
    PHASE22_PROVIDER_EXECUTION_CALIBRATION_RECEIPT,
)

_FROZEN_PROVIDER_ACCOUNT_FINGERPRINT = (
    "70d38b13a2afb1ada12883a486ddb39aa0626e4c262b69ee44410bb6531d6086"
)
_REQUIRED_SYMBOLS = (
    "AUDJPY",
    "EURUSD",
    "GBPJPY",
    "GBPUSD",
    "NAS100",
    "XAUUSD",
)
_NATIVE_VOLUME_QUANTUM = Decimal("0.01")
_BPS = Decimal("10000")


@dataclass(frozen=True, slots=True)
class Phase22ProviderAccountLineageReceipt:
    provider_key: str
    legacy_account_fingerprint_sha256: str
    phase22_account_fingerprint_sha256: str
    same_account_proven: bool
    broker_mutation_performed: bool = False
    holdout_outcomes_used: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if self.provider_key != "ctrader-demo":
            raise CiboCapitalManagementError(
                "Phase22 provider lineage provider drift"
            )
        expected = (
            _FROZEN_PROVIDER_ACCOUNT_FINGERPRINT,
            PHASE22_PROVIDER_EXECUTION_CALIBRATION_RECEIPT.account_fingerprint_sha256,
        )
        observed = (
            self.legacy_account_fingerprint_sha256,
            self.phase22_account_fingerprint_sha256,
        )
        if observed != expected or not self.same_account_proven:
            raise CiboCapitalManagementError(
                "Phase22 provider account lineage is not proven"
            )
        if (
            self.broker_mutation_performed
            or self.holdout_outcomes_used
            or self.productive_authority
        ):
            raise CiboCapitalManagementError(
                "Phase22 provider lineage governance contamination"
            )

    def payload(self) -> dict[str, object]:
        return asdict(self)

    def fingerprint(self) -> str:
        raw = json.dumps(
            self.payload(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return "sha256:" + hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True, slots=True)
class Phase22ProviderNumericExecutionSpec:
    qore_symbol: str
    provider_symbol: str
    observed_at: datetime
    bid: Decimal
    ask: Decimal
    display_digits: int
    contract_size_per_volume: Decimal
    minimum_volume: Decimal
    maximum_volume: Decimal
    volume_step: Decimal
    margin_per_volume_usd: Decimal
    commission_per_volume_usd: Decimal
    worst_adverse_slippage_bps: Decimal
    quote_to_usd: Decimal
    usd_value_per_price_unit_per_volume: Decimal
    derived_price_quantum: Decimal
    derived_value_per_quantum_usd: Decimal
    source_provider_terms_artifact_sha256: str
    source_empirical_execution_artifact_sha256: str
    derivation_kind: str = "PROVIDER_TERMS_PLUS_EMPIRICAL_EXECUTION_V1"
    historical_exact_claimed: bool = False
    holdout_outcomes_used: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if self.qore_symbol not in _REQUIRED_SYMBOLS or not self.provider_symbol:
            raise CiboCapitalManagementError(
                "Phase22 provider numeric symbol drift"
            )
        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise CiboCapitalManagementError(
                "Phase22 provider numeric observed_at must be aware"
            )
        for name in (
            "bid",
            "ask",
            "contract_size_per_volume",
            "minimum_volume",
            "maximum_volume",
            "volume_step",
            "margin_per_volume_usd",
            "quote_to_usd",
            "usd_value_per_price_unit_per_volume",
            "derived_price_quantum",
            "derived_value_per_quantum_usd",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value <= 0
            ):
                raise CiboCapitalManagementError(
                    f"Phase22 provider numeric {name} invalid"
                )
        for name in ("commission_per_volume_usd", "worst_adverse_slippage_bps"):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value < 0
            ):
                raise CiboCapitalManagementError(
                    f"Phase22 provider numeric {name} invalid"
                )
        if self.ask < self.bid or self.maximum_volume < self.minimum_volume:
            raise CiboCapitalManagementError(
                "Phase22 provider numeric bounds invalid"
            )
        if type(self.display_digits) is not int or self.display_digits <= 0:
            raise CiboCapitalManagementError(
                "Phase22 provider numeric digits invalid"
            )
        if self.derivation_kind != "PROVIDER_TERMS_PLUS_EMPIRICAL_EXECUTION_V1":
            raise CiboCapitalManagementError(
                "Phase22 provider numeric derivation drift"
            )
        for value in (
            self.source_provider_terms_artifact_sha256,
            self.source_empirical_execution_artifact_sha256,
        ):
            if not value.startswith("sha256:") or len(value) != 71:
                raise CiboCapitalManagementError(
                    "Phase22 provider numeric source digest invalid"
                )
        if (
            self.historical_exact_claimed
            or self.holdout_outcomes_used
            or self.productive_authority
        ):
            raise CiboCapitalManagementError(
                "Phase22 provider numeric governance contamination"
            )

    def payload(self) -> dict[str, object]:
        payload = asdict(self)
        payload["observed_at"] = self.observed_at.isoformat()
        for name, value in tuple(payload.items()):
            if isinstance(value, Decimal):
                payload[name] = format(value, "f")
        return payload


def build_account_lineage_receipt(account_ref: str) -> Phase22ProviderAccountLineageReceipt:
    if not isinstance(account_ref, str) or not account_ref:
        raise CiboCapitalManagementError(
            "Phase22 provider lineage account ref required"
        )
    legacy = hashlib.sha256(account_ref.encode("utf-8")).hexdigest()
    phase22 = hashlib.sha256(
        f"ctrader-demo:{account_ref}".encode()
    ).hexdigest()
    return Phase22ProviderAccountLineageReceipt(
        provider_key="ctrader-demo",
        legacy_account_fingerprint_sha256=legacy,
        phase22_account_fingerprint_sha256=phase22,
        same_account_proven=(
            legacy == _FROZEN_PROVIDER_ACCOUNT_FINGERPRINT
            and phase22
            == PHASE22_PROVIDER_EXECUTION_CALIBRATION_RECEIPT.account_fingerprint_sha256
        ),
    )


def _decimal(value: object, name: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except Exception as error:
        raise CiboCapitalManagementError(
            f"Phase22 provider numeric {name} invalid"
        ) from error
    if not result.is_finite():
        raise CiboCapitalManagementError(
            f"Phase22 provider numeric {name} must be finite"
        )
    return result


def _provider_mid(row: dict[str, Any]) -> Decimal:
    return (_decimal(row["bid"], "bid") + _decimal(row["ask"], "ask")) / 2


def _margin_per_volume(row: dict[str, Any]) -> Decimal:
    lot_size = int(row["lot_size_cents"])
    matches = [
        item
        for item in row["expected_margin"]
        if int(item["native_volume_cents"]) == lot_size
    ]
    if len(matches) != 1:
        raise CiboCapitalManagementError(
            "Phase22 provider numeric one-volume margin quote missing"
        )
    item = matches[0]
    return max(
        _decimal(item["buy_margin_usd"], "buy_margin_usd"),
        _decimal(item["sell_margin_usd"], "sell_margin_usd"),
    )


def build_numeric_execution_specs(
    *,
    provider_terms_payload: dict[str, Any],
    empirical_execution_payload: dict[str, Any],
    account_lineage: Phase22ProviderAccountLineageReceipt,
) -> tuple[Phase22ProviderNumericExecutionSpec, ...]:
    if not isinstance(account_lineage, Phase22ProviderAccountLineageReceipt):
        raise CiboCapitalManagementError(
            "Phase22 provider numeric lineage receipt required"
        )
    if provider_terms_payload.get("provider_key") != "ctrader-demo":
        raise CiboCapitalManagementError(
            "Phase22 provider numeric provider terms drift"
        )
    if empirical_execution_payload.get("provider_key") != "ctrader-demo":
        raise CiboCapitalManagementError(
            "Phase22 provider numeric empirical provider drift"
        )
    if (
        provider_terms_payload.get("historical_exact_claimed") is not False
        or provider_terms_payload.get("holdout_outcomes_used") is not False
        or empirical_execution_payload.get("historical_2017_exact_claimed")
        is not False
        or empirical_execution_payload.get("holdout_outcomes_used") is not False
        or empirical_execution_payload.get("execution_model_ready") is not True
        or empirical_execution_payload.get("empirical_slippage_calibrated")
        is not True
    ):
        raise CiboCapitalManagementError(
            "Phase22 provider numeric source governance/readiness invalid"
        )
    symbols = provider_terms_payload.get("symbols")
    if not isinstance(symbols, dict) or tuple(sorted(symbols)) != _REQUIRED_SYMBOLS:
        raise CiboCapitalManagementError(
            "Phase22 provider numeric term surface drift"
        )
    summaries_raw = empirical_execution_payload.get("summaries")
    if not isinstance(summaries_raw, list):
        raise CiboCapitalManagementError(
            "Phase22 provider numeric empirical summaries missing"
        )
    summaries = {
        str(item["qore_symbol"]): item
        for item in summaries_raw
        if isinstance(item, dict)
    }
    if tuple(sorted(summaries)) != _REQUIRED_SYMBOLS:
        raise CiboCapitalManagementError(
            "Phase22 provider numeric empirical surface drift"
        )

    gbpusd_mid = _provider_mid(symbols["GBPUSD"])
    gbpjpy_mid = _provider_mid(symbols["GBPJPY"])
    jpy_to_usd = gbpusd_mid / gbpjpy_mid
    if jpy_to_usd <= 0:
        raise CiboCapitalManagementError(
            "Phase22 provider numeric JPY/USD cross invalid"
        )

    provider_digest = "sha256:" + CURRENT_CTRADER_DEMO_PROVIDER_ECONOMICS.artifact_sha256
    empirical_digest = (
        PHASE22_PROVIDER_EXECUTION_CALIBRATION_RECEIPT.empirical_artifact_digest
    )
    specs: list[Phase22ProviderNumericExecutionSpec] = []
    for symbol in _REQUIRED_SYMBOLS:
        row = symbols[symbol]
        summary = summaries[symbol]
        lot_size_cents = Decimal(str(row["lot_size_cents"]))
        if lot_size_cents <= 0:
            raise CiboCapitalManagementError(
                "Phase22 provider numeric lot size invalid"
            )
        contract_size = lot_size_cents * _NATIVE_VOLUME_QUANTUM
        minimum_volume = (
            Decimal(str(row["min_volume_cents"])) / lot_size_cents
        )
        maximum_volume = (
            Decimal(str(row["max_volume_cents"])) / lot_size_cents
        )
        volume_step = (
            Decimal(str(row["step_volume_cents"])) / lot_size_cents
        )
        if symbol in {"AUDJPY", "GBPJPY"}:
            quote_to_usd = jpy_to_usd
        else:
            quote_to_usd = Decimal(1)

        mean_commission = _decimal(
            summary["mean_commission_usd"],
            "mean_commission_usd",
        )
        commission_per_volume = mean_commission / minimum_volume
        worst_bps = _decimal(
            summary["worst_adverse_slippage_bps"],
            "worst_adverse_slippage_bps",
        )
        digits = int(row["digits"])
        price_quantum = Decimal(1).scaleb(-digits)
        value_per_price_unit = contract_size * quote_to_usd
        value_per_quantum = value_per_price_unit * price_quantum
        specs.append(
            Phase22ProviderNumericExecutionSpec(
                qore_symbol=symbol,
                provider_symbol=str(row["provider_symbol"]),
                observed_at=datetime.fromisoformat(str(row["observed_at"])),
                bid=_decimal(row["bid"], "bid"),
                ask=_decimal(row["ask"], "ask"),
                display_digits=digits,
                contract_size_per_volume=contract_size,
                minimum_volume=minimum_volume,
                maximum_volume=maximum_volume,
                volume_step=volume_step,
                margin_per_volume_usd=_margin_per_volume(row),
                commission_per_volume_usd=commission_per_volume,
                worst_adverse_slippage_bps=worst_bps,
                quote_to_usd=quote_to_usd,
                usd_value_per_price_unit_per_volume=value_per_price_unit,
                derived_price_quantum=price_quantum,
                derived_value_per_quantum_usd=value_per_quantum,
                source_provider_terms_artifact_sha256=provider_digest,
                source_empirical_execution_artifact_sha256=empirical_digest,
            )
        )
    return tuple(specs)


def load_json_object(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise CiboCapitalManagementError(
            "Phase22 provider numeric JSON object required"
        )
    return raw


def numeric_spec_freeze_payload(
    *,
    specs: tuple[Phase22ProviderNumericExecutionSpec, ...],
    account_lineage: Phase22ProviderAccountLineageReceipt,
) -> dict[str, object]:
    if tuple(item.qore_symbol for item in specs) != _REQUIRED_SYMBOLS:
        raise CiboCapitalManagementError(
            "Phase22 provider numeric ordered surface drift"
        )
    return {
        "schema": "qore.cibo.phase22.provider-numeric-execution-freeze.v1",
        "status": "READY",
        "account_lineage": account_lineage.payload(),
        "account_lineage_sha256": account_lineage.fingerprint(),
        "specs": [item.payload() for item in specs],
        "provider_terms_artifact_id": (
            CURRENT_CTRADER_DEMO_PROVIDER_ECONOMICS.artifact_id
        ),
        "provider_terms_artifact_sha256": (
            "sha256:" + CURRENT_CTRADER_DEMO_PROVIDER_ECONOMICS.artifact_sha256
        ),
        "empirical_execution_artifact_id": (
            PHASE22_PROVIDER_EXECUTION_CALIBRATION_RECEIPT.empirical_artifact_id
        ),
        "empirical_execution_artifact_sha256": (
            PHASE22_PROVIDER_EXECUTION_CALIBRATION_RECEIPT.empirical_artifact_digest
        ),
        "holdout_market_data_read": False,
        "holdout_outcomes_used": False,
        "broker_mutation_performed": False,
        "historical_provider_economics_claimed": False,
        "productive_authority": False,
    }
