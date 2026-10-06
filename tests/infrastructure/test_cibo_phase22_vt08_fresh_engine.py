from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.cibo_phase22_vt08_fresh_engine import (
    Phase22VolumeFreeOpportunity,
    resample_m5_to_m15,
)
from qore.infrastructure.trader_lab.ict_turtle_soup_r4_source_exact import (
    Bar,
    Evidence,
)


def _bar(opened_at: datetime, value: str) -> Bar:
    price = Decimal(value)
    return Bar(
        opened_at=opened_at,
        closed_at=opened_at + timedelta(minutes=5),
        open=price,
        high=price + Decimal("0.0002"),
        low=price - Decimal("0.0002"),
        close=price + Decimal("0.0001"),
    )


def test_m5_to_m15_uses_exact_three_bar_utc_bins_only() -> None:
    start = datetime(2015, 10, 19, 0, 0, tzinfo=UTC)
    bars = (
        _bar(start, "1.1000"),
        _bar(start + timedelta(minutes=5), "1.1001"),
        _bar(start + timedelta(minutes=10), "1.1002"),
        _bar(start + timedelta(minutes=15), "1.1003"),
        _bar(start + timedelta(minutes=25), "1.1004"),
    )
    evidence = Evidence(symbol="EURUSD", digits=5, bars=bars)

    m15, receipt = resample_m5_to_m15(evidence)

    assert len(m15) == 1
    assert receipt.source_m5_bars == 5
    assert receipt.emitted_m15_bars == 1
    assert receipt.incomplete_m15_bins == 1
    assert m15[0].opened_at == start
    assert m15[0].closed_at == start + timedelta(minutes=15)
    assert m15[0].open == Decimal("1.1000")
    assert m15[0].close == Decimal("1.1003")
    assert receipt.fingerprint().startswith("sha256:")


def test_volume_free_opportunity_rejects_quantity_semantics() -> None:
    opportunity = Phase22VolumeFreeOpportunity(
        trader_id="VT08_FOREX",
        symbol="EURUSD",
        signal_fingerprint="sha256:" + "1" * 64,
        signal_at="2015-10-19T10:00:00+00:00",
        entry_at="2015-10-19T10:00:00+00:00",
        exit_at="2015-10-19T14:00:00+00:00",
        side="long",
        entry="1.10",
        stop="1.09",
        target="1.12",
        exit_price="1.12",
        exit_reason="target",
        realized_r="2",
        methodology_sha256="sha256:" + "2" * 64,
        causal_provenance=("git:" + "3" * 40, "sha256:" + "4" * 64),
    )

    assert opportunity.volume is None
