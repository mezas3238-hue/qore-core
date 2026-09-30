"""Architect-B immutable forward economic evidence manifest for Architect A.

The manifest binds the already-sealed Phase20D decision/provider plane to the
independent Risk/execution, CMA settlement and T20 capacity-release planes.

It never invents provider economics, imputes missing outcomes, changes the
frozen Phase20 V3 candidate, or grants productive authority. Incomplete
lineage is represented as an explicit gap and fails closed for scientific
consumption.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase20_execution_risk_store import (
    VersionedPhase20ExecutedRiskBook,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_policy_store import (
    VersionedPhase20ForwardPolicyBook,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    Phase20ForwardDecisionSeal,
    VersionedPhase20ForwardEvidenceBook,
)
from qore.infrastructure.cibo_ce2i_phase20_policy_candidate import (
    FROZEN_PHASE20_POLICY_CANDIDATE,
)
from qore.infrastructure.cibo_ce2i_phase20_qualification import (
    Phase20QualificationStatus,
    run_phase20d_full_surface_qualification,
)
from qore.infrastructure.cibo_ce2i_phase20_qualification_plan import (
    FROZEN_PHASE20D_QUALIFICATION_PLAN,
    phase20d_qualification_plan_sha256,
)
from qore.infrastructure.cibo_cma_settlement_store import (
    VersionedCmaSettlementBook,
)
from qore.infrastructure.cibo_t20_capital_release_evidence import (
    VersionedT20CapitalReleaseBook,
)

ARCH_B_FORWARD_ECONOMIC_MANIFEST_ID = (
    "CIBO_ARCH_B_FORWARD_ECONOMIC_EVIDENCE_MANIFEST_V1"
)


@dataclass(frozen=True, slots=True)
class ArchBForwardEconomicManifestRow:
    decision_epoch_id: str
    decision_evidence_sha256: str
    decision_at: datetime
    fold_id: str
    signal_fingerprint: str
    trader_id: str
    candidate_id: str
    code_sha: str
    parameter_sha256: str
    collector_git_sha: str
    provider_key: str
    account_ref: str
    environment: str
    provider_evidence_id: str
    qore_symbol: str
    provider_symbol: str
    provider_economics_sha256: str
    provider_observed_at: str
    provider_minimum_volume: Decimal
    provider_volume_step: Decimal
    provider_margin_per_volume_usd: Decimal
    provider_commission_per_volume_usd: Decimal
    provider_slippage_reserve_per_volume_usd: Decimal
    provider_bid: Decimal
    provider_ask: Decimal
    policy_record_sha256: str
    policy_selected: bool
    baseline_policy_id: str
    baseline_selected: bool
    execution_risk_evidence_id: str
    executed_risk_sha256: str
    executed_source_volume: Decimal
    executed_initial_stop_risk_usd: Decimal
    settlement_sha256: str
    settlement_deal_ids: tuple[int, ...]
    realized_net_pnl_usd: Decimal
    outcome_observed_at: datetime
    release_evidence_sha256: str
    release_chain_sha256: str
    released_stop_risk_capacity_usd: Decimal
    released_margin_capacity_usd: Decimal
    terminal_release_at: datetime
    capital_minutes: Decimal

    def __post_init__(self) -> None:
        for name in (
            "decision_epoch_id",
            "signal_fingerprint",
            "trader_id",
            "candidate_id",
            "code_sha",
            "collector_git_sha",
            "provider_key",
            "account_ref",
            "environment",
            "provider_evidence_id",
            "qore_symbol",
            "provider_symbol",
            "provider_observed_at",
            "policy_record_sha256",
            "baseline_policy_id",
            "execution_risk_evidence_id",
        ):
            if not getattr(self, name):
                raise CiboCapitalManagementError(
                    f"Architect-B manifest {name} is required"
                )
        for name in (
            "decision_evidence_sha256",
            "parameter_sha256",
            "provider_economics_sha256",
            "executed_risk_sha256",
            "settlement_sha256",
            "release_evidence_sha256",
            "release_chain_sha256",
        ):
            _sha(getattr(self, name), name)
        if self.fold_id not in {"WF1", "WF2", "WF3", "WF4"}:
            raise CiboCapitalManagementError(
                "Architect-B manifest fold identity is invalid"
            )
        _aware(self.decision_at, "decision_at")
        _aware(self.outcome_observed_at, "outcome_observed_at")
        _aware(self.terminal_release_at, "terminal_release_at")
        if self.outcome_observed_at < self.decision_at:
            raise CiboCapitalManagementError(
                "Architect-B outcome cannot predate decision"
            )
        if self.terminal_release_at > self.outcome_observed_at:
            raise CiboCapitalManagementError(
                "Architect-B release cannot postdate terminal outcome observation"
            )
        for name in (
            "provider_minimum_volume",
            "provider_volume_step",
            "provider_margin_per_volume_usd",
            "provider_bid",
            "provider_ask",
            "executed_source_volume",
            "executed_initial_stop_risk_usd",
            "released_stop_risk_capacity_usd",
            "released_margin_capacity_usd",
            "capital_minutes",
        ):
            _positive(getattr(self, name), name)
        for name in (
            "provider_commission_per_volume_usd",
            "provider_slippage_reserve_per_volume_usd",
        ):
            _nonnegative(getattr(self, name), name)
        if self.provider_ask < self.provider_bid:
            raise CiboCapitalManagementError(
                "Architect-B provider ask cannot be below bid"
            )
        if not self.settlement_deal_ids:
            raise CiboCapitalManagementError(
                "Architect-B settlement deal lineage is required"
            )
        if self.released_stop_risk_capacity_usd != self.executed_initial_stop_risk_usd:
            raise CiboCapitalManagementError(
                "Architect-B terminal release must restore executed stop-risk capacity"
            )


@dataclass(frozen=True, slots=True)
class ArchBForwardEconomicEvidenceGap:
    decision_evidence_sha256: str
    signal_fingerprint: str
    blocking: bool
    reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        _sha(self.decision_evidence_sha256, "gap decision_evidence_sha256")
        if not self.signal_fingerprint or not self.reasons:
            raise CiboCapitalManagementError(
                "Architect-B evidence gap identity/reasons required"
            )
        if len(self.reasons) != len(set(self.reasons)):
            raise CiboCapitalManagementError(
                "Architect-B evidence gap reasons must be unique"
            )


@dataclass(frozen=True, slots=True)
class ArchBForwardEconomicManifest:
    manifest_id: str
    frozen_candidate_id: str
    frozen_code_sha: str
    frozen_parameter_sha256: str
    qualification_plan_id: str
    qualification_plan_sha256: str
    baseline_policy_id: str
    qualification_status: str
    decision_epochs: int
    candidate_rows: int
    complete_lineage_rows: int
    rows: tuple[ArchBForwardEconomicManifestRow, ...]
    gaps: tuple[ArchBForwardEconomicEvidenceGap, ...]
    ready_for_scientific_consumption: bool
    certification_ready: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if self.manifest_id != ARCH_B_FORWARD_ECONOMIC_MANIFEST_ID:
            raise CiboCapitalManagementError(
                "Architect-B manifest identity drift"
            )
        frozen = FROZEN_PHASE20_POLICY_CANDIDATE
        plan = FROZEN_PHASE20D_QUALIFICATION_PLAN
        if (
            self.frozen_candidate_id != frozen.candidate_id
            or self.frozen_code_sha != frozen.code_sha
            or self.frozen_parameter_sha256 != frozen.parameter_sha256()
        ):
            raise CiboCapitalManagementError(
                "Architect-B frozen Phase20 V3 lineage drift"
            )
        if (
            self.qualification_plan_id != plan.plan_id
            or self.qualification_plan_sha256
            != phase20d_qualification_plan_sha256()
            or self.baseline_policy_id != plan.baseline_policy_id
        ):
            raise CiboCapitalManagementError(
                "Architect-B qualification-plan lineage drift"
            )
        if self.decision_epochs < 0 or self.candidate_rows < 0:
            raise CiboCapitalManagementError(
                "Architect-B manifest counts must be non-negative"
            )
        if self.complete_lineage_rows != len(self.rows):
            raise CiboCapitalManagementError(
                "Architect-B complete-lineage count drift"
            )
        if self.complete_lineage_rows > self.candidate_rows:
            raise CiboCapitalManagementError(
                "Architect-B complete rows exceed candidate rows"
            )
        keys = tuple(
            (row.decision_evidence_sha256, row.signal_fingerprint)
            for row in self.rows
        )
        if len(keys) != len(set(keys)):
            raise CiboCapitalManagementError(
                "Architect-B manifest duplicate row identity"
            )
        gap_keys = tuple(
            (gap.decision_evidence_sha256, gap.signal_fingerprint)
            for gap in self.gaps
        )
        if len(gap_keys) != len(set(gap_keys)):
            raise CiboCapitalManagementError(
                "Architect-B manifest duplicate gap identity"
            )
        if self.ready_for_scientific_consumption and any(
            gap.blocking for gap in self.gaps
        ):
            raise CiboCapitalManagementError(
                "Architect-B scientific readiness cannot coexist with blocking gaps"
            )
        if self.ready_for_scientific_consumption and (
            self.qualification_status not in {"PASS", "FAIL"}
            or self.decision_epochs <= 0
            or self.candidate_rows <= 0
            or self.complete_lineage_rows <= 0
        ):
            raise CiboCapitalManagementError(
                "Architect-B scientific readiness requires non-empty qualified lineage"
            )
        if self.certification_ready or self.productive_authority:
            raise CiboCapitalManagementError(
                "Architect-B manifest cannot certify or grant productive authority"
            )

    def fingerprint(self) -> str:
        return _digest(_canonical(asdict(self)))


def build_arch_b_forward_economic_manifest(
    *,
    evidence_book: VersionedPhase20ForwardEvidenceBook,
    policy_book: VersionedPhase20ForwardPolicyBook,
    executed_risk_book: VersionedPhase20ExecutedRiskBook,
    settlement_book: VersionedCmaSettlementBook,
    release_book: VersionedT20CapitalReleaseBook,
) -> ArchBForwardEconomicManifest:
    """Build a fail-closed B->A evidence bridge from immutable durable books."""

    if not isinstance(evidence_book, VersionedPhase20ForwardEvidenceBook):
        raise CiboCapitalManagementError(
            "Architect-B manifest requires canonical forward evidence book"
        )
    if not isinstance(policy_book, VersionedPhase20ForwardPolicyBook):
        raise CiboCapitalManagementError(
            "Architect-B manifest requires canonical forward policy book"
        )
    if not isinstance(executed_risk_book, VersionedPhase20ExecutedRiskBook):
        raise CiboCapitalManagementError(
            "Architect-B manifest requires canonical executed-risk book"
        )
    if not isinstance(settlement_book, VersionedCmaSettlementBook):
        raise CiboCapitalManagementError(
            "Architect-B manifest requires canonical CMA settlement book"
        )
    if not isinstance(release_book, VersionedT20CapitalReleaseBook):
        raise CiboCapitalManagementError(
            "Architect-B manifest requires canonical T20 release book"
        )

    qualification = run_phase20d_full_surface_qualification(
        evidence_book=evidence_book,
        policy_book=policy_book,
    )
    frozen = FROZEN_PHASE20_POLICY_CANDIDATE
    plan = FROZEN_PHASE20D_QUALIFICATION_PLAN
    decisions = tuple(
        sorted(
            evidence_book.decisions,
            key=lambda item: (item.decision_at, item.evidence_sha256),
        )
    )
    fold_by_sha = _fold_by_decision(decisions)
    decision_by_sha = {item.evidence_sha256: item for item in decisions}
    policy_by_sha = {
        item.evidence_sha256: item for item in policy_book.decisions
    }
    outcome_by_key = {
        (item.decision_evidence_sha256, item.signal_fingerprint): item
        for item in evidence_book.outcomes
    }

    rows: list[ArchBForwardEconomicManifestRow] = []
    gaps: list[ArchBForwardEconomicEvidenceGap] = []

    for qrow in qualification.rows:
        decision = decision_by_sha[qrow.decision_evidence_sha256]
        reasons = _decision_lineage_reasons(decision)
        payload = _json_object(decision.canonical_payload_json, "decision")
        candidate_row = _candidate_row(payload, qrow.signal_fingerprint)
        provider = _mapping(candidate_row.get("provider_observation"), "provider")
        opportunity = _mapping(candidate_row.get("opportunity"), "opportunity")
        candidate = _mapping(candidate_row.get("candidate"), "candidate")
        account = _mapping(payload.get("account_identity"), "account_identity")
        provider_evidence_id = str(candidate_row.get("provider_evidence_id", ""))
        policy = policy_by_sha.get(decision.evidence_sha256)
        outcome = outcome_by_key.get(
            (decision.evidence_sha256, qrow.signal_fingerprint)
        )

        if not provider_evidence_id:
            reasons.append("PROVIDER_EVIDENCE_ID_MISSING")
        if policy is None:
            reasons.append("POLICY_SEAL_MISSING")

        if outcome is None:
            reasons.append("TERMINAL_OUTCOME_NOT_OBSERVED")
            gaps.append(
                ArchBForwardEconomicEvidenceGap(
                    decision_evidence_sha256=decision.evidence_sha256,
                    signal_fingerprint=qrow.signal_fingerprint,
                    blocking=bool(qrow.policy_selected or qrow.baseline_selected),
                    reasons=tuple(dict.fromkeys(reasons)),
                )
            )
            continue

        risk = executed_risk_book.risk_for(
            decision_evidence_sha256=decision.evidence_sha256,
            signal_fingerprint=qrow.signal_fingerprint,
            position_id=outcome.position_id,
        )
        settlement = settlement_book.state_for(
            signal_fingerprint=qrow.signal_fingerprint,
            position_id=outcome.position_id,
        )
        release = release_book.for_signal_position(
            signal_fingerprint=qrow.signal_fingerprint,
            position_id=outcome.position_id,
        )

        if risk is None:
            reasons.append("EXECUTED_RISK_EVIDENCE_MISSING")
        if settlement is None:
            reasons.append("CMA_SETTLEMENT_STATE_MISSING")
        if release is None:
            reasons.append("T20_RELEASE_EVIDENCE_MISSING")
        if reasons:
            gaps.append(
                ArchBForwardEconomicEvidenceGap(
                    decision_evidence_sha256=decision.evidence_sha256,
                    signal_fingerprint=qrow.signal_fingerprint,
                    blocking=True,
                    reasons=tuple(dict.fromkeys(reasons)),
                )
            )
            continue

        assert policy is not None
        assert risk is not None
        assert settlement is not None
        assert release is not None
        _reconcile_complete_lineage(
            decision=decision,
            outcome=outcome,
            risk=risk,
            settlement=settlement,
            release=release,
        )
        provider_sha = _digest(
            {
                "provider_evidence_id": provider_evidence_id,
                "provider_observation": provider,
                "opportunity_qore_symbol": opportunity.get("qore_symbol"),
                "opportunity_provider_symbol": opportunity.get("provider_symbol"),
            }
        )
        risk_sha = _digest(_canonical(asdict(risk)))
        settlement_sha = _settlement_sha256(settlement)

        rows.append(
            ArchBForwardEconomicManifestRow(
                decision_epoch_id=decision.decision_epoch_id,
                decision_evidence_sha256=decision.evidence_sha256,
                decision_at=decision.decision_at,
                fold_id=fold_by_sha[decision.evidence_sha256],
                signal_fingerprint=qrow.signal_fingerprint,
                trader_id=str(candidate["trader_id"]),
                candidate_id=decision.candidate_id,
                code_sha=decision.code_sha,
                parameter_sha256=decision.parameter_sha256,
                collector_git_sha=decision.collector_git_sha or "",
                provider_key=str(account.get("provider_key", "")),
                account_ref=str(account.get("account_ref", "")),
                environment=str(account.get("environment", "")),
                provider_evidence_id=provider_evidence_id,
                qore_symbol=str(opportunity.get("qore_symbol", "")),
                provider_symbol=str(opportunity.get("provider_symbol", "")),
                provider_economics_sha256=provider_sha,
                provider_observed_at=str(provider.get("observed_at", "")),
                provider_minimum_volume=_dec(provider, "minimum_volume"),
                provider_volume_step=_dec(provider, "volume_step"),
                provider_margin_per_volume_usd=_dec(provider, "margin_per_volume"),
                provider_commission_per_volume_usd=_dec(
                    provider, "commission_per_volume_usd"
                ),
                provider_slippage_reserve_per_volume_usd=_dec(
                    provider, "slippage_reserve_per_volume_usd"
                ),
                provider_bid=_dec(provider, "bid"),
                provider_ask=_dec(provider, "ask"),
                policy_record_sha256=policy.policy_record_sha256,
                policy_selected=qrow.policy_selected,
                baseline_policy_id=plan.baseline_policy_id,
                baseline_selected=qrow.baseline_selected,
                execution_risk_evidence_id=risk.evidence_id,
                executed_risk_sha256=risk_sha,
                executed_source_volume=risk.filled_source_volume,
                executed_initial_stop_risk_usd=(
                    risk.executed_initial_stop_risk_usd
                ),
                settlement_sha256=settlement_sha,
                settlement_deal_ids=outcome.settlement_deal_ids,
                realized_net_pnl_usd=outcome.realized_net_pnl_usd,
                outcome_observed_at=outcome.observed_at,
                release_evidence_sha256=release.evidence_sha256,
                release_chain_sha256=release.chain_sha256,
                released_stop_risk_capacity_usd=(
                    release.evidence.total_released_stop_risk_capacity_usd
                ),
                released_margin_capacity_usd=(
                    release.evidence.total_released_margin_capacity_usd
                ),
                terminal_release_at=release.evidence.terminal_release_at,
                capital_minutes=outcome.capital_minutes
                if outcome.capital_minutes is not None
                else Decimal(0),
            )
        )

    blocking = any(gap.blocking for gap in gaps)
    scientific = (
        qualification.status
        in {Phase20QualificationStatus.PASS, Phase20QualificationStatus.FAIL}
        and not blocking
    )
    return ArchBForwardEconomicManifest(
        manifest_id=ARCH_B_FORWARD_ECONOMIC_MANIFEST_ID,
        frozen_candidate_id=frozen.candidate_id,
        frozen_code_sha=frozen.code_sha,
        frozen_parameter_sha256=frozen.parameter_sha256(),
        qualification_plan_id=plan.plan_id,
        qualification_plan_sha256=phase20d_qualification_plan_sha256(),
        baseline_policy_id=plan.baseline_policy_id,
        qualification_status=qualification.status.value,
        decision_epochs=len(decisions),
        candidate_rows=len(qualification.rows),
        complete_lineage_rows=len(rows),
        rows=tuple(rows),
        gaps=tuple(gaps),
        ready_for_scientific_consumption=scientific,
    )


def _decision_lineage_reasons(
    decision: Phase20ForwardDecisionSeal,
) -> list[str]:
    frozen = FROZEN_PHASE20_POLICY_CANDIDATE
    reasons: list[str] = []
    if decision.candidate_id != frozen.candidate_id:
        reasons.append("FROZEN_CANDIDATE_ID_DRIFT")
    if decision.code_sha != frozen.code_sha:
        reasons.append("FROZEN_CODE_SHA_DRIFT")
    if decision.parameter_sha256 != frozen.parameter_sha256():
        reasons.append("FROZEN_PARAMETER_SHA_DRIFT")
    if decision.decision_at < FROZEN_PHASE20D_QUALIFICATION_PLAN.frozen_at:
        reasons.append("PRE_FREEZE_DECISION")
    if not decision.sealed_within_deadline:
        reasons.append("PREOUTCOME_SEAL_DEADLINE_FAILED")
    if decision.collector_git_sha is None:
        reasons.append("COLLECTOR_GIT_SHA_MISSING")
    payload = _json_object(decision.canonical_payload_json, "decision")
    if payload.get("evidence_kind") != "FORWARD_OBSERVED":
        reasons.append("EVIDENCE_KIND_NOT_FORWARD_OBSERVED")
    return reasons


def _reconcile_complete_lineage(
    *,
    decision: Phase20ForwardDecisionSeal,
    outcome: Any,
    risk: Any,
    settlement: Any,
    release: Any,
) -> None:
    if outcome.execution_risk_evidence_id != risk.evidence_id:
        raise CiboCapitalManagementError(
            "Architect-B outcome/executed-risk identity drift"
        )
    if outcome.executed_initial_stop_risk_usd != risk.executed_initial_stop_risk_usd:
        raise CiboCapitalManagementError(
            "Architect-B outcome/executed-risk amount drift"
        )
    if not settlement.position_closed:
        raise CiboCapitalManagementError(
            "Architect-B manifest requires terminal CMA settlement"
        )
    deal_ids = tuple(record.deal_id for record in settlement.records)
    if deal_ids != outcome.settlement_deal_ids:
        raise CiboCapitalManagementError(
            "Architect-B outcome/CMA settlement deal drift"
        )
    if settlement.realized_net_pnl_usd != outcome.realized_net_pnl_usd:
        raise CiboCapitalManagementError(
            "Architect-B outcome/CMA realized PnL drift"
        )
    evidence = release.evidence
    auth = evidence.authorization
    if (
        auth.decision_evidence_sha256 != decision.evidence_sha256
        or auth.signal_fingerprint != outcome.signal_fingerprint
        or auth.position_id != outcome.position_id
        or auth.execution_evidence_id != risk.evidence_id
    ):
        raise CiboCapitalManagementError(
            "Architect-B T20 authorization lineage drift"
        )
    if evidence.source_outcome_evidence_id != outcome.evidence_id:
        raise CiboCapitalManagementError(
            "Architect-B T20 outcome lineage drift"
        )
    if evidence.terminal_settlement_pnl_usd != outcome.realized_net_pnl_usd:
        raise CiboCapitalManagementError(
            "Architect-B T20 settlement PnL drift"
        )
    if (
        evidence.total_released_stop_risk_capacity_usd
        != risk.executed_initial_stop_risk_usd
    ):
        raise CiboCapitalManagementError(
            "Architect-B T20 stop-risk release drift"
        )
    if outcome.capital_released_at != evidence.terminal_release_at:
        raise CiboCapitalManagementError(
            "Architect-B Phase20/T20 release timestamp drift"
        )
    if outcome.capital_minutes != evidence.release_latency_minutes:
        raise CiboCapitalManagementError(
            "Architect-B Phase20/T20 capital-minute drift"
        )


def _fold_by_decision(
    decisions: tuple[Phase20ForwardDecisionSeal, ...],
) -> dict[str, str]:
    count = FROZEN_PHASE20D_QUALIFICATION_PLAN.fold_count
    base, remainder = divmod(len(decisions), count)
    result: dict[str, str] = {}
    cursor = 0
    for index in range(count):
        size = base + (1 if index < remainder else 0)
        for decision in decisions[cursor : cursor + size]:
            result[decision.evidence_sha256] = f"WF{index + 1}"
        cursor += size
    return result


def _candidate_row(
    payload: dict[str, object],
    signal_fingerprint: str,
) -> dict[str, object]:
    raw = payload.get("candidates")
    if not isinstance(raw, list):
        raise CiboCapitalManagementError(
            "Architect-B decision candidates must be list"
        )
    found: list[dict[str, object]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        candidate = item.get("candidate")
        if (
            isinstance(candidate, dict)
            and candidate.get("signal_fingerprint") == signal_fingerprint
        ):
            found.append(item)
    if len(found) != 1:
        raise CiboCapitalManagementError(
            "Architect-B candidate identity must resolve exactly once"
        )
    return found[0]


def _settlement_sha256(settlement: Any) -> str:
    payload = {
        "signal_fingerprint": settlement.signal_fingerprint,
        "position_id": settlement.position_id,
        "position_closed": settlement.position_closed,
        "records": [
            {
                "event": record.event,
                "deal_id": record.deal_id,
                "signal_fingerprint": record.signal_fingerprint,
                "position_id": record.position_id,
                "net_profit_usd": format(record.net_profit_usd, "f"),
                "position_open_after": record.position_open_after,
            }
            for record in settlement.records
        ],
    }
    return _digest(payload)


def _json_object(raw: str, name: str) -> dict[str, object]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as error:
        raise CiboCapitalManagementError(
            f"Architect-B {name} JSON is invalid"
        ) from error
    if not isinstance(value, dict):
        raise CiboCapitalManagementError(
            f"Architect-B {name} JSON must be object"
        )
    return value


def _mapping(value: object, name: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise CiboCapitalManagementError(
            f"Architect-B {name} must be object"
        )
    return value


def _dec(value: dict[str, object], key: str) -> Decimal:
    try:
        result = Decimal(str(value[key]))
    except (KeyError, ValueError) as error:
        raise CiboCapitalManagementError(
            f"Architect-B provider {key} is invalid"
        ) from error
    if not result.is_finite():
        raise CiboCapitalManagementError(
            f"Architect-B provider {key} must be finite"
        )
    return result


def _canonical(value: Any) -> Any:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, datetime):
        return value.isoformat()
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


def _digest(value: object) -> str:
    raw = json.dumps(
        _canonical(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _sha(value: str, name: str) -> None:
    if (
        not isinstance(value, str)
        or not value.startswith("sha256:")
        or len(value) != 71
        or any(char not in "0123456789abcdef" for char in value[7:])
    ):
        raise CiboCapitalManagementError(
            f"Architect-B {name} must be canonical SHA-256"
        )


def _aware(value: datetime, name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise CiboCapitalManagementError(
            f"Architect-B {name} must be timezone-aware"
        )


def _positive(value: Decimal, name: str) -> None:
    if not isinstance(value, Decimal) or not value.is_finite() or value <= 0:
        raise CiboCapitalManagementError(
            f"Architect-B {name} must be finite positive Decimal"
        )


def _nonnegative(value: Decimal, name: str) -> None:
    if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
        raise CiboCapitalManagementError(
            f"Architect-B {name} must be finite non-negative Decimal"
        )
