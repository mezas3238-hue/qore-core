"""Causal replay contracts for Shared↔Trader intelligence research."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime

from qore.infrastructure.core_stack_v2.shared_position_world_lineage import (
    SharedPositionEntryWorldRecord,
    SharedPositionWorldNowDelta,
)
from qore.infrastructure.core_stack_v2.shared_trader_intelligence import (
    SharedTraderIntelligenceSnapshot,
    SharedTraderIntelligenceValidationError,
    TraderSharedOpportunityAssessment,
)


@dataclass(frozen=True, slots=True)
class SharedTraderCausalReplayFrame:
    """What Shared/Trader/position state legally existed at one decision time."""

    frame_id: str
    decision_time: datetime
    shared_snapshot: SharedTraderIntelligenceSnapshot
    trader_assessment: TraderSharedOpportunityAssessment | None
    position_entry_world: SharedPositionEntryWorldRecord | None
    position_world_delta: SharedPositionWorldNowDelta | None
    source_data_fingerprints: tuple[str, ...]
    policy_fingerprints: tuple[str, ...]
    provenance_refs: tuple[str, ...]
    future_market_data_used: bool = False
    future_outcome_used: bool = False
    future_report_used: bool = False
    future_weather_used: bool = False
    future_roll_state_used: bool = False
    outcome_evidence_refs: tuple[str, ...] = ()
    productive_behavior_authority: bool = False

    def __post_init__(self) -> None:
        if not self.frame_id.strip():
            raise SharedTraderIntelligenceValidationError(
                "replay frame_id must be non-empty"
            )
        if self.decision_time.tzinfo is None:
            raise SharedTraderIntelligenceValidationError(
                "replay decision_time must be timezone-aware"
            )
        if self.decision_time.utcoffset() is None:
            raise SharedTraderIntelligenceValidationError(
                "replay decision_time must be timezone-aware"
            )
        if self.shared_snapshot.observed_at > self.decision_time:
            raise SharedTraderIntelligenceValidationError(
                "replay cannot consume Shared snapshot from the future"
            )
        if self.shared_snapshot.evidence_cutoff_at > self.decision_time:
            raise SharedTraderIntelligenceValidationError(
                "replay cannot consume future Shared evidence"
            )
        if self.trader_assessment is not None:
            if self.trader_assessment.assessed_at > self.decision_time:
                raise SharedTraderIntelligenceValidationError(
                    "replay cannot consume future Trader assessment"
                )
        if self.position_entry_world is not None:
            if self.position_entry_world.opened_at > self.decision_time:
                raise SharedTraderIntelligenceValidationError(
                    "replay cannot expose a future position"
                )
            if (
                self.position_entry_world.asset
                != self.shared_snapshot.asset
            ):
                raise SharedTraderIntelligenceValidationError(
                    "replay position asset must match Shared snapshot"
                )
        if self.position_world_delta is not None:
            if self.position_entry_world is None:
                raise SharedTraderIntelligenceValidationError(
                    "world delta requires position entry lineage"
                )
            if self.position_world_delta.compared_at > self.decision_time:
                raise SharedTraderIntelligenceValidationError(
                    "replay cannot consume future world delta"
                )
            if (
                self.position_world_delta.entry_world_record_id
                != self.position_entry_world.entry_world_record_id
            ):
                raise SharedTraderIntelligenceValidationError(
                    "replay world delta lineage mismatch"
                )
            if (
                self.position_world_delta.current_snapshot_id
                != self.shared_snapshot.snapshot_id
            ):
                raise SharedTraderIntelligenceValidationError(
                    "replay world delta must use frame Shared snapshot"
                )
        for name in (
            "source_data_fingerprints",
            "policy_fingerprints",
            "provenance_refs",
        ):
            refs = getattr(self, name)
            if not refs:
                raise SharedTraderIntelligenceValidationError(
                    f"{name} must be non-empty"
                )
            if refs != tuple(sorted(set(refs))):
                raise SharedTraderIntelligenceValidationError(
                    f"{name} must be unique and canonical"
                )
        for fingerprint in (
            self.source_data_fingerprints + self.policy_fingerprints
        ):
            if len(fingerprint) != 64:
                raise SharedTraderIntelligenceValidationError(
                    "replay fingerprints must be sha256 hex"
                )
            try:
                int(fingerprint, 16)
            except ValueError as exc:
                raise SharedTraderIntelligenceValidationError(
                    "replay fingerprints must be sha256 hex"
                ) from exc
        if self.outcome_evidence_refs:
            raise SharedTraderIntelligenceValidationError(
                "historical decision frame cannot contain outcome evidence"
            )
        if (
            self.future_market_data_used
            or self.future_outcome_used
            or self.future_report_used
            or self.future_weather_used
            or self.future_roll_state_used
        ):
            raise SharedTraderIntelligenceValidationError(
                "historical decision frame contains future information"
            )
        if self.productive_behavior_authority:
            raise SharedTraderIntelligenceValidationError(
                "causal replay cannot authorize productive behavior"
            )

    def fingerprint(self) -> str:
        trader_assessment_payload: dict[str, object] | None = None
        if self.trader_assessment is not None:
            trader_assessment_payload = asdict(self.trader_assessment)
            trader_assessment_payload["assessed_at"] = (
                self.trader_assessment.assessed_at.astimezone(UTC).isoformat()
            )
            trader_assessment_payload["disposition"] = (
                self.trader_assessment.disposition.value
            )
        payload = {
            "frame_id": self.frame_id,
            "decision_time": self.decision_time.astimezone(UTC).isoformat(),
            "shared_snapshot_fingerprint": (
                self.shared_snapshot.fingerprint()
            ),
            "trader_assessment": trader_assessment_payload,
            "position_entry_world_fingerprint": (
                None
                if self.position_entry_world is None
                else self.position_entry_world.fingerprint()
            ),
            "position_world_delta_fingerprint": (
                None
                if self.position_world_delta is None
                else self.position_world_delta.fingerprint()
            ),
            "source_data_fingerprints": self.source_data_fingerprints,
            "policy_fingerprints": self.policy_fingerprints,
            "provenance_refs": self.provenance_refs,
            "future_market_data_used": False,
            "future_outcome_used": False,
            "future_report_used": False,
            "future_weather_used": False,
            "future_roll_state_used": False,
            "outcome_evidence_refs": (),
            "productive_behavior_authority": False,
        }
        raw = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        return hashlib.sha256(raw.encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class SharedTraderCausalReplaySequence:
    replay_id: str
    dataset_fingerprint: str
    frames: tuple[SharedTraderCausalReplayFrame, ...]
    protected_holdout: bool
    protected_holdout_open_authorized: bool = False
    outcome_aware_policy_mutation: bool = False
    productive_behavior_authority: bool = False

    def __post_init__(self) -> None:
        if not self.replay_id.strip():
            raise SharedTraderIntelligenceValidationError(
                "replay_id must be non-empty"
            )
        if len(self.dataset_fingerprint) != 64:
            raise SharedTraderIntelligenceValidationError(
                "dataset_fingerprint must be sha256 hex"
            )
        try:
            int(self.dataset_fingerprint, 16)
        except ValueError as exc:
            raise SharedTraderIntelligenceValidationError(
                "dataset_fingerprint must be sha256 hex"
            ) from exc
        frame_ids = tuple(item.frame_id for item in self.frames)
        if len(frame_ids) != len(set(frame_ids)):
            raise SharedTraderIntelligenceValidationError(
                "replay frame ids must be unique"
            )
        ordered = tuple(
            sorted(
                self.frames,
                key=lambda item: (item.decision_time, item.frame_id),
            )
        )
        if self.frames != ordered:
            raise SharedTraderIntelligenceValidationError(
                "replay frames must be chronological and deterministic"
            )
        if self.protected_holdout and not self.protected_holdout_open_authorized:
            raise SharedTraderIntelligenceValidationError(
                "protected holdout replay requires explicit authorization"
            )
        if (
            self.outcome_aware_policy_mutation
            or self.productive_behavior_authority
        ):
            raise SharedTraderIntelligenceValidationError(
                "causal replay cannot mutate policy or productive behavior"
            )

    def fingerprint(self) -> str:
        payload = {
            "replay_id": self.replay_id,
            "dataset_fingerprint": self.dataset_fingerprint,
            "frames": [
                {
                    "frame_id": item.frame_id,
                    "fingerprint": item.fingerprint(),
                }
                for item in self.frames
            ],
            "protected_holdout": self.protected_holdout,
            "protected_holdout_open_authorized": (
                self.protected_holdout_open_authorized
            ),
            "outcome_aware_policy_mutation": False,
            "productive_behavior_authority": False,
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode()).hexdigest()
