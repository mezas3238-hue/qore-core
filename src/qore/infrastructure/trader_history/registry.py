"""Append-only Trader Historical Intelligence Registry and deterministic projection.

The registry is the durable longitudinal memory of every exact Trader version. It
is an immutable aggregate: ``append_study`` returns a *new* registry and never
deletes, overwrites, or relabels evidence belonging to an older version. A
duplicate logical identity with a contradictory payload fails closed; exact
idempotent replay of the same immutable record is a no-op success.

The current capability view is a pure, deterministic projection of certified
historical evidence. It selects only evidence compatible with the exact requested
Trader version, preserves market/timeframe/regime/side/condition specificity,
retains contradictions, surfaces insufficient evidence, and never manufactures
``DEMO_ELIGIBLE``, execution authority, Risk bypass, or Production authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from qore.infrastructure.research_sample_partition import SampleRole
from qore.infrastructure.trader_history.contracts import (
    TraderHistoryBlockedError,
    TraderHistoryEpistemicStatus,
    TraderHistoryEvidenceRef,
    TraderHistoryFavorableKind,
    TraderHistoryMarketRef,
    TraderHistoryPartitionIdentity,
    TraderHistoryRegimeRef,
    TraderHistorySessionRef,
    TraderHistorySide,
    TraderHistoryStudyId,
    TraderHistoryStudyKind,
    TraderHistoryStudyRecord,
    TraderHistoryStudyVersion,
    TraderHistorySufficiency,
    TraderHistoryTimeframeRef,
    TraderHistoryValidationError,
    TraderVersionIdentity,
    _canonical_decimal,
    _utc_iso,
    _validate_timestamp,
    validate_study_record,
)
from qore.kernel.result import Failure, Result, Success

_ScopeKey = tuple[
    tuple[str, ...],
    tuple[str, ...],
    str | None,
    str | None,
    str | None,
    str | None,
]


def _none_safe(value: str | None) -> str:
    """Sortable sentinel: ``None`` sorts before every non-empty scope value."""
    return "" if value is None else value


def _record_sort_key(record: TraderHistoryStudyRecord) -> tuple[str, str, str, str]:
    return (
        record.produced_at.astimezone(UTC).isoformat(timespec="microseconds"),
        record.trader_version.fingerprint.value,
        str(record.study_id.value),
        record.study_version.value,
    )


def _scope_key(
    markets: tuple[TraderHistoryMarketRef, ...],
    timeframes: tuple[TraderHistoryTimeframeRef, ...],
    regime: TraderHistoryRegimeRef | None,
    session: TraderHistorySessionRef | None,
    side: TraderHistorySide | None,
    condition: TraderHistoryFavorableKind | None,
) -> _ScopeKey:
    return (
        tuple(item.value for item in markets),
        tuple(item.value for item in timeframes),
        None if regime is None else regime.value,
        None if session is None else session.value,
        None if side is None else side.value,
        None if condition is None else condition.value,
    )


@dataclass(frozen=True, slots=True)
class TraderHistoricalIntelligenceRegistry:
    """Immutable, canonically ordered, append-only Trader history aggregate."""

    records: tuple[TraderHistoryStudyRecord, ...] = ()

    def __post_init__(self) -> None:
        if type(self.records) is not tuple:
            raise TraderHistoryValidationError(
                "registry records must be an immutable tuple"
            )
        for record in self.records:
            validate_study_record(record)
        ordered = tuple(sorted(self.records, key=_record_sort_key))
        object.__setattr__(self, "records", ordered)
        _check_no_duplicate_study_identity(ordered)
        _check_partition_governance(ordered)
        _check_hypothesis_lineage(ordered)
        _check_supersedes(ordered)

    def append_study(
        self,
        record: TraderHistoryStudyRecord,
    ) -> Result[TraderHistoricalIntelligenceRegistry, TraderHistoryBlockedError]:
        """Append one immutable study; returns a NEW registry or a fail-closed error.

        Appending is the only transition. It never mutates ``self`` and never
        deletes or overwrites older evidence. An exact idempotent replay is a
        no-op ``Success(self)``; a contradictory duplicate, a consumed-holdout
        reuse, or an inconsistent hypothesis/supersedes lineage fails closed as
        ``Failure(TraderHistoryBlockedError)``.
        """
        if type(record) is not TraderHistoryStudyRecord:
            return Failure(
                TraderHistoryBlockedError("append requires TraderHistoryStudyRecord")
            )
        try:
            validate_study_record(record)
        except TraderHistoryValidationError as error:
            return Failure(
                TraderHistoryBlockedError(f"study record failed validation: {error}")
            )

        for existing in self.records:
            if (
                existing.study_id == record.study_id
                and existing.study_version == record.study_version
            ):
                if (
                    existing.fingerprint == record.fingerprint
                    and existing.logical_values() == record.logical_values()
                ):
                    return Success(self)
                return Failure(
                    TraderHistoryBlockedError(
                        "contradictory duplicate study identity fails closed"
                    )
                )

        try:
            return Success(
                TraderHistoricalIntelligenceRegistry(
                    records=self.records + (record,)
                )
            )
        except TraderHistoryValidationError as error:
            return Failure(
                TraderHistoryBlockedError(f"history append failed closed: {error}")
            )

    def logical_values(self) -> tuple[object, ...]:
        return tuple(record.logical_values() for record in self.records)


def _check_no_duplicate_study_identity(
    records: tuple[TraderHistoryStudyRecord, ...],
) -> None:
    seen: set[tuple[str, str]] = set()
    for record in records:
        key = (str(record.study_id.value), record.study_version.value)
        if key in seen:
            raise TraderHistoryValidationError(
                "registry must not contain duplicate study identities"
            )
        seen.add(key)


def _check_partition_governance(
    records: tuple[TraderHistoryStudyRecord, ...],
) -> None:
    """Fail closed on holdout relabeling and cross-study holdout reuse.

    A partition identity is committed to one ``(role, dataset_fingerprint)``: the
    same ``partition_id`` may never be re-declared with a different role or
    dataset. A holdout is identified by its content ``dataset_fingerprint``, and a
    dataset fingerprint is committed to exactly one sample role across the whole
    ledger, so a consumed external-validation dataset can never be re-sliced under
    a new ``partition_id`` and relabeled as development/calibration (or vice
    versa).
    """
    seen_partitions: dict[object, tuple[SampleRole, str]] = {}
    dataset_roles: dict[tuple[str, str], SampleRole] = {}
    ev_owners: dict[tuple[str, str], TraderHistoryStudyId] = {}
    for record in records:
        trader_lineage = record.trader_version.trader_code.value
        for partition in record.partitions:
            previous = seen_partitions.get(partition.partition_id)
            if previous is not None and previous != (
                partition.role,
                partition.dataset_fingerprint,
            ):
                raise TraderHistoryValidationError(
                    "partition identity cannot be relabeled with a different role "
                    "or dataset"
                )
            seen_partitions[partition.partition_id] = (
                partition.role,
                partition.dataset_fingerprint,
            )
            dataset_key = (trader_lineage, partition.dataset_fingerprint)
            committed_role = dataset_roles.get(dataset_key)
            if committed_role is not None and committed_role is not partition.role:
                raise TraderHistoryValidationError(
                    "dataset fingerprint cannot be relabeled across sample roles "
                    "within the same Trader lineage"
                )
            dataset_roles[dataset_key] = partition.role
            if partition.role is SampleRole.EXTERNAL_VALIDATION:
                owner = ev_owners.get(dataset_key)
                if owner is not None and owner != record.study_id:
                    raise TraderHistoryValidationError(
                        "external-validation holdout content cannot be consumed by "
                        "more than one study within the same Trader lineage"
                    )
                ev_owners[dataset_key] = record.study_id


def _check_hypothesis_lineage(
    records: tuple[TraderHistoryStudyRecord, ...],
) -> None:
    by_id = {record.study_id: record for record in records}
    verdicts: dict[str, TraderHistoryStudyKind] = {}
    hypothesis_tokens: set[str] = set()
    for record in records:
        if record.kind is TraderHistoryStudyKind.HYPOTHESIS:
            if record.hypothesis_id is None:
                raise TraderHistoryValidationError(
                    "hypothesis study requires a hypothesis id"
                )
            token = record.hypothesis_id.value
            if token in hypothesis_tokens:
                raise TraderHistoryValidationError(
                    "hypothesis id must be unique across the registry"
                )
            hypothesis_tokens.add(token)
    for record in records:
        if record.kind not in (
            TraderHistoryStudyKind.HYPOTHESIS_FALSIFICATION,
            TraderHistoryStudyKind.HYPOTHESIS_CONFIRMATION,
        ):
            continue
        if record.parent_study is None:
            raise TraderHistoryValidationError(
                "hypothesis confirmation/falsification requires a parent study"
            )
        parent = by_id.get(record.parent_study)
        if parent is None or parent.kind is not TraderHistoryStudyKind.HYPOTHESIS:
            raise TraderHistoryValidationError(
                "hypothesis confirmation/falsification requires an existing "
                "hypothesis parent study"
            )
        if record.hypothesis_id is None or parent.hypothesis_id is None:
            raise TraderHistoryValidationError(
                "hypothesis confirmation/falsification requires a hypothesis id"
            )
        if parent.hypothesis_id != record.hypothesis_id:
            raise TraderHistoryValidationError(
                "hypothesis id must match the parent hypothesis study"
            )
        if parent.trader_version.trader_code != record.trader_version.trader_code:
            raise TraderHistoryValidationError(
                "hypothesis confirmation/falsification must remain within the "
                "same Trader lineage"
            )
        if (
            parent.trader_version.fingerprint
            == record.trader_version.fingerprint
        ):
            raise TraderHistoryValidationError(
                "hypothesis confirmation/falsification must bind a new Trader "
                "version produced by the proposed change"
            )
        key = record.hypothesis_id.value
        if key in verdicts and verdicts[key] is not record.kind:
            raise TraderHistoryValidationError(
                "a hypothesis cannot be both confirmed and falsified"
            )
        verdicts[key] = record.kind
        if record.kind is TraderHistoryStudyKind.HYPOTHESIS_CONFIRMATION:
            if not any(
                partition.role is SampleRole.EXTERNAL_VALIDATION
                for partition in record.partitions
            ):
                raise TraderHistoryValidationError(
                    "hypothesis confirmation requires a fresh external-validation "
                    "holdout partition"
                )


def _check_supersedes(
    records: tuple[TraderHistoryStudyRecord, ...],
) -> None:
    ids = {record.study_id for record in records}
    for record in records:
        for target in record.supersedes:
            if target == record.study_id:
                raise TraderHistoryValidationError(
                    "a study cannot supersede itself"
                )
            if target not in ids:
                raise TraderHistoryValidationError(
                    "supersedes must reference an existing study"
                )


def studies_for_version(
    registry: TraderHistoricalIntelligenceRegistry,
    trader_version: TraderVersionIdentity,
) -> tuple[TraderHistoryStudyRecord, ...]:
    """Return every study bound to the exact requested Trader version."""

    if type(registry) is not TraderHistoricalIntelligenceRegistry:
        raise TraderHistoryValidationError(
            "registry must be TraderHistoricalIntelligenceRegistry"
        )
    if type(trader_version) is not TraderVersionIdentity:
        raise TraderHistoryValidationError(
            "trader_version must be TraderVersionIdentity"
        )
    TraderVersionIdentity.__post_init__(trader_version)
    matched = tuple(
        record
        for record in registry.records
        if record.trader_version.fingerprint == trader_version.fingerprint
    )
    for record in matched:
        validate_study_record(record)
    return tuple(sorted(matched, key=_record_sort_key))


def studies_by_kind(
    registry: TraderHistoricalIntelligenceRegistry,
    trader_version: TraderVersionIdentity,
    kind: TraderHistoryStudyKind,
) -> tuple[TraderHistoryStudyRecord, ...]:
    """Return studies of one kind for the exact requested Trader version."""

    if type(kind) is not TraderHistoryStudyKind:
        raise TraderHistoryValidationError("kind must be TraderHistoryStudyKind")
    return tuple(
        record
        for record in studies_for_version(registry, trader_version)
        if record.kind is kind
    )


def consumed_holdouts(
    registry: TraderHistoricalIntelligenceRegistry,
) -> tuple[TraderHistoryPartitionIdentity, ...]:
    """Return every external-validation holdout partition already consumed."""

    if type(registry) is not TraderHistoricalIntelligenceRegistry:
        raise TraderHistoryValidationError(
            "registry must be TraderHistoricalIntelligenceRegistry"
        )
    result = sorted(
        {
            partition
            for record in registry.records
            for partition in record.partitions
            if partition.role is SampleRole.EXTERNAL_VALIDATION
        },
        key=lambda item: str(item.partition_id),
    )
    return tuple(result)


@dataclass(frozen=True, slots=True)
class TraderHistoryMetricView:
    """One certified quantitative claim with its exact evidence scope and refs."""

    metric_code: str
    value: Decimal
    markets: tuple[TraderHistoryMarketRef, ...]
    timeframes: tuple[TraderHistoryTimeframeRef, ...]
    regime: TraderHistoryRegimeRef | None
    session: TraderHistorySessionRef | None
    side: TraderHistorySide | None
    condition: TraderHistoryFavorableKind | None
    evidence_refs: tuple[TraderHistoryEvidenceRef, ...]
    source_study: TraderHistoryStudyId
    source_study_version: TraderHistoryStudyVersion

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.metric_code,
            _canonical_decimal(self.value),
            tuple(item.value for item in self.markets),
            tuple(item.value for item in self.timeframes),
            None if self.regime is None else self.regime.value,
            None if self.session is None else self.session.value,
            None if self.side is None else self.side.value,
            None if self.condition is None else self.condition.value,
            tuple(item.value for item in self.evidence_refs),
            str(self.source_study.value),
            self.source_study_version.value,
        )


@dataclass(frozen=True, slots=True)
class TraderHistoryContradiction:
    """Two or more certified values for the same metric in the same scope."""

    metric_code: str
    markets: tuple[TraderHistoryMarketRef, ...]
    timeframes: tuple[TraderHistoryTimeframeRef, ...]
    regime: TraderHistoryRegimeRef | None
    session: TraderHistorySessionRef | None
    side: TraderHistorySide | None
    condition: TraderHistoryFavorableKind | None
    values: tuple[Decimal, ...]
    evidence_refs: tuple[TraderHistoryEvidenceRef, ...]

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.metric_code,
            tuple(item.value for item in self.markets),
            tuple(item.value for item in self.timeframes),
            None if self.regime is None else self.regime.value,
            None if self.session is None else self.session.value,
            None if self.side is None else self.side.value,
            None if self.condition is None else self.condition.value,
            tuple(_canonical_decimal(value) for value in self.values),
            tuple(item.value for item in self.evidence_refs),
        )


@dataclass(frozen=True, slots=True)
class TraderHistoryCurrentView:
    """Deterministic current evidence-backed capability projection.

    ``certified_metrics`` contains only certified, sufficient, evidence-backed
    claims; contradictory scopes are retained in ``contradictions`` (indeterminate)
    rather than silently choosing the favorable value. The view carries no
    authority fields and can never manufacture ``DEMO_ELIGIBLE``.
    """

    trader_version: TraderVersionIdentity
    derived_at: datetime
    certified_metrics: tuple[TraderHistoryMetricView, ...]
    contradictions: tuple[TraderHistoryContradiction, ...]
    exploratory_records: tuple[TraderHistoryStudyRecord, ...]
    stale_records: tuple[TraderHistoryStudyRecord, ...]
    insufficient_metrics: tuple[str, ...]
    consumed_holdouts: tuple[TraderHistoryPartitionIdentity, ...]
    evidence_refs: tuple[TraderHistoryEvidenceRef, ...]

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.trader_version.logical_values(),
            _utc_iso(self.derived_at, field_name="derived_at"),
            tuple(item.logical_values() for item in self.certified_metrics),
            tuple(item.logical_values() for item in self.contradictions),
            tuple(item.logical_values() for item in self.exploratory_records),
            tuple(item.logical_values() for item in self.stale_records),
            self.insufficient_metrics,
            tuple(item.logical_values() for item in self.consumed_holdouts),
            tuple(item.logical_values() for item in self.evidence_refs),
        )


def _metric_view_sort_key(view: TraderHistoryMetricView) -> tuple[object, ...]:
    return (
        view.metric_code,
        tuple(item.value for item in view.markets),
        tuple(item.value for item in view.timeframes),
        _none_safe(None if view.regime is None else view.regime.value),
        _none_safe(None if view.session is None else view.session.value),
        _none_safe(None if view.side is None else view.side.value),
        _none_safe(None if view.condition is None else view.condition.value),
        _canonical_decimal(view.value),
        str(view.source_study.value),
        view.source_study_version.value,
    )


def project_current_capability(
    registry: TraderHistoricalIntelligenceRegistry,
    trader_version: TraderVersionIdentity,
    *,
    derived_at: datetime,
) -> Result[TraderHistoryCurrentView, TraderHistoryBlockedError]:
    """Project a deterministic current capability view from certified history.

    The projection is a pure function of the registry and requested version; for
    identical history and identical inputs it always returns the identical view.
    """
    if type(registry) is not TraderHistoricalIntelligenceRegistry:
        return Failure(
            TraderHistoryBlockedError(
                "projection requires TraderHistoricalIntelligenceRegistry"
            )
        )
    if type(trader_version) is not TraderVersionIdentity:
        return Failure(
            TraderHistoryBlockedError("projection requires TraderVersionIdentity")
        )
    try:
        TraderVersionIdentity.__post_init__(trader_version)
        _validate_timestamp(derived_at, field_name="derived_at")
        records = studies_for_version(registry, trader_version)
    except TraderHistoryValidationError as error:
        return Failure(TraderHistoryBlockedError(f"projection input invalid: {error}"))

    # No hindsight: only evidence produced on or before ``derived_at`` can be
    # projected as the "current" view at that instant.
    records = tuple(
        record for record in records if record.produced_at <= derived_at
    )
    superseded_ids = {target for record in records for target in record.supersedes}
    certified = [
        record
        for record in records
        if record.epistemic_status is TraderHistoryEpistemicStatus.CERTIFIED
        and record.study_id not in superseded_ids
    ]
    exploratory = [
        record
        for record in records
        if record.epistemic_status
        not in (
            TraderHistoryEpistemicStatus.CERTIFIED,
            TraderHistoryEpistemicStatus.STALE,
            TraderHistoryEpistemicStatus.SUPERSEDED,
        )
        and record.study_id not in superseded_ids
    ]
    stale = [
        record
        for record in records
        if record.epistemic_status
        in (
            TraderHistoryEpistemicStatus.STALE,
            TraderHistoryEpistemicStatus.SUPERSEDED,
        )
        or record.study_id in superseded_ids
    ]

    views: list[TraderHistoryMetricView] = []
    for record in certified:
        for metric in record.quantitative_claims:
            views.append(
                TraderHistoryMetricView(
                    metric_code=metric.metric_code,
                    value=metric.value,
                    markets=record.market_scope,
                    timeframes=record.timeframe_scope,
                    regime=record.regime,
                    session=record.session,
                    side=record.side,
                    condition=record.condition,
                    evidence_refs=metric.evidence_refs,
                    source_study=record.study_id,
                    source_study_version=record.study_version,
                )
            )

    grouped: dict[tuple[str, _ScopeKey], list[TraderHistoryMetricView]] = {}
    for item in views:
        key = (
            item.metric_code,
            _scope_key(
                item.markets,
                item.timeframes,
                item.regime,
                item.session,
                item.side,
                item.condition,
            ),
        )
        grouped.setdefault(key, []).append(item)

    certified_metrics: list[TraderHistoryMetricView] = []
    contradictions: list[TraderHistoryContradiction] = []
    for (metric_code, _), group in grouped.items():
        distinct_values = sorted({view.value for view in group}, key=_canonical_decimal)
        refs = tuple(
            sorted(
                {
                    ref
                    for view in group
                    for ref in view.evidence_refs
                },
                key=lambda item: item.value,
            )
        )
        first = group[0]
        markets = first.markets
        timeframes = first.timeframes
        regime = first.regime
        session = first.session
        side = first.side
        condition = first.condition
        if len(distinct_values) > 1:
            contradictions.append(
                TraderHistoryContradiction(
                    metric_code=metric_code,
                    markets=markets,
                    timeframes=timeframes,
                    regime=regime,
                    session=session,
                    side=side,
                    condition=condition,
                    values=tuple(distinct_values),
                    evidence_refs=refs,
                )
            )
        else:
            certified_metrics.append(
                TraderHistoryMetricView(
                    metric_code=metric_code,
                    value=distinct_values[0],
                    markets=markets,
                    timeframes=timeframes,
                    regime=regime,
                    session=session,
                    side=side,
                    condition=condition,
                    evidence_refs=refs,
                    source_study=first.source_study,
                    source_study_version=first.source_study_version,
                )
            )

    insufficient_metrics = tuple(
        sorted(
            {
                metric.metric_code
                for record in records
                if (
                    record.sufficiency is TraderHistorySufficiency.INSUFFICIENT
                    or record.epistemic_status
                    is TraderHistoryEpistemicStatus.INSUFFICIENT_EVIDENCE
                )
                for metric in record.quantitative_claims
            }
        )
    )

    evidence_refs = tuple(
        sorted(
            {
                ref
                for view in certified_metrics
                for ref in view.evidence_refs
            },
            key=lambda item: item.value,
        )
    )

    view = TraderHistoryCurrentView(
        trader_version=trader_version,
        derived_at=derived_at,
        certified_metrics=tuple(
            sorted(certified_metrics, key=_metric_view_sort_key)
        ),
        contradictions=tuple(
            sorted(
                contradictions,
                key=lambda item: (
                    item.metric_code,
                    tuple(m.value for m in item.markets),
                    tuple(t.value for t in item.timeframes),
                    _none_safe(None if item.regime is None else item.regime.value),
                    _none_safe(None if item.session is None else item.session.value),
                    _none_safe(None if item.side is None else item.side.value),
                    _none_safe(None if item.condition is None else item.condition.value),
                ),
            )
        ),
        exploratory_records=tuple(sorted(exploratory, key=_record_sort_key)),
        stale_records=tuple(sorted(stale, key=_record_sort_key)),
        insufficient_metrics=insufficient_metrics,
        consumed_holdouts=consumed_holdouts(registry),
        evidence_refs=evidence_refs,
    )
    return Success(view)


@dataclass(frozen=True, slots=True)
class TraderHistoryMarketEvidence:
    """Per-market evidence projection: certified metrics + insufficient markers."""

    market: TraderHistoryMarketRef
    certified_metrics: tuple[TraderHistoryMetricView, ...]
    insufficient_metrics: tuple[str, ...]
    evidence_refs: tuple[TraderHistoryEvidenceRef, ...]

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.market.value,
            tuple(item.logical_values() for item in self.certified_metrics),
            self.insufficient_metrics,
            tuple(item.logical_values() for item in self.evidence_refs),
        )


def market_evidence(
    registry: TraderHistoricalIntelligenceRegistry,
    trader_version: TraderVersionIdentity,
) -> tuple[TraderHistoryMarketEvidence, ...]:
    """Return per-market certified/insufficient evidence without inventing rankings.

    No "best market" or relative ranking is inferred: each market is reported with
    only the evidence directly scoped to it, and insufficient samples stay
    insufficient rather than optimistic.
    """

    if type(registry) is not TraderHistoricalIntelligenceRegistry:
        raise TraderHistoryValidationError(
            "registry must be TraderHistoricalIntelligenceRegistry"
        )
    if type(trader_version) is not TraderVersionIdentity:
        raise TraderHistoryValidationError(
            "trader_version must be TraderVersionIdentity"
        )
    TraderVersionIdentity.__post_init__(trader_version)
    records = studies_for_version(registry, trader_version)
    markets = sorted(
        {market for record in records for market in record.market_scope},
        key=lambda item: item.value,
    )
    result: list[TraderHistoryMarketEvidence] = []
    for market in markets:
        scoped_certified: list[TraderHistoryMetricView] = []
        scoped_insufficient: set[str] = set()
        scoped_refs: set[TraderHistoryEvidenceRef] = set()
        for record in records:
            if market not in record.market_scope:
                continue
            if record.epistemic_status is TraderHistoryEpistemicStatus.CERTIFIED:
                for metric in record.quantitative_claims:
                    view = TraderHistoryMetricView(
                        metric_code=metric.metric_code,
                        value=metric.value,
                        markets=record.market_scope,
                        timeframes=record.timeframe_scope,
                        regime=record.regime,
                        session=record.session,
                        side=record.side,
                        condition=record.condition,
                        evidence_refs=metric.evidence_refs,
                        source_study=record.study_id,
                        source_study_version=record.study_version,
                    )
                    scoped_certified.append(view)
                    scoped_refs.update(metric.evidence_refs)
            elif (
                record.sufficiency is TraderHistorySufficiency.INSUFFICIENT
                or record.epistemic_status
                is TraderHistoryEpistemicStatus.INSUFFICIENT_EVIDENCE
            ):
                scoped_insufficient.update(
                    metric.metric_code for metric in record.quantitative_claims
                )
        result.append(
            TraderHistoryMarketEvidence(
                market=market,
                certified_metrics=tuple(
                    sorted(scoped_certified, key=_metric_view_sort_key)
                ),
                insufficient_metrics=tuple(sorted(scoped_insufficient)),
                evidence_refs=tuple(
                    sorted(scoped_refs, key=lambda item: item.value)
                ),
            )
        )
    return tuple(result)


def hypothesis_lineage(
    registry: TraderHistoricalIntelligenceRegistry,
    hypothesis_id: str,
) -> tuple[TraderHistoryStudyRecord, ...]:
    """Return the traceable lineage for one hypothesis id (hypothesis + verdicts)."""

    if type(registry) is not TraderHistoricalIntelligenceRegistry:
        raise TraderHistoryValidationError(
            "registry must be TraderHistoricalIntelligenceRegistry"
        )
    if type(hypothesis_id) is not str or not hypothesis_id:
        raise TraderHistoryValidationError("hypothesis_id must be a non-empty str")
    return tuple(
        sorted(
            (
                record
                for record in registry.records
                if record.hypothesis_id is not None
                and record.hypothesis_id.value == hypothesis_id
            ),
            key=_record_sort_key,
        )
    )


@dataclass(frozen=True, slots=True)
class TraderHistoryVersionDiff:
    """Deterministic evidence difference between two exact Trader versions."""

    left: TraderVersionIdentity
    right: TraderVersionIdentity
    left_only_kinds: tuple[str, ...]
    right_only_kinds: tuple[str, ...]
    left_certified_metrics: tuple[TraderHistoryMetricView, ...]
    right_certified_metrics: tuple[TraderHistoryMetricView, ...]
    left_insufficient_metrics: tuple[str, ...]
    right_insufficient_metrics: tuple[str, ...]

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.left.logical_values(),
            self.right.logical_values(),
            self.left_only_kinds,
            self.right_only_kinds,
            tuple(item.logical_values() for item in self.left_certified_metrics),
            tuple(item.logical_values() for item in self.right_certified_metrics),
            self.left_insufficient_metrics,
            self.right_insufficient_metrics,
        )


def diff_versions(
    registry: TraderHistoricalIntelligenceRegistry,
    left: TraderVersionIdentity,
    right: TraderVersionIdentity,
) -> TraderHistoryVersionDiff:
    """Return a deterministic evidence diff between two exact Trader versions."""

    if type(left) is not TraderVersionIdentity or type(right) is not TraderVersionIdentity:
        raise TraderHistoryValidationError("diff requires two TraderVersionIdentity")
    left_records = studies_for_version(registry, left)
    right_records = studies_for_version(registry, right)
    left_kinds = {record.kind.value for record in left_records}
    right_kinds = {record.kind.value for record in right_records}

    def _certified(
        records: tuple[TraderHistoryStudyRecord, ...],
    ) -> tuple[TraderHistoryMetricView, ...]:
        views: list[TraderHistoryMetricView] = []
        for record in records:
            if record.epistemic_status is not TraderHistoryEpistemicStatus.CERTIFIED:
                continue
            for metric in record.quantitative_claims:
                views.append(
                    TraderHistoryMetricView(
                        metric_code=metric.metric_code,
                        value=metric.value,
                        markets=record.market_scope,
                        timeframes=record.timeframe_scope,
                        regime=record.regime,
                        session=record.session,
                        side=record.side,
                        condition=record.condition,
                        evidence_refs=metric.evidence_refs,
                        source_study=record.study_id,
                        source_study_version=record.study_version,
                    )
                )
        return tuple(sorted(views, key=_metric_view_sort_key))

    def _insufficient(
        records: tuple[TraderHistoryStudyRecord, ...],
    ) -> tuple[str, ...]:
        return tuple(
            sorted(
                {
                    metric.metric_code
                    for record in records
                    if (
                        record.sufficiency is TraderHistorySufficiency.INSUFFICIENT
                        or record.epistemic_status
                        is TraderHistoryEpistemicStatus.INSUFFICIENT_EVIDENCE
                    )
                    for metric in record.quantitative_claims
                }
            )
        )

    return TraderHistoryVersionDiff(
        left=left,
        right=right,
        left_only_kinds=tuple(sorted(left_kinds - right_kinds)),
        right_only_kinds=tuple(sorted(right_kinds - left_kinds)),
        left_certified_metrics=_certified(left_records),
        right_certified_metrics=_certified(right_records),
        left_insufficient_metrics=_insufficient(left_records),
        right_insufficient_metrics=_insufficient(right_records),
    )
