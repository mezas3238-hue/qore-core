from __future__ import annotations

from datetime import date
from decimal import Decimal

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_r_milestone_protection_2r_v1 as milestone,
)
from qore.infrastructure.trader_lab import (
    capitalizer_scalper_utc001_consumed_audit_v1 as audit,
)
from qore.infrastructure.trader_lab import (
    universal_trader_certification_standard_001 as utc,
)


def _trade(
    index: int,
    *,
    operating_date: str,
    realized_r: str,
) -> milestone.SimulatedTrade:
    hour = 10 + (index % 5)
    entry_at = f"{operating_date}T{hour:02d}:00:00+00:00"
    exit_at = f"{operating_date}T{hour:02d}:30:00+00:00"
    return milestone.SimulatedTrade(
        symbol=f"S{index:03d}",
        session="NEW_YORK",
        operating_date=operating_date,
        side="LONG",
        entry_at=entry_at,
        exit_at=exit_at,
        entry_price="100",
        original_stop_price="99",
        final_stop_price="99",
        target_price="102",
        realized_gross_r=realized_r,
        exit_reason="TARGET" if Decimal(realized_r) > 0 else "STOP",
        mode="ORIGINAL",
        protection_updates=0,
        first_protection_at=None,
        max_milestone_r_seen_before_exit="0",
        same_minute_stop_target_ambiguity=False,
    )


def _rows() -> tuple[milestone.SimulatedTrade, ...]:
    rows: list[milestone.SimulatedTrade] = []
    for index in range(30):
        rows.append(
            _trade(
                index,
                operating_date=f"2022-10-{(index % 20) + 1:02d}",
                realized_r="2" if index % 2 == 0 else "-1",
            )
        )
    for index in range(30, 60):
        rows.append(
            _trade(
                index,
                operating_date=f"2023-10-{(index % 20) + 1:02d}",
                realized_r="2" if index % 2 == 0 else "-1",
            )
        )
    return tuple(rows)


def test_split_exam_years_uses_anniversary_boundaries() -> None:
    split = audit._split_exam_years(
        _rows(),
        window_start=date(2022, 9, 17),
        window_end_exclusive=date(2024, 9, 17),
    )

    assert len(split) == 2
    assert split[0][0] == date(2022, 9, 17)
    assert split[0][1] == date(2023, 9, 17)
    assert split[1][0] == date(2023, 9, 17)
    assert split[1][1] == date(2024, 9, 17)
    assert len(split[0][2]) == 30
    assert len(split[1][2]) == 30


def test_consumed_audit_has_no_fresh_certification_authority() -> None:
    report = audit.build_report(
        _rows(),
        population_role="CONSUMED_VALIDATION_2022_2024",
        window_start=date(2022, 9, 17),
        window_end_exclusive=date(2024, 9, 17),
        development_only=False,
        consumed_for_engineering=True,
    )

    assert report.fresh_certification_authority is False
    assert report.global_metrics_have_certification_authority is False
    assert report.temporal_compensation_allowed is False
    assert report.cost_certification_blocked is True
    assert report.trader_certified is False
    assert len(report.exam_years) == 2
    for year in report.exam_years:
        assert year.utc_evidence.certification_required is True
        assert year.utc_evidence.consumed_for_engineering is True
        assert year.utc_evidence.cost_certification_blocked is True
        missing = {
            gate.gate
            for gate in year.utc_gate_statuses
            if gate.status is utc.GateStatus.MISSING
        }
        assert "post_cost_profit_factor" in missing
        assert "loss_cluster_gate" in missing
        assert "sample_sufficiency" in missing


def test_development_years_have_zero_certification_authority() -> None:
    report = audit.build_report(
        _rows(),
        population_role="DEVELOPMENT_2022_2024",
        window_start=date(2022, 9, 17),
        window_end_exclusive=date(2024, 9, 17),
        development_only=True,
        consumed_for_engineering=True,
    )

    for year in report.exam_years:
        assert year.utc_evidence.certification_required is False
        assert year.utc_evidence.development_only is True
        assert len(year.utc_gate_statuses) == 1
        assert year.utc_gate_statuses[0].status is utc.GateStatus.NOT_APPLICABLE


def test_split_rejects_non_two_year_window() -> None:
    try:
        audit._split_exam_years(
            _rows(),
            window_start=date(2022, 9, 17),
            window_end_exclusive=date(2023, 9, 17),
        )
    except ValueError as exc:
        assert "exact two-year" in str(exc)
    else:
        raise AssertionError("expected exact-two-year failure")
