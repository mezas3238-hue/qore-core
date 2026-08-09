from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from uuid import UUID

import pytest

from qore.infrastructure.research_hypothesis_family import (
    ResearchBootstrapHypothesisPlan,
    ResearchHypothesisFamilyManifestId,
    ResearchHypothesisFamilyValidationError,
    build_research_bootstrap_hypothesis_family_evidence,
    build_research_bootstrap_hypothesis_family_manifest,
)
from qore.infrastructure.research_periodic_bootstrap_test import (
    ResearchPeriodicBootstrapAlternative,
    ResearchPeriodicBootstrapTestEvidence,
    ResearchPeriodicBootstrapTestId,
    ResearchPeriodicBootstrapTestPolicy,
    build_research_periodic_bootstrap_test_evidence,
)
from qore.infrastructure.research_periodic_equity import (
    ResearchPeriodicEquityReturnSeries,
    ResearchPeriodicReturnPoint,
)
from qore.kernel.result import Failure, Success


def _uuid(suffix: int) -> UUID:
    return UUID(f"89000000-0000-0000-0000-{suffix:012d}")


def _point(value: str) -> ResearchPeriodicReturnPoint:
    point = object.__new__(ResearchPeriodicReturnPoint)
    object.__setattr__(point, "return_rate", Decimal(value))
    return point


def _series(*values: str) -> ResearchPeriodicEquityReturnSeries:
    series = object.__new__(ResearchPeriodicEquityReturnSeries)
    object.__setattr__(series, "returns", tuple(_point(value) for value in values))
    return series


def _policy(seed: int) -> ResearchPeriodicBootstrapTestPolicy:
    return ResearchPeriodicBootstrapTestPolicy(
        null_mean_per_period=Decimal("0"),
        alternative=ResearchPeriodicBootstrapAlternative.GREATER,
        block_length=2,
        resample_count=12,
        seed=seed,
    )


def _evidence(
    suffix: int,
    series: ResearchPeriodicEquityReturnSeries,
    policy: ResearchPeriodicBootstrapTestPolicy,
) -> ResearchPeriodicBootstrapTestEvidence:
    built = build_research_periodic_bootstrap_test_evidence(
        test_id=ResearchPeriodicBootstrapTestId(_uuid(suffix)),
        series=series,
        policy=policy,
    )
    assert isinstance(built, Success)
    return built.value


def test_manifest_canonicalizes_family_by_test_id() -> None:
    first_series = _series("0.1", "0.2", "0.3", "0.4")
    second_series = _series("0.2", "0.1", "0.4", "0.3")
    first = ResearchBootstrapHypothesisPlan(
        test_id=ResearchPeriodicBootstrapTestId(_uuid(1)),
        series=first_series,
        policy=_policy(1),
    )
    second = ResearchBootstrapHypothesisPlan(
        test_id=ResearchPeriodicBootstrapTestId(_uuid(2)),
        series=second_series,
        policy=_policy(2),
    )

    built = build_research_bootstrap_hypothesis_family_manifest(
        manifest_id=ResearchHypothesisFamilyManifestId(_uuid(100)),
        plans=(second, first),
    )

    assert isinstance(built, Success)
    assert built.value.plans == (first, second)
    assert built.value.family_size == 2


def test_manifest_rejects_duplicate_test_ids() -> None:
    series = _series("0.1", "0.2", "0.3", "0.4")
    duplicate_id = ResearchPeriodicBootstrapTestId(_uuid(10))
    built = build_research_bootstrap_hypothesis_family_manifest(
        manifest_id=ResearchHypothesisFamilyManifestId(_uuid(101)),
        plans=(
            ResearchBootstrapHypothesisPlan(
                test_id=duplicate_id,
                series=series,
                policy=_policy(1),
            ),
            ResearchBootstrapHypothesisPlan(
                test_id=duplicate_id,
                series=series,
                policy=_policy(2),
            ),
        ),
    )

    assert isinstance(built, Failure)
    assert "unique" in str(built.error)


def test_family_evidence_binds_exact_manifest_series_and_policy() -> None:
    first_series = _series("0.1", "0.2", "0.3", "0.4")
    second_series = _series("0.4", "0.3", "0.2", "0.1")
    first_policy = _policy(3)
    second_policy = _policy(4)
    first_plan = ResearchBootstrapHypothesisPlan(
        test_id=ResearchPeriodicBootstrapTestId(_uuid(20)),
        series=first_series,
        policy=first_policy,
    )
    second_plan = ResearchBootstrapHypothesisPlan(
        test_id=ResearchPeriodicBootstrapTestId(_uuid(21)),
        series=second_series,
        policy=second_policy,
    )
    manifest_result = build_research_bootstrap_hypothesis_family_manifest(
        manifest_id=ResearchHypothesisFamilyManifestId(_uuid(102)),
        plans=(first_plan, second_plan),
    )
    assert isinstance(manifest_result, Success)
    first_result = _evidence(20, first_series, first_policy)
    second_result = _evidence(21, second_series, second_policy)

    built = build_research_bootstrap_hypothesis_family_evidence(
        manifest=manifest_result.value,
        tests=(second_result, first_result),
    )

    assert isinstance(built, Success)
    assert built.value.tests == (first_result, second_result)
    assert built.value.family_size == 2


def test_family_evidence_rejects_result_policy_mismatch() -> None:
    series = _series("0.1", "0.2", "0.3", "0.4")
    first_policy = _policy(5)
    second_policy = _policy(6)
    first_plan = ResearchBootstrapHypothesisPlan(
        test_id=ResearchPeriodicBootstrapTestId(_uuid(30)),
        series=series,
        policy=first_policy,
    )
    second_plan = ResearchBootstrapHypothesisPlan(
        test_id=ResearchPeriodicBootstrapTestId(_uuid(31)),
        series=series,
        policy=second_policy,
    )
    manifest_result = build_research_bootstrap_hypothesis_family_manifest(
        manifest_id=ResearchHypothesisFamilyManifestId(_uuid(103)),
        plans=(first_plan, second_plan),
    )
    assert isinstance(manifest_result, Success)
    wrong_policy = _policy(99)

    built = build_research_bootstrap_hypothesis_family_evidence(
        manifest=manifest_result.value,
        tests=(
            _evidence(30, series, wrong_policy),
            _evidence(31, series, second_policy),
        ),
    )

    assert isinstance(built, Failure)
    assert "policy" in str(built.error)


def test_family_evidence_rejects_missing_manifest_member() -> None:
    series = _series("0.1", "0.2", "0.3", "0.4")
    first_policy = _policy(7)
    second_policy = _policy(8)
    manifest_result = build_research_bootstrap_hypothesis_family_manifest(
        manifest_id=ResearchHypothesisFamilyManifestId(_uuid(104)),
        plans=(
            ResearchBootstrapHypothesisPlan(
                test_id=ResearchPeriodicBootstrapTestId(_uuid(40)),
                series=series,
                policy=first_policy,
            ),
            ResearchBootstrapHypothesisPlan(
                test_id=ResearchPeriodicBootstrapTestId(_uuid(41)),
                series=series,
                policy=second_policy,
            ),
        ),
    )
    assert isinstance(manifest_result, Success)

    built = build_research_bootstrap_hypothesis_family_evidence(
        manifest=manifest_result.value,
        tests=(_evidence(40, series, first_policy),),
    )

    assert isinstance(built, Failure)


def test_manifest_object_rejects_noncanonical_plan_order() -> None:
    series = _series("0.1", "0.2", "0.3", "0.4")
    first = ResearchBootstrapHypothesisPlan(
        test_id=ResearchPeriodicBootstrapTestId(_uuid(50)),
        series=series,
        policy=_policy(10),
    )
    second = ResearchBootstrapHypothesisPlan(
        test_id=ResearchPeriodicBootstrapTestId(_uuid(51)),
        series=series,
        policy=_policy(11),
    )
    built = build_research_bootstrap_hypothesis_family_manifest(
        manifest_id=ResearchHypothesisFamilyManifestId(_uuid(105)),
        plans=(first, second),
    )
    assert isinstance(built, Success)

    with pytest.raises(ResearchHypothesisFamilyValidationError):
        replace(built.value, plans=(second, first))


def test_family_manifest_does_not_claim_preregistration_or_production() -> None:
    series = _series("0.1", "0.2", "0.3", "0.4")
    built = build_research_bootstrap_hypothesis_family_manifest(
        manifest_id=ResearchHypothesisFamilyManifestId(_uuid(106)),
        plans=(
            ResearchBootstrapHypothesisPlan(
                test_id=ResearchPeriodicBootstrapTestId(_uuid(60)),
                series=series,
                policy=_policy(12),
            ),
            ResearchBootstrapHypothesisPlan(
                test_id=ResearchPeriodicBootstrapTestId(_uuid(61)),
                series=series,
                policy=_policy(13),
            ),
        ),
    )
    assert isinstance(built, Success)
    manifest = built.value

    assert not hasattr(manifest, "preregistered")
    assert not hasattr(manifest, "frozen_before_outcomes")
    assert not hasattr(manifest, "strategy_approved")
    assert not hasattr(manifest, "production_ready")
