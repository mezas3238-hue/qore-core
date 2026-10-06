"""Deterministic factor/correlation lineage for CE2I T08.

This A1 contract joins the already-causal T08 correlation audit to candidate
structural-stop factor mappings and derives factor-overlap/concentration facts.
It never grants runtime netting credit and does not turn descriptive
correlation into an economic-utility claim.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from decimal import Decimal

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase20_t08_correlation import (
    T08CorrelationAudit,
)
from qore.infrastructure.cibo_ce2i_phase20_t08_risk_mapping import (
    T08FactorRiskMappingAudit,
)

GATE_ID = "CIBO_T08_FACTOR_CORRELATION_LINEAGE_V1"
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class T08FactorOverlap:
    factor_id: str
    mapping_count: int
    gross_factor_risk_usd: Decimal
    net_signed_factor_risk_usd: Decimal
    cancellation_usd: Decimal
    gross_share: Decimal

    def __post_init__(self) -> None:
        if not self.factor_id:
            raise CiboCapitalManagementError("T08 lineage factor id required")
        if (
            not isinstance(self.mapping_count, int)
            or isinstance(self.mapping_count, bool)
            or self.mapping_count <= 0
        ):
            raise CiboCapitalManagementError(
                "T08 lineage mapping_count must be positive int"
            )
        for name in (
            "gross_factor_risk_usd",
            "net_signed_factor_risk_usd",
            "cancellation_usd",
            "gross_share",
        ):
            value = getattr(self, name)
            if not isinstance(value, Decimal) or not value.is_finite():
                raise CiboCapitalManagementError(
                    f"T08 lineage {name} must be finite Decimal"
                )
        expected = self.gross_factor_risk_usd - abs(
            self.net_signed_factor_risk_usd
        )
        if (
            self.gross_factor_risk_usd <= 0
            or self.cancellation_usd != expected
            or self.cancellation_usd < 0
        ):
            raise CiboCapitalManagementError(
                "T08 lineage factor-risk accounting drift"
            )
        if self.gross_share <= 0 or self.gross_share > 1:
            raise CiboCapitalManagementError(
                "T08 lineage gross_share must be in (0,1]"
            )


@dataclass(frozen=True, slots=True)
class T08FactorCorrelationLineageReport:
    gate_id: str
    decision_at_iso: str
    correlation_sample_size: int
    required_folds: int
    mapping_count: int
    total_structural_stop_risk_usd: Decimal
    total_gross_factor_risk_usd: Decimal
    total_factor_cancellation_usd: Decimal
    dominant_factor_gross_share: Decimal
    factors: tuple[T08FactorOverlap, ...]
    correlation_lineage_bound: bool
    mapping_lineage_bound: bool
    structural_risk_conserved: bool
    factor_overlap_measured: bool
    blockers: tuple[str, ...]
    deterministic_replay: bool = True
    hindsight_factor_selection_used: bool = False
    netting_credit_authorized: bool = False
    productive_authority: bool = False
    live_authorized: bool = False
    real_capital_authorized: bool = False
    scientific_disposition_allowed_by_lineage_alone: bool = False

    def __post_init__(self) -> None:
        if self.gate_id != GATE_ID:
            raise CiboCapitalManagementError("T08 lineage gate identity drift")
        if (
            self.correlation_sample_size < 0
            or self.required_folds != 4
            or self.mapping_count < 0
        ):
            raise CiboCapitalManagementError(
                "T08 lineage canonical surface drift"
            )
        for name in (
            "total_structural_stop_risk_usd",
            "total_gross_factor_risk_usd",
            "total_factor_cancellation_usd",
            "dominant_factor_gross_share",
        ):
            value = getattr(self, name)
            if not isinstance(value, Decimal) or not value.is_finite():
                raise CiboCapitalManagementError(
                    f"T08 lineage {name} must be finite Decimal"
                )
        if (
            self.total_structural_stop_risk_usd < 0
            or self.total_gross_factor_risk_usd < 0
            or self.total_factor_cancellation_usd < 0
            or self.dominant_factor_gross_share < 0
            or self.dominant_factor_gross_share > 1
        ):
            raise CiboCapitalManagementError(
                "T08 lineage aggregate metric bounds drift"
            )
        complete = (
            self.correlation_lineage_bound
            and self.mapping_lineage_bound
            and self.structural_risk_conserved
            and self.factor_overlap_measured
        )
        if complete != (not self.blockers):
            raise CiboCapitalManagementError(
                "T08 lineage blocker/completion drift"
            )
        if (
            not self.deterministic_replay
            or self.hindsight_factor_selection_used
            or self.netting_credit_authorized
            or self.productive_authority
            or self.live_authorized
            or self.real_capital_authorized
            or self.scientific_disposition_allowed_by_lineage_alone
        ):
            raise CiboCapitalManagementError(
                "T08 lineage governance drift"
            )

    @property
    def lineage_complete(self) -> bool:
        return not self.blockers

    @property
    def scientific_blockers(self) -> tuple[str, ...]:
        return self.blockers + (
            "T08_FRESH_OOS_NETTING_UTILITY_REQUIRED",
            "T08_STRESS_AND_WF1_WF4_REPLICATION_REQUIRED",
        )

    def fingerprint(self) -> str:
        payload = asdict(self)
        for name in (
            "total_structural_stop_risk_usd",
            "total_gross_factor_risk_usd",
            "total_factor_cancellation_usd",
            "dominant_factor_gross_share",
        ):
            payload[name] = format(getattr(self, name), "f")
        for target, source in zip(
            payload["factors"],
            self.factors,
            strict=True,
        ):
            for name in (
                "gross_factor_risk_usd",
                "net_signed_factor_risk_usd",
                "cancellation_usd",
                "gross_share",
            ):
                target[name] = format(getattr(source, name), "f")
        raw = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return "sha256:" + hashlib.sha256(raw).hexdigest()


def assess_t08_factor_correlation_lineage(
    *,
    correlation: T08CorrelationAudit,
    mappings: tuple[T08FactorRiskMappingAudit, ...],
) -> T08FactorCorrelationLineageReport:
    """Bind causal correlation state to conserved structural factor risk."""

    if not isinstance(correlation, T08CorrelationAudit):
        raise CiboCapitalManagementError(
            "T08 lineage requires canonical correlation audit"
        )
    if (
        not isinstance(mappings, tuple)
        or any(
            not isinstance(item, T08FactorRiskMappingAudit)
            for item in mappings
        )
    ):
        raise CiboCapitalManagementError(
            "T08 lineage requires canonical risk mappings"
        )

    blockers: list[str] = []
    correlation_bound = (
        correlation.required_folds == 4
        and len(correlation.folds) == 4
        and correlation.sample_size >= correlation.minimum_samples
        and correlation.correlation_matrix_identified
        and correlation.directional_stability_observed
        and not correlation.risk_mapping_verified
        and not correlation.netting_utility_oos
        and not correlation.netting_credit_authorized
    )
    if not correlation_bound:
        blockers.append("T08_CORRELATION_LINEAGE_INCOMPLETE")

    signals = tuple(item.signal_fingerprint for item in mappings)
    if len(signals) != len(set(signals)):
        raise CiboCapitalManagementError(
            "T08 lineage duplicate signal mapping"
        )

    mapping_bound = bool(mappings)
    mapping_ids: set[str] = set()
    for item in mappings:
        if (
            item.decision_at != correlation.decision_at
            or item.correlation_sample_size != correlation.sample_size
            or not item.candidate_mapping_identified
            or item.risk_mapping_verified
            or item.netting_credit_authorized
            or not item.allocations
            or item.mapping_candidate_id is None
        ):
            mapping_bound = False
            continue
        if _SHA256_RE.fullmatch(item.mapping_candidate_id) is None:
            raise CiboCapitalManagementError(
                "T08 lineage mapping id must be canonical SHA256"
            )
        if item.mapping_candidate_id in mapping_ids:
            raise CiboCapitalManagementError(
                "T08 lineage duplicate mapping identity"
            )
        mapping_ids.add(item.mapping_candidate_id)
    if not mapping_bound:
        blockers.append("T08_FACTOR_RISK_MAPPING_LINEAGE_INCOMPLETE")

    structural_total = sum(
        (item.structural_stop_risk_usd for item in mappings),
        Decimal(0),
    )
    gross_total = sum(
        (
            sum(
                (
                    abs(allocation.signed_risk_usd)
                    for allocation in item.allocations
                ),
                Decimal(0),
            )
            for item in mappings
        ),
        Decimal(0),
    )
    conserved = bool(mappings) and all(
        item.gross_allocated_risk_usd == item.structural_stop_risk_usd
        and sum(
            (
                abs(allocation.signed_risk_usd)
                for allocation in item.allocations
            ),
            Decimal(0),
        )
        == item.structural_stop_risk_usd
        for item in mappings
    )
    if not conserved:
        blockers.append("T08_STRUCTURAL_STOP_RISK_CONSERVATION_NOT_PROVEN")

    by_factor: dict[str, list[Decimal]] = {}
    for item in mappings:
        for allocation in item.allocations:
            by_factor.setdefault(allocation.factor_id, []).append(
                allocation.signed_risk_usd
            )

    factors: list[T08FactorOverlap] = []
    for factor_id in sorted(by_factor):
        values = by_factor[factor_id]
        gross = sum((abs(value) for value in values), Decimal(0))
        net = sum(values, Decimal(0))
        factors.append(
            T08FactorOverlap(
                factor_id=factor_id,
                mapping_count=len(values),
                gross_factor_risk_usd=gross,
                net_signed_factor_risk_usd=net,
                cancellation_usd=gross - abs(net),
                gross_share=(
                    gross / gross_total if gross_total > 0 else Decimal(0)
                ),
            )
        )

    overlap_measured = bool(factors) and gross_total > 0
    if not overlap_measured:
        blockers.append("T08_FACTOR_OVERLAP_NOT_MEASURABLE")

    cancellation = sum(
        (item.cancellation_usd for item in factors),
        Decimal(0),
    )
    dominant_share = max(
        (item.gross_share for item in factors),
        default=Decimal(0),
    )

    return T08FactorCorrelationLineageReport(
        gate_id=GATE_ID,
        decision_at_iso=correlation.decision_at.isoformat(),
        correlation_sample_size=correlation.sample_size,
        required_folds=correlation.required_folds,
        mapping_count=len(mappings),
        total_structural_stop_risk_usd=structural_total,
        total_gross_factor_risk_usd=gross_total,
        total_factor_cancellation_usd=cancellation,
        dominant_factor_gross_share=dominant_share,
        factors=tuple(factors),
        correlation_lineage_bound=correlation_bound,
        mapping_lineage_bound=mapping_bound,
        structural_risk_conserved=conserved,
        factor_overlap_measured=overlap_measured,
        blockers=tuple(dict.fromkeys(blockers)),
    )
