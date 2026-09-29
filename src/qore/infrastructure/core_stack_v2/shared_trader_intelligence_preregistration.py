"""Preregistration contract for historical proactive Shared↔Trader research."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import StrEnum

from qore.infrastructure.core_stack_v2.shared_trader_intelligence import (
    SharedTraderIntelligenceValidationError,
)


class SharedSTIResearchQuestion(StrEnum):
    OPPORTUNITY_DISCOVERY = "OPPORTUNITY_DISCOVERY"
    REGIME_TRANSITION = "REGIME_TRANSITION"
    CONTINUATION_POSITIVE_TAIL = "CONTINUATION_POSITIVE_TAIL"
    POSITION_THREAT = "POSITION_THREAT"


@dataclass(frozen=True, slots=True)
class SharedSTIHistoricalStudyPreregistration:
    """Freeze a development/validation STI study before outcome inspection."""

    preregistration_id: str
    version: str
    frozen_at: datetime
    trader_id: str
    trader_version: str
    trader_config_fingerprint: str
    dataset_fingerprint: str
    opportunity_universe_fingerprint: str
    materiality_policy_fingerprint: str
    control_policy_fingerprint: str
    treatment_policy_fingerprint: str
    split_identity: str
    research_questions: tuple[SharedSTIResearchQuestion, ...]
    markets: tuple[str, ...]
    horizons: tuple[str, ...]
    selection_rule_ref: str
    threshold_spec_ref: str
    metric_definition_refs: tuple[str, ...]
    stress_protocol_ref: str
    temporal_replication_protocol_ref: str
    source_evidence_refs: tuple[str, ...]
    selection_rules_frozen: bool = True
    thresholds_frozen: bool = True
    development_evidence_only: bool = True
    protected_certification_holdout_opened: bool = False
    protected_certification_holdout_fingerprint: str | None = None
    outcome_aware_policy_mutation_authorized: bool = False
    productive_behavior_authority: bool = False

    def __post_init__(self) -> None:
        for name in (
            "preregistration_id",
            "version",
            "trader_id",
            "trader_version",
            "split_identity",
            "selection_rule_ref",
            "threshold_spec_ref",
            "stress_protocol_ref",
            "temporal_replication_protocol_ref",
        ):
            if not str(getattr(self, name)).strip():
                raise SharedTraderIntelligenceValidationError(
                    f"{name} must be non-empty"
                )

        if self.frozen_at.tzinfo is None or self.frozen_at.utcoffset() is None:
            raise SharedTraderIntelligenceValidationError(
                "preregistration frozen_at must be timezone-aware"
            )

        fingerprint_fields = (
            "trader_config_fingerprint",
            "dataset_fingerprint",
            "opportunity_universe_fingerprint",
            "materiality_policy_fingerprint",
            "control_policy_fingerprint",
            "treatment_policy_fingerprint",
        )
        for name in fingerprint_fields:
            value = str(getattr(self, name))
            if len(value) != 64:
                raise SharedTraderIntelligenceValidationError(
                    f"{name} must be sha256 hex"
                )
            try:
                int(value, 16)
            except ValueError as exc:
                raise SharedTraderIntelligenceValidationError(
                    f"{name} must be sha256 hex"
                ) from exc

        if self.control_policy_fingerprint == self.treatment_policy_fingerprint:
            raise SharedTraderIntelligenceValidationError(
                "control and treatment policy fingerprints must differ"
            )

        canonical_questions = tuple(
            sorted(set(self.research_questions), key=lambda item: item.value)
        )
        if (
            not self.research_questions
            or self.research_questions != canonical_questions
        ):
            raise SharedTraderIntelligenceValidationError(
                "research questions must be non-empty, unique and canonical"
            )

        for name in ("markets", "horizons", "metric_definition_refs", "source_evidence_refs"):
            values = getattr(self, name)
            if not values or values != tuple(sorted(set(values))):
                raise SharedTraderIntelligenceValidationError(
                    f"{name} must be non-empty, unique and canonical"
                )

        if not self.selection_rules_frozen or not self.thresholds_frozen:
            raise SharedTraderIntelligenceValidationError(
                "preregistration must freeze selection rules and thresholds"
            )
        if not self.development_evidence_only:
            raise SharedTraderIntelligenceValidationError(
                "initial STI preregistration is development/validation only"
            )
        if (
            self.protected_certification_holdout_opened
            or self.protected_certification_holdout_fingerprint is not None
        ):
            raise SharedTraderIntelligenceValidationError(
                "STI preregistration cannot open or identify protected certification holdout"
            )
        if self.outcome_aware_policy_mutation_authorized:
            raise SharedTraderIntelligenceValidationError(
                "STI preregistration cannot authorize outcome-aware mutation"
            )
        if self.productive_behavior_authority:
            raise SharedTraderIntelligenceValidationError(
                "STI preregistration cannot authorize productive behavior"
            )

    def fingerprint(self) -> str:
        payload = asdict(self)
        payload["frozen_at"] = self.frozen_at.astimezone(UTC).isoformat()
        payload["research_questions"] = tuple(
            item.value for item in self.research_questions
        )
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode()).hexdigest()
