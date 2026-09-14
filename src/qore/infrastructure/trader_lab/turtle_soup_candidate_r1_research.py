"""Governed research-run provenance for Turtle Soup candidate R1.

This module binds source-faithful configuration and one frozen QORE experimental
management policy into a deterministic strategy-configuration identity, then
uses the repository-wide ``ResearchRunEvidence`` contract to bind datasets,
execution model, transaction costs, and exact software revision.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from re import fullmatch
from uuid import UUID, uuid5

from qore.infrastructure.historical_dataset import HistoricalDatasetManifest
from qore.infrastructure.research_run import (
    ResearchExecutionModelId,
    ResearchRandomnessMode,
    ResearchReplayPolicyVersion,
    ResearchRunError,
    ResearchRunEvidence,
    ResearchRunId,
    ResearchSoftwareRevision,
    ResearchStrategyConfigurationId,
    ResearchTransactionCostModelId,
    build_research_run_evidence,
)
from qore.infrastructure.trader_lab.turtle_soup_candidate_r1 import (
    RESEARCH_IDENTITY,
    TurtleSoupR1Config,
    TurtleSoupR1ValidationError,
)
from qore.infrastructure.trader_lab.turtle_soup_candidate_r1_management import (
    TurtleSoupR1ExperimentalPolicy,
)
from qore.kernel.result import Result

_SCHEMA = "qore.trader_lab.turtle_soup_candidate_r1.research_configuration.v1"
_REPLAY_POLICY = ResearchReplayPolicyVersion("turtle-soup-candidate-r1-development-v1")
_STRATEGY_NAMESPACE = UUID("54b8b7fb-bbe6-57c1-9d58-7291a4e9372f")
_SHA256 = r"[0-9a-f]{64}"


@dataclass(frozen=True, slots=True)
class TurtleSoupR1ResearchConfiguration:
    """One exact source configuration + experimental management policy."""

    source_config_fingerprint: str
    management_policy_fingerprint: str
    management_policy_id: str

    def __post_init__(self) -> None:
        if fullmatch(_SHA256, self.source_config_fingerprint) is None:
            raise TurtleSoupR1ValidationError(
                "source_config_fingerprint must be lowercase SHA-256"
            )
        if fullmatch(_SHA256, self.management_policy_fingerprint) is None:
            raise TurtleSoupR1ValidationError(
                "management_policy_fingerprint must be lowercase SHA-256"
            )
        if not self.management_policy_id:
            raise TurtleSoupR1ValidationError("management_policy_id must be non-empty")

    def fingerprint(self) -> str:
        payload = {
            "schema": _SCHEMA,
            "research_identity": RESEARCH_IDENTITY,
            "source_config_fingerprint": self.source_config_fingerprint,
            "management_policy_id": self.management_policy_id,
            "management_policy_fingerprint": self.management_policy_fingerprint,
            "management_provenance": "QORE_EXPERIMENTAL_MANAGEMENT",
        }
        encoded = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
        return sha256(encoded).hexdigest()

    def strategy_configuration_id(self) -> ResearchStrategyConfigurationId:
        """Derive stable UUID identity from the canonical combined fingerprint."""

        return ResearchStrategyConfigurationId(
            uuid5(_STRATEGY_NAMESPACE, self.fingerprint())
        )


def bind_research_configuration(
    *,
    source_config: TurtleSoupR1Config,
    management_policy: TurtleSoupR1ExperimentalPolicy,
) -> TurtleSoupR1ResearchConfiguration:
    if type(source_config) is not TurtleSoupR1Config:
        raise TurtleSoupR1ValidationError("source_config must be TurtleSoupR1Config")
    if type(management_policy) is not TurtleSoupR1ExperimentalPolicy:
        raise TurtleSoupR1ValidationError(
            "management_policy must be TurtleSoupR1ExperimentalPolicy"
        )
    return TurtleSoupR1ResearchConfiguration(
        source_config_fingerprint=source_config.fingerprint(),
        management_policy_fingerprint=management_policy.fingerprint(),
        management_policy_id=management_policy.policy_id.value,
    )


def build_turtle_soup_r1_development_run_evidence(
    *,
    run_id: ResearchRunId,
    created_at: datetime,
    datasets: tuple[HistoricalDatasetManifest, ...],
    simulated_start: datetime,
    simulated_end: datetime,
    source_config: TurtleSoupR1Config,
    management_policy: TurtleSoupR1ExperimentalPolicy,
    software_revision: ResearchSoftwareRevision,
    execution_model_id: ResearchExecutionModelId,
    transaction_cost_model_id: ResearchTransactionCostModelId,
) -> Result[ResearchRunEvidence, ResearchRunError]:
    """Bind every economically material development-replay input before replay."""

    if type(execution_model_id) is not ResearchExecutionModelId:
        raise TurtleSoupR1ValidationError(
            "development replay requires explicit ResearchExecutionModelId"
        )
    if type(transaction_cost_model_id) is not ResearchTransactionCostModelId:
        raise TurtleSoupR1ValidationError(
            "development replay requires explicit ResearchTransactionCostModelId"
        )
    binding = bind_research_configuration(
        source_config=source_config,
        management_policy=management_policy,
    )
    return build_research_run_evidence(
        run_id=run_id,
        created_at=created_at,
        datasets=datasets,
        replay_policy_version=_REPLAY_POLICY,
        simulated_start=simulated_start,
        simulated_end=simulated_end,
        strategy_configuration_id=binding.strategy_configuration_id(),
        software_revision=software_revision,
        execution_model_id=execution_model_id,
        transaction_cost_model_id=transaction_cost_model_id,
        randomness_mode=ResearchRandomnessMode.DETERMINISTIC,
        random_seed=None,
    )
