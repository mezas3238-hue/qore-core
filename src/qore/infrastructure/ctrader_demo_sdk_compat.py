from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime

from qore.infrastructure.ctrader_demo_operational_probe import (
    CTraderDemoOperationalEvidence,
    CTraderDemoOperationalObservation,
    CTraderDemoOperationalProbeInputs,
    CTraderDemoOperationalProbeValidationError,
    closed_m5_interval,
    run_ctrader_demo_closed_m5_probe,
    unix_milliseconds,
)
from qore.infrastructure.ports import ExternalPortError
from qore.kernel.result import Failure, Result, Success

_EVIDENCE_SCHEMA = "qore.ctrader-demo.sdk-closed-m5-evidence.v1"
_SUPPORTED_SDK_VERSION = "0.9.2"


def ctrader_historical_m5_query_window(started_at: datetime) -> tuple[int, int]:
    """Return inclusive provider timestamps for exactly the latest closed M5 bar."""
    opened_at, closed_at = closed_m5_interval(started_at)
    from_timestamp = unix_milliseconds(opened_at)
    to_timestamp = unix_milliseconds(closed_at) - 1
    if to_timestamp < from_timestamp:
        raise CTraderDemoOperationalProbeValidationError(
            "cTrader historical M5 query window must be non-empty"
        )
    return from_timestamp, to_timestamp


@dataclass(frozen=True, slots=True)
class CTraderDemoSdkOperationalEvidence:
    """Preserve optional SDK wire-field provenance around canonical probe evidence."""

    canonical: CTraderDemoOperationalEvidence
    sdk_package_version: str
    provider_has_more_supported: bool
    provider_has_more_explicit: bool
    provider_has_more: bool | None

    def __post_init__(self) -> None:
        if not isinstance(self.canonical, CTraderDemoOperationalEvidence):
            raise CTraderDemoOperationalProbeValidationError(
                "cTrader SDK evidence canonical value must be operational evidence"
            )
        if self.sdk_package_version != _SUPPORTED_SDK_VERSION:
            raise CTraderDemoOperationalProbeValidationError(
                "cTrader SDK evidence version must match the certified runtime version"
            )
        if type(self.provider_has_more_supported) is not bool:
            raise CTraderDemoOperationalProbeValidationError(
                "cTrader SDK evidence has_more_supported must be a strict bool"
            )
        if type(self.provider_has_more_explicit) is not bool:
            raise CTraderDemoOperationalProbeValidationError(
                "cTrader SDK evidence has_more_explicit must be a strict bool"
            )
        if not self.provider_has_more_supported and self.provider_has_more_explicit:
            raise CTraderDemoOperationalProbeValidationError(
                "unsupported cTrader SDK hasMore cannot be explicit"
            )
        if self.provider_has_more_explicit:
            if type(self.provider_has_more) is not bool:
                raise CTraderDemoOperationalProbeValidationError(
                    "explicit cTrader SDK hasMore must carry a strict bool"
                )
        elif self.provider_has_more is not None:
            raise CTraderDemoOperationalProbeValidationError(
                "absent cTrader SDK hasMore must retain None provenance"
            )

    def public_payload(self) -> dict[str, object]:
        payload = self.canonical.public_payload()
        payload["provider_has_more"] = self.provider_has_more
        payload["provider_has_more_explicit"] = self.provider_has_more_explicit
        payload["provider_has_more_supported"] = self.provider_has_more_supported
        payload["schema"] = _EVIDENCE_SCHEMA
        payload["sdk_package_version"] = self.sdk_package_version
        return payload

    def to_json(self) -> str:
        return json.dumps(self.public_payload(), sort_keys=True, separators=(",", ":"))


def run_ctrader_demo_sdk_compat_probe(
    inputs: CTraderDemoOperationalProbeInputs,
    observation: CTraderDemoOperationalObservation,
    *,
    sdk_package_version: str,
    provider_has_more_supported: bool,
    provider_has_more_explicit: bool,
    provider_has_more: bool | None,
) -> Result[CTraderDemoSdkOperationalEvidence, ExternalPortError]:
    """Run the canonical probe while preserving SDK optional-field provenance."""
    if sdk_package_version != _SUPPORTED_SDK_VERSION:
        return Failure(
            CTraderDemoOperationalProbeValidationError(
                "cTrader SDK runtime version is not certified by this delivery"
            )
        )
    if type(provider_has_more_supported) is not bool:
        return Failure(
            CTraderDemoOperationalProbeValidationError(
                "cTrader SDK has_more_supported must be a strict bool"
            )
        )
    if type(provider_has_more_explicit) is not bool:
        return Failure(
            CTraderDemoOperationalProbeValidationError(
                "cTrader SDK has_more_explicit must be a strict bool"
            )
        )
    if not provider_has_more_supported and provider_has_more_explicit:
        return Failure(
            CTraderDemoOperationalProbeValidationError(
                "unsupported cTrader SDK hasMore cannot be explicit"
            )
        )
    if provider_has_more_explicit:
        if type(provider_has_more) is not bool:
            return Failure(
                CTraderDemoOperationalProbeValidationError(
                    "explicit cTrader SDK hasMore must be a strict bool"
                )
            )
        if observation.trendbars_response.has_more is not provider_has_more:
            return Failure(
                CTraderDemoOperationalProbeValidationError(
                    "cTrader SDK hasMore bridge value must match explicit wire value"
                )
            )
    else:
        if provider_has_more is not None:
            return Failure(
                CTraderDemoOperationalProbeValidationError(
                    "absent cTrader SDK hasMore must retain None provenance"
                )
            )
        if observation.trendbars_response.has_more:
            return Failure(
                CTraderDemoOperationalProbeValidationError(
                    "absent cTrader SDK hasMore may only bridge to false"
                )
            )

    result = run_ctrader_demo_closed_m5_probe(inputs, observation)
    if isinstance(result, Failure):
        return Failure(result.error)
    try:
        evidence = CTraderDemoSdkOperationalEvidence(
            canonical=result.value,
            sdk_package_version=sdk_package_version,
            provider_has_more_supported=provider_has_more_supported,
            provider_has_more_explicit=provider_has_more_explicit,
            provider_has_more=provider_has_more,
        )
    except ExternalPortError as error:
        return Failure(error)
    return Success(evidence)
