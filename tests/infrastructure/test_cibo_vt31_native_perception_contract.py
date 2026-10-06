from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    TraderOpportunityEnvelope,
)
from qore.infrastructure.cibo_native_maximum_intelligence import (
    validate_native_maximum_perception,
)
from qore.infrastructure.traders.vt31_nas100_native_perception import (
    build_vt31_native_causal_perception,
)


def _bars() -> tuple[SimpleNamespace, ...]:
    opened = datetime(2026, 1, 5, 14, 0, tzinfo=UTC)
    rows = []
    for index in range(90):
        start = opened + timedelta(minutes=index)
        price = 100.0 + index * 0.01
        rows.append(
            SimpleNamespace(
                opened_at=start,
                closed_at=start + timedelta(minutes=1),
                open=price,
                high=price + 0.05,
                low=price - 0.05,
                close=price + 0.01,
            )
        )
    return tuple(rows)


def test_vt31_native_perception_is_admissible_to_native_max() -> None:
    context = build_vt31_native_causal_perception(
        day_bars=_bars(),
        prior_admitted_day_bars=(),
        prior_admitted_days=(),
        decision_at=datetime(2026, 1, 5, 15, 30, tzinfo=UTC),
        side="long",
        intended_entry=Decimal("100"),
        stop_loss=Decimal("99"),
        take_profit=Decimal("102"),
    )

    payload = dict(context)
    assert payload["cibo_native_perception_complete"] == "true"
    assert payload["cibo_native_perception_version"]
    assert not any("future" in key.lower() for key in payload)
    assert not any("outcome" in key.lower() for key in payload)

    opportunity = TraderOpportunityEnvelope(
        trader_id=TraderLineage.VT31_NAS100,
        signal_fingerprint="vt31-native-contract",
        qore_symbol="NAS100",
        provider_symbol="NAS100",
        side="long",
        entry_type="market",
        intended_entry=Decimal("100"),
        stop_loss=Decimal("99"),
        take_profit=Decimal("102"),
        stop_loss_per_volume=Decimal("1"),
        margin_per_volume=Decimal("10"),
        volume_step=Decimal("0.01"),
        minimum_volume=Decimal("0.01"),
        maximum_volume=Decimal("100"),
        decision_context=context,
    )

    assert validate_native_maximum_perception((opportunity,)) == (
        ("vt31-native-contract", len(context)),
    )
