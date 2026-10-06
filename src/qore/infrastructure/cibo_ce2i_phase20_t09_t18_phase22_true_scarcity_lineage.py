"""Phase22-native true-scarcity lineage for CE2I T09/T18.

The original Phase20 scarcity-readiness audit intentionally consumes only
FORWARD_OBSERVED evidence. The active Phase22 certification population is a
historical replay, so A1 must not rewrite its evidence kind or fabricate broker
execution. This module reads the canonical historical replay book and proves
only decision-time scarcity population lineage and coverage.

No PnL magnitude is inspected and no economic-utility claim is produced.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase19l_competition import (
    MINIMUM_ROBUST_COMPETITION_EPOCHS,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_policy_store import (
    Phase20ForwardPolicyDecisionSeal,
    VersionedPhase20ForwardPolicyBook,
)
from qore.infrastructure.cibo_ce2i_phase20_qualification_plan import (
    FROZEN_PHASE20D_QUALIFICATION_PLAN,
)
from qore.infrastructure.cibo_phase22_historical_replay_settlement import (
    VersionedPhase22HistoricalReplayEvidenceBook,
)

GATE_ID = "CIBO_T09_T18_TRUE_SCARCITY_LINEAGE_V1"


@dataclass(frozen=True, slots=True)
class Phase22ScarcityFold:
    fold_id: str
    decision_epochs: int
    candidate_instances: int
    candidate_outcomes: int
    selected_instances: int
    selected_outcomes: int
    candidate_outcome_coverage: Decimal
    selected_outcome_coverage: Decimal

    def __post_init__(self) -> None:
        if self.fold_id not in {"WF1", "WF2", "WF3", "WF4"}:
            raise CiboCapitalManagementError(
                "Phase22 scarcity fold identity must be WF1..WF4"
            )
        for name in (
            "decision_epochs",
            "candidate_instances",
            "candidate_outcomes",
            "selected_instances",
            "selected_outcomes",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value < 0
            ):
                raise CiboCapitalManagementError(
                    f"Phase22 scarcity {name} must be non-negative int"
                )
        for name in (
            "candidate_outcome_coverage",
            "selected_outcome_coverage",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value < 0
                or value > 1
            ):
                raise CiboCapitalManagementError(
                    f"Phase22 scarcity {name} must be Decimal in [0,1]"
                )


@dataclass(frozen=True, slots=True)
class Phase22T09T18TrueScarcityLineage:
    gate_id: str
    candidate_id: str
    source_population_sha256: str
    policy_population_sha256: str
    amendment_sha256: str
    usable_replay_epochs: int
    exact_competition_epochs: int
    scarce_competition_epochs: int
    cross_trader_scarce_epochs: int
    represented_traders: tuple[str, ...]
    t09_scarce_decision_sha256s: tuple[str, ...]
    t18_cross_trader_scarce_decision_sha256s: tuple[str, ...]
    t09_folds: tuple[Phase22ScarcityFold, ...]
    t18_folds: tuple[Phase22ScarcityFold, ...]
    t09_ready_for_utility: bool
    t18_ready_for_utility: bool
    t09_blockers: tuple[str, ...]
    t18_blockers: tuple[str, ...]
    pnl_magnitudes_read: bool = False
    counterfactual_effect_identified: bool = False
    productive_authority: bool = False
    live_authorized: bool = False
    real_capital_authorized: bool = False

    def __post_init__(self) -> None:
        if self.gate_id != GATE_ID:
            raise CiboCapitalManagementError(
                "Phase22 scarcity lineage gate identity drift"
            )
        if not self.candidate_id:
            raise CiboCapitalManagementError(
                "Phase22 scarcity lineage candidate identity required"
            )
        for name in (
            "source_population_sha256",
            "policy_population_sha256",
            "amendment_sha256",
        ):
            value = getattr(self, name)
            if not value.startswith("sha256:") or len(value) != 71:
                raise CiboCapitalManagementError(
                    f"Phase22 scarcity lineage {name} invalid"
                )
        for name in (
            "usable_replay_epochs",
            "exact_competition_epochs",
            "scarce_competition_epochs",
            "cross_trader_scarce_epochs",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value < 0
            ):
                raise CiboCapitalManagementError(
                    f"Phase22 scarcity lineage {name} invalid"
                )
        if self.cross_trader_scarce_epochs > self.scarce_competition_epochs:
            raise CiboCapitalManagementError(
                "Phase22 cross-Trader scarcity exceeds scarcity"
            )
        if self.t09_ready_for_utility != (not self.t09_blockers):
            raise CiboCapitalManagementError(
                "Phase22 T09 scarcity readiness/blocker drift"
            )
        if self.t18_ready_for_utility != (not self.t18_blockers):
            raise CiboCapitalManagementError(
                "Phase22 T18 scarcity readiness/blocker drift"
            )
        prohibited = (
            self.pnl_magnitudes_read,
            self.counterfactual_effect_identified,
            self.productive_authority,
            self.live_authorized,
            self.real_capital_authorized,
        )
        if any(prohibited):
            raise CiboCapitalManagementError(
                "Phase22 scarcity lineage governance contamination"
            )

    def fingerprint(self) -> str:
        payload = asdict(self)
        for collection in ("t09_folds", "t18_folds"):
            for fold in payload[collection]:
                fold["candidate_outcome_coverage"] = format(
                    fold["candidate_outcome_coverage"], "f"
                )
                fold["selected_outcome_coverage"] = format(
                    fold["selected_outcome_coverage"], "f"
                )
        raw = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return "sha256:" + hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True, slots=True)
class _Epoch:
    decision_sha256: str
    candidate_signals: tuple[str, ...]
    candidate_traders: tuple[str, ...]
    selected_signals: tuple[str, ...]
    candidate_outcomes: int
    selected_outcomes: int


def assess_phase22_t09_t18_true_scarcity_lineage(
    *,
    evidence_book: VersionedPhase22HistoricalReplayEvidenceBook,
    policy_book: VersionedPhase20ForwardPolicyBook,
) -> Phase22T09T18TrueScarcityLineage:
    """Identify true decision-time scarcity in the Phase22 replay population."""

    if not isinstance(
        evidence_book,
        VersionedPhase22HistoricalReplayEvidenceBook,
    ):
        raise CiboCapitalManagementError(
            "Phase22 scarcity lineage requires canonical replay book"
        )
    if not isinstance(policy_book, VersionedPhase20ForwardPolicyBook):
        raise CiboCapitalManagementError(
            "Phase22 scarcity lineage requires canonical policy book"
        )
    if not evidence_book.decisions:
        raise CiboCapitalManagementError(
            "Phase22 scarcity lineage requires replay decisions"
        )

    candidates = {item.candidate_id for item in evidence_book.decisions}
    if len(candidates) != 1:
        raise CiboCapitalManagementError(
            "Phase22 scarcity lineage candidate drift"
        )
    candidate_id = next(iter(candidates))
    outcomes = {
        (item.decision_evidence_sha256, item.signal_fingerprint)
        for item in evidence_book.outcomes
    }
    policies = {
        item.evidence_sha256: item for item in policy_book.decisions
    }

    exact_count = 0
    scarce_rows: list[_Epoch] = []
    cross_rows: list[_Epoch] = []
    missing_policy = 0
    traders: set[str] = set()

    ordered = tuple(
        sorted(
            evidence_book.decisions,
            key=lambda item: (item.decision_at, item.evidence_sha256),
        )
    )
    for decision in ordered:
        payload = _payload(decision.canonical_payload_json)
        rows = _candidates(payload)
        if len(rows) < 2:
            continue
        exact_count += 1
        if not _scarce(payload, rows):
            continue

        policy = policies.get(decision.evidence_sha256)
        if policy is None:
            missing_policy += 1
            continue
        _verify_policy(policy)
        signals = tuple(str(item["signal_fingerprint"]) for item in rows)
        trader_ids = tuple(str(item["trader_id"]) for item in rows)
        if len(signals) != len(set(signals)):
            raise CiboCapitalManagementError(
                "Phase22 scarcity candidate signals must be unique"
            )
        selected = policy.selected_signal_fingerprints
        if not set(selected).issubset(set(signals)):
            raise CiboCapitalManagementError(
                "Phase22 scarcity policy selected outside candidate set"
            )
        row = _Epoch(
            decision_sha256=decision.evidence_sha256,
            candidate_signals=signals,
            candidate_traders=trader_ids,
            selected_signals=selected,
            candidate_outcomes=sum(
                1
                for signal in signals
                if (decision.evidence_sha256, signal) in outcomes
            ),
            selected_outcomes=sum(
                1
                for signal in selected
                if (decision.evidence_sha256, signal) in outcomes
            ),
        )
        scarce_rows.append(row)
        traders.update(trader_ids)
        if len(set(trader_ids)) >= 2:
            cross_rows.append(row)

    plan = FROZEN_PHASE20D_QUALIFICATION_PLAN
    t09_folds = _folds(scarce_rows, plan.fold_count)
    t18_folds = _folds(cross_rows, plan.fold_count)

    t09_blockers = _blockers(
        prefix="T09",
        rows=scarce_rows,
        folds=t09_folds,
        missing_policy=missing_policy,
        candidate_threshold=plan.minimum_candidate_outcome_coverage,
        selected_threshold=plan.required_selected_outcome_coverage,
    )
    t18_blockers = _blockers(
        prefix="T18",
        rows=cross_rows,
        folds=t18_folds,
        missing_policy=missing_policy,
        candidate_threshold=plan.minimum_candidate_outcome_coverage,
        selected_threshold=plan.required_selected_outcome_coverage,
    )

    return Phase22T09T18TrueScarcityLineage(
        gate_id=GATE_ID,
        candidate_id=candidate_id,
        source_population_sha256=_source_population_sha256(evidence_book),
        policy_population_sha256=_policy_population_sha256(policy_book),
        amendment_sha256=evidence_book.amendment_sha256,
        usable_replay_epochs=len(ordered),
        exact_competition_epochs=exact_count,
        scarce_competition_epochs=len(scarce_rows),
        cross_trader_scarce_epochs=len(cross_rows),
        represented_traders=tuple(sorted(traders)),
        t09_scarce_decision_sha256s=tuple(
            item.decision_sha256 for item in scarce_rows
        ),
        t18_cross_trader_scarce_decision_sha256s=tuple(
            item.decision_sha256 for item in cross_rows
        ),
        t09_folds=t09_folds,
        t18_folds=t18_folds,
        t09_ready_for_utility=not t09_blockers,
        t18_ready_for_utility=not t18_blockers,
        t09_blockers=t09_blockers,
        t18_blockers=t18_blockers,
    )


def _blockers(
    *,
    prefix: str,
    rows: list[_Epoch],
    folds: tuple[Phase22ScarcityFold, ...],
    missing_policy: int,
    candidate_threshold: Decimal,
    selected_threshold: Decimal,
) -> tuple[str, ...]:
    blockers: list[str] = []
    if len(rows) < MINIMUM_ROBUST_COMPETITION_EPOCHS:
        blockers.append(
            f"{prefix}_TRUE_SCARCITY_EPOCHS_{len(rows)}_OF_"
            f"{MINIMUM_ROBUST_COMPETITION_EPOCHS}"
        )
    if missing_policy:
        blockers.append(f"{prefix}_SCARCITY_POLICY_COVERAGE_INCOMPLETE")

    candidate_instances = sum(len(item.candidate_signals) for item in rows)
    candidate_outcomes = sum(item.candidate_outcomes for item in rows)
    selected_instances = sum(len(item.selected_signals) for item in rows)
    selected_outcomes = sum(item.selected_outcomes for item in rows)
    if _coverage(candidate_outcomes, candidate_instances) < candidate_threshold:
        blockers.append(f"{prefix}_CANDIDATE_OUTCOME_COVERAGE_NOT_MET")
    if selected_instances == 0:
        blockers.append(f"{prefix}_NO_SELECTED_OPPORTUNITIES")
    elif _coverage(selected_outcomes, selected_instances) < selected_threshold:
        blockers.append(f"{prefix}_SELECTED_OUTCOME_COVERAGE_NOT_MET")

    if len(folds) != 4 or any(item.decision_epochs == 0 for item in folds):
        blockers.append(f"{prefix}_WF1_WF4_COVERAGE_INCOMPLETE")
    elif any(
        item.candidate_outcome_coverage < candidate_threshold
        or item.selected_outcome_coverage < selected_threshold
        for item in folds
    ):
        blockers.append(f"{prefix}_WF1_WF4_OUTCOME_COVERAGE_NOT_MET")
    return tuple(blockers)


def _folds(
    rows: list[_Epoch],
    fold_count: int,
) -> tuple[Phase22ScarcityFold, ...]:
    if not rows:
        return ()
    base, remainder = divmod(len(rows), fold_count)
    start = 0
    result: list[Phase22ScarcityFold] = []
    for index in range(fold_count):
        count = base + (1 if index < remainder else 0)
        fold = rows[start : start + count]
        start += count
        candidate_instances = sum(len(item.candidate_signals) for item in fold)
        candidate_outcomes = sum(item.candidate_outcomes for item in fold)
        selected_instances = sum(len(item.selected_signals) for item in fold)
        selected_outcomes = sum(item.selected_outcomes for item in fold)
        result.append(
            Phase22ScarcityFold(
                fold_id=f"WF{index + 1}",
                decision_epochs=len(fold),
                candidate_instances=candidate_instances,
                candidate_outcomes=candidate_outcomes,
                selected_instances=selected_instances,
                selected_outcomes=selected_outcomes,
                candidate_outcome_coverage=_coverage(
                    candidate_outcomes,
                    candidate_instances,
                ),
                selected_outcome_coverage=_coverage(
                    selected_outcomes,
                    selected_instances,
                ),
            )
        )
    return tuple(result)


def _payload(raw: str) -> dict[str, object]:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as error:
        raise CiboCapitalManagementError(
            "Phase22 scarcity decision payload invalid JSON"
        ) from error
    if not isinstance(payload, dict):
        raise CiboCapitalManagementError(
            "Phase22 scarcity decision payload must be object"
        )
    if payload.get("evidence_kind") != "HISTORICAL_REPLAY_OBSERVED":
        raise CiboCapitalManagementError(
            "Phase22 scarcity lineage requires historical replay evidence"
        )
    return payload


def _candidates(payload: dict[str, object]) -> tuple[dict[str, object], ...]:
    raw = payload.get("candidates")
    if not isinstance(raw, list):
        raise CiboCapitalManagementError(
            "Phase22 scarcity candidates must be list"
        )
    result: list[dict[str, object]] = []
    for row in raw:
        if not isinstance(row, dict):
            raise CiboCapitalManagementError(
                "Phase22 scarcity candidate row must be object"
            )
        candidate = row.get("candidate")
        if not isinstance(candidate, dict):
            raise CiboCapitalManagementError(
                "Phase22 scarcity candidate payload must be object"
            )
        for field in (
            "signal_fingerprint",
            "trader_id",
            "concentration_group",
        ):
            if not isinstance(candidate.get(field), str):
                raise CiboCapitalManagementError(
                    f"Phase22 scarcity candidate {field} invalid"
                )
        result.append(candidate)
    return tuple(result)


def _scarce(
    payload: dict[str, object],
    candidates: tuple[dict[str, object], ...],
) -> bool:
    risk_headroom = _decimal(payload.get("hard_risk_headroom_usd"))
    margin_headroom = _decimal(payload.get("margin_headroom_usd"))
    total_risk = sum(
        (_decimal(item.get("stop_risk_usd")) for item in candidates),
        Decimal(0),
    )
    total_margin = sum(
        (_decimal(item.get("margin_usd")) for item in candidates),
        Decimal(0),
    )
    if total_risk > risk_headroom or total_margin > margin_headroom:
        return True

    raw_limits = payload.get("concentration_limit_by_group")
    if not isinstance(raw_limits, list):
        raise CiboCapitalManagementError(
            "Phase22 scarcity concentration limits must be list"
        )
    limits: dict[str, Decimal] = {}
    for item in raw_limits:
        if (
            not isinstance(item, list)
            or len(item) != 2
            or not isinstance(item[0], str)
        ):
            raise CiboCapitalManagementError(
                "Phase22 scarcity concentration limit row invalid"
            )
        limits[item[0]] = _decimal(item[1])

    used: dict[str, Decimal] = {}
    for candidate in candidates:
        group = str(candidate["concentration_group"])
        used[group] = used.get(group, Decimal(0)) + _decimal(
            candidate.get("concentration_risk_usd")
        )
    return any(
        group in limits and amount > limits[group]
        for group, amount in used.items()
    )


def _verify_policy(policy: Phase20ForwardPolicyDecisionSeal) -> None:
    expected = "sha256:" + hashlib.sha256(
        policy.canonical_record_json.encode("utf-8")
    ).hexdigest()
    if expected != policy.policy_record_sha256:
        raise CiboCapitalManagementError(
            "Phase22 scarcity policy digest drift"
        )
    try:
        record = json.loads(policy.canonical_record_json)
    except json.JSONDecodeError as error:
        raise CiboCapitalManagementError(
            "Phase22 scarcity policy record invalid JSON"
        ) from error
    if not isinstance(record, dict):
        raise CiboCapitalManagementError(
            "Phase22 scarcity policy record must be object"
        )
    if record.get("evidence_sha256") != policy.evidence_sha256:
        raise CiboCapitalManagementError(
            "Phase22 scarcity policy/evidence binding drift"
        )


def _source_population_sha256(
    book: VersionedPhase22HistoricalReplayEvidenceBook,
) -> str:
    return _digest(
        {
            "generation": book.generation,
            "amendment_sha256": book.amendment_sha256,
            "decisions": [item.evidence_sha256 for item in book.decisions],
            "outcomes": [item.fingerprint() for item in book.outcomes],
        }
    )


def _policy_population_sha256(
    book: VersionedPhase20ForwardPolicyBook,
) -> str:
    return _digest(
        {
            "generation": book.generation,
            "policies": [
                (item.evidence_sha256, item.policy_record_sha256)
                for item in book.decisions
            ],
        }
    )


def _digest(payload: object) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _coverage(numerator: int, denominator: int) -> Decimal:
    if denominator == 0:
        return Decimal(1)
    return Decimal(numerator) / Decimal(denominator)


def _decimal(value: object) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as error:
        raise CiboCapitalManagementError(
            "Phase22 scarcity monetary field invalid"
        ) from error
    if not result.is_finite() or result < 0:
        raise CiboCapitalManagementError(
            "Phase22 scarcity monetary field must be finite non-negative"
        )
    return result
