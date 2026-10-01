"""Phase22-native causal population lineage for CE2I T12 and T13.

T12/T13 Phase20 population audits are intentionally restricted to
FORWARD_OBSERVED evidence. The active certification candidate is a historical
replay. This A1 sidecar consumes the canonical Phase22 replay book without
rewriting its evidence kind.

T12 validates causal regime/schema coverage only. T13 reconstructs drawdown and
loss-cluster history using only outcomes observed strictly before each decision.
Neither surface identifies an economically useful treatment by itself.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase19_portfolio_replay import (
    PHASE19_REQUIRED_TRADERS,
)
from qore.infrastructure.cibo_ce2i_phase20_policy_candidate import (
    FROZEN_PHASE20_POLICY_CANDIDATE,
)
from qore.infrastructure.cibo_ce2i_phase20_qualification_plan import (
    FROZEN_PHASE20D_QUALIFICATION_PLAN,
)
from qore.infrastructure.cibo_ce2i_regime_selector import (
    CorrelationState,
    LiquidityState,
    ProviderCondition,
    VolatilityState,
)
from qore.infrastructure.cibo_phase22_historical_replay_settlement import (
    Phase22HistoricalReplayOutcomeSeal,
    VersionedPhase22HistoricalReplayEvidenceBook,
)

GATE_ID = "CIBO_T12_T13_PHASE22_CAUSAL_POPULATION_LINEAGE_V1"
_CANONICAL_REGIME_FIELDS = (
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
class Phase22T12LineageCoverage:
    trader_id: TraderLineage
    decision_epochs: int
    canonical_regime_epochs: int
    account_risk_snapshot_bound_epochs: int
    provider_condition_bound_epochs: int

    def __post_init__(self) -> None:
        if self.trader_id not in PHASE19_REQUIRED_TRADERS:
            raise CiboCapitalManagementError(
                "Phase22 T12 lineage outside seven-Trader universe"
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
                    f"Phase22 T12 {name} invalid"
                )
            if name != "decision_epochs" and value > self.decision_epochs:
                raise CiboCapitalManagementError(
                    f"Phase22 T12 {name} exceeds lineage epochs"
                )

    @property
    def structurally_complete(self) -> bool:
        return (
            self.decision_epochs > 0
            and self.canonical_regime_epochs == self.decision_epochs
            and self.account_risk_snapshot_bound_epochs == self.decision_epochs
            and self.provider_condition_bound_epochs == self.decision_epochs
        )


@dataclass(frozen=True, slots=True)
class Phase22T12RegimeLineage:
    usable_replay_epochs: int
    represented_lineages: tuple[TraderLineage, ...]
    canonical_lineages: tuple[TraderLineage, ...]
    noncanonical_lineages: tuple[TraderLineage, ...]
    missing_lineages: tuple[TraderLineage, ...]
    lineage_coverage: tuple[Phase22T12LineageCoverage, ...]
    schema_7_of_7: bool
    lineage_complete: bool
    lineage_blockers: tuple[str, ...]
    outcomes_read: bool = False
    causal_utility_identified: bool = False

    def __post_init__(self) -> None:
        required = set(PHASE19_REQUIRED_TRADERS)
        coverage = tuple(item.trader_id for item in self.lineage_coverage)
        if set(coverage) != required or len(coverage) != len(required):
            raise CiboCapitalManagementError(
                "Phase22 T12 coverage must contain exact 7/7 Traders"
            )
        if self.schema_7_of_7 != (set(self.canonical_lineages) == required):
            raise CiboCapitalManagementError(
                "Phase22 T12 7/7 schema flag drift"
            )
        if self.lineage_complete != (not self.lineage_blockers):
            raise CiboCapitalManagementError(
                "Phase22 T12 lineage completion/blocker drift"
            )
        if self.outcomes_read or self.causal_utility_identified:
            raise CiboCapitalManagementError(
                "Phase22 T12 lineage cannot consume outcomes/promote utility"
            )

    @property
    def scientific_blockers(self) -> tuple[str, ...]:
        return self.lineage_blockers + (
            "T12_CAUSAL_REGIME_UTILITY_AND_WF1_WF4_REPLICATION_REQUIRED",
        )


@dataclass(frozen=True, slots=True)
class Phase22T13ReserveLineage:
    usable_decision_epochs: int
    candidate_epochs: int
    candidate_instances: int
    settled_history_epochs: int
    loss_cluster_epochs: int
    settlement_drawdown_epochs: int
    reserve_pressure_epochs: int
    scarce_risk_headroom_epochs: int
    pressure_and_scarcity_epochs: int
    maximum_loss_cluster: int
    maximum_settlement_drawdown_usd: Decimal
    minimum_decision_epochs: int
    decision_threshold_met: bool
    source_decision_sha256s: tuple[str, ...]
    lineage_complete: bool
    lineage_blockers: tuple[str, ...]
    future_outcome_used: bool = False
    reserve_policy_identified: bool = False
    causal_utility_identified: bool = False

    def __post_init__(self) -> None:
        for name in (
            "usable_decision_epochs",
            "candidate_epochs",
            "candidate_instances",
            "settled_history_epochs",
            "loss_cluster_epochs",
            "settlement_drawdown_epochs",
            "reserve_pressure_epochs",
            "scarce_risk_headroom_epochs",
            "pressure_and_scarcity_epochs",
            "maximum_loss_cluster",
            "minimum_decision_epochs",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value < 0
            ):
                raise CiboCapitalManagementError(
                    f"Phase22 T13 {name} invalid"
                )
        if (
            not isinstance(self.maximum_settlement_drawdown_usd, Decimal)
            or not self.maximum_settlement_drawdown_usd.is_finite()
            or self.maximum_settlement_drawdown_usd < 0
        ):
            raise CiboCapitalManagementError(
                "Phase22 T13 maximum drawdown invalid"
            )
        if self.pressure_and_scarcity_epochs > self.reserve_pressure_epochs:
            raise CiboCapitalManagementError(
                "Phase22 T13 pressure/scarcity count drift"
            )
        if self.lineage_complete != (not self.lineage_blockers):
            raise CiboCapitalManagementError(
                "Phase22 T13 lineage completion/blocker drift"
            )
        if (
            self.future_outcome_used
            or self.reserve_policy_identified
            or self.causal_utility_identified
        ):
            raise CiboCapitalManagementError(
                "Phase22 T13 lineage governance contamination"
            )

    @property
    def scientific_blockers(self) -> tuple[str, ...]:
        return self.lineage_blockers + (
            "T13_RESERVE_POLICY_NOT_IDENTIFIED",
            "T13_CAUSAL_UTILITY_AND_WF1_WF4_REPLICATION_REQUIRED",
        )


@dataclass(frozen=True, slots=True)
class Phase22T12T13CausalPopulationReport:
    gate_id: str
    candidate_id: str
    source_population_sha256: str
    amendment_sha256: str
    t12: Phase22T12RegimeLineage
    t13: Phase22T13ReserveLineage
    productive_authority: bool = False
    live_authorized: bool = False
    real_capital_authorized: bool = False

    def __post_init__(self) -> None:
        if self.gate_id != GATE_ID:
            raise CiboCapitalManagementError(
                "Phase22 T12/T13 lineage gate identity drift"
            )
        if not self.candidate_id:
            raise CiboCapitalManagementError(
                "Phase22 T12/T13 candidate identity required"
            )
        for name in ("source_population_sha256", "amendment_sha256"):
            value = getattr(self, name)
            if not value.startswith("sha256:") or len(value) != 71:
                raise CiboCapitalManagementError(
                    f"Phase22 T12/T13 {name} invalid"
                )
        if (
            self.productive_authority
            or self.live_authorized
            or self.real_capital_authorized
        ):
            raise CiboCapitalManagementError(
                "Phase22 T12/T13 lineage grants no productive authority"
            )

    def fingerprint(self) -> str:
        payload = asdict(self)
        payload["t13"]["maximum_settlement_drawdown_usd"] = format(
            self.t13.maximum_settlement_drawdown_usd,
            "f",
        )
        raw = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            default=str,
        ).encode("utf-8")
        return "sha256:" + hashlib.sha256(raw).hexdigest()


def assess_phase22_t12_t13_causal_population(
    evidence_book: VersionedPhase22HistoricalReplayEvidenceBook,
) -> Phase22T12T13CausalPopulationReport:
    """Build causal T12/T13 lineage from historical replay evidence."""

    if not isinstance(
        evidence_book,
        VersionedPhase22HistoricalReplayEvidenceBook,
    ):
        raise CiboCapitalManagementError(
            "Phase22 T12/T13 requires canonical replay evidence book"
        )
    if not evidence_book.decisions:
        raise CiboCapitalManagementError(
            "Phase22 T12/T13 requires replay decisions"
        )
    candidate_ids = {item.candidate_id for item in evidence_book.decisions}
    if len(candidate_ids) != 1:
        raise CiboCapitalManagementError(
            "Phase22 T12/T13 candidate identity drift"
        )

    ordered = tuple(
        sorted(
            evidence_book.decisions,
            key=lambda item: (item.decision_at, item.evidence_sha256),
        )
    )
    payloads = tuple(_payload(item.canonical_payload_json) for item in ordered)

    t12 = _assess_t12(ordered, payloads)
    t13 = _assess_t13(ordered, payloads, evidence_book.outcomes)
    return Phase22T12T13CausalPopulationReport(
        gate_id=GATE_ID,
        candidate_id=next(iter(candidate_ids)),
        source_population_sha256=_source_population_sha256(evidence_book),
        amendment_sha256=evidence_book.amendment_sha256,
        t12=t12,
        t13=t13,
    )


def _assess_t12(
    decisions: tuple,
    payloads: tuple[dict[str, object], ...],
) -> Phase22T12RegimeLineage:
    counters: dict[TraderLineage, list[int]] = {
        trader: [0, 0, 0, 0] for trader in PHASE19_REQUIRED_TRADERS
    }

    for decision, payload in zip(decisions, payloads, strict=True):
        slots = payload.get("population_slots")
        if not isinstance(slots, list) or not slots:
            raise CiboCapitalManagementError(
                "Phase22 T12 population_slots must be non-empty list"
            )
        lineages = _lineages(slots)
        regime_ok = _canonical_regime(payload)
        snapshots_ok = _snapshots_bound(payload, decision.decision_at)
        provider_ok = _provider_condition_bound(payload)
        for trader in lineages:
            counts = counters[trader]
            counts[0] += 1
            counts[1] += int(regime_ok)
            counts[2] += int(snapshots_ok)
            counts[3] += int(provider_ok)

    coverage = tuple(
        Phase22T12LineageCoverage(
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

    blockers: list[str] = []
    if missing:
        blockers.append("T12_PHASE22_REQUIRED_LINEAGES_NOT_ALL_REPRESENTED")
    if noncanonical:
        blockers.append("T12_PHASE22_CANONICAL_REGIME_COVERAGE_INCOMPLETE")
    return Phase22T12RegimeLineage(
        usable_replay_epochs=len(decisions),
        represented_lineages=represented,
        canonical_lineages=canonical,
        noncanonical_lineages=noncanonical,
        missing_lineages=missing,
        lineage_coverage=coverage,
        schema_7_of_7=len(canonical) == len(PHASE19_REQUIRED_TRADERS),
        lineage_complete=not blockers,
        lineage_blockers=tuple(blockers),
    )


def _assess_t13(
    decisions: tuple,
    payloads: tuple[dict[str, object], ...],
    outcomes: tuple[Phase22HistoricalReplayOutcomeSeal, ...],
) -> Phase22T13ReserveLineage:
    candidate_epochs = 0
    candidate_instances = 0
    settled_history_epochs = 0
    loss_cluster_epochs = 0
    drawdown_epochs = 0
    reserve_pressure_epochs = 0
    scarce_epochs = 0
    pressure_and_scarcity = 0
    maximum_loss_cluster = 0
    maximum_drawdown = Decimal(0)

    ordered_outcomes = tuple(
        sorted(outcomes, key=lambda item: (item.observed_at, item.evidence_id))
    )
    for decision, payload in zip(decisions, payloads, strict=True):
        candidates = payload.get("candidates")
        if not isinstance(candidates, list):
            raise CiboCapitalManagementError(
                "Phase22 T13 candidates must be list"
            )
        candidate_count = len(candidates)
        candidate_instances += candidate_count
        if candidate_count:
            candidate_epochs += 1

        prior = tuple(
            item for item in ordered_outcomes
            if item.observed_at < decision.decision_at
        )
        if prior:
            settled_history_epochs += 1
        loss_cluster = _trailing_loss_cluster(prior)
        current_drawdown, historical_max = _settlement_drawdowns(prior)
        if loss_cluster:
            loss_cluster_epochs += 1
        if current_drawdown > 0:
            drawdown_epochs += 1
        maximum_loss_cluster = max(maximum_loss_cluster, loss_cluster)
        maximum_drawdown = max(maximum_drawdown, historical_max)

        pressure = candidate_count > 0 and (
            loss_cluster > 0 or current_drawdown > 0
        )
        if pressure:
            reserve_pressure_epochs += 1

        hard_headroom = _decimal(payload.get("hard_risk_headroom_usd"))
        candidate_risk = sum(
            (_candidate_stop_risk(row) for row in candidates),
            Decimal(0),
        )
        scarce = candidate_count > 0 and candidate_risk > hard_headroom
        if scarce:
            scarce_epochs += 1
        if pressure and scarce:
            pressure_and_scarcity += 1

    minimum = FROZEN_PHASE20D_QUALIFICATION_PLAN.minimum_decision_epochs
    threshold_met = len(decisions) >= minimum
    blockers: list[str] = []
    if not threshold_met:
        blockers.append(
            f"T13_PHASE22_MINIMUM_DECISION_EPOCHS_NOT_MET:"
            f"{len(decisions)}/{minimum}"
        )
    if settled_history_epochs == 0:
        blockers.append("T13_PHASE22_NO_SETTLED_CAUSAL_HISTORY")
    if reserve_pressure_epochs == 0:
        blockers.append("T13_PHASE22_NO_RESERVE_PRESSURE_EPOCHS")
    if pressure_and_scarcity == 0:
        blockers.append("T13_PHASE22_NO_PRESSURE_SCARCITY_INTERSECTION")

    return Phase22T13ReserveLineage(
        usable_decision_epochs=len(decisions),
        candidate_epochs=candidate_epochs,
        candidate_instances=candidate_instances,
        settled_history_epochs=settled_history_epochs,
        loss_cluster_epochs=loss_cluster_epochs,
        settlement_drawdown_epochs=drawdown_epochs,
        reserve_pressure_epochs=reserve_pressure_epochs,
        scarce_risk_headroom_epochs=scarce_epochs,
        pressure_and_scarcity_epochs=pressure_and_scarcity,
        maximum_loss_cluster=maximum_loss_cluster,
        maximum_settlement_drawdown_usd=maximum_drawdown,
        minimum_decision_epochs=minimum,
        decision_threshold_met=threshold_met,
        source_decision_sha256s=tuple(
            item.evidence_sha256 for item in decisions
        ),
        lineage_complete=not blockers,
        lineage_blockers=tuple(blockers),
    )


def _payload(raw: str) -> dict[str, object]:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as error:
        raise CiboCapitalManagementError(
            "Phase22 T12/T13 decision payload invalid JSON"
        ) from error
    if not isinstance(payload, dict):
        raise CiboCapitalManagementError(
            "Phase22 T12/T13 decision payload must be object"
        )
    if payload.get("evidence_kind") != "HISTORICAL_REPLAY_OBSERVED":
        raise CiboCapitalManagementError(
            "Phase22 T12/T13 requires historical replay evidence"
        )
    return payload


def _lineages(slots: list[object]) -> tuple[TraderLineage, ...]:
    result: list[TraderLineage] = []
    for row in slots:
        if not isinstance(row, dict):
            raise CiboCapitalManagementError(
                "Phase22 T12 population slot must be object"
            )
        try:
            trader = TraderLineage(str(row["trader_id"]))
        except (KeyError, ValueError) as error:
            raise CiboCapitalManagementError(
                "Phase22 T12 population Trader invalid"
            ) from error
        if trader not in PHASE19_REQUIRED_TRADERS:
            raise CiboCapitalManagementError(
                "Phase22 T12 population contains foreign Trader"
            )
        result.append(trader)
    if len(result) != len(set(result)):
        raise CiboCapitalManagementError(
            "Phase22 T12 population repeats Trader lineage"
        )
    return tuple(result)


def _canonical_regime(payload: dict[str, object]) -> bool:
    regime = payload.get("regime_state")
    if not isinstance(regime, dict):
        return False
    if any(
        field not in regime or regime[field] is None
        for field in _CANONICAL_REGIME_FIELDS
    ):
        return False
    if regime["liquidity"] not in {item.value for item in LiquidityState}:
        return False
    if regime["volatility"] not in {item.value for item in VolatilityState}:
        return False
    if regime["correlation"] not in {item.value for item in CorrelationState}:
        return False
    if regime["provider_condition"] not in {
        item.value for item in ProviderCondition
    }:
        return False
    for name in ("risk_utilization", "margin_utilization", "drawdown_utilization"):
        value = _optional_decimal(regime[name])
        if value is None or value < 0 or value > 1:
            return False
    opportunity_count = regime["opportunity_count"]
    candidates = payload.get("candidates")
    if (
        not isinstance(opportunity_count, int)
        or isinstance(opportunity_count, bool)
        or opportunity_count < 0
        or not isinstance(candidates, list)
        or opportunity_count != len(candidates)
    ):
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


def _snapshots_bound(payload: dict[str, object], decision_at) -> bool:
    for prefix in ("capital", "risk"):
        identity = payload.get(f"{prefix}_snapshot_id")
        observed_raw = payload.get(f"{prefix}_snapshot_observed_at")
        if not isinstance(identity, str) or not identity:
            return False
        if not isinstance(observed_raw, str):
            return False
        try:
            from datetime import datetime

            observed = datetime.fromisoformat(observed_raw)
        except ValueError:
            return False
        if observed.tzinfo is None or observed.utcoffset() is None:
            return False
        if observed > decision_at:
            return False
        age = Decimal(str((decision_at - observed).total_seconds()))
        if age > FROZEN_PHASE20_POLICY_CANDIDATE.snapshot_max_age_seconds:
            return False
    return True


def _trailing_loss_cluster(
    outcomes: tuple[Phase22HistoricalReplayOutcomeSeal, ...],
) -> int:
    count = 0
    for item in reversed(outcomes):
        if item.realized_net_pnl_usd < 0:
            count += 1
        else:
            break
    return count


def _settlement_drawdowns(
    outcomes: tuple[Phase22HistoricalReplayOutcomeSeal, ...],
) -> tuple[Decimal, Decimal]:
    cash = Decimal(0)
    peak = Decimal(0)
    max_drawdown = Decimal(0)
    for item in outcomes:
        cash += item.realized_net_pnl_usd
        peak = max(peak, cash)
        max_drawdown = max(max_drawdown, peak - cash)
    return peak - cash, max_drawdown


def _candidate_stop_risk(row: object) -> Decimal:
    if not isinstance(row, dict):
        raise CiboCapitalManagementError(
            "Phase22 T13 candidate row must be object"
        )
    candidate = row.get("candidate")
    if not isinstance(candidate, dict):
        raise CiboCapitalManagementError(
            "Phase22 T13 candidate payload missing"
        )
    return _decimal(candidate.get("stop_risk_usd"))


def _source_population_sha256(
    book: VersionedPhase22HistoricalReplayEvidenceBook,
) -> str:
    raw = json.dumps(
        {
            "generation": book.generation,
            "amendment_sha256": book.amendment_sha256,
            "decision_sha256s": [
                item.evidence_sha256 for item in book.decisions
            ],
            "outcome_sha256s": [item.fingerprint() for item in book.outcomes],
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _decimal(value: object) -> Decimal:
    result = _optional_decimal(value)
    if result is None or result < 0:
        raise CiboCapitalManagementError(
            "Phase22 T12/T13 monetary field must be finite non-negative"
        )
    return result


def _optional_decimal(value: object) -> Decimal | None:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    if not result.is_finite():
        return None
    return result
