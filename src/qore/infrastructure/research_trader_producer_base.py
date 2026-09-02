"""Shared deterministic machinery for bounded OHLC trader signal producers."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import ClassVar

from qore.functional.decisions import FunctionalDecision
from qore.infrastructure.market_data import OhlcSnapshot
from qore.infrastructure.research_evaluator_identity import (
    ResearchDecisionEvaluatorFamily,
    ResearchDecisionEvaluatorIdentity,
    ResearchDecisionEvaluatorSchemaVersion,
)
from qore.infrastructure.research_execution_session import QualifiedReplayObservation
from qore.infrastructure.research_lineage_errors import (
    ResearchEvaluatorIdentityMismatchError,
    ResearchLineageValidationError,
)
from qore.infrastructure.research_run import ResearchSoftwareRevision
from qore.infrastructure.research_schedule import ResearchStartPolicy
from qore.infrastructure.research_strategy_freeze import ResearchRunStrategyBinding
from qore.infrastructure.research_strategy_state import ResearchStrategyState
from qore.infrastructure.research_trader_signal import (
    TraderSignalSide,
    TraderSignalStateContent,
    build_trader_signal_decision,
    derive_trader_correlation_id,
    derive_trader_decision_id,
)


class BoundedOhlcTraderEvaluator:
    """Base class for deterministic OHLC-window trader decision evaluators.

    Subclasses provide a methodology family/revision, a derived lookback and
    window capacity, an immutable configuration fingerprint, and the concrete
    :meth:`_decide` predicate. This base owns the shared state/decision
    plumbing so each methodology stays a small falsifiable rule set.
    """

    _family: ClassVar[str]
    _schema_version: ClassVar[str] = "v1"
    _software_revision: ClassVar[str]

    config_fingerprint: str

    @property
    def required_lookback(self) -> int:
        raise NotImplementedError

    @property
    def window_capacity(self) -> int:
        raise NotImplementedError

    @property
    def identity(self) -> ResearchDecisionEvaluatorIdentity:
        return ResearchDecisionEvaluatorIdentity(
            family=ResearchDecisionEvaluatorFamily(self._family),
            schema_version=ResearchDecisionEvaluatorSchemaVersion(
                self._schema_version
            ),
            software_revision=ResearchSoftwareRevision(self._software_revision),
        )

    def _validate_binding(
        self,
        strategy_binding: ResearchRunStrategyBinding,
    ) -> None:
        if not isinstance(strategy_binding, ResearchRunStrategyBinding):
            raise ResearchLineageValidationError(
                "strategy_binding must be ResearchRunStrategyBinding"
            )
        revision = strategy_binding.run.software_revision.value
        if revision != self._software_revision:
            raise ResearchEvaluatorIdentityMismatchError(
                "strategy run software revision does not match evaluator revision"
            )

    def create_initial_state(
        self,
        *,
        strategy_binding: ResearchRunStrategyBinding,
        start_policy: ResearchStartPolicy,
    ) -> ResearchStrategyState:
        self._validate_binding(strategy_binding)
        if not isinstance(start_policy, ResearchStartPolicy):
            raise ResearchLineageValidationError(
                "start_policy must be ResearchStartPolicy"
            )
        return ResearchStrategyState(
            evaluator_identity=self.identity,
            evaluation_sequence_number=0,
            state_schema_version=self._schema_version,
            exact_content=TraderSignalStateContent(
                config_fingerprint=self.config_fingerprint,
                bars=(),
                last_closed_at=None,
            ),
        )

    @staticmethod
    def _extract_snapshots(
        observations: tuple[QualifiedReplayObservation, ...],
    ) -> tuple[OhlcSnapshot, ...]:
        if not isinstance(observations, tuple):
            raise ResearchLineageValidationError(
                "newly_visible_inputs must be a tuple"
            )
        snapshots: list[OhlcSnapshot] = []
        for item in observations:
            if not isinstance(item, QualifiedReplayObservation):
                raise ResearchLineageValidationError(
                    "every newly_visible_input must be QualifiedReplayObservation"
                )
            payload = item.observation.payload
            if not isinstance(payload, OhlcSnapshot):
                raise ResearchLineageValidationError(
                    "trader signal evaluator requires OhlcSnapshot payload"
                )
            snapshots.append(payload)
        return tuple(snapshots)

    @staticmethod
    def _append_bars(
        content: TraderSignalStateContent,
        snapshots: tuple[OhlcSnapshot, ...],
        capacity: int,
    ) -> tuple[tuple[tuple[float, float, float], ...], datetime | None]:
        bars = list(content.bars)
        last_closed_at = content.last_closed_at
        for snapshot in snapshots:
            if last_closed_at is not None and snapshot.closed_at <= last_closed_at:
                raise ResearchLineageValidationError(
                    "trader signal chronology conflict: bar closed_at is not "
                    "strictly increasing"
                )
            bars.append((snapshot.close, snapshot.high, snapshot.low))
            last_closed_at = snapshot.closed_at
        if len(bars) > capacity:
            bars = bars[-capacity:]
        return tuple(bars), last_closed_at

    def evaluate(
        self,
        *,
        strategy_binding: ResearchRunStrategyBinding,
        prior_state: ResearchStrategyState,
        newly_visible_inputs: tuple[QualifiedReplayObservation, ...],
        simulated_now: datetime,
    ) -> tuple[ResearchStrategyState, tuple[FunctionalDecision, ...]]:
        self._validate_binding(strategy_binding)
        if not isinstance(prior_state, ResearchStrategyState):
            raise ResearchLineageValidationError(
                "prior_state must be ResearchStrategyState"
            )
        if prior_state.evaluator_identity != self.identity:
            raise ResearchEvaluatorIdentityMismatchError(
                "prior_state evaluator identity does not match evaluator identity"
            )
        content = prior_state.exact_content
        if not isinstance(content, TraderSignalStateContent):
            raise ResearchLineageValidationError(
                "prior_state exact_content must be TraderSignalStateContent"
            )
        if content.config_fingerprint != self.config_fingerprint:
            raise ResearchEvaluatorIdentityMismatchError(
                "prior_state configuration fingerprint does not match evaluator config"
            )

        snapshots = self._extract_snapshots(newly_visible_inputs)
        bars, last_closed_at = self._append_bars(
            content,
            snapshots,
            self.window_capacity,
        )
        next_sequence = prior_state.evaluation_sequence_number + 1
        next_content = TraderSignalStateContent(
            config_fingerprint=self.config_fingerprint,
            bars=bars,
            last_closed_at=last_closed_at,
        )
        next_state = ResearchStrategyState(
            evaluator_identity=self.identity,
            evaluation_sequence_number=next_sequence,
            state_schema_version=self._schema_version,
            exact_content=next_content,
        )

        if len(bars) < self.required_lookback:
            return next_state, ()

        side, reason_code, summary, evidence = self._decide(bars)
        binding_fingerprint = strategy_binding.binding_fingerprint.value
        decision_id = derive_trader_decision_id(
            binding_fingerprint=binding_fingerprint,
            sequence_number=next_sequence,
            side=side,
            evidence=evidence,
        )
        decision = build_trader_signal_decision(
            decision_id=decision_id,
            timestamp=simulated_now,
            correlation_id=derive_trader_correlation_id(binding_fingerprint),
            side=side,
            reason_code=reason_code,
            summary=summary,
            evidence=evidence,
        )
        return next_state, (decision,)

    def _decide(
        self,
        bars: tuple[tuple[float, float, float], ...],
    ) -> tuple[TraderSignalSide, str, str, Mapping[str, str]]:
        raise NotImplementedError
