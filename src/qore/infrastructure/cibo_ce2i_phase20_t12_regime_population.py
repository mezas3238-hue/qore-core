"""Forward causal-regime population audit for CE2I T12.

Phase19M remains immutable historical evidence: five lineages had the shared
historical schema, VT31 had a bespoke unmapped schema and VT08 lacked the
shared schema. This module does not reinterpret or backfill those rows.

Instead it audits fresh Phase20 FORWARD_OBSERVED decisions, where all runtime
paths emit the same CiboCapitalRegimeState contract. Coverage is attributed to
the Trader lineages present in each sealed population manifest. Current
capital/Risk snapshot bindings and provider-condition state are also checked.

No outcomes are read. No regime thresholds are fit. Structural 7/7 forward
coverage does not itself calibrate T12 or prove OOS regime utility.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase19_portfolio_replay import (
    PHASE19_REQUIRED_TRADERS,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    Phase20ForwardDecisionSeal,
    VersionedPhase20ForwardEvidenceBook,
)
from qore.infrastructure.cibo_ce2i_phase20_policy_candidate import (
    FROZEN_PHASE20_POLICY_CANDIDATE,
)
from qore.infrastructure.cibo_ce2i_regime_selector import (
    CorrelationState,
    LiquidityState,
    ProviderCondition,
    VolatilityState,
)

FORWARD_CANONICAL_REGIME_FIELDS = (
    "liquidity",
    "volatility",
    "correlation",
    "provider_condition",
    "risk_utilization",
    "margin_utilization",
    "drawdown_utilization",
    "opportunity_count",
    "position_path_adverse",
    "evidence_stale",
)


@dataclass(frozen=True, slots=True)
class Phase20T12LineageRegimeCoverage:
    trader_id: TraderLineage
    decision_epochs: int
    canonical_regime_epochs: int
    account_risk_snapshot_bound_epochs: int
    provider_condition_bound_epochs: int

    def __post_init__(self) -> None:
        if self.trader_id not in PHASE19_REQUIRED_TRADERS:
            raise CiboCapitalManagementError(
                "Phase20 T12 lineage is outside seven-Trader CIBO universe"
            )
        for name in (
            "decision_epochs",
            "canonical_regime_epochs",
            "account_risk_snapshot_bound_epochs",
            "provider_condition_bound_epochs",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value < 0
            ):
                raise CiboCapitalManagementError(
                    f"Phase20 T12 {name} must be non-negative int"
                )
            if name != "decision_epochs" and value > self.decision_epochs:
                raise CiboCapitalManagementError(
                    f"Phase20 T12 {name} exceeds lineage epochs"
                )

    @property
    def structurally_complete(self) -> bool:
        return (
            self.decision_epochs > 0
            and self.canonical_regime_epochs == self.decision_epochs
            and self.account_risk_snapshot_bound_epochs
            == self.decision_epochs
            and self.provider_condition_bound_epochs
            == self.decision_epochs
        )


@dataclass(frozen=True, slots=True)
class Phase20T12RegimePopulationAudit:
    usable_forward_epochs: int
    canonical_regime_epochs: int
    account_risk_snapshot_bound_epochs: int
    provider_condition_bound_epochs: int
    represented_lineages: tuple[TraderLineage, ...]
    canonical_lineages: tuple[TraderLineage, ...]
    noncanonical_lineages: tuple[TraderLineage, ...]
    missing_lineages: tuple[TraderLineage, ...]
    lineage_coverage: tuple[Phase20T12LineageRegimeCoverage, ...]
    forward_schema_7_of_7: bool
    burned_phase19_reinterpreted: bool
    fresh_oos_generalization_demonstrated: bool
    blockers: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in (
            "usable_forward_epochs",
            "canonical_regime_epochs",
            "account_risk_snapshot_bound_epochs",
            "provider_condition_bound_epochs",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value < 0
            ):
                raise CiboCapitalManagementError(
                    f"Phase20 T12 {name} must be non-negative int"
                )
        required = set(PHASE19_REQUIRED_TRADERS)
        for name in (
            "represented_lineages",
            "canonical_lineages",
            "noncanonical_lineages",
            "missing_lineages",
        ):
            values = getattr(self, name)
            if len(values) != len(set(values)) or not set(values).issubset(
                required
            ):
                raise CiboCapitalManagementError(
                    f"Phase20 T12 {name} contains invalid lineages"
                )
        coverage_traders = tuple(
            item.trader_id for item in self.lineage_coverage
        )
        if set(coverage_traders) != required or len(coverage_traders) != len(
            required
        ):
            raise CiboCapitalManagementError(
                "Phase20 T12 coverage must contain all seven lineages"
            )
        if self.burned_phase19_reinterpreted:
            raise CiboCapitalManagementError(
                "Phase20 T12 cannot reinterpret burned Phase19 evidence"
            )
        if self.fresh_oos_generalization_demonstrated:
            raise CiboCapitalManagementError(
                "Phase20 T12 population audit cannot demonstrate OOS utility"
            )
        if self.forward_schema_7_of_7 != (
            set(self.canonical_lineages) == required
        ):
            raise CiboCapitalManagementError(
                "Phase20 T12 7/7 structural flag drift"
            )


def assess_phase20_t12_regime_population(
    evidence_book: VersionedPhase20ForwardEvidenceBook,
) -> Phase20T12RegimePopulationAudit:
    """Audit the common causal regime schema without reading outcomes."""

    if not isinstance(evidence_book, VersionedPhase20ForwardEvidenceBook):
        raise CiboCapitalManagementError(
            "Phase20 T12 requires canonical forward evidence book"
        )

    counters: dict[TraderLineage, list[int]] = {
        trader: [0, 0, 0, 0] for trader in PHASE19_REQUIRED_TRADERS
    }
    usable_epochs = 0
    canonical_epochs = 0
    snapshot_epochs = 0
    provider_epochs = 0

    for decision in sorted(
        evidence_book.decisions,
        key=lambda item: (item.decision_at, item.evidence_sha256),
    ):
        if not _usable(decision):
            continue
        payload = _payload(decision)
        slots = payload.get("population_slots")
        if not isinstance(slots, list) or not slots:
            raise CiboCapitalManagementError(
                "Phase20 T12 forward population manifest is invalid"
            )
        lineages = _lineages(slots)
        regime_ok = _canonical_regime(payload)
        snapshots_ok = _snapshots_bound(payload, decision)
        provider_ok = _provider_condition_bound(payload)
        usable_epochs += 1
        if regime_ok:
            canonical_epochs += 1
        if snapshots_ok:
            snapshot_epochs += 1
        if provider_ok:
            provider_epochs += 1
        for trader in lineages:
            counts = counters[trader]
            counts[0] += 1
            counts[1] += int(regime_ok)
            counts[2] += int(snapshots_ok)
            counts[3] += int(provider_ok)

    coverage = tuple(
        Phase20T12LineageRegimeCoverage(
            trader_id=trader,
            decision_epochs=counters[trader][0],
            canonical_regime_epochs=counters[trader][1],
            account_risk_snapshot_bound_epochs=counters[trader][2],
            provider_condition_bound_epochs=counters[trader][3],
        )
        for trader in PHASE19_REQUIRED_TRADERS
    )
    represented = tuple(
        item.trader_id for item in coverage if item.decision_epochs > 0
    )
    canonical = tuple(
        item.trader_id for item in coverage if item.structurally_complete
    )
    noncanonical = tuple(
        item.trader_id
        for item in coverage
        if item.decision_epochs > 0 and not item.structurally_complete
    )
    missing = tuple(
        item.trader_id for item in coverage if item.decision_epochs == 0
    )
    complete = len(canonical) == len(PHASE19_REQUIRED_TRADERS)

    blockers: list[str] = []
    if usable_epochs == 0:
        blockers.append("NO_FRESH_FORWARD_T12_REGIME_EPOCHS")
    if missing:
        blockers.append("FORWARD_T12_REQUIRED_LINEAGES_NOT_ALL_REPRESENTED")
    if noncanonical:
        blockers.append("FORWARD_T12_CANONICAL_REGIME_COVERAGE_INCOMPLETE")
    if any(
        item.account_risk_snapshot_bound_epochs != item.decision_epochs
        for item in coverage
        if item.decision_epochs > 0
    ):
        blockers.append(
            "FORWARD_T12_ACCOUNT_RISK_SNAPSHOT_BINDING_INCOMPLETE"
        )
    if any(
        item.provider_condition_bound_epochs != item.decision_epochs
        for item in coverage
        if item.decision_epochs > 0
    ):
        blockers.append(
            "FORWARD_T12_PROVIDER_CONDITION_STATE_BINDING_INCOMPLETE"
        )
    blockers.append("FRESH_OOS_T12_REGIME_GENERALIZATION_REQUIRED")

    return Phase20T12RegimePopulationAudit(
        usable_forward_epochs=usable_epochs,
        canonical_regime_epochs=canonical_epochs,
        account_risk_snapshot_bound_epochs=snapshot_epochs,
        provider_condition_bound_epochs=provider_epochs,
        represented_lineages=represented,
        canonical_lineages=canonical,
        noncanonical_lineages=noncanonical,
        missing_lineages=missing,
        lineage_coverage=coverage,
        forward_schema_7_of_7=complete,
        burned_phase19_reinterpreted=False,
        fresh_oos_generalization_demonstrated=False,
        blockers=tuple(blockers),
    )


def _usable(decision: Phase20ForwardDecisionSeal) -> bool:
    if decision.sealed_at is None:
        return False
    if (
        decision.seal_deadline_at is not None
        and not decision.sealed_within_deadline
    ):
        return False
    return _payload(decision).get("evidence_kind") == "FORWARD_OBSERVED"


def _payload(decision: Phase20ForwardDecisionSeal) -> dict[str, object]:
    try:
        payload = json.loads(decision.canonical_payload_json)
    except json.JSONDecodeError as error:
        raise CiboCapitalManagementError(
            "Phase20 T12 decision payload invalid JSON"
        ) from error
    if not isinstance(payload, dict):
        raise CiboCapitalManagementError(
            "Phase20 T12 decision payload must be object"
        )
    return payload


def _lineages(slots: list[object]) -> tuple[TraderLineage, ...]:
    result: list[TraderLineage] = []
    for row in slots:
        if not isinstance(row, dict):
            raise CiboCapitalManagementError(
                "Phase20 T12 population slot must be object"
            )
        try:
            trader = TraderLineage(str(row["trader_id"]))
        except (KeyError, ValueError) as error:
            raise CiboCapitalManagementError(
                "Phase20 T12 population slot Trader is invalid"
            ) from error
        if trader not in PHASE19_REQUIRED_TRADERS:
            raise CiboCapitalManagementError(
                "Phase20 T12 population contains non-CIBO lineage"
            )
        result.append(trader)
    if len(result) != len(set(result)):
        raise CiboCapitalManagementError(
            "Phase20 T12 population repeats Trader lineage in one epoch"
        )
    return tuple(result)


def _canonical_regime(payload: dict[str, object]) -> bool:
    regime = payload.get("regime_state")
    if not isinstance(regime, dict):
        return False
    if any(
        field not in regime or regime[field] is None
        for field in FORWARD_CANONICAL_REGIME_FIELDS
    ):
        return False
    if regime["liquidity"] not in {item.value for item in LiquidityState}:
        return False
    if regime["volatility"] not in {
        item.value for item in VolatilityState
    }:
        return False
    if regime["correlation"] not in {
        item.value for item in CorrelationState
    }:
        return False
    if regime["provider_condition"] not in {
        item.value for item in ProviderCondition
    }:
        return False
    for name in (
        "risk_utilization",
        "margin_utilization",
        "drawdown_utilization",
    ):
        value = _decimal(regime[name])
        if value is None or value < 0 or value > 1:
            return False
    opportunity_count = regime["opportunity_count"]
    if (
        not isinstance(opportunity_count, int)
        or isinstance(opportunity_count, bool)
        or opportunity_count < 0
    ):
        return False
    candidates = payload.get("candidates")
    if not isinstance(candidates, list) or opportunity_count != len(candidates):
        return False
    return all(
        type(regime[name]) is bool
        for name in ("position_path_adverse", "evidence_stale")
    )


def _provider_condition_bound(payload: dict[str, object]) -> bool:
    regime = payload.get("regime_state")
    return (
        isinstance(regime, dict)
        and regime.get("provider_condition")
        in {item.value for item in ProviderCondition}
    )


def _snapshots_bound(
    payload: dict[str, object],
    decision: Phase20ForwardDecisionSeal,
) -> bool:
    for prefix in ("capital", "risk"):
        identity = payload.get(f"{prefix}_snapshot_id")
        observed_raw = payload.get(f"{prefix}_snapshot_observed_at")
        if not isinstance(identity, str) or not identity:
            return False
        if not isinstance(observed_raw, str):
            return False
        try:
            observed = datetime.fromisoformat(observed_raw)
        except ValueError:
            return False
        if observed.tzinfo is None or observed.utcoffset() is None:
            return False
        if observed > decision.decision_at:
            return False
        age = Decimal(
            str((decision.decision_at - observed).total_seconds())
        )
        if age > FROZEN_PHASE20_POLICY_CANDIDATE.snapshot_max_age_seconds:
            return False
    return True


def _decimal(value: object) -> Decimal | None:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    if not result.is_finite():
        return None
    return result
