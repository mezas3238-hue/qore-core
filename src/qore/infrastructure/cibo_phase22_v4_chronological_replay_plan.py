"""Causal Phase22 V4 replay plan separating predecision state from fresh outcomes.

The builder receives the already-claimed 7/7 fresh batch only after Trader
execution, but it produces two disjoint surfaces:

1. decision epochs containing strictly predecision geometry/provider/capital
   inputs consumed by CIBO; and
2. outcome events carrying exit-time structural results consumed only by
   chronological settlement.

Changing a future outcome must never change a decision-epoch fingerprint.
"""
# ruff: noqa: I001, E402

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_phase22_v4_execution_inputs import (
    Phase22SealedFreshBatchInput,
)
from qore.infrastructure.cibo_phase22_fresh_capital_projection import (
    Phase22FreshCapitalProjection,
)
from qore.infrastructure.cibo_phase22_trader_parity_manifest import (
    CANONICAL_PHASE22_TRADER_IDS,
)


@dataclass(frozen=True, slots=True)
class Phase22PredecisionCandidate:
    signal_fingerprint: str
    trader_id: str
    qore_symbol: str
    signal_at: datetime
    entry_at: datetime
    projection: Phase22FreshCapitalProjection

    def __post_init__(self) -> None:
        opportunity = self.projection.candidate.capital_input.opportunity
        if (
            self.signal_fingerprint != opportunity.signal_fingerprint
            or self.trader_id != opportunity.trader_id.value
            or self.qore_symbol != opportunity.qore_symbol
        ):
            raise CiboCapitalManagementError(
                "Phase22 replay-plan candidate/projection lineage drift"
            )
        _aware(self.signal_at, "signal_at")
        _aware(self.entry_at, "entry_at")
        if self.entry_at < self.signal_at:
            raise CiboCapitalManagementError(
                "Phase22 replay-plan entry precedes signal"
            )

    def payload(self) -> dict[str, object]:
        capital = self.projection.candidate.capital_input
        opportunity = capital.opportunity
        envelope = self.projection.provider_envelope
        return {
            "signal_fingerprint": self.signal_fingerprint,
            "trader_id": self.trader_id,
            "qore_symbol": self.qore_symbol,
            "signal_at": self.signal_at.isoformat(),
            "entry_at": self.entry_at.isoformat(),
            "provider_symbol": opportunity.provider_symbol,
            "side": opportunity.side,
            "entry_type": opportunity.entry_type,
            "intended_entry": _decimal(opportunity.intended_entry),
            "structural_stop": _decimal(opportunity.stop_loss),
            "technical_target": _decimal(opportunity.take_profit),
            "stop_loss_per_volume": _decimal(
                opportunity.stop_loss_per_volume
            ),
            "margin_per_volume": _decimal(opportunity.margin_per_volume),
            "minimum_volume": _decimal(opportunity.minimum_volume),
            "maximum_volume": _decimal(opportunity.maximum_volume),
            "volume_step": _decimal(opportunity.volume_step),
            "minimum_execution_steps": opportunity.minimum_execution_steps,
            "minimum_stop_risk_usd": _decimal(
                capital.minimum_stop_risk_usd
            ),
            "minimum_margin_usd": _decimal(capital.minimum_margin_usd),
            "concentration_group": capital.concentration_group,
            "concentration_risk_usd": _decimal(
                capital.concentration_risk_usd
            ),
            "provider_model_sha256": capital.provider_model_sha256,
            "provider_numeric_freeze_sha256": (
                self.projection.provider_numeric_freeze_sha256
            ),
            "decision_provider_cost_proxy_usd": _decimal(
                envelope.minimum_execution_cost_usd
            ),
            "provider_observed_at": envelope.observed_at.isoformat(),
            "future_outcome_fields_present": False,
        }

    def fingerprint(self) -> str:
        return _sha(self.payload())


@dataclass(frozen=True, slots=True)
class Phase22DecisionEpochPlan:
    decision_epoch_id: str
    market_decision_at: datetime
    candidates: tuple[Phase22PredecisionCandidate, ...]

    def __post_init__(self) -> None:
        if not self.decision_epoch_id:
            raise CiboCapitalManagementError(
                "Phase22 replay-plan epoch id required"
            )
        _aware(self.market_decision_at, "market_decision_at")
        if not self.candidates:
            raise CiboCapitalManagementError(
                "Phase22 replay-plan epoch requires candidates"
            )
        fingerprints = tuple(
            item.signal_fingerprint for item in self.candidates
        )
        if len(fingerprints) != len(set(fingerprints)):
            raise CiboCapitalManagementError(
                "Phase22 replay-plan duplicate signal in epoch"
            )
        if any(
            item.signal_at != self.market_decision_at
            for item in self.candidates
        ):
            raise CiboCapitalManagementError(
                "Phase22 replay-plan epoch signal-time drift"
            )

    def payload(self) -> dict[str, object]:
        return {
            "decision_epoch_id": self.decision_epoch_id,
            "market_decision_at": self.market_decision_at.isoformat(),
            "candidates": [item.payload() for item in self.candidates],
            "outcomes_present": False,
            "risk_authority": False,
            "execution_authority": False,
            "productive_authority": False,
        }

    def fingerprint(self) -> str:
        return _sha(self.payload())


@dataclass(frozen=True, slots=True)
class Phase22OutcomeEvent:
    signal_fingerprint: str
    trader_id: str
    qore_symbol: str
    entry_at: datetime
    exit_at: datetime
    gross_structural_outcome_r: Decimal
    exit_reason: str

    def __post_init__(self) -> None:
        if not self.signal_fingerprint or not self.trader_id or not self.qore_symbol:
            raise CiboCapitalManagementError(
                "Phase22 replay-plan outcome lineage required"
            )
        _aware(self.entry_at, "entry_at")
        _aware(self.exit_at, "exit_at")
        if self.exit_at <= self.entry_at:
            raise CiboCapitalManagementError(
                "Phase22 replay-plan outcome exit must follow entry"
            )
        if (
            not isinstance(self.gross_structural_outcome_r, Decimal)
            or not self.gross_structural_outcome_r.is_finite()
        ):
            raise CiboCapitalManagementError(
                "Phase22 replay-plan structural outcome must be finite"
            )
        if not self.exit_reason:
            raise CiboCapitalManagementError(
                "Phase22 replay-plan exit reason required"
            )

    def payload(self) -> dict[str, object]:
        return {
            "signal_fingerprint": self.signal_fingerprint,
            "trader_id": self.trader_id,
            "qore_symbol": self.qore_symbol,
            "entry_at": self.entry_at.isoformat(),
            "exit_at": self.exit_at.isoformat(),
            "gross_structural_outcome_r": _decimal(
                self.gross_structural_outcome_r
            ),
            "exit_reason": self.exit_reason,
        }

    def fingerprint(self) -> str:
        return _sha(self.payload())


@dataclass(frozen=True, slots=True)
class Phase22ChronologicalReplayPlan:
    fresh_batch_sha256: str
    epochs: tuple[Phase22DecisionEpochPlan, ...]
    outcome_events: tuple[Phase22OutcomeEvent, ...]
    trader_ids: tuple[str, ...]
    future_outcomes_excluded_from_epoch_hashes: bool = True
    productive_authority: bool = False

    def __post_init__(self) -> None:
        _sha256(self.fresh_batch_sha256, "fresh_batch_sha256")
        if not self.epochs or not self.outcome_events:
            raise CiboCapitalManagementError(
                "Phase22 chronological replay requires epochs and outcomes"
            )
        if self.trader_ids != CANONICAL_PHASE22_TRADER_IDS:
            raise CiboCapitalManagementError(
                "Phase22 chronological replay requires exact 7/7 Traders"
            )
        epoch_times = tuple(item.market_decision_at for item in self.epochs)
        if epoch_times != tuple(sorted(epoch_times)):
            raise CiboCapitalManagementError(
                "Phase22 chronological replay epochs are not ordered"
            )
        outcome_times = tuple(item.exit_at for item in self.outcome_events)
        if outcome_times != tuple(sorted(outcome_times)):
            raise CiboCapitalManagementError(
                "Phase22 chronological replay outcomes are not ordered"
            )
        epoch_signals = {
            candidate.signal_fingerprint
            for epoch in self.epochs
            for candidate in epoch.candidates
        }
        outcome_signals = {
            item.signal_fingerprint for item in self.outcome_events
        }
        if epoch_signals != outcome_signals:
            raise CiboCapitalManagementError(
                "Phase22 chronological replay decision/outcome surface drift"
            )
        if (
            not self.future_outcomes_excluded_from_epoch_hashes
            or self.productive_authority
        ):
            raise CiboCapitalManagementError(
                "Phase22 chronological replay governance drift"
            )

    def predecision_fingerprint(self) -> str:
        return _sha(
            {
                "fresh_batch_sha256": self.fresh_batch_sha256,
                "epochs": [
                    {
                        "decision_epoch_id": item.decision_epoch_id,
                        "fingerprint": item.fingerprint(),
                    }
                    for item in self.epochs
                ],
                "trader_ids": list(self.trader_ids),
                "future_outcomes_excluded_from_epoch_hashes": True,
            }
        )

    def outcome_schedule_fingerprint(self) -> str:
        return _sha(
            {
                "fresh_batch_sha256": self.fresh_batch_sha256,
                "outcomes": [
                    item.fingerprint() for item in self.outcome_events
                ],
            }
        )


def build_phase22_chronological_replay_plan(
    *,
    fresh: Phase22SealedFreshBatchInput,
    projections: tuple[Phase22FreshCapitalProjection, ...],
) -> Phase22ChronologicalReplayPlan:
    """Create a causal epoch stream plus a disjoint settlement schedule."""

    if not isinstance(fresh, Phase22SealedFreshBatchInput):
        raise CiboCapitalManagementError(
            "Phase22 chronological replay requires sealed fresh batch"
        )
    if any(
        not isinstance(item, Phase22FreshCapitalProjection)
        for item in projections
    ):
        raise CiboCapitalManagementError(
            "Phase22 chronological replay projections invalid"
        )

    opportunities = fresh.batch.opportunities
    if len(projections) != len(opportunities):
        raise CiboCapitalManagementError(
            "Phase22 chronological replay projection count drift"
        )
    projected = {
        item.candidate.capital_input.opportunity.signal_fingerprint: item
        for item in projections
    }
    if len(projected) != len(projections):
        raise CiboCapitalManagementError(
            "Phase22 chronological replay duplicate projection signal"
        )

    epoch_rows: dict[datetime, list[Phase22PredecisionCandidate]] = {}
    outcomes: list[Phase22OutcomeEvent] = []
    represented: set[str] = set()
    for opportunity in opportunities:
        projection = projected.get(opportunity.signal_fingerprint)
        if projection is None:
            raise CiboCapitalManagementError(
                "Phase22 chronological replay missing projection"
            )
        candidate = Phase22PredecisionCandidate(
            signal_fingerprint=opportunity.signal_fingerprint,
            trader_id=opportunity.trader_id.value,
            qore_symbol=opportunity.qore_symbol,
            signal_at=opportunity.signal_at,
            entry_at=opportunity.entry_at,
            projection=projection,
        )
        epoch_rows.setdefault(opportunity.signal_at, []).append(candidate)
        outcomes.append(
            Phase22OutcomeEvent(
                signal_fingerprint=opportunity.signal_fingerprint,
                trader_id=opportunity.trader_id.value,
                qore_symbol=opportunity.qore_symbol,
                entry_at=opportunity.entry_at,
                exit_at=opportunity.exit_at,
                gross_structural_outcome_r=(
                    opportunity.gross_structural_outcome_r
                ),
                exit_reason=opportunity.exit_reason,
            )
        )
        represented.add(opportunity.trader_id.value)

    # The claimed batch preserves the exact 7/7 lane surface even when a lane
    # legitimately emits zero executable opportunities. Population maturity is
    # preregistered in Phase20/22 qualification readiness (global lineages and
    # minimum outcomes per lineage); do not turn an insufficient population
    # into an orchestration crash before NOT_READY can be recorded.
    _ = represented

    epochs = []
    for index, market_at in enumerate(sorted(epoch_rows), start=1):
        candidates = tuple(
            sorted(
                epoch_rows[market_at],
                key=lambda item: (
                    item.trader_id,
                    item.qore_symbol,
                    item.signal_fingerprint,
                ),
            )
        )
        material = {
            "index": index,
            "market_decision_at": market_at.isoformat(),
            "signals": [item.signal_fingerprint for item in candidates],
        }
        epochs.append(
            Phase22DecisionEpochPlan(
                decision_epoch_id=(
                    "phase22-v4-epoch:"
                    + hashlib.sha256(
                        json.dumps(
                            material,
                            sort_keys=True,
                            separators=(",", ":"),
                        ).encode("utf-8")
                    ).hexdigest()
                ),
                market_decision_at=market_at,
                candidates=candidates,
            )
        )

    ordered_outcomes = tuple(
        sorted(
            outcomes,
            key=lambda item: (
                item.exit_at,
                item.entry_at,
                item.signal_fingerprint,
            ),
        )
    )
    return Phase22ChronologicalReplayPlan(
        fresh_batch_sha256=fresh.declared_batch_sha256,
        epochs=tuple(epochs),
        outcome_events=ordered_outcomes,
        trader_ids=CANONICAL_PHASE22_TRADER_IDS,
    )


def _decimal(value: Decimal) -> str:
    return format(value, "f")


def _aware(value: datetime, name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise CiboCapitalManagementError(
            f"Phase22 replay-plan {name} must be timezone-aware"
        )


def _sha(payload: dict[str, Any]) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _sha256(value: str, name: str) -> None:
    if (
        not isinstance(value, str)
        or not value.startswith("sha256:")
        or len(value) != 71
        or any(char not in "0123456789abcdef" for char in value[7:])
    ):
        raise CiboCapitalManagementError(
            f"Phase22 replay-plan {name} invalid"
        )
