"""WP-05 V11 sequential mechanism confirmation.

V10 proved that post-source observations add material information but retained
too many false declarations because any single checkpoint LLR crossing became
an absorbing terminal state. V11 changes only the sequential decision
architecture: terminal confirmation requires two-of-three structural mechanisms
to agree.

Historical Target-V2 labels are offline-only for R8 fitting/calibration and
consumed evaluation. Runtime assessment is causal and authority-free.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import StrEnum
from math import isfinite, log
from statistics import median

from qore.infrastructure.core_stack_v2.temporal_hierarchy_sequential_changepoint_v10 import (
    V10_CHECKPOINTS_MINUTES,
    V10_FEATURE_NAMES,
    SequentialChangePointTrainingEpisode,
    SequentialCheckpointEvidence,
)

V11_DISCOVERY_FRACTION_BPS = 7_000
V11_CALIBRATION_TERMINAL_PRESERVATION_BPS = 9_800
V11_CHECKPOINTS_MINUTES = V10_CHECKPOINTS_MINUTES
V11_FEATURE_NAMES = V10_FEATURE_NAMES


class V11Mechanism(StrEnum):
    FRONTIER_PATH = "FRONTIER_PATH"
    CROSS_MARKET = "CROSS_MARKET"
    SOURCE_HIERARCHY_PRIOR = "SOURCE_HIERARCHY_PRIOR"
    COMBINED_COMPARATOR = "COMBINED_COMPARATOR"


_MECHANISM_FEATURE_NAMES: dict[V11Mechanism, tuple[str, ...]] = {
    V11Mechanism.FRONTIER_PATH: V11_FEATURE_NAMES[:10],
    V11Mechanism.CROSS_MARKET: V11_FEATURE_NAMES[10:13],
    V11Mechanism.SOURCE_HIERARCHY_PRIOR: V11_FEATURE_NAMES[13:16],
    V11Mechanism.COMBINED_COMPARATOR: V11_FEATURE_NAMES,
}
_FEATURE_INDEX = {name: index for index, name in enumerate(V11_FEATURE_NAMES)}


class V11CognitiveState(StrEnum):
    UNRESOLVED = "UNRESOLVED"
    TERMINAL_WATCH = "TERMINAL_WATCH"
    TERMINAL_CONFIRMED = "TERMINAL_CONFIRMED"
    RECOVERY_SUPPORTED = "RECOVERY_SUPPORTED"


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamps must be timezone-aware")
    return value.astimezone(UTC)


@dataclass(frozen=True, slots=True)
class MechanismDensity:
    mechanism: V11Mechanism
    checkpoint_minutes: int
    feature_names: tuple[str, ...]
    terminal_centers_micros: tuple[int, ...]
    terminal_scales_micros: tuple[int, ...]
    nonterminal_centers_micros: tuple[int, ...]
    nonterminal_scales_micros: tuple[int, ...]
    terminal_count: int
    nonterminal_count: int

    def __post_init__(self) -> None:
        if self.checkpoint_minutes not in V11_CHECKPOINTS_MINUTES:
            raise ValueError("V11 density checkpoint outside frozen schedule")
        expected = _MECHANISM_FEATURE_NAMES[self.mechanism]
        if self.feature_names != expected:
            raise ValueError("V11 mechanism feature schema drift")
        width = len(expected)
        vectors = (
            self.terminal_centers_micros,
            self.terminal_scales_micros,
            self.nonterminal_centers_micros,
            self.nonterminal_scales_micros,
        )
        if any(len(item) != width for item in vectors):
            raise ValueError("V11 mechanism density width mismatch")
        if any(value <= 0 for value in self.terminal_scales_micros):
            raise ValueError("V11 terminal density scales must be positive")
        if any(value <= 0 for value in self.nonterminal_scales_micros):
            raise ValueError("V11 nonterminal density scales must be positive")
        if self.terminal_count < 10 or self.nonterminal_count < 10:
            raise ValueError("V11 density requires both classes")


@dataclass(frozen=True, slots=True)
class V11MechanismConfirmationModel:
    fitted_at: datetime
    fit_partition: str
    checkpoints_minutes: tuple[int, ...]
    feature_names: tuple[str, ...]
    mechanism_feature_names: tuple[tuple[str, tuple[str, ...]], ...]
    densities: tuple[MechanismDensity, ...]
    confirmation_threshold_micros: int
    source_comparator_threshold_micros: int
    max_checkpoint_comparator_threshold_micros: int
    calibration_confirmation_terminal_preservation_bps: int
    calibration_confirmation_false_reduction_bps: int
    calibration_source_terminal_preservation_bps: int
    calibration_source_false_reduction_bps: int
    calibration_max_terminal_preservation_bps: int
    calibration_max_false_reduction_bps: int
    calibration_gate_pass: bool
    fit_count: int
    fit_terminal_count: int
    fit_nonterminal_count: int
    calibration_count: int
    calibration_terminal_count: int
    calibration_nonterminal_count: int
    purged_discovery_count: int
    discovery_observed_max: datetime
    calibration_source_min: datetime
    target_used_for_training_only: bool = True
    runtime_future_market_used: bool = False
    outcome_used_at_runtime: bool = False
    trader_identity_used: bool = False
    symbol_identity_used: bool = False
    setup_identity_used: bool = False
    pnl_used_at_runtime: bool = False
    methodology_authority: bool = False
    knowledge_promotion_authority: bool = False
    sizing_authority: bool = False
    risk_authority: bool = False
    order_authority: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        _utc(self.fitted_at)
        if self.fit_partition != "r8":
            raise ValueError("V11 fit partition must be r8")
        if self.checkpoints_minutes != V11_CHECKPOINTS_MINUTES:
            raise ValueError("V11 checkpoint schedule drift")
        if self.feature_names != V11_FEATURE_NAMES:
            raise ValueError("V11 feature schema drift")
        expected_groups = tuple(
            (mechanism.value, _MECHANISM_FEATURE_NAMES[mechanism])
            for mechanism in (
                V11Mechanism.FRONTIER_PATH,
                V11Mechanism.CROSS_MARKET,
                V11Mechanism.SOURCE_HIERARCHY_PRIOR,
            )
        )
        if self.mechanism_feature_names != expected_groups:
            raise ValueError("V11 frozen mechanism groups drift")
        expected_density_count = len(V11_CHECKPOINTS_MINUTES) * len(
            V11Mechanism
        )
        if len(self.densities) != expected_density_count:
            raise ValueError("V11 density set incomplete")
        if _utc(self.discovery_observed_max) >= _utc(self.calibration_source_min):
            raise ValueError("V11 chronological purge boundary is not strict")
        if self.purged_discovery_count < 0:
            raise ValueError("V11 purge count cannot be negative")
        if self.fit_terminal_count < 10 or self.fit_nonterminal_count < 10:
            raise ValueError("V11 fit requires both target classes")
        if self.calibration_terminal_count < 5:
            raise ValueError("V11 calibration requires terminal evidence")
        for name in (
            "calibration_confirmation_terminal_preservation_bps",
            "calibration_confirmation_false_reduction_bps",
            "calibration_source_terminal_preservation_bps",
            "calibration_source_false_reduction_bps",
            "calibration_max_terminal_preservation_bps",
            "calibration_max_false_reduction_bps",
        ):
            if not 0 <= int(getattr(self, name)) <= 10_000:
                raise ValueError(f"{name} must be within 0..10000")
        if self.calibration_gate_pass and (
            self.calibration_confirmation_terminal_preservation_bps
            < V11_CALIBRATION_TERMINAL_PRESERVATION_BPS
        ):
            raise ValueError("V11 calibration gate inconsistent")
        if (
            self.runtime_future_market_used
            or self.outcome_used_at_runtime
            or self.trader_identity_used
            or self.symbol_identity_used
            or self.setup_identity_used
            or self.pnl_used_at_runtime
            or self.methodology_authority
            or self.knowledge_promotion_authority
            or self.sizing_authority
            or self.risk_authority
            or self.order_authority
            or self.execution_authority
        ):
            raise ValueError("V11 model carries forbidden evidence or authority")


@dataclass(frozen=True, slots=True)
class V11CheckpointAssessment:
    checkpoint_minutes: int
    frontier_llr_micros: int
    cross_market_llr_micros: int
    hierarchy_llr_micros: int
    confirmation_score_micros: int | None
    state: V11CognitiveState
    confirmed_support: tuple[V11Mechanism, ...]
    future_market_used: bool = False
    target_used: bool = False

    def __post_init__(self) -> None:
        if self.checkpoint_minutes not in V11_CHECKPOINTS_MINUTES:
            raise ValueError("V11 assessment checkpoint outside frozen schedule")
        if self.checkpoint_minutes == 0 and self.state is V11CognitiveState.TERMINAL_CONFIRMED:
            raise ValueError("V11 t0 may not confirm terminal")
        if self.future_market_used or self.target_used:
            raise ValueError("V11 runtime assessment uses forbidden evidence")


@dataclass(frozen=True, slots=True)
class V11EpisodeAssessment:
    episode_id: str
    checkpoints: tuple[V11CheckpointAssessment, ...]
    first_confirmation_minute: int | None
    confirmation_support: tuple[V11Mechanism, ...]
    source_comparator_declared: bool
    max_checkpoint_comparator_declared: bool


@dataclass(frozen=True, slots=True)
class V11MechanismConfirmationEvaluation:
    partition: str
    sample_count: int
    baseline_terminal_count: int
    baseline_false_declaration_count: int
    source_false_declaration_count: int
    source_missed_terminal_count: int
    source_false_declaration_reduction_bps: int
    source_terminal_detection_preservation_bps: int
    max_checkpoint_false_declaration_count: int
    max_checkpoint_missed_terminal_count: int
    max_checkpoint_false_declaration_reduction_bps: int
    max_checkpoint_terminal_detection_preservation_bps: int
    v11_false_declaration_count: int
    v11_missed_terminal_count: int
    v11_false_declaration_reduction_bps: int
    v11_terminal_detection_preservation_bps: int
    confirmation_latency_p50_minutes: int
    confirmation_latency_p95_minutes: int
    confirmations_at_3m: int
    confirmations_at_5m: int
    confirmations_at_10m: int
    confirmations_at_15m: int
    terminal_watch_final_count: int
    recovery_supported_final_count: int
    unresolved_final_count: int
    confirmation_support_counts: tuple[tuple[str, int], ...]


def _select_features(
    evidence: SequentialCheckpointEvidence,
    mechanism: V11Mechanism,
) -> tuple[float, ...]:
    names = _MECHANISM_FEATURE_NAMES[mechanism]
    values = tuple(evidence.features[_FEATURE_INDEX[name]] for name in names)
    if any(not isfinite(value) for value in values):
        raise ValueError("V11 mechanism features must be finite")
    return values


def _robust_center_scale(
    rows: tuple[tuple[float, ...], ...],
) -> tuple[tuple[float, ...], tuple[float, ...]]:
    if not rows:
        raise ValueError("V11 robust density requires rows")
    width = len(rows[0])
    centers = tuple(median(row[index] for row in rows) for index in range(width))
    scales = []
    for index, center in enumerate(centers):
        mad = median(abs(row[index] - center) for row in rows)
        scales.append(max(1e-4, mad * 1.4826))
    return centers, tuple(scales)


def _micros(values: tuple[float, ...], *, positive: bool = False) -> tuple[int, ...]:
    if positive:
        return tuple(max(1, int(round(value * 1_000_000))) for value in values)
    return tuple(int(round(value * 1_000_000)) for value in values)


def _fit_density(
    *,
    mechanism: V11Mechanism,
    checkpoint_minutes: int,
    episodes: tuple[SequentialChangePointTrainingEpisode, ...],
) -> MechanismDensity:
    index = V11_CHECKPOINTS_MINUTES.index(checkpoint_minutes)
    terminal = tuple(
        _select_features(item.checkpoints[index], mechanism)
        for item in episodes
        if item.terminal_failure and item.checkpoints[index].evidence_complete
    )
    nonterminal = tuple(
        _select_features(item.checkpoints[index], mechanism)
        for item in episodes
        if not item.terminal_failure and item.checkpoints[index].evidence_complete
    )
    if len(terminal) < 10 or len(nonterminal) < 10:
        raise ValueError("V11 discovery lacks target-family evidence")
    t_center, t_scale = _robust_center_scale(terminal)
    n_center, n_scale = _robust_center_scale(nonterminal)
    return MechanismDensity(
        mechanism=mechanism,
        checkpoint_minutes=checkpoint_minutes,
        feature_names=_MECHANISM_FEATURE_NAMES[mechanism],
        terminal_centers_micros=_micros(t_center),
        terminal_scales_micros=_micros(t_scale, positive=True),
        nonterminal_centers_micros=_micros(n_center),
        nonterminal_scales_micros=_micros(n_scale, positive=True),
        terminal_count=len(terminal),
        nonterminal_count=len(nonterminal),
    )


def _density_map(
    model: V11MechanismConfirmationModel,
) -> dict[tuple[int, V11Mechanism], MechanismDensity]:
    return {
        (item.checkpoint_minutes, item.mechanism): item
        for item in model.densities
    }


def _llr_micros(
    *,
    evidence: SequentialCheckpointEvidence,
    density: MechanismDensity,
) -> int:
    values = _select_features(evidence, density.mechanism)
    total = 0.0
    for value, tc, ts, nc, ns in zip(
        values,
        density.terminal_centers_micros,
        density.terminal_scales_micros,
        density.nonterminal_centers_micros,
        density.nonterminal_scales_micros,
        strict=True,
    ):
        t_center = tc / 1_000_000.0
        t_scale = ts / 1_000_000.0
        n_center = nc / 1_000_000.0
        n_scale = ns / 1_000_000.0
        terminal_log = -log(t_scale) - 0.5 * ((value - t_center) / t_scale) ** 2
        nonterminal_log = -log(n_scale) - 0.5 * ((value - n_center) / n_scale) ** 2
        total += max(-20.0, min(20.0, terminal_log - nonterminal_log))
    return int(round(total / len(values) * 1_000_000))


def _second_largest(values: tuple[int, int, int]) -> int:
    return sorted(values)[1]


def _episode_raw_scores(
    *,
    episode: SequentialChangePointTrainingEpisode,
    densities: tuple[MechanismDensity, ...],
) -> tuple[
    tuple[int, ...],
    tuple[int, ...],
    tuple[int, ...],
    tuple[int, ...],
    tuple[int | None, ...],
]:
    lookup = {
        (item.checkpoint_minutes, item.mechanism): item
        for item in densities
    }
    frontier: list[int] = []
    cross: list[int] = []
    hierarchy: list[int] = []
    combined: list[int] = []
    confirmation: list[int | None] = []
    for index, evidence in enumerate(episode.checkpoints):
        minute = evidence.checkpoint_minutes
        f = _llr_micros(
            evidence=evidence,
            density=lookup[(minute, V11Mechanism.FRONTIER_PATH)],
        )
        c = _llr_micros(
            evidence=evidence,
            density=lookup[(minute, V11Mechanism.CROSS_MARKET)],
        )
        h = _llr_micros(
            evidence=evidence,
            density=lookup[(minute, V11Mechanism.SOURCE_HIERARCHY_PRIOR)],
        )
        full = _llr_micros(
            evidence=evidence,
            density=lookup[(minute, V11Mechanism.COMBINED_COMPARATOR)],
        )
        frontier.append(f)
        cross.append(c)
        hierarchy.append(h)
        combined.append(full)
        if index == 0:
            confirmation.append(None)
        else:
            persistent = min(frontier[index - 1], f)
            confirmation.append(
                _second_largest((persistent, c, hierarchy[0]))
            )
    return (
        tuple(frontier),
        tuple(cross),
        tuple(hierarchy),
        tuple(combined),
        tuple(confirmation),
    )


def _highest_threshold_for_preservation(
    *,
    terminal_scores: tuple[int, ...],
    minimum_preservation_bps: int,
) -> int:
    if not terminal_scores:
        raise ValueError("V11 calibration requires terminal scores")
    candidates = sorted(set(terminal_scores), reverse=True)
    count = len(terminal_scores)
    for threshold in candidates:
        preserved = sum(score >= threshold for score in terminal_scores)
        if preserved * 10_000 // count >= minimum_preservation_bps:
            return threshold
    return min(terminal_scores)


def _threshold_metrics(
    *,
    scores: tuple[tuple[int, bool], ...],
    threshold: int,
) -> tuple[int, int]:
    terminal_count = sum(label for _, label in scores)
    nonterminal_count = len(scores) - terminal_count
    terminal_detected = sum(
        label and score >= threshold for score, label in scores
    )
    nonterminal_declared = sum(
        (not label) and score >= threshold for score, label in scores
    )
    preservation = (
        0
        if terminal_count == 0
        else terminal_detected * 10_000 // terminal_count
    )
    reduction = (
        0
        if nonterminal_count == 0
        else (nonterminal_count - nonterminal_declared) * 10_000
        // nonterminal_count
    )
    return preservation, reduction


def fit_v11_mechanism_confirmation_model(
    *,
    fitted_at: datetime,
    fit_partition: str,
    episodes: tuple[SequentialChangePointTrainingEpisode, ...],
    discovery_fraction_bps: int = V11_DISCOVERY_FRACTION_BPS,
    calibration_terminal_preservation_bps: int = (
        V11_CALIBRATION_TERMINAL_PRESERVATION_BPS
    ),
) -> V11MechanismConfirmationModel:
    cutoff = _utc(fitted_at)
    if fit_partition != "r8":
        raise ValueError("V11 fit partition is frozen to r8")
    if discovery_fraction_bps != V11_DISCOVERY_FRACTION_BPS:
        raise ValueError("V11 discovery split is frozen at 7000 bps")
    if (
        calibration_terminal_preservation_bps
        != V11_CALIBRATION_TERMINAL_PRESERVATION_BPS
    ):
        raise ValueError("V11 calibration preservation is frozen at 9800 bps")
    if any(_utc(item.observed_at) > cutoff for item in episodes):
        raise ValueError("future V11 training evidence beyond fitted_at")

    ordered = tuple(sorted(episodes, key=lambda item: item.checkpoints[0].as_of))
    split = len(ordered) * discovery_fraction_bps // 10_000
    if split < 100 or len(ordered) - split < 50:
        raise ValueError("insufficient chronological V11 evidence")
    raw_discovery = ordered[:split]
    calibration = ordered[split:]
    calibration_source_min = _utc(calibration[0].checkpoints[0].as_of)
    discovery = tuple(
        item
        for item in raw_discovery
        if all(point.evidence_complete for point in item.checkpoints)
        and _utc(item.observed_at) < calibration_source_min
    )
    purged = len(raw_discovery) - len(discovery)
    if len(discovery) < 100:
        raise ValueError("V11 purge leaves insufficient discovery evidence")
    discovery_observed_max = max(_utc(item.observed_at) for item in discovery)
    if discovery_observed_max >= calibration_source_min:
        raise AssertionError("V11 chronological purge boundary is not strict")

    densities = tuple(
        _fit_density(
            mechanism=mechanism,
            checkpoint_minutes=minute,
            episodes=discovery,
        )
        for minute in V11_CHECKPOINTS_MINUTES
        for mechanism in V11Mechanism
    )

    confirmation_rows: list[tuple[int, bool]] = []
    source_rows: list[tuple[int, bool]] = []
    max_rows: list[tuple[int, bool]] = []
    confirmation_terminal_scores: list[int] = []
    source_terminal_scores: list[int] = []
    max_terminal_scores: list[int] = []

    for item in calibration:
        _, _, _, combined, confirmation = _episode_raw_scores(
            episode=item,
            densities=densities,
        )
        confirmation_score = max(
            value for value in confirmation if value is not None
        )
        source_score = combined[0]
        max_score = max(combined)
        confirmation_rows.append((confirmation_score, item.terminal_failure))
        source_rows.append((source_score, item.terminal_failure))
        max_rows.append((max_score, item.terminal_failure))
        if item.terminal_failure:
            confirmation_terminal_scores.append(confirmation_score)
            source_terminal_scores.append(source_score)
            max_terminal_scores.append(max_score)

    confirmation_threshold = _highest_threshold_for_preservation(
        terminal_scores=tuple(confirmation_terminal_scores),
        minimum_preservation_bps=calibration_terminal_preservation_bps,
    )
    source_threshold = _highest_threshold_for_preservation(
        terminal_scores=tuple(source_terminal_scores),
        minimum_preservation_bps=calibration_terminal_preservation_bps,
    )
    max_threshold = _highest_threshold_for_preservation(
        terminal_scores=tuple(max_terminal_scores),
        minimum_preservation_bps=calibration_terminal_preservation_bps,
    )

    confirmation_preservation, confirmation_reduction = _threshold_metrics(
        scores=tuple(confirmation_rows),
        threshold=confirmation_threshold,
    )
    source_preservation, source_reduction = _threshold_metrics(
        scores=tuple(source_rows),
        threshold=source_threshold,
    )
    max_preservation, max_reduction = _threshold_metrics(
        scores=tuple(max_rows),
        threshold=max_threshold,
    )

    fit_terminal = sum(item.terminal_failure for item in discovery)
    calibration_terminal = sum(item.terminal_failure for item in calibration)
    mechanism_groups = tuple(
        (mechanism.value, _MECHANISM_FEATURE_NAMES[mechanism])
        for mechanism in (
            V11Mechanism.FRONTIER_PATH,
            V11Mechanism.CROSS_MARKET,
            V11Mechanism.SOURCE_HIERARCHY_PRIOR,
        )
    )
    return V11MechanismConfirmationModel(
        fitted_at=cutoff,
        fit_partition=fit_partition,
        checkpoints_minutes=V11_CHECKPOINTS_MINUTES,
        feature_names=V11_FEATURE_NAMES,
        mechanism_feature_names=mechanism_groups,
        densities=densities,
        confirmation_threshold_micros=confirmation_threshold,
        source_comparator_threshold_micros=source_threshold,
        max_checkpoint_comparator_threshold_micros=max_threshold,
        calibration_confirmation_terminal_preservation_bps=(
            confirmation_preservation
        ),
        calibration_confirmation_false_reduction_bps=confirmation_reduction,
        calibration_source_terminal_preservation_bps=source_preservation,
        calibration_source_false_reduction_bps=source_reduction,
        calibration_max_terminal_preservation_bps=max_preservation,
        calibration_max_false_reduction_bps=max_reduction,
        calibration_gate_pass=(
            confirmation_preservation >= calibration_terminal_preservation_bps
        ),
        fit_count=len(discovery),
        fit_terminal_count=fit_terminal,
        fit_nonterminal_count=len(discovery) - fit_terminal,
        calibration_count=len(calibration),
        calibration_terminal_count=calibration_terminal,
        calibration_nonterminal_count=len(calibration) - calibration_terminal,
        purged_discovery_count=purged,
        discovery_observed_max=discovery_observed_max,
        calibration_source_min=calibration_source_min,
    )


def _support_at_confirmation(
    *,
    frontier_previous: int,
    frontier_current: int,
    cross_current: int,
    hierarchy_source: int,
    threshold: int,
) -> tuple[V11Mechanism, ...]:
    persistent = min(frontier_previous, frontier_current)
    values = (
        (V11Mechanism.FRONTIER_PATH, persistent),
        (V11Mechanism.CROSS_MARKET, cross_current),
        (V11Mechanism.SOURCE_HIERARCHY_PRIOR, hierarchy_source),
    )
    return tuple(mechanism for mechanism, value in values if value >= threshold)


def assess_v11_episode(
    *,
    model: V11MechanismConfirmationModel,
    episode: SequentialChangePointTrainingEpisode,
) -> V11EpisodeAssessment:
    frontier, cross, hierarchy, combined, confirmation = _episode_raw_scores(
        episode=episode,
        densities=model.densities,
    )
    source_declared = combined[0] >= model.source_comparator_threshold_micros
    max_declared = (
        max(combined) >= model.max_checkpoint_comparator_threshold_micros
    )

    checkpoints: list[V11CheckpointAssessment] = []
    first_confirmation: int | None = None
    confirmed_support: tuple[V11Mechanism, ...] = ()

    for index, evidence in enumerate(episode.checkpoints):
        minute = evidence.checkpoint_minutes
        score = confirmation[index]

        if first_confirmation is not None:
            state = V11CognitiveState.TERMINAL_CONFIRMED
            support = confirmed_support
        elif index > 0 and score is not None and (
            score >= model.confirmation_threshold_micros
        ):
            support = _support_at_confirmation(
                frontier_previous=frontier[index - 1],
                frontier_current=frontier[index],
                cross_current=cross[index],
                hierarchy_source=hierarchy[0],
                threshold=model.confirmation_threshold_micros,
            )
            if len(support) < 2:
                raise AssertionError("V11 confirmation lost two-of-three support")
            first_confirmation = minute
            confirmed_support = support
            state = V11CognitiveState.TERMINAL_CONFIRMED
        elif (
            evidence.breach_observed
            and evidence.safe_reclaim_streak >= 3
            and evidence.features[0] > 0.0
        ):
            support = ()
            state = V11CognitiveState.RECOVERY_SUPPORTED
        else:
            support = ()
            watch_values = (
                frontier[index],
                cross[index],
                hierarchy[0],
            )
            watch_score = _second_largest(watch_values)
            state = (
                V11CognitiveState.TERMINAL_WATCH
                if watch_score >= model.confirmation_threshold_micros
                else V11CognitiveState.UNRESOLVED
            )

        checkpoints.append(
            V11CheckpointAssessment(
                checkpoint_minutes=minute,
                frontier_llr_micros=frontier[index],
                cross_market_llr_micros=cross[index],
                hierarchy_llr_micros=hierarchy[0],
                confirmation_score_micros=score,
                state=state,
                confirmed_support=support,
            )
        )

    return V11EpisodeAssessment(
        episode_id=episode.checkpoints[0].episode_id,
        checkpoints=tuple(checkpoints),
        first_confirmation_minute=first_confirmation,
        confirmation_support=confirmed_support,
        source_comparator_declared=source_declared,
        max_checkpoint_comparator_declared=max_declared,
    )


def _latency_quantile(values: tuple[int, ...], bps: int) -> int:
    if not values:
        return -1
    ordered = sorted(values)
    index = (len(ordered) - 1) * bps // 10_000
    return ordered[index]


def _reduction_preservation(
    *,
    false_count: int,
    terminal_count: int,
    declared_false: int,
    missed_terminal: int,
) -> tuple[int, int]:
    reduction = (
        0
        if false_count == 0
        else (false_count - declared_false) * 10_000 // false_count
    )
    preservation = (
        0
        if terminal_count == 0
        else (terminal_count - missed_terminal) * 10_000 // terminal_count
    )
    return reduction, preservation


def evaluate_v11_mechanism_confirmation(
    *,
    model: V11MechanismConfirmationModel,
    partition: str,
    episodes: tuple[SequentialChangePointTrainingEpisode, ...],
) -> V11MechanismConfirmationEvaluation:
    assessed = tuple(
        (item, assess_v11_episode(model=model, episode=item))
        for item in episodes
    )
    terminal_count = sum(item.terminal_failure for item, _ in assessed)
    false_count = len(assessed) - terminal_count

    source_false = sum(
        (not item.terminal_failure) and result.source_comparator_declared
        for item, result in assessed
    )
    source_missed = sum(
        item.terminal_failure and not result.source_comparator_declared
        for item, result in assessed
    )
    max_false = sum(
        (not item.terminal_failure) and result.max_checkpoint_comparator_declared
        for item, result in assessed
    )
    max_missed = sum(
        item.terminal_failure and not result.max_checkpoint_comparator_declared
        for item, result in assessed
    )
    v11_false = sum(
        (not item.terminal_failure)
        and result.first_confirmation_minute is not None
        for item, result in assessed
    )
    v11_missed = sum(
        item.terminal_failure
        and result.first_confirmation_minute is None
        for item, result in assessed
    )
    source_reduction, source_preservation = _reduction_preservation(
        false_count=false_count,
        terminal_count=terminal_count,
        declared_false=source_false,
        missed_terminal=source_missed,
    )
    max_reduction, max_preservation = _reduction_preservation(
        false_count=false_count,
        terminal_count=terminal_count,
        declared_false=max_false,
        missed_terminal=max_missed,
    )
    v11_reduction, v11_preservation = _reduction_preservation(
        false_count=false_count,
        terminal_count=terminal_count,
        declared_false=v11_false,
        missed_terminal=v11_missed,
    )

    latencies = tuple(
        int(result.first_confirmation_minute)
        for item, result in assessed
        if item.terminal_failure and result.first_confirmation_minute is not None
    )
    confirmation_counts = {
        minute: sum(
            item.terminal_failure
            and result.first_confirmation_minute == minute
            for item, result in assessed
        )
        for minute in (3, 5, 10, 15)
    }
    final_states = tuple(result.checkpoints[-1].state for _, result in assessed)

    support_counts: dict[str, int] = {}
    for _, result in assessed:
        if result.first_confirmation_minute is None:
            continue
        key = "+".join(sorted(item.value for item in result.confirmation_support))
        support_counts[key] = support_counts.get(key, 0) + 1

    return V11MechanismConfirmationEvaluation(
        partition=partition,
        sample_count=len(assessed),
        baseline_terminal_count=terminal_count,
        baseline_false_declaration_count=false_count,
        source_false_declaration_count=source_false,
        source_missed_terminal_count=source_missed,
        source_false_declaration_reduction_bps=source_reduction,
        source_terminal_detection_preservation_bps=source_preservation,
        max_checkpoint_false_declaration_count=max_false,
        max_checkpoint_missed_terminal_count=max_missed,
        max_checkpoint_false_declaration_reduction_bps=max_reduction,
        max_checkpoint_terminal_detection_preservation_bps=max_preservation,
        v11_false_declaration_count=v11_false,
        v11_missed_terminal_count=v11_missed,
        v11_false_declaration_reduction_bps=v11_reduction,
        v11_terminal_detection_preservation_bps=v11_preservation,
        confirmation_latency_p50_minutes=_latency_quantile(latencies, 5_000),
        confirmation_latency_p95_minutes=_latency_quantile(latencies, 9_500),
        confirmations_at_3m=confirmation_counts[3],
        confirmations_at_5m=confirmation_counts[5],
        confirmations_at_10m=confirmation_counts[10],
        confirmations_at_15m=confirmation_counts[15],
        terminal_watch_final_count=sum(
            state is V11CognitiveState.TERMINAL_WATCH for state in final_states
        ),
        recovery_supported_final_count=sum(
            state is V11CognitiveState.RECOVERY_SUPPORTED
            for state in final_states
        ),
        unresolved_final_count=sum(
            state is V11CognitiveState.UNRESOLVED for state in final_states
        ),
        confirmation_support_counts=tuple(sorted(support_counts.items())),
    )


def v11_model_fingerprint(model: V11MechanismConfirmationModel) -> str:
    payload = asdict(model)
    payload["fitted_at"] = _utc(model.fitted_at).isoformat()
    payload["discovery_observed_max"] = _utc(
        model.discovery_observed_max
    ).isoformat()
    payload["calibration_source_min"] = _utc(
        model.calibration_source_min
    ).isoformat()
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def v11_representation_fingerprint() -> str:
    payload = {
        "identity": "QORE_SHARED_WP05_SEQUENTIAL_MECHANISM_CONFIRMATION_V11_001",
        "target": "HIGHER_TIMEFRAME_STRUCTURAL_FAILURE_V2",
        "checkpoints_minutes": list(V11_CHECKPOINTS_MINUTES),
        "feature_names": list(V11_FEATURE_NAMES),
        "mechanism_groups": {
            mechanism.value: list(_MECHANISM_FEATURE_NAMES[mechanism])
            for mechanism in (
                V11Mechanism.FRONTIER_PATH,
                V11Mechanism.CROSS_MARKET,
                V11Mechanism.SOURCE_HIERARCHY_PRIOR,
            )
        },
        "confirmation": "SECOND_LARGEST_OF_PERSISTENT_FRONTIER_CROSS_HIERARCHY",
        "t0_confirmation_allowed": False,
        "terminal_confirmation_absorbing": True,
        "runtime_future_market_used": False,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
