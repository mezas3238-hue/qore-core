"""Chronological transition-uncertainty calibration for GEN-C10 research.

This module does not mutate the frozen GEN-C10 V1 semantic identity. It builds
descriptive, provider-bound empirical transition support from legally observed
chronological twin transitions. The output is evidence for a future successor
identity only; it is not a market-probability model and grants no authority.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from qore.infrastructure.cibo_compound_capital import CiboCompoundCapitalError

GENC10_TRANSITION_CALIBRATION_ID = (
    "CIBO_GENC10_TRANSITION_UNCERTAINTY_CALIBRATION_V1"
)


class Genc10TransitionEvidenceKind(StrEnum):
    FORWARD_OBSERVED = "FORWARD_OBSERVED"
    SYNTHETIC_CONTRACT = "SYNTHETIC_CONTRACT"
    BURNED_RESEARCH = "BURNED_RESEARCH"
    SEALED_HOLDOUT = "SEALED_HOLDOUT"


@dataclass(frozen=True, slots=True)
class Genc10ObservedTransition:
    transition_id: str
    account_identity_fingerprint: str
    conditioning_key: str
    start_twin_sha256: str
    end_twin_sha256: str
    provider_registry_sha256: str
    observed_start_at: datetime
    observed_end_at: datetime
    realized_capital_delta_usd: Decimal
    compound_value_delta_usd: Decimal
    protected_floor_delta_usd: Decimal
    stop_risk_capacity_delta_usd: Decimal
    stop_risk_usage_delta_usd: Decimal
    margin_capacity_delta_usd: Decimal
    margin_usage_delta_usd: Decimal
    active_deployment_count_delta: int
    known_option_count_delta: int
    provider_constraints_changed: bool
    evidence_kind: Genc10TransitionEvidenceKind
    decision_population_sha256: str
    future_data_used: bool = False
    market_probability_claimed: bool = False

    def __post_init__(self) -> None:
        for name in (
            "transition_id",
            "account_identity_fingerprint",
            "conditioning_key",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value:
                raise CiboCompoundCapitalError(
                    f"GEN-C10 transition {name} is required"
                )
        for name in (
            "start_twin_sha256",
            "end_twin_sha256",
            "provider_registry_sha256",
            "decision_population_sha256",
        ):
            _sha(getattr(self, name), name)
        _aware(self.observed_start_at, "observed_start_at")
        _aware(self.observed_end_at, "observed_end_at")
        if self.observed_end_at <= self.observed_start_at:
            raise CiboCompoundCapitalError(
                "GEN-C10 transition end must follow start"
            )
        for name in (
            "realized_capital_delta_usd",
            "compound_value_delta_usd",
            "protected_floor_delta_usd",
            "stop_risk_capacity_delta_usd",
            "stop_risk_usage_delta_usd",
            "margin_capacity_delta_usd",
            "margin_usage_delta_usd",
        ):
            _signed(getattr(self, name), name)
        for name in (
            "active_deployment_count_delta",
            "known_option_count_delta",
        ):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise CiboCompoundCapitalError(
                    f"GEN-C10 transition {name} must be int"
                )
        if type(self.provider_constraints_changed) is not bool:
            raise CiboCompoundCapitalError(
                "GEN-C10 provider_constraints_changed must be bool"
            )
        if type(self.evidence_kind) is not Genc10TransitionEvidenceKind:
            raise CiboCompoundCapitalError(
                "GEN-C10 transition evidence kind is invalid"
            )
        if self.evidence_kind is not Genc10TransitionEvidenceKind.FORWARD_OBSERVED:
            raise CiboCompoundCapitalError(
                "GEN-C10 calibration requires FORWARD_OBSERVED evidence"
            )
        if self.future_data_used or self.market_probability_claimed:
            raise CiboCompoundCapitalError(
                "GEN-C10 calibration forbids future data/probability claims"
            )


@dataclass(frozen=True, slots=True)
class Genc10DecimalSupport:
    minimum: Decimal
    maximum: Decimal

    def __post_init__(self) -> None:
        _signed(self.minimum, "support minimum")
        _signed(self.maximum, "support maximum")
        if self.minimum > self.maximum:
            raise CiboCompoundCapitalError(
                "GEN-C10 support minimum cannot exceed maximum"
            )


@dataclass(frozen=True, slots=True)
class Genc10IntegerSupport:
    minimum: int
    maximum: int

    def __post_init__(self) -> None:
        for name in ("minimum", "maximum"):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise CiboCompoundCapitalError(
                    f"GEN-C10 integer support {name} must be int"
                )
        if self.minimum > self.maximum:
            raise CiboCompoundCapitalError(
                "GEN-C10 integer support minimum cannot exceed maximum"
            )


@dataclass(frozen=True, slots=True)
class Genc10TransitionSupport:
    conditioning_key: str
    observation_count: int
    observed_from: datetime
    observed_through: datetime
    realized_capital_delta_usd: Genc10DecimalSupport
    compound_value_delta_usd: Genc10DecimalSupport
    protected_floor_delta_usd: Genc10DecimalSupport
    stop_risk_capacity_delta_usd: Genc10DecimalSupport
    stop_risk_usage_delta_usd: Genc10DecimalSupport
    margin_capacity_delta_usd: Genc10DecimalSupport
    margin_usage_delta_usd: Genc10DecimalSupport
    active_deployment_count_delta: Genc10IntegerSupport
    known_option_count_delta: Genc10IntegerSupport
    provider_constraint_change_observations: int

    def __post_init__(self) -> None:
        if not self.conditioning_key or self.observation_count <= 0:
            raise CiboCompoundCapitalError(
                "GEN-C10 transition support identity/count invalid"
            )
        _aware(self.observed_from, "support observed_from")
        _aware(self.observed_through, "support observed_through")
        if self.observed_through <= self.observed_from:
            raise CiboCompoundCapitalError(
                "GEN-C10 support requires positive chronological span"
            )
        if (
            self.provider_constraint_change_observations < 0
            or self.provider_constraint_change_observations
            > self.observation_count
        ):
            raise CiboCompoundCapitalError(
                "GEN-C10 provider-change observation count invalid"
            )


@dataclass(frozen=True, slots=True)
class Genc10TransitionCalibrationReport:
    calibration_id: str
    account_identity_fingerprint: str
    source_population_sha256: str
    calibration_cutoff_at: datetime
    observation_count: int
    supports: tuple[Genc10TransitionSupport, ...]
    report_sha256: str
    frozen_v1_mutated: bool = False
    market_probability_claimed: bool = False
    production_policy_selected: bool = False
    certification_ready: bool = False

    def __post_init__(self) -> None:
        if self.calibration_id != GENC10_TRANSITION_CALIBRATION_ID:
            raise CiboCompoundCapitalError(
                "GEN-C10 transition calibration identity drift"
            )
        if not self.account_identity_fingerprint:
            raise CiboCompoundCapitalError(
                "GEN-C10 calibration account identity required"
            )
        _sha(self.source_population_sha256, "source_population_sha256")
        _aware(self.calibration_cutoff_at, "calibration_cutoff_at")
        if self.observation_count <= 0 or not self.supports:
            raise CiboCompoundCapitalError(
                "GEN-C10 calibration requires observed transitions"
            )
        _sha(self.report_sha256, "report_sha256")
        if (
            self.frozen_v1_mutated
            or self.market_probability_claimed
            or self.production_policy_selected
            or self.certification_ready
        ):
            raise CiboCompoundCapitalError(
                "GEN-C10 calibration governance drift"
            )


def calibrate_genc10_transition_uncertainty(
    *,
    observations: tuple[Genc10ObservedTransition, ...],
    source_population_sha256: str,
    calibration_cutoff_at: datetime,
) -> Genc10TransitionCalibrationReport:
    """Build descriptive empirical support using only pre-cutoff observations."""

    if not observations:
        raise CiboCompoundCapitalError(
            "GEN-C10 calibration population cannot be empty"
        )
    _sha(source_population_sha256, "source_population_sha256")
    _aware(calibration_cutoff_at, "calibration_cutoff_at")

    ids = tuple(item.transition_id for item in observations)
    if len(ids) != len(set(ids)):
        raise CiboCompoundCapitalError(
            "GEN-C10 calibration transition ids must be unique"
        )
    accounts = {item.account_identity_fingerprint for item in observations}
    if len(accounts) != 1:
        raise CiboCompoundCapitalError(
            "GEN-C10 calibration cannot mix account identities"
        )
    populations = {item.decision_population_sha256 for item in observations}
    if populations != {source_population_sha256}:
        raise CiboCompoundCapitalError(
            "GEN-C10 calibration population lineage drift"
        )
    if any(item.observed_end_at >= calibration_cutoff_at for item in observations):
        raise CiboCompoundCapitalError(
            "GEN-C10 calibration cannot consume at/after-cutoff transitions"
        )

    ordered = tuple(
        sorted(
            observations,
            key=lambda item: (
                item.observed_start_at,
                item.observed_end_at,
                item.transition_id,
            ),
        )
    )
    if any(
        current.observed_start_at < prior.observed_start_at
        for prior, current in zip(ordered, ordered[1:], strict=False)
    ):
        raise CiboCompoundCapitalError(
            "GEN-C10 calibration chronology drift"
        )

    supports = tuple(
        _support(key, tuple(item for item in ordered if item.conditioning_key == key))
        for key in sorted({item.conditioning_key for item in ordered})
    )
    payload = {
        "calibration_id": GENC10_TRANSITION_CALIBRATION_ID,
        "account_identity_fingerprint": next(iter(accounts)),
        "source_population_sha256": source_population_sha256,
        "calibration_cutoff_at": calibration_cutoff_at.isoformat(),
        "observation_ids": [item.transition_id for item in ordered],
        "supports": [_support_payload(item) for item in supports],
        "market_probability_claimed": False,
        "frozen_v1_mutated": False,
    }
    digest = _payload_sha256(payload)
    return Genc10TransitionCalibrationReport(
        calibration_id=GENC10_TRANSITION_CALIBRATION_ID,
        account_identity_fingerprint=next(iter(accounts)),
        source_population_sha256=source_population_sha256,
        calibration_cutoff_at=calibration_cutoff_at,
        observation_count=len(ordered),
        supports=supports,
        report_sha256=digest,
    )


def _support(
    key: str,
    rows: tuple[Genc10ObservedTransition, ...],
) -> Genc10TransitionSupport:
    if not rows:
        raise CiboCompoundCapitalError(
            "GEN-C10 support group cannot be empty"
        )
    decimal_names = (
        "realized_capital_delta_usd",
        "compound_value_delta_usd",
        "protected_floor_delta_usd",
        "stop_risk_capacity_delta_usd",
        "stop_risk_usage_delta_usd",
        "margin_capacity_delta_usd",
        "margin_usage_delta_usd",
    )
    integer_names = (
        "active_deployment_count_delta",
        "known_option_count_delta",
    )
    decimal_support = {
        name: Genc10DecimalSupport(
            minimum=min(getattr(item, name) for item in rows),
            maximum=max(getattr(item, name) for item in rows),
        )
        for name in decimal_names
    }
    integer_support = {
        name: Genc10IntegerSupport(
            minimum=min(getattr(item, name) for item in rows),
            maximum=max(getattr(item, name) for item in rows),
        )
        for name in integer_names
    }
    return Genc10TransitionSupport(
        conditioning_key=key,
        observation_count=len(rows),
        observed_from=min(item.observed_start_at for item in rows),
        observed_through=max(item.observed_end_at for item in rows),
        provider_constraint_change_observations=sum(
            1 for item in rows if item.provider_constraints_changed
        ),
        **decimal_support,
        **integer_support,
    )


def _support_payload(value: Genc10TransitionSupport) -> dict[str, object]:
    payload = asdict(value)
    payload["observed_from"] = value.observed_from.isoformat()
    payload["observed_through"] = value.observed_through.isoformat()
    for name in (
        "realized_capital_delta_usd",
        "compound_value_delta_usd",
        "protected_floor_delta_usd",
        "stop_risk_capacity_delta_usd",
        "stop_risk_usage_delta_usd",
        "margin_capacity_delta_usd",
        "margin_usage_delta_usd",
    ):
        item = getattr(value, name)
        payload[name] = {
            "minimum": format(item.minimum, "f"),
            "maximum": format(item.maximum, "f"),
        }
    return payload


def _payload_sha256(value: object) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _sha(value: str, name: str) -> None:
    if (
        not isinstance(value, str)
        or not value.startswith("sha256:")
        or len(value) != 71
        or any(char not in "0123456789abcdef" for char in value[7:])
    ):
        raise CiboCompoundCapitalError(
            f"GEN-C10 calibration {name} must be canonical SHA-256"
        )


def _aware(value: datetime, name: str) -> None:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise CiboCompoundCapitalError(
            f"GEN-C10 calibration {name} must be timezone-aware"
        )


def _signed(value: Decimal, name: str) -> None:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise CiboCompoundCapitalError(
            f"GEN-C10 calibration {name} must be finite Decimal"
        )
