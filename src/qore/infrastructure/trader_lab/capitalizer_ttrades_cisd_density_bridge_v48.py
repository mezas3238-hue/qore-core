"""V48 density bridge from the consumed TTrades CISD M1 1Y replay.

This artifact is population evidence only. The historical replay held an older higher-level
candidate set, stop, target and lifecycle constant, so its economics and entry counts are
NOT the final V48 source-native population and cannot be inherited by the new Trader.

It establishes a narrower causal fact: once a directional raid candidate reached the
standalone TTrades M1 execution layer, local sweep -> opposing series -> CISD retained a
large fraction of candidates without requiring FVG or ICT MSS.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

IDENTITY = "QORE_CAPITALIZER_V48_TTRADES_CISD_DENSITY_BRIDGE"


@dataclass(frozen=True, slots=True)
class V48TTradesCISDConsumedEvidence:
    workflow_run_id: int = 35629551926
    workflow_head: str = "3cf763b0860b6f49839cc3eb6417703addd8f286"
    aggregate_artifact_id: int = 10654022630
    window_start: str = "2025-09-17T00:00:00+00:00"
    window_end_exclusive: str = "2026-09-17T00:00:00+00:00"
    source_candidates_in_window: int = 5572
    directional_raid_candidates: int = 853
    close_entries: int = 612
    close_max3_selected: int = 599
    retest_entries: int = 575
    retest_max3_selected: int = 569
    fvg_required: bool = False
    ict_mss_required: bool = False
    higher_level_setup_changed: bool = False
    economics_inherited_by_v48: bool = False
    final_v48_population_claimed: bool = False

    @property
    def close_survival_vs_directional_raid(self) -> Decimal:
        return Decimal(self.close_entries) / Decimal(self.directional_raid_candidates)

    @property
    def retest_survival_vs_directional_raid(self) -> Decimal:
        return Decimal(self.retest_entries) / Decimal(self.directional_raid_candidates)

    def __post_init__(self) -> None:
        if self.workflow_run_id != 35629551926:
            raise ValueError("unexpected TTrades CISD authoritative run")
        if self.aggregate_artifact_id != 10654022630:
            raise ValueError("unexpected TTrades CISD aggregate artifact")
        if self.fvg_required or self.ict_mss_required:
            raise ValueError("standalone TTrades CISD replay did not require FVG/ICT MSS")
        if self.higher_level_setup_changed:
            raise ValueError("historical CISD experiment held higher-level setup constant")
        if self.economics_inherited_by_v48 or self.final_v48_population_claimed:
            raise ValueError("consumed surrogate evidence cannot become V48 certification")


TTRADES_CISD_1Y_EVIDENCE = V48TTradesCISDConsumedEvidence()


@dataclass(frozen=True, slots=True)
class V48TTradesCISDDensityAdjudication:
    identity: str = IDENTITY
    evidence: V48TTradesCISDConsumedEvidence = TTRADES_CISD_1Y_EVIDENCE
    m1_cisd_scarcity_supported_as_primary_v47_explanation: bool = False
    cross_layer_composition_remains_primary_investigation: bool = True
    historical_economics_reusable: bool = False
    historical_target_policy_reusable: bool = False
    historical_stop_policy_reusable: bool = False
    fresh_holdout_authorized: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY:
            raise ValueError("V48 TTrades CISD density bridge identity is frozen")
        if self.m1_cisd_scarcity_supported_as_primary_v47_explanation:
            raise ValueError("consumed 1Y evidence contradicts M1-CISD scarcity explanation")
        if not self.cross_layer_composition_remains_primary_investigation:
            raise ValueError("V48 must continue investigating cross-layer composition loss")
        if (
            self.historical_economics_reusable
            or self.historical_target_policy_reusable
            or self.historical_stop_policy_reusable
            or self.fresh_holdout_authorized
        ):
            raise ValueError("density bridge grants no strategy/certification authority")


V48_TTRADES_CISD_DENSITY_ADJUDICATION = V48TTradesCISDDensityAdjudication()
