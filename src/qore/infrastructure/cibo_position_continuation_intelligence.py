"""CIBO native open-position continuation intelligence.

Research-only, causal, outcome-free.  Estimates the remaining expected economic
value of an already-open position from expectation frozen at entry, observed
age, and the known structural exit horizon.  It never reads realized/future
outcome and never increases expected value above the entry expectation.

This engine supplies Portfolio with a causal KEEP/RELEASE comparison surface.
It grants no Risk, sizing, execution or broker authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)


@dataclass(frozen=True, slots=True)
class CiboPositionContinuationInput:
    signal_fingerprint: str
    observed_at: datetime
    entry_at: datetime
    planned_exit_at: datetime
    entry_expected_net_value_usd: Decimal
    entry_expected_capital_minutes: Decimal
    current_stop_risk_usd: Decimal
    current_margin_usd: Decimal
    expectation_evidence_sha256: str

    def __post_init__(self) -> None:
        if not self.signal_fingerprint:
            raise CiboCapitalManagementError(
                "continuation input signal identity required"
            )
        for name in ("observed_at", "entry_at", "planned_exit_at"):
            value = getattr(self, name)
            if value.tzinfo is None or value.utcoffset() is None:
                raise CiboCapitalManagementError(
                    f"continuation {name} must be timezone-aware"
                )
        if self.entry_at > self.observed_at:
            raise CiboCapitalManagementError(
                "continuation cannot observe before position entry"
            )
        if self.planned_exit_at <= self.entry_at:
            raise CiboCapitalManagementError(
                "continuation planned exit must follow entry"
            )
        for name in (
            "entry_expected_net_value_usd",
            "entry_expected_capital_minutes",
            "current_stop_risk_usd",
            "current_margin_usd",
        ):
            value = getattr(self, name)
            if not isinstance(value, Decimal) or not value.is_finite():
                raise CiboCapitalManagementError(
                    f"continuation {name} must be finite Decimal"
                )
        if self.entry_expected_capital_minutes <= 0:
            raise CiboCapitalManagementError(
                "continuation entry expected capital minutes must be positive"
            )
        if self.current_stop_risk_usd < 0 or self.current_margin_usd < 0:
            raise CiboCapitalManagementError(
                "continuation current capacity use cannot be negative"
            )
        if (
            not self.expectation_evidence_sha256.startswith("sha256:")
            or len(self.expectation_evidence_sha256) != 71
        ):
            raise CiboCapitalManagementError(
                "continuation expectation evidence digest invalid"
            )


@dataclass(frozen=True, slots=True)
class CiboPositionContinuationEstimate:
    signal_fingerprint: str
    observed_at: datetime
    remaining_capital_minutes: Decimal
    elapsed_minutes: Decimal
    remaining_fraction_of_entry_horizon: Decimal
    expected_continuation_net_value_usd: Decimal
    continuation_utility_per_minute: Decimal
    value_identified: bool
    outcome_used: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if not self.signal_fingerprint:
            raise CiboCapitalManagementError(
                "continuation estimate identity required"
            )
        for name in (
            "remaining_capital_minutes",
            "elapsed_minutes",
            "remaining_fraction_of_entry_horizon",
        ):
            value = getattr(self, name)
            if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
                raise CiboCapitalManagementError(
                    f"continuation estimate {name} invalid"
                )
        if self.remaining_fraction_of_entry_horizon > 1:
            raise CiboCapitalManagementError(
                "continuation remaining fraction cannot exceed one"
            )
        for name in (
            "expected_continuation_net_value_usd",
            "continuation_utility_per_minute",
        ):
            value = getattr(self, name)
            if not isinstance(value, Decimal) or not value.is_finite():
                raise CiboCapitalManagementError(
                    f"continuation estimate {name} must be finite Decimal"
                )
        if self.outcome_used or self.productive_authority:
            raise CiboCapitalManagementError(
                "continuation intelligence cannot use outcomes or authority"
            )


def estimate_position_continuation(
    evidence: CiboPositionContinuationInput,
) -> CiboPositionContinuationEstimate:
    """Estimate remaining ex-ante value without future/outcome information."""

    if not isinstance(evidence, CiboPositionContinuationInput):
        raise CiboCapitalManagementError(
            "continuation engine requires canonical input"
        )

    elapsed_seconds = max(
        Decimal(0),
        Decimal(str((evidence.observed_at - evidence.entry_at).total_seconds())),
    )
    elapsed_minutes = elapsed_seconds / Decimal(60)

    if evidence.observed_at >= evidence.planned_exit_at:
        remaining_minutes = Decimal(0)
    else:
        remaining_minutes = (
            Decimal(
                str(
                    (
                        evidence.planned_exit_at - evidence.observed_at
                    ).total_seconds()
                )
            )
            / Decimal(60)
        )

    normalized_remaining = min(
        Decimal(1),
        max(
            Decimal(0),
            remaining_minutes / evidence.entry_expected_capital_minutes,
        ),
    )
    continuation_value = (
        evidence.entry_expected_net_value_usd * normalized_remaining
    )
    utility_per_minute = (
        Decimal(0)
        if remaining_minutes <= 0
        else continuation_value / remaining_minutes
    )
    identified = evidence.observed_at < evidence.planned_exit_at

    return CiboPositionContinuationEstimate(
        signal_fingerprint=evidence.signal_fingerprint,
        observed_at=evidence.observed_at,
        remaining_capital_minutes=remaining_minutes,
        elapsed_minutes=elapsed_minutes,
        remaining_fraction_of_entry_horizon=normalized_remaining,
        expected_continuation_net_value_usd=continuation_value,
        continuation_utility_per_minute=utility_per_minute,
        value_identified=identified,
        outcome_used=False,
        productive_authority=False,
    )
