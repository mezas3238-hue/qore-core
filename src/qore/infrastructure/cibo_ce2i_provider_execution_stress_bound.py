"""Frozen provider-execution stress envelope for CIBO certification.

This is an owner-authorized fallback when empirical slippage population is too
small.  It does not claim observed slippage.  It freezes a conservative,
multi-scenario execution-cost surface so the final fresh holdout must report
sensitivity under predetermined provider degradation instead of waiting for a
large forward fill population.

No scenario is selected from holdout outcomes and no scenario grants productive
authority.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from decimal import Decimal

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)

PROVIDER_EXECUTION_STRESS_PROFILE_ID = (
    "CIBO_PROVIDER_EXECUTION_STRESS_BOUND_V1"
)
PROVIDER_EXECUTION_STRESS_PROFILE_FROZEN_AT = datetime(
    2026, 10, 1, 13, 55, tzinfo=UTC
)


@dataclass(frozen=True, slots=True)
class ProviderExecutionStressScenario:
    scenario_id: str
    spread_multiplier: Decimal
    adverse_slippage_spread_multiple: Decimal
    commission_multiplier: Decimal
    margin_multiplier: Decimal

    def __post_init__(self) -> None:
        if not self.scenario_id:
            raise CiboCapitalManagementError(
                "provider execution stress scenario id is required"
            )
        for name in (
            "spread_multiplier",
            "adverse_slippage_spread_multiple",
            "commission_multiplier",
            "margin_multiplier",
        ):
            value = getattr(self, name)
            if not isinstance(value, Decimal) or not value.is_finite():
                raise CiboCapitalManagementError(
                    f"provider execution stress {name} must be finite Decimal"
                )
            if value < 0:
                raise CiboCapitalManagementError(
                    f"provider execution stress {name} cannot be negative"
                )
        if self.spread_multiplier < 1:
            raise CiboCapitalManagementError(
                "provider execution stress spread multiplier cannot improve terms"
            )
        if self.commission_multiplier < 1:
            raise CiboCapitalManagementError(
                "provider execution stress commission multiplier cannot improve terms"
            )
        if self.margin_multiplier < 1:
            raise CiboCapitalManagementError(
                "provider execution stress margin multiplier cannot improve terms"
            )


@dataclass(frozen=True, slots=True)
class ProviderExecutionStressProfile:
    profile_id: str
    frozen_at: datetime
    scenarios: tuple[ProviderExecutionStressScenario, ...]
    empirical_slippage_claimed: bool = False
    historical_2017_exact_claimed: bool = False
    holdout_outcomes_used: bool = False
    target_aware: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if self.profile_id != PROVIDER_EXECUTION_STRESS_PROFILE_ID:
            raise CiboCapitalManagementError(
                "provider execution stress profile identity drift"
            )
        if self.frozen_at.tzinfo is None or self.frozen_at.utcoffset() is None:
            raise CiboCapitalManagementError(
                "provider execution stress freeze must be timezone-aware"
            )
        if not self.scenarios:
            raise CiboCapitalManagementError(
                "provider execution stress scenarios are required"
            )
        ids = tuple(item.scenario_id for item in self.scenarios)
        if len(ids) != len(set(ids)):
            raise CiboCapitalManagementError(
                "provider execution stress scenario ids must be unique"
            )
        if any(
            (
                self.empirical_slippage_claimed,
                self.historical_2017_exact_claimed,
                self.holdout_outcomes_used,
                self.target_aware,
                self.productive_authority,
            )
        ):
            raise CiboCapitalManagementError(
                "provider execution stress profile governance drift"
            )

    def fingerprint(self) -> str:
        raw = json.dumps(
            _canonical(asdict(self)),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return "sha256:" + hashlib.sha256(raw).hexdigest()


FROZEN_PROVIDER_EXECUTION_STRESS_PROFILE = ProviderExecutionStressProfile(
    profile_id=PROVIDER_EXECUTION_STRESS_PROFILE_ID,
    frozen_at=PROVIDER_EXECUTION_STRESS_PROFILE_FROZEN_AT,
    scenarios=(
        ProviderExecutionStressScenario(
            scenario_id="NATIVE_BASE",
            spread_multiplier=Decimal("1.00"),
            adverse_slippage_spread_multiple=Decimal("0.00"),
            commission_multiplier=Decimal("1.00"),
            margin_multiplier=Decimal("1.00"),
        ),
        ProviderExecutionStressScenario(
            scenario_id="MODERATE_DEGRADATION",
            spread_multiplier=Decimal("1.50"),
            adverse_slippage_spread_multiple=Decimal("0.50"),
            commission_multiplier=Decimal("1.25"),
            margin_multiplier=Decimal("1.10"),
        ),
        ProviderExecutionStressScenario(
            scenario_id="SEVERE_DEGRADATION",
            spread_multiplier=Decimal("2.00"),
            adverse_slippage_spread_multiple=Decimal("1.00"),
            commission_multiplier=Decimal("1.50"),
            margin_multiplier=Decimal("1.25"),
        ),
        ProviderExecutionStressScenario(
            scenario_id="EXTREME_DEGRADATION",
            spread_multiplier=Decimal("3.00"),
            adverse_slippage_spread_multiple=Decimal("2.00"),
            commission_multiplier=Decimal("2.00"),
            margin_multiplier=Decimal("1.50"),
        ),
    ),
)


def provider_execution_stress_profile_sha256() -> str:
    return FROZEN_PROVIDER_EXECUTION_STRESS_PROFILE.fingerprint()


def _canonical(value: object) -> object:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, tuple):
        return [_canonical(item) for item in value]
    if isinstance(value, list):
        return [_canonical(item) for item in value]
    if isinstance(value, dict):
        return {
            str(key): _canonical(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    return value
