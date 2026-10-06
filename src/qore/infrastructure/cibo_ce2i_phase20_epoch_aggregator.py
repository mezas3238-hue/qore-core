"""Deterministic Phase20D portfolio decision-epoch aggregation.

The aggregator observes Trader/symbol slots before portfolio allocation. Every
expected slot must terminalize causally as a candidate or an explicit
non-candidate state. Once sealed, no candidate can be added.

Research-only: it does not size, reserve capital, authorize Risk or mutate a
broker.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from threading import RLock

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_epoch import (
    Phase20ForwardObservedOpportunity,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_evidence import (
    Phase20ForwardPopulationDisposition,
    Phase20ForwardPopulationSlotEvidence,
)


@dataclass(frozen=True, slots=True)
class Phase20DecisionEpochSlot:
    slot_id: str
    trader_id: TraderLineage
    qore_symbol: str

    def __post_init__(self) -> None:
        if not self.slot_id or not self.qore_symbol:
            raise CiboCapitalManagementError(
                "Phase20D epoch slot identity/symbol are required"
            )
        if type(self.trader_id) is not TraderLineage:
            raise CiboCapitalManagementError(
                "Phase20D epoch slot Trader must be canonical"
            )


@dataclass(frozen=True, slots=True)
class Phase20DecisionEpochTerminal:
    slot: Phase20DecisionEpochSlot
    observed_at: datetime
    disposition: Phase20ForwardPopulationDisposition
    reason: str
    opportunity: Phase20ForwardObservedOpportunity | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.slot, Phase20DecisionEpochSlot):
            raise CiboCapitalManagementError(
                "Phase20D terminal slot must be canonical"
            )
        _aware(self.observed_at, name="terminal observed_at")
        if type(self.disposition) is not Phase20ForwardPopulationDisposition:
            raise CiboCapitalManagementError(
                "Phase20D terminal disposition must be canonical"
            )
        if not self.reason:
            raise CiboCapitalManagementError(
                "Phase20D terminal reason is required"
            )
        if self.disposition is Phase20ForwardPopulationDisposition.CANDIDATE:
            if not isinstance(
                self.opportunity,
                Phase20ForwardObservedOpportunity,
            ):
                raise CiboCapitalManagementError(
                    "Phase20D candidate terminal needs observed opportunity"
                )
            envelope = self.opportunity.opportunity
            if (
                envelope.trader_id is not self.slot.trader_id
                or envelope.qore_symbol != self.slot.qore_symbol
            ):
                raise CiboCapitalManagementError(
                    "Phase20D candidate terminal does not match declared slot"
                )
            if self.opportunity.provider_observation.observed_at > self.observed_at:
                raise CiboCapitalManagementError(
                    "Phase20D provider observation cannot postdate slot terminal"
                )
        elif self.opportunity is not None:
            raise CiboCapitalManagementError(
                "Phase20D non-candidate terminal cannot carry opportunity"
            )

    def population_evidence(self) -> Phase20ForwardPopulationSlotEvidence:
        fingerprint = (
            self.opportunity.opportunity.signal_fingerprint
            if self.opportunity is not None
            else None
        )
        return Phase20ForwardPopulationSlotEvidence(
            slot_id=self.slot.slot_id,
            trader_id=self.slot.trader_id,
            qore_symbol=self.slot.qore_symbol,
            observed_at=self.observed_at,
            disposition=self.disposition,
            reason=self.reason,
            signal_fingerprint=fingerprint,
        )


@dataclass(frozen=True, slots=True)
class Phase20DecisionEpochBatch:
    decision_epoch_id: str
    opened_at: datetime
    deadline_at: datetime
    decision_at: datetime
    population_slots: tuple[Phase20ForwardPopulationSlotEvidence, ...]
    opportunities: tuple[Phase20ForwardObservedOpportunity, ...]

    def __post_init__(self) -> None:
        if not self.decision_epoch_id:
            raise CiboCapitalManagementError(
                "Phase20D batch decision epoch identity is required"
            )
        for name in ("opened_at", "deadline_at", "decision_at"):
            _aware(getattr(self, name), name=name)
        if self.deadline_at <= self.opened_at:
            raise CiboCapitalManagementError(
                "Phase20D epoch deadline must follow open"
            )
        if not self.population_slots:
            raise CiboCapitalManagementError(
                "Phase20D batch population cannot be empty"
            )
        if not (self.opened_at <= self.decision_at <= self.deadline_at):
            raise CiboCapitalManagementError(
                "Phase20D decision must occur inside epoch window"
            )
        if any(
            item.observed_at > self.decision_at
            for item in self.population_slots
        ):
            raise CiboCapitalManagementError(
                "Phase20D population cannot postdate decision"
            )


def build_phase20_decision_epoch_id(
    *,
    epoch_scope: str,
    opened_at: datetime,
    expected_slots: tuple[Phase20DecisionEpochSlot, ...],
) -> str:
    """Build a stable epoch identity before any Trader result is known."""

    if not epoch_scope:
        raise CiboCapitalManagementError(
            "Phase20D epoch scope is required"
        )
    _aware(opened_at, name="opened_at")
    _validate_expected_slots(expected_slots)
    payload = {
        "epoch_scope": epoch_scope,
        "opened_at": opened_at.isoformat(),
        "expected_slots": [
            {
                "slot_id": item.slot_id,
                "trader_id": item.trader_id.value,
                "qore_symbol": item.qore_symbol,
            }
            for item in sorted(
                expected_slots,
                key=lambda item: (
                    item.slot_id,
                    item.trader_id.value,
                    item.qore_symbol,
                ),
            )
        ],
    }
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return f"phase20d-epoch:{sha256(raw).hexdigest()}"


class Phase20DecisionEpochAggregator:
    """Thread-safe, single-seal accumulator for one causal portfolio epoch."""

    def __init__(
        self,
        *,
        epoch_scope: str,
        opened_at: datetime,
        deadline_at: datetime,
        expected_slots: tuple[Phase20DecisionEpochSlot, ...],
    ) -> None:
        _aware(opened_at, name="opened_at")
        _aware(deadline_at, name="deadline_at")
        if deadline_at <= opened_at:
            raise CiboCapitalManagementError(
                "Phase20D epoch deadline must follow open"
            )
        _validate_expected_slots(expected_slots)
        self._opened_at = opened_at
        self._deadline_at = deadline_at
        self._slots = {
            item.slot_id: item
            for item in expected_slots
        }
        self._terminals: dict[str, Phase20DecisionEpochTerminal] = {}
        self._decision_epoch_id = build_phase20_decision_epoch_id(
            epoch_scope=epoch_scope,
            opened_at=opened_at,
            expected_slots=expected_slots,
        )
        self._sealed: Phase20DecisionEpochBatch | None = None
        self._lock = RLock()

    @property
    def decision_epoch_id(self) -> str:
        return self._decision_epoch_id

    def record_candidate(
        self,
        *,
        slot_id: str,
        opportunity: Phase20ForwardObservedOpportunity,
        observed_at: datetime,
        reason: str = "VALID_TRADER_OPPORTUNITY",
    ) -> None:
        self._record(
            Phase20DecisionEpochTerminal(
                slot=self._slot(slot_id),
                observed_at=observed_at,
                disposition=Phase20ForwardPopulationDisposition.CANDIDATE,
                reason=reason,
                opportunity=opportunity,
            )
        )

    def record_non_candidate(
        self,
        *,
        slot_id: str,
        disposition: Phase20ForwardPopulationDisposition,
        observed_at: datetime,
        reason: str,
    ) -> None:
        if disposition is Phase20ForwardPopulationDisposition.CANDIDATE:
            raise CiboCapitalManagementError(
                "Phase20D candidate must use record_candidate"
            )
        self._record(
            Phase20DecisionEpochTerminal(
                slot=self._slot(slot_id),
                observed_at=observed_at,
                disposition=disposition,
                reason=reason,
            )
        )

    def seal(self, *, decision_at: datetime) -> Phase20DecisionEpochBatch:
        """Seal once; missing slots at deadline become explicit deadline misses."""

        _aware(decision_at, name="decision_at")
        with self._lock:
            if self._sealed is not None:
                if self._sealed.decision_at == decision_at:
                    return self._sealed
                raise CiboCapitalManagementError(
                    "Phase20D epoch already sealed at another decision time"
                )
            if decision_at < self._opened_at or decision_at > self._deadline_at:
                raise CiboCapitalManagementError(
                    "Phase20D decision time outside epoch window"
                )
            missing = tuple(
                slot
                for slot_id, slot in sorted(self._slots.items())
                if slot_id not in self._terminals
            )
            if missing and decision_at < self._deadline_at:
                raise CiboCapitalManagementError(
                    "Phase20D epoch cannot seal before all slots terminalize"
                )
            if missing:
                for slot in missing:
                    self._terminals[slot.slot_id] = (
                        Phase20DecisionEpochTerminal(
                            slot=slot,
                            observed_at=self._deadline_at,
                            disposition=(
                                Phase20ForwardPopulationDisposition
                                .DEADLINE_MISSED
                            ),
                            reason="DECISION_EPOCH_DEADLINE_MISSED",
                        )
                    )
            terminals = tuple(
                self._terminals[slot_id]
                for slot_id in sorted(self._slots)
            )
            if any(item.observed_at > decision_at for item in terminals):
                raise CiboCapitalManagementError(
                    "Phase20D terminal observation postdates decision"
                )
            population = tuple(
                item.population_evidence() for item in terminals
            )
            opportunities = tuple(
                sorted(
                    (
                        item.opportunity
                        for item in terminals
                        if item.opportunity is not None
                    ),
                    key=lambda item: (
                        item.opportunity.trader_id.value,
                        item.opportunity.qore_symbol,
                        item.opportunity.provider_symbol,
                        item.opportunity.signal_fingerprint,
                    ),
                )
            )
            self._sealed = Phase20DecisionEpochBatch(
                decision_epoch_id=self._decision_epoch_id,
                opened_at=self._opened_at,
                deadline_at=self._deadline_at,
                decision_at=decision_at,
                population_slots=population,
                opportunities=opportunities,
            )
            return self._sealed

    def _slot(self, slot_id: str) -> Phase20DecisionEpochSlot:
        if not slot_id:
            raise CiboCapitalManagementError(
                "Phase20D slot_id is required"
            )
        try:
            return self._slots[slot_id]
        except KeyError as error:
            raise CiboCapitalManagementError(
                "Phase20D result references undeclared epoch slot"
            ) from error

    def _record(self, terminal: Phase20DecisionEpochTerminal) -> None:
        with self._lock:
            if self._sealed is not None:
                raise CiboCapitalManagementError(
                    "Phase20D candidate/result cannot be added after epoch seal"
                )
            if terminal.observed_at < self._opened_at:
                raise CiboCapitalManagementError(
                    "Phase20D terminal cannot predate epoch open"
                )
            if terminal.observed_at > self._deadline_at:
                raise CiboCapitalManagementError(
                    "Phase20D terminal cannot arrive after epoch deadline"
                )
            previous = self._terminals.get(terminal.slot.slot_id)
            if previous is not None:
                if previous == terminal:
                    return
                raise CiboCapitalManagementError(
                    "Phase20D epoch slot already terminalized differently"
                )
            self._terminals[terminal.slot.slot_id] = terminal


def _validate_expected_slots(
    expected_slots: tuple[Phase20DecisionEpochSlot, ...],
) -> None:
    if not expected_slots:
        raise CiboCapitalManagementError(
            "Phase20D expected epoch slots cannot be empty"
        )
    if not all(
        isinstance(item, Phase20DecisionEpochSlot)
        for item in expected_slots
    ):
        raise CiboCapitalManagementError(
            "Phase20D expected slots must be canonical"
        )
    ids = tuple(item.slot_id for item in expected_slots)
    if len(ids) != len(set(ids)):
        raise CiboCapitalManagementError(
            "Phase20D expected slot ids must be unique"
        )
    keys = tuple(
        (item.trader_id, item.qore_symbol)
        for item in expected_slots
    )
    if len(keys) != len(set(keys)):
        raise CiboCapitalManagementError(
            "Phase20D expected Trader/symbol slots must be unique"
        )


def _aware(value: datetime, *, name: str) -> None:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise CiboCapitalManagementError(
            f"Phase20D {name} must be timezone-aware"
        )
