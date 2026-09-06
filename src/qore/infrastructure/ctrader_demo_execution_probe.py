from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from re import fullmatch
from uuid import NAMESPACE_URL, UUID, uuid5

from qore.domain.events import CausationId, CorrelationId
from qore.infrastructure.connectivity import ProviderEndpoint
from qore.infrastructure.ctrader_demo_execution_codec import (
    build_ctrader_demo_order_create_plan,
)
from qore.infrastructure.ctrader_demo_execution_configuration import (
    CTraderDemoCapability,
    CTraderDemoOperationalLimits,
    CTraderDemoRuntimeConfiguration,
    CTraderSymbolMapping,
    ctrader_demo_secret_requirements,
)
from qore.infrastructure.ctrader_demo_execution_contracts import (
    CTraderDemoExecutionError,
    ctrader_demo_account_fingerprint,
)
from qore.infrastructure.execution_boundary import (
    ExecutionReceiptId,
    ExecutionRequestId,
    ExecutionSubmission,
)
from qore.infrastructure.market_test_environment import (
    MarketRuntimeEnvironment,
    MarketTestAccountIdentity,
)
from qore.infrastructure.order_intent import (
    ExecutionIdempotencyKey,
    ExecutionInstrument,
    OrderIntent,
    OrderIntentId,
    OrderQuantity,
    OrderSide,
    OrderType,
)
from qore.infrastructure.ports import (
    ExternalPortError,
    ExternalRequestMetadata,
)
from qore.infrastructure.pretrade_safety import (
    AuthorizedOrderIntent,
    ExecutionSafetySwitchSnapshot,
    ExecutionSwitchState,
    PreTradeAuthorization,
    PreTradeAuthorizationId,
    PreTradeDecision,
    PreTradePolicyId,
)
from qore.infrastructure.transport import ExternalTransportTimeout
from qore.kernel.result import Failure, Result, Success

_PROVIDER_KEY = "ctrader-demo"
_EVIDENCE_SCHEMA = "qore.ctrader-demo.execution-plan-evidence.v1"


class CTraderDemoOperationalProbeError(ExternalPortError):
    """Base error for one explicitly authorized cTrader DEMO operational probe."""

    __slots__ = ()


class CTraderDemoOperationalProbeValidationError(CTraderDemoOperationalProbeError):
    """Violation of the operational probe's DEMO-only invariants."""

    __slots__ = ()


class CTraderDemoOperationalCredentialBlockedError(CTraderDemoOperationalProbeError):
    """Typed blocker when authorized DEMO credential material is absent."""

    __slots__ = ()


def _stable_uuid(run_key: str, purpose: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"qore:ctrader-demo:{run_key}:{purpose}")


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise CTraderDemoOperationalProbeValidationError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise CTraderDemoOperationalProbeValidationError(f"{field_name} must be timezone-aware")


@dataclass(frozen=True, slots=True, repr=False)
class CTraderDemoOperationalProbeInputs:
    """Explicit external inputs for one DEMO-only execution planning probe."""

    run_key: str
    account_ref: str
    instrument: str
    side: OrderSide
    order_type: OrderType
    quantity: Decimal
    started_at: datetime
    token_material: bytes = field(repr=False, compare=False, hash=False)

    def __post_init__(self) -> None:
        if not isinstance(self.run_key, str) or fullmatch(r"[0-9]+-[0-9]+", self.run_key) is None:
            raise CTraderDemoOperationalProbeValidationError(
                "run_key must use '<run-id>-<attempt>' numeric syntax"
            )
        if not isinstance(self.account_ref, str) or not self.account_ref:
            raise CTraderDemoOperationalProbeValidationError("account_ref must be explicit")
        MarketTestAccountIdentity(
            provider_key=_PROVIDER_KEY,
            account_ref=self.account_ref,
            environment=MarketRuntimeEnvironment.DEMO,
        )
        try:
            ExecutionInstrument(self.instrument)
        except ExternalPortError as error:
            raise CTraderDemoOperationalProbeValidationError(
                "instrument must be a canonical execution instrument"
            ) from error
        if not isinstance(self.side, OrderSide):
            raise CTraderDemoOperationalProbeValidationError("side must be canonical OrderSide")
        if not isinstance(self.order_type, OrderType):
            raise CTraderDemoOperationalProbeValidationError(
                "order_type must be canonical OrderType"
            )
        if not isinstance(self.quantity, Decimal):
            raise CTraderDemoOperationalProbeValidationError("quantity must be Decimal")
        if not self.quantity.is_finite() or self.quantity <= 0:
            raise CTraderDemoOperationalProbeValidationError("quantity must be finite and positive")
        if self.order_type is OrderType.LIMIT:
            raise CTraderDemoOperationalProbeValidationError(
                "operational probe planning slice supports MARKET orders only"
            )
        _validate_timestamp(self.started_at, field_name="started_at")
        if not isinstance(self.token_material, bytes):
            raise CTraderDemoOperationalProbeValidationError("token material must be bytes")

    def __repr__(self) -> str:
        return (
            "CTraderDemoOperationalProbeInputs("
            f"run_key={self.run_key!r}, "
            f"account_ref_fingerprint={ctrader_demo_account_fingerprint(self.account_ref)!r}, "
            f"instrument={self.instrument!r}, "
            f"side={self.side.value!r}, "
            f"order_type={self.order_type.value!r}, "
            f"quantity={format(self.quantity, 'f')!r}, "
            f"started_at={self.started_at.isoformat()}, "
            "token_material=<redacted>)"
        )


@dataclass(frozen=True, slots=True)
class CTraderDemoOperationalEvidence:
    """Sanitized planning evidence; never performs a provider mutation."""

    run_key: str
    provider_key: str
    environment: str
    endpoint_host: str
    account_fingerprint: str
    instrument: str
    side: str
    order_type: str
    quantity: str
    client_msg_id: str
    symbol_id: int
    volume_units: int
    status: str

    def __post_init__(self) -> None:
        if self.provider_key != _PROVIDER_KEY:
            raise CTraderDemoOperationalProbeValidationError(
                "operational evidence provider must be ctrader-demo"
            )
        if self.environment != MarketRuntimeEnvironment.DEMO.value:
            raise CTraderDemoOperationalProbeValidationError(
                "operational evidence environment must be demo"
            )
        if self.endpoint_host != "demo.ctraderapi.com":
            raise CTraderDemoOperationalProbeValidationError(
                "operational evidence endpoint must be the cTrader DEMO host"
            )
        if self.status not in {"planned", "blocked"}:
            raise CTraderDemoOperationalProbeValidationError(
                "operational evidence status must be planned or blocked"
            )
        if not isinstance(self.symbol_id, int) or self.symbol_id <= 0:
            raise CTraderDemoOperationalProbeValidationError(
                "operational evidence symbol_id must be a positive int"
            )
        if not isinstance(self.volume_units, int) or self.volume_units <= 0:
            raise CTraderDemoOperationalProbeValidationError(
                "operational evidence volume_units must be a positive int"
            )

    def public_payload(self) -> dict[str, object]:
        return {
            "account_fingerprint": self.account_fingerprint,
            "client_msg_id": self.client_msg_id,
            "endpoint_host": self.endpoint_host,
            "environment": self.environment,
            "instrument": self.instrument,
            "order_type": self.order_type,
            "provider_key": self.provider_key,
            "quantity": self.quantity,
            "run_key": self.run_key,
            "schema": _EVIDENCE_SCHEMA,
            "side": self.side,
            "status": self.status,
            "symbol_id": self.symbol_id,
            "volume_units": self.volume_units,
        }

    def to_json(self) -> str:
        return json.dumps(self.public_payload(), sort_keys=True, separators=(",", ":"))


def _configuration(
    inputs: CTraderDemoOperationalProbeInputs,
) -> CTraderDemoRuntimeConfiguration:
    instrument = ExecutionInstrument(inputs.instrument)
    return CTraderDemoRuntimeConfiguration(
        provider_key=_PROVIDER_KEY,
        environment=MarketRuntimeEnvironment.DEMO,
        endpoint=ProviderEndpoint(host="demo.ctraderapi.com", port=5035),
        account=MarketTestAccountIdentity(
            provider_key=_PROVIDER_KEY,
            account_ref=inputs.account_ref,
            environment=MarketRuntimeEnvironment.DEMO,
        ),
        symbol_mappings=(
            CTraderSymbolMapping(
                instrument=instrument,
                symbol_id=(_stable_uuid(inputs.run_key, "symbol").int & 0x7FFFFFFF) | 1,
                symbol_name=instrument.value,
                digits=5,
                volume_step=Decimal(1),
                min_volume_units=1,
                max_volume_units=1_000_000_000,
                step_volume_units=1,
            ),
        ),
        capabilities=(
            CTraderDemoCapability.ACCOUNT,
            CTraderDemoCapability.ORDERS,
        ),
        rest_timeout=ExternalTransportTimeout(milliseconds=3000),
        limits=CTraderDemoOperationalLimits(order_requests_per_second=1),
        secret_requirements=ctrader_demo_secret_requirements(),
    )


def _metadata(run_key: str) -> ExternalRequestMetadata:
    return ExternalRequestMetadata(
        correlation_id=CorrelationId(_stable_uuid(run_key, "correlation")),
        causation_id=CausationId(_stable_uuid(run_key, "causation")),
        attributes={
            "run-key": run_key,
            "workflow": "qore-ctrader-demo-execution-operational-probe",
        },
    )


def _submission(
    inputs: CTraderDemoOperationalProbeInputs,
) -> ExecutionSubmission:
    created_at = inputs.started_at - timedelta(seconds=4)
    intent = OrderIntent(
        intent_id=OrderIntentId(_stable_uuid(inputs.run_key, "intent")),
        idempotency_key=ExecutionIdempotencyKey(_stable_uuid(inputs.run_key, "idempotency")),
        instrument=ExecutionInstrument(inputs.instrument),
        side=inputs.side,
        order_type=inputs.order_type,
        quantity=OrderQuantity(inputs.quantity),
        created_at=created_at,
        metadata=_metadata(inputs.run_key),
    )
    authorization = PreTradeAuthorization(
        authorization_id=PreTradeAuthorizationId(_stable_uuid(inputs.run_key, "authorization")),
        policy_id=PreTradePolicyId("qore.ctrader.demo.pretrade"),
        intent_id=intent.intent_id,
        decision=PreTradeDecision.APPROVED,
        evaluated_at=created_at + timedelta(seconds=1),
        expires_at=created_at + timedelta(minutes=1),
        reason="bounded ctrader demo execution planning approved",
    )
    authorized = AuthorizedOrderIntent(
        intent=intent,
        authorization=authorization,
        switch=ExecutionSafetySwitchSnapshot(
            state=ExecutionSwitchState.ENABLED,
            observed_at=created_at + timedelta(seconds=2),
            reason="demo execution switch enabled",
        ),
        authorized_at=created_at + timedelta(seconds=3),
    )
    return ExecutionSubmission(
        request_id=ExecutionRequestId(_stable_uuid(inputs.run_key, "request")),
        receipt_id=ExecutionReceiptId(_stable_uuid(inputs.run_key, "receipt")),
        authorized_intent=authorized,
        submitted_at=inputs.started_at,
    )


def run_ctrader_demo_operational_probe(
    inputs: CTraderDemoOperationalProbeInputs,
) -> Result[CTraderDemoOperationalEvidence, ExternalPortError]:
    """Build one DEMO-only secret-free execution plan without provider mutation."""
    if not isinstance(inputs, CTraderDemoOperationalProbeInputs):
        return Failure(
            CTraderDemoOperationalProbeValidationError(
                "operational probe requires CTraderDemoOperationalProbeInputs"
            )
        )
    if not inputs.token_material:
        return Failure(
            CTraderDemoOperationalCredentialBlockedError(
                "authorized cTrader DEMO credential material is absent; "
                "real DEMO write certification requires injected credentials"
            )
        )
    try:
        configuration = _configuration(inputs)
        plan_result = build_ctrader_demo_order_create_plan(
            configuration,
            _submission(inputs),
        )
    except (CTraderDemoExecutionError, ExternalPortError) as error:
        return Failure(
            CTraderDemoOperationalProbeValidationError(
                f"cTrader DEMO execution planning failed: {error}"
            )
        )
    if isinstance(plan_result, Failure):
        return Failure(plan_result.error)
    plan = plan_result.value
    try:
        evidence = CTraderDemoOperationalEvidence(
            run_key=inputs.run_key,
            provider_key=configuration.provider_key,
            environment=configuration.environment.value,
            endpoint_host=configuration.endpoint.host,
            account_fingerprint=ctrader_demo_account_fingerprint(inputs.account_ref),
            instrument=inputs.instrument,
            side=plan.side.value,
            order_type=plan.order_type.value,
            quantity=format(inputs.quantity, "f"),
            client_msg_id=plan.client_msg_id,
            symbol_id=plan.symbol_id,
            volume_units=plan.volume_units,
            status="planned",
        )
    except ExternalPortError as error:
        return Failure(error)
    return Success(evidence)


def _required_environment(name: str) -> str:
    value = os.environ.get(name)
    if value is None or not value:
        raise CTraderDemoOperationalProbeValidationError(
            f"required operational environment binding is missing: {name}"
        )
    return value


def _load_operational_inputs() -> CTraderDemoOperationalProbeInputs:
    run_key = _required_environment("QORE_PROBE_RUN_KEY")
    account_ref = _required_environment("QORE_CTRADER_DEMO_ACCOUNT_ID")
    instrument = _required_environment("QORE_CTRADER_DEMO_INSTRUMENT")
    side_raw = _required_environment("QORE_CTRADER_DEMO_SIDE")
    quantity_raw = _required_environment("QORE_CTRADER_DEMO_QUANTITY")
    started_raw = _required_environment("QORE_PROBE_STARTED_AT")
    token_raw = os.environ.get("QORE_CTRADER_DEMO_TOKEN", "")
    os.environ.pop("QORE_CTRADER_DEMO_TOKEN", None)
    try:
        started_at = datetime.fromisoformat(started_raw)
    except ValueError as error:
        raise CTraderDemoOperationalProbeValidationError(
            "QORE_PROBE_STARTED_AT must be ISO-8601"
        ) from error
    try:
        side = OrderSide(side_raw)
    except ValueError as error:
        raise CTraderDemoOperationalProbeValidationError(
            "QORE_CTRADER_DEMO_SIDE must be buy or sell"
        ) from error
    try:
        quantity = Decimal(quantity_raw)
    except InvalidOperation as error:
        raise CTraderDemoOperationalProbeValidationError(
            "QORE_CTRADER_DEMO_QUANTITY must be a decimal"
        ) from error
    token_material = token_raw.encode("ascii") if token_raw else b""
    return CTraderDemoOperationalProbeInputs(
        run_key=run_key,
        account_ref=account_ref,
        instrument=instrument,
        side=side,
        order_type=OrderType.MARKET,
        quantity=quantity,
        started_at=started_at,
        token_material=token_material,
    )


def _write_evidence(path: Path, evidence: CTraderDemoOperationalEvidence) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{evidence.to_json()}\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Plan one QORE cTrader DEMO execution (no provider mutation)."
    )
    parser.add_argument("--evidence-file", required=True)
    args = parser.parse_args(argv)
    try:
        inputs = _load_operational_inputs()
        result = run_ctrader_demo_operational_probe(inputs)
        if isinstance(result, Failure):
            print(f"QORE cTrader DEMO probe blocked: {type(result.error).__name__}: {result.error}")
            return 1
        _write_evidence(Path(args.evidence_file), result.value)
        print(
            "QORE cTrader DEMO probe planned: "
            f"instrument={result.value.instrument} "
            f"status={result.value.status}"
        )
        return 0
    except ExternalPortError as error:
        print(f"QORE cTrader DEMO probe blocked: {type(error).__name__}: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
