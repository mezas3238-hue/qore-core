"""Pre-outcome provenance amendment for the Phase22 historical holdout.

The active V2 holdout is historical. It cannot truthfully produce cTrader DEMO
order/deal/position identifiers from 2015-2016. This amendment preserves the
frozen policy and economic thresholds while requiring a separate empirical
current-provider calibration before counterfactual replay economics may be
constructed. It never relabels current DEMO fills as historical fills.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_holdout_registry import (
    ACTIVE_USD60_HOLDOUT_CANDIDATE,
)
from qore.infrastructure.cibo_ce2i_phase20_policy_candidate import (
    FROZEN_PHASE20_POLICY_CANDIDATE,
)
from qore.infrastructure.cibo_ce2i_phase20_qualification_plan import (
    phase20d_qualification_plan_sha256,
)
from qore.infrastructure.cibo_ce2i_phase22_qualification_plan import (
    phase22_holdout_qualification_plan_sha256,
)

AMENDMENT_ID = "CIBO_PHASE22_HISTORICAL_REPLAY_ECONOMICS_AMENDMENT_V1"
EXECUTION_ECONOMICS_KIND = (
    "EMPIRICALLY_CALIBRATED_COUNTERFACTUAL_HISTORICAL_REPLAY"
)
_SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_REQUIRED_SYMBOLS = (
    "AUDJPY",
    "EURUSD",
    "GBPJPY",
    "GBPUSD",
    "NAS100",
    "XAUUSD",
)
_MINIMUM_ORDERS_PER_SYMBOL = 8


@dataclass(frozen=True, slots=True)
class Phase22ProviderCalibrationReceipt:
    artifact_sha256: str
    git_sha: str
    account_fingerprint_sha256: str
    observed_at: datetime
    status: str
    required_symbols: tuple[str, ...]
    distinct_entry_orders_by_symbol: tuple[tuple[str, int], ...]
    empirical_slippage_calibrated: bool
    execution_model_ready: bool
    execution_population_ready: bool
    created_positions_closed: bool
    minimum_volume_only: bool
    historical_provider_economics_claimed: bool
    historical_holdout_execution_claimed: bool
    holdout_outcomes_used: bool
    fundednext_touched: bool
    vps_touched: bool
    live_authorized: bool
    real_capital_authorized: bool
    productive_authority: bool
    blockers: tuple[str, ...]

    def __post_init__(self) -> None:
        if _SHA256_RE.fullmatch(self.artifact_sha256) is None:
            raise CiboCapitalManagementError(
                "Phase22 provider calibration artifact digest invalid"
            )
        if _SHA1_RE.fullmatch(self.git_sha) is None:
            raise CiboCapitalManagementError(
                "Phase22 provider calibration Git SHA invalid"
            )
        if (
            len(self.account_fingerprint_sha256) != 64
            or any(
                char not in "0123456789abcdef"
                for char in self.account_fingerprint_sha256
            )
        ):
            raise CiboCapitalManagementError(
                "Phase22 provider calibration account fingerprint invalid"
            )
        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise CiboCapitalManagementError(
                "Phase22 provider calibration timestamp must be timezone-aware"
            )
        if self.status != "READY":
            raise CiboCapitalManagementError(
                "Phase22 provider calibration must be READY"
            )
        if self.required_symbols != _REQUIRED_SYMBOLS:
            raise CiboCapitalManagementError(
                "Phase22 provider calibration symbol surface drift"
            )
        counts = dict(self.distinct_entry_orders_by_symbol)
        if tuple(sorted(counts)) != _REQUIRED_SYMBOLS:
            raise CiboCapitalManagementError(
                "Phase22 provider calibration count surface drift"
            )
        if any(
            counts[symbol] < _MINIMUM_ORDERS_PER_SYMBOL
            for symbol in _REQUIRED_SYMBOLS
        ):
            raise CiboCapitalManagementError(
                "Phase22 provider calibration population below minimum"
            )
        required_true = (
            self.empirical_slippage_calibrated,
            self.execution_model_ready,
            self.execution_population_ready,
            self.created_positions_closed,
            self.minimum_volume_only,
        )
        if not all(required_true):
            raise CiboCapitalManagementError(
                "Phase22 provider calibration readiness incomplete"
            )
        prohibited = (
            self.historical_provider_economics_claimed,
            self.historical_holdout_execution_claimed,
            self.holdout_outcomes_used,
            self.fundednext_touched,
            self.vps_touched,
            self.live_authorized,
            self.real_capital_authorized,
            self.productive_authority,
        )
        if any(prohibited):
            raise CiboCapitalManagementError(
                "Phase22 provider calibration governance contamination"
            )
        if self.blockers:
            raise CiboCapitalManagementError(
                "Phase22 provider calibration READY receipt cannot retain blockers"
            )

    def fingerprint(self) -> str:
        payload = asdict(self)
        payload["observed_at"] = self.observed_at.isoformat()
        raw = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return "sha256:" + hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True, slots=True)
class Phase22HistoricalReplayEconomicsAmendment:
    amendment_id: str
    candidate_id: str
    candidate_parameter_sha256: str
    phase20d_plan_sha256: str
    phase22_plan_sha256: str
    provider_calibration_sha256: str
    execution_economics_kind: str
    fresh_outcomes_emitted_before_amendment: bool
    holdout_outcomes_inspected_before_amendment: bool
    policy_changed: bool
    thresholds_changed: bool
    historical_broker_fills_claimed: bool
    current_demo_fills_relabelled_as_historical: bool
    fabricated_execution_evidence_allowed: bool
    provider_calibration_population_disjoint_from_holdout: bool
    downstream_replay_settlement_adapter_required: bool
    productive_authority: bool = False
    certification_claimed: bool = False

    def __post_init__(self) -> None:
        if self.amendment_id != AMENDMENT_ID:
            raise CiboCapitalManagementError(
                "Phase22 replay economics amendment identity drift"
            )
        if self.candidate_id != ACTIVE_USD60_HOLDOUT_CANDIDATE.candidate_id:
            raise CiboCapitalManagementError(
                "Phase22 replay economics candidate drift"
            )
        if (
            self.candidate_parameter_sha256
            != FROZEN_PHASE20_POLICY_CANDIDATE.parameter_sha256()
        ):
            raise CiboCapitalManagementError(
                "Phase22 replay economics parameter drift"
            )
        if self.phase20d_plan_sha256 != phase20d_qualification_plan_sha256():
            raise CiboCapitalManagementError(
                "Phase22 replay economics Phase20D threshold-plan drift"
            )
        if self.phase22_plan_sha256 != phase22_holdout_qualification_plan_sha256():
            raise CiboCapitalManagementError(
                "Phase22 replay economics Phase22 plan drift"
            )
        if _SHA256_RE.fullmatch(self.provider_calibration_sha256) is None:
            raise CiboCapitalManagementError(
                "Phase22 replay economics calibration digest invalid"
            )
        if self.execution_economics_kind != EXECUTION_ECONOMICS_KIND:
            raise CiboCapitalManagementError(
                "Phase22 replay economics kind drift"
            )
        prohibited = (
            self.fresh_outcomes_emitted_before_amendment,
            self.holdout_outcomes_inspected_before_amendment,
            self.policy_changed,
            self.thresholds_changed,
            self.historical_broker_fills_claimed,
            self.current_demo_fills_relabelled_as_historical,
            self.fabricated_execution_evidence_allowed,
            self.productive_authority,
            self.certification_claimed,
        )
        if any(prohibited):
            raise CiboCapitalManagementError(
                "Phase22 replay economics amendment violates pre-outcome governance"
            )
        if not self.provider_calibration_population_disjoint_from_holdout:
            raise CiboCapitalManagementError(
                "Phase22 replay economics calibration must be disjoint from holdout"
            )
        if not self.downstream_replay_settlement_adapter_required:
            raise CiboCapitalManagementError(
                "Phase22 replay economics amendment cannot bypass replay adapter"
            )

    def fingerprint(self) -> str:
        raw = json.dumps(
            asdict(self),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return "sha256:" + hashlib.sha256(raw).hexdigest()


def freeze_phase22_historical_replay_economics_amendment(
    *,
    provider_calibration: Phase22ProviderCalibrationReceipt,
    fresh_outcomes_emitted: bool,
    holdout_outcomes_inspected: bool,
) -> Phase22HistoricalReplayEconomicsAmendment:
    """Freeze provenance semantics without changing policy or thresholds."""

    if not isinstance(provider_calibration, Phase22ProviderCalibrationReceipt):
        raise CiboCapitalManagementError(
            "Phase22 replay amendment requires canonical provider calibration"
        )
    if type(fresh_outcomes_emitted) is not bool:
        raise CiboCapitalManagementError(
            "Phase22 replay amendment fresh outcome flag must be bool"
        )
    if type(holdout_outcomes_inspected) is not bool:
        raise CiboCapitalManagementError(
            "Phase22 replay amendment holdout inspection flag must be bool"
        )
    return Phase22HistoricalReplayEconomicsAmendment(
        amendment_id=AMENDMENT_ID,
        candidate_id=ACTIVE_USD60_HOLDOUT_CANDIDATE.candidate_id,
        candidate_parameter_sha256=(
            FROZEN_PHASE20_POLICY_CANDIDATE.parameter_sha256()
        ),
        phase20d_plan_sha256=phase20d_qualification_plan_sha256(),
        phase22_plan_sha256=phase22_holdout_qualification_plan_sha256(),
        provider_calibration_sha256=provider_calibration.fingerprint(),
        execution_economics_kind=EXECUTION_ECONOMICS_KIND,
        fresh_outcomes_emitted_before_amendment=fresh_outcomes_emitted,
        holdout_outcomes_inspected_before_amendment=holdout_outcomes_inspected,
        policy_changed=False,
        thresholds_changed=False,
        historical_broker_fills_claimed=False,
        current_demo_fills_relabelled_as_historical=False,
        fabricated_execution_evidence_allowed=False,
        provider_calibration_population_disjoint_from_holdout=True,
        downstream_replay_settlement_adapter_required=True,
    )
