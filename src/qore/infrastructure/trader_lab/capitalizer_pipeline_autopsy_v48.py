"""V48 pre-economic pipeline autopsy over consumed V47 evidence.

Counts are frozen observations from already-consumed V47 runs. The module only measures
where population vanished. It does not alter gates, select trades, read Fresh Holdout,
or claim that removing a bottleneck would improve economics.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

IDENTITY = "QORE_CAPITALIZER_V48_PIPELINE_AUTOPSY"


@dataclass(frozen=True, slots=True)
class V48PipelineStage:
    stage_id: str
    entered: int
    passed: int
    source_run_id: int
    note: str

    def __post_init__(self) -> None:
        if not self.stage_id or self.stage_id != self.stage_id.upper():
            raise ValueError("stage_id must be non-empty uppercase")
        if self.entered < 0 or self.passed < 0 or self.passed > self.entered:
            raise ValueError("pipeline counts must satisfy 0 <= passed <= entered")
        if self.source_run_id <= 0:
            raise ValueError("pipeline stage requires authoritative run provenance")

    @property
    def incremental_survival(self) -> Decimal:
        if self.entered == 0:
            return Decimal("0")
        return Decimal(self.passed) / Decimal(self.entered)


@dataclass(frozen=True, slots=True)
class V48PipelineAutopsy:
    identity: str
    route: str
    root_population: int
    stages: tuple[V48PipelineStage, ...]
    fresh_holdout_used: bool = False
    outcome_used_to_define_stages: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY:
            raise ValueError("V48 pipeline autopsy identity is frozen")
        if self.root_population <= 0:
            raise ValueError("pipeline autopsy requires positive root population")
        if self.fresh_holdout_used or self.outcome_used_to_define_stages:
            raise ValueError("V48 pipeline autopsy must remain pre-economic/outcome-blind")
        if not self.stages:
            raise ValueError("pipeline autopsy requires stages")

    @property
    def final_population(self) -> int:
        return self.stages[-1].passed

    @property
    def cumulative_survival(self) -> Decimal:
        return Decimal(self.final_population) / Decimal(self.root_population)

    @property
    def most_destructive_stage(self) -> V48PipelineStage:
        return min(self.stages, key=lambda stage: stage.incremental_survival)


FRACTAL_S2A_AUTOPSY = V48PipelineAutopsy(
    identity=IDENTITY,
    route="FRACTAL_V47_S2A",
    root_population=2551,
    stages=(
        V48PipelineStage(
            "HTF_ALIGNED",
            2551,
            1459,
            36642644284,
            "Upstream canonical source events surviving HTF alignment.",
        ),
        V48PipelineStage(
            "M15_BOUND",
            1459,
            804,
            36642644284,
            "HTF-aligned events with downstream M15 structure bound.",
        ),
        V48PipelineStage(
            "INDEPENDENT_M1_BOUND",
            804,
            232,
            36642644284,
            "M15-bound events surviving the independent M1 execution construction.",
        ),
        V48PipelineStage(
            "EVENT_TARGET_BOUND",
            232,
            157,
            36642644284,
            "M1-bound events with event-specific structural target.",
        ),
        V48PipelineStage(
            "ROUTED_FRACTAL",
            157,
            154,
            36642644284,
            "Target-bound events resolved as FRACTAL route.",
        ),
        V48PipelineStage(
            "EXACT_PROVIDER_FILL",
            154,
            99,
            36642644284,
            "Routed candidates with exact executable provider tick fill.",
        ),
        V48PipelineStage(
            "V46_ADMITTED",
            99,
            91,
            36642644284,
            "Exact fills accepted by the V46 source adapter.",
        ),
    ),
)


FTM_S2C_AUTOPSY = V48PipelineAutopsy(
    identity=IDENTITY,
    route="FTM_V47_S2C",
    root_population=46840,
    stages=(
        V48PipelineStage(
            "HTF_CONTINUATION_ALIGNED",
            46840,
            20773,
            36653436873,
            "Raw sweeps aligned with HTF continuation direction.",
        ),
        V48PipelineStage(
            "CONTINUATION_FIRST",
            20773,
            9828,
            36653436873,
            "Continuation CISD confirms before the expected reversal.",
        ),
        V48PipelineStage(
            "ICT_CONTINUATION_MSS_FVG",
            9828,
            1750,
            36653436873,
            "Continuation-first episodes surviving the added ICT MSS/displacement/FVG layer.",
        ),
        V48PipelineStage(
            "INDEPENDENT_M1_BOUND",
            1750,
            653,
            36653436873,
            "Episodes surviving independent downstream M1 execution construction.",
        ),
        V48PipelineStage(
            "DETERMINISTIC_TARGET_BOUND",
            653,
            204,
            36653436873,
            "M1-bound episodes surviving deterministic structural target resolution.",
        ),
        V48PipelineStage(
            "EXACT_PROVIDER_FILL",
            204,
            141,
            36653436873,
            "Target-bound candidates with exact provider tick fill.",
        ),
        V48PipelineStage(
            "V46_ADMITTED",
            141,
            98,
            36653436873,
            "Exact fills accepted by the V46 source adapter.",
        ),
    ),
)


@dataclass(frozen=True, slots=True)
class V48RootCauseEvidence:
    evidence_id: str
    source_run_id: int
    current_pipeline_count: int
    alternative_construction_count: int
    interpretation: str

    def __post_init__(self) -> None:
        if self.current_pipeline_count < 0 or self.alternative_construction_count < 0:
            raise ValueError("root-cause counts cannot be negative")


S1R_INDEPENDENT_M1_EVIDENCE = V48RootCauseEvidence(
    evidence_id="S1R_INDEPENDENT_M1_RECOVERY",
    source_run_id=36614122909,
    current_pipeline_count=3,
    alternative_construction_count=15,
    interpretation=(
        "The coupled S1 path found only 3 M1 structure-bound candidates, while the "
        "independent local M1 reconstruction produced 15 complete owner M1 triads. "
        "This is evidence of composition loss, not proof of economic edge."
    ),
)


def stage_survival_table(
    autopsy: V48PipelineAutopsy,
) -> tuple[tuple[str, int, int, Decimal, Decimal], ...]:
    rows: list[tuple[str, int, int, Decimal, Decimal]] = []
    for stage in autopsy.stages:
        cumulative = Decimal(stage.passed) / Decimal(autopsy.root_population)
        rows.append(
            (
                stage.stage_id,
                stage.entered,
                stage.passed,
                stage.incremental_survival,
                cumulative,
            )
        )
    return tuple(rows)
