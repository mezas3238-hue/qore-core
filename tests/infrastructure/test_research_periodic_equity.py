from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

from qore.infrastructure.proprietary_accounts import CurrencyCode, MoneyAmount
from qore.infrastructure.research_periodic_equity import (
    ResearchEquityEvidenceReference,
    ResearchEquityFlowStatus,
    ResearchEquityObservationId,
    ResearchEquityValuationBasis,
    ResearchEquityValuationObservation,
    ResearchPeriodicEquityPolicy,
    ResearchPeriodicEquityValidationError,
    ResearchValuationModelBinding,
    ResearchValuationModelId,
    build_research_periodic_equity_return_series,
)
from qore.infrastructure.research_run import ResearchRunEvidence
from qore.kernel.result import Failure, Success

_SIMULATED = datetime(2026, 1, 5, 12, 0, tzinfo=UTC)
_PROCESS = datetime(2026, 8, 9, 12, 0, tzinfo=UTC)
_USD = CurrencyCode("USD")


def _uuid(suffix: int) -> UUID:
    return UUID(f"78000000-0000-0000-0000-{suffix:012d}")


def _money(value: str) -> MoneyAmount:
    return MoneyAmount(currency=_USD, amount=Decimal(value))


def _run(*, with_cost_model: bool = True, hours: int = 2) -> ResearchRunEvidence:
    run = object.__new__(ResearchRunEvidence)
    object.__setattr__(run, "run_id", "research-run-test")
    object.__setattr__(run, "created_at", _PROCESS - timedelta(minutes=2))
    object.__setattr__(run, "datasets", ())
    object.__setattr__(run, "replay_policy_version", "point-in-time-v1")
    object.__setattr__(run, "simulated_start", _SIMULATED)
    object.__setattr__(run, "simulated_end", _SIMULATED + timedelta(hours=hours))
    object.__setattr__(run, "strategy_configuration_id", "strategy-test")
    object.__setattr__(run, "software_revision", "a9b9e786")
    object.__setattr__(run, "execution_model_id", None)
    object.__setattr__(
        run,
        "transaction_cost_model_id",
        "cost-model-test" if with_cost_model else None,
    )
    object.__setattr__(run, "randomness_mode", "deterministic")
    object.__setattr__(run, "random_seed", None)
    object.__setattr__(run, "input_fingerprint", "fixture-fingerprint")
    return run


def _binding(
    *,
    basis: ResearchEquityValuationBasis = ResearchEquityValuationBasis.NET,
    with_cost_model: bool = True,
) -> ResearchValuationModelBinding:
    return ResearchValuationModelBinding(
        run=_run(with_cost_model=with_cost_model),
        model_id=ResearchValuationModelId(_uuid(1)),
        model_version="valuation-v1",
        basis=basis,
        bound_at=_PROCESS - timedelta(minutes=1),
        evidence_ref=ResearchEquityEvidenceReference(_uuid(2)),
    )


def _observation(
    binding: ResearchValuationModelBinding,
    *,
    suffix: int,
    hours: int,
    equity: str,
    flow_status: ResearchEquityFlowStatus,
) -> ResearchEquityValuationObservation:
    return ResearchEquityValuationObservation(
        observation_id=ResearchEquityObservationId(_uuid(100 + suffix)),
        binding=binding,
        valued_at=_SIMULATED + timedelta(hours=hours),
        equity=_money(equity),
        flow_status_since_prior=flow_status,
        recorded_at=_PROCESS + timedelta(seconds=suffix),
        evidence_ref=ResearchEquityEvidenceReference(_uuid(200 + suffix)),
    )


def test_fixed_period_series_derives_returns_from_explicit_equity_evidence() -> None:
    binding = _binding()
    observations = (
        _observation(
            binding,
            suffix=1,
            hours=0,
            equity="1000",
            flow_status=ResearchEquityFlowStatus.BASELINE,
        ),
        _observation(
            binding,
            suffix=2,
            hours=1,
            equity="1100",
            flow_status=ResearchEquityFlowStatus.NO_EXTERNAL_FLOW,
        ),
        _observation(
            binding,
            suffix=3,
            hours=2,
            equity="990",
            flow_status=ResearchEquityFlowStatus.NO_EXTERNAL_FLOW,
        ),
    )
    built = build_research_periodic_equity_return_series(
        binding=binding,
        policy=ResearchPeriodicEquityPolicy(interval_seconds=3_600),
        observations=tuple(reversed(observations)),
    )

    assert isinstance(built, Success)
    series = built.value
    assert series.observations == observations
    assert series.period_count == 2
    assert series.returns[0].return_rate == Decimal("0.1")
    assert series.returns[1].return_rate == Decimal("-0.1")


def test_net_valuation_requires_transaction_cost_model_bound_to_run() -> None:
    with pytest.raises(ResearchPeriodicEquityValidationError):
        _binding(
            basis=ResearchEquityValuationBasis.NET,
            with_cost_model=False,
        )

    gross = _binding(
        basis=ResearchEquityValuationBasis.GROSS,
        with_cost_model=False,
    )
    assert gross.basis is ResearchEquityValuationBasis.GROSS


def test_periodic_series_rejects_missing_or_irregular_schedule_points() -> None:
    binding = _binding()
    baseline = _observation(
        binding,
        suffix=10,
        hours=0,
        equity="1000",
        flow_status=ResearchEquityFlowStatus.BASELINE,
    )
    terminal = _observation(
        binding,
        suffix=11,
        hours=2,
        equity="1050",
        flow_status=ResearchEquityFlowStatus.NO_EXTERNAL_FLOW,
    )

    built = build_research_periodic_equity_return_series(
        binding=binding,
        policy=ResearchPeriodicEquityPolicy(interval_seconds=3_600),
        observations=(baseline, terminal),
    )

    assert isinstance(built, Failure)
    assert "exact fixed schedule" in str(built.error)


def test_periodic_returns_fail_closed_on_external_or_unknown_cash_flows() -> None:
    for status in (
        ResearchEquityFlowStatus.EXTERNAL_FLOW_PRESENT,
        ResearchEquityFlowStatus.UNKNOWN,
    ):
        binding = _binding()
        observations = (
            _observation(
                binding,
                suffix=20,
                hours=0,
                equity="1000",
                flow_status=ResearchEquityFlowStatus.BASELINE,
            ),
            _observation(
                binding,
                suffix=21,
                hours=1,
                equity="1100",
                flow_status=status,
            ),
            _observation(
                binding,
                suffix=22,
                hours=2,
                equity="1200",
                flow_status=ResearchEquityFlowStatus.NO_EXTERNAL_FLOW,
            ),
        )
        built = build_research_periodic_equity_return_series(
            binding=binding,
            policy=ResearchPeriodicEquityPolicy(interval_seconds=3_600),
            observations=observations,
        )
        assert isinstance(built, Failure)
        assert "explicit NO_EXTERNAL_FLOW" in str(built.error)


def test_process_evidence_time_is_separate_from_simulated_valuation_time() -> None:
    binding = _binding()
    observation = _observation(
        binding,
        suffix=30,
        hours=0,
        equity="1000",
        flow_status=ResearchEquityFlowStatus.BASELINE,
    )

    assert observation.valued_at < binding.bound_at
    assert observation.recorded_at >= binding.bound_at


def test_return_point_rejects_metric_tampering() -> None:
    binding = _binding()
    observations = (
        _observation(
            binding,
            suffix=40,
            hours=0,
            equity="1000",
            flow_status=ResearchEquityFlowStatus.BASELINE,
        ),
        _observation(
            binding,
            suffix=41,
            hours=1,
            equity="1100",
            flow_status=ResearchEquityFlowStatus.NO_EXTERNAL_FLOW,
        ),
        _observation(
            binding,
            suffix=42,
            hours=2,
            equity="1210",
            flow_status=ResearchEquityFlowStatus.NO_EXTERNAL_FLOW,
        ),
    )
    built = build_research_periodic_equity_return_series(
        binding=binding,
        policy=ResearchPeriodicEquityPolicy(interval_seconds=3_600),
        observations=observations,
    )
    assert isinstance(built, Success)

    with pytest.raises(ResearchPeriodicEquityValidationError):
        replace(built.value.returns[0], return_rate=Decimal("999"))


def test_periodic_equity_boundary_makes_no_valuation_or_sharpe_claims() -> None:
    binding = _binding()
    observations = (
        _observation(
            binding,
            suffix=50,
            hours=0,
            equity="1000",
            flow_status=ResearchEquityFlowStatus.BASELINE,
        ),
        _observation(
            binding,
            suffix=51,
            hours=1,
            equity="1000",
            flow_status=ResearchEquityFlowStatus.NO_EXTERNAL_FLOW,
        ),
        _observation(
            binding,
            suffix=52,
            hours=2,
            equity="1000",
            flow_status=ResearchEquityFlowStatus.NO_EXTERNAL_FLOW,
        ),
    )
    built = build_research_periodic_equity_return_series(
        binding=binding,
        policy=ResearchPeriodicEquityPolicy(interval_seconds=3_600),
        observations=observations,
    )
    assert isinstance(built, Success)
    series = built.value

    assert not hasattr(series, "mark_to_market")
    assert not hasattr(series, "sharpe_ratio")
    assert not hasattr(series, "sortino_ratio")
    assert not hasattr(series, "statistically_significant")
    assert not hasattr(series, "production_ready")
