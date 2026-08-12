from __future__ import annotations

import json
from dataclasses import dataclass

from qore.infrastructure.ctrader_demo_operational_probe import (
    CTraderDemoOperationalEvidence,
    CTraderDemoOperationalObservation,
    CTraderDemoOperationalProbeInputs,
    CTraderDemoOperationalProbeValidationError,
    run_ctrader_demo_closed_m5_probe,
)
from qore.infrastructure.ports import ExternalPortError
from qore.kernel.result import Failure, Result, Success

_EVIDENCE_SCHEMA = "qore.ctrader-demo.sdk-closed-m5-evidence.v1"


@dataclass(frozen=True, slots=True)
class CTraderDemoSdkOperationalEvidence:
    """Preserve optional SDK wire-field provenance around canonical probe evidence."""

    canonical: CTraderDemoOperationalEvidence
    provider_has_more_explicit: bool
    provider_has_more: bool | None

    def __post_init__(self) -> None:
        if not isinstance(self.canonical, CTraderDemoOperationalEvidence):
            raise CTraderDemoOperationalProbeValidationError(
                "cTrader SDK evidence canonical value must be operational evidence"
            )
        if type(self.provider_has_more_explicit) is not bool:
            raise CTraderDemoOperationalProbeValidationError(
                "cTrader SDK evidence has_more_explicit must be a strict bool"
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
        payload["schema"] = _EVIDENCE_SCHEMA
        return payload

    def to_json(self) -> str:
        return json.dumps(self.public_payload(), sort_keys=True, separators=(",", ":"))


def run_ctrader_demo_sdk_compat_probe(
    inputs: CTraderDemoOperationalProbeInputs,
    observation: CTraderDemoOperationalObservation,
    *,
    provider_has_more_explicit: bool,
    provider_has_more: bool | None,
) -> Result[CTraderDemoSdkOperationalEvidence, ExternalPortError]:
    """Run the canonical probe while preserving SDK 0.9.2 optional-field absence."""
    if type(provider_has_more_explicit) is not bool:
        return Failure(
            CTraderDemoOperationalProbeValidationError(
                "cTrader SDK has_more_explicit must be a strict bool"
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
            provider_has_more_explicit=provider_has_more_explicit,
            provider_has_more=provider_has_more,
        )
    except ExternalPortError as error:
        return Failure(error)
    return Success(evidence)
