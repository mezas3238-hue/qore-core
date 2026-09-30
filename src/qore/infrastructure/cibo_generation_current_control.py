"""Immutable AS-IS generation control manifest for CIBO research.

This module does not freeze the active branch by itself. It defines the
fail-closed contract that must be satisfied before an exact green repository
state can become CIBO_GENERATION_CURRENT_CONTROL_V1.

Research/governance only: no sizing, Risk, execution, DEMO, LIVE, production,
real-capital or merge authority.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime

from qore.infrastructure.cibo_ce2i_phase20_policy_candidate import (
    FROZEN_PHASE20_POLICY_CANDIDATE,
)
from qore.infrastructure.cibo_compound_capital import CiboCompoundCapitalError
from qore.infrastructure.cibo_internal_capital_market import (
    GENC6_POLICY_FROZEN_AT,
    GENC6_POLICY_ID,
    genc6_policy_sha256,
)
from qore.infrastructure.cibo_profit_preservation_shadow import (
    GENC7_POLICY_FROZEN_AT,
    GENC7_POLICY_ID,
    genc7_policy_sha256,
)
from qore.infrastructure.cibo_sequential_compounding_shadow_policy import (
    GENC5_SHADOW_POLICY_FROZEN_AT,
    GENC5_SHADOW_POLICY_ID,
    genc5_shadow_policy_sha256,
)

CIBO_CURRENT_CONTROL_ID = "CIBO_GENERATION_CURRENT_CONTROL_V1"

_SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


def _require_aware(value: datetime, name: str) -> None:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise CiboCompoundCapitalError(
            f"current control {name} must be timezone-aware"
        )


def _require_sha256(value: str, name: str) -> None:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise CiboCompoundCapitalError(
            f"current control {name} must be canonical SHA-256"
        )


@dataclass(frozen=True, slots=True)
class CiboCurrentGenerationControlManifest:
    control_id: str
    git_sha: str
    sealed_at: datetime
    phase20_candidate_id: str
    phase20_code_sha: str
    phase20_parameter_sha256: str
    genc5_policy_id: str
    genc5_policy_sha256: str
    genc5_frozen_at: datetime
    genc6_policy_id: str
    genc6_policy_sha256: str
    genc6_frozen_at: datetime
    genc7_policy_id: str
    genc7_policy_sha256: str
    genc7_frozen_at: datetime
    trader_surface_sha256: str
    provider_capability_snapshot_sha256: str
    capital_state_snapshot_sha256: str
    capital_utilization_snapshot_sha256: str
    workflow_evidence_sha256: str
    world_cup_mission_sha256: str
    world_cup_gap_matrix_sha256: str
    all_required_ci_green: bool
    holdout_2017h1_untouched: bool
    economic_baseline_measurement_bound: bool
    economic_baseline_measurement_blockers: tuple[str, ...]
    phase20_v3_mutated: bool = False
    outcome_data_used_to_select_control: bool = False
    runtime_authority: bool = False
    risk_authority: bool = False
    execution_authority: bool = False
    live_authority: bool = False
    real_capital_authority: bool = False
    merge_authority: bool = False

    def __post_init__(self) -> None:
        if self.control_id != CIBO_CURRENT_CONTROL_ID:
            raise CiboCompoundCapitalError(
                "current control identity drift"
            )
        if _SHA1_RE.fullmatch(self.git_sha) is None:
            raise CiboCompoundCapitalError(
                "current control Git SHA must be lowercase 40-hex"
            )
        _require_aware(self.sealed_at, "sealed_at")
        if (
            self.phase20_candidate_id
            != FROZEN_PHASE20_POLICY_CANDIDATE.candidate_id
            or self.phase20_code_sha
            != FROZEN_PHASE20_POLICY_CANDIDATE.code_sha
            or self.phase20_parameter_sha256
            != FROZEN_PHASE20_POLICY_CANDIDATE.parameter_sha256()
        ):
            raise CiboCompoundCapitalError(
                "current control Phase20 V3 identity drift"
            )
        if (
            self.genc5_policy_id != GENC5_SHADOW_POLICY_ID
            or self.genc5_policy_sha256 != genc5_shadow_policy_sha256()
            or self.genc5_frozen_at != GENC5_SHADOW_POLICY_FROZEN_AT
        ):
            raise CiboCompoundCapitalError(
                "current control GEN-C5 identity drift"
            )
        if (
            self.genc6_policy_id != GENC6_POLICY_ID
            or self.genc6_policy_sha256 != genc6_policy_sha256()
            or self.genc6_frozen_at != GENC6_POLICY_FROZEN_AT
        ):
            raise CiboCompoundCapitalError(
                "current control GEN-C6 identity drift"
            )
        if (
            self.genc7_policy_id != GENC7_POLICY_ID
            or self.genc7_policy_sha256 != genc7_policy_sha256()
            or self.genc7_frozen_at != GENC7_POLICY_FROZEN_AT
        ):
            raise CiboCompoundCapitalError(
                "current control GEN-C7 identity drift"
            )
        for name in (
            "phase20_parameter_sha256",
            "genc5_policy_sha256",
            "genc6_policy_sha256",
            "genc7_policy_sha256",
            "trader_surface_sha256",
            "provider_capability_snapshot_sha256",
            "capital_state_snapshot_sha256",
            "capital_utilization_snapshot_sha256",
            "workflow_evidence_sha256",
            "world_cup_mission_sha256",
            "world_cup_gap_matrix_sha256",
        ):
            _require_sha256(getattr(self, name), name)
        for name in (
            "all_required_ci_green",
            "holdout_2017h1_untouched",
            "economic_baseline_measurement_bound",
            "phase20_v3_mutated",
            "outcome_data_used_to_select_control",
            "runtime_authority",
            "risk_authority",
            "execution_authority",
            "live_authority",
            "real_capital_authority",
            "merge_authority",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCompoundCapitalError(
                    f"current control {name} must be bool"
                )
        if len(self.economic_baseline_measurement_blockers) != len(
            set(self.economic_baseline_measurement_blockers)
        ):
            raise CiboCompoundCapitalError(
                "current control economic baseline blockers must be unique"
            )
        if any(
            not isinstance(item, str) or not item
            for item in self.economic_baseline_measurement_blockers
        ):
            raise CiboCompoundCapitalError(
                "current control economic baseline blockers are invalid"
            )
        if self.economic_baseline_measurement_bound:
            if self.economic_baseline_measurement_blockers:
                raise CiboCompoundCapitalError(
                    "bound economic baseline cannot retain blockers"
                )
        elif not self.economic_baseline_measurement_blockers:
            raise CiboCompoundCapitalError(
                "unbound economic baseline must state explicit blockers"
            )
        if not self.all_required_ci_green:
            raise CiboCompoundCapitalError(
                "current control cannot seal while required CI is not green"
            )
        if not self.holdout_2017h1_untouched:
            raise CiboCompoundCapitalError(
                "current control requires untouched 2017H1 holdout"
            )
        if self.phase20_v3_mutated:
            raise CiboCompoundCapitalError(
                "current control cannot seal mutated Phase20 V3"
            )
        if self.outcome_data_used_to_select_control:
            raise CiboCompoundCapitalError(
                "current control cannot be selected from outcome inspection"
            )
        if any(
            (
                self.runtime_authority,
                self.risk_authority,
                self.execution_authority,
                self.live_authority,
                self.real_capital_authority,
                self.merge_authority,
            )
        ):
            raise CiboCompoundCapitalError(
                "current control manifest grants no productive authority"
            )

    def fingerprint(self) -> str:
        payload = asdict(self)
        for name in (
            "sealed_at",
            "genc5_frozen_at",
            "genc6_frozen_at",
            "genc7_frozen_at",
        ):
            payload[name] = getattr(self, name).isoformat()
        raw = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        return "sha256:" + hashlib.sha256(raw).hexdigest()


def seal_current_generation_control(
    *,
    git_sha: str,
    sealed_at: datetime,
    trader_surface_sha256: str,
    provider_capability_snapshot_sha256: str,
    capital_state_snapshot_sha256: str,
    capital_utilization_snapshot_sha256: str,
    workflow_evidence_sha256: str,
    world_cup_mission_sha256: str,
    world_cup_gap_matrix_sha256: str,
    all_required_ci_green: bool,
    holdout_2017h1_untouched: bool,
    economic_baseline_measurement_bound: bool,
    economic_baseline_measurement_blockers: tuple[str, ...],
) -> CiboCurrentGenerationControlManifest:
    """Seal the exact green AS-IS research generation as future control."""

    return CiboCurrentGenerationControlManifest(
        control_id=CIBO_CURRENT_CONTROL_ID,
        git_sha=git_sha,
        sealed_at=sealed_at,
        phase20_candidate_id=FROZEN_PHASE20_POLICY_CANDIDATE.candidate_id,
        phase20_code_sha=FROZEN_PHASE20_POLICY_CANDIDATE.code_sha,
        phase20_parameter_sha256=(
            FROZEN_PHASE20_POLICY_CANDIDATE.parameter_sha256()
        ),
        genc5_policy_id=GENC5_SHADOW_POLICY_ID,
        genc5_policy_sha256=genc5_shadow_policy_sha256(),
        genc5_frozen_at=GENC5_SHADOW_POLICY_FROZEN_AT,
        genc6_policy_id=GENC6_POLICY_ID,
        genc6_policy_sha256=genc6_policy_sha256(),
        genc6_frozen_at=GENC6_POLICY_FROZEN_AT,
        genc7_policy_id=GENC7_POLICY_ID,
        genc7_policy_sha256=genc7_policy_sha256(),
        genc7_frozen_at=GENC7_POLICY_FROZEN_AT,
        trader_surface_sha256=trader_surface_sha256,
        provider_capability_snapshot_sha256=(
            provider_capability_snapshot_sha256
        ),
        capital_state_snapshot_sha256=capital_state_snapshot_sha256,
        capital_utilization_snapshot_sha256=(
            capital_utilization_snapshot_sha256
        ),
        workflow_evidence_sha256=workflow_evidence_sha256,
        world_cup_mission_sha256=world_cup_mission_sha256,
        world_cup_gap_matrix_sha256=world_cup_gap_matrix_sha256,
        all_required_ci_green=all_required_ci_green,
        holdout_2017h1_untouched=holdout_2017h1_untouched,
        economic_baseline_measurement_bound=(
            economic_baseline_measurement_bound
        ),
        economic_baseline_measurement_blockers=(
            economic_baseline_measurement_blockers
        ),
        phase20_v3_mutated=False,
        outcome_data_used_to_select_control=False,
        runtime_authority=False,
        risk_authority=False,
        execution_authority=False,
        live_authority=False,
        real_capital_authority=False,
        merge_authority=False,
    )
