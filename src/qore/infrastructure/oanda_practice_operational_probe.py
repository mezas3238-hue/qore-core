from __future__ import annotations

import argparse
import hashlib
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from re import fullmatch
from uuid import NAMESPACE_URL, UUID, uuid5

from qore.domain.events import CausationId, CorrelationId
from qore.infrastructure.activation_policy import (
    ProviderActivationDecisionSnapshot,
    ProviderActivationEvaluation,
    ProviderActivationMode,
    ProviderActivationPolicy,
    ProviderActivationSecretReferences,
    evaluate_provider_activation_policy,
)
from qore.infrastructure.adapter_configuration import (
    AdapterConfigurationMode,
    ExternalAdapterConfiguration,
)
from qore.infrastructure.adapter_lifecycle import (
    AdapterLifecycleActor,
    AdapterLifecycleState,
    AdapterLifecycleTransitionReason,
    AdapterLifecycleTransitionRequest,
    apply_adapter_lifecycle_transition,
    declare_adapter_lifecycle,
)
from qore.infrastructure.connectivity import ProviderEndpoint
from qore.infrastructure.https_transport import build_stdlib_bearer_https_transport
from qore.infrastructure.market_data import Instrument, MarketDataSnapshotId, QuoteRequest
from qore.infrastructure.market_test_environment import (
    MarketRuntimeEnvironment,
    MarketTestAccountIdentity,
)
from qore.infrastructure.oanda_practice_configuration import (
    OandaPracticeCapability,
    OandaPracticeOperationalLimits,
    OandaPracticeRuntimeConfiguration,
    oanda_practice_secret_requirements,
)
from qore.infrastructure.oanda_practice_credentials import (
    OandaPracticeCredentialActivation,
    activate_oanda_practice_credentials,
)
from qore.infrastructure.oanda_practice_market_feed import (
    build_oanda_practice_market_data_flow,
    compose_oanda_practice_read_only_provider,
)
from qore.infrastructure.ports import (
    AdapterId,
    ExternalPortError,
    ExternalRequestMetadata,
    ExternalSourceDescriptor,
    PortName,
    SourceId,
)
from qore.infrastructure.providers import (
    ProviderCapability,
    ProviderCapabilitySet,
    ProviderDescriptor,
    ProviderEnablement,
    ProviderId,
    ProviderName,
)
from qore.infrastructure.secret_resolution import (
    MappingSecretMaterialResolver,
    SecretAuthenticatedTransportBoundary,
)
from qore.infrastructure.secrets import SecretExternalReference, SecretRef, SecretRefId
from qore.infrastructure.transport import ExternalTransportTimeout
from qore.kernel.result import Failure, Result, Success

_ALLOWED_INSTRUMENTS = ("EUR_USD", "GBP_USD")
_SECRET_REFERENCE = SecretExternalReference("oanda/practice/personal-access-token")
_EVIDENCE_SCHEMA = "qore.oanda-practice.market-feed-evidence.v1"


class OandaPracticeOperationalProbeError(ExternalPortError):
    """Base error for one explicitly authorized OANDA Practice operational probe."""

    __slots__ = ()


class OandaPracticeOperationalProbeValidationError(OandaPracticeOperationalProbeError):
    """Violation of the operational probe's Practice-only invariants."""

    __slots__ = ()


def _validate_explicit_datetime(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise OandaPracticeOperationalProbeValidationError(
            f"{field_name} must be a datetime"
        )
    if value.tzinfo is None or value.utcoffset() is None:
        raise OandaPracticeOperationalProbeValidationError(
            f"{field_name} must be timezone-aware"
        )


def _stable_uuid(run_key: str, purpose: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"qore:oanda-practice:{run_key}:{purpose}")


def _account_fingerprint(account_ref: str) -> str:
    digest = hashlib.sha256(account_ref.encode("utf-8")).hexdigest()
    return f"sha256:{digest[:24]}"


@dataclass(frozen=True, slots=True, repr=False)
class OandaPracticeOperationalProbeInputs:
    """Explicit external inputs for one read-only Practice pricing probe."""

    run_key: str
    account_ref: str
    instrument: str
    token_material: bytes = field(repr=False, compare=False, hash=False)
    started_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.run_key, str) or fullmatch(r"[0-9]+-[0-9]+", self.run_key) is None:
            raise OandaPracticeOperationalProbeValidationError(
                "run_key must use '<run-id>-<attempt>' numeric syntax"
            )
        if not isinstance(self.account_ref, str) or not self.account_ref:
            raise OandaPracticeOperationalProbeValidationError(
                "account_ref must be explicit"
            )
        if self.instrument not in _ALLOWED_INSTRUMENTS:
            raise OandaPracticeOperationalProbeValidationError(
                "instrument must be an approved OANDA Practice symbol"
            )
        if not isinstance(self.token_material, bytes) or not self.token_material:
            raise OandaPracticeOperationalProbeValidationError(
                "Practice token material must be non-empty bytes"
            )
        _validate_explicit_datetime(self.started_at, field_name="started_at")
        MarketTestAccountIdentity(
            provider_key="oanda-v20",
            account_ref=self.account_ref,
            environment=MarketRuntimeEnvironment.DEMO,
        )

    def __repr__(self) -> str:
        return (
            "OandaPracticeOperationalProbeInputs("
            f"run_key={self.run_key!r}, "
            f"account_ref_fingerprint={_account_fingerprint(self.account_ref)!r}, "
            f"instrument={self.instrument!r}, "
            f"started_at={self.started_at.isoformat()}, "
            "token_material=<redacted>)"
        )


@dataclass(frozen=True, slots=True)
class OandaPracticeOperationalEvidence:
    """Sanitized proof that one canonical quote traversed the real Practice path."""

    run_key: str
    provider_key: str
    environment: str
    endpoint_host: str
    account_fingerprint: str
    instrument: str
    snapshot_id: UUID
    observed_at: datetime
    bid: float
    ask: float

    def __post_init__(self) -> None:
        if self.provider_key != "oanda-v20":
            raise OandaPracticeOperationalProbeValidationError(
                "operational evidence provider must be oanda-v20"
            )
        if self.environment != MarketRuntimeEnvironment.DEMO.value:
            raise OandaPracticeOperationalProbeValidationError(
                "operational evidence environment must be demo"
            )
        if self.endpoint_host != "api-fxpractice.oanda.com":
            raise OandaPracticeOperationalProbeValidationError(
                "operational evidence endpoint must be OANDA Practice"
            )
        if self.instrument not in _ALLOWED_INSTRUMENTS:
            raise OandaPracticeOperationalProbeValidationError(
                "operational evidence instrument must be allowlisted"
            )
        if not isinstance(self.snapshot_id, UUID):
            raise OandaPracticeOperationalProbeValidationError(
                "operational evidence snapshot_id must be UUID"
            )
        _validate_explicit_datetime(self.observed_at, field_name="observed_at")
        if type(self.bid) is not float or type(self.ask) is not float:
            raise OandaPracticeOperationalProbeValidationError(
                "operational evidence bid and ask must be floats"
            )
        if self.bid <= 0.0 or self.ask <= 0.0 or self.bid > self.ask:
            raise OandaPracticeOperationalProbeValidationError(
                "operational evidence prices must form a valid positive quote"
            )

    def public_payload(self) -> dict[str, object]:
        """Return stable evidence safe for logs/artifacts; account and token stay hidden."""
        return {
            "account_fingerprint": self.account_fingerprint,
            "ask": self.ask,
            "bid": self.bid,
            "endpoint_host": self.endpoint_host,
            "environment": self.environment,
            "instrument": self.instrument,
            "observed_at": self.observed_at.isoformat(),
            "provider_key": self.provider_key,
            "run_key": self.run_key,
            "schema": _EVIDENCE_SCHEMA,
            "snapshot_id": str(self.snapshot_id),
            "status": "success",
        }

    def to_json(self) -> str:
        return json.dumps(self.public_payload(), sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True, slots=True)
class FixedOperationalProbeClock:
    """Explicit clock used by one probe; the caller supplies its timestamp."""

    value: datetime

    def __post_init__(self) -> None:
        _validate_explicit_datetime(self.value, field_name="clock value")

    def now(self) -> datetime:
        return self.value


def _configuration(inputs: OandaPracticeOperationalProbeInputs) -> OandaPracticeRuntimeConfiguration:
    return OandaPracticeRuntimeConfiguration(
        provider_key="oanda-v20",
        environment=MarketRuntimeEnvironment.DEMO,
        rest_endpoint=ProviderEndpoint(host="api-fxpractice.oanda.com"),
        streaming_endpoint=ProviderEndpoint(host="stream-fxpractice.oanda.com"),
        account=MarketTestAccountIdentity(
            provider_key="oanda-v20",
            account_ref=inputs.account_ref,
            environment=MarketRuntimeEnvironment.DEMO,
        ),
        symbols=_ALLOWED_INSTRUMENTS,
        capabilities=(
            OandaPracticeCapability.ACCOUNT,
            OandaPracticeCapability.ORDERS,
            OandaPracticeCapability.PRICING,
            OandaPracticeCapability.TRANSACTIONS,
        ),
        rest_timeout=ExternalTransportTimeout(milliseconds=3000),
        stream_connect_timeout=ExternalTransportTimeout(milliseconds=5000),
        limits=OandaPracticeOperationalLimits(
            rest_requests_per_second=1,
            active_streams=0,
            new_connections_per_second=1,
        ),
        secret_requirements=oanda_practice_secret_requirements(),
    )


def _provider(run_key: str) -> ProviderDescriptor:
    return ProviderDescriptor(
        provider_id=ProviderId(_stable_uuid(run_key, "provider")),
        provider_name=ProviderName("oanda-v20"),
        enablement=ProviderEnablement.READ_ONLY,
        capabilities=ProviderCapabilitySet(
            (ProviderCapability.HEALTH, ProviderCapability.MARKET_DATA_READ)
        ),
    )


def _source(run_key: str) -> ExternalSourceDescriptor:
    return ExternalSourceDescriptor(
        adapter_id=AdapterId(_stable_uuid(run_key, "adapter")),
        source_id=SourceId(_stable_uuid(run_key, "source")),
        port_name=PortName("market-data.oanda-practice"),
    )


def _metadata(run_key: str) -> ExternalRequestMetadata:
    return ExternalRequestMetadata(
        correlation_id=CorrelationId(_stable_uuid(run_key, "correlation")),
        causation_id=CausationId(_stable_uuid(run_key, "causation")),
        attributes={
            "run-key": run_key,
            "workflow": "mission-03-oanda-practice-operational-probe",
        },
    )


def _secret_ref(
    configuration: OandaPracticeRuntimeConfiguration,
    run_key: str,
) -> SecretRef:
    return SecretRef(
        ref_id=SecretRefId(_stable_uuid(run_key, "secret-ref")),
        name=configuration.secret_requirements.requirements[0].name,
        external_reference=_SECRET_REFERENCE,
        metadata={
            "account-ref": configuration.account.account_ref,
            "environment": configuration.environment.value,
            "provider": configuration.provider_key,
        },
    )


def _activation(
    configuration: OandaPracticeRuntimeConfiguration,
    *,
    run_key: str,
    started_at: datetime,
    secret_ref: SecretRef,
) -> Result[ProviderActivationDecisionSnapshot, ExternalPortError]:
    provider = _provider(run_key)
    source = _source(run_key)
    metadata = _metadata(run_key)
    adapter_configuration = ExternalAdapterConfiguration(
        provider=provider,
        source=source,
        mode=AdapterConfigurationMode.READ_ONLY,
        secret_requirements=configuration.secret_requirements,
    )
    declared = declare_adapter_lifecycle(
        descriptor=source,
        provider=provider,
        declared_at=started_at - timedelta(seconds=4),
        actor=AdapterLifecycleActor("mission03.operational-probe"),
        metadata=metadata,
    )
    if isinstance(declared, Failure):
        return Failure(declared.error)
    lifecycle = declared.value
    for offset, state, reason in (
        (
            3,
            AdapterLifecycleState.CONFIGURED,
            AdapterLifecycleTransitionReason.CONFIGURATION_ACCEPTED,
        ),
        (
            2,
            AdapterLifecycleState.INITIALIZED,
            AdapterLifecycleTransitionReason.INITIALIZE_REQUESTED,
        ),
    ):
        transition = apply_adapter_lifecycle_transition(
            lifecycle,
            AdapterLifecycleTransitionRequest(
                to_state=state,
                reason=reason,
                transitioned_at=started_at - timedelta(seconds=offset),
                actor=AdapterLifecycleActor("mission03.operational-probe"),
                metadata=metadata,
            ),
        )
        if isinstance(transition, Failure):
            return Failure(transition.error)
        lifecycle = transition.value
    evaluated = evaluate_provider_activation_policy(
        ProviderActivationEvaluation(
            policy=ProviderActivationPolicy(
                provider=provider,
                source=source,
                mode=ProviderActivationMode.READ_ONLY,
                required_capabilities=(ProviderCapability.MARKET_DATA_READ,),
            ),
            configuration=adapter_configuration,
            lifecycle=lifecycle,
            secrets=ProviderActivationSecretReferences((secret_ref,)),
            evaluated_at=started_at - timedelta(seconds=1),
            metadata=metadata,
        )
    )
    if isinstance(evaluated, Failure):
        return Failure(evaluated.error)
    if not evaluated.value.can_activate:
        return Failure(
            OandaPracticeOperationalProbeValidationError(
                "Practice operational probe activation must be explicitly allowed"
            )
        )
    return Success(evaluated.value)


def _credential(
    configuration: OandaPracticeRuntimeConfiguration,
    inputs: OandaPracticeOperationalProbeInputs,
    *,
    secret_ref: SecretRef,
) -> Result[OandaPracticeCredentialActivation, ExternalPortError]:
    resolved = activate_oanda_practice_credentials(
        configuration,
        secret_ref,
        resolver=MappingSecretMaterialResolver(
            {_SECRET_REFERENCE: inputs.token_material}
        ),
        metadata=_metadata(inputs.run_key),
        activated_at=inputs.started_at,
    )
    if isinstance(resolved, Failure):
        return Failure(resolved.error)
    return Success(resolved.value)


def run_oanda_practice_quote_probe(
    inputs: OandaPracticeOperationalProbeInputs,
    *,
    authenticated_transport: SecretAuthenticatedTransportBoundary,
) -> Result[OandaPracticeOperationalEvidence, ExternalPortError]:
    """Execute one read-only Practice quote through the canonical ingestion path."""
    if not isinstance(inputs, OandaPracticeOperationalProbeInputs):
        return Failure(
            OandaPracticeOperationalProbeValidationError(
                "operational probe requires OandaPracticeOperationalProbeInputs"
            )
        )
    try:
        configuration = _configuration(inputs)
        secret_ref = _secret_ref(configuration, inputs.run_key)
    except ExternalPortError as error:
        return Failure(error)
    activation = _activation(
        configuration,
        run_key=inputs.run_key,
        started_at=inputs.started_at,
        secret_ref=secret_ref,
    )
    if isinstance(activation, Failure):
        return activation
    credential = _credential(configuration, inputs, secret_ref=secret_ref)
    if isinstance(credential, Failure):
        return credential
    provider = compose_oanda_practice_read_only_provider(
        configuration=configuration,
        credential=credential.value,
        activation=activation.value,
        authenticated_transport=authenticated_transport,
    )
    if isinstance(provider, Failure):
        return Failure(provider.error)
    flow = build_oanda_practice_market_data_flow(
        provider=provider.value,
        configuration=configuration,
        resolved_at=inputs.started_at,
    )
    if isinstance(flow, Failure):
        return Failure(flow.error)
    snapshot_id = MarketDataSnapshotId(_stable_uuid(inputs.run_key, "quote-snapshot"))
    quote = flow.value.read_quote(
        QuoteRequest(Instrument(inputs.instrument)),
        snapshot_id=snapshot_id,
        metadata=_metadata(inputs.run_key),
    )
    if isinstance(quote, Failure):
        return Failure(quote.error)
    snapshot = quote.value
    try:
        evidence = OandaPracticeOperationalEvidence(
            run_key=inputs.run_key,
            provider_key=configuration.provider_key,
            environment=configuration.environment.value,
            endpoint_host=configuration.rest_endpoint.host,
            account_fingerprint=_account_fingerprint(inputs.account_ref),
            instrument=snapshot.instrument.symbol,
            snapshot_id=snapshot.snapshot_id.value,
            observed_at=snapshot.observed_at,
            bid=snapshot.bid,
            ask=snapshot.ask,
        )
    except ExternalPortError as error:
        return Failure(error)
    return Success(evidence)


def _required_environment(name: str) -> str:
    value = os.environ.get(name)
    if value is None or not value:
        raise OandaPracticeOperationalProbeValidationError(
            f"required operational environment binding is missing: {name}"
        )
    return value


def _load_operational_inputs() -> OandaPracticeOperationalProbeInputs:
    run_key = _required_environment("QORE_PROBE_RUN_KEY")
    account_ref = _required_environment("QORE_OANDA_PRACTICE_ACCOUNT_ID")
    instrument = _required_environment("QORE_OANDA_PRACTICE_INSTRUMENT")
    started_raw = _required_environment("QORE_PROBE_STARTED_AT")
    token_raw = _required_environment("QORE_OANDA_PRACTICE_TOKEN")
    os.environ.pop("QORE_OANDA_PRACTICE_TOKEN", None)
    try:
        started_at = datetime.fromisoformat(started_raw)
    except ValueError as error:
        raise OandaPracticeOperationalProbeValidationError(
            "QORE_PROBE_STARTED_AT must be ISO-8601"
        ) from error
    try:
        token_material = token_raw.encode("ascii")
    except UnicodeEncodeError as error:
        raise OandaPracticeOperationalProbeValidationError(
            "Practice token material must be ASCII"
        ) from error
    return OandaPracticeOperationalProbeInputs(
        run_key=run_key,
        account_ref=account_ref,
        instrument=instrument,
        token_material=token_material,
        started_at=started_at,
    )


def _write_evidence(path: Path, evidence: OandaPracticeOperationalEvidence) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{evidence.to_json()}\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Execute one QORE OANDA fxTrade Practice read-only market-data probe."
    )
    parser.add_argument("--evidence-file", required=True)
    args = parser.parse_args(argv)
    try:
        inputs = _load_operational_inputs()
        transport = build_stdlib_bearer_https_transport(
            clock=FixedOperationalProbeClock(inputs.started_at)
        )
        result = run_oanda_practice_quote_probe(
            inputs,
            authenticated_transport=transport,
        )
        if isinstance(result, Failure):
            print(
                "QORE OANDA Practice probe failed: "
                f"{type(result.error).__name__}: {result.error}"
            )
            return 1
        _write_evidence(Path(args.evidence_file), result.value)
        print(
            "QORE OANDA Practice probe succeeded: "
            f"instrument={result.value.instrument} "
            f"observed_at={result.value.observed_at.isoformat()}"
        )
        return 0
    except (OandaPracticeOperationalProbeError, ExternalPortError) as error:
        print(f"QORE OANDA Practice probe blocked: {type(error).__name__}: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
