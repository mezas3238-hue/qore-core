"""Frozen Phase 20 policy candidate for fresh-forward qualification.

This module pre-registers one research policy candidate before any qualifying
forward evidence may be consumed. The candidate has no runtime allocation,
Risk, execution, DEMO-governed, LIVE, real-capital or merge authority.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from hashlib import sha256

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)

_SHA1_RE = re.compile(r"^[0-9a-f]{40}$")


@dataclass(frozen=True, slots=True)
class Phase20FrozenPolicyCandidate:
    candidate_id: str
    code_sha: str
    frozen_at: datetime
    mpc_horizon_steps: int
    snapshot_max_age_seconds: Decimal
    current_forecast_max_age_seconds: Decimal
    composition_order: tuple[str, ...]
    active_ce2i_tools: tuple[str, ...]
    accounting_dependencies: tuple[str, ...]
    outcome_aware: bool = False
    validation_tuned: bool = False
    phase19j_burned_validation_reused: bool = False
    policy_certified: bool = False
    allocation_authority: bool = False
    risk_authority: bool = False
    execution_authority: bool = False
    demo_execution_authorized: bool = False
    live_authorized: bool = False
    real_capital_authorized: bool = False
    merge_authorized: bool = False

    def __post_init__(self) -> None:
        if not self.candidate_id:
            raise CiboCapitalManagementError(
                "Phase20 frozen candidate_id is required"
            )
        if _SHA1_RE.fullmatch(self.code_sha) is None:
            raise CiboCapitalManagementError(
                "Phase20 frozen code_sha must be lowercase 40-hex"
            )
        if self.frozen_at.tzinfo is None or self.frozen_at.utcoffset() is None:
            raise CiboCapitalManagementError(
                "Phase20 frozen_at must be timezone-aware"
            )
        if type(self.mpc_horizon_steps) is not int or self.mpc_horizon_steps <= 0:
            raise CiboCapitalManagementError(
                "Phase20 MPC horizon must be positive int"
            )
        for name in (
            "snapshot_max_age_seconds",
            "current_forecast_max_age_seconds",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value <= 0
            ):
                raise CiboCapitalManagementError(
                    f"Phase20 {name} must be finite positive Decimal"
                )
        if not self.composition_order:
            raise CiboCapitalManagementError(
                "Phase20 composition_order is required"
            )
        if len(self.active_ce2i_tools) != len(set(self.active_ce2i_tools)):
            raise CiboCapitalManagementError(
                "Phase20 active tool list must be unique"
            )
        if len(self.accounting_dependencies) != len(
            set(self.accounting_dependencies)
        ):
            raise CiboCapitalManagementError(
                "Phase20 accounting dependency list must be unique"
            )
        if (
            self.outcome_aware
            or self.validation_tuned
            or self.phase19j_burned_validation_reused
            or self.policy_certified
            or self.allocation_authority
            or self.risk_authority
            or self.execution_authority
            or self.demo_execution_authorized
            or self.live_authorized
            or self.real_capital_authorized
            or self.merge_authorized
        ):
            raise CiboCapitalManagementError(
                "Phase20 frozen candidate governance drift"
            )

    def parameter_payload(self) -> dict[str, object]:
        return {
            "candidate_id": self.candidate_id,
            "mpc_horizon_steps": self.mpc_horizon_steps,
            "snapshot_max_age_seconds": format(
                self.snapshot_max_age_seconds,
                "f",
            ),
            "current_forecast_max_age_seconds": format(
                self.current_forecast_max_age_seconds,
                "f",
            ),
            "composition_order": list(self.composition_order),
            "active_ce2i_tools": list(self.active_ce2i_tools),
            "accounting_dependencies": list(self.accounting_dependencies),
            "regime_thresholds": {
                "drawdown_defensive": "0.50",
                "drawdown_recovery": "0.75",
                "risk_defensive": "0.70",
                "risk_recovery": "0.85",
                "margin_defensive": "0.80",
            },
            "single_candidate_direct_postures": ["STABLE", "WATCH"],
            "multi_candidate_competition_minimum": 2,
            "mpc_representative_rule": (
                "minimum capacity pressure per future decision step"
            ),
            "mpc_reserve_rule": (
                "maximum requirement across deterministic representatives"
            ),
        }

    def parameter_sha256(self) -> str:
        payload = json.dumps(
            self.parameter_payload(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return f"sha256:{sha256(payload).hexdigest()}"


FROZEN_PHASE20_POLICY_CANDIDATE = Phase20FrozenPolicyCandidate(
    candidate_id="CIBO_PHASE20H20I_FORWARD_CANDIDATE_V1",
    code_sha="a0a9759a5bbe30fb21e1aee154fadc6509136937",
    frozen_at=datetime(2026, 9, 27, 13, 24, tzinfo=UTC),
    mpc_horizon_steps=2,
    snapshot_max_age_seconds=Decimal("2"),
    current_forecast_max_age_seconds=Decimal("2"),
    composition_order=(
        "SEAL_PREDECISION_EVIDENCE",
        "SELECT_CAUSAL_REGIME",
        "PHASE20I_RESERVE",
        "PHASE20H_ALLOCATE_REMAINDER",
        "QORE_RISK_DOWNSTREAM",
    ),
    active_ce2i_tools=("T09", "T12", "T13", "T15", "T18"),
    accounting_dependencies=("T19", "T20"),
)
