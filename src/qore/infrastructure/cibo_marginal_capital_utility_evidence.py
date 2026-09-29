"""Causal evidence contract for CIBO GEN-C4 marginal capital utility.

GEN-C4 deliberately does NOT compute an optimal size or utility score. It
defines what must be known before a later preregistered policy may ask whether
one more unit of capital deserves deployment.

Shared may contribute read-only facts. A Shared fact cannot be consumed for a
capital decision unless its own contract says calibration, fresh OOS stability,
temporal stability and economic utility have been validated. Shared never gains
sizing, allocation, Risk or execution authority through this interface.

Research-only: no runtime capital authority.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
)
from qore.infrastructure.cibo_compound_capital import (
    CiboCompoundCapitalError,
)

_SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


class SharedCapitalFactKind(StrEnum):
    OPPORTUNITY_QUALITY = "OPPORTUNITY_QUALITY"
    CONTINUATION_SUPPORT = "CONTINUATION_SUPPORT"
    FAILURE_HAZARD = "FAILURE_HAZARD"
    POSITIVE_TAIL_POTENTIAL = "POSITIVE_TAIL_POTENTIAL"
    REGIME_STABILITY = "REGIME_STABILITY"
    CROSS_MARKET_COHERENCE = "CROSS_MARKET_COHERENCE"
    EPISTEMIC_UNCERTAINTY = "EPISTEMIC_UNCERTAINTY"
    RELATIONSHIP_STABILITY = "RELATIONSHIP_STABILITY"
    SYSTEMIC_STRESS = "SYSTEMIC_STRESS"


@dataclass(frozen=True, slots=True)
class SharedCapitalIntelligenceFact:
    fact_id: str
    kind: SharedCapitalFactKind
    normalized_value: Decimal
    value_semantics: str
    observed_at: datetime
    valid_until: datetime | None
    producer_identity: str
    producer_git_sha: str
    evidence_sha256: str
    calibration_artifact_sha256: str | None = None
    calibrated: bool = False
    fresh_oos_validated: bool = False
    temporal_stability_validated: bool = False
    economic_utility_validated: bool = False
    eligible_for_capital_use: bool = False
    read_only: bool = True
    sizing_authority: bool = False
    capital_authority: bool = False
    risk_authority: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        if not self.fact_id or not self.value_semantics:
            raise CiboCompoundCapitalError(
                "Shared capital fact identity/semantics is required"
            )
        if type(self.kind) is not SharedCapitalFactKind:
            raise CiboCompoundCapitalError(
                "Shared capital fact kind is invalid"
            )
        if (
            not isinstance(self.normalized_value, Decimal)
            or not self.normalized_value.is_finite()
            or self.normalized_value < 0
            or self.normalized_value > 1
        ):
            raise CiboCompoundCapitalError(
                "Shared capital fact normalized value must be in [0,1]"
            )
        _aware(self.observed_at, "Shared fact observed_at")
        if self.valid_until is not None:
            _aware(self.valid_until, "Shared fact valid_until")
            if self.valid_until < self.observed_at:
                raise CiboCompoundCapitalError(
                    "Shared capital fact validity cannot predate observation"
                )
        if not self.producer_identity:
            raise CiboCompoundCapitalError(
                "Shared capital fact producer identity is required"
            )
        if _SHA1_RE.fullmatch(self.producer_git_sha) is None:
            raise CiboCompoundCapitalError(
                "Shared capital fact producer Git SHA is invalid"
            )
        _sha(self.evidence_sha256, "Shared fact evidence_sha256")
        for name in (
            "calibrated",
            "fresh_oos_validated",
            "temporal_stability_validated",
            "economic_utility_validated",
            "eligible_for_capital_use",
            "read_only",
            "sizing_authority",
            "capital_authority",
            "risk_authority",
            "execution_authority",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCompoundCapitalError(
                    f"Shared capital fact {name} must be bool"
                )
        if (
            not self.read_only
            or self.sizing_authority
            or self.capital_authority
            or self.risk_authority
            or self.execution_authority
        ):
            raise CiboCompoundCapitalError(
                "Shared capital intelligence must remain read-only/no-authority"
            )

        validations = (
            self.calibrated,
            self.fresh_oos_validated,
            self.temporal_stability_validated,
            self.economic_utility_validated,
        )
        if self.eligible_for_capital_use:
            if not all(validations):
                raise CiboCompoundCapitalError(
                    "capital-eligible Shared fact requires complete validation"
                )
            _sha(
                self.calibration_artifact_sha256,
                "Shared fact calibration_artifact_sha256",
            )
        elif self.calibration_artifact_sha256 is not None:
            _sha(
                self.calibration_artifact_sha256,
                "Shared fact calibration_artifact_sha256",
            )


@dataclass(frozen=True, slots=True)
class SharedToCiboCapitalIntelligenceSnapshot:
    snapshot_id: str
    decision_at: datetime
    facts: tuple[SharedCapitalIntelligenceFact, ...]
    snapshot_sha256: str
    read_only: bool = True
    sizing_authority: bool = False
    capital_authority: bool = False
    risk_authority: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        if not self.snapshot_id:
            raise CiboCompoundCapitalError(
                "Shared->CIBO snapshot identity is required"
            )
        _aware(self.decision_at, "Shared->CIBO decision_at")
        _sha(self.snapshot_sha256, "Shared->CIBO snapshot_sha256")
        if not isinstance(self.facts, tuple) or any(
            not isinstance(item, SharedCapitalIntelligenceFact)
            for item in self.facts
        ):
            raise CiboCompoundCapitalError(
                "Shared->CIBO facts must be canonical tuple"
            )
        ids = tuple(item.fact_id for item in self.facts)
        if len(ids) != len(set(ids)):
            raise CiboCompoundCapitalError(
                "Shared->CIBO fact ids must be unique"
            )
        kinds = tuple(item.kind for item in self.facts)
        if len(kinds) != len(set(kinds)):
            raise CiboCompoundCapitalError(
                "Shared->CIBO snapshot cannot duplicate fact kinds"
            )
        for fact in self.facts:
            if fact.observed_at > self.decision_at:
                raise CiboCompoundCapitalError(
                    "Shared->CIBO fact cannot arrive from the future"
                )
            if (
                fact.valid_until is not None
                and fact.valid_until < self.decision_at
            ):
                raise CiboCompoundCapitalError(
                    "Shared->CIBO fact is stale at decision time"
                )
        for name in (
            "read_only",
            "sizing_authority",
            "capital_authority",
            "risk_authority",
            "execution_authority",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCompoundCapitalError(
                    f"Shared->CIBO snapshot {name} must be bool"
                )
        if (
            not self.read_only
            or self.sizing_authority
            or self.capital_authority
            or self.risk_authority
            or self.execution_authority
        ):
            raise CiboCompoundCapitalError(
                "Shared->CIBO contract cannot transfer authority"
            )

    def fact(self, fact_id: str) -> SharedCapitalIntelligenceFact:
        rows = tuple(item for item in self.facts if item.fact_id == fact_id)
        if len(rows) != 1:
            raise CiboCompoundCapitalError(
                "Shared->CIBO fact identity not found"
            )
        return rows[0]


@dataclass(frozen=True, slots=True)
class MarginalCapitalUtilityEvidence:
    evidence_id: str
    decision_at: datetime
    account_identity: CiboAccountCapitalIdentity
    trader_id: TraderLineage
    signal_fingerprint: str
    source_opportunity_decision_sha256: str
    source_baseline_policy_record_sha256: str
    current_compound_capacity_usd: Decimal
    requested_incremental_capital_usd: Decimal
    expected_incremental_return_usd: Decimal
    incremental_stop_risk_usd: Decimal
    incremental_margin_usd: Decimal
    incremental_execution_cost_usd: Decimal
    incremental_concentration_risk_usd: Decimal
    incremental_drawdown_risk_proxy_usd: Decimal
    incremental_optionality_consumed_usd: Decimal
    expected_capital_minutes: Decimal
    epistemic_uncertainty: Decimal
    provider_evidence_sha256: str
    expectation_evidence_sha256: str
    factor_evidence_sha256: str | None
    duration_evidence_sha256: str
    execution_evidence_sha256: str
    optionality_evidence_sha256: str
    shared_snapshot: SharedToCiboCapitalIntelligenceSnapshot | None = None
    shared_fact_ids_used: tuple[str, ...] = ()
    outcome_present: bool = False
    utility_score_computed: bool = False
    sizing_authority: bool = False
    capital_authority: bool = False
    risk_authority: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        if not self.evidence_id or not self.signal_fingerprint:
            raise CiboCompoundCapitalError(
                "marginal capital evidence identity/signal is required"
            )
        _aware(self.decision_at, "marginal capital decision_at")
        if not isinstance(
            self.account_identity,
            CiboAccountCapitalIdentity,
        ):
            raise CiboCompoundCapitalError(
                "marginal capital account identity is invalid"
            )
        if type(self.trader_id) is not TraderLineage:
            raise CiboCompoundCapitalError(
                "marginal capital Trader identity is invalid"
            )
        for name in (
            "current_compound_capacity_usd",
            "requested_incremental_capital_usd",
            "incremental_stop_risk_usd",
            "incremental_margin_usd",
            "incremental_execution_cost_usd",
            "incremental_concentration_risk_usd",
            "incremental_drawdown_risk_proxy_usd",
            "incremental_optionality_consumed_usd",
            "expected_capital_minutes",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value < 0
            ):
                raise CiboCompoundCapitalError(
                    f"marginal capital {name} must be finite non-negative"
                )
        if self.requested_incremental_capital_usd <= 0:
            raise CiboCompoundCapitalError(
                "marginal capital request must be positive"
            )
        if self.requested_incremental_capital_usd > (
            self.current_compound_capacity_usd
        ):
            raise CiboCompoundCapitalError(
                "marginal capital request exceeds current compound capacity"
            )
        if (
            not isinstance(self.expected_incremental_return_usd, Decimal)
            or not self.expected_incremental_return_usd.is_finite()
        ):
            raise CiboCompoundCapitalError(
                "marginal expected incremental return must be finite Decimal"
            )
        if self.expected_capital_minutes <= 0:
            raise CiboCompoundCapitalError(
                "marginal expected capital duration must be positive"
            )
        if (
            not isinstance(self.epistemic_uncertainty, Decimal)
            or not self.epistemic_uncertainty.is_finite()
            or self.epistemic_uncertainty < 0
            or self.epistemic_uncertainty > 1
        ):
            raise CiboCompoundCapitalError(
                "marginal epistemic uncertainty must be in [0,1]"
            )

        for name in (
            "source_opportunity_decision_sha256",
            "source_baseline_policy_record_sha256",
            "provider_evidence_sha256",
            "expectation_evidence_sha256",
            "duration_evidence_sha256",
            "execution_evidence_sha256",
            "optionality_evidence_sha256",
        ):
            _sha(getattr(self, name), name)
        if self.factor_evidence_sha256 is not None:
            _sha(
                self.factor_evidence_sha256,
                "factor_evidence_sha256",
            )

        if len(self.shared_fact_ids_used) != len(
            set(self.shared_fact_ids_used)
        ):
            raise CiboCompoundCapitalError(
                "marginal Shared fact ids must be unique"
            )
        if self.shared_fact_ids_used:
            if self.shared_snapshot is None:
                raise CiboCompoundCapitalError(
                    "marginal Shared facts require bound Shared snapshot"
                )
            if self.shared_snapshot.decision_at != self.decision_at:
                raise CiboCompoundCapitalError(
                    "marginal Shared snapshot decision binding drift"
                )
            for fact_id in self.shared_fact_ids_used:
                fact = self.shared_snapshot.fact(fact_id)
                if not fact.eligible_for_capital_use:
                    raise CiboCompoundCapitalError(
                        "unvalidated Shared fact cannot influence capital"
                    )
        elif self.shared_snapshot is not None:
            if self.shared_snapshot.decision_at != self.decision_at:
                raise CiboCompoundCapitalError(
                    "marginal Shared snapshot decision binding drift"
                )

        for name in (
            "outcome_present",
            "utility_score_computed",
            "sizing_authority",
            "capital_authority",
            "risk_authority",
            "execution_authority",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCompoundCapitalError(
                    f"marginal capital {name} must be bool"
                )
        if (
            self.outcome_present
            or self.utility_score_computed
            or self.sizing_authority
            or self.capital_authority
            or self.risk_authority
            or self.execution_authority
        ):
            raise CiboCompoundCapitalError(
                "GEN-C4 evidence cannot contain outcomes, utility or authority"
            )


def _sha(value: str | None, name: str) -> None:
    if (
        not isinstance(value, str)
        or _SHA256_RE.fullmatch(value) is None
    ):
        raise CiboCompoundCapitalError(
            f"marginal capital {name} must be canonical SHA-256"
        )


def _aware(value: datetime, name: str) -> None:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise CiboCompoundCapitalError(
            f"marginal capital {name} must be timezone-aware"
        )
