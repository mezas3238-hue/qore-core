from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import pytest

from qore.infrastructure.research_sample_partition import SampleRole
from qore.infrastructure.trader_history.contracts import (
    TraderHistoryAuthorityKind,
    TraderHistoryCertification,
    TraderHistoryEpistemicStatus,
    TraderHistoryEvidenceRef,
    TraderHistoryFinding,
    TraderHistoryMarketRef,
    TraderHistoryMetric,
    TraderHistoryPartitionIdentity,
    TraderHistoryProducerId,
    TraderHistorySide,
    TraderHistorySoftwareSha,
    TraderHistoryStudyId,
    TraderHistoryStudyKind,
    TraderHistoryStudyRecord,
    TraderHistoryStudyVersion,
    TraderHistorySufficiency,
    TraderHistoryTimeframeRef,
    TraderHistoryValidationError,
    TraderVersionFingerprint,
    TraderVersionIdentity,
    build_study_record,
    build_trader_version_identity,
    validate_study_record,
)
from qore.infrastructure.traders.contracts import (
    DemoTradingConfigFingerprint,
    DemoTradingMethodologyFingerprint,
    DemoTradingMethodologyId,
    DemoTradingMethodologyVersion,
    DemoTradingTraderCode,
    DemoTradingTraderVersion,
)

_NOW = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)


def _fp(n: int) -> str:
    return f"{n:064x}"


def _fp40(n: int) -> str:
    return f"{n:040x}"


_DEV_PARTITION_ID = UUID("00000000-0000-0000-0000-000000000001")


def _dev_partition(n: int = 90) -> TraderHistoryPartitionIdentity:
    return TraderHistoryPartitionIdentity(_DEV_PARTITION_ID, _fp(n), SampleRole.DEVELOPMENT)


_AUTHORITY_KIND_BY_KIND = {
    TraderHistoryStudyKind.INDEPENDENT_VALIDATION: (
        TraderHistoryAuthorityKind.INDEPENDENT_VALIDATION
    ),
    TraderHistoryStudyKind.RISK_REVIEW: TraderHistoryAuthorityKind.RISK,
    TraderHistoryStudyKind.CIBO_REVIEW: TraderHistoryAuthorityKind.CIBO,
    TraderHistoryStudyKind.ECONOMIC_EVALUATION: TraderHistoryAuthorityKind.ECONOMIC,
}


_AUTHORITY_ID = UUID("00000000-0000-4000-8000-0000000000aa")


def _certification(
    kind: TraderHistoryStudyKind,
    produced_at: datetime = _NOW,
    *,
    study_id: TraderHistoryStudyId | None = None,
    study_version: str = "v1",
) -> TraderHistoryCertification:
    authority_kind = _AUTHORITY_KIND_BY_KIND.get(
        kind, TraderHistoryAuthorityKind.TRADER_LAB
    )
    certification = object.__new__(TraderHistoryCertification)
    object.__setattr__(certification, "authority_kind", authority_kind)
    object.__setattr__(certification, "authority_id", _AUTHORITY_ID)
    object.__setattr__(certification, "issued_at", produced_at)
    object.__setattr__(
        certification,
        "study_id",
        study_id if study_id is not None else TraderHistoryStudyId(uuid4()),
    )
    object.__setattr__(
        certification,
        "study_version",
        TraderHistoryStudyVersion(study_version),
    )
    object.__setattr__(certification, "_issued", True)
    return certification


def _rebind_certification(
    certification: TraderHistoryCertification,
    study_id: TraderHistoryStudyId,
    study_version: TraderHistoryStudyVersion,
) -> TraderHistoryCertification:
    if (
        certification.study_id == study_id
        and certification.study_version == study_version
    ):
        return certification
    rebound = object.__new__(TraderHistoryCertification)
    object.__setattr__(rebound, "authority_kind", certification.authority_kind)
    object.__setattr__(rebound, "authority_id", certification.authority_id)
    object.__setattr__(rebound, "issued_at", certification.issued_at)
    object.__setattr__(rebound, "study_id", study_id)
    object.__setattr__(rebound, "study_version", study_version)
    object.__setattr__(rebound, "_issued", True)
    return rebound


def _version(code: str = "vt-08", version: str = "v1", config: int = 1) -> TraderVersionIdentity:
    return build_trader_version_identity(
        trader_code=DemoTradingTraderCode(code),
        version=DemoTradingTraderVersion(version),
        config_fingerprint=DemoTradingConfigFingerprint(_fp(config)),
        methodology_id=DemoTradingMethodologyId("ny-precision-core"),
        methodology_version=DemoTradingMethodologyVersion("v1"),
        methodology_fingerprint=DemoTradingMethodologyFingerprint(_fp(2)),
        software_sha=TraderHistorySoftwareSha(_fp40(3)),
    )


def _ref(value: str = "evidence:replay") -> TraderHistoryEvidenceRef:
    return TraderHistoryEvidenceRef(value)


def _metric(code: str = "expectancy", value: str = "0.10") -> TraderHistoryMetric:
    return TraderHistoryMetric(code, Decimal(value), (_ref(),))


def _study(**overrides: Any) -> TraderHistoryStudyRecord:
    kwargs: dict[str, Any] = {
        "study_id": TraderHistoryStudyId(uuid4()),
        "study_version": TraderHistoryStudyVersion("v1"),
        "trader_version": _version(),
        "kind": TraderHistoryStudyKind.REPLAY,
        "epistemic_status": TraderHistoryEpistemicStatus.CERTIFIED,
        "sufficiency": TraderHistorySufficiency.SUFFICIENT,
        "produced_at": _NOW,
        "producer": TraderHistoryProducerId("trader-lab"),
        "market_scope": (TraderHistoryMarketRef("EUR/USD"),),
        "timeframe_scope": (TraderHistoryTimeframeRef("h1"),),
        "partitions": (_dev_partition(),),
        "quantitative_claims": (_metric(),),
    }
    kwargs.update(overrides)
    if kwargs["epistemic_status"] is TraderHistoryEpistemicStatus.CERTIFIED:
        if "certification" in kwargs:
            kwargs["certification"] = _rebind_certification(
                kwargs["certification"], kwargs["study_id"], kwargs["study_version"]
            )
        else:
            kwargs["certification"] = _certification(
                kwargs["kind"],
                kwargs["produced_at"],
                study_id=kwargs["study_id"],
                study_version=kwargs["study_version"].value,
            )
    return build_study_record(**kwargs)


def test_version_fingerprint_is_deterministic_and_content_bound() -> None:
    left = _version(config=1)
    right = _version(config=1)
    assert left == right
    assert left.fingerprint == right.fingerprint
    changed = _version(config=2)
    assert changed.fingerprint != left.fingerprint


def test_version_identity_rejects_wrong_fingerprint() -> None:
    good = _version()
    with pytest.raises(TraderHistoryValidationError):
        TraderVersionIdentity(
            trader_code=good.trader_code,
            version=good.version,
            config_fingerprint=good.config_fingerprint,
            methodology_id=good.methodology_id,
            methodology_version=good.methodology_version,
            methodology_fingerprint=good.methodology_fingerprint,
            software_sha=good.software_sha,
            fingerprint=TraderVersionFingerprint(_fp(99)),
        )


def test_study_record_builds_and_orders_canonically() -> None:
    study = _study(
        market_scope=(
            TraderHistoryMarketRef("GBP/USD"),
            TraderHistoryMarketRef("EUR/USD"),
        ),
        timeframe_scope=(
            TraderHistoryTimeframeRef("d1"),
            TraderHistoryTimeframeRef("h1"),
        ),
    )
    assert tuple(m.value for m in study.market_scope) == ("EUR/USD", "GBP/USD")
    assert tuple(t.value for t in study.timeframe_scope) == ("d1", "h1")


def test_certified_requires_sufficient() -> None:
    with pytest.raises(TraderHistoryValidationError):
        _study(sufficiency=TraderHistorySufficiency.INSUFFICIENT)


def test_insufficient_evidence_requires_insufficient_sufficiency() -> None:
    with pytest.raises(TraderHistoryValidationError):
        _study(
            epistemic_status=TraderHistoryEpistemicStatus.INSUFFICIENT_EVIDENCE,
            sufficiency=TraderHistorySufficiency.SUFFICIENT,
        )


def test_hypothesis_kind_cannot_be_certified() -> None:
    with pytest.raises(TraderHistoryValidationError):
        _study(
            kind=TraderHistoryStudyKind.HYPOTHESIS,
            epistemic_status=TraderHistoryEpistemicStatus.CERTIFIED,
        )


def test_hypothesis_kind_requires_hypothesis_status() -> None:
    with pytest.raises(TraderHistoryValidationError):
        _study(kind=TraderHistoryStudyKind.HYPOTHESIS)


def test_failure_analysis_must_be_inferred() -> None:
    with pytest.raises(TraderHistoryValidationError):
        _study(
            kind=TraderHistoryStudyKind.FAILURE_ANALYSIS,
            epistemic_status=TraderHistoryEpistemicStatus.OBSERVED,
        )
    study = _study(
        kind=TraderHistoryStudyKind.FAILURE_ANALYSIS,
        epistemic_status=TraderHistoryEpistemicStatus.INFERRED,
    )
    assert study.kind is TraderHistoryStudyKind.FAILURE_ANALYSIS


def test_metric_without_evidence_ref_fails_closed() -> None:
    with pytest.raises(TraderHistoryValidationError):
        TraderHistoryMetric("expectancy", Decimal("0.1"), ())


def test_metric_rejects_float_as_decimal() -> None:
    with pytest.raises(TraderHistoryValidationError):
        TraderHistoryMetric("expectancy", 0.1, (_ref(),))  # type: ignore[arg-type]


def test_metric_rejects_bool_as_evidence_ref() -> None:
    with pytest.raises(TraderHistoryValidationError):
        TraderHistoryMetric("expectancy", Decimal("0.1"), (True,))  # type: ignore[arg-type]


def test_market_rejects_bool_and_int() -> None:
    with pytest.raises(TraderHistoryValidationError):
        TraderHistoryMarketRef(True)  # type: ignore[arg-type]
    with pytest.raises(TraderHistoryValidationError):
        TraderHistoryMarketRef(1)  # type: ignore[arg-type]


def test_timezone_naive_timestamp_fails_closed() -> None:
    with pytest.raises(TraderHistoryValidationError):
        _study(produced_at=datetime(2026, 1, 1, 0, 0))


def test_exact_runtime_type_rejects_enum_string_laundering() -> None:
    with pytest.raises(TraderHistoryValidationError):
        _study(sufficiency="sufficient")
    with pytest.raises(TraderHistoryValidationError):
        _study(kind="replay")


def test_side_is_exact_enum() -> None:
    study = _study(side=TraderHistorySide.BUY)
    assert study.side is TraderHistorySide.BUY
    with pytest.raises(TraderHistoryValidationError):
        _study(side="buy")


def test_quantitative_claim_requires_observed_inferred_or_certified() -> None:
    with pytest.raises(TraderHistoryValidationError):
        _study(
            kind=TraderHistoryStudyKind.HYPOTHESIS,
            epistemic_status=TraderHistoryEpistemicStatus.HYPOTHESIS,
            quantitative_claims=(_metric(),),
        )


def test_partition_identity_exact_types() -> None:
    partition = TraderHistoryPartitionIdentity(
        partition_id=uuid4(),
        dataset_fingerprint=_fp(7),
        role=SampleRole.EXTERNAL_VALIDATION,
    )
    assert partition.role is SampleRole.EXTERNAL_VALIDATION
    with pytest.raises(TraderHistoryValidationError):
        TraderHistoryPartitionIdentity(
            partition_id=uuid4(),
            dataset_fingerprint=_fp(7),
            role="external_validation",  # type: ignore[arg-type]
        )


def test_finding_requires_evidence() -> None:
    with pytest.raises(TraderHistoryValidationError):
        TraderHistoryFinding("negative-expectancy", ())
    finding = TraderHistoryFinding("negative-expectancy", (_ref(),))
    assert finding.finding_code == "negative-expectancy"


def test_evidence_ref_rejects_sensitive_material() -> None:
    for value in ("client_secret", "private_key", "authorization:bearer"):
        with pytest.raises(TraderHistoryValidationError):
            TraderHistoryEvidenceRef(value)
    # Benign control: a normal opaque ref is still accepted.
    assert TraderHistoryEvidenceRef("evidence:replay").value == "evidence:replay"


def test_study_fingerprint_detects_payload_change() -> None:
    left = _study()
    right = _study(study_id=left.study_id, study_version=left.study_version)
    assert left.study_id == right.study_id
    assert left.fingerprint == right.fingerprint  # same logical content
    changed = _study(
        study_id=left.study_id,
        study_version=left.study_version,
        quantitative_claims=(_metric(value="0.99"),),
    )
    assert changed.fingerprint != left.fingerprint


def test_supersedes_and_limitations_are_canonical() -> None:
    a = TraderHistoryStudyId(uuid4())
    b = TraderHistoryStudyId(uuid4())
    study = _study(
        supersedes=(b, a),
        limitations=("known-limitation-b", "known-limitation-a"),
    )
    assert set(study.supersedes) == {a, b}
    assert study.supersedes == tuple(
        sorted((a, b), key=lambda item: str(item.value))
    )
    assert study.limitations == ("known-limitation-a", "known-limitation-b")


def test_reflective_corruption_of_partition_role_fails_closed() -> None:
    partition = TraderHistoryPartitionIdentity(
        partition_id=uuid4(),
        dataset_fingerprint=_fp(7),
        role=SampleRole.EXTERNAL_VALIDATION,
    )
    sid = TraderHistoryStudyId(uuid4())
    study = build_study_record(
        study_id=sid,
        study_version=TraderHistoryStudyVersion("v1"),
        trader_version=_version(),
        kind=TraderHistoryStudyKind.OOS,
        epistemic_status=TraderHistoryEpistemicStatus.CERTIFIED,
        sufficiency=TraderHistorySufficiency.SUFFICIENT,
        produced_at=_NOW,
        producer=TraderHistoryProducerId("trader-lab"),
        certification=_certification(TraderHistoryStudyKind.OOS, _NOW, study_id=sid),
        market_scope=(TraderHistoryMarketRef("EUR/USD"),),
        timeframe_scope=(TraderHistoryTimeframeRef("h1"),),
        partitions=(partition,),
    )
    object.__setattr__(partition, "role", "external_validation")
    with pytest.raises(TraderHistoryValidationError):
        validate_study_record(study)


def test_reflective_corruption_of_metric_value_fails_closed() -> None:
    metric = _metric()
    sid = TraderHistoryStudyId(uuid4())
    study = build_study_record(
        study_id=sid,
        study_version=TraderHistoryStudyVersion("v1"),
        trader_version=_version(),
        kind=TraderHistoryStudyKind.REPLAY,
        epistemic_status=TraderHistoryEpistemicStatus.CERTIFIED,
        sufficiency=TraderHistorySufficiency.SUFFICIENT,
        produced_at=_NOW,
        producer=TraderHistoryProducerId("trader-lab"),
        certification=_certification(
            TraderHistoryStudyKind.REPLAY, _NOW, study_id=sid
        ),
        market_scope=(TraderHistoryMarketRef("EUR/USD"),),
        timeframe_scope=(TraderHistoryTimeframeRef("h1"),),
        partitions=(_dev_partition(),),
        quantitative_claims=(metric,),
    )
    object.__setattr__(metric, "value", 0.5)
    with pytest.raises(TraderHistoryValidationError):
        validate_study_record(study)


def test_certified_quantitative_claim_requires_partition() -> None:
    with pytest.raises(TraderHistoryValidationError):
        _study(partitions=())


def test_hypothesis_status_requires_hypothesis_kind() -> None:
    with pytest.raises(TraderHistoryValidationError):
        _study(
            kind=TraderHistoryStudyKind.REPLAY,
            epistemic_status=TraderHistoryEpistemicStatus.HYPOTHESIS,
        )


def test_falsified_status_requires_falsification_kind() -> None:
    with pytest.raises(TraderHistoryValidationError):
        _study(
            kind=TraderHistoryStudyKind.REPLAY,
            epistemic_status=TraderHistoryEpistemicStatus.FALSIFIED,
        )
