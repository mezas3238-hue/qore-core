"""Phase19M causal-regime observability audit for CE2I T12.

This module classifies only information available in immutable Phase-18 rows.
It does not inspect outcomes, fit regime boundaries, size positions, or grant
allocation/Risk/execution authority.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase19_portfolio_replay import (
    PHASE19_REQUIRED_TRADERS,
)

CANONICAL_REGIME_FIELDS = (
    "d1_body_alignment",
    "d1_range_state",
    "h1_body_alignment",
    "h1_range_state",
    "h4_body_alignment",
    "h4_range_state",
    "m5_displacement_alignment",
    "m5_efficiency_state",
    "m5_volatility_state",
)

VT31_BESPOKE_REGIME_FIELDS = (
    "h1_state",
    "h4_state",
    "premarket_state",
    "prior_day_state",
    "reference_volatility_state",
)


class Phase19RegimeEvidenceClass(StrEnum):
    CANONICAL_SHARED_SCHEMA = "CANONICAL_SHARED_SCHEMA"
    BESPOKE_UNMAPPED_SCHEMA = "BESPOKE_UNMAPPED_SCHEMA"
    MISSING_SHARED_SCHEMA = "MISSING_SHARED_SCHEMA"
    MIXED_OR_PARTIAL = "MIXED_OR_PARTIAL"


@dataclass(frozen=True, slots=True)
class Phase19RegimeLineageAudit:
    trader_id: TraderLineage
    row_count: int
    canonical_regime_rows: int
    bespoke_regime_rows: int
    missing_regime_rows: int
    evidence_class: Phase19RegimeEvidenceClass

    def __post_init__(self) -> None:
        if self.trader_id not in PHASE19_REQUIRED_TRADERS:
            raise CiboCapitalManagementError(
                "Phase19M Trader is outside supported CMA portfolio"
            )
        if type(self.row_count) is not int or self.row_count <= 0:
            raise CiboCapitalManagementError(
                "Phase19M row_count must be positive int"
            )
        for name in (
            "canonical_regime_rows",
            "bespoke_regime_rows",
            "missing_regime_rows",
        ):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise CiboCapitalManagementError(
                    f"Phase19M {name} must be non-negative int"
                )
        if (
            self.canonical_regime_rows
            + self.bespoke_regime_rows
            + self.missing_regime_rows
            != self.row_count
        ):
            raise CiboCapitalManagementError(
                "Phase19M regime row accounting drift"
            )
        if type(self.evidence_class) is not Phase19RegimeEvidenceClass:
            raise CiboCapitalManagementError(
                "Phase19M evidence_class is invalid"
            )


@dataclass(frozen=True, slots=True)
class Phase19RegimeIdentifiability:
    lineages: tuple[Phase19RegimeLineageAudit, ...]

    def __post_init__(self) -> None:
        traders = tuple(item.trader_id for item in self.lineages)
        if len(traders) != len(set(traders)):
            raise CiboCapitalManagementError(
                "Phase19M duplicate Trader audit"
            )
        if set(traders) != set(PHASE19_REQUIRED_TRADERS):
            raise CiboCapitalManagementError(
                "Phase19M requires complete seven-Trader audit"
            )

    @property
    def canonical_lineages(self) -> tuple[TraderLineage, ...]:
        return tuple(
            item.trader_id
            for item in self.lineages
            if item.evidence_class
            is Phase19RegimeEvidenceClass.CANONICAL_SHARED_SCHEMA
        )

    @property
    def bespoke_unmapped_lineages(self) -> tuple[TraderLineage, ...]:
        return tuple(
            item.trader_id
            for item in self.lineages
            if item.evidence_class
            is Phase19RegimeEvidenceClass.BESPOKE_UNMAPPED_SCHEMA
        )

    @property
    def missing_lineages(self) -> tuple[TraderLineage, ...]:
        return tuple(
            item.trader_id
            for item in self.lineages
            if item.evidence_class
            is Phase19RegimeEvidenceClass.MISSING_SHARED_SCHEMA
        )

    @property
    def portfolio_regime_state_identified(self) -> bool:
        return len(self.canonical_lineages) == len(PHASE19_REQUIRED_TRADERS)


def _has_canonical_regime(row: Mapping[str, object]) -> bool:
    regime = row.get("regime")
    return isinstance(regime, dict) and all(
        field in regime and regime[field] is not None
        for field in CANONICAL_REGIME_FIELDS
    )


def _has_vt31_bespoke_regime(row: Mapping[str, object]) -> bool:
    return all(
        field in row and row[field] is not None
        for field in VT31_BESPOKE_REGIME_FIELDS
    )


def audit_phase19_regime_rows(
    *,
    trader_id: TraderLineage,
    rows: tuple[Mapping[str, object], ...],
) -> Phase19RegimeLineageAudit:
    if not rows:
        raise CiboCapitalManagementError(
            "Phase19M lineage audit requires rows"
        )

    canonical = 0
    bespoke = 0
    missing = 0
    for row in rows:
        if _has_canonical_regime(row):
            canonical += 1
        elif (
            trader_id is TraderLineage.VT31_NAS100
            and _has_vt31_bespoke_regime(row)
        ):
            bespoke += 1
        else:
            missing += 1

    if canonical == len(rows):
        evidence_class = Phase19RegimeEvidenceClass.CANONICAL_SHARED_SCHEMA
    elif bespoke == len(rows):
        evidence_class = Phase19RegimeEvidenceClass.BESPOKE_UNMAPPED_SCHEMA
    elif missing == len(rows):
        evidence_class = Phase19RegimeEvidenceClass.MISSING_SHARED_SCHEMA
    else:
        evidence_class = Phase19RegimeEvidenceClass.MIXED_OR_PARTIAL

    return Phase19RegimeLineageAudit(
        trader_id=trader_id,
        row_count=len(rows),
        canonical_regime_rows=canonical,
        bespoke_regime_rows=bespoke,
        missing_regime_rows=missing,
        evidence_class=evidence_class,
    )


def build_phase19_regime_identifiability(
    audits: tuple[Phase19RegimeLineageAudit, ...],
) -> Phase19RegimeIdentifiability:
    return Phase19RegimeIdentifiability(lineages=audits)
