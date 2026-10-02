"""Canonical Phase22 V4 historical replay decision/policy sealing.

The historical market clock remains 2015-2016 while the replay seal is created
post-Phase21 in 2026. Current provider observations are bound only as an
empirical counterfactual model; they are never represented as historical fills
or historical provider terms.
"""
# ruff: noqa: I001, E402

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, fields, is_dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any

from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_full_surface import AdvancedPortfolioEvidence
from qore.infrastructure.cibo_ce2i_opportunity_competition import (
    CapitalOpportunityCandidate,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_policy_store import (
    Phase20ForwardPolicyDecisionSeal,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    Phase20ForwardDecisionSeal,
)
from qore.infrastructure.cibo_ce2i_phase20_mpc import Phase20MpcKnownOption
from qore.infrastructure.cibo_ce2i_phase20_policy_candidate import (
    FROZEN_PHASE20_POLICY_CANDIDATE,
)
from qore.infrastructure.cibo_ce2i_phase20_train_prior import (
    build_frozen_train_expectation,
)
from qore.infrastructure.cibo_ce2i_regime_selector import CiboCapitalRegimeState
from qore.infrastructure.cibo_phase22_v4_historical_policy_replay import (
    Phase22HistoricalCapitalInput,
    Phase22HistoricalPolicyDecisionRecord,
    evaluate_phase22_historical_policy,
)
from qore.infrastructure.cibo_phase22_v4_source_receipt import (
    load_phase22_v4_source_receipt,
)

V4_SOURCE_RECEIPT = load_phase22_v4_source_receipt(
    Path("docs/research/CIBO-PHASE22-V4-SOURCE-RECEIPT.json")
)
V4_SOURCE_BINDINGS = V4_SOURCE_RECEIPT.bindings
from qore.infrastructure.cibo_phase22_provider_execution_calibration_receipt import (
    PHASE22_PROVIDER_EXECUTION_CALIBRATION_RECEIPT,
)
from qore.infrastructure.cibo_provider_economic_normalization import (
    ProviderEconomicObservation,
    normalize_provider_economics,
)

_EVIDENCE_KIND = "HISTORICAL_REPLAY_OBSERVED"
_V4_SOURCE_COLLECTOR_GIT_SHAS = (V4_SOURCE_RECEIPT.corpus_git_sha,)


@dataclass(frozen=True, slots=True)
class Phase22HistoricalReplayCandidateEvidence:
    capital_input: Phase22HistoricalCapitalInput
    provider_observation: ProviderEconomicObservation
    provider_evidence_id: str

    def __post_init__(self) -> None:
        if not isinstance(self.capital_input, Phase22HistoricalCapitalInput):
            raise CiboCapitalManagementError(
                "Phase22 replay candidate capital input invalid"
            )
        if not isinstance(self.provider_observation, ProviderEconomicObservation):
            raise CiboCapitalManagementError(
                "Phase22 replay candidate provider observation invalid"
            )
        if not self.provider_evidence_id:
            raise CiboCapitalManagementError(
                "Phase22 replay candidate provider evidence id required"
            )
        expected_model = PHASE22_PROVIDER_EXECUTION_CALIBRATION_RECEIPT.fingerprint()
        if self.capital_input.provider_model_sha256 != expected_model:
            raise CiboCapitalManagementError(
                "Phase22 replay candidate provider model lineage drift"
            )
        normalized = normalize_provider_economics(
            opportunity=self.capital_input.opportunity,
            observation=self.provider_observation,
        )
        if normalized.minimum_stop_risk_usd != (
            self.capital_input.minimum_stop_risk_usd
        ):
            raise CiboCapitalManagementError(
                "Phase22 replay candidate minimum stop-risk normalization drift"
            )
        if normalized.minimum_margin_usd != self.capital_input.minimum_margin_usd:
            raise CiboCapitalManagementError(
                "Phase22 replay candidate minimum margin normalization drift"
            )


@dataclass(frozen=True, slots=True)
class Phase22HistoricalReplaySealPair:
    decision: Phase20ForwardDecisionSeal
    policy: Phase20ForwardPolicyDecisionSeal
    policy_record: Phase22HistoricalPolicyDecisionRecord

    def __post_init__(self) -> None:
        if self.policy.evidence_sha256 != self.decision.evidence_sha256:
            raise CiboCapitalManagementError(
                "Phase22 replay decision/policy seal lineage mismatch"
            )
        if (
            tuple(self.policy.selected_signal_fingerprints)
            != _selected_fingerprints(self.policy_record)
        ):
            raise CiboCapitalManagementError(
                "Phase22 replay selected-signal seal drift"
            )


def seal_phase22_historical_replay_epoch(
    *,
    decision_epoch_id: str,
    market_decision_at: datetime,
    replay_sealed_at: datetime,
    seal_deadline_at: datetime,
    account_identity: CiboAccountCapitalIdentity,
    candidates: tuple[Phase22HistoricalReplayCandidateEvidence, ...],
    regime_state: CiboCapitalRegimeState,
    hard_risk_headroom_usd: Decimal,
    margin_headroom_usd: Decimal,
    concentration_limit_by_group: tuple[tuple[str, Decimal], ...],
    current_step: int,
    advanced_evidence: AdvancedPortfolioEvidence | None = None,
    known_options: tuple[Phase20MpcKnownOption, ...] = (),
    lab_allow_nonpositive_expectation: bool = False,
) -> Phase22HistoricalReplaySealPair:
    """Seal one historical epoch using the frozen policy and current provider model."""

    effective_advanced_evidence = (
        AdvancedPortfolioEvidence()
        if advanced_evidence is None
        else advanced_evidence
    )

    if not decision_epoch_id:
        raise CiboCapitalManagementError(
            "Phase22 replay decision epoch id required"
        )
    if not candidates:
        raise CiboCapitalManagementError(
            "Phase22 replay sealing requires at least one candidate"
        )
    for name, value in (
        ("market_decision_at", market_decision_at),
        ("replay_sealed_at", replay_sealed_at),
        ("seal_deadline_at", seal_deadline_at),
    ):
        if value.tzinfo is None or value.utcoffset() is None:
            raise CiboCapitalManagementError(
                f"Phase22 replay sealing {name} must be timezone-aware"
            )
    if seal_deadline_at < replay_sealed_at:
        raise CiboCapitalManagementError(
            "Phase22 replay seal deadline cannot predate physical seal"
        )

    provider_model = PHASE22_PROVIDER_EXECUTION_CALIBRATION_RECEIPT.fingerprint()
    if any(
        item.capital_input.provider_model_sha256 != provider_model
        for item in candidates
    ):
        raise CiboCapitalManagementError(
            "Phase22 replay sealing provider model set drift"
        )
    fingerprints = tuple(
        item.capital_input.opportunity.signal_fingerprint for item in candidates
    )
    if len(fingerprints) != len(set(fingerprints)):
        raise CiboCapitalManagementError(
            "Phase22 replay sealing duplicate signal fingerprint"
        )

    policy_record = evaluate_phase22_historical_policy(
        market_decision_at=market_decision_at,
        replay_sealed_at=replay_sealed_at,
        account_identity=account_identity,
        inputs=tuple(item.capital_input for item in candidates),
        regime_state=regime_state,
        hard_risk_headroom_usd=hard_risk_headroom_usd,
        margin_headroom_usd=margin_headroom_usd,
        concentration_limit_by_group=concentration_limit_by_group,
        current_step=current_step,
        advanced_evidence=effective_advanced_evidence,
        known_options=known_options,
        lab_allow_nonpositive_expectation=lab_allow_nonpositive_expectation,
    )

    candidate_rows: list[dict[str, object]] = []
    population_slots: list[dict[str, object]] = []
    for item in candidates:
        capital = item.capital_input
        opportunity = capital.opportunity
        expectation = build_frozen_train_expectation(
            trader_id=opportunity.trader_id,
            stop_risk_usd=capital.minimum_stop_risk_usd,
            as_of=market_decision_at,
        )
        candidate = CapitalOpportunityCandidate(
            signal_fingerprint=opportunity.signal_fingerprint,
            trader_id=opportunity.trader_id,
            qore_symbol=opportunity.qore_symbol,
            provider_symbol=opportunity.provider_symbol,
            decision_as_of=market_decision_at,
            expectation=expectation,
            stop_risk_usd=capital.minimum_stop_risk_usd,
            margin_usd=capital.minimum_margin_usd,
            concentration_group=capital.concentration_group,
            concentration_risk_usd=capital.concentration_risk_usd,
        )
        candidate_rows.append(
            {
                "provider_evidence_id": item.provider_evidence_id,
                "provider_model_sha256": provider_model,
                "provider_time_semantics": (
                    "CURRENT_EMPIRICAL_COUNTERFACTUAL_MODEL_NOT_HISTORICAL_TERMS"
                ),
                "opportunity": _canonical(opportunity),
                "provider_observation": _canonical(item.provider_observation),
                "candidate": _canonical(candidate),
            }
        )
        population_slots.append(
            {
                "slot_id": (
                    f"{opportunity.trader_id.value}|{opportunity.qore_symbol}|"
                    f"{decision_epoch_id}|{opportunity.signal_fingerprint}"
                ),
                "trader_id": opportunity.trader_id.value,
                "qore_symbol": opportunity.qore_symbol,
                "observed_at": market_decision_at.isoformat(),
                "disposition": "CANDIDATE",
                "reason": "frozen Trader opportunity present at historical epoch",
                "signal_fingerprint": opportunity.signal_fingerprint,
            }
        )

    source_lineage = {
        "source_receipt_sha256": V4_SOURCE_RECEIPT.fingerprint(),
        "collector_git_shas": list(_V4_SOURCE_COLLECTOR_GIT_SHAS),
        "multi_source_historical_holdout": True,
    }
    decision_payload = {
        "schema": "qore.cibo.phase22.historical-replay-decision.v1",
        "evidence_kind": _EVIDENCE_KIND,
        "decision_epoch_id": decision_epoch_id,
        "market_decision_at": market_decision_at.isoformat(),
        "replay_sealed_at": replay_sealed_at.isoformat(),
        "hard_risk_headroom_usd": format(hard_risk_headroom_usd, "f"),
        "margin_headroom_usd": format(margin_headroom_usd, "f"),
        "concentration_limit_by_group": [
            [name, format(value, "f")]
            for name, value in concentration_limit_by_group
        ],
        "population_slots": population_slots,
        "candidates": candidate_rows,
        "source_lineage": source_lineage,
        "provider_model_sha256": provider_model,
        "counterfactual_historical_replay": True,
        "historical_provider_terms_claimed": False,
        "historical_broker_fills_claimed": False,
        "outcome_present": False,
        "risk_authority": False,
        "execution_authority": False,
        "productive_authority": False,
    }
    decision_json = _json(decision_payload)
    evidence_sha = _sha256(decision_json)
    frozen = FROZEN_PHASE20_POLICY_CANDIDATE
    decision = Phase20ForwardDecisionSeal(
        evidence_id=f"phase22-replay-decision:{evidence_sha[7:]}",
        decision_epoch_id=decision_epoch_id,
        evidence_sha256=evidence_sha,
        decision_at=market_decision_at,
        candidate_id=frozen.candidate_id,
        code_sha=frozen.code_sha,
        parameter_sha256=frozen.parameter_sha256(),
        signal_fingerprints=fingerprints,
        canonical_payload_json=decision_json,
        collector_git_sha=None,
        sealed_at=replay_sealed_at,
        seal_deadline_at=seal_deadline_at,
    )

    policy_payload = {
        "schema": "qore.cibo.phase22.historical-replay-policy.v1",
        "evidence_sha256": evidence_sha,
        **_canonical(policy_record),
        "source_lineage": source_lineage,
        "provider_model_sha256": provider_model,
        "historical_provider_terms_claimed": False,
        "historical_broker_fills_claimed": False,
    }
    policy_json = _json(policy_payload)
    policy = Phase20ForwardPolicyDecisionSeal(
        evidence_sha256=evidence_sha,
        policy_record_sha256=_sha256(policy_json),
        allocator_disposition=policy_record.allocator_decision.disposition.value,
        selected_signal_fingerprints=_selected_fingerprints(policy_record),
        canonical_record_json=policy_json,
    )
    return Phase22HistoricalReplaySealPair(
        decision=decision,
        policy=policy,
        policy_record=policy_record,
    )


def _selected_fingerprints(
    record: Phase22HistoricalPolicyDecisionRecord,
) -> tuple[str, ...]:
    allocation = record.allocator_decision.allocation
    return (
        ()
        if allocation is None
        else tuple(allocation.selected_signal_fingerprints)
    )


def _json(value: object) -> str:
    return json.dumps(
        _canonical(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )


def _sha256(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _canonical(value: Any) -> Any:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: _canonical(getattr(value, field.name))
            for field in fields(value)
        }
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
