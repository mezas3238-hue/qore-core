from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

import qore.infrastructure.client_accounts as accounts
import qore.infrastructure.hosting_latency_safety as latency
import qore.infrastructure.hosting_reliability_lab as lab
import qore.kernel.result as result

_NOW = datetime(2026, 8, 10, 4, 0, tzinfo=UTC)
_ACCOUNT = accounts.TradingAccountId(UUID("56000000-0000-0000-0000-000000000003"))
_OTHER_ACCOUNT = accounts.TradingAccountId(
    UUID("56000000-0000-0000-0000-000000000099")
)
_RUNTIME = accounts.ExecutionRuntimeReference(
    UUID("56000000-0000-0000-0000-000000000004")
)


def _uuid(suffix: int) -> UUID:
    return UUID(f"56000000-0000-0000-0000-{suffix:012d}")


def _duration(milliseconds: int) -> latency.HostingLatencyDuration:
    return latency.HostingLatencyDuration.from_milliseconds(milliseconds)


def _distribution(
    *,
    p50: int = 15,
    p95: int = 20,
    p99: int = 25,
    maximum: int = 28,
    boundary: lab.HostingReliabilityBoundary = (
        lab.HostingReliabilityBoundary.NETWORK_EGRESS
    ),
    account_id: accounts.TradingAccountId = _ACCOUNT,
) -> latency.HostingLatencyDistribution:
    return latency.HostingLatencyDistribution(
        account_id=account_id,
        runtime_ref=_RUNTIME,
        boundary=boundary,
        sample_count=1_000,
        minimum=_duration(5),
        p50=_duration(p50),
        p95=_duration(p95),
        p99=_duration(p99),
        maximum=_duration(maximum),
        jitter=_duration(3),
        window_started_at=_NOW - timedelta(minutes=1),
        window_ended_at=_NOW,
        evidence_ref=lab.HostingReliabilityEvidenceReference(_uuid(10)),
    )


def _baseline(
    *,
    boundary: lab.HostingReliabilityBoundary = (
        lab.HostingReliabilityBoundary.NETWORK_EGRESS
    ),
    account_id: accounts.TradingAccountId = _ACCOUNT,
) -> latency.HostingLatencyBaseline:
    return latency.HostingLatencyBaseline(
        account_id=account_id,
        runtime_ref=_RUNTIME,
        boundary=boundary,
        reference_p50=_duration(10),
        reference_p95=_duration(15),
        reference_p99=_duration(20),
        certified_at=_NOW - timedelta(minutes=2),
        evidence_ref=lab.HostingReliabilityEvidenceReference(_uuid(11)),
    )


def _envelope_policy(
    *,
    contain_on_degraded: bool = True,
    hard_ceiling_ms: int = 300,
) -> latency.HostingLatencyEnvelopePolicy:
    return latency.HostingLatencyEnvelopePolicy(
        policy_ref=lab.HostingReliabilityPolicyReference(_uuid(20)),
        evidence_ref=lab.HostingReliabilityEvidenceReference(_uuid(21)),
        absolute_warning=_duration(50),
        absolute_degraded=_duration(100),
        catastrophic_hard_ceiling=_duration(hard_ceiling_ms),
        relative_warning_basis_points=15_000,
        relative_degraded_basis_points=20_000,
        contain_on_degraded=contain_on_degraded,
        effective_at=_NOW - timedelta(minutes=5),
        expires_at=None,
    )


def _lab_policy(
    *actions: lab.HostingReliabilityInfrastructureAction,
) -> lab.HostingReliabilityPolicySnapshot:
    return lab.HostingReliabilityPolicySnapshot(
        policy_ref=lab.HostingReliabilityPolicyReference(_uuid(30)),
        version=1,
        allowed_actions=(lab.HostingReliabilityInfrastructureAction.NO_ACTION, *actions),
        effective_at=_NOW - timedelta(minutes=5),
        expires_at=None,
    )


def _evaluate(
    distribution: latency.HostingLatencyDistribution,
    *,
    baseline: latency.HostingLatencyBaseline | None = None,
    envelope_policy: latency.HostingLatencyEnvelopePolicy | None = None,
    reliability_policy: lab.HostingReliabilityPolicySnapshot | None = None,
) -> result.Result[
    latency.HostingLatencyEnvelopeAssessment,
    latency.HostingLatencySafetyError,
]:
    return latency.evaluate_hosting_latency_envelope(
        distribution,
        baseline or _baseline(boundary=distribution.boundary),
        envelope_policy or _envelope_policy(),
        reliability_policy
        or _lab_policy(lab.HostingReliabilityInfrastructureAction.CONTAIN_NEW_WORK),
        observation_id=lab.HostingReliabilityObservationId(_uuid(40)),
        assessment_id=lab.HostingReliabilityAssessmentId(_uuid(41)),
        evaluated_at=_NOW + timedelta(seconds=1),
    )


def test_duration_is_integer_microseconds_and_300ms_ceiling_is_exact() -> None:
    assert _duration(300).microseconds == 300_000
    assert latency.PROVISIONAL_CATASTROPHIC_HARD_CEILING_US == 300_000
    assert latency.PROVISIONAL_CATASTROPHIC_HARD_CEILING == _duration(300)

    with pytest.raises(latency.HostingLatencySafetyValidationError):
        latency.HostingLatencyDuration(-1)


def test_distribution_requires_monotonic_percentiles() -> None:
    with pytest.raises(latency.HostingLatencySafetyValidationError):
        _distribution(p50=15, p95=40, p99=30, maximum=50)


def test_policy_cannot_weaken_catastrophic_ceiling_above_300ms() -> None:
    with pytest.raises(latency.HostingLatencySafetyValidationError):
        _envelope_policy(hard_ceiling_ms=301)


def test_certified_valley_records_no_action_with_evidence() -> None:
    evaluated = _evaluate(_distribution())

    assert isinstance(evaluated, result.Success)
    assert evaluated.value.state is latency.HostingLatencyEnvelopeState.CERTIFIED
    assert evaluated.value.effective_warning == _duration(30)
    assert evaluated.value.effective_degraded == _duration(40)
    assert evaluated.value.reliability_assessment.authorized_action is (
        lab.HostingReliabilityInfrastructureAction.NO_ACTION
    )
    assert evaluated.value.reliability_observation.condition is (
        lab.HostingReliabilityCondition.NORMAL
    )


def test_relative_warning_detects_deterioration_below_absolute_warning() -> None:
    evaluated = _evaluate(_distribution(p50=18, p95=28, p99=35, maximum=38))

    assert isinstance(evaluated, result.Success)
    assert evaluated.value.state is latency.HostingLatencyEnvelopeState.WARNING
    assert evaluated.value.distribution.p99 < _duration(50)
    assert evaluated.value.reliability_assessment.authorized_action is (
        lab.HostingReliabilityInfrastructureAction.NO_ACTION
    )


def test_degraded_path_can_contain_new_work_when_policy_authorizes_it() -> None:
    evaluated = _evaluate(_distribution(p50=20, p95=35, p99=45, maximum=48))

    assert isinstance(evaluated, result.Success)
    assert evaluated.value.state is latency.HostingLatencyEnvelopeState.DEGRADED
    assert evaluated.value.reliability_assessment.authorized_action is (
        lab.HostingReliabilityInfrastructureAction.CONTAIN_NEW_WORK
    )
    assert evaluated.value.reliability_observation.severity is (
        lab.HostingReliabilitySeverity.DEGRADED
    )


def test_degraded_path_may_record_no_action_without_required_containment() -> None:
    evaluated = _evaluate(
        _distribution(p50=20, p95=35, p99=45, maximum=48),
        envelope_policy=_envelope_policy(contain_on_degraded=False),
        reliability_policy=_lab_policy(),
    )

    assert isinstance(evaluated, result.Success)
    assert evaluated.value.state is latency.HostingLatencyEnvelopeState.DEGRADED
    assert evaluated.value.reliability_assessment.authorized_action is (
        lab.HostingReliabilityInfrastructureAction.NO_ACTION
    )


def test_catastrophic_300ms_breach_contains_but_never_authorizes_failover() -> None:
    evaluated = _evaluate(
        _distribution(p50=20, p95=35, p99=50, maximum=300),
    )

    assert isinstance(evaluated, result.Success)
    assert evaluated.value.state is latency.HostingLatencyEnvelopeState.EMERGENCY
    assert evaluated.value.reliability_assessment.authorized_action is (
        lab.HostingReliabilityInfrastructureAction.CONTAIN_NEW_WORK
    )
    assert not hasattr(evaluated.value, "failover")
    assert not hasattr(evaluated.value, "switch_server")
    assert not hasattr(evaluated.value, "acquire_lease")


def test_breach_is_not_authority_when_lab_policy_disallows_containment() -> None:
    evaluated = _evaluate(
        _distribution(p50=20, p95=35, p99=50, maximum=300),
        reliability_policy=_lab_policy(),
    )

    assert isinstance(evaluated, result.Failure)
    assert isinstance(evaluated.error, latency.HostingLatencySafetyAuthorizationError)


def test_maximum_spike_can_degrade_while_p99_remains_in_certified_valley() -> None:
    evaluated = _evaluate(
        _distribution(p50=15, p95=20, p99=25, maximum=100),
    )

    assert isinstance(evaluated, result.Success)
    assert evaluated.value.state is latency.HostingLatencyEnvelopeState.DEGRADED


def test_distribution_and_baseline_must_have_exact_same_scope() -> None:
    evaluated = _evaluate(
        _distribution(),
        baseline=_baseline(account_id=_OTHER_ACCOUNT),
    )

    assert isinstance(evaluated, result.Failure)
    assert isinstance(evaluated.error, latency.HostingLatencySafetyValidationError)


def test_only_latency_boundaries_are_accepted() -> None:
    with pytest.raises(latency.HostingLatencySafetyValidationError):
        _distribution(boundary=lab.HostingReliabilityBoundary.MARKET_DATA)


def test_ingress_internal_egress_and_round_trip_are_independent_surfaces() -> None:
    for boundary in (
        lab.HostingReliabilityBoundary.NETWORK_INGRESS,
        lab.HostingReliabilityBoundary.INTERNAL_PIPELINE,
        lab.HostingReliabilityBoundary.NETWORK_EGRESS,
        lab.HostingReliabilityBoundary.ROUND_TRIP,
    ):
        evaluated = _evaluate(_distribution(boundary=boundary))
        assert isinstance(evaluated, result.Success)
        assert evaluated.value.distribution.boundary is boundary


def test_baseline_recalibration_accepts_only_certified_evidence() -> None:
    certified = _evaluate(_distribution())
    degraded = _evaluate(_distribution(p50=20, p95=35, p99=45, maximum=48))
    assert isinstance(certified, result.Success)
    assert isinstance(degraded, result.Success)

    recalibrated = latency.recalibrate_hosting_latency_baseline(
        certified.value,
        certified_at=_NOW + timedelta(seconds=2),
        evidence_ref=lab.HostingReliabilityEvidenceReference(_uuid(50)),
    )
    assert isinstance(recalibrated, result.Success)
    assert recalibrated.value.reference_p99 == certified.value.distribution.p99

    rejected = latency.recalibrate_hosting_latency_baseline(
        degraded.value,
        certified_at=_NOW + timedelta(seconds=2),
        evidence_ref=lab.HostingReliabilityEvidenceReference(_uuid(51)),
    )
    assert isinstance(rejected, result.Failure)
    assert isinstance(rejected.error, latency.HostingLatencySafetyAuthorizationError)


def test_latency_envelope_exposes_no_trading_or_server_switch_authority() -> None:
    states = {state.value for state in latency.HostingLatencyEnvelopeState}
    assert states == {"certified", "warning", "degraded", "emergency"}
    assert "failover" not in states
    assert "recovery" not in states

    prohibited = {
        "buy",
        "sell",
        "submit_order",
        "retry_order",
        "redispatch",
        "switch_server",
        "failover",
        "acquire_lease",
        "revoke_lease",
        "core_decision",
    }
    for surface in (
        latency.HostingLatencyDistribution,
        latency.HostingLatencyBaseline,
        latency.HostingLatencyEnvelopePolicy,
        latency.HostingLatencyEnvelopeAssessment,
    ):
        assert prohibited.isdisjoint(set(dir(surface)))
