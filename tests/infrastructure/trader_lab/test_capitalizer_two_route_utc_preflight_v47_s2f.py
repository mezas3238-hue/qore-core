from __future__ import annotations

from decimal import Decimal

import pytest

from qore.infrastructure.trader_lab import (
    capitalizer_two_route_gross_economics_v47_s2e as s2e,
)
from qore.infrastructure.trader_lab import (
    capitalizer_two_route_utc_preflight_v47_s2f as s2f,
)


def _trade(value: str = "1") -> s2e.S2EGrossTrade:
    return s2e.S2EGrossTrade(
        identity=s2e.IDENTITY,
        source_population_identity=(
            "QORE_CAPITALIZER_V47_S2D_TWO_ROUTE_POPULATION_FREEZE"
        ),
        source_stream="FTM",
        period="validation",
        symbol="EURUSD",
        session="LONDON",
        operating_date="2023-01-05",
        side="LONG",
        route="FAILURE_TO_MANIPULATE_CONTINUATION",
        entry_at="2023-01-05T08:00:00+00:00",
        entry_price="100",
        stop_price="99",
        target_price="103",
        initial_risk_price="1",
        target_r="3",
        exit_at="2023-01-05T09:00:00+00:00",
        exit_price="101",
        exit_reason="SESSION_EXIT",
        realized_gross_r=value,
        m1_bars_held=60,
        exact_exit_ticks_required=False,
        stop_first_fallback_used=False,
    )


def test_adapter_never_invents_protection() -> None:
    row = s2f._adapt(_trade())
    assert row.original_stop_price == "99"
    assert row.final_stop_price == "99"
    assert row.protection_updates == 0
    assert row.first_protection_at is None
    assert row.mode == "FAILURE_TO_MANIPULATE_CONTINUATION"


def test_cost_adjustment_changes_only_realized_r() -> None:
    source = s2f._adapt(_trade("1.25"))
    adjusted = s2f._cost_adjusted((source,), Decimal("0.25"))
    assert adjusted[0].realized_gross_r == "1.00"
    assert adjusted[0].entry_at == source.entry_at
    assert adjusted[0].target_price == source.target_price


def test_prefresh_report_requires_bound_cost_pair() -> None:
    with pytest.raises(ValueError, match="cost evidence/value binding mismatch"):
        s2f.build_report(
            (_trade(),),
            provider_cost_evidence_bound=False,
            additional_cost_r_per_trade=Decimal("0.1"),
        )


def test_s2f_cannot_claim_fresh_holdout_or_certification() -> None:
    with pytest.raises(ValueError, match="cannot open/certify"):
        s2f.S2FReport(
            identity=s2f.IDENTITY,
            source_population_rows=1,
            provider_cost_evidence_bound=False,
            additional_cost_r_per_trade=None,
            periods=(),
            all_consumed_oos_prefresh_gates_passed=False,
            candidate_head_can_be_frozen_for_fresh_holdout=False,
            fresh_holdout_opened=True,
        )
