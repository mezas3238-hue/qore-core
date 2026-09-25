from __future__ import annotations

import json
import random
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import cast
from uuid import UUID

import pytest

from qore.infrastructure.market_data import (
    Instrument,
    MarketDataSnapshotId,
    OhlcSnapshot,
    Timeframe,
)
from qore.infrastructure.ports import AdapterId, ExternalSourceDescriptor, PortName, SourceId
from qore.infrastructure.trader_lab.first_cohort_backtest import (
    FirstCohortBacktestError,
    FirstCohortBacktestTrade,
    _h4_context,
    _history,
    _load,
)
from qore.infrastructure.trader_lab.first_cohort_characterization import (
    FirstCohortCharacterizationError,
    _Bucket,
    _trend_regime,
    _volatility_regime,
    run_characterization,
)
from qore.infrastructure.trader_lab.first_cohort_characterization_aggregate import (
    run_characterization_aggregate,
)
from qore.infrastructure.trader_lab.first_cohort_failure_analysis import (
    FirstCohortFailureAnalysisError,
)
from qore.infrastructure.trader_lab.first_cohort_hypothesis_register import (
    run_hypothesis_register,
)
from qore.infrastructure.trader_lab.first_cohort_walk_forward import (
    ConfigurationAssessment,
    SegmentMetrics,
    _fingerprint,
    _grids,
    _parameters,
    _rank,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide

_CODES = ("vt-01", "vt-08", "vt-09", "vt-17", "vt-31")
_SYMBOLS = ("AUDUSD", "EURUSD", "GBPUSD", "USDCAD", "USDJPY", "XAUUSD")
_SOURCE = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("79000000-0000-0000-0000-000000000001")),
    source_id=SourceId(UUID("79000000-0000-0000-0000-000000000002")),
    port_name=PortName("market-data.characterization-test"),
)


def _bar(index: int, close: float, *, spread: float = 0.001) -> OhlcSnapshot:
    opened_at = datetime(2026, 1, 1, tzinfo=UTC) + timedelta(hours=4 * index)
    return OhlcSnapshot(
        snapshot_id=MarketDataSnapshotId(
            UUID(f"79000000-0000-0000-0001-{index + 1:012d}")
        ),
        instrument=Instrument("EURUSD"),
        source=_SOURCE,
        timeframe=Timeframe(14_400),
        opened_at=opened_at,
        closed_at=opened_at + timedelta(hours=4),
        open=close,
        high=close + spread,
        low=close - spread,
        close=close,
    )


def _trade(rate: str = "0.01", *, reason: str = "target") -> FirstCohortBacktestTrade:
    signal_at = datetime(2026, 1, 1, tzinfo=UTC)
    return FirstCohortBacktestTrade(
        trader_code="vt-01",
        signal_at=signal_at,
        filled_at=signal_at + timedelta(minutes=5),
        exited_at=signal_at + timedelta(minutes=10),
        side=DemoTradingSetupSide.LONG,
        entry_price=Decimal("1"),
        stop_loss=Decimal("0.99"),
        take_profit=Decimal("1.02"),
        exit_price=Decimal("1.01"),
        return_rate=Decimal(rate),
        exit_reason=reason,
    )


def _outcomes(mean: str = "0.001", *, count: int = 10) -> dict[str, object]:
    return {
        "count": count,
        "mean": mean,
        "minimum": mean,
        "maximum": mean,
        "population_variance": "0",
        "win_rate": "1" if Decimal(mean) > 0 else "0",
    }


def _bucket(mean: str = "0.001") -> dict[str, object]:
    return {
        "setup_count": 10,
        "filled_count": 10,
        "unfilled_count": 0,
        "fill_rate": "1",
        "outcomes": _outcomes(mean),
        "exit_reason_counts": {"target": 10},
        "close_path_mfe_fraction": _outcomes("0.002"),
        "close_path_mae_fraction": _outcomes("0.001"),
    }


def _profile(code: str) -> dict[str, object]:
    fingerprint = f"{_CODES.index(code) + 1:064x}"
    category = {"normal": _bucket()}
    parameter_name = {
        "vt-01": "sweep_strength",
        "vt-08": "range_length",
        "vt-09": "swing_strength",
        "vt-31": "sweep_strength",
    }.get(code)
    return {
        "profile": "production-default",
        "selected_by_in_sample_only": True,
        "config_fingerprint": fingerprint,
        "parameters": {} if parameter_name is None else {parameter_name: 2},
        "methodology_identity": {
            "trader_version": "v1",
            "methodology_id": code,
            "methodology_version": "v1",
            "methodology_fingerprint": f"{_CODES.index(code) + 11:064x}",
            "timeframe": "M5",
            "session": "continuous",
        },
        "setup_count": 10,
        "filled_setup_count": 10,
        "fill_rate": "1",
        "outcomes": _outcomes(),
        "abstain_reason_counts": {"no-sweep": 90},
        "side_counts": {"long": 10},
        "exit_reason_counts": {"target": 10},
        "setup_reason_counts": {"canonical": 10},
        "by_trend_regime": category,
        "by_volatility_regime": category,
        "by_signal_hour_utc": {"10": _bucket()},
        "by_signal_weekday_utc": {"1": _bucket()},
        "by_chronological_quartile": {"q1": _bucket()},
        "by_calendar_month": {"01": _bucket()},
        "by_calendar_year": {"2026": _bucket()},
        "by_session": {"continuous": _bucket()},
        "by_side": {"long": _bucket()},
    }


def _write_characterizations(tmp_path: Path) -> tuple[Path, ...]:
    paths: list[Path] = []
    for symbol in _SYMBOLS:
        payload = {
            "schema": "qore.trader_lab.first_cohort_characterization.v1",
            "environment": "demo",
            "read_only": True,
            "symbol": symbol,
            "account_fingerprint": "a" * 64,
            "software_sha": "b" * 40,
            "results": [
                {"trader_code": code, "profiles": [_profile(code)]} for code in _CODES
            ],
        }
        path = tmp_path / f"{symbol}-characterization.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        paths.append(path)
    return tuple(paths)


def _market_bar(opened_at: datetime, *, minutes: int) -> dict[str, object]:
    return {
        "opened_at": opened_at.isoformat(),
        "closed_at": (opened_at + timedelta(minutes=minutes)).isoformat(),
        "open": "1.1000",
        "high": "1.1010",
        "low": "1.0990",
        "close": "1.1005",
    }


def _write_market(tmp_path: Path, *, duplicate_m5: bool = False) -> Path:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    recent = start + timedelta(days=731)
    m5 = [
        _market_bar(start, minutes=5),
        *[
            _market_bar(recent + timedelta(minutes=5 * index), minutes=5)
            for index in range(3)
        ],
    ]
    if duplicate_m5:
        m5.append(dict(m5[-1]))
    periods: dict[str, list[dict[str, object]]] = {
        "M1": [],
        "M5": m5,
        "M15": [
            _market_bar(start, minutes=15),
            *[
                _market_bar(recent + timedelta(minutes=15 * index), minutes=15)
                for index in range(3)
            ],
        ],
        "H4": [
            _market_bar(start, minutes=240),
            _market_bar(recent, minutes=240),
        ],
    }
    payload = {
        "environment": "demo",
        "read_only": True,
        "account_is_live": False,
        "trading_permission_verified": True,
        "account_fingerprint": "a" * 64,
        "symbol": {"symbol_name": "EURUSD"},
        "checked_at": (recent + timedelta(hours=5)).isoformat(),
        "software_sha": "b" * 40,
        "required_coverage_days": 730,
        "requested_lookback_days": 760,
        "periods": periods,
    }
    payload["coverage"] = {
        period: {
            "bar_count": len(periods[period]),
            "first_opened_at": periods[period][0]["opened_at"],
            "last_closed_at": periods[period][-1]["closed_at"],
            "span_seconds": int(
                (
                    datetime.fromisoformat(
                        cast(str, periods[period][-1]["closed_at"])
                    )
                    - datetime.fromisoformat(
                        cast(str, periods[period][0]["opened_at"])
                    )
                ).total_seconds()
            ),
        }
        for period in ("M5", "M15", "H4")
    }
    path = tmp_path / "market.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _write_walk_forward(tmp_path: Path) -> Path:
    metrics = {
        "sample_size": 0,
        "mean_return": "0",
        "win_rate": "0",
        "population_variance": "0",
    }
    results: list[dict[str, object]] = []
    for code, grid in _grids().items():
        assessments = [
            {
                "parameters": dict(_parameters(evaluator)),
                "config_fingerprint": _fingerprint(evaluator),
                "in_sample": metrics,
                "in_sample_pass": False,
                "oos": metrics,
                "oos_pass": False,
                "stressed_oos": metrics,
                "stress_pass": False,
            }
            for evaluator in grid
        ]
        results.append(
            {
                "trader_code": code,
                "assessed_configurations": len(assessments),
                "selected": None,
                "assessments": assessments,
            }
        )
    payload = {
        "schema": "qore.trader_lab.first_cohort_walk_forward.v2",
        "environment": "demo",
        "read_only": True,
        "account_fingerprint": "a" * 64,
        "software_sha": "b" * 40,
        "symbol": "EURUSD",
        "results": results,
    }
    path = tmp_path / "walk.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_past_only_regime_descriptors_distinguish_trend_and_volatility() -> None:
    trend = tuple(_bar(index, 1.0 + index * 0.001) for index in range(60))
    assert _trend_regime(trend) == "trend"

    normal_then_high = tuple(
        _bar(index, 1.0, spread=0.0001 if index < 40 else 0.001)
        for index in range(50)
    )
    assert _volatility_regime(normal_then_high) == "high"
    future = _bar(50, 10.0, spread=1.0)
    assert _volatility_regime(normal_then_high) == _volatility_regime(
        (*normal_then_high, future)[:-1]
    )


def test_h4_binary_lookup_is_exactly_equivalent_to_prior_linear_policy() -> None:
    h4 = tuple(_bar(index, 1.0 + index * 0.001) for index in range(70))
    probes = (
        h4[0].opened_at,
        h4[0].closed_at,
        h4[31].closed_at + timedelta(seconds=1),
        h4[-1].closed_at + timedelta(days=1),
    )
    for as_of in probes:
        indices = [index for index, bar in enumerate(h4) if bar.closed_at <= as_of]
        expected = () if not indices else _history(h4, indices[-1], limit=32)
        assert _h4_context(h4, as_of=as_of) == expected


def _linear_h4_reference(
    h4: tuple[OhlcSnapshot, ...], *, as_of: datetime
) -> tuple[OhlcSnapshot, ...]:
    indices = [index for index, bar in enumerate(h4) if bar.closed_at <= as_of]
    return () if not indices else _history(h4, indices[-1], limit=32)


def test_h4_equivalence_covers_empty_boundaries_future_and_large_history() -> None:
    assert _h4_context((), as_of=datetime(2026, 1, 1, tzinfo=UTC)) == ()
    h4 = tuple(_bar(index, 1.0 + index * 0.00001) for index in range(10_000))
    probes = (
        h4[0].opened_at,
        h4[0].closed_at - timedelta(microseconds=1),
        h4[0].closed_at,
        h4[0].closed_at + timedelta(microseconds=1),
        h4[-1].closed_at - timedelta(microseconds=1),
        h4[-1].closed_at,
        h4[-1].closed_at + timedelta(days=30),
    )
    for as_of in probes:
        assert _h4_context(h4, as_of=as_of) == _linear_h4_reference(
            h4, as_of=as_of
        )


def test_h4_equivalence_preserves_gaps_irregular_spacing_and_contiguous_tail() -> None:
    indices = (0, 1, 2, 8, 9, 21, 22, 23, 24, 80, 81)
    h4 = tuple(_bar(index, 1.0 + index * 0.001) for index in indices)
    probes = tuple(
        moment
        for bar in h4
        for moment in (
            bar.closed_at - timedelta(microseconds=1),
            bar.closed_at,
            bar.closed_at + timedelta(microseconds=1),
        )
    )
    for as_of in probes:
        assert _h4_context(h4, as_of=as_of) == _linear_h4_reference(
            h4, as_of=as_of
        )
    assert _h4_context(h4, as_of=h4[9].closed_at) == h4[9:10]
    assert _h4_context(h4, as_of=h4[8].closed_at) == h4[5:9]


def test_h4_randomized_metamorphic_equivalence_and_future_exclusion() -> None:
    generator = random.Random(0x48434F4E54455854)
    for _case in range(250):
        indices = sorted(generator.sample(range(2_000), generator.randint(1, 160)))
        h4 = tuple(_bar(index, 1.0 + index * 0.00001) for index in indices)
        as_of = datetime(2026, 1, 1, tzinfo=UTC) + timedelta(
            seconds=generator.randint(-1, 2_000 * 14_400 + 14_400)
        )
        optimized = _h4_context(h4, as_of=as_of)
        assert optimized == _linear_h4_reference(h4, as_of=as_of)
        assert all(bar.closed_at <= as_of for bar in optimized)

        future = _bar(2_001 + _case, 2.0)
        extended = tuple(sorted((*h4, future), key=lambda bar: bar.closed_at))
        if future.closed_at > as_of:
            assert _h4_context(extended, as_of=as_of) == optimized


def test_auxiliary_m1_can_be_empty_but_duplicate_consumed_evidence_is_rejected(
    tmp_path: Path,
) -> None:
    series, _fingerprint_value, _symbol, _checked_at, _software_sha = _load(
        _write_market(tmp_path)
    )
    assert series["M1"] == ()

    with pytest.raises(FirstCohortBacktestError, match="duplicate bars"):
        _load(_write_market(tmp_path, duplicate_m5=True))


def test_market_loader_requires_declared_and_actual_730_day_coverage(
    tmp_path: Path,
) -> None:
    path = _write_market(tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["coverage"]["M5"]["span_seconds"] -= 1
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(FirstCohortBacktestError, match="coverage span mismatch"):
        _load(path)

    path = _write_market(tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["required_coverage_days"] = 729
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(FirstCohortBacktestError, match="at least 730"):
        _load(path)


def test_characterization_preserves_full_grid_and_decision_funnel(tmp_path: Path) -> None:
    payload = run_characterization(
        _write_market(tmp_path),
        _write_walk_forward(tmp_path),
    )

    for row_value, grid in zip(
        cast(list[object], payload["results"]), _grids().values(), strict=True
    ):
        row = cast(dict[str, object], row_value)
        profiles = cast(list[dict[str, object]], row["profiles"])
        assert len(profiles) == len(grid)
        assert [item["config_fingerprint"] for item in profiles] == [
            _fingerprint(item) for item in grid
        ]
        funnel = cast(dict[str, object], profiles[0]["decision_funnel"])
        assert funnel["decision_opportunities"] == 3
        assert cast(int, funnel["setup"]) + cast(int, funnel["abstain"]) <= 3


def test_bucket_records_fill_exit_excursion_and_outcome_metrics() -> None:
    bucket = _Bucket()
    bucket.record(None)
    bucket.record(_trade(), mfe=Decimal("0.02"), mae=Decimal("0.005"))

    payload = bucket.payload()

    assert payload["setup_count"] == 2
    assert payload["filled_count"] == 1
    assert payload["unfilled_count"] == 1
    assert payload["fill_rate"] == "0.5"
    assert payload["exit_reason_counts"] == {"target": 1}
    assert cast(dict[str, object], payload["outcomes"])["mean"] == "0.01"


def test_walk_forward_ranking_cannot_read_oos_or_stress_metrics() -> None:
    weak_oos = SegmentMetrics(10, Decimal("-1"), Decimal("0"), Decimal("9"))
    strong_oos = SegmentMetrics(10, Decimal("1"), Decimal("1"), Decimal("0"))
    in_sample = SegmentMetrics(10, Decimal("0.01"), Decimal("0.6"), Decimal("0.001"))
    left = ConfigurationAssessment(
        parameters=(("sweep_strength", 1),),
        config_fingerprint="same",
        in_sample=in_sample,
        in_sample_pass=True,
        oos=weak_oos,
        oos_pass=False,
        stressed_oos=weak_oos,
        stress_pass=False,
    )
    right = ConfigurationAssessment(
        parameters=(("sweep_strength", 2),),
        config_fingerprint="same",
        in_sample=in_sample,
        in_sample_pass=True,
        oos=strong_oos,
        oos_pass=True,
        stressed_oos=strong_oos,
        stress_pass=True,
    )

    assert _rank(left) == _rank(right)


def test_characterization_aggregate_preserves_config_identity_and_six_markets(
    tmp_path: Path,
) -> None:
    paths = _write_characterizations(tmp_path)
    payload = run_characterization_aggregate(paths)

    assert payload["symbols"] == list(_SYMBOLS)
    first = cast(dict[str, object], cast(list[object], payload["results"])[0])
    profile = cast(dict[str, object], cast(list[object], first["profiles"])[0])
    assert profile["instrument_count"] == 6
    assert profile["positive_expectancy_instrument_count"] == 6
    assert "robust" in cast(list[str], profile["classification_labels"])
    assert json.dumps(payload, sort_keys=True) == json.dumps(
        run_characterization_aggregate(tuple(reversed(paths))), sort_keys=True
    )


def test_characterization_aggregate_rejects_duplicate_instrument(tmp_path: Path) -> None:
    paths = _write_characterizations(tmp_path)
    with pytest.raises(FirstCohortCharacterizationError, match="distinct symbols"):
        run_characterization_aggregate((*paths[:-1], paths[0]))


def test_hypothesis_register_marks_holdout_consumed_and_binds_software_sha(
    tmp_path: Path,
) -> None:
    characterization = run_characterization_aggregate(
        _write_characterizations(tmp_path)
    )
    characterization_path = tmp_path / "characterization-aggregate.json"
    characterization_path.write_text(json.dumps(characterization), encoding="utf-8")
    failure = {
        "schema": "qore.trader_lab.first_cohort_failure_analysis_aggregate.v1",
        "account_fingerprint": "a" * 64,
        "software_sha": "b" * 40,
        "symbols": list(_SYMBOLS),
        "results": [
            {
                "trader_code": code,
                "diagnostic_signal_counts": {"oos_collapse": 6},
            }
            for code in _CODES
        ],
    }
    multi = {
        "schema": "qore.trader_lab.first_cohort_multi_pair_walk_forward.v1",
        "account_fingerprint": "a" * 64,
        "software_sha": "b" * 40,
        "results": [{"trader_code": code} for code in _CODES],
    }
    failure_path = tmp_path / "failure.json"
    multi_path = tmp_path / "multi.json"
    failure_path.write_text(json.dumps(failure), encoding="utf-8")
    multi_path.write_text(json.dumps(multi), encoding="utf-8")

    payload = run_hypothesis_register(
        failure_path,
        characterization_path,
        multi_path,
        software_sha="b" * 40,
    )

    assert payload["software_sha"] == "b" * 40
    governance = cast(dict[str, object], payload["holdout_governance"])
    assert governance["current_oos_state"] == "consumed_for_research"
    hypotheses = cast(list[dict[str, object]], payload["hypotheses"])
    assert hypotheses[0]["required_fresh_holdout"] is True
    assert hypotheses[0]["confidence"] == "high"
    assert hypotheses[0]["software_sha"] == "b" * 40
    assert "previously unseen" in cast(str, hypotheses[0]["new_evidence_required"])
    assert cast(dict[str, object], hypotheses[0]["origin_configuration"])[
        "config_fingerprint"
    ]

    with pytest.raises(FirstCohortFailureAnalysisError, match="software_sha"):
        run_hypothesis_register(
            failure_path,
            characterization_path,
            multi_path,
            software_sha="not-a-sha",
        )
